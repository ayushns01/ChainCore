#!/usr/bin/env python3
"""
Test Competitive Mining Between Multiple Nodes
Demonstrates the original mining_client.py approach with multiple miners
"""

import sys
import os
import time
import json
import requests
import subprocess
from typing import List

def create_test_wallet(filename: str, name: str) -> str:
    """Create a test wallet and return the address"""
    # Import wallet functionality
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    from src.crypto.ecdsa_crypto import ECDSAKeyPair
    
    # Create wallet
    keypair = ECDSAKeyPair()
    wallet_data = {
        'keypair': keypair.to_dict(),
        'address': keypair.address,
        'type': 'ECDSA',
        'version': '1.0',
        'name': name
    }
    
    with open(filename, 'w') as f:
        json.dump(wallet_data, f, indent=2)
    
    print(f"✅ Created wallet for {name}: {keypair.address}")
    return keypair.address

def wait_for_node(port: int, timeout: int = 30) -> bool:
    """Wait for a node to become ready"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"http://localhost:{port}/status", timeout=2)
            if response.status_code == 200:
                return True
        except:
            time.sleep(1)
    return False

def get_node_status(port: int) -> dict:
    """Get node status"""
    try:
        response = requests.get(f"http://localhost:{port}/status", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {}

def start_network_node(node_id: str, port: int) -> subprocess.Popen:
    """Start a network node"""
    cmd = [
        sys.executable, "network_node.py",
        "--node-id", node_id,
        "--api-port", str(port),
        "--quiet"
    ]
    
    print(f"🚀 Starting network node {node_id} on port {port}")
    
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def start_mining_client(miner_address: str, node_url: str) -> subprocess.Popen:
    """Start a mining client"""
    cmd = [
        sys.executable, "mining_client.py",
        "--wallet", miner_address,
        "--node", node_url,
        "--quiet"
    ]
    
    print(f"⛏️  Starting mining client for {miner_address[:16]}...")
    print(f"   🌐 Connecting to: {node_url}")
    
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def main():
    print("=" * 60)
    print("🏁 ChainCore Dynamic Mining Network Test")
    print("=" * 60)
    
    # Ask user how many miners to create
    try:
        num_miners = int(input("🎯 How many mining nodes to create? (default 3): ") or 3)
        if num_miners < 1:
            num_miners = 3
        if num_miners > 20:
            print("⚠️  Limited to 20 nodes for testing")
            num_miners = 20
    except ValueError:
        num_miners = 3
    
    print(f"\n🏗️  Setting up {num_miners}-node competitive mining network...")
    
    # Create test wallets and start nodes and miners dynamically
    network_nodes = []
    mining_clients = []
    miner_addresses = []
    test_wallets = []
    
    for i in range(1, num_miners + 1):
        wallet_file = f"test_miner{i}.json"
        miner_address = create_test_wallet(wallet_file, f"Miner{i}")
        miner_addresses.append(miner_address)
        test_wallets.append(wallet_file)
        
        # Start network node
        port = 5000 + i
        node_url = f"http://localhost:{port}"
        network_node = start_network_node(f"core{i}", port)
        network_nodes.append(network_node)
        
        # Wait a moment for node to start before connecting miner
        time.sleep(1)
        
        # Start mining client
        mining_client = start_mining_client(miner_address, node_url)
        mining_clients.append(mining_client)
    
    # Combine all processes for cleanup
    all_processes = network_nodes + mining_clients
    
    # Wait for nodes to start
    print("\n⏳ Waiting for nodes to initialize...")
    ports = [5000 + i for i in range(1, num_miners + 1)]
    
    for i, port in enumerate(ports, 1):
        if wait_for_node(port):
            print(f"✅ Node {i} ready on port {port}")
        else:
            print(f"❌ Node {i} failed to start on port {port}")
            return
    
    print("\n🔗 Network topology established!")
    
    # Let nodes discover each other
    time.sleep(5)
    
    # Monitor mining competition
    print("\n⛏️  Starting competitive mining monitoring...")
    print("   (Watching for 60 seconds)")
    print("-" * 60)
    
    start_time = time.time()
    last_lengths = [0] * num_miners
    
    try:
        while time.time() - start_time < 60:
            print(f"\r⏰ Time: {int(time.time() - start_time):02d}s ", end="")
            
            # Check each node dynamically
            for i, port in enumerate(ports):
                status = get_node_status(port)
                if status:
                    chain_length = status.get('blockchain_length', 0)
                    pending_txs = status.get('pending_transactions', 0)
                    
                    # Check if this node received a new block
                    if chain_length > last_lengths[i]:
                        print(f"\n🎉 New block #{chain_length} received by Node {i+1}!")
                        last_lengths[i] = chain_length
                    
                    print(f"N{i+1}:[L{chain_length}|P{pending_txs}|⛏️] ", end="")
                else:
                    print(f"N{i+1}:[OFFLINE] ", end="")
            
            # Add newline every 10 seconds for readability with many nodes
            if num_miners > 5 and int(time.time() - start_time) % 10 == 0:
                print()
            
            time.sleep(2)
    
    except KeyboardInterrupt:
        print("\n\n🛑 Monitoring stopped by user")
    
    print("\n\n📊 Final Statistics:")
    print("-" * 50)
    
    active_nodes = 0
    max_chain_length = 0
    
    for i, port in enumerate(ports):
        status = get_node_status(port)
        if status:
            active_nodes += 1
            chain_length = status.get('blockchain_length', 0)
            pending_txs = status.get('pending_transactions', 0)
            max_chain_length = max(max_chain_length, chain_length)
            
            print(f"Node {i+1} (port {port}):")
            print(f"  📊 Chain Length: {chain_length}")
            print(f"  📋 Pending Transactions: {pending_txs}")
            print(f"  🔄 Status: {'Synced' if chain_length == max_chain_length else 'Syncing'}")
        else:
            print(f"Node {i+1} (port {port}): OFFLINE")
    
    print(f"\n🌐 Network Summary:")
    print(f"  📊 Total Nodes: {num_miners}")
    print(f"  ✅ Active Nodes: {active_nodes}")
    print(f"  🔗 Final Chain Length: {max_chain_length}")
    
    print(f"\n🏁 Mining Competition Results:")
    print(f"  ⏱️  Test Duration: {int(time.time() - start_time)} seconds")
    print(f"  💎 Total Blocks: {max_chain_length}")
    print(f"  ⛏️  Miners Active: {num_miners} mining_client.py processes")
    
    # Stop all processes
    print("\n🛑 Stopping all processes...")
    for i, process in enumerate(all_processes, 1):
        try:
            process.terminate()
            process.wait(timeout=10)
            print(f"✅ Process {i} stopped")
        except:
            process.kill()
            print(f"⚠️  Process {i} force killed")
    
    # Clean up test wallets
    for wallet in test_wallets:
        try:
            os.remove(wallet)
        except:
            pass
    
    print(f"\n✅ {num_miners}-miner competitive test completed!")
    print("   📝 Used original mining_client.py approach")
    print("=" * 60)

if __name__ == "__main__":
    main()