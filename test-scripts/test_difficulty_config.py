#!/usr/bin/env python3
"""
Test script to verify centralized difficulty configuration works
"""

import sys
import os

# Add src and parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_config_import():
    """Test that config can be imported correctly"""
    print("🧪 Testing configuration import...")
    
    try:
        from src.config import BLOCKCHAIN_DIFFICULTY, get_difficulty, get_mining_target
        print(f"✅ Config imported successfully")
        print(f"   BLOCKCHAIN_DIFFICULTY = {BLOCKCHAIN_DIFFICULTY}")
        print(f"   get_difficulty() = {get_difficulty()}")
        print(f"   get_mining_target() = '{get_mining_target()}'")
        return True
    except Exception as e:
        print(f"❌ Config import failed: {e}")
        return False

def test_network_node_config():
    """Test that network_node uses centralized config"""
    print("\n🧪 Testing network_node configuration...")
    
    try:
        import network_node
        print(f"✅ Network node imports config successfully")
        print(f"   BLOCKCHAIN_DIFFICULTY = {network_node.BLOCKCHAIN_DIFFICULTY}")
        
        # Test Block class uses correct difficulty
        from src.blockchain.bitcoin_transaction import Transaction
        test_tx = Transaction.create_coinbase_transaction("test", 50.0, 0)
        block = network_node.Block(0, [test_tx], "0" * 64)
        print(f"   Block.target_difficulty = {block.target_difficulty}")
        print(f"   Block mining target = '{block._calculate_hash()[:10]}...'")
        return True
    except Exception as e:
        print(f"❌ Network node config failed: {e}")
        return False

def test_blockchain_safe_config():
    """Test that blockchain_safe uses centralized config"""
    print("\n🧪 Testing blockchain_safe configuration...")
    
    try:
        from src.concurrency.blockchain_safe import ThreadSafeBlockchain
        blockchain = ThreadSafeBlockchain()
        print(f"✅ Blockchain safe imports config successfully")
        print(f"   blockchain.target_difficulty = {blockchain.target_difficulty}")
        print(f"   blockchain.block_reward = {blockchain.block_reward}")
        return True
    except Exception as e:
        print(f"❌ Blockchain safe config failed: {e}")
        return False

def test_mining_safe_config():
    """Test that mining_safe uses centralized config"""
    print("\n🧪 Testing mining_safe configuration...")
    
    try:
        from src.concurrency.mining_safe import WorkCoordinator
        coordinator = WorkCoordinator()
        default_difficulty = coordinator._get_default_difficulty()
        print(f"✅ Mining safe imports config successfully")
        print(f"   coordinator._get_default_difficulty() = {default_difficulty}")
        return True
    except Exception as e:
        print(f"❌ Mining safe config failed: {e}")
        return False

def test_difficulty_consistency():
    """Test that all components report same difficulty"""
    print("\n🧪 Testing difficulty consistency across components...")
    
    try:
        from src.config import BLOCKCHAIN_DIFFICULTY
        import network_node
        from src.concurrency.blockchain_safe import ThreadSafeBlockchain
        from src.concurrency.mining_safe import WorkCoordinator
        
        config_difficulty = BLOCKCHAIN_DIFFICULTY
        network_difficulty = network_node.BLOCKCHAIN_DIFFICULTY
        
        blockchain = ThreadSafeBlockchain()
        blockchain_difficulty = blockchain.target_difficulty
        
        coordinator = WorkCoordinator()
        mining_difficulty = coordinator._get_default_difficulty()
        
        print(f"   Config difficulty:     {config_difficulty}")
        print(f"   Network difficulty:    {network_difficulty}")
        print(f"   Blockchain difficulty: {blockchain_difficulty}")
        print(f"   Mining difficulty:     {mining_difficulty}")
        
        if config_difficulty == network_difficulty == blockchain_difficulty == mining_difficulty:
            print("✅ All components use same difficulty - PERFECT!")
            return True
        else:
            print("❌ Difficulty mismatch detected!")
            return False
            
    except Exception as e:
        print(f"❌ Consistency test failed: {e}")
        return False

def main():
    """Run all configuration tests"""
    print("🚀 ChainCore Difficulty Configuration Test")
    print("=" * 50)
    
    tests = [
        test_config_import,
        test_network_node_config,
        test_blockchain_safe_config,
        test_mining_safe_config,
        test_difficulty_consistency
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Configuration system working perfectly!")
        print("💡 You can now change difficulty in src/config.py and it will")
        print("   automatically update all components when nodes restart.")
    else:
        print("⚠️  Some tests failed - check configuration setup")
    
    print("\n📋 Next steps:")
    print("1. Edit src/config.py to change BLOCKCHAIN_DIFFICULTY")
    print("2. Restart nodes: pkill -f network_node.py && python3 network_node.py ...")
    print("3. Start mining: python3 mining_client.py --wallet ... --node ...")

if __name__ == "__main__":
    main()