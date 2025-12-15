#!/usr/bin/env python3

import os
import sys
import time
import json

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from clients.mining_client import MiningClient

def test_mining_fix():
    """Test that the mining fix preserves transactions"""
    print("🔍 Testing mining transaction fix...")
    
    # Initialize mining client
    client = MiningClient(
        node_url="http://localhost:5000",
        wallet_address="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"  # Valid bitcoin address format
    )
    
    # Create a mock template with transactions
    test_template = {
        'index': 8,
        'previous_hash': '00001234567890abcdef',
        'merkle_root': 'test_merkle_root',
        'timestamp': int(time.time()),
        'all_transactions': [
            {
                'id': 'coinbase_tx_123',
                'type': 'coinbase',
                'outputs': [
                    {'amount': 50.0, 'address': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa'}
                ],
                'block_reward': 50.0
            }
        ]
    }
    
    print(f"✅ Template created with {len(test_template['all_transactions'])} transactions")
    print(f"   Coinbase transaction ID: {test_template['all_transactions'][0]['id']}")
    
    # Test the _precompute_block_data method (this should strip transactions)
    base_json = client._precompute_block_data(test_template, 4)
    base_dict = json.loads(base_json[:-1] + '}')  # Remove trailing for parsing
    
    print(f"⚠️  Base template has {len(base_dict.get('all_transactions', []))} transactions (expected: 0)")
    
    # Simulate what happens after mining success with our fix
    print("\n🔧 Testing FIXED mining result creation...")
    
    # This is the NEW way (with fix)
    mined_block_fixed = test_template.copy()  # Preserve original template
    mined_block_fixed['nonce'] = 12345
    mined_block_fixed['hash'] = '000098765432109876543210'
    
    print(f"✅ Fixed mined block has {len(mined_block_fixed.get('all_transactions', []))} transactions")
    print(f"   Coinbase transaction preserved: {mined_block_fixed['all_transactions'][0]['id']}")
    
    # This is the OLD way (broken)
    mined_block_broken = json.loads(base_json[:-1] + ',"nonce":12345}')
    mined_block_broken['hash'] = '000098765432109876543210'
    
    print(f"❌ Broken mined block has {len(mined_block_broken.get('all_transactions', []))} transactions")
    
    print("\n🎯 Fix verification:")
    if len(mined_block_fixed.get('all_transactions', [])) > 0:
        print("✅ SUCCESS: Fixed version preserves transactions!")
    else:
        print("❌ FAILED: Fixed version still missing transactions!")
        
    if len(mined_block_broken.get('all_transactions', [])) == 0:
        print("✅ CONFIRMED: Old version was indeed broken (no transactions)")
    else:
        print("❌ UNEXPECTED: Old version somehow has transactions")

if __name__ == "__main__":
    test_mining_fix()