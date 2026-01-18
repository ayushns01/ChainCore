#!/usr/bin/env python3
"""
ChainCore Blockchain Monitor
Real-time tracking of block mining and hash chain integrity across all network peers
Automatically discovers and monitors all active nodes in the network
"""

import requests
import json
import time
import sys
import threading
import concurrent.futures
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

class NetworkBlockchainMonitor:
    def __init__(self, discovery_start_port: int = 5000, discovery_end_port: int = 5010):
        self.discovery_start_port = discovery_start_port
        self.discovery_end_port = discovery_end_port
        self.active_peers: Set[str] = set()
        self.peer_data: Dict[str, Dict] = {}
        self.peer_lock = threading.RLock()
        self.peer_last_seen: Dict[str, int] = {}  # Track last seen length per peer
        
        # Clear any preserved data on initialization
        self._clear_all_data()
        
        # Network statistics - reset on each run
        self.network_stats = {
            'total_peers': 0,
            'longest_chain_length': 0,
            'network_hash_rate': 0.0,
            'consensus_status': 'unknown'
        }
    
    def _clear_all_data(self):
        """Clear all preserved blockchain data and reset state"""
        with self.peer_lock:
            self.active_peers.clear()
            self.peer_data.clear()
            self.peer_last_seen.clear()
            self.network_stats = {
                'total_peers': 0,
                'longest_chain_length': 0,
                'network_hash_rate': 0.0,
                'consensus_status': 'unknown'
            }
        print("Cleared all preserved blockchain data")
        
    def discover_active_peers(self) -> Set[str]:
        """Automatically discover all active peers in the network"""
        discovered_peers = set()
        
        print(f"Discovering active peers on ports {self.discovery_start_port}-{self.discovery_end_port}...")
        
        def check_peer(port: int) -> Optional[str]:
            """Check if a peer is active on the given port"""
            peer_url = f"http://localhost:{port}"
            try:
                response = requests.get(f"{peer_url}/status", timeout=1)  # Faster timeout
                if response.status_code == 200:
                    data = response.json()
                    # Verify it's actually a ChainCore node
                    if 'blockchain_length' in data and 'node_id' in data:
                        return peer_url
            except requests.RequestException:
                pass
            return None
        
        # Use thread pool for concurrent peer discovery with optimized settings
        port_range = list(range(self.discovery_start_port, self.discovery_end_port))
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(check_peer, port) for port in port_range]
            
            # Use as_completed with reasonable timeout
            try:
                for future in concurrent.futures.as_completed(futures, timeout=15):
                    try:
                        peer_url = future.result(timeout=0.5)  # Quick individual timeout
                        if peer_url:
                            discovered_peers.add(peer_url)
                            print(f"   ✅ Found active peer: {peer_url}")
                    except concurrent.futures.TimeoutError:
                        pass  # Skip slow responses
                    except Exception:
                        pass  # Skip errors
            except concurrent.futures.TimeoutError:
                print(f"   ⏰ Discovery completed - found {len(discovered_peers)} peers")
                # Cancel any remaining futures
                for future in futures:
                    if not future.done():
                        future.cancel()
        
        with self.peer_lock:
            self.active_peers = discovered_peers
            
        print(f"🎉 Discovery complete: {len(discovered_peers)} active peers found")
        return discovered_peers
    
    def get_peer_blockchain_data(self, peer_url: str) -> Optional[Dict]:
        """Get blockchain data from a specific peer"""
        try:
            response = requests.get(f"{peer_url}/blockchain", timeout=10)
            if response.status_code == 200:
                return response.json()
        except requests.RequestException:
            pass
        return None
    
    def get_peer_status(self, peer_url: str) -> Optional[Dict]:
        """Get status information from a specific peer"""
        try:
            response = requests.get(f"{peer_url}/status", timeout=5)
            if response.status_code == 200:
                return response.json()
        except requests.RequestException:
            pass
        return None
    
    def get_consensus_ledger(self, peer_chains: Dict) -> Dict:
        """
        ENHANCED: Determine the unified consensus ledger from all peer chains
        Returns the longest valid chain that represents the network's unified ledger
        """
        if not peer_chains:
            return {'consensus_chain': [], 'consensus_source': None, 'consensus_count': 0}
        
        # Find the longest valid chain(s)
        longest_length = 0
        candidate_chains = []
        
        for peer_url, peer_data in peer_chains.items():
            chain = peer_data['chain']
            chain_length = len(chain)
            
            # Validate chain integrity
            if self.is_valid_chain(chain):
                if chain_length > longest_length:
                    longest_length = chain_length
                    candidate_chains = [(peer_url, chain)]
                elif chain_length == longest_length:
                    candidate_chains.append((peer_url, chain))
        
        if not candidate_chains:
            return {'consensus_chain': [], 'consensus_source': None, 'consensus_count': 0}
        
        # If multiple chains of same length, find the one with majority consensus
        if len(candidate_chains) == 1:
            consensus_source, consensus_chain = candidate_chains[0]
            consensus_count = 1
        else:
            # Compare chains and find majority consensus
            chain_groups = {}
            for peer_url, chain in candidate_chains:
                # Create chain signature based on hashes
                chain_sig = tuple(block['hash'] for block in chain)
                if chain_sig not in chain_groups:
                    chain_groups[chain_sig] = []
                chain_groups[chain_sig].append((peer_url, chain))
            
            # Pick the chain group with most nodes
            consensus_group = max(chain_groups.values(), key=len)
            consensus_source, consensus_chain = consensus_group[0]
            consensus_count = len(consensus_group)
        
        # Verify consensus percentage
        total_nodes = len(peer_chains)
        consensus_percentage = (consensus_count / total_nodes) * 100 if total_nodes > 0 else 0
        
        return {
            'consensus_chain': consensus_chain,
            'consensus_source': consensus_source,
            'consensus_count': consensus_count,
            'total_nodes': total_nodes,
            'consensus_percentage': consensus_percentage,
            'longest_length': longest_length
        }
    
    def _check_and_report_consensus_issues(self, peer_chains: Dict, consensus_ledger: Dict):
        """Check for and report consensus issues like forks or disagreements"""
        if not peer_chains:
            return
        
        consensus_chain = consensus_ledger.get('consensus_chain', [])
        consensus_length = len(consensus_chain)
        total_nodes = len(peer_chains)
        consensus_count = consensus_ledger.get('consensus_count', 0)
        
        # Check for nodes with different chain lengths
        nodes_with_issues = []
        for peer_url, peer_data in peer_chains.items():
            peer_chain = peer_data['chain']
            peer_length = len(peer_chain)
            
            # Check if this node's chain differs from consensus
            if peer_length != consensus_length:
                port = peer_url.split(':')[-1]
                nodes_with_issues.append(f"Node-{port} ({peer_length} blocks)")
            elif peer_length > 0 and consensus_length > 0:
                # Check if same length but different blocks (fork)
                for i in range(min(peer_length, consensus_length)):
                    if i < len(peer_chain) and i < len(consensus_chain):
                        if peer_chain[i]['hash'] != consensus_chain[i]['hash']:
                            port = peer_url.split(':')[-1]
                            nodes_with_issues.append(f"Node-{port} (fork at block #{i})")
                            break
        
        # Report consensus issues
        if nodes_with_issues:
            print("⚠️  CONSENSUS ISSUES DETECTED:")
            print(f"   🌐 Unified Ledger: {consensus_length} blocks ({consensus_count}/{total_nodes} nodes)")
            print("   🍴 Nodes with different chains:")
            for issue in nodes_with_issues:
                print(f"      - {issue}")
            print()
        elif total_nodes > 1 and consensus_count == total_nodes:
            # Perfect consensus - only report occasionally
            import random
            if random.random() < 0.1:  # 10% chance to show this message
                print(f"✅ Perfect consensus: All {total_nodes} nodes agree on {consensus_length} block ledger")
                print()

    def aggregate_network_data(self) -> Dict:
        """Aggregate blockchain data from all active peers"""
        with self.peer_lock:
            if not self.active_peers:
                return {'chain': [], 'peer_count': 0}
        
        peer_blockchains = {}
        peer_statuses = {}
        
        def fetch_peer_data(peer_url: str) -> Tuple[str, Optional[Dict], Optional[Dict]]:
            """Fetch both blockchain and status data from a peer"""
            blockchain_data = self.get_peer_blockchain_data(peer_url)
            status_data = self.get_peer_status(peer_url)
            return peer_url, blockchain_data, status_data
        
        # Fetch data from all peers concurrently with improved error handling
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_peer_data, peer_url) 
                      for peer_url in self.active_peers]
            
            try:
                for future in concurrent.futures.as_completed(futures, timeout=25):
                    try:
                        peer_url, blockchain_data, status_data = future.result(timeout=2)
                        if blockchain_data:
                            peer_blockchains[peer_url] = blockchain_data
                        if status_data:
                            peer_statuses[peer_url] = status_data
                    except concurrent.futures.TimeoutError:
                        pass  # Skip slow peers
                    except Exception as e:
                        pass  # Skip failed peers
            except concurrent.futures.TimeoutError:
                print(f"   ⏰ Data fetch timeout - continuing with available data")
                # Cancel remaining futures
                for future in futures:
                    if not future.done():
                        future.cancel()
        
        # Store peer data for analysis (cleared each run)
        with self.peer_lock:
            # Clear previous data before storing new data
            self.peer_data.clear()
            self.peer_data = {
                'blockchains': peer_blockchains,
                'statuses': peer_statuses
            }
        
        # Simply return each peer's blockchain data separately - no aggregation
        peer_chains = {}
        for peer_url, blockchain_data in peer_blockchains.items():
            chain = blockchain_data.get('chain', [])
            if chain:  # Any chain with blocks
                peer_chains[peer_url] = {
                    'chain': chain,
                    'length': len(chain)
                }
        
        # ENHANCED: Determine consensus ledger
        consensus_info = self.get_consensus_ledger(peer_chains)
        
        return {
            'peer_chains': peer_chains,
            'peer_count': len(peer_chains),
            'total_active_peers': len(self.active_peers),
            'has_any_data': len(peer_chains) > 0,
            'consensus_ledger': consensus_info
        }
    
    def is_valid_chain(self, chain: List[Dict]) -> bool:
        """Quick validation of blockchain integrity"""
        if not chain:
            return True
        
        for i in range(1, len(chain)):
            if chain[i]['previous_hash'] != chain[i-1]['hash']:
                return False
        return True
    
    def chains_match(self, chain1: List[Dict], chain2: List[Dict]) -> bool:
        """Check if two chains have matching blocks"""
        if len(chain1) != len(chain2):
            return False
        
        for i in range(len(chain1)):
            if chain1[i]['hash'] != chain2[i]['hash']:
                return False
        return True
    
    def extract_miner_from_block(self, block: Dict, source_peer: str = None) -> tuple:
        """Extract miner address and mining node from block data with attribution preservation"""
        try:
            # First transaction should be coinbase
            coinbase_tx = block['transactions'][0]
            miner_address = "unknown"
            if coinbase_tx['outputs']:
                miner_address = coinbase_tx['outputs'][0]['recipient_address']
            
            # CRITICAL: Read actual mining node from block metadata
            mining_node = "unknown"
            
            # Priority 1: Check mining_metadata (complete attribution info)
            if 'mining_metadata' in block and isinstance(block['mining_metadata'], dict):
                metadata = block['mining_metadata']
                if 'mining_node' in metadata and metadata['mining_node']:
                    mining_node = metadata['mining_node']
                elif 'mining_provenance' in metadata and isinstance(metadata['mining_provenance'], dict):
                    provenance = metadata['mining_provenance']
                    if 'mining_node' in provenance and provenance['mining_node']:
                        mining_node = provenance['mining_node']
            
            # Priority 2: Check direct mining_node field
            elif 'mining_node' in block and block['mining_node']:
                mining_node = block['mining_node']
            
            # Priority 3: Try to infer from source peer information
            elif source_peer:
                # If we know which peer this block came from, use that as fallback
                peer_port = source_peer.split(':')[-1] if ':' in str(source_peer) else "unknown"
                mining_node = f"Node-{peer_port}"
            
            # Priority 4: Default to unknown if no mining attribution found
            else:
                mining_node = "unknown"
            
            return miner_address, mining_node
            
        except (KeyError, IndexError) as e:
            # Fallback: Try to infer from context if available
            if hasattr(self, '_current_source_peer') and self._current_source_peer:
                peer_port = self._current_source_peer.split(':')[-1]
                return "unknown", f"Node-{peer_port}"
            return "unknown", "unknown"
    
    def _check_block_consensus(self, block: Dict, peer_chains: Dict) -> Dict:
        """Check consensus status of a block across network nodes"""
        consensus_count = 0
        total_nodes = len(peer_chains)
        first_appearance = "unknown"
        
        block_hash = block.get('hash', '')
        block_index = block.get('index', -1)
        
        for peer_url, peer_data in peer_chains.items():
            peer_chain = peer_data.get('chain', [])
            
            # Check if this block exists in this peer's chain
            for peer_block in peer_chain:
                if (peer_block.get('index') == block_index and 
                    peer_block.get('hash') == block_hash):
                    consensus_count += 1
                    
                    # Track first appearance (could enhance with timestamps)
                    if first_appearance == "unknown":
                        peer_port = peer_url.split(':')[-1]
                        first_appearance = f"Node-{peer_port}"
                    break
        
        return {
            'consensus_count': consensus_count,
            'total_nodes': total_nodes,
            'consensus_percentage': (consensus_count / total_nodes * 100) if total_nodes > 0 else 0,
            'first_appearance': first_appearance,
            'is_consensus': consensus_count > (total_nodes / 2)  # Majority consensus
        }
    
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
    
    def get_enhanced_peer_metadata(self, peer_url: str) -> Dict:
        """Get comprehensive metadata from a peer including block headers and chain info"""
        try:
            metadata = {
                'peer_url': peer_url,
                'timestamp': time.time(),
                'basic_status': None,
                'chain_info': None,
                'genesis_verification': False,
                'recent_blocks_metadata': None,
                'errors': []
            }
            
            # Get basic status
            try:
                status_response = requests.get(f"{peer_url}/status", timeout=3)
                if status_response.status_code == 200:
                    metadata['basic_status'] = status_response.json()
                else:
                    metadata['errors'].append(f"Status HTTP {status_response.status_code}")
            except requests.RequestException as e:
                metadata['errors'].append(f"Status error: {str(e)}")
            
            # Get enhanced chain information
            try:
                chain_info_response = requests.get(f"{peer_url}/chain/info", timeout=3)
                if chain_info_response.status_code == 200:
                    metadata['chain_info'] = chain_info_response.json().get('chain_info', {})
                    
                    # Verify genesis block
                    import sys
                    import os
                    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src'))
                    from config.genesis_block import GENESIS_BLOCK_HASH
                    peer_genesis = metadata['chain_info'].get('genesis_hash')
                    metadata['genesis_verification'] = (peer_genesis == GENESIS_BLOCK_HASH)
                    
                else:
                    metadata['errors'].append(f"Chain info HTTP {chain_info_response.status_code}")
            except requests.RequestException as e:
                metadata['errors'].append(f"Chain info error: {str(e)}")
            
            # Get recent blocks with full metadata
            try:
                blocks_response = requests.get(f"{peer_url}/blocks/range?start=0&end=20", timeout=5)
                if blocks_response.status_code == 200:
                    blocks_data = blocks_response.json().get('blocks', [])
                    metadata['recent_blocks_metadata'] = self._analyze_blocks_comprehensive(blocks_data)
                else:
                    metadata['errors'].append(f"Blocks HTTP {blocks_response.status_code}")
            except requests.RequestException as e:
                metadata['errors'].append(f"Blocks error: {str(e)}")
            
            return metadata
            
        except Exception as e:
            return {
                'peer_url': peer_url,
                'timestamp': time.time(),
                'errors': [f"Critical error: {str(e)}"],
                'metadata_available': False
            }
    
    def _analyze_blocks_comprehensive(self, blocks_data: List[Dict]) -> Dict:
        """Comprehensive analysis of blocks metadata"""
        if not blocks_data:
            return {'blocks_analyzed': 0}
        
        analysis = {
            'blocks_analyzed': len(blocks_data),
            'genesis_block': None,
            'latest_block': None,
            'mining_nodes': {},
            'transaction_analysis': {
                'total_transactions': 0,
                'coinbase_transactions': 0,
                'user_transactions': 0,
                'average_tx_per_block': 0
            },
            'timing_analysis': {
                'timestamps': [],
                'average_block_time': 0,
                'block_intervals': []
            },
            'difficulty_analysis': {
                'difficulties': [],
                'average_difficulty': 0,
                'difficulty_changes': 0
            },
            'metadata_preservation': {
                'blocks_with_mining_metadata': 0,
                'blocks_with_genesis_metadata': 0,
                'metadata_completion_rate': 0
            }
        }
        
        # Sort blocks by index for proper analysis
        sorted_blocks = sorted(blocks_data, key=lambda b: b.get('index', 0))
        
        # Analyze each block
        for i, block_data in enumerate(sorted_blocks):
            block_index = block_data.get('index', 0)
            
            # Genesis block special handling
            if block_index == 0:
                analysis['genesis_block'] = {
                    'hash': block_data.get('hash'),
                    'timestamp': block_data.get('timestamp'),
                    'has_genesis_metadata': '_genesis_metadata' in block_data,
                    'genesis_data': block_data.get('_genesis_metadata', {})
                }
            
            # Track latest block
            if not analysis['latest_block'] or block_index > analysis['latest_block'].get('index', 0):
                analysis['latest_block'] = {
                    'index': block_index,
                    'hash': block_data.get('hash'),
                    'timestamp': block_data.get('timestamp'),
                    'difficulty': block_data.get('target_difficulty'),
                    'transaction_count': len(block_data.get('transactions', []))
                }
            
            # Mining node analysis
            mining_metadata = block_data.get('_mining_metadata', {})
            if mining_metadata:
                analysis['metadata_preservation']['blocks_with_mining_metadata'] += 1
                mining_node = mining_metadata.get('mining_node', 'unknown')
                
                if mining_node not in analysis['mining_nodes']:
                    analysis['mining_nodes'][mining_node] = {
                        'blocks_mined': 0,
                        'block_indices': [],
                        'first_block': block_index,
                        'last_block': block_index
                    }
                
                node_stats = analysis['mining_nodes'][mining_node]
                node_stats['blocks_mined'] += 1
                node_stats['block_indices'].append(block_index)
                node_stats['last_block'] = max(node_stats['last_block'], block_index)
            
            # Transaction analysis
            transactions = block_data.get('transactions', [])
            analysis['transaction_analysis']['total_transactions'] += len(transactions)
            
            coinbase_count = sum(1 for tx in transactions if tx.get('is_coinbase', False))
            analysis['transaction_analysis']['coinbase_transactions'] += coinbase_count
            analysis['transaction_analysis']['user_transactions'] += len(transactions) - coinbase_count
            
            # Timing analysis
            timestamp = block_data.get('timestamp')
            if timestamp:
                analysis['timing_analysis']['timestamps'].append(timestamp)
                
                # Calculate block interval
                if i > 0 and len(analysis['timing_analysis']['timestamps']) > 1:
                    prev_timestamp = analysis['timing_analysis']['timestamps'][i-1]
                    interval = timestamp - prev_timestamp
                    analysis['timing_analysis']['block_intervals'].append(interval)
            
            # Difficulty analysis
            difficulty = block_data.get('target_difficulty')
            if difficulty is not None:
                analysis['difficulty_analysis']['difficulties'].append(difficulty)
                
                # Check for difficulty changes
                if i > 0 and len(analysis['difficulty_analysis']['difficulties']) > 1:
                    prev_difficulty = analysis['difficulty_analysis']['difficulties'][i-1]
                    if difficulty != prev_difficulty:
                        analysis['difficulty_analysis']['difficulty_changes'] += 1
            
            # Check for genesis metadata
            if '_genesis_metadata' in block_data:
                analysis['metadata_preservation']['blocks_with_genesis_metadata'] += 1
        
        # Calculate averages
        if analysis['transaction_analysis']['total_transactions'] > 0:
            analysis['transaction_analysis']['average_tx_per_block'] = (
                analysis['transaction_analysis']['total_transactions'] / len(sorted_blocks)
            )
        
        if analysis['timing_analysis']['block_intervals']:
            analysis['timing_analysis']['average_block_time'] = (
                sum(analysis['timing_analysis']['block_intervals']) / 
                len(analysis['timing_analysis']['block_intervals'])
            )
        
        if analysis['difficulty_analysis']['difficulties']:
            analysis['difficulty_analysis']['average_difficulty'] = (
                sum(analysis['difficulty_analysis']['difficulties']) / 
                len(analysis['difficulty_analysis']['difficulties'])
            )
        
        # Calculate metadata completion rate
        total_metadata_fields = len(sorted_blocks) * 2  # Mining + Genesis metadata
        actual_metadata = (analysis['metadata_preservation']['blocks_with_mining_metadata'] + 
                          analysis['metadata_preservation']['blocks_with_genesis_metadata'])
        analysis['metadata_preservation']['metadata_completion_rate'] = (
            (actual_metadata / total_metadata_fields * 100) if total_metadata_fields > 0 else 0
        )
        
        return analysis

    def analyze_mining_distribution(self, blocks: List[Dict]) -> Dict:
        """Analyze which core nodes mined which blocks across the network"""
        miner_stats = {}
        
        for block in blocks:
            miner_address, mining_node = self.extract_miner_from_block(block)
            
            # Enhanced key with clear core identification
            if mining_node != "unknown":
                miner_key = f"Core-{mining_node}"
            else:
                miner_key = f"Unknown-Core ({miner_address[:12]}...)"
            
            if miner_key not in miner_stats:
                miner_stats[miner_key] = {
                    'miner_address': miner_address,
                    'mining_node': mining_node,
                    'core_identifier': miner_key,
                    'blocks_mined': 0,
                    'block_indices': [],
                    'total_rewards': 0.0,
                    'first_block': block['index'],
                    'last_block': block['index'],
                    'metadata_preserved': 'mining_metadata' in block or 'mining_node' in block
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
    
    def analyze_network_peer_status(self) -> Dict:
        """Analyze status of all network peers"""
        with self.peer_lock:
            if not self.peer_data.get('statuses'):
                return {}
        
        peer_analysis = {}
        
        for peer_url, status_data in self.peer_data['statuses'].items():
            peer_analysis[peer_url] = {
                'node_id': status_data.get('node_id', 'unknown'),
                'blockchain_length': status_data.get('blockchain_length', 0),
                'pending_transactions': status_data.get('pending_transactions', 0),
                'peers_connected': status_data.get('peers', 0),
                'uptime': status_data.get('uptime', 0),
                'api_calls': status_data.get('api_calls', 0),
                'target_difficulty': status_data.get('target_difficulty', 0),
                'thread_safe': status_data.get('thread_safe', False)
            }
        
        return peer_analysis
    
    def display_network_status(self):
        """Display comprehensive network status with unified ledger info"""
        print("🌐 UNIFIED NETWORK LEDGER STATUS")
        print("=" * 50)
        
        # Get current data
        data = self.aggregate_network_data()
        consensus_ledger = data.get('consensus_ledger', {})
        consensus_chain = consensus_ledger.get('consensus_chain', [])
        
        # Basic network stats
        print(f"📊 Active Peers: {len(self.active_peers)}")
        print(f"📝 Unified Ledger: {len(consensus_chain)} blocks")
        
        # Consensus information
        consensus_count = consensus_ledger.get('consensus_count', 0)
        total_nodes = consensus_ledger.get('total_nodes', 0)
        consensus_percentage = consensus_ledger.get('consensus_percentage', 0)
        
        if total_nodes > 0:
            print(f"🌐 Network Consensus: {consensus_count}/{total_nodes} nodes ({consensus_percentage:.1f}%)")
            if consensus_percentage >= 100:
                print("✅ Perfect Consensus: All nodes agree on ledger state")
            elif consensus_percentage >= 80:
                print("🟢 Strong Consensus: Majority agreement")
            elif consensus_percentage >= 60:
                print("🟡 Weak Consensus: Some disagreement detected")
            else:
                print("🔴 Poor Consensus: Significant network fragmentation")
        else:
            print("⏳ No consensus data available")
        
        print()
        
        # Peer details
        peer_analysis = self.analyze_network_peer_status()
        if peer_analysis:
            print("📡 PEER DETAILS")
            print("-" * 30)
            
            for peer_url, analysis in peer_analysis.items():
                status_icon = "🟢" if analysis['thread_safe'] else "🟡"
                print(f"{status_icon} {peer_url}")
                print(f"   🆔 Node ID: {analysis['node_id']}")
                print(f"   Chain Length: {analysis['blockchain_length']}")
                print(f"   📝 Pending TXs: {analysis['pending_transactions']}")
                print(f"   🌐 Connected Peers: {analysis['peers_connected']}")
                print(f"   🎯 Difficulty: {analysis['target_difficulty']}")
                print(f"   ⏱️  Uptime: {analysis['uptime']:.1f}s")
                print(f"   📞 API Calls: {analysis['api_calls']}")
                print()
        
        # Check for consensus issues
        chains_by_length = defaultdict(int)
        with self.peer_lock:
            if self.peer_data.get('blockchains'):
                for blockchain_data in self.peer_data['blockchains'].values():
                    chain_length = len(blockchain_data.get('chain', []))
                    chains_by_length[chain_length] += 1
        
        if len(chains_by_length) > 1:
            print("⚠️  CONSENSUS WARNINGS")
            print("-" * 25)
            print("🔀 Different chain lengths detected:")
            for length, peer_count in sorted(chains_by_length.items(), reverse=True):
                print(f"   {length} blocks: {peer_count} peer(s)")
            print("   💡 Network may be experiencing forks or sync issues")
            print()
    
    def display_peer_mining_comparison(self, miner_stats: Dict):
        """Display mining distribution with core node identification"""
        print("🏭 CORE NODE MINING DISTRIBUTION")
        print("=" * 60)
        
        total_blocks = sum(stats['blocks_mined'] for stats in miner_stats.values())
        
        if total_blocks == 0:
            print("❌ No blocks mined yet in the network")
            return
        
        print(f"📊 Total blocks analyzed: {total_blocks}")
        print(f"🏭 Active mining cores: {len(miner_stats)}")
        print()
        
        # Display each core's mining performance
        for core_id, stats in sorted(miner_stats.items(), key=lambda x: x[1]['blocks_mined'], reverse=True):
            percentage = (stats['blocks_mined'] / total_blocks * 100) if total_blocks > 0 else 0
            
            # Enhanced core display
            print(f"⛏️  {core_id}")
            print(f"   📦 Blocks mined: {stats['blocks_mined']} ({percentage:.1f}%)")
            print(f"   💰 Total rewards: {stats['total_rewards']:.2f} CC")
            print(f"   🏷️  Miner address: {stats['miner_address']}")
            print(f"   📊 Block range: #{stats['first_block']} → #{stats['last_block']}")
            print(f"   🔗 Recent blocks: {stats['block_indices'][-5:]}")  # Show last 5 blocks
            
            # Show metadata preservation status
            if stats['metadata_preserved']:
                print(f"   ✅ Mining attribution preserved")
            else:
                print(f"   ⚠️  Mining attribution missing")
            
            print()
    
    def identify_miner_peer(self, miner_address: str, peer_analysis: Dict) -> Optional[str]:
        """Try to identify which peer a miner address belongs to"""
        # This is a heuristic - in a real system you'd need better correlation
        # For now, we'll just return the first peer if there's only one
        if len(peer_analysis) == 1:
            return list(peer_analysis.keys())[0]
        return None
    
    def display_block_details(self, block: Dict, is_new: bool = False, source_peer: str = None):
        """Display block information for unified ledger"""
        miner_address, mining_node = self.extract_miner_from_block(block, source_peer)
        timestamp = datetime.fromtimestamp(block['timestamp']).strftime("%H:%M:%S")
        
        # Enhanced display for unified ledger
        print(f"   🔗 Hash: {block['hash'][:32]}...")
        print(f"   ⬅️  Prev: {block['previous_hash'][:32]}...")
        print(f"   ⏰ Time: {timestamp}")
        print(f"   🎲 Nonce: {block['nonce']}")
        
        # Show mining attribution  
        if mining_node != "unknown":
            print(f"   ⛏️  Mined by: {mining_node}")
        else:
            print(f"   ⛏️  Mined by: Unknown Node")
        
        # Show miner address (truncated if long)
        if len(miner_address) > 40:
            print(f"   🏷️  Address: {miner_address[:20]}...{miner_address[-15:]}")
        else:
            print(f"   🏷️  Address: {miner_address}")
        
        # Show coinbase reward
        try:
            coinbase_tx = block['transactions'][0]
            if coinbase_tx['outputs']:
                reward = coinbase_tx['outputs'][0]['amount']
                print(f"   💰 Reward: {reward} CC")
        except (KeyError, IndexError):
            pass
        
        # Show transaction count
        tx_count = len(block.get('transactions', []))
        print(f"   📝 Transactions: {tx_count}")
        
        # Show mining metadata if available
        if 'mining_metadata' in block:
            metadata = block['mining_metadata']
            if metadata.get('attribution_preserved'):
                print(f"   ✅ Mining attribution preserved")
        
        print()
    
    def display_mining_summary(self, miner_stats: Dict):
        """Display mining distribution summary"""
        print("MINING DISTRIBUTION SUMMARY")
        print("=" * 50)
        
        total_blocks = sum(stats['blocks_mined'] for stats in miner_stats.values())
        
        for miner, stats in sorted(miner_stats.items(), key=lambda x: x[1]['blocks_mined'], reverse=True):
            percentage = (stats['blocks_mined'] / total_blocks * 100) if total_blocks > 0 else 0
            
            print(f"Miner: {miner[:30]}...")
            print(f"  Blocks: {stats['blocks_mined']} ({percentage:.1f}%)")
            print(f"  💰 Rewards: {stats['total_rewards']}")
            print(f"  📊 Range: #{stats['first_block']} → #{stats['last_block']}")
            print(f"  🏷️  Blocks: {stats['block_indices']}")
            print()
    
    def display_hash_chain_status(self, issues: List[Dict]):
        """Display hash chain integrity status"""
        print("HASH CHAIN INTEGRITY")
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
                    print(f"   Block #{issue['block_index']}: Hash mismatch")
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
    
    def monitor_realtime(self, interval: int = 5, rediscover_interval: int = 60):
        """Monitor blockchain across all network peers in real-time"""
        print("🚀 ChainCore Network-Wide Blockchain Monitor")
        print("=" * 60)
        print("🧹 Starting fresh - all previous data cleared")
        print(f"Auto-discovery range: ports {self.discovery_start_port}-{self.discovery_end_port}")
        print(f"📊 Update interval: {interval} seconds")
        print(f"🔄 Peer rediscovery: every {rediscover_interval} seconds")
        print("Press Ctrl+C to stop\n")
        
        # Clear all data before starting monitoring
        self._clear_all_data()
        last_discovery = 0
        
        try:
            while True:
                current_time = time.time()
                
                # Periodic peer rediscovery
                if current_time - last_discovery > rediscover_interval:
                    print(f"🔄 Rediscovering peers...")
                    self.discover_active_peers()
                    last_discovery = current_time
                    print()
                
                # Skip if no peers found
                if not self.active_peers:
                    print("⏳ No active peers found. Trying discovery...")
                    self.discover_active_peers()
                    time.sleep(interval)
                    continue
                
                # Get data from all individual nodes
                data = self.aggregate_network_data()
                
                if not data or not data.get('has_any_data', False):
                    print("⏳ No active nodes found. Waiting for nodes to start...")
                    time.sleep(interval)
                    continue
                
                # Display network status occasionally
                if current_time - last_discovery < 5:
                    self.display_network_status()
                
                # ENHANCED: Track unified consensus ledger instead of individual peers
                consensus_ledger = data.get('consensus_ledger', {})
                consensus_chain = consensus_ledger.get('consensus_chain', [])
                new_blocks_found = False
                
                # Track the unified network ledger
                network_key = "unified_ledger"
                if network_key not in self.peer_last_seen:
                    self.peer_last_seen[network_key] = 0
                
                current_ledger_length = len(consensus_chain)
                last_ledger_length = self.peer_last_seen[network_key]
                
                # Show new blocks in the unified consensus ledger
                if current_ledger_length > last_ledger_length:
                    consensus_count = consensus_ledger.get('consensus_count', 0)
                    total_nodes = consensus_ledger.get('total_nodes', 0)
                    consensus_percentage = consensus_ledger.get('consensus_percentage', 0)
                    
                    print(f"🎉 NEW BLOCKS ADDED TO UNIFIED LEDGER:")
                    print(f"   🌐 Network Consensus: {consensus_count}/{total_nodes} nodes ({consensus_percentage:.1f}%)")
                    
                    # Display only the new blocks in the consensus ledger
                    for i in range(last_ledger_length, current_ledger_length):
                        if i < len(consensus_chain):
                            block = consensus_chain[i]
                            
                            print(f"📝 LEDGER BLOCK #{block['index']} - NETWORK ACCEPTED")
                            self.display_block_details(block, is_new=True, source_peer=None)
                            print(f"   ✅ Consensus Status: ACCEPTED by {consensus_count}/{total_nodes} nodes")
                            print()
                    
                    # Update tracking for the unified ledger
                    self.peer_last_seen[network_key] = current_ledger_length
                    new_blocks_found = True
                
                # Check for consensus issues (forks or disagreements)
                peer_chains = data.get('peer_chains', {})
                self._check_and_report_consensus_issues(peer_chains, consensus_ledger)
                
                # If no new blocks found, show waiting message occasionally
                if not new_blocks_found and current_time % 10 < interval:
                    print("⏳ Monitoring unified network ledger for new blocks...")
                    consensus_count = consensus_ledger.get('consensus_count', 0)
                    total_nodes = consensus_ledger.get('total_nodes', 0)
                    ledger_length = len(consensus_chain)
                    print(f"   📊 Unified Ledger: {ledger_length} blocks")
                    print(f"   🌐 Network Consensus: {consensus_count}/{total_nodes} nodes")
                else:
                    # Show periodic status updates even without new blocks
                    if int(current_time) % 30 == 0:  # Every 30 seconds
                        ledger_length = len(consensus_chain)
                        consensus_count = consensus_ledger.get('consensus_count', 0)
                        total_nodes = consensus_ledger.get('total_nodes', 0)
                        print(f"💭 Network status: {len(self.active_peers)} peers, unified ledger: {ledger_length} blocks")
                        print(f"   🌐 Consensus: {consensus_count}/{total_nodes} nodes agree")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n👋 Network monitoring stopped")
    
    def display_network_consensus_summary(self, data: Dict):
        """Display network consensus information"""
        print("🎯 NETWORK CONSENSUS STATUS")
        print("-" * 40)
        
        total_peers = data.get('peer_count', 0)
        consensus_peers = data.get('consensus_peers', 0)
        longest_chain = data.get('chain', [])
        
        if total_peers == 0:
            print("❌ No peers responding")
            return
        
        consensus_percentage = (consensus_peers / total_peers * 100) if total_peers > 0 else 0
        
        print(f"📊 Consensus: {consensus_peers}/{total_peers} peers ({consensus_percentage:.1f}%)")
        print(f"Canonical Chain: {len(longest_chain)} blocks")
        
        if consensus_percentage >= 80:
            print("✅ Strong consensus - network is stable")
        elif consensus_percentage >= 60:
            print("⚠️  Weak consensus - possible fork in progress")
        else:
            print("❌ Poor consensus - network fragmentation detected")
        
        # Show any chain conflicts
        with self.peer_lock:
            if self.peer_data.get('blockchains'):
                chain_lengths = {}
                for peer_url, blockchain_data in self.peer_data['blockchains'].items():
                    chain_length = len(blockchain_data.get('chain', []))
                    if chain_length not in chain_lengths:
                        chain_lengths[chain_length] = []
                    chain_lengths[chain_length].append(peer_url)
                
                if len(chain_lengths) > 1:
                    print("\n🔀 Chain length conflicts:")
                    for length, peers in sorted(chain_lengths.items(), reverse=True):
                        print(f"   {length} blocks: {len(peers)} peer(s)")
                        for peer in peers:
                            print(f"      • {peer}")
        
        print()
    
    def full_analysis(self):
        """Perform complete network-wide blockchain analysis"""
        print("📊 ChainCore Network-Wide Blockchain Analysis")
        print("=" * 60)
        print("🧹 Starting fresh analysis - all previous data cleared")
        
        # Clear all data before analysis
        self._clear_all_data()
        
        # Discover all active peers
        self.discover_active_peers()
        
        if not self.active_peers:
            print("❌ No active peers found in the network")
            return
        
        # Get aggregated network data
        data = self.aggregate_network_data()
        if not data or not data.get('chain'):
            print("❌ Cannot retrieve blockchain data from network")
            return
        
        blocks = data['chain']
        
        print(f"Total blocks: {len(blocks)}")
        print(f"🌐 Active peers: {len(self.active_peers)}")
        print(f"🎯 Consensus: {data.get('consensus_peers', 0)}/{data.get('peer_count', 0)} peers")
        print(f"Analysis time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Network status overview
        self.display_network_status()
        
        # Show all blocks
        print("📋 COMPLETE NETWORK BLOCKCHAIN")
        print("-" * 40)
        for block in blocks:
            self.display_block_details(block)
        
        # Network-wide mining analysis
        miner_stats = self.analyze_mining_distribution(blocks)
        self.display_peer_mining_comparison(miner_stats)
        
        # Hash chain integrity
        issues = self.verify_hash_chain(blocks)
        self.display_hash_chain_status(issues)
        
        # Network consensus analysis
        self.display_network_consensus_summary(data)

def main():
    if len(sys.argv) < 2:
        print("🚀 ChainCore Network-Wide Blockchain Monitor")
        print("Automatically discovers and monitors all active peers")
        print()
        print("Usage:")
        print("  python3 blockchain_monitor.py monitor [start_port] [end_port] [interval]  - Network monitoring")
        print("  python3 blockchain_monitor.py analyze [start_port] [end_port]            - Network analysis")
        print("  python3 blockchain_monitor.py compare [url1] [url2]                     - Compare two nodes")
        print("  python3 blockchain_monitor.py legacy [node_url]                         - Single node mode")
        print()
        print("Examples:")
        print("  python3 blockchain_monitor.py monitor                    # Monitor ports 5000-5100")
        print("  python3 blockchain_monitor.py monitor 5000 5020 3       # Monitor ports 5000-5020, 3s interval")
        print("  python3 blockchain_monitor.py analyze 5000 5050         # Analyze ports 5000-5050")
        print("  python3 blockchain_monitor.py compare http://localhost:5000 http://localhost:5001")
        print("  python3 blockchain_monitor.py legacy http://localhost:5000  # Old single-node mode")
        return
    
    command = sys.argv[1]
    
    if command == "monitor":
        start_port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
        end_port = int(sys.argv[3]) if len(sys.argv) > 3 else 5010
        interval = int(sys.argv[4]) if len(sys.argv) > 4 else 5
        
        monitor = NetworkBlockchainMonitor(start_port, end_port)
        monitor.monitor_realtime(interval)
    
    elif command == "analyze":
        start_port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
        end_port = int(sys.argv[3]) if len(sys.argv) > 3 else 5010
        
        monitor = NetworkBlockchainMonitor(start_port, end_port)
        monitor.full_analysis()
    
    elif command == "compare":
        url1 = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:5000"
        url2 = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:5001"
        
        print("Comparing two blockchain nodes")
        print("=" * 40)
        
        # Use the new network monitor for better comparison
        monitor = NetworkBlockchainMonitor()
        
        data1 = monitor.get_peer_blockchain_data(url1)
        data2 = monitor.get_peer_blockchain_data(url2)
        
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
    
    elif command == "legacy":
        # Legacy single-node monitoring mode
        node_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:5000"
        interval = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        
        print("🔄 Legacy single-node monitoring mode")
        print(f"Monitoring: {node_url}")
        print("💡 Use 'monitor' command for network-wide monitoring")
        print()
        
        # Create a simple single-node monitor using the legacy class
        class LegacyBlockchainMonitor:
            def __init__(self, node_url: str):
                self.node_url = node_url
                self.last_seen_length = 0
                
                # Use methods from NetworkBlockchainMonitor
                self.network_monitor = NetworkBlockchainMonitor()
            
            def get_blockchain_data(self):
                return self.network_monitor.get_peer_blockchain_data(self.node_url)
            
            def monitor_realtime(self, interval: int):
                print(f"Monitoring {self.node_url} every {interval} seconds...")
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
                        
                        if current_length > self.last_seen_length:
                            for i in range(self.last_seen_length, current_length):
                                if i < len(blocks):
                                    self.network_monitor.display_block_details(blocks[i], is_new=True)
                            self.last_seen_length = current_length
                        
                        time.sleep(interval)
                        
                except KeyboardInterrupt:
                    print("\n👋 Monitoring stopped")
        
        legacy_monitor = LegacyBlockchainMonitor(node_url)
        legacy_monitor.monitor_realtime(interval)
    
    else:
        print(f"❌ Unknown command: {command}")
        print("Use 'python3 blockchain_monitor.py' to see available commands")

if __name__ == "__main__":
    main()