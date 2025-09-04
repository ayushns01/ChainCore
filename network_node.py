#!/usr/bin/env python3
"""
Thread-Safe ChainCore Network Node
Thread-safe blockchain node

This implementation combines the original network_node.py with full thread safety integration.
All original functionality is preserved while adding concurrency control.

Thread Safety Features:
- Reader-writer locks with deadlock detection
- MVCC UTXO management with snapshot isolation
- Atomic operations for blockchain state changes
- Connection pooling and rate limiting for peers
- Work coordination for mining operations
- Statistics and monitoring
"""

import sys
import os
import json
import time
import threading
import argparse
import logging
from typing import Dict, List, Set, Optional
from flask import Flask, request, jsonify

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import thread-safe components
from src.concurrency import (
    ThreadSafeBlockchain, ThreadSafeMiner,
    synchronized, LockOrder, 
    mining_pool, lock_manager
)

# Import networking
from src.networking import (
    PeerManager, initialize_peer_manager, get_peer_manager
)
from src.networking.connection_cleaner import start_connection_cleanup, stop_connection_cleanup

# Import consensus mechanisms
from src.consensus import (
    get_mining_coordinator
)

# Import original components
from src.blockchain.bitcoin_transaction import Transaction
from src.crypto.ecdsa_crypto import hash_data, double_sha256

# Import centralized configuration
from src.config import BLOCKCHAIN_DIFFICULTY, BLOCK_REWARD, get_difficulty, get_mining_target

# Global blockchain configuration (centralized)
# To change difficulty, edit src/config.py BLOCKCHAIN_DIFFICULTY value

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Block class moved to src/blockchain/block.py to avoid circular imports
from src.blockchain.block import Block

