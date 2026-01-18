#!/usr/bin/env python3
"""
Test script to validate automatic blockchain synchronization
"""

import time
import requests
import sys
import json

def check_node_status(port):
    """Get detailed node status including blockchain sync info"""
    try:
        response = requests.get(f"http://localhost:{port}/status", timeout=3)
        if response.status_code == 200:
            data = response.json()
            return {
                'port': port,
                'node_id': data.get('node_id'),
                'blockchain_length': data.get('blockchain_length', 0),
                'peers': data.get('peers', 0),
                'sync_info': data.get('blockchain_sync', {}),
                'online': True
            }
    except:
        pass
    return {'port': port, 'online': False}

def trigger_manual_sync(port):
    """Trigger manual sync on a node"""
    try:
        response = requests.post(f"http://localhost:{port}/sync_now", timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        return {'error': str(e)}
    return None

def monitor_sync_behavior(ports, duration=180):
    """Monitor automatic blockchain synchronization across nodes"""
    print(f"🔄 Monitoring Blockchain Synchronization")
    print("=" * 70)
    print(f"Monitoring {len(ports)} nodes for {duration} seconds...")
    print("Checking for automatic sync behavior every 10 seconds")
    print()
    
    start_time = time.time()
    
    while time.time() - start_time < duration:
        current_time = time.time() - start_time
        print(f"Time: {current_time:.0f}s")
        print("-" * 50)
        
        nodes = []
        blockchain_lengths = []
        
        for port in ports:
            status = check_node_status(port)
            nodes.append(status)
            
            if status['online']:
                blockchain_lengths.append(status['blockchain_length'])
                sync_info = status['sync_info']
                
                print(f"Node {status['node_id']} (port {port}):")
                print(f"  Blockchain Length: {status['blockchain_length']}")
                print(f"  Active Peers: {status['peers']}")
                print(f"  Auto Sync: {'✅' if sync_info.get('auto_sync_enabled') else '❌'}")
                print(f"  Sync Interval: {sync_info.get('sync_interval', 'N/A')}s")
                print(f"  Successful Syncs: {sync_info.get('successful_syncs', 0)}")
                print(f"  Failed Syncs: {sync_info.get('failed_syncs', 0)}")
                
                last_sync = sync_info.get('last_sync_time', 0)
                if last_sync > 0:
                    sync_ago = time.time() - last_sync
                    print(f"  Last Sync: {sync_ago:.0f}s ago")
                else:
                    print(f"  Last Sync: Never")
            else:
                print(f"Node on port {port}: ❌ Offline")
        
        # Analyze sync status
        if blockchain_lengths:
            min_length = min(blockchain_lengths)
            max_length = max(blockchain_lengths)
            
            print(f"\\nNetwork Status:")
            print(f"  Chain lengths: {min_length} - {max_length}")
            
            if min_length == max_length:
                print(f"  🟢 All nodes synchronized (length: {min_length})")
            else:
                print(f"  🟡 Sync in progress (gap: {max_length - min_length} blocks)")
                
                # Show which nodes are behind
                for node in nodes:
                    if node['online'] and node['blockchain_length'] < max_length:
                        behind = max_length - node['blockchain_length']
                        print(f"    ⚠️  {node['node_id']} is {behind} blocks behind")
        
        print()
        time.sleep(10)

def test_sync_scenarios():
    """Test different blockchain sync scenarios"""
    print("🧪 Blockchain Sync Test Scenarios")
    print("=" * 50)
    
    # Test 1: Check if nodes are running
    print("Test 1: Node Discovery")
    test_ports = [5000, 5001, 5002, 5003]
    online_nodes = []
    
    for port in test_ports:
        status = check_node_status(port)
        if status['online']:
            online_nodes.append(status)
            print(f"  ✅ Node {status['node_id']} online (length: {status['blockchain_length']})")
        else:
            print(f"  ❌ Node on port {port} offline")
    
    if len(online_nodes) < 2:
        print("\\n❌ Need at least 2 nodes running for sync testing")
        return
    
    print(f"\\n✅ Found {len(online_nodes)} online nodes")
    
    # Test 2: Check sync configuration
    print("\\nTest 2: Auto-Sync Configuration")
    for node in online_nodes:
        sync_info = node['sync_info']
        enabled = sync_info.get('auto_sync_enabled', False)
        interval = sync_info.get('sync_interval', 0)
        print(f"  {node['node_id']}: Auto-sync {'✅' if enabled else '❌'} (interval: {interval}s)")
    
    # Test 3: Trigger manual sync on shortest chain
    print("\\nTest 3: Manual Sync Test")
    lengths = [(node['blockchain_length'], node['port'], node['node_id']) for node in online_nodes]
    lengths.sort()
    
    if lengths[0][0] < lengths[-1][0]:
        shortest_port = lengths[0][1]
        shortest_node = lengths[0][2]
        print(f"  Triggering manual sync on {shortest_node} (port {shortest_port})")
        
        result = trigger_manual_sync(shortest_port)
        if result:
            print(f"  Result: {result}")
        else:
            print(f"  ❌ Manual sync failed")
    else:
        print("  ✅ All nodes already synchronized")

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 test_blockchain_sync.py monitor   - Monitor automatic sync")
        print("  python3 test_blockchain_sync.py test      - Run sync tests")
        print("  python3 test_blockchain_sync.py status    - Check current sync status")
        return
    
    command = sys.argv[1]
    
    if command == "monitor":
        ports = [5000, 5001, 5002, 5003, 5004]
        try:
            monitor_sync_behavior(ports, duration=180)
        except KeyboardInterrupt:
            print("\\n🛑 Monitoring stopped")
    
    elif command == "test":
        test_sync_scenarios()
    
    elif command == "status":
        print("🔍 Current Blockchain Sync Status")
        print("=" * 40)
        
        ports = [5000, 5001, 5002, 5003, 5004]
        for port in ports:
            status = check_node_status(port)
            if status['online']:
                print(f"Node {status['node_id']} (port {port}):")
                print(f"  Length: {status['blockchain_length']}, Peers: {status['peers']}")
                sync_info = status['sync_info']
                print(f"  Auto-sync: {'✅' if sync_info.get('auto_sync_enabled') else '❌'}")
                print(f"  Success/Fail: {sync_info.get('successful_syncs', 0)}/{sync_info.get('failed_syncs', 0)}")
            else:
                print(f"Node on port {port}: ❌ Offline")
        
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()