#!/usr/bin/env python3
"""
Enhanced Synchronization Test Script
Tests all new synchronization mechanisms in ChainCore
"""

import time
import requests
import json
import sys

def test_node_response(port):
    """Test if node is responding"""
    try:
        response = requests.get(f"http://localhost:{port}/status", timeout=3)
        return response.status_code == 200
    except:
        return False

def get_node_status(port):
    """Get enhanced node status including all sync mechanisms"""
    try:
        response = requests.get(f"http://localhost:{port}/status", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error getting status from port {port}: {e}")
    return None

def test_mempool_sync(ports):
    """Test mempool synchronization"""
    print("🔄 Testing Mempool Synchronization")
    print("-" * 50)
    
    # Trigger mempool sync on first node
    try:
        response = requests.post(f"http://localhost:{ports[0]}/sync_mempool", timeout=5)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Mempool sync triggered: {result['message']}")
        else:
            print(f"❌ Failed to trigger mempool sync: {response.text}")
    except Exception as e:
        print(f"❌ Mempool sync error: {e}")
    
    # Check mempool sync status on all nodes
    print("\nMempool Sync Status:")
    for port in ports:
        status = get_node_status(port)
        if status:
            mempool_sync = status.get('mempool_sync', {})
            print(f"  Port {port}: {'✅' if mempool_sync.get('enabled') else '❌'} "
                  f"(interval: {mempool_sync.get('interval')}s, "
                  f"syncs: {mempool_sync.get('syncs_completed', 0)})")

def test_network_stats_sync(ports):
    """Test network statistics synchronization"""
    print("\n📊 Testing Network Statistics Synchronization")
    print("-" * 50)
    
    # Trigger network stats sync
    try:
        response = requests.post(f"http://localhost:{ports[0]}/sync_network_stats", timeout=5)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Network stats sync triggered: {result['message']}")
        else:
            print(f"❌ Failed to trigger network stats sync: {response.text}")
    except Exception as e:
        print(f"❌ Network stats sync error: {e}")
    
    # Wait a moment for sync to complete
    time.sleep(2)
    
    # Check network-wide statistics
    print("\nNetwork-Wide Statistics:")
    for port in ports:
        try:
            response = requests.get(f"http://localhost:{port}/stats", timeout=5)
            if response.status_code == 200:
                stats = response.json()
                network_stats = stats.get('network_wide_stats', {})
                print(f"  Port {port}:")
                print(f"    Total Nodes: {network_stats.get('total_nodes', 0)}")
                print(f"    Max Chain Length: {network_stats.get('max_chain_length', 0)}")
                print(f"    Avg Peers/Node: {network_stats.get('avg_peers_per_node', 0):.1f}")
        except Exception as e:
            print(f"  Port {port}: Error getting stats - {e}")

def test_orphaned_blocks(ports):
    """Test orphaned block management"""
    print("\n🔗 Testing Orphaned Block Management")
    print("-" * 50)
    
    for port in ports:
        try:
            response = requests.get(f"http://localhost:{port}/orphaned_blocks", timeout=5)
            if response.status_code == 200:
                data = response.json()
                count = data.get('count', 0)
                print(f"  Port {port}: {count} orphaned blocks")
                if count > 0:
                    print("    Recent orphaned blocks:")
                    for i, block in enumerate(data.get('orphaned_blocks', [])[:3]):
                        print(f"      Block #{block['index']}: {block['hash'][:16]}...")
            else:
                print(f"  Port {port}: ❌ Failed to get orphaned blocks")
        except Exception as e:
            print(f"  Port {port}: Error - {e}")

def test_difficulty_adjustment(ports):
    """Test dynamic difficulty adjustment"""
    print("\n⚙️ Testing Dynamic Difficulty Adjustment")
    print("-" * 50)
    
    for port in ports:
        try:
            response = requests.get(f"http://localhost:{port}/network_config", timeout=5)
            if response.status_code == 200:
                config = response.json()
                print(f"  Port {port}:")
                print(f"    Current Difficulty: {config.get('current_difficulty', 'N/A')}")
                print(f"    Adjustment Enabled: {'✅' if config.get('difficulty_adjustment_enabled') else '❌'}")
                print(f"    Target Block Time: {config.get('target_block_time', 'N/A')}s")
                print(f"    Adjustment Interval: {config.get('difficulty_adjustment_interval', 'N/A')} blocks")
            else:
                print(f"  Port {port}: ❌ Failed to get network config")
        except Exception as e:
            print(f"  Port {port}: Error - {e}")

def test_sync_intervals(ports):
    """Test all synchronization intervals"""
    print("\n⏱️ Testing Synchronization Intervals")
    print("-" * 50)
    
    for port in ports:
        status = get_node_status(port)
        if status:
            print(f"  Port {port}:")
            
            # Blockchain sync
            blockchain_sync = status.get('blockchain_sync', {})
            print(f"    Blockchain: {'✅' if blockchain_sync.get('auto_sync_enabled') else '❌'} "
                  f"(every {blockchain_sync.get('sync_interval', 'N/A')}s)")
            
            # Mempool sync  
            mempool_sync = status.get('mempool_sync', {})
            print(f"    Mempool: {'✅' if mempool_sync.get('enabled') else '❌'} "
                  f"(every {mempool_sync.get('interval', 'N/A')}s)")
            
            # Network stats sync
            net_stats_sync = status.get('network_stats_sync', {})
            print(f"    Net Stats: {'✅' if net_stats_sync.get('enabled') else '❌'} "
                  f"(every {net_stats_sync.get('interval', 'N/A')}s)")
            
            # Peer discovery
            peer_discovery = status.get('peer_discovery', {})
            print(f"    Peer Discovery: {'✅' if peer_discovery.get('continuous_discovery_enabled') else '❌'} "
                  f"(every {peer_discovery.get('discovery_interval', 'N/A')}s)")
        else:
            print(f"  Port {port}: ❌ No response")

def main():
    """Main test runner"""
    print("🧪 Enhanced Synchronization Test Suite")
    print("=" * 60)
    
    # Test with common ports
    test_ports = [5000, 5001, 5002]
    
    # Check which nodes are online
    online_ports = []
    print("Checking node availability:")
    for port in test_ports:
        if test_node_response(port):
            online_ports.append(port)
            print(f"  ✅ Port {port}: Online")
        else:
            print(f"  ❌ Port {port}: Offline")
    
    if not online_ports:
        print("\n❌ No nodes are online. Please start some nodes first.")
        print("Example: python3 network_node.py --node-id=node1 --api-port=5000")
        return
    
    print(f"\nTesting with {len(online_ports)} online nodes: {online_ports}")
    print()
    
    # Run all tests
    test_sync_intervals(online_ports)
    test_mempool_sync(online_ports)
    test_network_stats_sync(online_ports)
    test_orphaned_blocks(online_ports)
    test_difficulty_adjustment(online_ports)
    
    print("\n" + "=" * 60)
    print("✅ Enhanced Synchronization Test Complete")
    print("\nNew Synchronization Features:")
    print("• Mempool synchronization (15s interval)")
    print("• Network-wide statistics aggregation (60s interval)")
    print("• Orphaned block management")
    print("• Dynamic difficulty adjustment")
    print("• Configuration synchronization")

if __name__ == "__main__":
    main()