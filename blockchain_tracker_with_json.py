#!/usr/bin/env python3
"""
ChainCore Blockchain Tracker with JSON Export
Comprehensive tracking and analysis with JSON output for storage and review
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Optional

class BlockchainTracker:
    def __init__(self, node_url: str = "http://localhost:5000"):
        self.node_url = node_url
        self.analysis_data = {}
        
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
    
    def get_node_status(self) -> Optional[Dict]:
        """Get node status information"""
        try:
            response = requests.get(f"{self.node_url}/status", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except requests.RequestException as e:
            return None
    
    def extract_miner_from_block(self, block: Dict) -> str:
        """Extract miner address from block's coinbase transaction"""
        try:
            coinbase_tx = block['transactions'][0]
            if coinbase_tx['outputs']:
                return coinbase_tx['outputs'][0]['recipient_address']
            return "unknown"
        except (KeyError, IndexError):
            return "unknown"
    
    def analyze_block_details(self, block: Dict, previous_block: Optional[Dict] = None) -> Dict:
        """Analyze detailed block information"""
        miner = self.extract_miner_from_block(block)
        
        # Hash validation
        required_zeros = "0" * block['target_difficulty']
        hash_meets_difficulty = block['hash'].startswith(required_zeros)
        
        # Previous hash validation
        if previous_block:
            prev_hash_correct = block['previous_hash'] == previous_block['hash']
        else:
            # Genesis block
            prev_hash_correct = block['previous_hash'] == "0" * 64
        
        # Index validation
        expected_index = previous_block['index'] + 1 if previous_block else 0
        index_correct = block['index'] == expected_index
        
        # Mining reward calculation
        mining_reward = 0.0
        transaction_fees = 0.0
        try:
            coinbase_tx = block['transactions'][0]
            if coinbase_tx['outputs']:
                mining_reward = coinbase_tx['outputs'][0]['amount']
            
            # Calculate fees from non-coinbase transactions
            for tx in block['transactions'][1:]:
                # This is a simplified fee calculation
                input_sum = len(tx['inputs']) * 0.1  # Placeholder
                output_sum = sum(output['amount'] for output in tx['outputs'])
                if input_sum > output_sum:
                    transaction_fees += input_sum - output_sum
        except (KeyError, IndexError):
            pass
        
        return {
            "block_index": block['index'],
            "block_hash": block['hash'],
            "previous_hash": block['previous_hash'],
            "miner_address": miner,
            "timestamp": block['timestamp'],
            "human_time": datetime.fromtimestamp(block['timestamp']).strftime("%Y-%m-%d %H:%M:%S"),
            "target_difficulty": block['target_difficulty'],
            "nonce": block['nonce'],
            "transaction_count": len(block['transactions']),
            "mining_reward": mining_reward,
            "transaction_fees": transaction_fees,
            "total_reward": mining_reward + transaction_fees,
            "validation": {
                "hash_meets_difficulty": hash_meets_difficulty,
                "previous_hash_correct": prev_hash_correct,
                "index_correct": index_correct,
                "required_hash_prefix": required_zeros,
                "actual_hash_prefix": block['hash'][:block['target_difficulty']]
            }
        }
    
    def analyze_mining_distribution(self, blocks: List[Dict]) -> Dict:
        """Analyze mining distribution across all miners"""
        miner_stats = {}
        
        for block in blocks:
            miner = self.extract_miner_from_block(block)
            
            if miner not in miner_stats:
                miner_stats[miner] = {
                    "blocks_mined": 0,
                    "block_indices": [],
                    "total_rewards": 0.0,
                    "first_block_index": block['index'],
                    "last_block_index": block['index'],
                    "average_difficulty": 0.0
                }
            
            stats = miner_stats[miner]
            stats['blocks_mined'] += 1
            stats['block_indices'].append(block['index'])
            stats['last_block_index'] = block['index']
            
            # Calculate rewards
            try:
                coinbase_tx = block['transactions'][0]
                if coinbase_tx['outputs']:
                    stats['total_rewards'] += coinbase_tx['outputs'][0]['amount']
            except (KeyError, IndexError):
                pass
        
        # Calculate percentages and averages
        total_blocks = len(blocks)
        for miner, stats in miner_stats.items():
            stats['percentage'] = (stats['blocks_mined'] / total_blocks * 100) if total_blocks > 0 else 0
            stats['average_reward_per_block'] = stats['total_rewards'] / stats['blocks_mined'] if stats['blocks_mined'] > 0 else 0
        
        return miner_stats
    
    def verify_hash_chain_integrity(self, blocks: List[Dict]) -> Dict:
        """Comprehensive hash chain integrity verification"""
        integrity_report = {
            "total_blocks": len(blocks),
            "valid_blocks": 0,
            "invalid_blocks": 0,
            "issues": [],
            "overall_status": "unknown"
        }
        
        for i, block in enumerate(blocks):
            block_valid = True
            block_issues = []
            
            # Check hash difficulty
            required_zeros = "0" * block['target_difficulty']
            if not block['hash'].startswith(required_zeros):
                block_valid = False
                block_issues.append({
                    "type": "invalid_difficulty",
                    "description": f"Hash doesn't meet difficulty requirement",
                    "expected_prefix": required_zeros,
                    "actual_prefix": block['hash'][:block['target_difficulty']]
                })
            
            # Check previous hash linkage
            if i == 0:
                # Genesis block
                if block['previous_hash'] != "0" * 64:
                    block_valid = False
                    block_issues.append({
                        "type": "invalid_genesis_prev_hash",
                        "description": "Genesis block should have previous_hash of all zeros",
                        "expected": "0" * 64,
                        "actual": block['previous_hash']
                    })
            else:
                # Regular block
                expected_prev_hash = blocks[i-1]['hash']
                if block['previous_hash'] != expected_prev_hash:
                    block_valid = False
                    block_issues.append({
                        "type": "broken_hash_chain",
                        "description": f"Previous hash doesn't match previous block's hash",
                        "expected": expected_prev_hash,
                        "actual": block['previous_hash']
                    })
            
            # Check index sequence
            expected_index = i
            if block['index'] != expected_index:
                block_valid = False
                block_issues.append({
                    "type": "invalid_index",
                    "description": f"Block index out of sequence",
                    "expected": expected_index,
                    "actual": block['index']
                })
            
            if block_valid:
                integrity_report['valid_blocks'] += 1
            else:
                integrity_report['invalid_blocks'] += 1
                integrity_report['issues'].append({
                    "block_index": block['index'],
                    "block_hash": block['hash'][:32] + "...",
                    "issues": block_issues
                })
        
        # Overall status
        if integrity_report['invalid_blocks'] == 0:
            integrity_report['overall_status'] = "perfect"
        elif integrity_report['invalid_blocks'] < integrity_report['total_blocks'] * 0.1:
            integrity_report['overall_status'] = "minor_issues"
        else:
            integrity_report['overall_status'] = "major_issues"
        
        return integrity_report
    
    def full_blockchain_analysis(self) -> Dict:
        """Perform comprehensive blockchain analysis"""
        print("🔍 Performing comprehensive blockchain analysis...")
        
        # Get blockchain data
        blockchain_data = self.get_blockchain_data()
        if not blockchain_data:
            return {"error": "Could not retrieve blockchain data"}
        
        # Get node status
        node_status = self.get_node_status()
        
        blocks = blockchain_data['chain']
        
        print(f"📊 Analyzing {len(blocks)} blocks...")
        
        # Analyze each block in detail
        detailed_blocks = []
        for i, block in enumerate(blocks):
            previous_block = blocks[i-1] if i > 0 else None
            block_analysis = self.analyze_block_details(block, previous_block)
            detailed_blocks.append(block_analysis)
        
        print("⛏️ Analyzing mining distribution...")
        # Mining distribution analysis
        mining_distribution = self.analyze_mining_distribution(blocks)
        
        print("🔗 Verifying hash chain integrity...")
        # Hash chain integrity verification
        integrity_report = self.verify_hash_chain_integrity(blocks)
        
        # Compile comprehensive analysis
        analysis = {
            "analysis_metadata": {
                "timestamp": datetime.now().isoformat(),
                "node_url": self.node_url,
                "analyzer_version": "1.0.0",
                "total_blocks_analyzed": len(blocks)
            },
            "node_status": node_status,
            "blockchain_summary": {
                "total_blocks": len(blocks),
                "genesis_block_hash": blocks[0]['hash'] if blocks else None,
                "latest_block_hash": blocks[-1]['hash'] if blocks else None,
                "latest_block_index": blocks[-1]['index'] if blocks else None,
                "difficulty_range": {
                    "min": min(block['target_difficulty'] for block in blocks) if blocks else None,
                    "max": max(block['target_difficulty'] for block in blocks) if blocks else None,
                    "current": blocks[-1]['target_difficulty'] if blocks else None
                },
                "time_range": {
                    "genesis_time": datetime.fromtimestamp(blocks[0]['timestamp']).isoformat() if blocks else None,
                    "latest_time": datetime.fromtimestamp(blocks[-1]['timestamp']).isoformat() if blocks else None,
                    "total_duration_seconds": blocks[-1]['timestamp'] - blocks[0]['timestamp'] if len(blocks) > 1 else 0
                }
            },
            "detailed_blocks": detailed_blocks,
            "mining_distribution": mining_distribution,
            "hash_chain_integrity": integrity_report,
            "statistics": {
                "total_transactions": sum(len(block['transactions']) for block in blocks),
                "total_mining_rewards": sum(
                    self.analyze_block_details(block)['mining_reward'] 
                    for block in blocks
                ),
                "average_block_time": (
                    (blocks[-1]['timestamp'] - blocks[0]['timestamp']) / (len(blocks) - 1)
                    if len(blocks) > 1 else 0
                ),
                "unique_miners": len(mining_distribution),
                "most_productive_miner": max(
                    mining_distribution.items(), 
                    key=lambda x: x[1]['blocks_mined']
                )[0] if mining_distribution else None
            }
        }
        
        self.analysis_data = analysis
        return analysis
    
    def save_to_json(self, filename: str = None) -> str:
        """Save analysis to JSON file"""
        if not self.analysis_data:
            print("❌ No analysis data to save. Run full_blockchain_analysis() first.")
            return ""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"blockchain_analysis_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.analysis_data, f, indent=2, default=str)
            
            print(f"✅ Analysis saved to: {filename}")
            return filename
        except Exception as e:
            print(f"❌ Error saving to JSON: {e}")
            return ""
    
    def display_summary(self):
        """Display human-readable summary of analysis"""
        if not self.analysis_data:
            print("❌ No analysis data available")
            return
        
        data = self.analysis_data
        
        print("\n" + "="*60)
        print("🔍 CHAINCORE BLOCKCHAIN ANALYSIS SUMMARY")
        print("="*60)
        
        # Basic info
        meta = data['analysis_metadata']
        print(f"📅 Analysis Time: {meta['timestamp']}")
        print(f"🌐 Node URL: {meta['node_url']}")
        print(f"📊 Blocks Analyzed: {meta['total_blocks_analyzed']}")
        
        # Blockchain summary
        summary = data['blockchain_summary']
        print(f"\n📦 BLOCKCHAIN OVERVIEW:")
        print(f"   Total Blocks: {summary['total_blocks']}")
        print(f"   Current Difficulty: {summary['difficulty_range']['current']}")
        print(f"   Latest Block: #{summary['latest_block_index']}")
        print(f"   Genesis Time: {summary['time_range']['genesis_time']}")
        print(f"   Latest Time: {summary['time_range']['latest_time']}")
        
        # Mining distribution
        print(f"\n⛏️ MINING DISTRIBUTION:")
        mining = data['mining_distribution']
        for miner, stats in sorted(mining.items(), key=lambda x: x[1]['blocks_mined'], reverse=True):
            miner_short = miner[:40] + "..." if len(miner) > 40 else miner
            print(f"   {miner_short}")
            print(f"      Blocks: {stats['blocks_mined']} ({stats['percentage']:.1f}%)")
            print(f"      Rewards: {stats['total_rewards']}")
            print(f"      Block Range: #{stats['first_block_index']} → #{stats['last_block_index']}")
        
        # Hash chain integrity
        print(f"\n🔗 HASH CHAIN INTEGRITY:")
        integrity = data['hash_chain_integrity']
        print(f"   Status: {integrity['overall_status'].upper()}")
        print(f"   Valid Blocks: {integrity['valid_blocks']}/{integrity['total_blocks']}")
        print(f"   Issues Found: {len(integrity['issues'])}")
        
        if integrity['issues']:
            print(f"   ⚠️ Issues:")
            for issue in integrity['issues'][:3]:  # Show first 3 issues
                print(f"      Block #{issue['block_index']}: {len(issue['issues'])} problems")
        
        # Statistics
        print(f"\n📈 STATISTICS:")
        stats = data['statistics']
        print(f"   Total Transactions: {stats['total_transactions']}")
        print(f"   Total Mining Rewards: {stats['total_mining_rewards']}")
        print(f"   Average Block Time: {stats['average_block_time']:.1f} seconds")
        print(f"   Unique Miners: {stats['unique_miners']}")
        print(f"   Most Productive: {stats['most_productive_miner'][:30]}..." if stats['most_productive_miner'] else "None")
        
        print("="*60)

