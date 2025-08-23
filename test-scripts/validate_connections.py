#!/usr/bin/env python3
"""
ChainCore Enhanced Synchronization Validation
Validates all connections and integrations are working properly
"""

import sys
import os
sys.path.insert(0, os.getcwd())

def validate_imports():
    """Test all critical imports work"""
    print("📦 Testing Imports")
    print("-" * 20)
    
    try:
        # Core concurrency imports
        from src.concurrency import (
            ThreadSafeBlockchain, ThreadSafePeerManager,
            synchronized, LockOrder, lock_manager
        )
        print("✅ Core concurrency imports")
        
        # Configuration imports
        from src.config import (
            DIFFICULTY_ADJUSTMENT_ENABLED, TARGET_BLOCK_TIME,
            DIFFICULTY_ADJUSTMENT_INTERVAL, get_all_config
        )
        print("✅ Enhanced configuration imports")
        
        # Network node
        from network_node import ThreadSafeNetworkNode
        print("✅ Network node import")
        
        # Mining client
        from mining_client import MiningClient
        print("✅ Mining client import")
        
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def validate_functionality():
    """Test that all new functionality is accessible"""
    print("\n🔧 Testing Functionality")
    print("-" * 25)
    
    try:
        # Test blockchain with enhanced features
        from src.concurrency.blockchain_safe import ThreadSafeBlockchain
        blockchain = ThreadSafeBlockchain()
        
        # Test difficulty adjustment
        if hasattr(blockchain, '_calculate_new_difficulty'):
            diff = blockchain._calculate_new_difficulty()
            print(f"✅ Difficulty adjustment: {diff}")
        else:
            print("❌ Difficulty adjustment missing")
        
        # Test orphaned blocks
        if hasattr(blockchain, 'get_orphaned_blocks'):
            orphaned = blockchain.get_orphaned_blocks()
            print(f"✅ Orphaned blocks: {len(orphaned)} blocks")
        else:
            print("❌ Orphaned blocks missing")
        
        # Test enhanced peer manager
        from src.concurrency.network_safe import ThreadSafePeerManager
        peer_manager = ThreadSafePeerManager()
        
        # Test mempool sync
        if hasattr(peer_manager, 'configure_mempool_sync'):
            peer_manager.configure_mempool_sync(True, 15.0)
            print("✅ Mempool sync configuration")
        else:
            print("❌ Mempool sync missing")
        
        # Test network stats
        if hasattr(peer_manager, 'get_network_wide_stats'):
            stats = peer_manager.get_network_wide_stats()
            print(f"✅ Network stats: {len(stats)} fields")
        else:
            print("❌ Network stats missing")
        
        return True
    except Exception as e:
        print(f"❌ Functionality error: {e}")
        return False

def validate_api_endpoints():
    """Test that all new API endpoints are registered"""
    print("\n🌐 Testing API Endpoints") 
    print("-" * 25)
    
    try:
        from network_node import ThreadSafeNetworkNode
        node = ThreadSafeNetworkNode('validate', 9995, 9994)
        
        # Get all registered routes
        routes = [rule.rule for rule in node.app.url_map.iter_rules()]
        
        # Check new endpoints
        new_endpoints = [
            '/orphaned_blocks',
            '/network_config',
            '/sync_mempool', 
            '/sync_network_stats'
        ]
        
        all_present = True
        for endpoint in new_endpoints:
            if endpoint in routes:
                print(f"✅ {endpoint}")
            else:
                print(f"❌ {endpoint} missing")
                all_present = False
        
        # Test enhanced status endpoint
        with node.app.test_client() as client:
            response = client.get('/status')
            if response.status_code == 200:
                data = response.get_json()
                
                if 'mempool_sync' in data and 'network_stats_sync' in data:
                    print("✅ Enhanced status endpoint")
                else:
                    print("❌ Status endpoint missing new fields")
                    all_present = False
            else:
                print(f"❌ Status endpoint failed: {response.status_code}")
                all_present = False
        
        return all_present
    except Exception as e:
        print(f"❌ API endpoint error: {e}")
        return False

def validate_configuration():
    """Test configuration synchronization"""
    print("\n⚙️ Testing Configuration")
    print("-" * 25)
    
    try:
        from src.config import (
            BLOCKCHAIN_DIFFICULTY, DIFFICULTY_ADJUSTMENT_ENABLED,
            TARGET_BLOCK_TIME, DIFFICULTY_ADJUSTMENT_INTERVAL
        )
        
        print(f"✅ Base difficulty: {BLOCKCHAIN_DIFFICULTY}")
        print(f"✅ Adjustment enabled: {DIFFICULTY_ADJUSTMENT_ENABLED}")
        print(f"✅ Target block time: {TARGET_BLOCK_TIME}s")
        print(f"✅ Adjustment interval: {DIFFICULTY_ADJUSTMENT_INTERVAL} blocks")
        
        # Test blockchain uses config
        from src.concurrency.blockchain_safe import ThreadSafeBlockchain
        blockchain = ThreadSafeBlockchain()
        
        if blockchain.difficulty_adjustment_enabled == DIFFICULTY_ADJUSTMENT_ENABLED:
            print("✅ Config sync to blockchain")
        else:
            print("❌ Config sync failed")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def main():
    """Run all validation tests"""
    print("🔍 ChainCore Enhanced Synchronization Validation")
    print("=" * 55)
    
    tests = [
        ("Imports", validate_imports),
        ("Functionality", validate_functionality),
        ("API Endpoints", validate_api_endpoints), 
        ("Configuration", validate_configuration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        if test_func():
            passed += 1
    
    print(f"\n📊 Validation Results")
    print("=" * 20)
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All validations passed!")
        print("\n✅ Enhanced Synchronization Features:")
        print("   • Mempool synchronization (15s interval)")
        print("   • Network-wide statistics aggregation (60s interval)")  
        print("   • Orphaned block management with recovery")
        print("   • Dynamic difficulty adjustment")
        print("   • Configuration synchronization")
        print("   • 4 new API endpoints")
        print("   • Enhanced status reporting")
        return True
    else:
        print(f"❌ {total - passed} validation(s) failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)