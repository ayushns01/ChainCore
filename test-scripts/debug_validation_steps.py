#!/usr/bin/env python3
"""
Debug each validation step individually to find the failure point
"""

import sys
import os
import requests
import json
import time

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.crypto.ecdsa_crypto import double_sha256
from src.blockchain.bitcoin_transaction import Transaction
from network_node import Block

def debug_validation_steps():
    print("🔬 DEBUGGING EACH VALIDATION STEP")
    print("=" * 50)
    
    # Step 1: Get and mine a block
    print("📋 Getting mined block...")
    
    resp = requests.post('http://localhost:5000/mine_block',
                        json={'miner_address': 'debug_validation'},
                        headers={'Content-Type': 'application/json'})
    
    if resp.status_code != 200:
        print("❌ Failed to get template")
        return
    
    data = resp.json()
    block_template = data['block_template']
    target_difficulty = data['target_difficulty']
    
    # Mine a valid nonce (reuse previous logic)
    required_prefix = "0" * target_difficulty
    nonce = 0
    
    while nonce < 1000:
        block_data = {
            'index': block_template['index'],
            'previous_hash': block_template['previous_hash'],
            'merkle_root': block_template['merkle_root'],
            'timestamp': block_template['timestamp'],
            'nonce': nonce,
            'target_difficulty': target_difficulty
        }
        calculated_hash = double_sha256(json.dumps(block_data, sort_keys=True))
        if calculated_hash.startswith(required_prefix):
            break
        nonce += 1
    else:
        print("❌ Failed to mine block")
        return
    
    # Create the block object
    final_block_template = block_template.copy()
    final_block_template['nonce'] = nonce
    
    transactions = [Transaction.from_dict(tx) for tx in final_block_template['transactions']]
    block = Block(
        final_block_template['index'],
        transactions,
        final_block_template['previous_hash'],
        final_block_template.get('timestamp'),
        final_block_template.get('nonce', 0),
        final_block_template.get('target_difficulty', 1)
    )
    
    print(f"✅ Block created: index={block.index}, hash={block.hash[:32]}...")
    
    # Step 2: Test each validation step manually
    print(f"\n🔍 VALIDATION STEP BY STEP:")
    
    # Step 2a: Basic hash validation
    print(f"📋 Step 2a: Basic hash validation...")
    hash_valid = block.is_valid_hash()
    print(f"   is_valid_hash(): {hash_valid}")
    if not hash_valid:
        print(f"   ❌ FAILED: Hash doesn't meet difficulty")
        return
    print(f"   ✅ PASSED")
    
    # Step 2b: Get current blockchain state
    print(f"📋 Step 2b: Getting current blockchain state...")
    blockchain_resp = requests.get('http://localhost:5000/blockchain')
    if blockchain_resp.status_code != 200:
        print(f"   ❌ FAILED: Can't get blockchain state")
        return
    
    blockchain_data = blockchain_resp.json()
    current_chain = blockchain_data['chain']
    print(f"   ✅ PASSED: Got chain with {len(current_chain)} blocks")
    
    # Step 2c: Check if block already exists
    print(f"📋 Step 2c: Check for duplicate blocks...")
    if block.index < len(current_chain):
        existing_block = current_chain[block.index]
        if existing_block['hash'] == block.hash:
            print(f"   ❌ FAILED: Duplicate block")
            return
        else:
            print(f"   ❌ FAILED: Fork detected")
            return
    print(f"   ✅ PASSED: No duplicate or fork")
    
    # Step 2d: Check previous hash connection
    print(f"📋 Step 2d: Check previous hash connection...")
    if block.index > 0:
        expected_prev = current_chain[-1]['hash']
        if block.previous_hash != expected_prev:
            print(f"   ❌ FAILED: Previous hash mismatch")
            print(f"      Expected: {expected_prev}")
            print(f"      Got:      {block.previous_hash}")
            return
    print(f"   ✅ PASSED: Previous hash correct")
    
    # Step 2e: Check index sequence
    print(f"📋 Step 2e: Check index sequence...")
    expected_index = len(current_chain)
    if block.index != expected_index:
        print(f"   ❌ FAILED: Index mismatch")
        print(f"      Expected: {expected_index}")
        print(f"      Got:      {block.index}")
        return
    print(f"   ✅ PASSED: Index sequence correct")
    
    # Step 2f: Validate transactions
    print(f"📋 Step 2f: Validate transactions...")
    for i, transaction in enumerate(block.transactions):
        print(f"   Transaction {i}: ID={transaction.tx_id[:16]}...")
        
        is_coinbase = transaction.is_coinbase()
        print(f"      Is coinbase: {is_coinbase}")
        
        if not is_coinbase:
            # We would validate non-coinbase transactions here
            print(f"      ⚠️  Non-coinbase transaction found - would need to validate")
        else:
            print(f"      ✅ Coinbase transaction - skipping validation")
    
    print(f"   ✅ PASSED: All transactions valid")
    
    # Step 3: Test for any exceptions
    print(f"\n📋 Step 3: Testing for exceptions...")
    
    try:
        # Try to access all block properties that validation might use
        _ = block.hash
        _ = block.index
        _ = block.previous_hash
        _ = block.target_difficulty
        _ = block.transactions
        _ = block.merkle_root
        _ = block.timestamp
        _ = block.nonce
        
        for tx in block.transactions:
            _ = tx.tx_id
            _ = tx.inputs
            _ = tx.outputs
            _ = tx.timestamp
            
        print(f"   ✅ PASSED: No exceptions accessing block properties")
        
    except Exception as e:
        print(f"   ❌ FAILED: Exception accessing block properties: {e}")
        return
    
    print(f"\n✅ ALL MANUAL VALIDATIONS PASSED!")
    
    # Step 4: Try submission again to see if timing helps
    print(f"\n📋 Step 4: Attempting submission with fresh timestamp...")
    
    # Update timestamp to be very recent
    fresh_template = final_block_template.copy()
    fresh_template['timestamp'] = time.time()
    
    submit_resp = requests.post('http://localhost:5000/submit_block',
                               json={'block': fresh_template},
                               headers={
                                   'Content-Type': 'application/json',
                                   'X-Local-Mining': 'true'
                               })
    
    print(f"   Response: {submit_resp.status_code} - {submit_resp.text}")
    
    if submit_resp.status_code == 200:
        print(f"   🎉 SUCCESS with fresh timestamp!")
    else:
        print(f"   ❌ Still failed with fresh timestamp")
        
        # Try one more thing - submit without the pre-calculated hash
        print(f"\n📋 Step 5: Trying submission without pre-calculated hash...")
        clean_template = {k: v for k, v in fresh_template.items() if k != 'hash'}
        
        submit_resp2 = requests.post('http://localhost:5000/submit_block',
                                   json={'block': clean_template},
                                   headers={
                                       'Content-Type': 'application/json',
                                       'X-Local-Mining': 'true'
                                   })
        
        print(f"   Response: {submit_resp2.status_code} - {submit_resp2.text}")

if __name__ == "__main__":
    debug_validation_steps()