#!/usr/bin/env python3
"""
Simple mining test to manually verify mining functionality
"""

import sys
import os
import requests
import json
import time

# Add src and parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mining_client import MiningClient

def simple_mining_test():
    print("🚀 Starting simple mining test...")
    
    # Check initial blockchain length
    resp = requests.get('http://localhost:5000/status')
    if resp.status_code == 200:
        initial_length = resp.json()['blockchain_length']
        print(f"📊 Initial blockchain length: {initial_length}")
    else:
        print("❌ Failed to get initial status")
        return False
    
    # Create mining client
    client = MiningClient("simple_test_miner", "http://localhost:5000")
    
    print("🔗 Testing network health check...")
    # For single-node testing, bypass the peer requirement
    print("⚠️  Bypassing network health check for single-node testing")
    
    print("⛏️  Starting mining for 10 seconds...")
    
    # Start mining in a controlled way
    client.is_mining = True
    client.start_time = time.time()
    
    try:
        # Try one mining attempt
        print("🎯 Attempting one mining cycle...")
        success = client.mine_with_retry(max_retries=1)
        
        if success:
            print("✅ Mining successful!")
        else:
            print("❌ Mining failed")
            
    except Exception as e:
        print(f"❌ Mining error: {e}")
        return False
    finally:
        client.is_mining = False
    
    # Check final blockchain length
    resp = requests.get('http://localhost:5000/status')
    if resp.status_code == 200:
        final_length = resp.json()['blockchain_length']
        print(f"📊 Final blockchain length: {final_length}")
        
        if final_length > initial_length:
            print("🎉 SUCCESS: Blockchain length increased!")
            return True
        else:
            print("❌ FAILURE: Blockchain length did not increase")
            return False
    else:
        print("❌ Failed to get final status")
        return False

if __name__ == "__main__":
    result = simple_mining_test()
    if result:
        print("\n✅ MINING TEST PASSED")
    else:
        print("\n❌ MINING TEST FAILED")