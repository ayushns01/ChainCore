#!/usr/bin/env python3
"""
Quick database connection test - diagnoses connection issues
"""

import psycopg2
import sys

def test_connection():
    """Test basic PostgreSQL connection"""
    
    print("🔍 Testing PostgreSQL connection...")
    
    # Connection parameters
    config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'postgres',  # Connect to default database first
        'user': 'postgres',
        'password': 'YOUR_PASSWORD'
    }
    
    try:
        print(f"   🔌 Connecting to {config['host']}:{config['port']}...")
        
        # Test connection with short timeout
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password'],
            connect_timeout=5  # 5 second timeout
        )
        
        print("   ✅ Connected to PostgreSQL!")
        
        # Test query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"   📊 PostgreSQL Version: {version}")
        
        # Test if our database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'chaincore_blockchain';")
        db_exists = cursor.fetchone()
        
        if db_exists:
            print("   ✅ chaincore_blockchain database exists")
        else:
            print("   ❌ chaincore_blockchain database NOT found")
            print("   💡 Need to create the database first")
        
        cursor.close()
        conn.close()
        
        print("   ✅ Connection test successful!")
        return True
        
    except psycopg2.OperationalError as e:
        print(f"   ❌ Connection failed: {e}")
        if "could not connect to server" in str(e):
            print("   💡 PostgreSQL server is not running")
            print("   🔧 Solution: Start PostgreSQL service")
        elif "authentication failed" in str(e):
            print("   💡 Wrong password")
            print("   🔧 Solution: Check password is 'YOUR_PASSWORD'")
        return False
        
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False

def test_chaincore_database():
    """Test connection to ChainCore database specifically"""
    
    print("\n🎯 Testing ChainCore database connection...")
    
    config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'chaincore_blockchain',
        'user': 'chaincore_user',
        'password': 'chaincore_secure_2024'
    }
    
    try:
        print("   🔌 Connecting to chaincore_blockchain...")
        
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password'],
            connect_timeout=5
        )
        
        print("   ✅ Connected to ChainCore database!")
        
        # Test tables exist
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()
        
        if tables:
            print(f"   ✅ Found {len(tables)} tables:")
            for table in tables:
                print(f"      - {table[0]}")
        else:
            print("   ❌ No tables found - schema not created")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.OperationalError as e:
        print(f"   ❌ ChainCore database connection failed: {e}")
        if "database \"chaincore_blockchain\" does not exist" in str(e):
            print("   💡 Database doesn't exist")
            print("   🔧 Solution: Create database using SQL Shell")
        elif "authentication failed" in str(e):
            print("   💡 User/password issue")
            print("   🔧 Solution: Create user with correct permissions")
        return False
        
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Quick PostgreSQL Connection Test")
    print("=" * 40)
    
    # Test basic connection
    basic_ok = test_connection()
    
    if basic_ok:
        # Test ChainCore database
        chaincore_ok = test_chaincore_database()
        
        if chaincore_ok:
            print("\n🎉 All tests passed! Database is ready!")
        else:
            print("\n⚠️  Basic connection works, but ChainCore database has issues")
    else:
        print("\n❌ Basic connection failed - PostgreSQL is not accessible")
        
    print("\n🔧 Next steps:")
    if not basic_ok:
        print("   1. Start PostgreSQL service")
        print("   2. Check password is 'YOUR_PASSWORD'")
    elif not chaincore_ok:
        print("   1. Create chaincore_blockchain database")
        print("   2. Create chaincore_user")
        print("   3. Run schema.sql")