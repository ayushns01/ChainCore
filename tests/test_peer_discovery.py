#!/usr/bin/env python3
"""
Test script to demonstrate continuous peer discovery
"""

import time
import subprocess
import requests
import sys
import signal
from concurrent.futures import ThreadPoolExecutor

def check_node_status(port):
    """Check if a node is running and get its peer count"""
    try:
        response = requests.get(f"http://localhost:{port}/status", timeout=2)
        if response.status_code == 200:
            data = response.json()
            peer_data = data.get('peer_discovery', {})
            peer_limits = peer_data.get('peer_limits', {})
            
            return {
                'port': port,
                'node_id': data.get('node_id'),
                'peers': data.get('peers', 0),
                'active_peers': peer_data.get('active_peers', 0),
                'total_peers': peer_data.get('total_peers', 0),
                'network_status': peer_data.get('network_status', 'unknown'),
                'continuous_discovery': peer_data.get('continuous_discovery_enabled', False),
                'discovery_interval': peer_data.get('discovery_interval', 0),
                'min_peers': peer_limits.get('min_peers', 0),
                'target_peers': peer_limits.get('target_peers', 0),
                'max_peers': peer_limits.get('max_peers', 0),
                'blockchain_length': data.get('blockchain_length', 0),
                'auto_sync': data.get('blockchain_sync', {}).get('auto_sync_enabled', False),
                'sync_interval': data.get('blockchain_sync', {}).get('sync_interval', 0),
                'successful_syncs': data.get('blockchain_sync', {}).get('successful_syncs', 0)
            }
    except:
        return None

def monitor_nodes(ports, duration=60):
    """Monitor multiple nodes and show peer discovery behavior"""
    print(f"🔍 Monitoring nodes for {duration} seconds...")
    print("=" * 80)
    
    start_time = time.time()
    
    while time.time() - start_time < duration:
        print(f"\nTime: {time.time() - start_time:.0f}s")
        print("-" * 40)
        
        for port in ports:
            status = check_node_status(port)
            if status:
                print(f"Node {status['node_id']} (port {port}):")
                print(f"  Blockchain Length: {status['blockchain_length']}")
                print(f"  Network Status: {status['network_status']}")
                print(f"  Active Peers: {status['active_peers']}/{status['total_peers']} known")
                print(f"  Peer Limits: {status['min_peers']} min, {status['target_peers']} target, {status['max_peers']} max")
                print(f"  Discovery: {'Enabled' if status['continuous_discovery'] else 'Disabled'} ({status['discovery_interval']}s interval)")
                print(f"  Auto-Sync: {'Enabled' if status['auto_sync'] else 'Disabled'} ({status['sync_interval']}s interval)")
                print(f"  Successful Syncs: {status['successful_syncs']}")
            else:
                print(f"Node on port {port}: Not running")
        
        time.sleep(10)  # Check every 10 seconds

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 test_peer_discovery.py demo     - Run demo with simulated nodes")
        print("  python3 test_peer_discovery.py monitor  - Monitor running nodes")
        return
    
    command = sys.argv[1]
    
    if command == "demo":
        print("🚀 Enhanced Peer Discovery Demo")
        print("=" * 50)
        print("New Features:")
        print("✅ Continuous peer discovery (every 60s)")
        print("✅ Optimized peer limits for 20-node network (2 min, 6 target, 10 max)")
        print("✅ Network status monitoring")
        print("✅ Discovery even when peers exist")
        print("✅ Extended port range (5000-5019) for 20 nodes")
        print("✅ Automatic blockchain synchronization (every 30s)")
        print("")
        print("Demo scenarios:")
        print("1. Start first node → 'isolated' status → discovers peers every 60s")
        print("2. Start second node → both discover each other → 'under-connected'")
        print("3. Start more nodes → status becomes 'establishing' → 'well-connected'")
        print("4. Nodes continue discovering new peers up to max limit")
        print("")
        print("💡 To run real demo:")
        print("   Terminal 1: python3 network_node.py --node-id core0 --api-port 5000")
        print("   Terminal 2: python3 network_node.py --node-id core1 --api-port 5001") 
        print("   Terminal 3: python3 network_node.py --node-id core2 --api-port 5002")
        print("   Terminal 4: python3 test_peer_discovery.py monitor")
        print("")
        print("🔍 Expected peer discovery behavior:")
        print("   - Nodes discover ALL available peers in network")
        print("   - Discovery continues even when peers exist")
        print("   - Network resilience through continuous monitoring")
        
    elif command == "monitor":
        try:
            # Monitor ports for 20-node prototype
            ports = [5000, 5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009, 
                    5010, 5011, 5012, 5013, 5014, 5015, 5016, 5017, 5018, 5019]
            monitor_nodes(ports, duration=120)
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped")
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()