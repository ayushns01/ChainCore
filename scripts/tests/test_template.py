#!/usr/bin/env python3
"""
Test mining template to see if it contains transactions
"""
import sys
sys.path.append('src')

import requests
import json

def test_mining_template():
    """Test what the mining template contains"""
    print("🧪 TESTING MINING TEMPLATE CONTENT")
    print("=" * 50)
    
    node_url = "http://localhost:5000"
    miner_address = "18NDhHYAa3bx3jAZkc7HZf3vKr1JrwVXG3"
    
    print(f"\n1. TESTING NODE CONNECTIVITY:")
    try:
        status_response = requests.get(f"{node_url}/status", timeout=5)
        if status_response.status_code == 200:
            status = status_response.json()
            print(f"✅ Node is running:")
            print(f"   Node ID: {status.get('node_id', 'unknown')}")
            print(f"   Chain Length: {status.get('chain_length', 'unknown')}")
        else:
            print(f"❌ Node not responding properly: {status_response.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot connect to node: {e}")
        print(f"\nTo test this, start a node first:")
        print(f"python src/nodes/network_node.py --node-id test --api-port 5000")
        return
    
    print(f"\n2. REQUESTING MINING TEMPLATE:")
    try:
        template_request = {
            "miner_address": miner_address
        }
        
        response = requests.post(
            f"{node_url}/mine_block",
            json=template_request,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Template created successfully:")
            print(f"   Status: {data.get('status', 'unknown')}")
            
            # Extract block template
            block_template = data.get('block_template', {})
            target_difficulty = data.get('target_difficulty', 0)
            
            print(f"   Target Difficulty: {target_difficulty}")
            print(f"   Block Index: {block_template.get('index', 'unknown')}")
            print(f"   Previous Hash: {block_template.get('previous_hash', 'unknown')[:16]}...")
            
            # Check transactions
            transactions = block_template.get('transactions', [])
            print(f"\n3. ANALYZING TRANSACTIONS IN TEMPLATE:")
            print(f"   Transaction Count: {len(transactions)}")
            
            if transactions:
                print(f"   Transaction Details:")
                for i, tx in enumerate(transactions):
                    tx_id = tx.get('tx_id', 'unknown')
                    inputs = tx.get('inputs', [])
                    outputs = tx.get('outputs', [])
                    is_coinbase = len(inputs) == 1 and inputs[0].get('tx_id') == '0' * 64
                    
                    print(f"      TX {i+1}: {tx_id[:16]}...")
                    print(f"         Type: {'Coinbase' if is_coinbase else 'Regular'}")
                    print(f"         Inputs: {len(inputs)}")
                    print(f"         Outputs: {len(outputs)}")
                    
                    # Show coinbase details
                    if is_coinbase and outputs:
                        for j, output in enumerate(outputs):
                            recipient = output.get('recipient_address', 'unknown')
                            amount = output.get('amount', 0)
                            print(f"         Output {j+1}: {amount} CC → {recipient}")
                            
                            # Verify recipient matches miner
                            if recipient == miner_address:
                                print(f"            ✅ Coinbase output goes to miner address")
                            else:
                                print(f"            ❌ Coinbase output mismatch!")
                                print(f"               Expected: {miner_address}")
                                print(f"               Got: {recipient}")
                    
                    # Show input details for coinbase
                    if is_coinbase and inputs:
                        coinbase_input = inputs[0]
                        if (coinbase_input.get('tx_id') == '0' * 64 and 
                            coinbase_input.get('output_index') == 0xFFFFFFFF):
                            print(f"         ✅ Valid coinbase input structure")
                        else:
                            print(f"         ❌ Invalid coinbase input structure")
                
            else:
                print(f"   ❌ NO TRANSACTIONS in template!")
                print(f"   This is the problem! Templates should contain:")
                print(f"   1. One coinbase transaction rewarding the miner")
                print(f"   2. Any pending user transactions")
            
            # Test template structure
            print(f"\n4. TEMPLATE STRUCTURE VALIDATION:")
            required_fields = ['index', 'transactions', 'previous_hash', 'timestamp']
            
            for field in required_fields:
                if field in block_template:
                    value = block_template[field]
                    if field == 'transactions':
                        print(f"   ✅ {field}: {len(value) if isinstance(value, list) else 'not a list'}")
                    else:
                        print(f"   ✅ {field}: {str(value)[:50]}...")
                else:
                    print(f"   ❌ {field}: MISSING")
            
            # Save template for debugging
            print(f"\n5. SAVING TEMPLATE FOR ANALYSIS:")
            template_file = "debug_template.json"
            with open(template_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"   Template saved to: {template_file}")
            
        else:
            print(f"❌ Template creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error requesting template: {e}")
    
    print(f"\n" + "=" * 50)
    print("🏁 MINING TEMPLATE TEST COMPLETE")

if __name__ == "__main__":
    test_mining_template()