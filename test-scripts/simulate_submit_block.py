#!/usr/bin/env python3
"""
Simulate the exact submit_block process to identify validation failure
"""

import sys
import os
import requests
import json

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.crypto.ecdsa_crypto import double_sha256
from src.blockchain.bitcoin_transaction import Transaction
from network_node import Block

def simulate_submit_block():
    print("🔬 SIMULATING SUBMIT_BLOCK PROCESS")
    print("=" * 50)
    
    # Step 1: Get a mined block (same as previous tests)
    print("📋 Step 1: Getting and mining block...")
    
    resp = requests.post('http://localhost:5000/mine_block',
                        json={'miner_address': 'simulate_test'},
                        headers={'Content-Type': 'application/json'})
    
    if resp.status_code != 200:
        print("❌ Failed to get template")
        return
    
    data = resp.json()
    block_template = data['block_template']
    target_difficulty = data['target_difficulty']
    
    # Mine a valid nonce
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
            print(f"✅ Mined block with nonce {nonce}, hash: {calculated_hash[:32]}...")
            break
        nonce += 1
    else:
        print("❌ Failed to mine block")
        return
    
    # Step 2: Simulate submit_block handler logic
    print("\n📋 Step 2: Simulating submit_block handler...")
    
    # Prepare block data as submit_block would receive it
    final_block_template = block_template.copy()
    final_block_template['nonce'] = nonce
    
    # This is the data the API handler receives
    submitted_data = {'block': final_block_template}
    block_data = submitted_data.get('block', submitted_data)
    
    print(f"   Received block data: index={block_data['index']}")
    
    # Step 3: Reconstruct block exactly as submit_block does
    print("\n📋 Step 3: Reconstructing block...")
    
    try:
        # Reconstruct transactions
        transactions = [Transaction.from_dict(tx) for tx in block_data['transactions']]
        print(f"   ✅ Reconstructed {len(transactions)} transactions")
        
        # Create Block object
        block = Block(
            block_data['index'],
            transactions,
            block_data['previous_hash'],
            block_data.get('timestamp'),
            block_data.get('nonce', 0),
            block_data.get('target_difficulty', 1)  # Using centralized config default
        )
        
        print(f"   ✅ Block object created")
        print(f"      Index: {block.index}")
        print(f"      Hash: {block.hash[:32]}...")
        print(f"      Target difficulty: {block.target_difficulty}")
        print(f"      Previous hash: {block.previous_hash[:32]}...")
        
    except Exception as e:
        print(f"   ❌ Block reconstruction failed: {e}")
        return
    
    # Step 4: Test block validation
    print("\n📋 Step 4: Testing block validation...")
    
    # Test is_valid_hash
    hash_valid = block.is_valid_hash()
    print(f"   is_valid_hash(): {hash_valid}")
    
    if not hash_valid:
        required = "0" * block.target_difficulty
        print(f"   ❌ Hash validation failed:")
        print(f"      Required prefix: '{required}'")
        print(f"      Actual hash: '{block.hash[:len(required) + 10]}...'")
        print(f"      Hash starts with required prefix: {block.hash.startswith(required)}")
        return
    
    # Test manual validation checks
    print(f"   ✅ Hash meets difficulty requirement")
    
    # Check if this would pass blockchain validation
    print("\n📋 Step 5: Checking blockchain-level validation...")
    
    # Get current blockchain state
    blockchain_resp = requests.get('http://localhost:5000/blockchain')
    if blockchain_resp.status_code == 200:
        blockchain_data = blockchain_resp.json()
        current_chain = blockchain_data['chain']
        
        print(f"   Current chain length: {len(current_chain)}")
        print(f"   Last block index: {current_chain[-1]['index']}")
        print(f"   Last block hash: {current_chain[-1]['hash'][:32]}...")
        
        # Check index sequence
        expected_index = len(current_chain)
        if block.index != expected_index:
            print(f"   ❌ Index mismatch: expected {expected_index}, got {block.index}")
            return
        
        # Check previous hash
        expected_prev_hash = current_chain[-1]['hash']
        if block.previous_hash != expected_prev_hash:
            print(f"   ❌ Previous hash mismatch:")
            print(f"      Expected: {expected_prev_hash}")
            print(f"      Got:      {block.previous_hash}")
            return
        
        print(f"   ✅ Index sequence correct: {block.index}")
        print(f"   ✅ Previous hash correct")
        
    else:
        print(f"   ❌ Failed to get blockchain state")
        return
    
    print(f"\n✅ ALL VALIDATIONS PASSED - Block should be accepted!")
    
    # Step 6: Try actual submission
    print(f"\n📋 Step 6: Attempting actual submission...")
    
    submit_resp = requests.post('http://localhost:5000/submit_block',
                               json={'block': final_block_template},
                               headers={
                                   'Content-Type': 'application/json',
                                   'X-Local-Mining': 'true'
                               })
    
    print(f"   Response code: {submit_resp.status_code}")
    print(f"   Response: {submit_resp.text}")
    
    if submit_resp.status_code == 200:
        print(f"   🎉 SUCCESS: Block was accepted!")
        
        # Verify blockchain length increased
        new_resp = requests.get('http://localhost:5000/status')
        if new_resp.status_code == 200:
            new_length = new_resp.json()['blockchain_length'] 
            print(f"   📊 New blockchain length: {new_length}")
    else:
        print(f"   ❌ FAILED: Block rejected despite passing all validations")

if __name__ == "__main__":
    simulate_submit_block()