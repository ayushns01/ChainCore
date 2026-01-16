#!/usr/bin/env python3
import sys
import os
import json
import time
import hashlib

# Add src and parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.crypto.ecdsa_crypto import double_sha256

# Sample block template data
block_template = {
    'index': 1,
    'previous_hash': '0000ed166891a0a870e805a85d69585fbac0bd7f1167182b81b6dce8a04174d3',
    'merkle_root': '5789a01464adf0358700b7447bb275f336e8f2fe9d23aa328ba08064226f54f0',
    'timestamp': 1755041812.7182798,
    'nonce': 0,
    'target_difficulty': 4
}

# Mine a block
target = '0000'
nonce = 0
while True:
    block_template['nonce'] = nonce
    block_data = {
        'index': block_template['index'],
        'previous_hash': block_template['previous_hash'],
        'merkle_root': block_template['merkle_root'],
        'timestamp': block_template['timestamp'],
        'nonce': nonce,
        'target_difficulty': 4
    }
    
    block_hash = double_sha256(json.dumps(block_data, sort_keys=True))
    if block_hash.startswith(target):
        print(f'Mined block! Hash: {block_hash}, Nonce: {nonce}')
        print(f'Block data: {json.dumps(block_data, sort_keys=True)}')
        
        # Create full block for submission
        transactions = [
            {
                "inputs": [
                    {
                        "output_index": 4294967295,
                        "script_sig": "COINBASE_BLOCK_1",
                        "signature": {},
                        "tx_id": "0000000000000000000000000000000000000000000000000000000000000000"
                    }
                ],
                "lock_time": 0,
                "outputs": [
                    {
                        "amount": 50.0,
                        "recipient_address": "test_miner_001",
                        "script_pubkey": "PAY_TO_ADDRESS(test_miner_001)"
                    }
                ],
                "timestamp": 1755041812.718132,
                "tx_id": "5789a01464adf0358700b7447bb275f336e8f2fe9d23aa328ba08064226f54f0",
                "version": 1
            }
        ]
        
        full_block = {
            'index': block_template['index'],
            'previous_hash': block_template['previous_hash'],
            'merkle_root': block_template['merkle_root'],
            'timestamp': block_template['timestamp'],
            'nonce': nonce,
            'target_difficulty': 4,
            'hash': block_hash,
            'transactions': transactions
        }
        
        print(f'Full block: {json.dumps(full_block, indent=2)}')
        break
    nonce += 1
    if nonce > 100000:
        print('Mining failed - took too long')
        break