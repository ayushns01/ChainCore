#!/usr/bin/env python3
import requests
import json

# The mined block from our debug script
mined_block = {
    "index": 1,
    "previous_hash": "0000ed166891a0a870e805a85d69585fbac0bd7f1167182b81b6dce8a04174d3",
    "merkle_root": "5789a01464adf0358700b7447bb275f336e8f2fe9d23aa328ba08064226f54f0",
    "timestamp": 1755041812.7182798,
    "nonce": 45682,
    "target_difficulty": 4,
    "hash": "0000d78db278200d4a06b696a8d243937e1e44391e0e8b44476200720ea2a22a",
    "transactions": [
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
}

try:
    response = requests.post(
        "http://localhost:5000/submit_block",
        json=mined_block,
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Success: {result}")
    else:
        print(f"Failed: {response.status_code}")
        
except Exception as e:
    print(f"Error: {e}")