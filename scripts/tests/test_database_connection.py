#!/usr/bin/env python3
"""
Test script to verify PostgreSQL database connection and basic operations
Run this to make sure your database setup is working correctly
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.data.connection import test_database_connection, get_db_manager
from src.data.block_dao import BlockDAO
from src.data.transaction_dao import TransactionDAO

def test_basic_connection():
    """Test basic database connection"""
    print("🔄 Testing database connection...")
    
    if test_database_connection():
        print("✅ Database connection successful!")
        return True
    else:
        print("❌ Database connection failed!")
        return False

def test_database_info():
    """Get and display database information"""
    print("\n📊 Getting database information...")
    
    try:
        db_manager = get_db_manager()
        info = db_manager.get_connection_info()
        
        print("✅ Database Information:")
        print(f"   📁 Database: {info.get('database_name', 'Unknown')}")
        print(f"   👤 User: {info.get('user_name', 'Unknown')}")
        print(f"   🆔 PostgreSQL Version: {info.get('postgresql_version', 'Unknown')}")
        print(f"   💾 Database Size: {info.get('database_size_bytes', 0):,} bytes")
        print(f"   🔗 Active Connections: {info.get('active_connections', 0)}")
        print(f"   🎯 Pool Size: {info.get('pool_size', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error getting database info: {e}")
        return False

def test_table_creation():
    """Test if all tables were created properly"""
    print("\n🏗️  Testing table creation...")
    
    try:
        db_manager = get_db_manager()
        
        # Check if all expected tables exist
        expected_tables = ['blocks', 'transactions', 'nodes', 'mining_stats', 'utxos']
        
        query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        
        results = db_manager.execute_query(query, fetch_all=True)
        existing_tables = [row[0] for row in results] if results else []
        
        print(f"✅ Found {len(existing_tables)} tables:")
        for table in existing_tables:
            status = "✅" if table in expected_tables else "ℹ️"
            print(f"   {status} {table}")
        
        missing_tables = set(expected_tables) - set(existing_tables)
        if missing_tables:
            print(f"\n❌ Missing tables: {', '.join(missing_tables)}")
            return False
        else:
            print(f"\n✅ All required tables found!")
            return True
            
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        return False

def test_basic_operations():
    """Test basic database operations"""
    print("\n🧪 Testing basic database operations...")
    
    try:
        # Test BlockDAO
        print("   Testing BlockDAO...")
        block_dao = BlockDAO()
        
        # Get blockchain length (should be 0 initially)
        length = block_dao.get_blockchain_length()
        print(f"   📊 Blockchain length: {length}")
        
        # Test TransactionDAO
        print("   Testing TransactionDAO...")
        tx_dao = TransactionDAO()
        
        # Get UTXO statistics (should be empty initially)
        utxo_stats = tx_dao.get_utxo_statistics()
        print(f"   📊 UTXO count: {utxo_stats.get('total_utxos', 0)}")
        
        print("✅ Basic operations test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error in basic operations test: {e}")
        return False

def test_sample_data_insertion():
    """Test inserting sample data"""
    print("\n📝 Testing sample data insertion...")
    
    try:
        db_manager = get_db_manager()
        
        # Insert a sample node
        query = """
            INSERT INTO nodes (node_id, node_url, api_port, status)
            VALUES ('test-node', 'http://localhost:5999', 5999, 'active')
            ON CONFLICT (node_id) DO UPDATE SET
                last_seen = NOW()
            RETURNING id
        """
        
        result = db_manager.execute_query(query, fetch_one=True)
        
        if result:
            node_id = result[0]
            print(f"✅ Sample node inserted/updated (ID: {node_id})")
            
            # Clean up - remove the test node
            cleanup_query = "DELETE FROM nodes WHERE node_id = 'test-node'"
            db_manager.execute_query(cleanup_query)
            print("✅ Test data cleaned up")
            
            return True
        else:
            print("❌ Failed to insert sample data")
            return False
            
    except Exception as e:
        print(f"❌ Error in sample data test: {e}")
        return False

def main():
    """Run all database tests"""
    print("🚀 ChainCore Database Connection Test")
    print("=" * 50)
    
    tests = [
        ("Basic Connection", test_basic_connection),
        ("Database Info", test_database_info),
        ("Table Creation", test_table_creation),
        ("Basic Operations", test_basic_operations),
        ("Sample Data", test_sample_data_insertion)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        print("-" * 30)
        
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed!")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Database is ready for ChainCore!")
        print("\n💡 Next steps:")
        print("   1. Integration with blockchain core")
        print("   2. Update mining client to use database")
        print("   3. Modify network node API endpoints")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        print("\n🔧 Troubleshooting:")
        print("   1. Verify PostgreSQL is running")
        print("   2. Check database credentials")
        print("   3. Ensure schema was created properly")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)