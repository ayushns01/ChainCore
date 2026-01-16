#!/usr/bin/env python3
"""
Restart Core1 (5001) to fix unicode status display issue
"""
import requests
import subprocess
import time
import sys
import os

def check_node_status(port):
    """Check if node is running"""
    try:
        response = requests.get(f"http://localhost:{port}/status", timeout=2)
        return response.status_code == 200
    except:
        return False

def stop_node(port):
    """Try to stop node gracefully"""
    try:
        response = requests.post(f"http://localhost:{port}/shutdown", timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    port = 5001
    print("🔧 ChainCore Core1 Restart Utility")
    print("=" * 40)
    
    # Check if Core1 is running
    if check_node_status(port):
        print(f"✅ Core1 (port {port}) is running")
        print("🛑 Attempting graceful shutdown...")
        
        if stop_node(port):
            print("✅ Graceful shutdown successful")
        else:
            print("⚠️  Graceful shutdown failed - node may need manual stop")
        
        # Wait a bit for shutdown
        time.sleep(3)
        
        if check_node_status(port):
            print("❌ Node still running - please stop it manually")
            print("💡 Try: Ctrl+C in the Core1 terminal window")
            return 1
    else:
        print(f"ℹ️  Core1 (port {port}) is not running")
    
    print("\n🚀 Starting Core1 with current codebase...")
    print("📝 Command: python network_node.py --node-id core1 --api-port 5001 --p2p-port 8001 --bootstrap-node http://localhost:5000")
    print("\n💡 This will fix the unicode status display issue")
    print("💡 The new instance will use the current ASCII status format")
    print("\n▶️  Please run this command in a new terminal:")
    print("   python network_node.py --node-id core1 --api-port 5001 --p2p-port 8001 --bootstrap-node http://localhost:5000")

if __name__ == "__main__":
    sys.exit(main())