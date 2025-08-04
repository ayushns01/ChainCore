#!/usr/bin/env python3
"""
ChainCore Mining Client - Proof-of-Work Block Mining
Connects to network nodes via API and mines new blocks
"""

import sys
import os
import json
import time
import hashlib
import argparse
import requests
from typing import Dict, Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.crypto.ecdsa_crypto import double_sha256

class MiningClient:
    def __init__(self, wallet_address: str, node_url: str = "http://localhost:5000"):
        self.wallet_address = wallet_address
        self.node_url = node_url
        self.is_mining = False
        self.blocks_mined = 0
        self.total_hash_rate = 0
        self.start_time = 0
    
    def get_block_template(self) -> Optional[Dict]:
        """Get block template from network node"""
        try:
            response = requests.post(
                f"{self.node_url}/mine_block",
                json={'miner_address': self.wallet_address},
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Failed to get block template: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting block template: {e}")
            return None
    
    def mine_block(self, block_template: Dict, target_difficulty: int) -> Optional[Dict]:
        """Mine a block using Proof of Work"""
        print(f"⛏️  Mining block {block_template['index']}...")
        print(f"   Target difficulty: {target_difficulty} leading zeros")
        print(f"   Transactions: {len(block_template['transactions'])}")
        
        target = "0" * target_difficulty
        nonce = 0
        start_time = time.time()
        hash_count = 0
        
        while True:
            # Update nonce
            block_template['nonce'] = nonce
            
            # Calculate hash
            block_data = {
                'index': block_template['index'],
                'previous_hash': block_template['previous_hash'],
                'merkle_root': block_template['merkle_root'],
                'timestamp': block_template['timestamp'],
                'nonce': nonce,
                'target_difficulty': target_difficulty
            }
            
            block_hash = double_sha256(json.dumps(block_data, sort_keys=True))
            hash_count += 1
            
            # Check if we found valid hash
            if block_hash.startswith(target):
                mining_time = time.time() - start_time
                hash_rate = hash_count / mining_time if mining_time > 0 else 0
                
                print(f"✅ Block mined!")
                print(f"   Hash: {block_hash}")
                print(f"   Nonce: {nonce}")
                print(f"   Time: {mining_time:.2f}s")
                print(f"   Hash rate: {hash_rate:.2f} H/s")
                
                block_template['hash'] = block_hash
                return block_template
            
            nonce += 1
            
            # Progress update every 100,000 hashes
            if nonce % 100000 == 0:
                elapsed = time.time() - start_time
                rate = hash_count / elapsed if elapsed > 0 else 0
                print(f"   Mining... Nonce: {nonce:,}, Rate: {rate:.0f} H/s, Hash: {block_hash[:10]}...")
            
            # Check if we should stop (in a real implementation, this would be more sophisticated)
            if not self.is_mining:
                print("🛑 Mining stopped")
                return None
    
    def submit_block(self, mined_block: Dict) -> bool:
        """Submit mined block to network"""
        try:
            response = requests.post(
                f"{self.node_url}/submit_block",
                json=mined_block,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Block submitted successfully!")
                print(f"   Status: {result['status']}")
                print(f"   Block hash: {result['block_hash']}")
                return True
            else:
                print(f"❌ Block submission failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error submitting block: {e}")
            return False
    
    def get_mining_stats(self) -> Dict:
        """Get mining statistics"""
        if self.start_time == 0:
            return {
                'is_mining': self.is_mining,
                'blocks_mined': 0,
                'total_time': 0,
                'average_block_time': 0,
                'estimated_hash_rate': 0
            }
        
        total_time = time.time() - self.start_time
        avg_block_time = total_time / self.blocks_mined if self.blocks_mined > 0 else 0
        
        return {
            'is_mining': self.is_mining,
            'blocks_mined': self.blocks_mined,
            'total_time': total_time,
            'average_block_time': avg_block_time,
            'estimated_hash_rate': self.total_hash_rate,
            'miner_address': self.wallet_address
        }
    
    def start_mining(self):
        """Start mining loop"""
        self.is_mining = True
        self.start_time = time.time()
        
        print(f"🚀 Starting mining for address: {self.wallet_address}")
        print(f"🔗 Connected to node: {self.node_url}")
        
        try:
            while self.is_mining:
                # Get block template
                template_response = self.get_block_template()
                if not template_response:
                    print("⏳ Waiting for block template...")
                    time.sleep(5)
                    continue
                
                block_template = template_response['block_template']
                target_difficulty = template_response['target_difficulty']
                
                # Mine the block
                mined_block = self.mine_block(block_template, target_difficulty)
                if not mined_block:
                    continue
                
                # Submit mined block
                if self.submit_block(mined_block):
                    self.blocks_mined += 1
                    print(f"🎉 Total blocks mined: {self.blocks_mined}")
                else:
                    print("❌ Block submission failed, continuing...")
                
                # Brief pause before next block
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Mining interrupted by user")
        except Exception as e:
            print(f"❌ Mining error: {e}")
        finally:
            self.is_mining = False
            
            # Print final stats
            stats = self.get_mining_stats()
            print(f"\n📊 Final Mining Stats:")
            print(f"   Blocks mined: {stats['blocks_mined']}")
            print(f"   Total time: {stats['total_time']:.2f}s")
            print(f"   Average block time: {stats['average_block_time']:.2f}s")

def main():
    parser = argparse.ArgumentParser(description='Bitcoin-style Mining Client')
    parser.add_argument('--wallet', '-w', required=True, help='Miner wallet address')
    parser.add_argument('--node', '-n', default='http://localhost:5000', help='Node URL')
    parser.add_argument('--stats', action='store_true', help='Show mining stats and exit')
    
    args = parser.parse_args()
    
    print("⛏️  Bitcoin-style Mining Client")
    print("=" * 40)
    
    miner = MiningClient(args.wallet, args.node)
    
    if args.stats:
        stats = miner.get_mining_stats()
        print(f"📊 Mining Stats:")
        print(f"   Blocks mined: {stats['blocks_mined']}")
        print(f"   Mining status: {'Active' if stats['is_mining'] else 'Inactive'}")
        print(f"   Miner address: {stats['miner_address']}")
    else:
        print(f"🎯 Mining for address: {args.wallet}")
        print(f"🔗 Node: {args.node}")
        print("Press Ctrl+C to stop mining")
        print("-" * 40)
        
        miner.start_mining()

if __name__ == '__main__':
    main()