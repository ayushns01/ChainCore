#!/usr/bin/env python3
"""
Test ChainCore database integration
Quick diagnostic for database-enabled blockchain
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_database_connection():
    """Test basic database connection"""
    print("1️⃣ Testing database connection...")
    
    try:
        from src.database.connection import get_db_manager
        db_manager = get_db_manager()
        db_manager.initialize()
        print("   ✅ Database connection successful")
        return True
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        return False

def test_blockchain_import():
    """Test blockchain import with database integration"""
    print("\n2️⃣ Testing blockchain import...")
    
    try:
        from src.concurrency.blockchain_safe import ThreadSafeBlockchain
        blockchain = ThreadSafeBlockchain()
        print(f"   ✅ Blockchain imported successfully")
        print(f"   🗄️  Database enabled: {getattr(blockchain, 'database_enabled', False)}")
        print(f"   📊 Chain length: {blockchain.get_chain_length()}")
        return True
    except Exception as e:
        print(f"   ❌ Blockchain import failed: {e}")
        return False

def test_block_creation():
    """Test creating and potentially storing a block"""
    print("\n3️⃣ Testing block creation...")
    
    try:
        from src.concurrency.blockchain_safe import ThreadSafeBlockchain
        blockchain = ThreadSafeBlockchain()
        
        # Create a test block template
        template = blockchain.create_block_template("test-miner-address", "test-node")
        print(f"   ✅ Block template created: #{template.index}")
        
        # Test mining simulation (set a simple nonce)
        template.nonce = 12345
        template.hash = template._calculate_hash()
        
        print(f"   🏷️  Block hash: {template.hash[:16]}...")
        return True
    except Exception as e:
        print(f"   ❌ Block creation failed: {e}")
        return False

def test_database_storage():
    """Test database storage directly"""
    print("\n4️⃣ Testing database storage...")
    
    try:
        from src.database.block_dao import BlockDAO
        block_dao = BlockDAO()
        
        length = block_dao.get_blockchain_length()
        print(f"   ✅ Database query successful")
        print(f"   📊 Blocks in database: {length}")
        
        if length > 0:
            latest = block_dao.get_latest_block()
            if latest:
                print(f"   📦 Latest block: #{latest['block_index']}")
                print(f"   ⛏️  Miner: {latest.get('miner_node', 'unknown')}")
        
        return True
    except Exception as e:
        print(f"   ❌ Database storage test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 ChainCore Database Integration Test")
    print("=" * 50)
    
    tests = [
        test_database_connection,
        test_blockchain_import, 
        test_block_creation,
        test_database_storage
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        else:
            break  # Stop on first failure
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! Database integration is working!")
        print("\n💡 Next steps:")
        print("   1. python network_node.py --node-id core1 --api-port 5001")
        print("   2. python mining_client.py --miner-address test --api-server http://localhost:5001")
        print("   3. Watch blocks get stored in PostgreSQL!")
    else:
        print("❌ Some tests failed. Check errors above.")
    
    return passed == len(tests)

if __name__ == "__main__":
    main()