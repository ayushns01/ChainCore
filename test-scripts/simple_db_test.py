#!/usr/bin/env python3
"""
Ultra-simple database connection test
"""

import psycopg2
import sys

def test_direct_connection():
    """Test direct psycopg2 connection"""
    print("🔍 Testing direct database connection...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='chaincore_blockchain',
            user='chaincore_user',
            password='chaincore_secure_2024',
            connect_timeout=3  # 3 second timeout
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM blocks")
        result = cursor.fetchone()
        
        print(f"✅ Direct connection works")
        print(f"📊 Blocks in database: {result[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Direct connection failed: {e}")
        return False

def test_import_only():
    """Test importing database modules"""
    print("\n🔍 Testing database module imports...")
    
    try:
        sys.path.insert(0, 'src')
        
        print("   Importing connection module...")
        from src.database.connection import get_db_manager
        print("   ✅ Connection module imported")
        
        print("   Importing DAO modules...")
        from src.database.block_dao import BlockDAO
        from src.database.transaction_dao import TransactionDAO
        print("   ✅ DAO modules imported")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Ultra-Simple Database Test")
    print("=" * 30)
    
    # Test 1: Direct connection
    direct_ok = test_direct_connection()
    
    if direct_ok:
        # Test 2: Module imports
        import_ok = test_import_only()
        
        if import_ok:
            print("\n🎉 Both tests passed!")
            print("The issue is likely in the connection pool initialization.")
        else:
            print("\n❌ Import test failed")
    else:
        print("\n❌ Direct connection failed")
        print("Check if PostgreSQL is running and credentials are correct")