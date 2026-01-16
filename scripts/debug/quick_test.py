#!/usr/bin/env python3
"""
Quick test to see why blocks have no transactions
"""
import sys
sys.path.append('src')

import time
import requests

def quick_mining_test():
    """Test mining directly without full setup"""
    print("🚀 QUICK MINING TEST")
    print("=" * 30)
    
    # Try to get status and template from any existing node
    node_url = "http://localhost:5000"
    miner_address = "18NDhHYAa3bx3jAZkc7HZf3vKr1JrwVXG3"
    
    print("1. Checking for running node...")
    try:
        status = requests.get(f"{node_url}/status", timeout=3).json()
        print(f"✅ Found running node: {status.get('node_id', 'unknown')}")
        print(f"   Chain length: {status.get('chain_length', 0)}")
    except:
        print("❌ No node running. To test this issue:")
        print("   1. Start node: python src/nodes/network_node.py --node-id test --api-port 5000")
        print("   2. Start mining: python src/clients/mining_client.py --wallet 18NDhHYAa3bx3jAZkc7HZf3vKr1JrwVXG3 --node http://localhost:5000")
        print("   3. Watch the enhanced logs to see transaction details")
        return
    
    print("\n2. Requesting mining template...")
    try:
        template_response = requests.post(
            f"{node_url}/mine_block",
            json={"miner_address": miner_address},
            timeout=10
        )
        
        if template_response.status_code == 200:
            data = template_response.json()
            template = data.get('block_template', {})
            transactions = template.get('transactions', [])
            
            print(f"✅ Template created successfully!")
            print(f"   Block index: {template.get('index', 'unknown')}")
            print(f"   Transactions: {len(transactions)}")
            
            if transactions:
                print(f"   Transaction details:")
                for i, tx in enumerate(transactions):
                    print(f"      TX {i+1}: {tx.get('tx_id', 'unknown')[:16]}...")
                    print(f"         Type: {'Coinbase' if tx.get('is_coinbase') else 'Regular'}")
                    
                    outputs = tx.get('outputs', [])
                    for j, output in enumerate(outputs):
                        amount = output.get('amount', 0)
                        recipient = output.get('recipient_address', 'unknown')
                        print(f"         Output {j+1}: {amount} CC → {recipient[:16]}...{recipient[-8:]}")
                        
                        if recipient == miner_address:
                            print(f"            ✅ This is the coinbase reward for our miner!")
                
                print(f"\n✅ TEMPLATE LOOKS GOOD! The issue must be elsewhere.")
                print(f"   The template contains proper coinbase transactions.")
                print(f"   The problem is likely in:")
                print(f"   1. Mining client not preserving transactions")
                print(f"   2. Block submission losing transactions") 
                print(f"   3. Block storage not saving transactions")
                
            else:
                print(f"❌ PROBLEM FOUND: Template has NO transactions!")
                print(f"   This means create_block_template() is not working.")
                print(f"   Expected: At least 1 coinbase transaction")
                print(f"   Got: 0 transactions")
        else:
            print(f"❌ Template request failed: {template_response.status_code}")
            print(f"   Response: {template_response.text}")
            
    except Exception as e:
        print(f"❌ Template test failed: {e}")
    
    print(f"\n3. With enhanced logging, you should now see:")
    print(f"   - Detailed transaction info when blocks are stored")
    print(f"   - Clear identification of where transactions are lost")
    print(f"   - Specific error messages if transaction storage fails")
    
    print(f"\n" + "=" * 30)
    print("🏁 QUICK TEST COMPLETE")

if __name__ == "__main__":
    quick_mining_test()