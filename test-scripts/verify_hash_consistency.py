#!/usr/bin/env python3
"""
Verify hash calculation consistency between template and reconstructed Block
"""

import sys
import os
import requests
import json

# Add src and parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.crypto.ecdsa_crypto import double_sha256
from src.blockchain.bitcoin_transaction import Transaction

def verify_hash_consistency():
    print("🔍 VERIFYING HASH CALCULATION CONSISTENCY")
    print("=" * 60)
    
    # Get block template
    resp = requests.post('http://localhost:5000/mine_block',
                        json={'miner_address': 'hash_test'},
                        headers={'Content-Type': 'application/json'})
    
    if resp.status_code != 200:
        print("❌ Failed to get template")
        return
    
    data = resp.json()
    block_template = data['block_template']
    
    print("📊 Original template:")
    print(f"   Merkle Root: {block_template['merkle_root']}")
    print(f"   Hash: {block_template['hash'][:32]}...")
    
    # Step 1: Verify template's merkle root calculation
    print("\n🔍 Step 1: Verify template merkle root...")
    
    tx_hashes = [tx['tx_id'] for tx in block_template['transactions']]
    print(f"   TX IDs from template: {[tx_id[:16]+'...' for tx_id in tx_hashes]}")
    
    # Manual merkle root calculation
    def calculate_merkle_root(tx_hashes):
        if not tx_hashes:
            return "0" * 64
        
        while len(tx_hashes) > 1:
            if len(tx_hashes) % 2 == 1:
                tx_hashes.append(tx_hashes[-1])
            
            next_level = []
            for i in range(0, len(tx_hashes), 2):
                combined = tx_hashes[i] + tx_hashes[i+1]
                import hashlib
                next_level.append(hashlib.sha256(combined.encode()).hexdigest())
            
            tx_hashes = next_level
        
        return tx_hashes[0]
    
    manual_merkle = calculate_merkle_root(tx_hashes)
    print(f"   Manual merkle calculation: {manual_merkle}")
    print(f"   Template merkle root: {block_template['merkle_root']}")
    print(f"   Merkle roots match: {manual_merkle == block_template['merkle_root']}")
    
    # Step 2: Reconstruct transactions and verify merkle root
    print("\n🔍 Step 2: Reconstruct transactions...")
    
    reconstructed_transactions = []
    for tx_data in block_template['transactions']:
        tx = Transaction.from_dict(tx_data)
        reconstructed_transactions.append(tx)
        print(f"   Reconstructed TX: {tx.tx_id[:16]}...")
        print(f"   Original TX ID:   {tx_data['tx_id'][:16]}...")
        print(f"   TX IDs match: {tx.tx_id == tx_data['tx_id']}")
    
    # Calculate merkle root from reconstructed transactions
    reconstructed_tx_ids = [tx.tx_id for tx in reconstructed_transactions]
    reconstructed_merkle = calculate_merkle_root(reconstructed_tx_ids)
    
    print(f"\n   Reconstructed merkle: {reconstructed_merkle}")
    print(f"   Original merkle: {block_template['merkle_root']}")
    print(f"   Reconstructed merkle matches: {reconstructed_merkle == block_template['merkle_root']}")
    
    # Step 3: Test Block object creation
    print("\n🔍 Step 3: Test Block object creation...")
    
    # Import Block
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from network_node import Block
    
    # Create Block object like the submit_block handler does
    block = Block(
        block_template['index'],
        reconstructed_transactions,
        block_template['previous_hash'],
        block_template['timestamp'],
        nonce=42,  # Test nonce
        target_difficulty=block_template['target_difficulty']
    )
    
    print(f"   Block merkle root: {block.merkle_root}")
    print(f"   Block hash: {block.hash[:32]}...")
    print(f"   Block merkle matches template: {block.merkle_root == block_template['merkle_root']}")
    
    # Step 4: Test mining a valid block
    print("\n🔍 Step 4: Mine a valid block...")
    
    required_prefix = "0" * block_template['target_difficulty']
    nonce = 0
    
    while nonce < 1000:
        test_block_data = {
            'index': block_template['index'],
            'previous_hash': block_template['previous_hash'],
            'merkle_root': block.merkle_root,  # Use the Block's calculated merkle root
            'timestamp': block_template['timestamp'],
            'nonce': nonce,
            'target_difficulty': block_template['target_difficulty']
        }
        
        calculated_hash = double_sha256(json.dumps(test_block_data, sort_keys=True))
        
        if calculated_hash.startswith(required_prefix):
            print(f"   ✅ Valid hash found at nonce {nonce}: {calculated_hash[:32]}...")
            
            # Create final block for submission test
            final_block_template = block_template.copy()
            final_block_template['nonce'] = nonce
            
            # Test submission
            print("\n🔍 Step 5: Test submission...")
            submit_resp = requests.post('http://localhost:5000/submit_block',
                                       json={'block': final_block_template},
                                       headers={
                                           'Content-Type': 'application/json',
                                           'X-Local-Mining': 'true'
                                       })
            
            print(f"   Submission result: {submit_resp.status_code}")
            print(f"   Response: {submit_resp.text}")
            
            if submit_resp.status_code == 200:
                print("   ✅ SUCCESS: Block accepted!")
            else:
                print("   ❌ FAILED: Block rejected")
            
            break
        
        nonce += 1
    else:
        print("   ❌ No valid hash found")

if __name__ == "__main__":
    verify_hash_consistency()