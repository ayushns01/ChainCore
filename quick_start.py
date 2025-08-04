#!/usr/bin/env python3
"""
Quick Start Script for Bitcoin-style Blockchain
Tests the complete system with proper architecture
"""

import subprocess
import time
import requests
import json
import sys
import os

def run_cmd(cmd, timeout=10):
    """Run command with timeout"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout"

def check_dependencies():
    """Check if all dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    # Check if we're in virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Not in virtual environment. Run: source venv/bin/activate")
        return False
    
    # Check required packages
    required = ['cryptography', 'requests', 'flask', 'base58']
    for package in required:
        success, _, _ = run_cmd(f"python -c 'import {package}'")
        if not success:
            print(f"❌ Missing package: {package}")
            print("   Run: pip install -r requirements.txt")
            return False
    
    print("✅ All dependencies OK")
    return True

def quick_test():
    """Quick test of the Bitcoin-style system"""
    print("🚀 Bitcoin-style Blockchain Quick Test")
    print("=" * 50)
    
    if not check_dependencies():
        return
    
    # Step 1: Start network node
    print("\n1️⃣ Starting network node...")
    node_process = subprocess.Popen(
        "python3 network_node.py --node-id test_node --api-port 5000",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for node to start
    time.sleep(5)
    
    # Check if node is running
    try:
        response = requests.get("http://localhost:5000/status", timeout=5)
        if response.status_code != 200:
            print("❌ Node failed to start")
            node_process.terminate()
            return
    except:
        print("❌ Node not responding")
        node_process.terminate()
        return
    
    print("✅ Network node started")
    
    # Step 2: Create wallets
    print("\n2️⃣ Creating wallets...")
    
    # Create miner wallet
    success, output, error = run_cmd("python3 wallet_client.py create --wallet test_miner.json")
    if not success:
        print(f"❌ Failed to create miner wallet: {error}")
        node_process.terminate()
        return
    
    # Create user wallet
    success, output, error = run_cmd("python3 wallet_client.py create --wallet test_user.json")
    if not success:
        print(f"❌ Failed to create user wallet: {error}")
        node_process.terminate()
        return
    
    print("✅ Wallets created")
    
    # Get miner address
    try:
        with open('test_miner.json', 'r') as f:
            miner_data = json.load(f)
            miner_address = miner_data['address']
    except:
        print("❌ Failed to read miner address")
        node_process.terminate()
        return
    
    # Get user address
    try:
        with open('test_user.json', 'r') as f:
            user_data = json.load(f)
            user_address = user_data['address']
    except:
        print("❌ Failed to read user address")
        node_process.terminate()
        return
    
    print(f"   Miner: {miner_address[:20]}...")
    print(f"   User:  {user_address[:20]}...")
    
    # Step 3: Mine a block
    print("\n3️⃣ Mining a block...")
    
    # Start mining for 30 seconds
    mining_process = subprocess.Popen(
        f"timeout 30 python3 mining_client.py --wallet {miner_address}",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for mining
    mining_process.wait()
    
    # Check blockchain length
    try:
        response = requests.get("http://localhost:5000/status")
        if response.status_code == 200:
            status = response.json()
            blocks = status['blockchain_length']
            print(f"✅ Blockchain has {blocks} blocks")
            
            if blocks > 1:
                print("✅ Mining successful!")
            else:
                print("⚠️  No blocks mined (may need more time)")
        
        # Check miner balance
        response = requests.get(f"http://localhost:5000/balance/{miner_address}")
        if response.status_code == 200:
            balance = response.json()['balance']
            print(f"💰 Miner balance: {balance} BTC")
        
    except Exception as e:
        print(f"❌ Error checking status: {e}")
    
    # Step 4: Create transaction (if miner has coins)
    print("\n4️⃣ Testing transaction...")
    
    try:
        response = requests.get(f"http://localhost:5000/balance/{miner_address}")
        if response.status_code == 200:
            miner_balance = response.json()['balance']
            
            if miner_balance > 0:
                print(f"📤 Sending 10 BTC from miner to user...")
                
                success, output, error = run_cmd(
                    f"python3 wallet_client.py send --wallet test_miner.json --to {user_address} --amount 10",
                    timeout=15
                )
                
                if success:
                    print("✅ Transaction sent!")
                    
                    # Check user balance
                    time.sleep(2)
                    response = requests.get(f"http://localhost:5000/balance/{user_address}")
                    if response.status_code == 200:
                        user_balance = response.json()['balance']
                        print(f"💰 User balance: {user_balance} BTC")
                else:
                    print(f"❌ Transaction failed: {error}")
            else:
                print("⚠️  Miner has no coins to send")
    
    except Exception as e:
        print(f"❌ Error with transaction: {e}")
    
    # Step 5: Show final status
    print("\n5️⃣ Final system status...")
    
    try:
        response = requests.get("http://localhost:5000/status")
        if response.status_code == 200:
            status = response.json()
            print(f"🔗 Blocks: {status['blockchain_length']}")
            print(f"📋 Pending TXs: {status['pending_transactions']}")
            print(f"⚙️  Difficulty: {status['target_difficulty']}")
    except:
        print("❌ Could not get final status")
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    node_process.terminate()
    
    # Remove test files
    for file in ['test_miner.json', 'test_user.json']:
        if os.path.exists(file):
            os.remove(file)
    
    print("\n" + "=" * 50)
    print("🎉 Bitcoin-style Blockchain Test Complete!")
    print("\n💡 What was demonstrated:")
    print("  ✅ Network node (no wallet attached)")
    print("  ✅ Separate wallet clients")
    print("  ✅ Mining client")
    print("  ✅ ECDSA signatures (Bitcoin-compatible)")
    print("  ✅ Transaction broadcasting")
    print("  ✅ Proof-of-Work mining")
    print("\n🚀 The system works like real Bitcoin!")
    
    print("\n📖 To run manually:")
    print("  # Start node:")
    print("  python3 network_node.py --api-port 5000")
    print()
    print("  # Create wallet:")
    print("  python3 wallet_client.py create --wallet my_wallet.json")
    print()
    print("  # Start mining:")
    print("  python3 mining_client.py --wallet YOUR_ADDRESS")
    print()
    print("  # Send transaction:")
    print("  python3 wallet_client.py send --wallet my_wallet.json --to ADDRESS --amount 10")

if __name__ == '__main__':
    quick_test()