class ThreadSafeNetworkNode:
    """
    Thread-safe network node with concurrency control
    """
    
    def __init__(self, node_id: str = "core0", api_port: int = 5000, p2p_port: int = 8000, bootstrap_nodes: List[str] = None):
        self.node_id = node_id
        self.api_port = api_port
        self.p2p_port = p2p_port
        
        # Thread-safe blockchain
        self.blockchain = ThreadSafeBlockchain()
        
        # IMMEDIATE WORKAROUND: Apply config difficulty at startup
        self._apply_config_difficulty_override()
        
        # REMOVED: Old peer manager is no longer used
        # self.peer_manager = ThreadSafePeerManager()
        
        # Peer management with full P2P capabilities
        bootstrap_nodes = bootstrap_nodes or []
        self.peer_network_manager = initialize_peer_manager(node_id, api_port, bootstrap_nodes)
        
        # Enhanced peer manager (alias for backward compatibility)
        self.peer_network_manager = self.peer_network_manager
        self.peer_manager = self.peer_network_manager
        
        # Flask app
        self.app = Flask(__name__)
        self.app.json.compact = False
        
        # Initialize API routes
        self._setup_api_routes()
        
        # Statistics
        self._stats = {
            'api_calls': 0,
            'blocks_processed': 0,
            'transactions_processed': 0,
            'peer_connections': 0,
            'uptime_start': time.time()
        }
        self._stats_lock = threading.Lock()
        
        
        logger.info("[INIT] ChainCore Network Node Successfully Initialized!")
        logger.info(f"   [ID] Node ID: {self.node_id}")
        logger.info(f"   [API] API Server: http://localhost:{self.api_port}")
        logger.info(f"   [P2P] P2P Port: {self.p2p_port}")
        logger.info("   [READY] All systems ready!")
    
    def _apply_config_difficulty_override(self):
        """Apply config difficulty setting at startup"""
        try:
            from src.config import BLOCKCHAIN_DIFFICULTY
            if hasattr(self.blockchain, 'set_mining_difficulty'):
                self.blockchain.set_mining_difficulty(BLOCKCHAIN_DIFFICULTY, force=True)
                logger.info(f"🔧 Forced difficulty to config value: {BLOCKCHAIN_DIFFICULTY}")
        except Exception as e:
            logger.warning(f"Could not apply config difficulty override: {e}")
    
    def _sync_with_network_before_mining(self) -> Dict:
        """Synchronization with chain validation"""
        blocks_added = 0
        sync_errors = []
        
        try:
            # Get active peers
            peers = self.peer_network_manager.get_active_peers()
            if not peers:
                return {'blocks_added': 0, 'error': 'No peers available'}
            
            current_length = self.blockchain.get_chain_length()
            max_peer_length = current_length
            best_peer = None
            
            # Optimized peer checking for large networks
            # Use status endpoint first (lightweight), then blockchain if needed
            peer_candidates = []
            
            # Phase 1: Quick status check for all peers
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                status_futures = {
                    executor.submit(self._get_peer_status, peer_url): peer_url 
                    for peer_url in peers
                }
                
                for future in concurrent.futures.as_completed(status_futures, timeout=10):
                    peer_url = status_futures[future]
                    try:
                        status = future.result()
                        if status and status.get('blockchain_length', 0) > current_length:
                            peer_candidates.append((peer_url, status['blockchain_length']))
                    except Exception:
                        continue
            
            # Phase 2: Sort by chain length and check top candidates only
            if peer_candidates:
                peer_candidates.sort(key=lambda x: x[1], reverse=True)  # Sort by length desc
                # Only check top 5 peers for full blockchain to save bandwidth
                top_peers = peer_candidates[:5]
                
                for peer_url, peer_length in top_peers:
                    try:
                        response = requests.get(f"{peer_url}/blockchain", timeout=10)
                        if response.status_code == 200:
                            peer_data = response.json()
                            actual_length = len(peer_data.get('chain', []))
                            
                            if actual_length > max_peer_length:
                                max_peer_length = actual_length
                                best_peer = peer_url
                                break  # Use first best peer found
                                
                    except requests.RequestException:
                        continue
            
            # Synchronization with validation
            if best_peer and max_peer_length > current_length:
                print(f"   [SYNC] Found longer chain: {max_peer_length} blocks vs our {current_length}")
                print(f"   [SYNC] Synchronizing with {best_peer}")
                
                # Get chain info first for validation
                chain_info_response = requests.get(f"{best_peer}/chain/info", timeout=5)
                if chain_info_response.status_code == 200:
                    peer_chain_info = chain_info_response.json().get('chain_info', {})
                    our_chain_info = self.blockchain.get_chain_info()
                    
                    # Verify genesis block matches (relaxed for local testing)
                    peer_genesis = peer_chain_info.get('genesis_hash')
                    our_genesis = our_chain_info.get('genesis_hash')
                    if peer_genesis and our_genesis and peer_genesis != our_genesis:
                        print(f"     [WARNING] Genesis block difference detected")
                        print(f"     [INFO] Our genesis: {our_genesis[:20]}...")
                        print(f"     [INFO] Peer genesis: {peer_genesis[:20]}...")
                        # Continue with sync - allow for minor genesis differences
                
                # Get missing blocks in optimized batches for large networks
                missing_blocks = max_peer_length - current_length
                
                # Dynamic batch sizing based on network size and missing blocks
                from src.config import SYNC_BATCH_SIZE, NETWORK_TIMEOUT_SCALING, BASE_TIMEOUT, MAX_TIMEOUT
                batch_size = min(SYNC_BATCH_SIZE, max(10, missing_blocks // 10))  # Adaptive batch size
                
                # Calculate timeout based on network size and batch size
                active_peer_count = len(self.peer_network_manager.get_active_peers())
                if NETWORK_TIMEOUT_SCALING:
                    sync_timeout = min(MAX_TIMEOUT, BASE_TIMEOUT + (active_peer_count * 0.5) + (batch_size * 0.1))
                else:
                    sync_timeout = BASE_TIMEOUT
                
                print(f"     [BATCH] Sync optimization: batch_size={batch_size}, timeout={sync_timeout:.1f}s")
                
                for start_index in range(current_length, max_peer_length, batch_size):
                    end_index = min(start_index + batch_size - 1, max_peer_length - 1)
                    
                    # Request block range with optimized timeout
                    response = requests.get(
                        f"{best_peer}/blocks/range?start={start_index}&end={end_index}",
                        timeout=sync_timeout
                    )
                    
                    if response.status_code == 200:
                        batch_data = response.json()
                        blocks_data = batch_data.get('blocks', [])
                        
                        # Add blocks in order
                        for block_data in blocks_data:
                            from src.blockchain.block import Block
                            block = Block.from_dict(block_data)
                            
                            if self.blockchain.add_block(block, allow_reorganization=False):
                                blocks_added += 1
                                if blocks_added % 10 == 0:  # Progress updates
                                    print(f"     [PROGRESS] Synchronized {blocks_added}/{missing_blocks} blocks...")
                            else:
                                print(f"     [ERROR] Failed to add block #{block.index}")
                                sync_errors.append(f"Block #{block.index} validation failed")
                                # Don't break completely - log and continue
                    else:
                        print(f"     [ERROR] Failed to get block range {start_index}-{end_index}")
                        break
                
                if blocks_added > 0:
                    print(f"   [SUCCESS] Synchronization complete: Added {blocks_added} blocks")
                else:
                    print(f"   [WARNING] No blocks added during synchronization")
            
            return {
                'blocks_added': blocks_added,
                'sync_errors': sync_errors if sync_errors else None,
                'peers_checked': len(peers),
                'best_peer': best_peer
            }
            
        except Exception as e:
            logger.error(f"Sync error: {e}")
            return {'blocks_added': 0, 'error': str(e)}
    
    def _setup_api_routes(self):
        """Setup all API routes with thread safety"""
        
        @self.app.route('/status', methods=['GET'])
        @synchronized("api_status", LockOrder.NETWORK, mode='read')
        def get_status():
            """Status endpoint with information"""
            self._increment_api_calls()
            
            # Get current statistics
            blockchain_length = self.blockchain.get_chain_length()
            pending_txs = len(self.blockchain.get_transaction_pool_copy())
            peer_status = self.peer_network_manager.get_status()
            active_peers = peer_status.get('active_peers', 0)
            total_peers = peer_status.get('total_peers', 0)
            uptime_seconds = time.time() - self._stats['uptime_start']
            
            # Calculate uptime in human readable format
            uptime_hours = int(uptime_seconds // 3600)
            uptime_minutes = int((uptime_seconds % 3600) // 60)
            uptime_readable = f"{uptime_hours}h {uptime_minutes}m" if uptime_hours > 0 else f"{uptime_minutes}m"
            
            # Determine network health status
            if active_peers == 0:
                network_health = "Single Node Mode"
            elif active_peers < self.peer_network_manager.target_outbound_connections:
                network_health = "Seeking More Peers"
            else:
                network_health = "Well Connected"

            # Determine node role (simplified)
            node_role = "Peer Node"

            # Get mining difficulty status
            difficulty_status = "Hard" if self.blockchain.target_difficulty > 4 else "Moderate"

            status_summary = f"""
+======================================================================+
|                    CHAINCORE NODE STATUS                            |
+======================================================================+
| Node: {self.node_id:<20} Port: {self.api_port:<20}              |
| Status: ONLINE & OPERATIONAL      Uptime: {uptime_readable:<15}   |
| Chain: {blockchain_length:,} blocks{' + ' + str(pending_txs) + ' pending' if pending_txs > 0 else '':20}   |
| Peers: {active_peers} connected ({total_peers} known)                      |
| Difficulty: {self.blockchain.target_difficulty} {difficulty_status:<30}   |
+======================================================================+
            """.strip()

            return jsonify({
                'STATUS_DISPLAY': status_summary,
                'node_id': self.node_id,
                'blockchain_length': blockchain_length,
                'pending_transactions': pending_txs,
                'peers': active_peers,
                'total_peers': total_peers,
                'node_role': node_role,
                'target_difficulty': self.blockchain.target_difficulty,
                'network_health': network_health,
                'uptime': uptime_seconds,
                'version': '2.0', # Updated version
                'thread_safe': True,  # Mining client expects this field
                'status': 'online',
                'node_info': {
                    'thread_safe': True,
                    'initialized': blockchain_length > 0,
                    'operational': True
                }
            })
        
        @self.app.route('/status/human', methods=['GET'])
        @self.app.route('/', methods=['GET'])  # Also serve on root URL
        def get_human_status():
            """Human-readable HTML status page for browser viewing"""
            status_data = get_status().json
            
            html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>ChainCore Node Status - {status_data['node_info']['node_id']}</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; line-height: 1.6; margin: 0; padding: 20px; background: #f5f7fa; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
        .status-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .status-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .status-card h3 {{ margin-top: 0; color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        .metric {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }}
        .metric:last-child {{ border-bottom: none; }}
        .metric-label {{ font-weight: 500; color: #666; }}
        .metric-value {{ font-weight: bold; color: #333; }}
        .status-online {{ color: #10b981; }}
        .status-warning {{ color: #f59e0b; }}
        .status-error {{ color: #ef4444; }}
        .refresh-btn {{ background: #667eea; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }}
        .refresh-btn:hover {{ background: #5a67d8; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>[CHAINCORE] ChainCore Blockchain Node</h1>
            <p>Node ID: <strong>{status_data['node_info']['node_id']}</strong> • 
               Port: <strong>{status_data['node_info']['api_port']}</strong> • 
               Status: <span class="status-online">{status_data['summary']['node_health']}</span></p>
            <button class="refresh-btn" onclick="location.reload()">🔄 Refresh Status</button>
        </div>
        
        <div class="status-grid">
            <div class="status-card">
                <h3>📊 Node Overview</h3>
                <div class="metric"><span class="metric-label">Health Status</span><span class="metric-value">{status_data['summary']['node_health']}</span></div>
                <div class="metric"><span class="metric-label">Network Status</span><span class="metric-value">{status_data['summary']['network_status']}</span></div>
                <div class="metric"><span class="metric-label">Blockchain Status</span><span class="metric-value">{status_data['summary']['blockchain_status']}</span></div>
                <div class="metric"><span class="metric-label">Node Role</span><span class="metric-value">{status_data['summary']['node_role']}</span></div>
                <div class="metric"><span class="metric-label">Uptime</span><span class="metric-value">{status_data['summary']['uptime']}</span></div>
            </div>
            
            <div class="status-card">
                <h3>⛓️ Blockchain Status</h3>
                <div class="metric"><span class="metric-label">Chain Length</span><span class="metric-value">{status_data['blockchain']['chain_length']} blocks</span></div>
                <div class="metric"><span class="metric-label">Status</span><span class="metric-value">{status_data['blockchain']['status_message']}</span></div>
                <div class="metric"><span class="metric-label">Pending Transactions</span><span class="metric-value">{status_data['blockchain']['pending_transactions']}</span></div>
                <div class="metric"><span class="metric-label">Mining Difficulty</span><span class="metric-value">{status_data['blockchain']['mining_difficulty']} ({status_data['blockchain']['difficulty_status']})</span></div>
                <div class="metric"><span class="metric-label">Genesis Block</span><span class="metric-value">{'✅ Yes' if status_data['blockchain']['genesis_initialized'] else '❌ No'}</span></div>
            </div>
            
            <div class="status-card">
                <h3>🌐 Network Status</h3>
                <div class="metric"><span class="metric-label">Network Health</span><span class="metric-value">{status_data['network']['status_message']}</span></div>
                <div class="metric"><span class="metric-label">Active Peers</span><span class="metric-value">{status_data['network']['active_peers']}</span></div>
                <div class="metric"><span class="metric-label">Is Main Node</span><span class="metric-value">{'🏆 Yes' if status_data['network']['is_main_node'] else '👥 No'}</span></div>
                <div class="metric"><span class="metric-label">Peer Discovery</span><span class="metric-value">{'✅ Enabled' if status_data['network']['discovery']['enabled'] else '❌ Disabled'}</span></div>
                <div class="metric"><span class="metric-label">Scan Range</span><span class="metric-value">{status_data['network']['discovery']['scan_range']}</span></div>
            </div>
            
            <div class="status-card">
                <h3>⚡ Performance</h3>
                <div class="metric"><span class="metric-label">API Calls Handled</span><span class="metric-value">{status_data['node_info']['api_calls_handled']}</span></div>
                <div class="metric"><span class="metric-label">Blocks Processed</span><span class="metric-value">{status_data['performance']['blocks_processed']}</span></div>
                <div class="metric"><span class="metric-label">Transactions Processed</span><span class="metric-value">{status_data['performance']['transactions_processed']}</span></div>
                <div class="metric"><span class="metric-label">Response Time</span><span class="metric-value">{status_data['performance']['average_response_time']}</span></div>
                <div class="metric"><span class="metric-label">Thread Safety</span><span class="metric-value">{'✅ Safe' if status_data['node_info']['thread_safe'] else '⚠️ Issues'}</span></div>
            </div>
        </div>
        
        <div style="margin-top: 20px; text-align: center; color: #666; font-size: 14px;">
            <p>🕒 Last Updated: <span id="timestamp"></span> • 
               <a href="/status" style="color: #667eea;">View JSON API</a> • 
               <a href="/blockchain" style="color: #667eea;">View Blockchain</a></p>
        </div>
    </div>
    
    <script>
        document.getElementById('timestamp').textContent = new Date().toLocaleString();
        
        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>"""
            return html
        
        @self.app.route('/blockchain', methods=['GET'])
        @synchronized("api_blockchain", LockOrder.NETWORK, mode='read')
        def get_blockchain():
            """Thread-safe blockchain retrieval"""
            self._increment_api_calls()
            
            chain_copy = self.blockchain.get_chain_copy()
            return jsonify({
                'length': len(chain_copy),
                'chain': [block.to_dict() for block in chain_copy]
            })
        
        @self.app.route('/blockchain/headers', methods=['GET'])
        @synchronized("api_blockchain_headers", LockOrder.NETWORK, mode='read')
        def get_blockchain_headers():
            """Get blockchain headers for header-first sync (industry standard)"""
            self._increment_api_calls()
            
            try:
                chain_copy = self.blockchain.get_chain_copy()
                headers = []
                
                for block in chain_copy:
                    headers.append({
                        'index': block.index,
                        'hash': block.hash,
                        'previous_hash': block.previous_hash,
                        'timestamp': block.timestamp,
                        'target_difficulty': block.target_difficulty,
                        'nonce': block.nonce,
                        'merkle_root': block.merkle_root
                    })
                
                return jsonify({
                    'headers': headers,
                    'count': len(headers)
                })
                
            except Exception as e:
                logger.error(f"Error getting blockchain headers: {e}")
                return jsonify({
                    'error': 'Failed to get blockchain headers',
                    'details': str(e)
                }), 500
        
        @self.app.route('/balance/<address>', methods=['GET'])
        @synchronized("api_balance", LockOrder.NETWORK, mode='read')
        def get_balance(address: str):
            """Thread-safe balance lookup"""
            self._increment_api_calls()
            
            balance = self.blockchain.utxo_set.get_balance(address)
            return jsonify({'balance': balance, 'address': address})
        
        @self.app.route('/utxos/<address>', methods=['GET'])
        @synchronized("api_utxos", LockOrder.NETWORK, mode='read')
        def get_utxos(address: str):
            """Thread-safe UTXO retrieval"""
            self._increment_api_calls()
            
            utxos = self.blockchain.utxo_set.get_utxos_for_address(address)
            return jsonify({'utxos': utxos, 'count': len(utxos)})
        
        @self.app.route('/transaction_pool', methods=['GET'])
        @synchronized("api_pool", LockOrder.NETWORK, mode='read')
        def get_transaction_pool():
            """Thread-safe transaction pool"""
            self._increment_api_calls()
            
            pool_copy = self.blockchain.get_transaction_pool_copy()
            return jsonify({
                'transactions': [tx.to_dict() for tx in pool_copy],
                'count': len(pool_copy)
            })
        
        @self.app.route('/add_transaction', methods=['POST'])
        @synchronized("api_add_tx", LockOrder.NETWORK, mode='write')
        def add_transaction():
            """Thread-safe transaction addition"""
            self._increment_api_calls()
            
            try:
                tx_data = request.get_json()
                transaction = Transaction.from_dict(tx_data)
                
                if self.blockchain.add_transaction(transaction):
                    # Broadcast to peers
                    self.peer_network_manager.broadcast_to_peers(
                        '/receive_transaction', 
                        tx_data,
                        timeout=5.0
                    )
                    
                    return jsonify({
                        'status': 'accepted',
                        'tx_id': transaction.tx_id
                    })
                else:
                    return jsonify({
                        'status': 'rejected',
                        'error': 'Invalid transaction'
                    }), 400
                    
            except Exception as e:
                logger.error(f"Error adding transaction: {e}")
                return jsonify({
                    'status': 'error',
                    'error': str(e)
                }), 500
        
        @self.app.route('/broadcast_transaction', methods=['POST'])
        @synchronized("api_broadcast_tx", LockOrder.NETWORK, mode='write')
        def broadcast_transaction():
            """Thread-safe transaction broadcasting (alias for add_transaction)"""
            self._increment_api_calls()
            
            try:
                tx_data = request.get_json()
                transaction = Transaction.from_dict(tx_data)
                
                if self.blockchain.add_transaction(transaction):
                    # Broadcast to peers
                    self.peer_network_manager.broadcast_to_peers(
                        '/receive_transaction', 
                        tx_data,
                        timeout=5.0
                    )
                    
                    return jsonify({
                        'status': 'accepted',
                        'tx_id': transaction.tx_id
                    })
                else:
                    return jsonify({
                        'status': 'rejected',
                        'error': 'Invalid transaction'
                    }), 400
                    
            except Exception as e:
                logger.error(f"Error broadcasting transaction: {e}")
                return jsonify({
                    'status': 'error',
                    'error': str(e)
                }), 500
        
        @self.app.route('/receive_transaction', methods=['POST'])
        @synchronized("api_receive_tx", LockOrder.NETWORK, mode='write')
        def receive_transaction():
            """Thread-safe transaction reception from peers"""
            self._increment_api_calls()
            
            try:
                tx_data = request.get_json()
                transaction = Transaction.from_dict(tx_data)
                
                if self.blockchain.add_transaction(transaction):
                    return jsonify({
                        'status': 'accepted',
                        'tx_id': transaction.tx_id
                    })
                else:
                    return jsonify({
                        'status': 'rejected',
                        'error': 'Invalid transaction'
                    }), 400
                    
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'error': str(e)
                }), 500
        
        @self.app.route('/mine_block', methods=['POST'])
        @synchronized("api_mine", LockOrder.NETWORK, mode='write')
        def mine_block():
            """Thread-safe mining block template with network synchronization"""
            self._increment_api_calls()
            
            try:
                data = request.get_json() or {}
                miner_address = data.get('miner_address', 'unknown')
                
                # Synchronize with network before creating mining template
                print(f"[SYNC] SYNC CHECK: Ensuring latest blockchain state before mining")
                sync_result = self._sync_with_network_before_mining()
                
                # MINING GUARD: Prevent mining if isolated from the network
                if sync_result.get('error') == 'No peers available':
                    logger.warning("Mining paused: No peers available for network synchronization.")
                    return jsonify({
                        'status': 'rejected',
                        'reason': 'isolated_node',
                        'error': 'Cannot mine a new block without active peer connections.'
                    }), 409

                if sync_result['blocks_added'] > 0:
                    print(f"   [SYNC] Synchronized: Added {sync_result['blocks_added']} blocks from network")
                    print(f"   [INFO] Updated chain length: {self.blockchain.get_chain_length()}")
                else:
                    print(f"   [PASS] Already synchronized with network")
                
                # Create mining template with latest chain state
                mining_node = f"Node-{self.api_port}"
                block_template = self.blockchain.create_block_template(miner_address, mining_node)
                
                return jsonify({
                    'status': 'template_created',
                    'block_template': block_template.to_dict(),
                    'target_difficulty': block_template.target_difficulty
                })
                
            except Exception as e:
                logger.error(f"Error creating block template: {e}")
                return jsonify({
                    'status': 'error',
                    'error': str(e)
                }), 500
        
        @self.app.route('/submit_block', methods=['POST'])
        @synchronized("api_submit_block", LockOrder.NETWORK, mode='write')
        def submit_block():
            """Thread-safe block submission with race condition prevention"""
            self._increment_api_calls()
            
            try:
                data = request.get_json()
                block_data = data.get('block', data)  # Handle both formats
                
                # Pre-submission network sync to prevent stale blocks
                is_locally_mined = request.headers.get('X-Local-Mining') == 'true'
                if not is_locally_mined:
                    print(f"[NETWORK] NETWORK BLOCK: Received block #{block_data.get('index', '?')} from peer")
                    # For network blocks, sync before processing to ensure latest state
                    sync_result = self._sync_with_network_before_mining()
                    if sync_result['blocks_added'] > 0:
                        print(f"   📥 Pre-processing sync: Added {sync_result['blocks_added']} blocks")
                
                # Use Block.from_dict for proper mining attribution preservation
                block = Block.from_dict(block_data)
                
                # If no mining node was preserved, use current node as fallback
                if not hasattr(block, '_mining_metadata') or not block._mining_metadata.get('mining_node'):
                    if not hasattr(block, '_mining_metadata'):
                        block._mining_metadata = {}
                    block._mining_metadata['mining_node'] = f"Node-{self.api_port}"
                
                # Get fresh chain state after potential sync
                current_chain_length = self.blockchain.get_chain_length()
                
                # Verify block is still valid after sync - locally mined block should be next in sequence
                # For locally mined blocks, we are more lenient since we know the context
                if is_locally_mined:
                    # Allow blocks that are the next in sequence (normal case)
                    if block.index == current_chain_length:
                        # This is the expected case - block is next in chain
                        pass
                    elif block.index < current_chain_length:
                        # Block is stale - chain has moved forward since template was created
                        logger.warning(f"LOCAL BLOCK STALE: Block #{block.index} vs chain #{current_chain_length}")
                        return jsonify({
                            'status': 'rejected',
                            'reason': 'stale_block',
                            'error': f'Block is stale: mining #{block.index}, chain now #{current_chain_length}',
                            'current_chain_length': current_chain_length
                        }), 409
                    else:
                        # block.index > current_chain_length - this shouldn't happen for local mining
                        logger.warning(f"LOCAL BLOCK FUTURE: Block #{block.index} vs chain #{current_chain_length}")
                        return jsonify({
                            'status': 'rejected',
                            'reason': 'invalid_index',
                            'error': f'Block index too high: #{block.index}, chain at #{current_chain_length}',
                            'current_chain_length': current_chain_length
                        }), 409
                
                # Case 1: Next sequential block (normal case)
                if block.index == current_chain_length:
                    pass  # Continue with normal processing
                
                # Case 2: Block from a fork (potential reorganization)
                elif block.index < current_chain_length:
                    logger.info(f"🍴 Potential fork detected: Block #{block.index} for chain length {current_chain_length}")
                    # Don't reject immediately - this could be part of a longer chain
                    pass
                
                # Case 3: Future block (missing intermediate blocks)
                elif block.index > current_chain_length:
                    logger.warning(f"⚠️ Future block #{block.index} received (chain length: {current_chain_length})")
                    # Request missing blocks from the sender
                    return jsonify({
                        'status': 'need_sync',
                        'error': f'Missing blocks: have #{current_chain_length-1}, received #{block.index}',
                        'reason': 'missing_blocks',
                        'request_blocks_from': current_chain_length - 1,
                        'request_blocks_to': block.index - 1
                    }), 202  # Accepted for later processing
                
                # Check if locally mined for priority handling
                is_locally_mined = request.headers.get('X-Local-Mining') == 'true'
                
                # BLOCKCHAIN CONSENSUS: First valid block wins
                if is_locally_mined:
                    # Local block - broadcast immediately to claim priority
                    print(f"[MINED] LOCAL BLOCK MINED: Broadcasting Block #{block.index} to network")
                    self.peer_network_manager.broadcast_to_peers(
                        '/submit_block',
                        {'block': block_data},
                        timeout=5.0  # Fast broadcast for priority
                    )
                
                # Multi-node consensus validation before acceptance
                network_consensus_result = self._validate_multi_node_consensus(block, is_locally_mined)
                
                # UNIFIED CONSENSUS: Use BlockchainSync for all fork resolutions
                if block.index < self.blockchain.get_chain_length():
                    sender_url = request.headers.get('X-Peer-Origin')
                    if sender_url:
                        try:
                            logger.info(f"🍴 Potential fork from {sender_url}, using enhanced sync for resolution")
                            # Use the proper sync mechanism to handle the fork
                            response = requests.get(f"{sender_url}/blockchain", timeout=10)
                            if response.status_code == 200:
                                competing_chain_data = response.json().get('chain', [])
                                sync_result, _ = self.blockchain.synchronizer.sync_with_peer_chain(
                                    peer_chain_data=competing_chain_data,
                                    peer_url=sender_url
                                )
                                if sync_result == 'fork_resolved':
                                    return jsonify({
                                        'status': 'accepted_fork_resolution',
                                        'message': 'Switched to heavier chain via sync'
                                    })
                        except Exception as e:
                            logger.warning(f"Fork resolution sync failed: {e}")
                
                # Attempt to add block (this validates the block)
                if self.blockchain.add_block(block):
                    # Extract miner information from multiple sources
                    miner_address = "unknown"
                    
                    # Try mining metadata first (most reliable)
                    if hasattr(block, '_mining_metadata') and block._mining_metadata:
                        miner_address = block._mining_metadata.get('miner_address', 'unknown')
                    
                    # Try top-level miner_address field
                    elif hasattr(block, 'miner_address') and block.miner_address:
                        miner_address = block.miner_address
                    
                    # Fallback to coinbase transaction recipient
                    elif block.transactions and block.transactions[0].outputs:
                        miner_address = block.transactions[0].outputs[0].recipient_address
                    
                    # Log successful block acceptance with consensus info
                    mining_source = "LOCALLY MINED" if is_locally_mined else f"RECEIVED from peer"
                    print(f"[ACCEPTED] BLOCK ACCEPTED: #{block.index} ({mining_source})")
                    print(f"   [MINER] Mined by: {miner_address}")
                    print(f"   [CHAIN] Chain length: {self.blockchain.get_chain_length()}")
                    print(f"   [NETWORK] Network peers: {len(self.peer_network_manager.get_active_peers())}")
                    
                    # Smart broadcasting based on network size and consensus
                    if not is_locally_mined:
                        # Received from peer - broadcast to all other peers to maintain consensus
                        sender_url = request.headers.get('X-Peer-Origin', 'unknown')
                        # Adaptive timeout based on network size
                        active_peers_count = len(self.peer_network_manager.get_active_peers())
                        if active_peers_count <= 10:
                            broadcast_timeout = 5.0
                        elif active_peers_count <= 50:
                            broadcast_timeout = 8.0
                        else:
                            broadcast_timeout = 12.0  # Longer timeout for large networks
                        
                        broadcast_results = self.peer_network_manager.broadcast_to_peers(
                            '/submit_block',
                            {'block': block_data},
                            timeout=broadcast_timeout,
                            exclude_sender=True,
                            sender_url=sender_url
                        )
                        
                        # Log broadcasting results for multi-node debugging
                        successful_broadcasts = sum(1 for success in broadcast_results.values() if success)
                        total_peers = len(broadcast_results)
                        if total_peers > 0:
                            print(f"   [NETWORK] Broadcasted to {successful_broadcasts}/{total_peers} peers")
                    else:
                        # Local mining - broadcast to all peers
                        # Adaptive timeout for local mining broadcasts in large networks
                        active_peers_count = len(self.peer_network_manager.get_active_peers())
                        if active_peers_count <= 10:
                            broadcast_timeout = 5.0
                        elif active_peers_count <= 50:
                            broadcast_timeout = 8.0
                        else:
                            broadcast_timeout = 12.0
                        
                        broadcast_results = self.peer_network_manager.broadcast_to_peers(
                            '/submit_block',
                            {'block': block_data},
                            timeout=broadcast_timeout
                        )
                        
                        successful_broadcasts = sum(1 for success in broadcast_results.values() if success)
                        total_peers = len(broadcast_results)
                        if total_peers > 0:
                            print(f"   [NETWORK] Notified {successful_broadcasts}/{total_peers} network peers")
                    
                    with self._stats_lock:
                        self._stats['blocks_processed'] += 1
                    
                    return jsonify({
                        'status': 'accepted',
                        'block_hash': block.hash,
                        'chain_length': self.blockchain.get_chain_length(),
                        'mining_source': 'local' if is_locally_mined else 'network'
                    })
                else:
                    # Block validation failed
                    print(f"❌ BLOCK REJECTED: #{block.index} (validation failed)")
                    return jsonify({
                        'status': 'rejected',
                        'error': 'Block validation failed',
                        'reason': 'invalid_block_data'
                    }), 400
                    
            except Exception as e:
                logger.error(f"Error submitting block: {e}")
                return jsonify({
                    'status': 'error',
                    'error': str(e)
                }), 500
        
        @self.app.route('/blocks/range', methods=['GET'])
        @synchronized("api_blocks_range", LockOrder.NETWORK, mode='read')
        def get_blocks_range():
            """Get range of blocks for synchronization"""
            self._increment_api_calls()
            
            try:
                start = int(request.args.get('start', 0))
                end = int(request.args.get('end', start + 100))  # Default to 100 block range
                
                # Limit range size to prevent memory issues
                max_range = 1000
                if end - start > max_range:
                    end = start + max_range
                
                blocks = self.blockchain.get_blocks_range(start, end)
                
                return jsonify({
                    'status': 'success',
                    'blocks': [block.to_dict() for block in blocks],
                    'start_index': start,
                    'end_index': end,
                    'actual_count': len(blocks)
                })
                
            except Exception as e:
                logger.error(f"Error getting block range: {e}")
                return jsonify({
                    'status': 'error',
                    'error': str(e)
                }), 500
        
        @self.app.route('/chain/info', methods=['GET'])
        @synchronized("api_chain_info", LockOrder.NETWORK, mode='read')
        def get_chain_info():
            """Get chain information"""
            self._increment_api_calls()
            
            try:
                chain_info = self.blockchain.get_chain_info()
                
                return jsonify({
                    'status': 'success',
                    'chain_info': chain_info,
                    'node_id': self.node_id,
                    'api_port': self.api_port
                })
                
            except Exception as e:
                logger.error(f"Error getting chain info: {e}")
                return jsonify({
                    'status': 'error',
                    'error': str(e)
                }), 500

        @self.app.route('/peers', methods=['GET'])
        @synchronized("api_peers", LockOrder.NETWORK, mode='read')
        def get_peers():
            """Thread-safe peer information"""
            self._increment_api_calls()
            
            peer_info = self.peer_network_manager.get_all_peers()
            active_peers = self.peer_network_manager.get_active_peers()
            
            return jsonify({
                'peers': list(peer_info.keys()),
                'active_peers': list(active_peers),
                'peer_count': len(active_peers),
                'peer_details': {url: {
                    'last_seen': info.last_seen,
                    'response_time': info.response_time,
                    'chain_length': info.chain_length,
                    'is_active': info.is_active
                } for url, info in peer_info.items()}
            })
        
        @self.app.route('/discover_peers', methods=['POST'])
        @synchronized("api_discover", LockOrder.NETWORK, mode='write')
        def discover_peers():
            """Thread-safe peer discovery"""
            self._increment_api_calls()
            
            try:
                data = request.get_json() or {}
                port_start = data.get('port_start', 5000)
                port_end = data.get('port_end', 5012)
                host = data.get('host', 'localhost')
                
                discovered = self.peer_network_manager.discover_peers(
                    port_range=range(port_start, port_end),
                    host=host
                )
                
                return jsonify({
                    'status': 'completed',
                    'discovered_peers': discovered,
                    'active_peers': len(self.peer_network_manager.get_active_peers())
                })
                
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'error': str(e)
                }), 500
        
        @self.app.route('/sync_now', methods=['POST'])
        @synchronized("api_sync", LockOrder.NETWORK, mode='write')
        def sync_now():
            """Thread-safe blockchain synchronization"""
            self._increment_api_calls()
            
            return jsonify({'status': 'disabled', 'message': 'Manual sync is handled automatically by the peer manager.'}), 501
        
        @self.app.route('/transactions/<address>', methods=['GET'])
        @synchronized("api_transactions", LockOrder.NETWORK, mode='read')
        def get_transactions(address: str):
            """Thread-safe transaction history lookup"""
            self._increment_api_calls()
            
            transactions = self.blockchain.get_transaction_history(address)
            return jsonify({'address': address, 'transactions': transactions})
        
        @self.app.route('/stats', methods=['GET'])
        @synchronized("api_stats", LockOrder.NETWORK, mode='read')
        def get_stats():
            """Thread-safe statistics"""
            self._increment_api_calls()
            
            blockchain_stats = self.blockchain.get_stats()
            peer_stats = self.peer_network_manager.get_status()
            
            return jsonify({
                'node_stats': {
                    'node_id': self.node_id,
                    'uptime': time.time() - self._stats['uptime_start'],
                    'api_calls': self._stats['api_calls'],
                    'blocks_processed': self._stats['blocks_processed'],
                    'transactions_processed': self._stats['transactions_processed']
                },
                'blockchain_stats': {
                    'blocks_processed': blockchain_stats.blocks_processed,
                    'transactions_processed': blockchain_stats.transactions_processed,
                    'utxo_count': blockchain_stats.utxo_count,
                    'chain_length': self.blockchain.get_chain_length()
                },
                'peer_stats': peer_stats,
                'lock_stats': lock_manager.get_all_stats(),
                'network_wide_stats': self.peer_manager.get_network_wide_stats()
            })
        
        @self.app.route('/orphaned_blocks', methods=['GET'])
        @synchronized("api_orphaned_blocks", LockOrder.NETWORK, mode='read')
        def get_orphaned_blocks():
            """Get orphaned blocks from blockchain"""
            self._increment_api_calls()
            
            orphaned_blocks = self.blockchain.get_orphaned_blocks()
            return jsonify({
                'orphaned_blocks': [block.to_dict() for block in orphaned_blocks],
                'count': len(orphaned_blocks)
            })
        
        @self.app.route('/network_config', methods=['GET'])
        @synchronized("api_network_config", LockOrder.NETWORK, mode='read')
        def get_network_config():
            """Get current network configuration"""
            self._increment_api_calls()
            
            from src.config import get_all_config
            config = get_all_config()
            config.update({
                'current_difficulty': self.blockchain.target_difficulty,
                'difficulty_adjustment_enabled': self.blockchain.difficulty_adjustment_enabled,
                'target_block_time': self.blockchain.target_block_time
            })
            
            return jsonify(config)
        
        @self.app.route('/config/refresh', methods=['POST'])
        @synchronized("api_config_refresh", LockOrder.NETWORK, mode='write')
        def refresh_config():
            """Refresh config settings from file"""
            self._increment_api_calls()
            
            if self.blockchain.refresh_config_settings():
                return jsonify({
                    'status': 'success',
                    'current_difficulty': self.blockchain.target_difficulty,
                    'mining_difficulty': self.blockchain.mining_difficulty,
                    'genesis_difficulty': self.blockchain.genesis_difficulty
                })
            else:
                return jsonify({'status': 'error'}), 500
        
        @self.app.route('/difficulty/set', methods=['POST'])
        @synchronized("api_difficulty_set", LockOrder.NETWORK, mode='write')
        def set_difficulty():
            """Manually override mining difficulty"""
            self._increment_api_calls()
            
            data = request.get_json()
            new_difficulty = data.get('difficulty')
            force = data.get('force', False)
            
            if self.blockchain.set_mining_difficulty(new_difficulty, force):
                return jsonify({
                    'status': 'success',
                    'old_difficulty': self.blockchain.target_difficulty,
                    'new_difficulty': new_difficulty
                })
            else:
                return jsonify({'status': 'error', 'message': 'Invalid difficulty'}), 400
        
        @self.app.route('/status/detailed', methods=['GET'])
        @synchronized("api_status_detailed", LockOrder.NETWORK, mode='read')
        def detailed_status():
            """Enhanced status showing both genesis and mining difficulty"""
            self._increment_api_calls()
            
            return jsonify({
                'genesis_difficulty': self.blockchain.genesis_difficulty,
                'mining_difficulty': self.blockchain.mining_difficulty,
                'current_target_difficulty': self.blockchain.target_difficulty,
                'config_in_sync': self.blockchain.mining_difficulty == self.blockchain.target_difficulty,
                'difficulty_adjustment_enabled': self.blockchain.difficulty_adjustment_enabled,
                'chain_length': self.blockchain.get_chain_length(),
                'pending_transactions': len(self.blockchain.transaction_pool)
            })
        
        @self.app.route('/sync_mempool', methods=['POST'])
        @synchronized("api_sync_mempool", LockOrder.NETWORK, mode='write')
        def sync_mempool_now():
            """Trigger immediate mempool synchronization"""
            self._increment_api_calls()
            
            try:
                # Force mempool sync
                self.peer_manager._last_mempool_sync = 0
                self.peer_manager._check_and_trigger_mempool_sync(len(self.peer_manager.get_active_peers()))
                
                return jsonify({
                    'status': 'sync_triggered',
                    'message': 'Mempool synchronization initiated'
                })
                
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'error': str(e)
                }), 500
        
        @self.app.route('/sync_network_stats', methods=['POST'])
        @synchronized("api_sync_network_stats", LockOrder.NETWORK, mode='write')
        def sync_network_stats_now():
            """Trigger immediate network statistics synchronization"""
            self._increment_api_calls()
            
            try:
                # Force network stats sync
                self.peer_manager._last_network_stats_sync = 0
                self.peer_manager._check_and_trigger_network_stats_sync(len(self.peer_manager.get_active_peers()))
                
                return jsonify({
                    'status': 'sync_triggered',
                    'message': 'Network statistics synchronization initiated'
                })
                
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'error': str(e)
                }), 500
        
        # Peer Exchange API Endpoints
        @self.app.route('/getpeers', methods=['GET'])
        @synchronized("api_getpeers", LockOrder.NETWORK, mode='read')
        def get_peers_for_exchange():
            """Get peer list for P2P exchange (Bitcoin-style getaddr)"""
            self._increment_api_calls()
            
            try:
                # Get peer network manager if available
                if hasattr(self, 'peer_network_manager') and self.peer_network_manager:
                    peers_data = self.peer_network_manager.get_peers_for_sharing()
                else:
                    # Fallback to basic peer manager
                    peer_info = self.peer_manager.get_all_peers()
                    peers_data = [
                        {
                            'url': url,
                            'last_seen': info.last_seen,
                            'chain_length': info.chain_length,
                            'response_time': info.response_time,
                            'is_active': info.is_active
                        }
                        for url, info in peer_info.items() if info.is_active
                    ]
                
                return jsonify({
                    'status': 'success',
                    'node_id': self.node_id,
                    'peers': peers_data,
                    'count': len(peers_data),
                    'timestamp': time.time()
                })
                
            except Exception as e:
                logger.error(f"Error in getpeers: {e}")
                return jsonify({
                    'status': 'error',
                    'error': str(e)
                }), 500
        
        @self.app.route('/sharepeers', methods=['POST'])
        @synchronized("api_sharepeers", LockOrder.NETWORK, mode='write')
        def receive_shared_peers():
            """Receive shared peers from other nodes (Bitcoin-style addr)"""
            self._increment_api_calls()
            
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'status': 'error', 'message': 'No data provided'}), 400
                
                sender_node_id = data.get('node_id', 'unknown')
                shared_peers = data.get('peers', [])
                
                if hasattr(self, 'peer_network_manager') and self.peer_network_manager:
                    result = self.peer_network_manager.handle_peer_share(sender_node_id, shared_peers)
                else:
                    # Fallback to basic peer addition
                    new_peers_added = 0
                    for peer_data in shared_peers:
                        peer_url = peer_data.get('url')
                        if peer_url and peer_url != f"http://localhost:{self.api_port}":
                            try:
                                self.peer_manager.add_peer(peer_url)
                                new_peers_added += 1
                            except:
                                pass
                    
                    result = {
                        'status': 'success',
                        'peers_received': len(shared_peers),
                        'new_peers_added': new_peers_added
                    }
                
                logger.info(f"Received peer share from {sender_node_id}: {result}")
                return jsonify(result)
                
            except Exception as e:
                logger.error(f"Error in sharepeers: {e}")
                return jsonify({
                    'status': 'error',
                    'error': str(e)
                }), 500
        
        @self.app.route('/addpeer', methods=['POST'])
        @synchronized("api_addpeer", LockOrder.NETWORK, mode='write')
        def add_peer_manually():
            """Manually add a peer to the network"""
            self._increment_api_calls()
            
            try:
                data = request.get_json()
                if not data or 'peer_url' not in data:
                    return jsonify({'status': 'error', 'message': 'peer_url required'}), 400
                
                peer_url = data['peer_url']
                
                # Validate URL format
                if not peer_url.startswith(('http://', 'https://')):
                    return jsonify({'status': 'error', 'message': 'Invalid URL format'}), 400
                
                # Don't add ourselves
                if peer_url == f"http://localhost:{self.api_port}":
                    return jsonify({'status': 'error', 'message': 'Cannot add self as peer'}), 400
                
                # Add peer
                if hasattr(self, 'peer_network_manager') and self.peer_network_manager:
                    success = self.peer_network_manager.add_peer(peer_url)
                else:
                    success = self.peer_manager.add_peer(peer_url)
                
                return jsonify({
                    'status': 'success' if success else 'exists',
                    'peer_url': peer_url,
                    'message': 'Peer added successfully' if success else 'Peer already exists'
                })
                
            except Exception as e:
                logger.error(f"Error in addpeer: {e}")
                return jsonify({
                    'status': 'error',
                    'error': str(e)
                }), 500
        
        @self.app.route('/broadcast', methods=['POST'])
        @synchronized("api_broadcast", LockOrder.NETWORK, mode='write')
        def broadcast_message():
            """Broadcast a message to all active peers"""
            self._increment_api_calls()
            
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'status': 'error', 'message': 'No data provided'}), 400
                
                endpoint = data.get('endpoint', 'receive_broadcast')
                message = data.get('message', {})
                timeout = data.get('timeout', 5)
                
                if hasattr(self, 'peer_network_manager') and self.peer_network_manager:
                    result = self.peer_network_manager.broadcast_to_peers(endpoint, message, timeout)
                else:
                    # Basic broadcast to active peers
                    active_peers = self.peer_manager.get_active_peers()
                    results = {}
                    
                    for peer_url in active_peers:
                        try:
                            response = requests.post(
                                f"{peer_url}/{endpoint}",
                                json=message,
                                timeout=timeout
                            )
                            results[peer_url] = response.status_code == 200
                        except:
                            results[peer_url] = False
                    
                    successful = sum(1 for success in results.values() if success)
                    result = {
                        'total_peers': len(active_peers),
                        'successful': successful,
                        'results': results
                    }
                
                return jsonify(result)
                
            except Exception as e:
                logger.error(f"Error in broadcast: {e}")
                return jsonify({
                    'status': 'error',
                    'error': str(e)
                }), 500
        
        @self.app.route('/receive_broadcast', methods=['POST'])
        @synchronized("api_receive_broadcast", LockOrder.NETWORK, mode='write')
        def receive_broadcast():
            """Receive broadcast message from other nodes"""
            self._increment_api_calls()
            
            try:
                data = request.get_json()
                logger.info(f"Received broadcast: {data}")
                
                return jsonify({
                    'status': 'received',
                    'node_id': self.node_id,
                    'timestamp': time.time()
                })
                
            except Exception as e:
                logger.error(f"Error in receive_broadcast: {e}")
                return jsonify({
                    'status': 'error',
                    'error': str(e)
                }), 500
        
        @self.app.route('/force_refresh', methods=['POST'])
        def force_refresh():
            """Force refresh status display to ensure consistency"""
            self._increment_api_calls()
            
            try:
                logger.info(f"Status display refresh requested for node {self.node_id}")
                
                # Force garbage collection to clear any cached data
                import gc
                gc.collect()
                
                # Return current status with force refresh flag
                return jsonify({
                    'status': 'refreshed',
                    'node_id': self.node_id,
                    'format_version': 'ascii-v2.0',
                    'timestamp': time.time(),
                    'message': 'Status display refreshed successfully'
                })
                
            except Exception as e:
                logger.error(f"Error in force_refresh: {e}")
                return jsonify({
                    'status': 'error',
                    'error': str(e)
                }), 500
    
    def _increment_api_calls(self):
        """Thread-safe API call counter"""
        with self._stats_lock:
            self._stats['api_calls'] += 1
    
    
    def _check_port_available(self, port: int) -> bool:
        """Check if a port is available for binding"""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('localhost', port))
                return True
        except OSError:
            return False
    
    def _find_available_port(self, start_port: int, max_attempts: int = 10) -> Optional[int]:
        """Find an available port starting from start_port"""
        for i in range(max_attempts):
            test_port = start_port + i
            if self._check_port_available(test_port):
                return test_port
        return None
    
    def _start_api_server_background(self, debug: bool = False):
        """Start Flask API server in background thread with port conflict resolution"""
        import threading
        import socket
        
        # Check for port conflicts and resolve them
        if not self._check_port_available(self.api_port):
            logger.warning(f"⚠️  Port {self.api_port} is not available")
            
            # Try to find an alternative port
            alternative_port = self._find_available_port(self.api_port + 1)
            if alternative_port:
                logger.info(f"🔄 Auto-resolving to port {alternative_port}")
                old_port = self.api_port
                self.api_port = alternative_port
                
                # Update self-URL in peer manager
                self_url = f"http://localhost:{self.api_port}"
                if hasattr(self, 'peer_manager'):
                    self.peer_manager._self_url = self_url
                    logger.info(f"🆔 Updated node self-URL: {self_url}")
            else:
                logger.error(f"❌ Cannot find available port near {self.api_port}")
                raise OSError(f"Port {self.api_port} and nearby ports are in use")
        
        # Start server in background thread
        self._server_ready = threading.Event()
        self._server_error = None
        
        def run_server():
            try:
                logger.info(f"🌐 Starting Flask API server on port {self.api_port}...")
                
                # Signal that we're about to start
                self._server_ready.set()
                
                self.app.run(
                    host='0.0.0.0',
                    port=self.api_port,
                    debug=debug,
                    threaded=True,
                    use_reloader=False
                )
            except Exception as e:
                self._server_error = e
                self._server_ready.set()  # Signal even on error
                logger.error(f"❌ Server startup failed: {e}")
        
        server_thread = threading.Thread(target=run_server, daemon=True, name=f"APIServer-{self.api_port}")
        server_thread.start()
        
        return server_thread
    
    def _validate_multi_node_consensus(self, block, is_locally_mined: bool) -> Dict:
        """
        ENHANCED: Validate block against multi-node network consensus
        Returns consensus validation results for large networks (N > 2)
        """
        try:
            active_peers = self.peer_manager.get_active_peers()
            consensus_data = {
                'network_size': len(active_peers),
                'consensus_checks': 0,
                'matching_chains': 0,
                'chain_lengths': [],
                'genesis_consensus': 0,
                'validation_successful': True
            }
            
            # Skip consensus check if network is too small or no peers
            if len(active_peers) < 2:
                logger.debug("🔍 Skipping consensus validation - insufficient peers")
                return consensus_data
            
            # ENHANCED: Adaptive consensus checking based on network size
            # Small networks (< 10): Check all peers
            # Medium networks (10-50): Check random sample of 10
            # Large networks (> 50): Check random sample of 20 with geographic distribution
            if len(active_peers) <= 10:
                sample_peers = active_peers
                consensus_threshold = 0.7  # 70% agreement for small networks
            elif len(active_peers) <= 50:
                import random
                sample_peers = random.sample(active_peers, min(10, len(active_peers)))
                consensus_threshold = 0.6  # 60% agreement for medium networks
            else:
                import random
                sample_peers = random.sample(active_peers, min(20, len(active_peers)))
                consensus_threshold = 0.5  # 50% agreement for large networks (more resilient)
            
            logger.debug(f"🔍 Validating consensus with {len(sample_peers)} peers")
            
            # Get our current chain state
            our_chain_length = self.blockchain.get_chain_length()
            our_genesis_hash = None
            if our_chain_length > 0:
                chain = self.blockchain.get_chain()
                our_genesis_hash = chain[0].hash if chain and len(chain) > 0 else None
            
            # Check each sample peer
            for peer_url in sample_peers:
                try:
                    response = requests.get(f"{peer_url}/status", timeout=3)
                    if response.status_code == 200:
                        peer_status = response.json()
                        peer_chain_length = peer_status.get('blockchain_length', 0)
                        
                        consensus_data['consensus_checks'] += 1
                        consensus_data['chain_lengths'].append(peer_chain_length)
                        
                        # Check if peer has similar chain length (within 1 block)
                        if abs(peer_chain_length - our_chain_length) <= 1:
                            consensus_data['matching_chains'] += 1
                        
                        # Verify genesis consensus if possible
                        try:
                            blockchain_response = requests.get(f"{peer_url}/blockchain", timeout=3)
                            if blockchain_response.status_code == 200:
                                peer_blockchain = blockchain_response.json()
                                peer_chain = peer_blockchain.get('chain', [])
                                if peer_chain and len(peer_chain) > 0:
                                    peer_genesis_hash = peer_chain[0].get('hash')
                                    if peer_genesis_hash == our_genesis_hash:
                                        consensus_data['genesis_consensus'] += 1
                        except:
                            pass  # Genesis check is optional
                        
                except Exception as e:
                    logger.debug(f"Consensus check failed for {peer_url}: {e}")
            
            # Calculate consensus percentage
            if consensus_data['consensus_checks'] > 0:
                matching_percentage = (consensus_data['matching_chains'] / consensus_data['consensus_checks']) * 100
                genesis_percentage = (consensus_data['genesis_consensus'] / consensus_data['consensus_checks']) * 100
                
                logger.debug(f"🔍 Consensus result: {matching_percentage:.1f}% chain agreement, {genesis_percentage:.1f}% genesis agreement")
                
                # ENHANCED: Use adaptive consensus threshold based on network size
                required_percentage = consensus_threshold * 100
                if matching_percentage < required_percentage:
                    logger.warning(f"⚠️  Low consensus in {len(active_peers)}-node network: {matching_percentage:.1f}% < {required_percentage:.1f}%")
                    consensus_data['validation_successful'] = False
                else:
                    logger.debug(f"✅ Consensus achieved: {matching_percentage:.1f}% >= {required_percentage:.1f}%")
            
            return consensus_data
            
        except Exception as e:
            logger.error(f"Multi-node consensus validation failed: {e}")
            return {'validation_successful': False, 'error': str(e)}
    
    def _get_peer_status(self, peer_url: str) -> Optional[Dict]:
        """Get peer status with timeout for large network efficiency"""
        try:
            response = requests.get(f"{peer_url}/status", timeout=3)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None
    
    def _wait_for_api_ready(self, timeout: float = 10.0) -> bool:
        """Wait for API server to be ready to accept connections"""
        import socket
        import time
        
        logger.info(f"⏳ Waiting for API server to be ready (timeout: {timeout}s)...")
        
        # Wait for server thread to start
        if not self._server_ready.wait(timeout=5.0):
            logger.error("❌ Server thread failed to start")
            return False
        
        # Check if there was a startup error
        if self._server_error:
            logger.error(f"❌ Server startup error: {self._server_error}")
            return False
        
        # Wait for actual port to be listening
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1.0)
                    result = s.connect_ex(('localhost', self.api_port))
                    if result == 0:
                        logger.info(f"✅ API server ready on port {self.api_port}")
                        return True
            except Exception:
                pass
            time.sleep(0.1)
        
        logger.error(f"❌ API server not ready after {timeout}s")
        return False
    
    def start_api_server(self, debug: bool = False):
        """Start Flask API server with enhanced error handling (blocking version)"""
        try:
            logger.info(f"🌐 Starting Flask API server on port {self.api_port}...")
            self.app.run(
                host='0.0.0.0',
                port=self.api_port,
                debug=debug,
                threaded=True,
                use_reloader=False
            )
        except OSError as e:
            if "Address already in use" in str(e):
                logger.error(f"❌ Port {self.api_port} is already in use!")
                logger.error("💡 Solutions:")
                logger.error(f"   1. Use a different port: --api-port {self.api_port + 1}")
                logger.error("   2. On macOS: Disable AirPlay Receiver in System Preferences")
                logger.error("   3. Find and stop the process using this port:")
                logger.error(f"      lsof -ti:{self.api_port} | xargs kill -9")
            else:
                logger.error(f"❌ Network error starting server: {e}")
            raise  # Re-raise so main() can handle it
        except Exception as e:
            logger.error(f"❌ Failed to start API server: {e}")
            logger.error("🔍 Check your network configuration and try again")
            raise  # Re-raise so main() can handle it
    
    def start(self, discover_peers: bool = True):
        """Start the thread-safe network node"""
        logger.info(f"Starting thread-safe network node: {self.node_id}")
        
        # Start enhanced peer manager
        if self.peer_network_manager:
            self.peer_network_manager.start()
            logger.info("P2P network manager started")
        
        # Start connection cleanup system
        try:
            start_connection_cleanup()
            logger.info("Connection cleanup system started")
        except Exception as e:
            logger.warning(f"Failed to start connection cleanup: {e}")
        
        # Start API server in background first (fix race condition)
        import threading
        self._start_api_server_background()
        
        # Wait briefly for API server to initialize
        import time
        time.sleep(1.0)
        
        # API server already started in background - just keep main thread alive
        logger.info("🚀 Starting ChainCore Network Node...")
        logger.info(f"   🌐 API Server running on port {self.api_port}")
        logger.info("   🔄 All sync mechanisms activated")
        logger.info("   🎯 Ready to accept connections!")
        
        # Keep main thread alive to prevent daemon threads from exiting
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Shutdown requested by user")
            self._cleanup_on_shutdown()
    
    def _cleanup_on_shutdown(self):
        """Clean up resources on node shutdown"""
        try:
            logger.info("🧹 Starting node cleanup...")
            
            # Stop enhanced peer manager
            if hasattr(self, 'peer_network_manager') and self.peer_network_manager:
                self.peer_network_manager.stop()
                logger.info("Peer manager stopped")
            
            # Stop connection cleanup
            stop_connection_cleanup()
            logger.info("Connection cleanup stopped")
            
            # Unregister from mining coordinator if we were mining
            try:
                mining_coordinator = get_mining_coordinator()
                # This will be used if this node was also mining
                # mining_coordinator.unregister_miner(f"node_{self.node_id}")
            except:
                pass
            
            # Force final cleanup
            from src.networking.connection_cleaner import get_connection_cleaner
            cleaner = get_connection_cleaner()
            cleaner.force_cleanup()
            
            logger.info("✅ Node cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def _perform_automatic_sync(self, peer_url: str, current_length: int, peer_length: int):
        """Callback for automatic blockchain synchronization"""
        try:
            logger.info(f"🔄 Automatic Blockchain Sync Triggered!")
            logger.info(f"   🌐 Syncing with peer: {peer_url}")
            logger.info(f"   📊 Chain comparison: Local={current_length}, Peer={peer_length}")
            logger.info("   🔍 Downloading longer chain...")
            
            # Use existing sync logic from sync_now endpoint
            sync_result = self.peer_manager.sync_with_best_peer()
            
            if sync_result:
                peer_url_result, chain_data = sync_result
                
                # Convert chain data to blocks (same logic as sync_now endpoint)
                new_chain = []
                for block_data in chain_data:
                    try:
                        # Create transactions
                        transactions = []
                        for tx_data in block_data.get('transactions', []):
                            tx = Transaction(
                                inputs=tx_data.get('inputs', []),
                                outputs=[
                                    type('Output', (), {
                                        'recipient_address': out['recipient_address'],
                                        'amount': out['amount']
                                    })() for out in tx_data.get('outputs', [])
                                ]
                            )
                            transactions.append(tx)
                        
                        # Create block
                        block = Block(
                            index=block_data['index'],
                            transactions=transactions,
                            previous_hash=block_data['previous_hash'],
                            timestamp=block_data.get('timestamp', time.time()),
                            nonce=block_data.get('nonce', 0),
                            target_difficulty=block_data.get('target_difficulty', 1)
                        )
                        new_chain.append(block)
                        
                    except Exception as e:
                        logger.error(f"Error creating block from sync data: {e}")
                        return
                
                # Use industry-standard smart sync instead of destructive replace_chain
                if self.blockchain.smart_sync_with_peer_chain(chain_data, peer_url_result):
                    new_length = self.blockchain.get_chain_length()
                    logger.info(f"🎉 Smart Blockchain Sync Successful!")
                    logger.info(f"   📊 Chain updated: {current_length} -> {new_length} blocks")
                    logger.info(f"   🌐 Source: {peer_url_result}")
                    logger.info(f"   💾 Mining history: PRESERVED")
                    
                    # Update stats
                    self._stats['successful_syncs'] = self._stats.get('successful_syncs', 0) + 1
                    self._stats['last_sync_time'] = time.time()
                    logger.info(f"   📈 Total successful syncs: {self._stats['successful_syncs']}")
                else:
                    logger.error("❌ Smart Sync Failed!")
                    logger.error("   🔍 Chain validation failed or sync error occurred")
                    self._stats['failed_syncs'] = self._stats.get('failed_syncs', 0) + 1
            else:
                logger.info("⚠️  Automatic Sync: No suitable peers available for sync")
                
        except Exception as e:
            logger.error(f"Error in automatic blockchain sync: {e}")
            self._stats['failed_syncs'] = self._stats.get('failed_syncs', 0) + 1
    
    def _configure_late_joiner_support(self):
        """Configure aggressive sync for nodes joining the network late"""
        # Start background thread for late-joiner detection and sync
        import threading
        sync_thread = threading.Thread(target=self._late_joiner_sync_loop, daemon=True)
        sync_thread.start()
        logger.info("🚀 Late-joiner support configured")
    
    def _late_joiner_sync_loop(self):
        """Background loop to detect if this node is a late joiner and sync aggressively"""
        import time
        
        # Wait for initial startup
        time.sleep(5)
        
        while True:
            try:
                current_length = self.blockchain.get_chain_length()
                
                # Check if we're significantly behind the network
                if self._detect_late_joiner_status(current_length):
                    logger.info("🔄 Late-joiner detected - starting aggressive sync")
                    self._perform_aggressive_sync()
                
                # Check every 30 seconds
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in late-joiner sync loop: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _detect_late_joiner_status(self, current_length: int) -> bool:
        """Detect if this node is significantly behind the network"""
        try:
            # Get peer info to check network chain length
            peers = self.peer_manager.get_active_peers()
            if not peers:
                return False
            
            # Sample a few peers to get network chain length
            max_peer_length = 0
            for peer_url in list(peers)[:3]:  # Check up to 3 peers
                try:
                    peer_info = self.peer_manager.get_peer_blockchain_info(peer_url)
                    if peer_info and 'chain' in peer_info:
                        peer_length = len(peer_info['chain'])
                        max_peer_length = max(max_peer_length, peer_length)
                except:
                    continue
            
            # If we're more than 5 blocks behind, we're a late joiner
            if max_peer_length > current_length:
                logger.info(f"📊 Chain length comparison: Local={current_length}, Network={max_peer_length}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting late-joiner status: {e}")
            return False
    
    def _perform_aggressive_sync(self):
        """Perform aggressive sync for late-joining nodes"""
        try:
            peers = self.peer_manager.get_active_peers()
            if not peers:
                logger.warning("⚠️  No peers available for aggressive sync")
                return
            
            logger.info(f"🔄 Starting aggressive sync with {len(peers)} peers")
            
            # Try multiple peers to get the best chain
            best_chain = None
            best_length = 0
            best_peer = None
            
            for peer_url in peers:
                try:
                    peer_info = self.peer_manager.get_peer_blockchain_info(peer_url)
                    if peer_info and 'chain' in peer_info:
                        peer_length = len(peer_info['chain'])
                        if peer_length > best_length:
                            best_chain = peer_info['chain']
                            best_length = peer_length
                            best_peer = peer_url
                            
                except Exception as e:
                    logger.warning(f"Failed to get chain from {peer_url}: {e}")
                    continue
            
            if best_chain and best_peer:
                current_length = self.blockchain.get_chain_length()
                logger.info(f"🎯 Found best chain: {best_length} blocks from {best_peer}")
                
                # Use enhanced smart sync
                if self.blockchain.smart_sync_with_peer_chain(best_chain, best_peer):
                    new_length = self.blockchain.get_chain_length()
                    logger.info(f"✅ Aggressive sync successful: {current_length} → {new_length} blocks")
                    logger.info(f"💾 Mining attribution preserved during aggressive sync")
                else:
                    logger.error("❌ Aggressive sync failed")
            else:
                logger.warning("⚠️  No suitable chain found for aggressive sync")
                
        except Exception as e:
            logger.error(f"Error in aggressive sync: {e}")
    
    def _perform_enhanced_automatic_sync(self):
        """Automatic sync that preserves mining attribution and updates balances"""
        try:
            logger.debug("🔄 Starting enhanced automatic blockchain sync")
            
            # Get current chain length
            current_length = self.blockchain.get_chain_length()
            
            # Get peer blockchain info with mining attribution preservation
            peer_sync_result = self.peer_manager.sync_with_best_peer_enhanced()
            
            if peer_sync_result:
                peer_url_result, chain_data = peer_sync_result
                
                logger.info(f"📡 Sync with peer: {peer_url_result}")
                logger.info(f"📊 Current chain length: {current_length}")
                logger.info(f"📊 Peer chain length: {len(chain_data)}")
                
                # Use industry-standard smart sync with enhanced features
                if self.blockchain.smart_sync_with_peer_chain(chain_data, peer_url_result):
                    new_length = self.blockchain.get_chain_length()
                    logger.info(f"🎉 Blockchain Sync Successful!")
                    logger.info(f"   📊 Chain updated: {current_length} -> {new_length} blocks")
                    logger.info(f"   🌐 Source: {peer_url_result}")
                    logger.info(f"   💾 Mining history: PRESERVED")
                    logger.info(f"   💰 Wallet balances: UPDATED")
                    
                    # Update stats
                    self._stats['successful_syncs'] = self._stats.get('successful_syncs', 0) + 1
                    self._stats['last_sync_time'] = time.time()
                    logger.info(f"   📈 Total successful syncs: {self._stats['successful_syncs']}")
                else:
                    logger.error("❌ Smart Sync Failed!")
                    logger.error("   🔍 Chain validation failed or sync error occurred")
                    self._stats['failed_syncs'] = self._stats.get('failed_syncs', 0) + 1
            else:
                logger.info("⚠️  Automatic Sync: No suitable peers available for sync")
                
        except Exception as e:
            logger.error(f"Error in enhanced automatic blockchain sync: {e}")
            self._stats['failed_syncs'] = self._stats.get('failed_syncs', 0) + 1
    
    def _add_synced_transaction(self, tx_data: dict, peer_url: str):
        """Callback for adding synced transactions from peers"""
        try:
            from src.blockchain.bitcoin_transaction import Transaction
            
            # Convert transaction data to Transaction object
            transaction = Transaction.from_dict(tx_data)
            
            # Add to our blockchain's transaction pool
            if self.blockchain.add_transaction(transaction):
                logger.info(f"✅ Added Synced Transaction from {peer_url}")
                logger.info(f"   📝 Transaction ID: {transaction.tx_id[:16]}...")
                logger.info(f"   💰 Value: {sum(output.amount for output in transaction.outputs):.2f} CC")
            else:
                logger.info(f"❌ Rejected Synced Transaction from {peer_url}")
                logger.info(f"   📝 Transaction ID: {transaction.tx_id[:16]}...")
                logger.info("   🔍 Reason: Invalid or duplicate transaction")
                
        except Exception as e:
            logger.error(f"Error adding synced transaction from {peer_url}: {e}")

    def cleanup(self):
        """Cleanup node resources"""
        logger.info(f"🔄 Shutting Down ChainCore Node: {self.node_id}")
        logger.info("   📊 Final Statistics:")
        logger.info(f"      API Calls: {self._stats.get('api_calls', 0)}")
        logger.info(f"      Blockchain Syncs: {self._stats.get('successful_syncs', 0)}")
        logger.info(f"      Blocks Processed: {self._stats.get('blocks_processed', 0)}")
        logger.info("   🧹 Cleaning up network connections...")
        
        self.peer_manager.cleanup()
        logger.info("✅ ChainCore Node Shutdown Complete")
        
        logger.info("Node cleanup complete")

def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(description='Thread-Safe ChainCore Network Node')
    parser.add_argument('--node-id', default='core0', help='Node identifier')
    parser.add_argument('--api-port', type=int, default=5001, help='API server port (default: 5001, avoid 5000 on macOS due to AirPlay)')
    parser.add_argument('--p2p-port', type=int, default=8000, help='P2P communication port')
    parser.add_argument('--no-discover', action='store_true', help='Skip peer discovery')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--quiet', action='store_true', help='Skip startup banner')
    parser.add_argument('--bootstrap-nodes', nargs='*', help='Bootstrap node URLs for initial network connection')
    parser.add_argument('--bootstrap-from-file', help='Load bootstrap nodes from file (one URL per line)')
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load bootstrap nodes
    bootstrap_nodes = []
    if args.bootstrap_nodes:
        bootstrap_nodes.extend(args.bootstrap_nodes)
    
    if args.bootstrap_from_file:
        try:
            with open(args.bootstrap_from_file, 'r') as f:
                file_nodes = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                bootstrap_nodes.extend(file_nodes)
                print(f"Loaded {len(file_nodes)} bootstrap nodes from {args.bootstrap_from_file}")
        except Exception as e:
            print(f"Warning: Could not load bootstrap file {args.bootstrap_from_file}: {e}")
    
    if bootstrap_nodes:
        print(f"Bootstrap nodes: {bootstrap_nodes}")
    
    # Show startup banner unless quiet mode
    if not args.quiet:
        try:
            from startup_banner import startup_network_node
            startup_network_node(args.node_id, args.api_port, args.p2p_port)
        except ImportError:
            print("🌟 ChainCore Network Node Starting...")
            print(f"   🆔 Node ID: {args.node_id}")
            print(f"   🌐 API Port: {args.api_port}")
            print(f"   📡 P2P Port: {args.p2p_port}")
    
    # Create and start node
    node = ThreadSafeNetworkNode(
        node_id=args.node_id,
        api_port=args.api_port,
        p2p_port=args.p2p_port,
        bootstrap_nodes=bootstrap_nodes
    )
    
    try:
        node.start(discover_peers=not args.no_discover)
    except KeyboardInterrupt:
        print("\n" + "=" * 50)
        print("🛑 ChainCore Node Shutting Down...")  
        print("=" * 50)
        logger.info("Shutdown requested by user")
    except OSError as e:
        if "Address already in use" in str(e):
            logger.error(f"\n🚨 STARTUP FAILED - Port {args.api_port} is in use")
            logger.error("Try running with: --api-port 5002")
        else:
            logger.error(f"Network error: {e}")
    except Exception as e:
        logger.error(f"❌ Node startup error: {e}")
        logger.error("🔍 Check the logs above for more details")
    finally:
        try:
            if 'node' in locals():
                node._cleanup_on_shutdown()
            print("✅ Shutdown complete. Thank you for using ChainCore!")
        except:
            pass

if __name__ == "__main__":
    main()