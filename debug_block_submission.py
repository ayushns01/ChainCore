#!/usr/bin/env python3
"""
Debug block submission to identify validation failures
"""

import sys
import os
import requests
import json

# Add src to path  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from src.crypto.ecdsa_crypto import double_sha256

def debug_block_submission():
    print("🔍 DEBUG: Block Submission Process")
    print("=" * 50)
    
    # Step 1: Get block template
    print("📋 Step 1: Getting block template...")
    resp = requests.post('http://localhost:5000/mine_block',
                        json={'miner_address': 'debug_miner'},
                        headers={'Content-Type': 'application/json'})
    
    if resp.status_code != 200:
        print(f"❌ Failed to get template: {resp.text}")
        return
    
    data = resp.json()
    block_template = data['block_template']
    target_difficulty = data['target_difficulty']
    
    print(f"✅ Template received: index={block_template['index']}, difficulty={target_difficulty}")
    
    # Step 2: "Mine" the block (find valid nonce)
    print("📋 Step 2: Mining block...")
    
    required_prefix = "0" * target_difficulty
    nonce = 0
    
    while nonce < 1000:  # Safety limit
        # Update block template with current nonce
        test_block = block_template.copy()
        test_block['nonce'] = nonce
        
        # Calculate hash using Block class method
        block_data = {
            'index': test_block['index'],
            'previous_hash': test_block['previous_hash'],
            'merkle_root': test_block['merkle_root'],
            'timestamp': test_block['timestamp'],
            'nonce': nonce,
            'target_difficulty': target_difficulty
        }
        
        calculated_hash = double_sha256(json.dumps(block_data, sort_keys=True))
        
        if calculated_hash.startswith(required_prefix):
            print(f"✅ Valid hash found! Nonce: {nonce}, Hash: {calculated_hash[:32]}...")
            break
        nonce += 1
    else:
        print("❌ No valid hash found in 1000 attempts")
        return
    
    # Step 3: Prepare submission data
    print("📋 Step 3: Preparing submission...")
    
    final_block = block_template.copy()
    final_block['nonce'] = nonce
    
    print("📊 Block data being submitted:")
    print(f"   Index: {final_block['index']}")
    print(f"   Previous Hash: {final_block['previous_hash'][:32]}...")
    print(f"   Timestamp: {final_block['timestamp']}")
    print(f"   Nonce: {final_block['nonce']}")
    print(f"   Target Difficulty: {final_block['target_difficulty']}")
    print(f"   Transactions: {len(final_block['transactions'])}")
    print(f"   Merkle Root: {final_block['merkle_root'][:32]}...")
    
    # Step 4: Submit block
    print("📋 Step 4: Submitting block...")
    
    submit_resp = requests.post('http://localhost:5000/submit_block',
                               json={'block': final_block},
                               headers={
                                   'Content-Type': 'application/json',
                                   'X-Local-Mining': 'true'
                               })
    
    print(f"📊 Submission response: {submit_resp.status_code}")
    print(f"📊 Response body: {submit_resp.text}")
    
    if submit_resp.status_code == 200:
        print("✅ Block submission successful!")
        
        # Check blockchain length
        status_resp = requests.get('http://localhost:5000/status')
        if status_resp.status_code == 200:
            new_length = status_resp.json()['blockchain_length']
            print(f"📊 New blockchain length: {new_length}")
    else:
        print("❌ Block submission failed")
        
        # Let's verify our hash calculation matches what Block constructor would produce
        print("\n🔍 DETAILED VALIDATION DEBUG:")
        
        # Simulate Block object creation
        print("📊 What Block constructor would calculate:")
        print(f"   Block data for hashing: {json.dumps(block_data, sort_keys=True)}")
        print(f"   Calculated hash: {calculated_hash}")
        print(f"   Meets difficulty? {calculated_hash.startswith(required_prefix)}")
        
        # Check if transactions have required fields
        print("📊 Transaction validation:")
        for i, tx in enumerate(final_block['transactions']):
            print(f"   TX {i}: ID={tx.get('tx_id', 'MISSING')[:16]}...")
            print(f"          Inputs: {len(tx.get('inputs', []))}")
            print(f"          Outputs: {len(tx.get('outputs', []))}")
            print(f"          Version: {tx.get('version', 'MISSING')}")

if __name__ == "__main__":
    debug_block_submission()