def main():
    if len(sys.argv) < 2:
        print("ChainCore Blockchain Tracker with JSON Export")
        print("Usage:")
        print("  python3 blockchain_tracker_with_json.py analyze [node_url] [output_file]")
        print("  python3 blockchain_tracker_with_json.py quick [node_url]")
        print()
        print("Examples:")
        print("  python3 blockchain_tracker_with_json.py analyze")
        print("  python3 blockchain_tracker_with_json.py analyze http://localhost:5001")
        print("  python3 blockchain_tracker_with_json.py analyze http://localhost:5000 my_analysis.json")
        print("  python3 blockchain_tracker_with_json.py quick")
        return
    
    command = sys.argv[1]
    node_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:5000"
    
    tracker = BlockchainTracker(node_url)
    
    if command == "analyze":
        # Full analysis with JSON export
        output_file = sys.argv[3] if len(sys.argv) > 3 else None
        
        analysis = tracker.full_blockchain_analysis()
        if "error" not in analysis:
            tracker.display_summary()
            filename = tracker.save_to_json(output_file)
            
            if filename:
                print(f"\n💾 Complete analysis saved to: {filename}")
                print(f"📂 File size: {len(json.dumps(analysis, indent=2))} characters")
                print(f"🔍 View with: cat {filename} | python3 -m json.tool")
        else:
            print(f"❌ Analysis failed: {analysis['error']}")
    
    elif command == "quick":
        # Quick analysis without JSON save
        analysis = tracker.full_blockchain_analysis()
        if "error" not in analysis:
            tracker.display_summary()
        else:
            print(f"❌ Analysis failed: {analysis['error']}")

if __name__ == "__main__":
    main()