#!/usr/bin/env python3
"""
ChainCore Mining Summary Framework
Real-time monitoring and verification of blockchain mining activity across all nodes
"""

import requests
import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import concurrent.futures

@dataclass
class BlockSummary:
    """Summary information for a mined block"""
    index: int
    hash: str
    previous_hash: str
    miner_address: str
    node_source: str
    timestamp: float
    difficulty: int
    nonce: int
    transactions_count: int
    mining_time: Optional[float] = None
    verified: bool = False

@dataclass
class NodeMiningStats:
    """Mining statistics for a specific node"""
    node_url: str
    node_id: str
    node_source: str
    port: int
    blocks_mined: int
    last_block_time: Optional[float] = None
    mining_rate: float = 0.0  # blocks per minute
    total_mining_time: float = 0.0
    avg_mining_time: float = 0.0
    is_active: bool = True

class MiningSummaryFramework:
    """
    Framework for monitoring and summarizing blockchain mining activity
    Provides real-time insights into which nodes are mining and block verification
    """
    
    def __init__(self, discovery_start_port: int = 5000, discovery_end_port: int = 5100):
        self.discovery_start_port = discovery_start_port
        self.discovery_end_port = discovery_end_port
        
        # Core tracking data
        self.active_nodes: Set[str] = set()
        self.node_stats: Dict[str, NodeMiningStats] = {}
        self.block_summaries: List[BlockSummary] = []
        self.node_last_seen: Dict[str, int] = {}  # Track last seen block count per node
        
        # Threading
        self.lock = threading.RLock()
        self.running = False
        
        # Summary data
        self.total_blocks_tracked = 0
        self.start_time = time.time()
        
    def discover_active_nodes(self) -> Set[str]:
        """Discover all active ChainCore nodes in the network"""
        print(f"🔍 Scanning ports {self.discovery_start_port}-{self.discovery_end_port} for active nodes...")
        active_nodes = set()
        discovered_ports = []
        
        def check_node(port: int) -> Optional[str]:
            """Check if a node is active on given port"""
            node_url = f"http://localhost:{port}"
            try:
                response = requests.get(f"{node_url}/status", timeout=1)
                if response.status_code == 200:
                    return node_url
            except requests.RequestException:
                pass
            return None
        
        # Concurrent node discovery
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            port_range = range(self.discovery_start_port, self.discovery_end_port + 1)
            futures = [executor.submit(check_node, port) for port in port_range]
            
            # Use a shorter timeout and handle timeouts gracefully
            try:
                for future in concurrent.futures.as_completed(futures, timeout=5):
                    try:
                        result = future.result()
                        if result:
                            active_nodes.add(result)
                            port = int(result.split(':')[-1])
                            discovered_ports.append(port)
                    except Exception:
                        pass
            except concurrent.futures.TimeoutError:
                # Cancel remaining futures and collect any completed ones
                for future in futures:
                    if future.done():
                        try:
                            result = future.result()
                            if result:
                                active_nodes.add(result)
                                port = int(result.split(':')[-1])
                                discovered_ports.append(port)
                        except Exception:
                            pass
                    else:
                        future.cancel()
        
        # Show discovery results
        if discovered_ports:
            print(f"✅ Found {len(discovered_ports)} active nodes: {sorted(discovered_ports)}")
        else:
            print("⚠️  No active nodes found")
        
        return active_nodes
    
    def get_node_info(self, node_url: str) -> Optional[Dict]:
        """Get detailed information from a specific node"""
        try:
            # Get node status
            status_response = requests.get(f"{node_url}/status", timeout=5)
            blockchain_response = requests.get(f"{node_url}/blockchain", timeout=5)
            
            if status_response.status_code == 200 and blockchain_response.status_code == 200:
                status_data = status_response.json()
                blockchain_data = blockchain_response.json()
                
                return {
                    'status': status_data,
                    'blockchain': blockchain_data,
                    'node_url': node_url,
                    'port': int(node_url.split(':')[-1])
                }
        except requests.RequestException:
            pass
        return None
    
    def extract_miner_address(self, block: Dict) -> str:
        """Extract miner address from block's coinbase transaction"""
        try:
            coinbase_tx = block['transactions'][0]
            if coinbase_tx['outputs']:
                return coinbase_tx['outputs'][0]['recipient_address']
        except (KeyError, IndexError):
            pass
        return "unknown"
    
    def create_block_summary(self, block: Dict, node_url: str) -> BlockSummary:
        """Create a BlockSummary object from block data"""
        miner_address = self.extract_miner_address(block)
        port = int(node_url.split(':')[-1])
        
        return BlockSummary(
            index=block.get('index', -1),
            hash=block.get('hash', ''),
            previous_hash=block.get('previous_hash', ''),
            miner_address=miner_address,
            node_source=f"Node-{port}",
            timestamp=block.get('timestamp', 0),
            difficulty=block.get('target_difficulty', 0),
            nonce=block.get('nonce', 0),
            transactions_count=len(block.get('transactions', [])),
            verified=True  # Mark as verified since it's from node's blockchain
        )
    
    def update_node_stats(self, node_url: str, node_info: Dict, new_blocks: List[BlockSummary]):
        """Update mining statistics for a node"""
        status = node_info['status']
        port = node_info['port']
        
        # Initialize or update node stats
        if node_url not in self.node_stats:
            self.node_stats[node_url] = NodeMiningStats(
                node_url=node_url,
                node_id=status.get('node_id', f'core{port-5000}'),
                node_source=f"Node-{port}",
                port=port,
                blocks_mined=0
            )
        
        node_stat = self.node_stats[node_url]
        node_stat.is_active = True
        
        # Update mining statistics
        if new_blocks:
            node_stat.blocks_mined += len(new_blocks)
            node_stat.last_block_time = max(block.timestamp for block in new_blocks)
            
            # Calculate mining rate (blocks per minute)
            elapsed_time = (time.time() - self.start_time) / 60.0  # minutes
            if elapsed_time > 0:
                node_stat.mining_rate = node_stat.blocks_mined / elapsed_time
    
    def scan_all_nodes(self) -> Dict[str, List[BlockSummary]]:
        """Scan all active nodes and return new blocks found"""
        # Discover active nodes
        current_nodes = self.discover_active_nodes()
        
        with self.lock:
            self.active_nodes = current_nodes
        
        # Get data from all nodes
        new_blocks_by_node = {}
        
        def fetch_node_data(node_url: str) -> Tuple[str, Optional[Dict], List[BlockSummary]]:
            """Fetch data from a single node"""
            port = node_url.split(':')[-1]
            print(f"📡 Fetching blockchain data from Node-{port} ({node_url})")
            
            node_info = self.get_node_info(node_url)
            new_blocks = []
            
            if node_info:
                blockchain = node_info['blockchain']
                chain = blockchain.get('chain', [])
                
                # Track last seen count for this node
                last_seen = self.node_last_seen.get(node_url, 0)
                current_count = len(chain)
                
                print(f"   📊 Node-{port}: {current_count} blocks total, {current_count - last_seen} new")
                
                # Extract new blocks
                if current_count > last_seen:
                    for i in range(last_seen, current_count):
                        if i < len(chain):
                            block_summary = self.create_block_summary(chain[i], node_url)
                            new_blocks.append(block_summary)
                    
                    # Update tracking
                    self.node_last_seen[node_url] = current_count
            else:
                print(f"   ❌ Node-{port}: Failed to fetch data")
            
            return node_url, node_info, new_blocks
        
        # Fetch data from all nodes concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(fetch_node_data, node_url) 
                      for node_url in current_nodes]
            
            try:
                for future in concurrent.futures.as_completed(futures, timeout=10):
                    try:
                        node_url, node_info, new_blocks = future.result()
                        
                        if new_blocks:
                            new_blocks_by_node[node_url] = new_blocks
                            
                            # Update statistics
                            with self.lock:
                                self.block_summaries.extend(new_blocks)
                                self.total_blocks_tracked += len(new_blocks)
                        
                        if node_info:
                            self.update_node_stats(node_url, node_info, new_blocks)
                            
                    except Exception as e:
                        print(f"⚠️  Error processing data: {e}")
            except concurrent.futures.TimeoutError:
                print("⚠️  Some nodes took too long to respond, continuing with available data...")
                # Cancel remaining futures
                for future in futures:
                    if not future.done():
                        future.cancel()
        
        return new_blocks_by_node
    
    def display_new_blocks(self, new_blocks_by_node: Dict[str, List[BlockSummary]]):
        """Display newly discovered blocks"""
        for node_url, blocks in new_blocks_by_node.items():
            port = int(node_url.split(':')[-1])
            print(f"\n🆕 NEW BLOCKS from Node-{port} ({node_url}):")
            print("-" * 50)
            
            for block in blocks:
                timestamp_str = datetime.fromtimestamp(block.timestamp).strftime("%H:%M:%S")
                print(f"📦 Block #{block.index}")
                print(f"   ⛏️  Mined by: {block.node_source}")
                print(f"   📍 Miner Address: {block.miner_address[:30]}...")
                print(f"   🕐 Time: {timestamp_str}")
                print(f"   🔗 Hash: {block.hash[:32]}...")
                print(f"   ⬅️  Prev: {block.previous_hash[:32]}...")
                print(f"   🎯 Difficulty: {block.difficulty}")
                print(f"   🔢 Nonce: {block.nonce}")
                print(f"   💰 Transactions: {block.transactions_count}")
                print(f"   ✅ Verified: {block.verified}")
                print()
    
    def display_blockchain_chain(self):
        """Display the blockchain as a sequential chain showing which node mined each block"""
        if not self.block_summaries:
            print("📦 No blocks found in the blockchain yet")
            return
        
        # Sort all blocks by index to show the proper chain sequence
        sorted_blocks = sorted(self.block_summaries, key=lambda x: x.index)
        
        print("\n" + "="*80)
        print("🔗 BLOCKCHAIN CHAIN SEQUENCE - COMPLETE DETAILS")
        print("="*80)
        
        for i, block in enumerate(sorted_blocks):
            timestamp_str = datetime.fromtimestamp(block.timestamp).strftime("%H:%M:%S")
            
            # Show connection to previous block
            if i == 0:
                print("🔗 GENESIS BLOCK")
            else:
                prev_block = sorted_blocks[i-1]
                link_status = "✅" if block.previous_hash == prev_block.hash else "❌ BROKEN"
                print(f"🔗 LINK #{i}: {link_status}")
            
            print(f"📦 BLOCK #{block.index}")
            print(f"   ⛏️  Mined by: {block.node_source}")
            print(f"   📍 Miner Address: {block.miner_address}")
            print(f"   🕐 Timestamp: {timestamp_str}")
            print(f"   🔗 Block Hash:     {block.hash}")
            print(f"   ⬅️  Previous Hash: {block.previous_hash}")
            print(f"   🎯 Difficulty: {block.difficulty}")
            print(f"   🔢 Nonce: {block.nonce}")
            print(f"   💰 Transactions: {block.transactions_count}")
            
            # Verify hash linkage to next block
            if i < len(sorted_blocks) - 1:
                next_block = sorted_blocks[i+1]
                if next_block.previous_hash == block.hash:
                    print(f"   ➡️  Links to: Block #{next_block.index} ✅")
                else:
                    print(f"   ➡️  Links to: Block #{next_block.index} ❌ BROKEN")
            else:
                print("   ➡️  Latest block (chain head)")
            
            print()
        
        print("="*80)
        
        # Show comprehensive chain integrity status
        integrity_issues = self.check_chain_integrity(sorted_blocks)
        if not integrity_issues:
            print("✅ BLOCKCHAIN INTEGRITY: PERFECT")
            print("   • All blocks properly linked")
            print("   • Sequential block indices")
            print("   • Valid hash chain")
        else:
            print("❌ BLOCKCHAIN INTEGRITY: ISSUES DETECTED")
            for issue in integrity_issues:
                print(f"   ⚠️  {issue}")
        
        print()
    
    def check_chain_integrity(self, sorted_blocks: List[BlockSummary]) -> List[str]:
        """Check if the blockchain chain is properly linked"""
        issues = []
        
        for i in range(1, len(sorted_blocks)):
            current = sorted_blocks[i]
            previous = sorted_blocks[i-1]
            
            # Check sequential indices
            if current.index != previous.index + 1:
                issues.append(f"Block #{current.index}: Index gap (previous was #{previous.index})")
            
            # Check hash linking
            if current.previous_hash != previous.hash:
                issues.append(f"Block #{current.index}: Previous hash mismatch")
        
        return issues
    
    def display_mining_summary(self):
        """Display comprehensive mining summary"""
        print("\n" + "="*80)
        print("⛏️  BLOCKCHAIN MINING SUMMARY")
        print("="*80)
        
        # Network overview
        runtime = (time.time() - self.start_time) / 60.0  # minutes
        print(f"🌐 Network Overview:")
        print(f"   📊 Active Nodes: {len(self.active_nodes)}")
        print(f"   📦 Total Blocks Tracked: {self.total_blocks_tracked}")
        print(f"   ⏱️  Runtime: {runtime:.1f} minutes")
        print(f"   📈 Network Mining Rate: {self.total_blocks_tracked/runtime:.2f} blocks/min" if runtime > 0 else "   📈 Network Mining Rate: 0.00 blocks/min")
        print()
        
        # Show the actual blockchain chain
        self.display_blockchain_chain()
        
        # Per-node mining statistics
        print("📊 NODE MINING STATISTICS:")
        print("-" * 60)
        
        if not self.node_stats:
            print("   No mining activity detected")
            return
        
        for node_url, stats in sorted(self.node_stats.items(), key=lambda x: x[1].blocks_mined, reverse=True):
            status_icon = "🟢" if stats.is_active else "🔴"
            last_block = datetime.fromtimestamp(stats.last_block_time).strftime("%H:%M:%S") if stats.last_block_time else "Never"
            
            print(f"{status_icon} {stats.node_source} (Port {stats.port}):")
            print(f"   📦 Blocks Mined: {stats.blocks_mined}")
            print(f"   📈 Mining Rate: {stats.mining_rate:.2f} blocks/min")
            print(f"   🕐 Last Block: {last_block}")
            print(f"   🔗 Node URL: {stats.node_url}")
            print()
        
        print("="*80)
    
    def verify_blockchain_integrity(self) -> Dict[str, bool]:
        """Verify that blocks are properly linked across the network"""
        verification_results = {}
        
        # Group blocks by node
        blocks_by_node = defaultdict(list)
        for block in self.block_summaries:
            blocks_by_node[block.node_source].append(block)
        
        # Verify each node's chain
        for node_source, blocks in blocks_by_node.items():
            sorted_blocks = sorted(blocks, key=lambda x: x.index)
            is_valid = True
            
            for i in range(1, len(sorted_blocks)):
                current_block = sorted_blocks[i]
                previous_block = sorted_blocks[i-1]
                
                # Check if blocks are properly linked
                if current_block.previous_hash != previous_block.hash:
                    is_valid = False
                    break
                
                # Check sequential indices
                if current_block.index != previous_block.index + 1:
                    is_valid = False
                    break
            
            verification_results[node_source] = is_valid
        
        return verification_results
    
    def run_continuous_monitoring(self, interval: int = 3):
        """Run continuous monitoring of mining activity"""
        print("🚀 ChainCore Mining Summary Framework")
        print("="*60)
        print(f"🔍 Monitoring ports {self.discovery_start_port}-{self.discovery_end_port}")
        print(f"📊 Update interval: {interval} seconds")
        print("Press Ctrl+C to stop\n")
        
        self.running = True
        self.start_time = time.time()
        
        try:
            while self.running:
                # Scan for new blocks
                new_blocks = self.scan_all_nodes()
                
                # Display new blocks if found
                if new_blocks:
                    self.display_new_blocks(new_blocks)
                
                # Show summary every 30 seconds or when new blocks are found
                current_time = time.time()
                if new_blocks or (int(current_time) % 30 < interval):
                    self.display_mining_summary()
                    
                    # Show blockchain integrity status
                    integrity_results = self.verify_blockchain_integrity()
                    if integrity_results:
                        print("\n🔒 BLOCKCHAIN INTEGRITY:")
                        for node, is_valid in integrity_results.items():
                            status = "✅ Valid" if is_valid else "❌ Invalid"
                            print(f"   {node}: {status}")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped by user")
        finally:
            self.running = False

def main():
    """Main function to run the mining summary framework"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ChainCore Mining Summary Framework")
    parser.add_argument("--start-port", type=int, default=5000, help="Start port for node discovery")
    parser.add_argument("--end-port", type=int, default=5100, help="End port for node discovery")
    parser.add_argument("--interval", type=int, default=3, help="Update interval in seconds")
    
    args = parser.parse_args()
    
    # Create and run the monitoring framework
    framework = MiningSummaryFramework(args.start_port, args.end_port)
    framework.run_continuous_monitoring(args.interval)

if __name__ == "__main__":
    main()