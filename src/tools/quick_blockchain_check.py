#!/usr/bin/env python3
"""
Quick blockchain verification commands
"""

import requests
import json
import sys

def check_blocks_and_miners(node_url="http://localhost:5000"):
    """Quick check of blocks and miners"""
    try:
        response = requests.get(f"{node_url}/blockchain")
        data = response.json()
        blocks = data['chain']
        
        print(f"📊 Blockchain Summary ({node_url})")
        print("=" * 50)
        print(f"Total blocks: {len(blocks)}")
        print()
        
        print("📋 Block Details:")
        for i, block in enumerate(blocks):
            # Extract miner
            try:
                miner = block['transactions'][0]['outputs'][0]['recipient_address']
                miner_short = miner[:20] + "..." if len(miner) > 20 else miner
            except:
                miner_short = "unknown"
            
            # Check hash validity
            required_zeros = "0" * block['target_difficulty']
            hash_valid = "✅" if block['hash'].startswith(required_zeros) else "❌"
            
            # Check previous hash link
            if i == 0:
                prev_valid = "✅" if block['previous_hash'] == "0" * 64 else "❌"
                prev_check = "Genesis"
            else:
                prev_valid = "✅" if block['previous_hash'] == blocks[i-1]['hash'] else "❌"
                prev_check = "Links correctly"
            
            print(f"Block #{block['index']:2d}: Miner={miner_short} | Hash={hash_valid} | PrevLink={prev_valid} ({prev_check})")
        
        # Mining distribution
        print("\n⛏️  Mining Distribution:")
        miners = {}
        for block in blocks:
            try:
                miner = block['transactions'][0]['outputs'][0]['recipient_address']
                miners[miner] = miners.get(miner, 0) + 1
            except:
                miners['unknown'] = miners.get('unknown', 0) + 1
        
        for miner, count in miners.items():
            miner_short = miner[:30] + "..." if len(miner) > 30 else miner
            percentage = (count / len(blocks)) * 100
            print(f"  {miner_short}: {count} blocks ({percentage:.1f}%)")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def check_hash_chain(node_url="http://localhost:5000"):
    """Check hash chain integrity"""
    try:
        response = requests.get(f"{node_url}/blockchain")
        data = response.json()
        blocks = data['chain']
        
        print(f"🔗 Hash Chain Verification ({node_url})")
        print("=" * 40)
        
        issues = 0
        
        for i in range(len(blocks)):
            block = blocks[i]
            
            # Check hash difficulty
            required_zeros = "0" * block['target_difficulty']
            if not block['hash'].startswith(required_zeros):
                print(f"❌ Block #{i}: Hash doesn't meet difficulty {block['target_difficulty']}")
                print(f"   Hash: {block['hash'][:40]}...")
                issues += 1
            
            # Check previous hash link
            if i == 0:
                if block['previous_hash'] != "0" * 64:
                    print(f"❌ Block #{i}: Genesis block has wrong previous_hash")
                    issues += 1
            else:
                if block['previous_hash'] != blocks[i-1]['hash']:
                    print(f"❌ Block #{i}: Previous hash mismatch")
                    print(f"   Expected: {blocks[i-1]['hash']}")
                    print(f"   Actual:   {block['previous_hash']}")
                    issues += 1
            
            # Check index sequence
            if block['index'] != i:
                print(f"❌ Block #{i}: Index mismatch (expected {i}, got {block['index']})")
                issues += 1
        
        if issues == 0:
            print("✅ Perfect hash chain - all blocks properly linked!")
            print(f"   • {len(blocks)} blocks verified")
            print("   • All hashes meet difficulty requirements")
            print("   • All previous_hash links are correct")
        else:
            print(f"❌ {issues} issues found in hash chain")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def compare_nodes(url1="http://localhost:5000", url2="http://localhost:5001"):
    """Compare blockchain state between two nodes"""
    try:
        print(f"🔍 Comparing Nodes")
        print("=" * 30)
        print(f"Node 1: {url1}")
        print(f"Node 2: {url2}")
        print()
        
        # Get data from both nodes
        resp1 = requests.get(f"{url1}/blockchain")
        resp2 = requests.get(f"{url2}/blockchain")
        
        data1 = resp1.json()
        data2 = resp2.json()
        
        blocks1 = data1['chain']
        blocks2 = data2['chain']
        
        print(f"📊 Block counts: {len(blocks1)} vs {len(blocks2)}")
        
        # Compare up to shortest chain
        min_len = min(len(blocks1), len(blocks2))
        differences = 0
        
        for i in range(min_len):
            if blocks1[i]['hash'] != blocks2[i]['hash']:
                differences += 1
                print(f"❌ Block #{i} differs:")
                print(f"   Node 1 hash: {blocks1[i]['hash'][:40]}...")
                print(f"   Node 2 hash: {blocks2[i]['hash'][:40]}...")
        
        if differences == 0:
            if len(blocks1) == len(blocks2):
                print("✅ Nodes are perfectly synchronized!")
            else:
                print(f"✅ Synchronized up to block #{min_len-1}")
                longer_node = "Node 1" if len(blocks1) > len(blocks2) else "Node 2"
                print(f"📊 {longer_node} has {abs(len(blocks1) - len(blocks2))} additional blocks")
        else:
            print(f"❌ {differences} differences found - nodes are not synchronized!")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    if len(sys.argv) < 2:
        print("Quick Blockchain Verification Commands:")
        print("  python3 quick_blockchain_check.py summary [node_url]")
        print("  python3 quick_blockchain_check.py hashchain [node_url]") 
        print("  python3 quick_blockchain_check.py compare [url1] [url2]")
        print()
        print("Examples:")
        print("  python3 quick_blockchain_check.py summary")
        print("  python3 quick_blockchain_check.py hashchain http://localhost:5001")
        print("  python3 quick_blockchain_check.py compare http://localhost:5000 http://localhost:5001")
        return
    
    command = sys.argv[1]
    
    if command == "summary":
        node_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:5000"
        check_blocks_and_miners(node_url)
    
    elif command == "hashchain":
        node_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:5000"
        check_hash_chain(node_url)
    
    elif command == "compare":
        url1 = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:5000"
        url2 = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:5001"
        compare_nodes(url1, url2)

if __name__ == "__main__":
    main()