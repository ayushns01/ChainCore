#!/usr/bin/env python3
"""
Test Enhanced P2P Networking System
Tests the full-mesh connectivity, peer gossiping, and consensus mechanisms
"""

import requests
import time
import json
from typing import Dict, List

def test_peer_exchange_api(base_urls: List[str]):
    """Test the new peer exchange APIs"""
    print("=== Testing Peer Exchange APIs ===")
    
    for i, base_url in enumerate(base_urls):
        print(f"\nTesting node {i+1}: {base_url}")
        
        try:
            # Test getpeers endpoint
            response = requests.get(f"{base_url}/getpeers", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"  [OK] /getpeers - {data['count']} peers available for sharing")
            else:
                print(f"  [FAIL] /getpeers - Status: {response.status_code}")
            
            # Test sharepeers endpoint
            test_peers = [
                {
                    'url': 'http://localhost:9999',
                    'node_id': 'test_node',
                    'last_seen': time.time(),
                    'chain_length': 5
                }
            ]
            
            share_data = {
                'node_id': f'test_client_{i}',
                'peers': test_peers,
                'timestamp': time.time()
            }
            
            response = requests.post(f"{base_url}/sharepeers", json=share_data, timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"  [OK] /sharepeers - Processed {data.get('peers_received', 0)} peers")
            else:
                print(f"  [FAIL] /sharepeers - Status: {response.status_code}")
            
            # Test addpeer endpoint
            add_data = {'peer_url': 'http://localhost:9998'}
            response = requests.post(f"{base_url}/addpeer", json=add_data, timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"  [OK] /addpeer - {data['status']}")
            else:
                print(f"  [FAIL] /addpeer - Status: {response.status_code}")
                
        except Exception as e:
            print(f"  [ERROR] {base_url}: {e}")

def test_broadcast_functionality(base_urls: List[str]):
    """Test message broadcasting between nodes"""
    print("\n=== Testing Broadcast Functionality ===")
    
    if len(base_urls) < 2:
        print("Need at least 2 nodes for broadcast testing")
        return
    
    broadcaster = base_urls[0]
    print(f"\nBroadcasting from: {broadcaster}")
    
    test_message = {
        'endpoint': 'receive_broadcast',
        'message': {
            'test_id': 'broadcast_test_123',
            'content': 'Hello ChainCore Network!',
            'timestamp': time.time()
        },
        'timeout': 10
    }
    
    try:
        response = requests.post(f"{broadcaster}/broadcast", json=test_message, timeout=15)
        if response.status_code == 200:
            data = response.json()
            successful = data.get('successful', 0)
            total = data.get('total_peers', 0)
            print(f"  [OK] Broadcast successful: {successful}/{total} peers reached")
            
            # Show detailed results
            for peer_url, success in data.get('results', {}).items():
                status = "✓" if success else "✗"
                print(f"    {status} {peer_url}")
        else:
            print(f"  [FAIL] Broadcast failed - Status: {response.status_code}")
    
    except Exception as e:
        print(f"  [ERROR] Broadcast test failed: {e}")

def test_peer_discovery_and_connectivity(base_urls: List[str]):
    """Test peer discovery and network connectivity"""
    print("\n=== Testing Peer Discovery & Connectivity ===")
    
    for i, base_url in enumerate(base_urls):
        print(f"\nNode {i+1}: {base_url}")
        
        try:
            # Get peer status
            response = requests.get(f"{base_url}/peers", timeout=5)
            if response.status_code == 200:
                data = response.json()
                active_peers = data.get('active_peers', [])
                peer_count = data.get('peer_count', 0)
                
                print(f"  Active peers: {peer_count}")
                for peer_url in active_peers[:5]:  # Show first 5
                    peer_details = data.get('peer_details', {}).get(peer_url, {})
                    chain_length = peer_details.get('chain_length', '?')
                    response_time = peer_details.get('response_time', '?')
                    print(f"    - {peer_url} (chain: {chain_length}, ping: {response_time:.2f}s)")
                
                if len(active_peers) > 5:
                    print(f"    ... and {len(active_peers) - 5} more peers")
                
            else:
                print(f"  [FAIL] Could not get peer info - Status: {response.status_code}")
                
        except Exception as e:
            print(f"  [ERROR] {base_url}: {e}")

