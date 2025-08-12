#!/usr/bin/env python3
"""
Manual mining test to verify blockchain growth
"""

import requests
import hashlib
import json
import time
import sys
import os

# Add src to path for double_sha256 function
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from src.crypto.ecdsa_crypto import double_sha256

def calculate_merkle_root(transactions):
    """Calculate merkle root for transactions"""
    if not transactions:
        return "0" * 64
    
    tx_hashes = [tx.get('tx_id', '') for tx in transactions]
    
    while len(tx_hashes) > 1:
        if len(tx_hashes) % 2 == 1:
            tx_hashes.append(tx_hashes[-1])
        
        next_level = []
        for i in range(0, len(tx_hashes), 2):
            combined = tx_hashes[i] + tx_hashes[i+1]
            next_level.append(hashlib.sha256(combined.encode()).hexdigest())
        
        tx_hashes = next_level
    
    return tx_hashes[0] if tx_hashes else "0" * 64

def test_manual_mining():
    # Get block template
    print('🔍 Getting block template...')
    resp = requests.post('http://localhost:5000/mine_block', 
                        json={'miner_address': 'manual_test_miner'}, 
                        headers={'Content-Type': 'application/json'})

    if resp.status_code != 200:
        print('Failed to get template:', resp.text)
        return False

    data = resp.json()
    block_template = data['block_template']
    target_difficulty = data['target_difficulty']

    print(f'⛏️  Mining block #{block_template["index"]} with difficulty {target_difficulty}...')

    # Calculate merkle root (this is needed for proper hash calculation)
    merkle_root = calculate_merkle_root(block_template['transactions'])
    
    # Simple mining loop using the same hash calculation as Block class
    required_prefix = '0' * target_difficulty
    nonce = 0
    start_time = time.time()

    while True:
        # Create block data for hashing (same structure as Block._calculate_hash)
        block_data = {
            'index': block_template['index'],
            'previous_hash': block_template['previous_hash'],
            'merkle_root': merkle_root,
            'timestamp': block_template['timestamp'],
            'nonce': nonce,
            'target_difficulty': target_difficulty
        }
        
        # Calculate hash using the same method as Block class
        hash_obj = double_sha256(json.dumps(block_data, sort_keys=True))
        
        if hash_obj.startswith(required_prefix):
            mining_time = time.time() - start_time
            print(f'✅ Block mined! Hash: {hash_obj[:32]}...')
            print(f'   Nonce: {nonce}, Time: {mining_time:.2f}s')
            
            # Update the block template with the successful nonce
            block_template['nonce'] = nonce
            
            # Submit the block (don't manually set hash - let Block constructor calculate it)
            submit_resp = requests.post('http://localhost:5000/submit_block',
                                       json={'block': block_template},
                                       headers={
                                           'Content-Type': 'application/json',
                                           'X-Local-Mining': 'true'
                                       })
            
            if submit_resp.status_code == 200:
                print('🎉 Block submitted successfully!')
                return True
            else:
                print('❌ Block submission failed:', submit_resp.text)
                return False
        
        nonce += 1
        if nonce % 1000 == 0:
            print(f'   Hashing... nonce: {nonce}')
        
        if nonce > 100000:  # Safety limit
            print('⏱️  Mining timeout after 100k attempts')
            return False

if __name__ == "__main__":
    # Check initial state
    print("📊 Before mining:")
    resp = requests.get('http://localhost:5000/status')
    if resp.status_code == 200:
        status = resp.json()
        print(f"   Blockchain length: {status['blockchain_length']}")
    
    # Try to mine a block
    success = test_manual_mining()
    
    # Check final state
    print("\n📊 After mining:")
    resp = requests.get('http://localhost:5000/status')
    if resp.status_code == 200:
        status = resp.json()
        print(f"   Blockchain length: {status['blockchain_length']}")
        
    if success:
        print("\n✅ Manual mining test completed successfully!")
    else:
        print("\n❌ Manual mining test failed!")