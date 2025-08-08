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
        self.current_hash_rate = 0
        self.total_hashes = 0
        self.start_time = 0
        self.last_hash_rate_update = 0
    
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
        """Legacy mine_block method - redirects to timeout version"""
        return self.mine_block_with_timeout(block_template, target_difficulty, timeout=120)
    
    def submit_block(self, mined_block: Dict) -> bool:
        """Legacy submit_block method - redirects to validation version"""
        return self.submit_block_with_validation(mined_block)
    
    def check_network_health(self) -> bool:
        """Check if network is stable before mining"""
        try:
            response = requests.get(f"{self.node_url}/status", timeout=5)
            if response.status_code != 200:
                print("⚠️  Node not responding")
                return False
            
            status = response.json()
            
            # Check if node has peers
            if status.get('peers', 0) == 0:
                print("⚠️  Node has no peers - network isolated")
                return False
            
            # Check if blockchain is growing (has more than genesis)
            if status.get('blockchain_length', 0) < 1:
                print("⚠️  Blockchain not initialized")
                return False
                
            return True
            
        except Exception as e:
            print(f"⚠️  Network health check failed: {e}")
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
        """Start mining loop with intelligent retry and refresh logic"""
        self.is_mining = True
        self.start_time = time.time()
        
        print(f"🚀 Starting mining for address: {self.wallet_address}")
        print(f"🔗 Connected to node: {self.node_url}")
        
        try:
            while self.is_mining:
                # Check network health before mining
                if not self.check_network_health():
                    print("⏳ Waiting for network to stabilize...")
                    time.sleep(10)
                    continue
                
                success = self.mine_with_retry()
                if success:
                    self.blocks_mined += 1
                    print(f"🎉 Total blocks mined: {self.blocks_mined}")
                    # Brief pause after successful mining
                    time.sleep(1)
                else:
                    # Longer pause after failures to let network stabilize
                    print("⏳ Network issues detected, waiting...")
                    time.sleep(5)
                
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
    
    def mine_with_retry(self, max_retries=3):
        """Mine with intelligent retry logic to handle stale templates"""
        for attempt in range(max_retries):
            try:
                # Get fresh block template for each attempt
                template_response = self.get_block_template()
                if not template_response:
                    print("⏳ Waiting for block template...")
                    time.sleep(5)
                    continue
                
                block_template = template_response['block_template']
                target_difficulty = template_response['target_difficulty']
                
                print(f"⛏️  Mining block {block_template['index']} (attempt {attempt + 1}/{max_retries})")
                
                # Mine the block with timeout
                mined_block = self.mine_block_with_timeout(block_template, target_difficulty, timeout=60)
                if not mined_block:
                    print("⏱️  Mining timed out, getting fresh template...")
                    continue
                
                # Submit mined block
                if self.submit_block_with_validation(mined_block):
                    print(f"✅ Block {mined_block['index']} successfully submitted!")
                    return True
                else:
                    print(f"❌ Attempt {attempt + 1} failed - block possibly stale")
                    if attempt < max_retries - 1:
                        print("🔄 Getting fresh template for retry...")
                        time.sleep(2)  # Brief pause before retry
                    
            except Exception as e:
                print(f"❌ Mining attempt {attempt + 1} error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        print(f"❌ All {max_retries} mining attempts failed")
        return False
    
    def mine_block_with_timeout(self, block_template: Dict, target_difficulty: int, timeout: int = 60) -> Optional[Dict]:
        """Mine a block with timeout to prevent infinite loops"""
        print(f"⛏️  Mining block {block_template['index']}...")
        print(f"   Target difficulty: {target_difficulty} leading zeros")
        print(f"   Transactions: {len(block_template['transactions'])}")
        print(f"   Timeout: {timeout} seconds")
        
        target = "0" * target_difficulty
        nonce = 0
        start_time = time.time()
        hash_count = 0
        
        # Reset hash count tracking for new mining attempt
        self._last_hash_count = 0
        
        while time.time() - start_time < timeout:
            if not self.is_mining:  # Check if mining was stopped
                print("🛑 Mining stopped")
                return None
                
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
                
                # Update total hash rate tracking
                self._update_hash_rate(hash_count, mining_time)
                
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
                remaining = timeout - elapsed
                
                # Update current hash rate periodically
                self._update_hash_rate(hash_count, elapsed)
                
                print(f"   Mining... Nonce: {nonce:,}, Rate: {rate:.0f} H/s, Remaining: {remaining:.0f}s")
        
        # Update hash rate for timeout case
        mining_time = time.time() - start_time
        self._update_hash_rate(hash_count, mining_time)
        
        print(f"⏱️  Mining timeout after {timeout} seconds")
        return None
    
    def submit_block_with_validation(self, mined_block: Dict) -> bool:
        """Submit mined block with enhanced error handling and validation"""
        try:
            response = requests.post(
                f"{self.node_url}/submit_block",
                json=mined_block,
                headers={
                    'Content-Type': 'application/json',
                    'X-Local-Mining': 'true'  # Mark as locally mined block
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Block submitted successfully!")
                print(f"   Status: {result['status']}")
                print(f"   Block hash: {result['block_hash']}")
                return True
            elif response.status_code == 400:
                error_info = response.json()
                print(f"❌ Block submission rejected: {error_info.get('error', 'Unknown error')}")
                
                # Check if it's a stale block error
                error_str = str(error_info).lower()
                if 'previous hash' in error_str or 'index' in error_str:
                    print("📄 Block is stale (blockchain moved forward during mining)")
                elif 'fork detected' in error_str or 'already exists' in error_str:
                    print("🍴 Fork detected or duplicate block (another miner won)")
                elif 'invalid transaction' in error_str:
                    print("💸 Transaction validation failed (possibly spent UTXOs)")
                else:
                    print(f"❌ Validation failed: {error_info}")
                    
                return False
            else:
                print(f"❌ Block submission failed with status {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            print("⏱️  Block submission timeout")
            return False
        except requests.exceptions.ConnectionError:
            print("🔌 Connection error during block submission")
            return False
        except Exception as e:
            print(f"❌ Error submitting block: {e}")
            return False
    
    def _update_hash_rate(self, hash_count: int, elapsed_time: float):
        """Update the total hash rate tracking"""
        if elapsed_time <= 0:
            return
            
        # Calculate current hash rate for this mining session
        self.current_hash_rate = hash_count / elapsed_time
        
        # Update total hashes (this should be cumulative across all mining attempts)
        # Only add new hashes since last update to avoid double counting
        if not hasattr(self, '_last_hash_count'):
            self._last_hash_count = 0
            
        new_hashes = hash_count - self._last_hash_count
        if new_hashes > 0:
            self.total_hashes += new_hashes
            self._last_hash_count = hash_count
        else:
            # Reset for new mining attempt
            self.total_hashes += hash_count
            self._last_hash_count = hash_count
        
        # Calculate overall average hash rate since mining started
        if self.start_time > 0:
            total_mining_time = time.time() - self.start_time
            if total_mining_time > 0:
                self.total_hash_rate = self.total_hashes / total_mining_time
            else:
                # For very short time periods, use current hash rate
                self.total_hash_rate = self.current_hash_rate
        
        self.last_hash_rate_update = time.time()
    
    def get_detailed_stats(self) -> Dict:
        """Get detailed mining statistics including hash rates"""
        basic_stats = self.get_mining_stats()
        
        return {
            **basic_stats,
            'current_hash_rate': self.current_hash_rate,
            'total_hashes': self.total_hashes,
            'last_update': self.last_hash_rate_update,
            'miner_address': self.wallet_address  # Ensure miner_address is included
        }

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
        stats = miner.get_detailed_stats()
        print(f"📊 Mining Stats:")
        print(f"   Blocks mined: {stats['blocks_mined']}")
        print(f"   Mining status: {'Active' if stats['is_mining'] else 'Inactive'}")
        print(f"   Total hash rate: {stats['estimated_hash_rate']:.2f} H/s")
        print(f"   Current hash rate: {stats['current_hash_rate']:.2f} H/s")
        print(f"   Total hashes: {stats['total_hashes']:,}")
        print(f"   Total time: {stats['total_time']:.2f}s")
        print(f"   Average block time: {stats['average_block_time']:.2f}s")
        print(f"   Miner address: {stats['miner_address']}")
    else:
        print(f"🎯 Mining for address: {args.wallet}")
        print(f"🔗 Node: {args.node}")
        print("Press Ctrl+C to stop mining")
        print("-" * 40)
        
        miner.start_mining()

if __name__ == '__main__':
    main()