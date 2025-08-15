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
    def __init__(self, node_url: str = None):
        self.node_url = node_url or "http://localhost:5000"  # Default but can be changed
        self.last_seen_length = 0
        self.block_history = []
        # Dynamic node tracking
        self.discovered_nodes = {}  # port -> node_info
        self.address_to_node = {}   # miner_address -> node_info
        self.node_discovery_attempted = False
        
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
    
    def extract_miner_from_block(self, block: Dict) -> tuple:
        """Extract miner address and identify the mining source from block's coinbase transaction"""
        try:
            # First transaction should be coinbase
            coinbase_tx = block['transactions'][0]
            if coinbase_tx['outputs']:
                miner_address = coinbase_tx['outputs'][0]['recipient_address']
                
                # Try to identify which node/client mined this block
                mining_source = self.identify_mining_source(miner_address, block)
                
                return miner_address, mining_source
            return "unknown", "unknown"
        except (KeyError, IndexError):
            return "unknown", "unknown"
    
    def identify_mining_source(self, miner_address: str, block: Dict) -> str:
        """Identify which mining client/node mined this block"""
        # Check if we have node discovery data
        if not self.discovered_nodes:
            self.discovered_nodes = self.discover_network_nodes(verbose=False)
        
        # Try to correlate mining time with node activity
        block_time = block.get('timestamp', 0)
        
        # If all miners use same address, try to identify by timing/nonce patterns
        if miner_address in self.address_to_node:
            return self.address_to_node[miner_address]
        
        # Try to identify by querying nodes about recent mining activity
        for port, node_info in self.discovered_nodes.items():
            try:
                # Check if this node has been actively mining recently
                response = requests.get(f"{node_info['url']}/status", timeout=2)
                if response.status_code == 200:
                    status = response.json()
                    
                    # Check if this node has mining activity indicators
                    api_calls = status.get('api_calls', 0)
                    if api_calls > 10:  # Active node indicator
                        # Store this correlation for future use
                        self.address_to_node[miner_address] = f"Node-{port}"
                        return f"Node-{port} ({node_info.get('node_id', 'unknown')})"
                        
            except requests.RequestException:
                continue
        
        # Default identification
        return f"Mining-Client-{miner_address[-8:]}"
    
    def discover_network_nodes(self, verbose: bool = False) -> Dict[str, Dict]:
        """Discover all active nodes in the network"""
        discovered = {}
        
        # Try common port range for ChainCore nodes
        base_ports = [5000, 5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009]
        
        for port in base_ports:
            try:
                node_url = f"http://localhost:{port}"
                response = requests.get(f"{node_url}/status", timeout=2)
                
                if response.status_code == 200:
                    status_data = response.json()
                    node_info = {
                        'url': node_url,
                        'port': port,
                        'node_id': status_data.get('node_id', f'node-{port}'),
                        'status': status_data,
                        'blockchain_length': status_data.get('blockchain_length', 0)
                    }
                    discovered[str(port)] = node_info
                    if verbose:
                        print(f"🔍 Found active node: {node_info['node_id']} on port {port}")
                    
            except requests.RequestException:
                # Node not available on this port
                continue
                
        return discovered
    
    def query_node_mining_addresses(self, node_info: Dict) -> List[str]:
        """Query a node to get its known mining addresses"""
        addresses = []
        try:
            # Try to get wallet or mining info from the node
            response = requests.get(f"{node_info['url']}/mining/addresses", timeout=3)
            if response.status_code == 200:
                data = response.json()
                addresses = data.get('addresses', [])
        except requests.RequestException:
            # If no mining addresses endpoint, try to infer from recent blocks
            pass
            
        # Also check if node has any pending mining templates
        try:
            response = requests.post(
                f"{node_info['url']}/mine_block", 
                json={'miner_address': 'probe_address'},
                timeout=3
            )
            if response.status_code == 200:
                # Node is accepting mining requests
                addresses.append('probe_address')
        except requests.RequestException:
            pass
            
        return addresses
    
    def build_address_mapping(self):
        """Build mapping of miner addresses to nodes by analyzing blockchain"""
        if not self.node_discovery_attempted:
            self.discovered_nodes = self.discover_network_nodes()
            self.node_discovery_attempted = True
            
            # Query each discovered node for their mining addresses
            for port, node_info in self.discovered_nodes.items():
                addresses = self.query_node_mining_addresses(node_info)
                for addr in addresses:
                    if addr and addr != 'probe_address':
                        self.address_to_node[addr] = node_info
        
        # Analyze recent blockchain data to build address mapping
        try:
            blockchain_data = self.get_blockchain_data()
            if blockchain_data and 'chain' in blockchain_data:
                blocks = blockchain_data['chain']
                
                # Analyze last 50 blocks or all blocks if fewer
                recent_blocks = blocks[-50:] if len(blocks) > 50 else blocks
                
                for block in recent_blocks:
                    miner_address = self.extract_miner_from_block(block)
                    if miner_address and miner_address not in self.address_to_node:
                        # Try to determine which node likely mined this
                        mining_node = self.infer_mining_node(block, miner_address)
                        if mining_node:
                            self.address_to_node[miner_address] = mining_node
                            
        except Exception as e:
            print(f"⚠️  Error building address mapping: {e}")
    
    def infer_mining_node(self, block: Dict, miner_address: str) -> Optional[Dict]:
        """Infer which node mined a block based on various factors"""
        # Try to find correlations between mining address and node characteristics
        block_time = block.get('timestamp', 0)
        
        # Check each discovered node's blockchain to see who has this block
        for port, node_info in self.discovered_nodes.items():
            try:
                response = requests.get(f"{node_info['url']}/blockchain", timeout=2)
                if response.status_code == 200:
                    node_chain = response.json().get('chain', [])
                    
                    # Check if this node has the block and it was recently added
                    for node_block in node_chain:
                        if (node_block.get('hash') == block.get('hash') and 
                            node_block.get('index') == block.get('index')):
                            
                            # This node has the block - likely they mined it or received it quickly
                            return node_info
                            
            except requests.RequestException:
                continue
                
        return None
    
    def identify_mining_node(self, miner_address: str) -> str:
        """Identify which node/core mined the block based on miner address"""
        # Only try to build address mapping in monitor mode when we have active connections
        # Skip this for offline analysis or when no nodes are running
        
        # Check if we have a direct mapping for this address
        if miner_address in self.address_to_node:
            node_info = self.address_to_node[miner_address]
            return f"{node_info['node_id']} (port {node_info['port']})"
        
        # Common mining addresses for known nodes
        known_miners = {
            'genesis': 'genesis',
            'test_miner': 'test node',
            'manual_test_miner': 'manual test',
            'debug_miner': 'debug node',
            'coinbase_test': 'test core',
            'simulate_test': 'simulation core',
            'hash_test': 'test core',
            'debug_validation': 'validation test',
        }
        
        # Check for exact matches in known miners
        if miner_address in known_miners:
            return known_miners[miner_address]
        
        # Try to infer from common patterns
        for pattern in ['core', 'node']:
            if pattern in miner_address.lower():
                # Extract number or identifier after pattern
                import re
                match = re.search(rf'{pattern}(\d+|[a-zA-Z]+)', miner_address.lower())
                if match:
                    identifier = match.group(1)
                    return f"{pattern}{identifier}"
        
        # Check if any discovered node matches this address pattern
        for port, node_info in self.discovered_nodes.items():
            node_id = node_info.get('node_id', '').lower()
            if (node_id in miner_address.lower() or 
                str(port) in miner_address or
                miner_address.lower() in node_id):
                return f"{node_info['node_id']} (port {port})"
        
        # For longer addresses (Bitcoin-style), show as external with node count info
        if len(miner_address) > 25:
            node_count = len(self.discovered_nodes)
            if node_count > 0:
                return f"external miner ({node_count} nodes active)"
            else:
                return "external miner"
        
        # Default case - show address prefix
        prefix = miner_address[:12] + "..." if len(miner_address) > 12 else miner_address
        return f"unknown ({prefix})"
    
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
    
    def _get_node_display_name(self) -> str:
        """Extract display name from node URL"""
        try:
            # Parse port from URL to identify node
            if "5000" in self.node_url:
                return "core0 (port 5000)"
            elif "5001" in self.node_url:
                return "core1 (port 5001)"
            elif "5002" in self.node_url:
                return "core2 (port 5002)"
            else:
                # Extract port from URL
                import re
                port_match = re.search(r':(\d+)', self.node_url)
                if port_match:
                    port = port_match.group(1)
                    return f"node (port {port})"
                else:
                    return self.node_url.replace("http://", "").replace("https://", "")
        except:
            return self.node_url
    
    def analyze_mining_distribution(self, blocks: List[Dict]) -> Dict:
        """Analyze which miners mined which blocks"""
        miner_stats = {}
        
        for block in blocks:
            miner_address, mining_source = self.extract_miner_from_block(block)
            # Use mining source as key for better differentiation
            miner_key = f"{mining_source} ({miner_address[:10]}...)" if len(miner_address) > 10 else f"{mining_source} ({miner_address})"
            
            if miner_key not in miner_stats:
                miner_stats[miner_key] = {
                    'miner_address': miner_address,
                    'mining_source': mining_source,
                    'blocks_mined': 0,
                    'block_indices': [],
                    'total_rewards': 0.0,
                    'first_block': block['index'],
                    'last_block': block['index']
                }
            
            stats = miner_stats[miner_key]
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
        miner_address, mining_source = self.extract_miner_from_block(block)
        mining_node = mining_source if mining_source != "unknown" else self.identify_mining_node(miner_address)
        timestamp = datetime.fromtimestamp(block['timestamp']).strftime("%H:%M:%S")
        
        # Determine if hash meets difficulty requirement
        required_zeros = "0" * block['target_difficulty']
        hash_valid = "✅" if block['hash'].startswith(required_zeros) else "❌"
        
        status = "🆕 NEW" if is_new else "📦"
        
        print(f"{status} Block #{block['index']}")
        print(f"   ⛏️  Mined by: {mining_node}")
        print(f"   📍 Address: {miner_address[:20]}..." if len(miner_address) > 20 else f"   📍 Address: {miner_address}")
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
        
        for miner_key, stats in sorted(miner_stats.items(), key=lambda x: x[1]['blocks_mined'], reverse=True):
            percentage = (stats['blocks_mined'] / total_blocks * 100) if total_blocks > 0 else 0
            miner_address = stats.get('miner_address', 'unknown')
            mining_source = stats.get('mining_source', 'unknown')
            
            print(f"Mining Source: {mining_source}")
            print(f"  📍 Address: {miner_address[:30]}..." if len(miner_address) > 30 else f"  📍 Address: {miner_address}")
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
        print(f"Update interval: {interval} seconds")
        print("Press Ctrl+C to stop\n")
        
        # Attempt to find active nodes
        active_node_found = False
        
        try:
            while True:
                # If we don't have an active node, try to discover one
                if not active_node_found:
                    discovered = self.discover_network_nodes(verbose=True)
                    
                    if discovered:
                        # Use the node with the longest blockchain
                        best_node = max(discovered.values(), 
                                      key=lambda x: x.get('blockchain_length', 0))
                        self.node_url = best_node['url']
                        active_node_found = True
                        print(f"✅ Connected to: {best_node['node_id']} ({self.node_url})")
                        print(f"📊 Blockchain length: {best_node.get('blockchain_length', 'unknown')}")
                        print(f"🌐 Found {len(discovered)} total active nodes")
                        print()
                    else:
                        print("⏳ No active nodes found. Waiting for nodes to start...")
                        time.sleep(interval * 2)  # Wait longer when no nodes
                        continue
                
                data = self.get_blockchain_data()
                if not data:
                    print(f"❌ Lost connection to {self.node_url}")
                    active_node_found = False  # Try to rediscover
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
        node_url = sys.argv[2] if len(sys.argv) > 2 else None  # Let monitor auto-discover
        interval = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        
        if node_url:
            monitor = BlockchainMonitor(node_url)
            print(f"🎯 Monitoring specific node: {node_url}")
        else:
            monitor = BlockchainMonitor()  # Will auto-discover
            print("🌐 Auto-discovery mode: will find and connect to active nodes")
        
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
            
            node1_name = monitor1._get_node_display_name()
            node2_name = monitor2._get_node_display_name()
            print(f"Node 1 - {node1_name}: {len(blocks1)} blocks")
            print(f"Node 2 - {node2_name}: {len(blocks2)} blocks")
            
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