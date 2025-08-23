#!/usr/bin/env python3
"""
Test Actual Mining and Database Recording
Performs complete mining cycle: template -> mining -> submission -> database verification
"""

import requests
import json
import time
import hashlib
import psycopg2
from datetime import datetime

def mine_block_simple(template, target_difficulty=4):
    """Simple mining function to find a valid nonce"""
    target = "0" * target_difficulty
    
    block_data = template['block_template']
    nonce = 0
    max_attempts = 100000
    
    print(f"  Mining with target: {target}...")
    start_time = time.time()
    
    while nonce < max_attempts:
        # Create block hash with current nonce
        block_data['nonce'] = nonce
        block_string = json.dumps(block_data, sort_keys=True)
        block_hash = hashlib.sha256(block_string.encode()).hexdigest()
        
        if block_hash.startswith(target):
            mining_time = time.time() - start_time
            print(f"  [SUCCESS] Block mined! Hash: {block_hash[:20]}...")
            print(f"  [TIME] Mining time: {mining_time:.2f}s, Attempts: {nonce + 1}")
            
            # Update the template with the found nonce and hash
            block_data['hash'] = block_hash
            return block_data, True
            
        nonce += 1
        
        if nonce % 10000 == 0:
            print(f"  [MINING] Mining... attempt {nonce}")
    
    print(f"  [ERROR] Mining failed after {max_attempts} attempts")
    return None, False

def test_complete_mining_cycle():
    """Test complete mining cycle and database recording"""
    print("ChainCore Complete Mining Test")
    print("=" * 50)
    
    node_url = "http://localhost:5000"
    
    # Step 1: Get mining template
    print("\n=== Step 1: Getting Mining Template ===")
    try:
        response = requests.post(
            f"{node_url}/mine_block",
            json={"miner_address": "complete_test_miner"},
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"[ERROR] Failed to get mining template: {response.status_code}")
            return False
            
        template = response.json()
        print(f"[PASS] Mining template received for block index {template['block_template']['index']}")
        
    except Exception as e:
        print(f"[ERROR] Error getting mining template: {e}")
        return False
    
    # Step 2: Mine the block
    print("\n=== Step 2: Mining Block ===")
    mined_block, mining_success = mine_block_simple(template)
    
    if not mining_success:
        print("[ERROR] Mining failed")
        return False
    
    # Step 3: Submit the mined block
    print("\n=== Step 3: Submitting Mined Block ===")
    try:
        submit_response = requests.post(
            f"{node_url}/submit_block",
            json={"block": mined_block},
            timeout=15
        )
        
        print(f"Submit response status: {submit_response.status_code}")
        
        if submit_response.status_code == 200:
            submit_result = submit_response.json()
            print(f"[PASS] Block submitted successfully!")
            print(f"[INFO] Result: {json.dumps(submit_result, indent=2)[:200]}...")
        else:
            print(f"[ERROR] Block submission failed: {submit_response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error submitting block: {e}")
        return False
    
    # Step 4: Wait for database recording
    print("\n=== Step 4: Verifying Database Recording ===")
    time.sleep(2)  # Wait for database writes
    
    try:
        conn = psycopg2.connect(
            dbname='chaincore_blockchain',
            user='chaincore_user', 
            password='chaincore_secure_2024',
            host='localhost',
            port=5432
        )
        cur = conn.cursor()
        
        # Check blocks table
        cur.execute('SELECT COUNT(*) FROM blocks')
        block_count = cur.fetchone()[0]
        print(f"[BLOCKS] Blocks in database: {block_count}")
        
        if block_count > 0:
            cur.execute('SELECT block_index, hash, miner_address, created_at FROM blocks ORDER BY block_index DESC LIMIT 3')
            blocks = cur.fetchall()
            print(f"Recent blocks:")
            for block in blocks:
                print(f"  Block {block[0]}: {block[1][:20]}... by {block[2]} at {block[3]}")
        
        # Check mining stats
        cur.execute('SELECT COUNT(*) FROM mining_stats')
        mining_stats_count = cur.fetchone()[0]
        print(f"[MINING] Mining stats records: {mining_stats_count}")
        
        # Check transactions
        cur.execute('SELECT COUNT(*) FROM transactions')
        transaction_count = cur.fetchone()[0]
        print(f"[TRANSACTIONS] Transactions in database: {transaction_count}")
        
        # Check UTXOs
        cur.execute('SELECT COUNT(*) FROM utxos')
        utxo_count = cur.fetchone()[0]
        print(f"[UTXOS] UTXOs in database: {utxo_count}")
        
        cur.close()
        conn.close()
        
        success = block_count > 0 and transaction_count > 0
        
        print(f"\n=== Mining Database Test Results ===")
        print(f"Block recorded: {'[PASS] YES' if block_count > 0 else '[FAIL] NO'}")
        print(f"Transactions recorded: {'[PASS] YES' if transaction_count > 0 else '[FAIL] NO'}")
        print(f"UTXOs recorded: {'[PASS] YES' if utxo_count > 0 else '[FAIL] NO'}")
        print(f"Mining stats: {'[PASS] YES' if mining_stats_count > 0 else '[FAIL] NO'}")
        
        return success
        
    except Exception as e:
        print(f"[ERROR] Database verification error: {e}")
        return False

if __name__ == "__main__":
    success = test_complete_mining_cycle()
    print(f"\n[RESULT] Overall Result: {'[SUCCESS]' if success else '[FAILED]'}")
    exit(0 if success else 1)