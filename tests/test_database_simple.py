#!/usr/bin/env python3
"""
Simple database test without connection pooling - avoids hanging issues
"""

import sys
import os
import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_simple_connection():
    """Test simple database connection without pooling"""
    print("🔍 Testing simple database connection...")
    
    try:
        # Direct connection with timeout
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='chaincore_blockchain',
            user='chaincore_user',
            password='chaincore_secure_2024',
            connect_timeout=5
        )
        
        print("✅ Connected successfully!")
        
        # Test query
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = 'public'")
        result = cursor.fetchone()
        
        print(f"✅ Found {result['table_count']} tables")
        
        # Test table access
        cursor.execute("SELECT COUNT(*) as block_count FROM blocks")
        result = cursor.fetchone()
        
        print(f"✅ Blocks table accessible ({result['block_count']} blocks)")
        
        cursor.close()
        conn.close()
        
        print("✅ Simple connection test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Simple connection test failed: {e}")
        return False

def test_dao_operations():
    """Test DAO operations with simple connection"""
    print("\n🧪 Testing DAO operations...")
    
    try:
        # Import after confirming connection works
        from src.data.block_dao import BlockDAO
        from src.data.transaction_dao import TransactionDAO
        
        # Test BlockDAO
        block_dao = BlockDAO()
        length = block_dao.get_blockchain_length()
        print(f"✅ BlockDAO works - chain length: {length}")
        
        # Test TransactionDAO
        tx_dao = TransactionDAO()
        utxo_stats = tx_dao.get_utxo_statistics()
        print(f"✅ TransactionDAO works - UTXOs: {utxo_stats.get('total_utxos', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ DAO operations failed: {e}")
        return False

def main():
    """Run simple tests"""
    print("🚀 Simple ChainCore Database Test")
    print("=" * 40)
    
    success1 = test_simple_connection()
    
    if success1:
        success2 = test_dao_operations()
        
        if success2:
            print("\n🎉 All simple tests passed!")
            print("✅ Database is working perfectly!")
            print("\n💡 You can now:")
            print("   1. Integrate with ChainCore blockchain")
            print("   2. Start storing blocks in database")
            print("   3. Use database for mining statistics")
            return True
        else:
            print("\n⚠️ Basic connection works, but DAO operations failed")
            return False
    else:
        print("\n❌ Basic connection failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)