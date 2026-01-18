#!/usr/bin/env python3
"""
Test script to verify mining statistics updates in nodes table
"""
import sys
sys.path.append('src')

import time
import requests
from data.simple_connection import get_simple_db_manager

def test_mining_stats_flow():
    """Test the complete mining statistics flow"""
    print("🧪 TESTING MINING STATISTICS FLOW")
    print("=" * 50)
    
    db = get_simple_db_manager()
    
    # Check if any nodes are currently registered
    print("\n1. CHECKING CURRENT NODES IN DATABASE:")
    nodes = db.execute_query("SELECT * FROM nodes ORDER BY created_at DESC", fetch_all=True)
    
    if nodes:
        print(f"Found {len(nodes)} registered nodes:")
        for node in nodes:
            print(f"  - {node['node_id']}: status={node['status']}, blocks_mined={node['blocks_mined']}, total_rewards={node['total_rewards']}")
    else:
        print("  No nodes currently registered")
    
    # Check if any node is running on port 5000
    print("\n2. CHECKING NODE CONNECTIVITY:")
    try:
        response = requests.get("http://localhost:5000/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Node at port 5000 is running:")
            print(f"   Node ID: {status.get('node_id', 'unknown')}")
            print(f"   Chain Length: {status.get('chain_length', 'unknown')}")
            print(f"   Active Peers: {status.get('active_peers', 'unknown')}")
            
            node_id = status.get('node_id', 'unknown')
            
            # Check current database state for this node
            print(f"\n3. CURRENT DATABASE STATE FOR {node_id}:")
            node_data = db.execute_query(
                "SELECT * FROM nodes WHERE node_id = %s", 
                (node_id,), 
                fetch_one=True
            )
            
            if node_data:
                print(f"   Status: {node_data['status']}")
                print(f"   Blocks Mined: {node_data['blocks_mined']}")
                print(f"   Total Rewards: {node_data['total_rewards']}")
                print(f"   Last Seen: {node_data['last_seen']}")
            else:
                print(f"   ❌ Node {node_id} not found in database!")
                return
            
            # Test mining template creation (should set status to 'mining')
            print(f"\n4. TESTING MINING TEMPLATE CREATION:")
            mine_response = requests.post(
                "http://localhost:5000/mine_block",
                json={"miner_address": "1TestMinerForStatsVerification123456789"},
                timeout=10
            )
            
            if mine_response.status_code == 200:
                print("✅ Mining template created successfully")
                
                # Check if status changed to 'mining'
                time.sleep(1)  # Small delay for database update
                updated_node = db.execute_query(
                    "SELECT status FROM nodes WHERE node_id = %s", 
                    (node_id,), 
                    fetch_one=True
                )
                
                if updated_node:
                    print(f"   Node status after template creation: {updated_node['status']}")
                    if updated_node['status'] == 'mining':
                        print("   ✅ Status correctly updated to 'mining'")
                    else:
                        print(f"   ⚠️ Expected 'mining', got '{updated_node['status']}'")
            else:
                print(f"❌ Mining template creation failed: {mine_response.status_code}")
                print(f"   Response: {mine_response.text}")
                
            print(f"\n5. TESTING MANUAL BLOCK MINING:")
            print("   Note: Complete mining test requires external mining client")
            print("   To test full flow, run:")
            print(f"   python src/clients/mining_client.py --wallet 1TestMinerForStatsVerification123456789 --node http://localhost:5000")
            
            # Instructions for complete testing
            print(f"\n6. COMPLETE TEST INSTRUCTIONS:")
            print("   1. Start a network node:")
            print("      python src/nodes/network_node.py --node-id test_node --api-port 5000")
            print("   2. Run this test script to verify initial state")
            print("   3. Start mining:")
            print("      python src/clients/mining_client.py --wallet 1TestMinerForStatsVerification123456789 --node http://localhost:5000")
            print("   4. Wait for a block to be mined")
            print("   5. Run this test script again to verify stats update")
            
        else:
            print(f"❌ Node at port 5000 returned status code: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ No node running at port 5000")
        print("\nTo start a test node, run:")
        print("D:/ChainCore/chaincore/Scripts/python.exe src/nodes/network_node.py --node-id test_stats --api-port 5000")
    except Exception as e:
        print(f"❌ Error checking node: {e}")
    
    print(f"\n7. DATABASE MONITORING:")
    print("   To monitor mining stats in real-time:")
    print("   python src/monitoring/database_monitor.py")
    
    print("\n" + "=" * 50)
    print("🏁 MINING STATISTICS TEST COMPLETE")

if __name__ == "__main__":
    test_mining_stats_flow()