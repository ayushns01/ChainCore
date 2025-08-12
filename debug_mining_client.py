#!/usr/bin/env python3
"""
Debug script to identify mining client issues
"""

import sys
import os
import requests
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_basic_connection():
    """Test basic API connectivity"""
    print("🔍 Testing basic API connectivity...")
    try:
        resp = requests.get('http://localhost:5000/status', timeout=5)
        if resp.status_code == 200:
            print("✅ API connection successful")
            return True
        else:
            print(f"❌ API returned status {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_mining_api():
    """Test mining API endpoint"""
    print("🔍 Testing mining API...")
    try:
        resp = requests.post('http://localhost:5000/mine_block',
                            json={'miner_address': 'debug_miner'},
                            headers={'Content-Type': 'application/json'},
                            timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            print("✅ Mining API successful")
            print(f"   Status: {data.get('status')}")
            print(f"   Target difficulty: {data.get('target_difficulty')}")
            return True
        else:
            print(f"❌ Mining API returned status {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"❌ Mining API failed: {e}")
        return False

def test_imports():
    """Test required imports"""
    print("🔍 Testing imports...")
    try:
        from src.crypto.ecdsa_crypto import double_sha256
        print("✅ Crypto imports successful")
        
        # Test the function
        result = double_sha256("test")
        print(f"✅ double_sha256 function works: {result[:16]}...")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Function test failed: {e}")
        return False

def test_mining_client_instantiation():
    """Test mining client class instantiation"""
    print("🔍 Testing mining client instantiation...")
    try:
        # Import the mining client
        from mining_client import MiningClient
        
        # Create instance
        client = MiningClient("debug_wallet", "http://localhost:5000")
        print("✅ MiningClient instantiation successful")
        
        # Test basic methods
        stats = client.get_mining_stats()
        print(f"✅ get_mining_stats works: {stats}")
        
        return True
    except ImportError as e:
        print(f"❌ MiningClient import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ MiningClient test failed: {e}")
        return False

def main():
    print("🔬 MINING CLIENT DIAGNOSTIC TEST")
    print("=" * 50)
    
    tests = [
        ("Basic Connection", test_basic_connection),
        ("Mining API", test_mining_api),
        ("Required Imports", test_imports),
        ("Mining Client Class", test_mining_client_instantiation)
    ]
    
    passed = 0
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        if test_func():
            passed += 1
        print("-" * 30)
    
    print(f"\n📊 RESULTS: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("✅ All tests passed - mining client should work!")
    else:
        print("❌ Some tests failed - this explains why mining client exits")

if __name__ == "__main__":
    main()