def test_consensus_status(base_urls: List[str]):
    """Test blockchain consensus across nodes"""
    print("\n=== Testing Blockchain Consensus ===")
    
    chain_lengths = {}
    
    for i, base_url in enumerate(base_urls):
        try:
            response = requests.get(f"{base_url}/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                chain_length = data.get('blockchain_length', 0)
                node_id = data.get('node_id', f'node_{i}')
                chain_lengths[node_id] = chain_length
                print(f"  {node_id}: {chain_length} blocks")
            else:
                print(f"  Node {i+1}: Failed to get status")
                
        except Exception as e:
            print(f"  Node {i+1}: Error - {e}")
    
    # Analyze consensus
    if chain_lengths:
        unique_lengths = set(chain_lengths.values())
        if len(unique_lengths) == 1:
            print(f"\n  ✓ Perfect consensus: All nodes have {list(unique_lengths)[0]} blocks")
        else:
            print(f"\n  ⚠ Consensus issues detected:")
            for length in sorted(unique_lengths):
                nodes_with_length = [node for node, l in chain_lengths.items() if l == length]
                print(f"    {length} blocks: {', '.join(nodes_with_length)}")

def test_enhanced_peer_manager_status(base_urls: List[str]):
    """Test enhanced peer manager status if available"""
    print("\n=== Testing Enhanced Peer Manager Status ===")
    
    for i, base_url in enumerate(base_urls):
        print(f"\nNode {i+1}: {base_url}")
        
        try:
            # Try to get enhanced peer manager status
            # This would be available if nodes are using the enhanced system
            response = requests.get(f"{base_url}/peer_manager_status", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print(f"  Enhanced peer manager active:")
                print(f"    Total peers: {data.get('total_peers', 0)}")
                print(f"    Active peers: {data.get('active_peers', 0)}")
                print(f"    Outbound connections: {data.get('outbound_connections', 0)}")
                print(f"    Target connections: {data.get('target_connections', 0)}")
            else:
                # Fall back to basic status
                response = requests.get(f"{base_url}/status", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    peers = data.get('peers', 0)
                    network_status = data.get('network', {}).get('status_message', 'Unknown')
                    print(f"  Basic peer manager:")
                    print(f"    Connected peers: {peers}")
                    print(f"    Network status: {network_status}")
                    
        except Exception as e:
            print(f"  [ERROR] {base_url}: {e}")

def main():
    """Run comprehensive P2P networking tests"""
    # Test with common ChainCore node ports
    test_nodes = [
        "http://localhost:5000",
        "http://localhost:5001", 
        "http://localhost:5002",
        "http://localhost:5003"
    ]
    
    print("ChainCore Enhanced P2P Networking Test Suite")
    print("=" * 50)
    
    # Filter to only active nodes
    active_nodes = []
    print("Discovering active nodes...")
    
    for node_url in test_nodes:
        try:
            response = requests.get(f"{node_url}/status", timeout=3)
            if response.status_code == 200:
                data = response.json()
                node_id = data.get('node_id', 'unknown')
                print(f"  ✓ {node_url} (Node: {node_id})")
                active_nodes.append(node_url)
            else:
                print(f"  ✗ {node_url} - Status: {response.status_code}")
        except:
            print(f"  ✗ {node_url} - Not reachable")
    
    if not active_nodes:
        print("\n❌ No active ChainCore nodes found!")
        print("Please start some nodes first:")
        print("  python network_node.py --node-id core0 --api-port 5000")
        print("  python network_node.py --node-id core1 --api-port 5001")
        return
    
    print(f"\nFound {len(active_nodes)} active nodes")
    
    # Run tests
    test_consensus_status(active_nodes)
    test_peer_discovery_and_connectivity(active_nodes)
    test_peer_exchange_api(active_nodes)
    test_broadcast_functionality(active_nodes)
    test_enhanced_peer_manager_status(active_nodes)
    
    print("\n" + "=" * 50)
    print("P2P Networking Test Complete")
    
    # Summary
    print(f"\nNetwork Summary:")
    print(f"  Active nodes: {len(active_nodes)}")
    print(f"  Nodes tested: {', '.join([url.split('//')[1] for url in active_nodes])}")

if __name__ == "__main__":
    main()