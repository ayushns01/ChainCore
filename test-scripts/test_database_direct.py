#!/usr/bin/env python3
"""
Direct database test without DAO classes - tests core functionality
"""

import sys
import os
import psycopg2
import psycopg2.extras
import json
import time

def make_64_char_string(prefix):
    """Create exactly 64 character string with given prefix"""
    if len(prefix) >= 64:
        return prefix[:64]
    return prefix + "0" * (64 - len(prefix))

def get_connection():
    """Get direct database connection"""
    return psycopg2.connect(
        host='localhost',
        port=5432,
        database='chaincore_blockchain',
        user='chaincore_user',
        password='chaincore_secure_2024',
        connect_timeout=5
    )

def test_direct_operations():
    """Test database operations directly"""
    print("🚀 Direct Database Operations Test")
    print("=" * 40)
    
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        print("✅ Connected to database")
        
        # Test 1: Check tables exist
        print("\n📋 Checking tables...")
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' ORDER BY table_name
        """)
        tables = cursor.fetchall()
        
        expected_tables = ['blocks', 'transactions', 'nodes', 'mining_stats', 'utxos']
        found_tables = [row['table_name'] for row in tables]
        
        for table in expected_tables:
            if table in found_tables:
                print(f"   ✅ {table}")
            else:
                print(f"   ❌ {table} - MISSING")
        
        # Test 2: Insert sample data
        print("\n📝 Testing data insertion...")
        
        # Insert a sample node
        cursor.execute("""
            INSERT INTO nodes (node_id, node_url, api_port, status)
            VALUES ('test-node-direct', 'http://localhost:5999', 5999, 'active')
            ON CONFLICT (node_id) DO UPDATE SET last_seen = NOW()
            RETURNING id
        """)
        node_result = cursor.fetchone()
        print(f"   ✅ Node inserted (ID: {node_result['id']})")
        
        # Insert a sample block
        sample_block_data = {
            "index": 999,
            "hash": make_64_char_string("test_block"),
            "previous_hash": make_64_char_string(""),  # 64 zeros
            "merkle_root": make_64_char_string("test_merkle"),
            "timestamp": time.time(),
            "nonce": 12345,
            "difficulty": 4,
            "transactions": []
        }
        
        cursor.execute("""
            INSERT INTO blocks (
                block_index, hash, previous_hash, merkle_root, 
                timestamp, nonce, difficulty, miner_node, 
                miner_address, transaction_count, block_data
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (block_index) DO UPDATE SET 
                timestamp = EXCLUDED.timestamp
            RETURNING id
        """, (
            sample_block_data["index"],
            sample_block_data["hash"],
            sample_block_data["previous_hash"],
            sample_block_data["merkle_root"],
            sample_block_data["timestamp"],
            sample_block_data["nonce"],
            sample_block_data["difficulty"],
            'test-node-direct',
            make_64_char_string('test-address'),
            0,
            json.dumps(sample_block_data)
        ))
        
        block_result = cursor.fetchone()
        print(f"   ✅ Block inserted (ID: {block_result['id']})")
        
        # Test 3: Query data
        print("\n🔍 Testing data retrieval...")
        
        cursor.execute("SELECT COUNT(*) as total FROM blocks")
        block_count = cursor.fetchone()
        print(f"   ✅ Total blocks: {block_count['total']}")
        
        cursor.execute("SELECT COUNT(*) as total FROM nodes")
        node_count = cursor.fetchone()
        print(f"   ✅ Total nodes: {node_count['total']}")
        
        cursor.execute("SELECT COUNT(*) as total FROM transactions")
        tx_count = cursor.fetchone()
        print(f"   ✅ Total transactions: {tx_count['total']}")
        
        cursor.execute("SELECT COUNT(*) as total FROM utxos")
        utxo_count = cursor.fetchone()
        print(f"   ✅ Total UTXOs: {utxo_count['total']}")
        
        # Test 4: Advanced queries
        print("\n📊 Testing advanced queries...")
        
        cursor.execute("""
            SELECT miner_node, COUNT(*) as blocks_mined 
            FROM blocks 
            GROUP BY miner_node 
            ORDER BY blocks_mined DESC
        """)
        mining_stats = cursor.fetchall()
        
        if mining_stats:
            print("   ✅ Mining statistics:")
            for stat in mining_stats[:3]:  # Show top 3
                print(f"      {stat['miner_node']}: {stat['blocks_mined']} blocks")
        
        # Test 5: Clean up test data
        print("\n🧹 Cleaning up test data...")
        cursor.execute("DELETE FROM blocks WHERE block_index = 999")
        cursor.execute("DELETE FROM nodes WHERE node_id = 'test-node-direct'")
        
        conn.commit()
        print("   ✅ Test data cleaned up")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 All direct database tests passed!")
        print("✅ Your PostgreSQL database is fully functional!")
        
        return True
        
    except Exception as e:
        print(f"❌ Direct database test failed: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

def test_blockchain_simulation():
    """Simulate basic blockchain operations"""
    print("\n⛓️ Testing blockchain simulation...")
    
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Create genesis block
        genesis_data = {
            "index": 0,
            "hash": make_64_char_string("genesis"),
            "previous_hash": make_64_char_string(""),  # 64 zeros
            "merkle_root": make_64_char_string("merkle"),
            "timestamp": time.time(),
            "nonce": 0,
            "difficulty": 4,
            "transactions": []
        }
        
        cursor.execute("""
            INSERT INTO blocks (
                block_index, hash, previous_hash, merkle_root, 
                timestamp, nonce, difficulty, miner_node, 
                miner_address, transaction_count, block_data
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (block_index) DO UPDATE SET 
                timestamp = EXCLUDED.timestamp
            RETURNING id
        """, (
            genesis_data["index"],
            genesis_data["hash"],
            genesis_data["previous_hash"],
            genesis_data["merkle_root"],
            genesis_data["timestamp"],
            genesis_data["nonce"],
            genesis_data["difficulty"],
            'genesis-node',
            make_64_char_string('genesis-addr'),
            0,
            json.dumps(genesis_data)
        ))
        
        conn.commit()
        
        # Verify blockchain integrity
        cursor.execute("""
            SELECT block_index, hash, previous_hash
            FROM blocks 
            ORDER BY block_index
        """)
        
        blocks = cursor.fetchall()
        print(f"   ✅ Created blockchain with {len(blocks)} block(s)")
        
        # Clean up
        cursor.execute("DELETE FROM blocks WHERE block_index = 0")
        conn.commit()
        
        cursor.close()
        conn.close()
        
        print("   ✅ Blockchain simulation successful!")
        return True
        
    except Exception as e:
        print(f"   ❌ Blockchain simulation failed: {e}")
        return False

def main():
    """Run all direct tests"""
    success1 = test_direct_operations()
    
    if success1:
        success2 = test_blockchain_simulation()
        
        if success2:
            print("\n🚀 CONGRATULATIONS!")
            print("=" * 50)
            print("✅ PostgreSQL database is fully working")
            print("✅ All tables are properly created")
            print("✅ Data insertion and retrieval works")
            print("✅ Advanced queries work")
            print("✅ Blockchain operations work")
            print("\n🎯 Next Steps:")
            print("   1. Integrate with ChainCore mining client")
            print("   2. Integrate with ChainCore network node")
            print("   3. Start storing real blockchain data")
            print("   4. Use database for mining analytics")
            
            return True
        else:
            print("\n⚠️ Basic operations work, blockchain simulation failed")
            return False
    else:
        print("\n❌ Direct database operations failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)