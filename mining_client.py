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
        """Enhanced network health check with peer connectivity validation"""
        try:
            response = requests.get(f"{self.node_url}/status", timeout=10)
            if response.status_code != 200:
                print(f"⚠️  Node not responding (HTTP {response.status_code})")
                return False
            
            status = response.json()
            
            # Check if blockchain is initialized (has at least genesis block)
            blockchain_length = status.get('blockchain_length', 0)
            if blockchain_length < 1:
                print("⚠️  Blockchain not initialized - waiting for genesis block")
                return False
            
            # Check thread safety status
            if not status.get('thread_safe', False):
                print("⚠️  Node thread safety issues detected")
                return False
                
            # Check peer connectivity for better mining coordination
            peer_count = status.get('peers', 0)
            if peer_count == 0:
                print("ℹ️  Single node mode - no peers connected")
            else:
                print(f"🌐 Connected to {peer_count} peers")
                
            print(f"✅ Network healthy - Chain length: {blockchain_length}")
            return True
            
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to node at {self.node_url}")
            print("   💡 Make sure the network node is running")
            return False
        except requests.exceptions.Timeout:
            print(f"⏰ Node timeout at {self.node_url}")
            return False
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
        
        print("=" * 60)
        print("⛏️  ChainCore Mining Client Started")
        print("=" * 60)
        print(f"💰 Mining Address: {self.wallet_address}")
        print(f"🌐 Network Node: {self.node_url}")
        print(f"📊 Session Start: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("🎯 Mining Strategy: Automatic retry with fresh templates")
        print("⚡ Performance: Progress updates every 100,000 hashes")
        print("-" * 60)
        
        try:
            while self.is_mining:
                # Check network health before mining
                if not self.check_network_health():
                    print("⚠️  Network Health Check Failed")
                    print("   🔍 Issues detected:")
                    print("      • Node not responding")
                    print("      • Blockchain not initialized")
                    print("   ⏳ Waiting 10 seconds for network to stabilize...")
                    time.sleep(10)
                    continue
                
                success = self.mine_with_retry()
                if success:
                    self.blocks_mined += 1
                    session_time = time.time() - self.start_time
                    avg_time = session_time / self.blocks_mined
                    print("🎉 BLOCK SUCCESSFULLY MINED!")
                    print(f"   📊 Session Stats:")
                    print(f"      Total Blocks: {self.blocks_mined}")
                    print(f"      Session Time: {session_time:.1f}s")
                    print(f"      Average per Block: {avg_time:.1f}s")
                    print(f"      Hash Rate: {self.current_hash_rate:.0f} H/s")
                    print("   ⚡ Getting next block template...")
                    # Brief pause after successful mining
                    time.sleep(1)
                else:
                    # Longer pause after failures to let network stabilize
                    print("❌ Mining Attempt Failed")
                    print("   🔍 Possible causes:")
                    print("      • Stale block template")
                    print("      • Network connectivity issues") 
                    print("      • Another miner found block first")
                    print("   ⏳ Waiting 5 seconds before retry...")
                    time.sleep(5)
                
        except KeyboardInterrupt:
            print("\n" + "=" * 60)
            print("🛑 Mining Session Stopped by User")
            print("=" * 60)
        except Exception as e:
            print(f"\n❌ Critical Mining Error: {e}")
            print("   🔍 Please check network connectivity and try again")
        finally:
            self.is_mining = False
            
            # Print final stats
            stats = self.get_mining_stats()
            end_time = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n📊 Mining Session Summary")
            print("=" * 40)
            print(f"   Session End: {end_time}")
            print(f"   💎 Blocks Mined: {stats['blocks_mined']}")
            print(f"   ⏱️  Total Time: {stats['total_time']:.1f} seconds")
            print(f"   ⚡ Average Block Time: {stats['average_block_time']:.1f}s")
            print(f"   🔥 Hash Rate: {stats['estimated_hash_rate']:.0f} H/s")
            if stats['blocks_mined'] > 0:
                earnings = stats['blocks_mined'] * 50.0  # Assuming 50 CC per block
                print(f"   💰 Estimated Earnings: {earnings:.1f} CC")
            print("=" * 40)
    
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
                
                print(f"⛏️  Mining Block #{block_template['index']}")
                print(f"   🎯 Attempt: {attempt + 1}/{max_retries}")
                print(f"   💎 Difficulty: {target_difficulty} leading zeros")
                print(f"   📝 Transactions: {len(block_template['transactions'])}")
                print(f"   ⏱️  Timeout: 60 seconds")
                
                # Mine the block with timeout
                mined_block = self.mine_block_with_timeout(block_template, target_difficulty, timeout=60)
                if not mined_block:
                    print("⏱️  Mining timed out, getting fresh template...")
                    continue
                
                # Submit mined block
                if self.submit_block_with_validation(mined_block):
                    print(f"🎉 Block #{mined_block['index']} Successfully Submitted!")
                    print(f"   📋 Hash: {mined_block['hash'][:16]}...{mined_block['hash'][-8:]}")
                    print(f"   🎲 Nonce: {mined_block['nonce']:,}")
                    return True
                else:
                    print(f"❌ Attempt {attempt + 1} Failed")
                    print("   🔍 Block rejected by network (possibly stale or duplicate)")
                    if attempt < max_retries - 1:
                        print("   🔄 Getting fresh block template for retry...")
                        time.sleep(2)  # Brief pause before retry
                    
            except Exception as e:
                print(f"❌ Mining attempt {attempt + 1} error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        print(f"❌ All {max_retries} mining attempts failed")
        return False
    
    def mine_block_with_timeout(self, block_template: Dict, target_difficulty: int, timeout: int = 60) -> Optional[Dict]:
        """Mine a block with timeout to prevent infinite loops"""
        target = "0" * target_difficulty
        
        print(f"🔥 Starting Proof-of-Work Mining...")
        print(f"   🎯 Target: {target} (difficulty {target_difficulty})")
        print(f"   📦 Block Size: {len(block_template['transactions'])} transactions")
        print("   ⚡ Mining in progress...")
        nonce = 0
        start_time = time.time()
        hash_count = 0
        
        # Reset hash count tracking for new mining attempt
        self._last_hash_count = 0
        
        # Preserve mining metadata from block template
        mining_metadata = block_template.get('mining_metadata', {})
        mining_node = block_template.get('mining_node', 'unknown')
        
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
                
                print(f"💎 PROOF-OF-WORK FOUND!")
                print(f"   🏆 Valid Hash: {block_hash}")
                print(f"   🎲 Winning Nonce: {nonce:,}")
                print(f"   ⏱️  Mining Time: {mining_time:.2f} seconds")
                print(f"   🔥 Hash Rate: {hash_rate:.0f} H/s")
                print("   📤 Submitting to network...")
                
                # Preserve all original block template data including mining metadata
                block_template['hash'] = block_hash
                
                # Ensure mining metadata is preserved in the final block
                if mining_metadata:
                    block_template['mining_metadata'] = mining_metadata
                if mining_node != 'unknown':
                    block_template['mining_node'] = mining_node
                
                return block_template
            
            nonce += 1
            
            # Progress update every 100,000 hashes
            if nonce % 100000 == 0:
                elapsed = time.time() - start_time
                rate = hash_count / elapsed if elapsed > 0 else 0
                remaining = timeout - elapsed
                
                # Update current hash rate periodically
                self._update_hash_rate(hash_count, elapsed)
                
                print(f"   ⚡ Progress: Nonce {nonce:,} | Rate: {rate:.0f} H/s | Time Left: {remaining:.0f}s")
        
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
                status = result.get('status', 'unknown')
                
                if status == 'accepted':
                    block_hash = result.get('block_hash', 'unknown')
                    chain_length = result.get('chain_length', 'unknown')
                    mining_source = result.get('mining_source', 'unknown')
                    
                    print(f"✅ BLOCK ACCEPTED by network!")
                    print(f"   📋 Block Hash: {block_hash[:32]}...")
                    print(f"   📊 Block Index: {mined_block['index']}")
                    print(f"   📈 Chain Length: {chain_length}")
                    print(f"   🏭 Source: {mining_source}")
                    return True
                else:
                    error_msg = result.get('error', 'Unknown error')
                    print(f"❌ BLOCK REJECTED: {error_msg}")
                    return False
                    
            elif response.status_code == 409:
                # Conflict - block already exists (race condition)
                result = response.json()
                error_msg = result.get('error', 'Block conflict')
                reason = result.get('reason', 'conflict')
                
                print(f"🏁 MINING RACE LOST: {error_msg}")
                print(f"   ⚡ Another miner submitted this block first")
                print(f"   🎯 Reason: {reason}")
                return False
                
            elif response.status_code == 400:
                error_info = response.json()
                error_msg = error_info.get('error', 'Unknown error')
                reason = error_info.get('reason', 'validation_failed')
                
                print(f"❌ BLOCK VALIDATION FAILED: {error_msg}")
                print(f"   🔍 Reason: {reason}")
                
                # Enhanced error handling for specific cases
                if reason == 'invalid_block_data':
                    print("   💾 Block data structure is invalid")
                elif 'previous hash' in error_msg.lower():
                    print("   📄 Block is stale (blockchain moved forward during mining)")
                elif 'transaction' in error_msg.lower():
                    print("   💸 Transaction validation failed (possibly spent UTXOs)")
                
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
    parser = argparse.ArgumentParser(description='ChainCore Mining Client')
    parser.add_argument('--wallet', '-w', required=True, help='Miner wallet address')
    parser.add_argument('--node', '-n', default='http://localhost:5000', help='Node URL')
    parser.add_argument('--stats', action='store_true', help='Show mining stats and exit')
    parser.add_argument('--quiet', action='store_true', help='Skip startup banner')
    
    args = parser.parse_args()
    
    # Show startup banner unless quiet mode
    if not args.quiet and not args.stats:
        try:
            from startup_banner import startup_mining_client
            startup_mining_client(args.wallet, args.node)
        except ImportError:
            print("⛏️  ChainCore Mining Client Starting...")
            print(f"   💰 Wallet: {args.wallet}")
            print(f"   🌐 Node: {args.node}")
    
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