#!/usr/bin/env python3
"""
Test ChainCore with simple database integration
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_simple_integration():
    """Test the simple database integration"""
    print("🚀 Testing Simple Database Integration")
    print("=" * 40)
    
    try:
        print("1️⃣ Testing simple database connection...")
        from src.data.simple_connection import get_simple_db_manager
        db_manager = get_simple_db_manager()
        db_manager.initialize()
        print("   ✅ Simple database connection works")
        
        print("\n2️⃣ Testing blockchain with database integration...")
        from src.concurrency.blockchain_safe import ThreadSafeBlockchain
        blockchain = ThreadSafeBlockchain()
        
        print(f"   ✅ Blockchain created")
        print(f"   🗄️  Database enabled: {blockchain.database_enabled}")
        print(f"   📊 Chain length: {blockchain.get_chain_length()}")
        
        if blockchain.database_enabled:
            print("\n3️⃣ Testing block template creation...")
            template = blockchain.create_block_template("test-miner", "test-node")
            print(f"   ✅ Block template created: #{template.index}")
            print(f"   🏷️  Hash: {template.hash[:16]}...")
            
            print("\n🎉 All tests passed!")
            print("✅ Simple database integration is working!")
            return True
        else:
            print("   ⚠️  Database not enabled in blockchain")
            return False
            
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if test_simple_integration():
        print("\n💡 Ready to test mining with database storage!")
        print("   Next: python network_node.py --node-id core1 --api-port 5001")
    else:
        print("\n❌ Integration test failed")