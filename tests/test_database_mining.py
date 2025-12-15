#!/usr/bin/env python3
"""
Test Database Mining Recording
Checks if mining data is properly stored in database
"""

import psycopg2
import requests
import json
import time
from datetime import datetime

def check_database_connection():
    """Test database connection"""
    try:
        conn = psycopg2.connect(
            dbname='chaincore_blockchain',
            user='chaincore_user', 
            password='chaincore_secure_2024',
            host='localhost',
            port=5432
        )
        cur = conn.cursor()
        cur.execute('SELECT version()')
        version = cur.fetchone()
        print(f"[PASS] Database connection successful: {version[0][:50]}...")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")
        return False

def check_table_data():
    """Check current data in all tables"""
    try:
        conn = psycopg2.connect(
            dbname='chaincore_blockchain',
            user='chaincore_user', 
            password='chaincore_secure_2024',
            host='localhost',
            port=5432
        )
        cur = conn.cursor()
        
        # Check all tables
        tables = ['blocks', 'mining_stats', 'transactions', 'utxos', 'nodes']
        for table in tables:
            cur.execute(f'SELECT COUNT(*) FROM {table}')
            count = cur.fetchone()[0]
            print(f"  {table}: {count} records")
            
            # Show some sample data if available
            if count > 0 and table == 'blocks':
                cur.execute(f'SELECT block_index, block_hash, miner_address, created_at FROM {table} ORDER BY block_index DESC LIMIT 3')
                blocks = cur.fetchall()
                print(f"    Recent blocks:")
                for block in blocks:
                    print(f"      Block {block[0]}: {block[1][:20]}... by {block[2]} at {block[3]}")
            
            elif count > 0 and table == 'mining_stats':
                cur.execute(f'SELECT node_id, block_id, mining_duration_seconds, hash_rate FROM {table} ORDER BY created_at DESC LIMIT 3')
                stats = cur.fetchall()
                print(f"    Recent mining stats:")
                for stat in stats:
                    print(f"      Node: {stat[0]}, Block: {stat[1]}, Duration: {stat[2]}s, Hash Rate: {stat[3]}")
                    
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to check table data: {e}")
        return False

def test_simple_mining():
    """Try to trigger simple mining via API"""
    print("\n=== Testing Simple Mining ===")
    
    try:
        # Try mining with minimal data
        response = requests.post(
            'http://localhost:5000/mine_block',
            json={'miner_address': 'test_database_miner'},
            timeout=30
        )
        
        print(f"  Mining response status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"  Mining response: {json.dumps(data, indent=2)}")
                return True
            except:
                print(f"  Mining response (text): {response.text[:200]}...")
                return True
        else:
            print(f"  Mining failed: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"  [ERROR] Mining request failed: {e}")
        return False

def check_node_status():
    """Check if nodes are properly recording data"""
    print("\n=== Node Status Check ===")
    
    nodes = [
        'http://localhost:5000',
        'http://localhost:5001', 
        'http://localhost:5002'
    ]
    
    for node_url in nodes:
        try:
            response = requests.get(f"{node_url}/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                chain_length = data.get('blockchain_length', 0)
                pending_txs = data.get('pending_transactions', 0)
                node_id = data.get('node_id', 'unknown')
                print(f"  {node_url}: {node_id} | Chain: {chain_length} | Pending: {pending_txs}")
            else:
                print(f"  {node_url}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"  {node_url}: Error - {e}")

def run_database_mining_test():
    """Run comprehensive database mining test"""
    print("ChainCore Database Mining Test")
    print("=" * 50)
    
    print("\n=== Database Connection Test ===")
    if not check_database_connection():
        return False
    
    print("\n=== Current Database State ===")
    check_table_data()
    
    check_node_status()
    
    # Try mining
    mining_success = test_simple_mining()
    
    # Check database after mining attempt
    print("\n=== Database State After Mining ===")
    check_table_data()
    
    print("\n=== Summary ===")
    print(f"Mining attempt: {'SUCCESS' if mining_success else 'FAILED'}")
    
    return True

if __name__ == "__main__":
    run_database_mining_test()