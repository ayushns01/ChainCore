#!/usr/bin/env python3
"""
Test coinbase transaction validation specifically
"""

import sys
import os
import requests
import json

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.blockchain.bitcoin_transaction import Transaction

def test_coinbase_validation():
    print("🔍 TESTING COINBASE VALIDATION")
    print("=" * 40)
    
    # Get a block template to test with real coinbase transaction
    resp = requests.post('http://localhost:5000/mine_block',
                        json={'miner_address': 'coinbase_test'},
                        headers={'Content-Type': 'application/json'})
    
    if resp.status_code != 200:
        print("❌ Failed to get template")
        return
    
    data = resp.json()
    block_template = data['block_template']
    
    # Get the coinbase transaction
    coinbase_tx_data = block_template['transactions'][0]
    print(f"📊 Coinbase transaction data:")
    print(f"   TX ID: {coinbase_tx_data['tx_id'][:16]}...")
    print(f"   Inputs: {len(coinbase_tx_data['inputs'])}")
    print(f"   Outputs: {len(coinbase_tx_data['outputs'])}")
    
    if coinbase_tx_data['inputs']:
        inp = coinbase_tx_data['inputs'][0]
        print(f"   Input 0: tx_id={inp['tx_id'][:16]}..., output_index={inp['output_index']}")
    
    # Reconstruct the transaction
    coinbase_tx = Transaction.from_dict(coinbase_tx_data)
    
    print(f"\n🔍 Testing is_coinbase():")
    is_coinbase = coinbase_tx.is_coinbase()
    print(f"   is_coinbase(): {is_coinbase}")
    
    # Check the conditions manually
    print(f"\n🔍 Manual coinbase check:")
    print(f"   Input count: {len(coinbase_tx.inputs)}")
    if coinbase_tx.inputs:
        inp = coinbase_tx.inputs[0]
        print(f"   Input 0 tx_id: {inp.tx_id}")
        print(f"   Input 0 output_index: {inp.output_index}")
        print(f"   Expected tx_id: {'0' * 64}")
        print(f"   Expected output_index: {0xFFFFFFFF}")
        
        tx_id_match = inp.tx_id == "0" * 64
        output_index_match = inp.output_index == 0xFFFFFFFF
        
        print(f"   TX ID matches: {tx_id_match}")
        print(f"   Output index matches: {output_index_match}")
        
        manual_coinbase = (len(coinbase_tx.inputs) == 1 and tx_id_match and output_index_match)
        print(f"   Manual coinbase check: {manual_coinbase}")
    
    if is_coinbase:
        print("✅ Coinbase transaction detected correctly")
    else:
        print("❌ Coinbase transaction NOT detected - this is the problem!")
        
    # Test what happens in validation loop
    print(f"\n🔍 Testing validation loop logic:")
    should_validate = not coinbase_tx.is_coinbase()
    print(f"   Should validate transaction: {should_validate}")
    
    if should_validate:
        print("❌ ERROR: Coinbase transaction would be validated (should be skipped)")
    else:
        print("✅ Coinbase transaction would be skipped in validation")

if __name__ == "__main__":
    test_coinbase_validation()