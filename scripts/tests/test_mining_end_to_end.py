#!/usr/bin/env python3

import os
import sys
import time
import json
import requests

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from clients.mining_client import MiningClient
from data.connection import get_connection

def test_actual_mining():
    """Test actual mining to verify transactions are preserved"""
    print("🔍 Testing actual mining with transaction preservation...")
    
    try:
        # Check if node is running
        response = requests.get("http://localhost:5000/blockchain/stats", timeout=2)
        if response.status_code != 200:
            print("❌ Node not running at localhost:5000")
            return
    except:
        print("❌ Cannot connect to node at localhost:5000")
        print("   Please start the node first: python -m src.nodes.node")
        return
    
    # Initialize mining client
    client = MiningClient(
        node_url="http://localhost:5000",
        wallet_address="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    )
    
    print("✅ Mining client initialized")
    
    # Get current blockchain state
    try:
        response = requests.get("http://localhost:5000/blockchain/stats")
        stats = response.json()
        current_height = stats['current_height']
        print(f"📊 Current blockchain height: {current_height}")
    except:
        print("❌ Cannot get blockchain stats")
        return
    
    # Mine one block
    print("⛏️  Starting mining (timeout: 30 seconds)...")
    
    try:
        result = client.mine_block_loop(max_iterations=1, timeout=30)
        if result:
            print("🎉 Successfully mined a block!")
            
            # Check if transactions were preserved
            if 'all_transactions' in result:
                tx_count = len(result['all_transactions'])
                print(f"✅ Mined block contains {tx_count} transactions")
                
                if tx_count > 0:
                    coinbase_tx = result['all_transactions'][0]
                    print(f"   Coinbase transaction ID: {coinbase_tx.get('id', 'unknown')}")
                    print(f"   Coinbase reward: {coinbase_tx.get('block_reward', 'unknown')} coins")
                    print("✅ SUCCESS: Transactions preserved in mining!")
                else:
                    print("❌ FAILED: No transactions in mined block")
            else:
                print("❌ FAILED: No 'all_transactions' field in mined block")
                
        else:
            print("⏱️  Mining timed out (difficulty may be too high)")
            
    except Exception as e:
        print(f"❌ Mining failed: {e}")

def check_database_for_transactions():
    """Check if transactions are actually stored in database"""
    print("\n🗄️  Checking database for stored transactions...")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Count transactions
        cursor.execute("SELECT COUNT(*) FROM transactions")
        tx_count = cursor.fetchone()[0]
        
        # Count blocks
        cursor.execute("SELECT COUNT(*) FROM blocks")
        block_count = cursor.fetchone()[0]
        
        print(f"📊 Database contains:")
        print(f"   Blocks: {block_count}")
        print(f"   Transactions: {tx_count}")
        
        if tx_count > 0:
            cursor.execute("SELECT id, type, data FROM transactions ORDER BY id DESC LIMIT 5")
            recent_txs = cursor.fetchall()
            print(f"   Recent transactions:")
            for tx_id, tx_type, data in recent_txs:
                print(f"     {tx_id}: {tx_type}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")

if __name__ == "__main__":
    test_actual_mining()
    check_database_for_transactions()