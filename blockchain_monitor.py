#!/usr/bin/env python3
"""
ChainCore Blockchain Monitor
Real-time tracking of block mining and hash chain integrity
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Optional

class BlockchainMonitor:
    def __init__(self, node_url: str = "http://localhost:5000"):
        self.node_url = node_url
        self.last_seen_length = 0
        self.block_history = []
        
    def get_blockchain_data(self) -> Optional[Dict]:
        """Get current blockchain data from node"""
        try:
            response = requests.get(f"{self.node_url}/blockchain", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ API Error: {response.status_code}")
                return None
        except requests.RequestException as e:
            print(f"❌ Connection Error: {e}")
            return None
    
    def extract_miner_from_block(self, block: Dict) -> str:
        """Extract miner address from block's coinbase transaction"""
        try:
            # First transaction should be coinbase
            coinbase_tx = block['transactions'][0]
            if coinbase_tx['outputs']:
                return coinbase_tx['outputs'][0]['recipient_address']
            return "unknown"
        except (KeyError, IndexError):
            return "unknown"
    
    def verify_hash_chain(self, blocks: List[Dict]) -> List[Dict]:
        """Verify the hash chain integrity and return issues"""
        issues = []
        
        for i in range(1, len(blocks)):
            current_block = blocks[i]
            previous_block = blocks[i-1]
            
            # Check if current block's previous_hash matches previous block's hash
            if current_block['previous_hash'] != previous_block['hash']:
                issues.append({
                    'type': 'hash_mismatch',
                    'block_index': current_block['index'],
                    'expected_prev_hash': previous_block['hash'],
                    'actual_prev_hash': current_block['previous_hash']
                })
            
            # Check if block index is sequential
            if current_block['index'] != previous_block['index'] + 1:
                issues.append({
                    'type': 'index_gap',
                    'block_index': current_block['index'],
                    'expected_index': previous_block['index'] + 1,
                    'actual_index': current_block['index']
                })
            
            # Check if hash starts with required zeros (difficulty)
            required_zeros = "0" * current_block['target_difficulty']
            if not current_block['hash'].startswith(required_zeros):
                issues.append({
                    'type': 'invalid_difficulty',
                    'block_index': current_block['index'],
                    'required_prefix': required_zeros,
                    'actual_hash': current_block['hash'][:20] + "..."
                })
        
        return issues
    
    def analyze_mining_distribution(self, blocks: List[Dict]) -> Dict:
        """Analyze which miners mined which blocks"""
        miner_stats = {}
        
        for block in blocks:
            miner = self.extract_miner_from_block(block)
            if miner not in miner_stats:
                miner_stats[miner] = {
                    'blocks_mined': 0,
                    'block_indices': [],
                    'total_rewards': 0.0,
                    'first_block': block['index'],
                    'last_block': block['index']
                }
            
            stats = miner_stats[miner]
            stats['blocks_mined'] += 1
            stats['block_indices'].append(block['index'])
            stats['last_block'] = block['index']
            
            # Calculate rewards from coinbase transaction
            try:
                coinbase_tx = block['transactions'][0]
                if coinbase_tx['outputs']:
                    stats['total_rewards'] += coinbase_tx['outputs'][0]['amount']
            except (KeyError, IndexError):
                pass
        
        return miner_stats
    
    def display_block_details(self, block: Dict, is_new: bool = False):
        """Display detailed block information"""
        miner = self.extract_miner_from_block(block)
        timestamp = datetime.fromtimestamp(block['timestamp']).strftime("%H:%M:%S")
        
        # Determine if hash meets difficulty requirement
        required_zeros = "0" * block['target_difficulty']
        hash_valid = "✅" if block['hash'].startswith(required_zeros) else "❌"
        
        status = "🆕 NEW" if is_new else "📦"
        
        print(f"{status} Block #{block['index']}")
        print(f"   ⛏️  Miner: {miner[:20]}...")
        print(f"   🕐 Time: {timestamp}")
        print(f"   🎯 Difficulty: {block['target_difficulty']} ({required_zeros})")
        print(f"   🔗 Hash: {block['hash'][:32]}... {hash_valid}")
        print(f"   ⬅️  Prev: {block['previous_hash'][:32]}...")
        print(f"   💰 Transactions: {len(block['transactions'])}")
        print(f"   🔢 Nonce: {block['nonce']}")
        
        # Show coinbase reward
        try:
            coinbase_tx = block['transactions'][0]
            if coinbase_tx['outputs']:
                reward = coinbase_tx['outputs'][0]['amount']
                print(f"   💵 Reward: {reward}")
        except (KeyError, IndexError):
            pass
        
        print()
    
    def display_mining_summary(self, miner_stats: Dict):
        """Display mining distribution summary"""
        print("⛏️  MINING DISTRIBUTION SUMMARY")
        print("=" * 50)
        
        total_blocks = sum(stats['blocks_mined'] for stats in miner_stats.values())
        
        for miner, stats in sorted(miner_stats.items(), key=lambda x: x[1]['blocks_mined'], reverse=True):
            percentage = (stats['blocks_mined'] / total_blocks * 100) if total_blocks > 0 else 0
            
            print(f"Miner: {miner[:30]}...")
            print(f"  📦 Blocks: {stats['blocks_mined']} ({percentage:.1f}%)")
            print(f"  💰 Rewards: {stats['total_rewards']}")
            print(f"  📊 Range: #{stats['first_block']} → #{stats['last_block']}")
            print(f"  🏷️  Blocks: {stats['block_indices']}")
            print()
    
    def display_hash_chain_status(self, issues: List[Dict]):
        """Display hash chain integrity status"""
        print("🔗 HASH CHAIN INTEGRITY")
        print("=" * 30)
        
        if not issues:
            print("✅ Perfect hash chain - no issues detected!")
            print("   • All previous_hash values match")
            print("   • All block indices are sequential")
            print("   • All hashes meet difficulty requirements")
        else:
            print(f"❌ {len(issues)} issues detected:")
            for issue in issues:
                if issue['type'] == 'hash_mismatch':
                    print(f"   🔗 Block #{issue['block_index']}: Hash mismatch")
                    print(f"      Expected: {issue['expected_prev_hash'][:32]}...")
                    print(f"      Actual:   {issue['actual_prev_hash'][:32]}...")
                elif issue['type'] == 'index_gap':
                    print(f"   📊 Block #{issue['block_index']}: Index gap")
                    print(f"      Expected: #{issue['expected_index']}")
                    print(f"      Actual:   #{issue['actual_index']}")
                elif issue['type'] == 'invalid_difficulty':
                    print(f"   🎯 Block #{issue['block_index']}: Invalid difficulty")
                    print(f"      Required: starts with '{issue['required_prefix']}'")
                    print(f"      Actual:   {issue['actual_hash']}")
        print()
    
    def monitor_realtime(self, interval: int = 3):
        """Monitor blockchain in real-time"""
        print("🚀 ChainCore Blockchain Real-Time Monitor")
        print("=" * 50)
        print(f"Monitoring node: {self.node_url}")
        print(f"Update interval: {interval} seconds")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                data = self.get_blockchain_data()
                if not data:
                    print("⏳ Waiting for node connection...")
                    time.sleep(interval)
                    continue
                
                blocks = data['chain']
                current_length = len(blocks)
                
                # Check for new blocks
                if current_length > self.last_seen_length:
                    # Show new blocks
                    for i in range(self.last_seen_length, current_length):
                        if i < len(blocks):
                            self.display_block_details(blocks[i], is_new=True)
                    
                    # Update tracking
                    self.last_seen_length = current_length
                    
                    # Show summaries every 5 blocks
                    if current_length % 5 == 0 and current_length > 0:
                        print("\n" + "=" * 60)
                        
                        # Mining distribution
                        miner_stats = self.analyze_mining_distribution(blocks)
                        self.display_mining_summary(miner_stats)
                        
                        # Hash chain integrity
                        issues = self.verify_hash_chain(blocks)
                        self.display_hash_chain_status(issues)
                        
                        print("=" * 60 + "\n")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped")
    
    def full_analysis(self):
        """Perform complete blockchain analysis"""
        print("📊 ChainCore Blockchain Full Analysis")
        print("=" * 50)
        
        data = self.get_blockchain_data()
        if not data:
            print("❌ Cannot connect to node")
            return
        
        blocks = data['chain']
        
        print(f"📦 Total blocks: {len(blocks)}")
        print(f"🔗 Node: {self.node_url}")
        print(f"🕐 Analysis time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Show all blocks
        print("📋 COMPLETE BLOCK LIST")
        print("-" * 30)
        for block in blocks:
            self.display_block_details(block)
        
        # Mining analysis
        miner_stats = self.analyze_mining_distribution(blocks)
        self.display_mining_summary(miner_stats)
        
        # Hash chain integrity
        issues = self.verify_hash_chain(blocks)
        self.display_hash_chain_status(issues)

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 blockchain_monitor.py monitor [node_url] [interval]  - Real-time monitoring")
        print("  python3 blockchain_monitor.py analyze [node_url]           - Full analysis")
        print("  python3 blockchain_monitor.py compare [url1] [url2]        - Compare two nodes")
        print()
        print("Examples:")
        print("  python3 blockchain_monitor.py monitor")
        print("  python3 blockchain_monitor.py monitor http://localhost:5001 2")
        print("  python3 blockchain_monitor.py analyze http://localhost:5000")
        print("  python3 blockchain_monitor.py compare http://localhost:5000 http://localhost:5001")
        return
    
    command = sys.argv[1]
    
    if command == "monitor":
        node_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:5000"
        interval = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        monitor = BlockchainMonitor(node_url)
        monitor.monitor_realtime(interval)
    
    elif command == "analyze":
        node_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:5000"
        monitor = BlockchainMonitor(node_url)
        monitor.full_analysis()
    
    elif command == "compare":
        url1 = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:5000"
        url2 = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:5001"
        
        print("🔍 Comparing two blockchain nodes")
        print("=" * 40)
        
        monitor1 = BlockchainMonitor(url1)
        monitor2 = BlockchainMonitor(url2)
        
        data1 = monitor1.get_blockchain_data()
        data2 = monitor2.get_blockchain_data()
        
        if data1 and data2:
            blocks1 = data1['chain']
            blocks2 = data2['chain']
            
            print(f"Node 1 ({url1}): {len(blocks1)} blocks")
            print(f"Node 2 ({url2}): {len(blocks2)} blocks")
            
            # Compare hash chains
            min_length = min(len(blocks1), len(blocks2))
            differences = 0
            
            for i in range(min_length):
                if blocks1[i]['hash'] != blocks2[i]['hash']:
                    differences += 1
                    print(f"❌ Block #{i} differs:")
                    print(f"   Node 1: {blocks1[i]['hash'][:32]}...")
                    print(f"   Node 2: {blocks2[i]['hash'][:32]}...")
            
            if differences == 0 and len(blocks1) == len(blocks2):
                print("✅ Nodes are perfectly synchronized!")
            elif differences == 0:
                print(f"✅ Synchronized up to block #{min_length-1}")
                print(f"📊 Length difference: {abs(len(blocks1) - len(blocks2))} blocks")
            else:
                print(f"❌ {differences} block differences detected!")
        else:
            print("❌ Could not connect to one or both nodes")

if __name__ == "__main__":
    main()