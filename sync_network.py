#!/usr/bin/env python3
"""
Network Synchronization Helper
Manually trigger synchronization between all active nodes
"""

import requests
import json
import time
from typing import List, Dict

def get_node_status(port: int) -> Dict:
    """Get status of a node"""
    try:
        response = requests.get(f"http://localhost:{port}/status", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def trigger_node_sync(port: int) -> bool:
    """Trigger manual sync on a node"""
    try:
        response = requests.post(f"http://localhost:{port}/sync_now", timeout=30)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Node {port}: {result['status']}")
            if 'new_length' in result:
                print(f"   📊 Chain length: {result.get('old_length', 0)} → {result['new_length']}")
            return True
        else:
            print(f"❌ Node {port}: Sync failed - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Node {port}: Sync error - {e}")
        return False

def discover_active_nodes() -> List[int]:
    """Discover all active nodes"""
    print("🔍 Discovering active nodes...")
    active_nodes = []
    
    for port in range(5000, 5010):
        status = get_node_status(port)
        if status:
            chain_length = status.get('blockchain_length', 0)
            node_id = status.get('node_id', f'node-{port}')
            active_nodes.append(port)
            print(f"   📡 Node {port} ({node_id}): {chain_length} blocks")
    
    return active_nodes

def sync_all_nodes():
    """Synchronize all active nodes"""
    print("🚀 ChainCore Network Synchronization")
    print("=" * 50)
    
    # Discover active nodes
    active_nodes = discover_active_nodes()
    
    if len(active_nodes) < 2:
        print("⚠️  Need at least 2 nodes for synchronization")
        return
    
    print(f"\n🌐 Found {len(active_nodes)} active nodes")
    print("🔄 Starting synchronization process...")
    print()
    
    # Get initial status
    print("📊 Pre-sync status:")
    node_statuses = {}
    for port in active_nodes:
        status = get_node_status(port)
        if status:
            node_statuses[port] = status
            print(f"   Node {port}: {status.get('blockchain_length', 0)} blocks")
    
    print("\n🔄 Triggering sync on all nodes...")
    
    # Trigger sync on all nodes (multiple rounds)
    for round_num in range(3):  # Multiple sync rounds
        print(f"\n📡 Sync Round {round_num + 1}:")
        for port in active_nodes:
            trigger_node_sync(port)
        
        # Wait between rounds
        if round_num < 2:
            print("⏳ Waiting 5 seconds before next round...")
            time.sleep(5)
    
    # Check final status
    print("\n📊 Post-sync status:")
    chain_lengths = []
    for port in active_nodes:
        status = get_node_status(port)
        if status:
            length = status.get('blockchain_length', 0)
            chain_lengths.append(length)
            print(f"   Node {port}: {length} blocks")
    
    # Check consensus
    print("\n🎯 Consensus Analysis:")
    if len(set(chain_lengths)) == 1:
        print("✅ Perfect consensus achieved!")
        print(f"   All nodes have {chain_lengths[0]} blocks")
    else:
        print("⚠️  Consensus issues remain:")
        for length in sorted(set(chain_lengths), reverse=True):
            count = chain_lengths.count(length)
            print(f"   {length} blocks: {count} node(s)")
        print("\n💡 Try running this script again or check network connectivity")

if __name__ == "__main__":
    sync_all_nodes()