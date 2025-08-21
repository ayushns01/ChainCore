#!/usr/bin/env python3
"""
Thread-Safe ChainCore Network Node
Enterprise-grade blockchain node with comprehensive thread safety

This implementation combines the original network_node.py with full thread safety integration.
All original functionality is preserved while adding enterprise-grade concurrency control.

Thread Safety Features:
- Advanced reader-writer locks with deadlock detection
- MVCC UTXO management with snapshot isolation
- Atomic operations for blockchain state changes
- Connection pooling and rate limiting for peers
- Work coordination for mining operations
- Comprehensive statistics and monitoring
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
    ThreadSafeBlockchain, ThreadSafePeerManager, ThreadSafeMiner,
    synchronized, LockOrder, peer_manager, 
    mining_pool, lock_manager
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
    Thread-safe network node with enterprise-grade concurrency control
    """
    
    def __init__(self, node_id: str = "core0", api_port: int = 5000, p2p_port: int = 8000):
        self.node_id = node_id
        self.api_port = api_port
        self.p2p_port = p2p_port
        
        # Thread-safe blockchain
        self.blockchain = ThreadSafeBlockchain()
        
        # Thread-safe peer management
        self.peer_manager = ThreadSafePeerManager()
        
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
        
        
        logger.info("🌟 ChainCore Network Node Successfully Initialized!")
        logger.info(f"   🆔 Node ID: {self.node_id}")
        logger.info(f"   🌐 API Server: http://localhost:{self.api_port}")
        logger.info(f"   📡 P2P Port: {self.p2p_port}")
        logger.info("   ✨ All systems ready!")
    
    def _sync_with_network_before_mining(self) -> Dict:
        """Synchronize with network peers before mining to ensure latest chain state"""
        blocks_added = 0
        
        try:
            # Get active peers
            peers = self.peer_manager.get_active_peers()
            if not peers:
                return {'blocks_added': 0, 'error': 'No peers available'}
            
            current_length = self.blockchain.get_chain_length()
            max_peer_length = current_length
            best_peer = None
            
            # Check all peers for longer chains
            for peer_url in peers:
                try:
                    response = requests.get(f"{peer_url}/blockchain", timeout=5)
                    if response.status_code == 200:
                        peer_data = response.json()
                        peer_chain_length = len(peer_data.get('chain', []))
                        
                        if peer_chain_length > max_peer_length:
                            max_peer_length = peer_chain_length
                            best_peer = peer_url
                            
                except requests.RequestException:
                    continue  # Skip unresponsive peers
            
            # Synchronize if we found a longer chain
            if best_peer and max_peer_length > current_length:
                print(f"   🔄 Found longer chain: {max_peer_length} blocks vs our {current_length}")
                print(f"   📡 Synchronizing with {best_peer}")
                
                # Get the longer chain
                response = requests.get(f"{best_peer}/blockchain", timeout=10)
                if response.status_code == 200:
                    peer_data = response.json()
                    peer_chain = peer_data.get('chain', [])
                    
                    # Add missing blocks
                    for block_data in peer_chain[current_length:]:
                        from src.blockchain.block import Block
                        block = Block.from_dict(block_data)
                        
                        if self.blockchain.add_block(block):
                            blocks_added += 1
                            print(f"     ✅ Added block #{block.index} from network")
                        else:
                            print(f"     ❌ Failed to add block #{block.index}")
                            break
            
            return {'blocks_added': blocks_added}
            
        except Exception as e:
            logger.error(f"Sync error: {e}")
            return {'blocks_added': 0, 'error': str(e)}
    
    def _setup_api_routes(self):
        """Setup all API routes with thread safety"""
        
        @self.app.route('/status', methods=['GET'])
        @synchronized("api_status", LockOrder.NETWORK, mode='read')
        def get_status():
            """Enhanced user-friendly status endpoint with comprehensive information"""
            self._increment_api_calls()
            
            # Get current statistics
            blockchain_length = self.blockchain.get_chain_length()
            pending_txs = len(self.blockchain.get_transaction_pool_copy())
            active_peers = self.peer_manager.get_active_peers()
            peer_stats = self.peer_manager.get_stats()
            uptime_seconds = time.time() - self._stats['uptime_start']
            
            # Calculate uptime in human readable format
            uptime_hours = int(uptime_seconds // 3600)
            uptime_minutes = int((uptime_seconds % 3600) // 60)
            uptime_readable = f"{uptime_hours}h {uptime_minutes}m" if uptime_hours > 0 else f"{uptime_minutes}m"
            
            # Determine network health status
            if len(active_peers) == 0:
                network_status = "isolated"
                network_health = "⚠️  Single Node Mode"
            elif len(active_peers) < self.peer_manager._min_peers:
                network_status = "under_connected"
                network_health = "🔍 Seeking More Peers"
            elif len(active_peers) >= self.peer_manager._target_peers:
                network_status = "well_connected"
                network_health = "🌐 Well Connected"
            else:
                network_status = "connecting"
                network_health = "🔄 Building Network"
            
            # Determine blockchain status
            if blockchain_length <= 1:
                blockchain_status = "genesis"
                blockchain_health = "🏁 Genesis Block Only"
            elif pending_txs == 0:
                blockchain_status = "idle"
                blockchain_health = "💤 No Pending Transactions"
            else:
                blockchain_status = "active"
                blockchain_health = f"⚡ Processing {pending_txs} Transactions"
            
            # Determine node role
            is_main_node = self.peer_manager.get_main_node_status()
            node_role = "🏆 Main Coordinator" if is_main_node else "👥 Peer Node"
            
            # Get mining difficulty status
            difficulty_status = "🔥 Very Hard" if self.blockchain.target_difficulty > 6 else \
                              "⚡ Hard" if self.blockchain.target_difficulty > 4 else \
                              "🟢 Moderate" if self.blockchain.target_difficulty > 2 else \
                              "🟡 Easy"
            
            # Create status summary at top
            status_summary = f"""
╔══════════════════════════════════════════════════════════════════════╗
║                    🚀 CHAINCORE NODE STATUS                          ║
╠══════════════════════════════════════════════════════════════════════╣
║ 🆔 Node: {self.node_id:<20} 🌐 Port: {self.api_port:<20}        ║
║ 🟢 Status: ONLINE & OPERATIONAL      ⏱️  Uptime: {uptime_readable:<15} ║
║ ⛓️  Chain: {blockchain_length:,} blocks{' + ' + str(pending_txs) + ' pending' if pending_txs > 0 else '':20} ║
║ 🌐 Peers: {len(active_peers)} connected {'(Main Node)' if is_main_node else '(Peer Node)':25} ║
║ 🎯 Difficulty: {self.blockchain.target_difficulty} {difficulty_status:<30} ║
║ 🔄 Sync: {blockchain_health:<45} ║
╚══════════════════════════════════════════════════════════════════════╝
            """.strip()

            return jsonify({
                # === 🚀 QUICK STATUS DISPLAY ===
                'STATUS_DISPLAY': status_summary,
                '📊 QUICK_OVERVIEW': {
                    'NODE_ID': self.node_id,
                    'PORT': self.api_port,
                    'STATUS': 'ONLINE',
                    'BLOCKCHAIN_LENGTH': f"{blockchain_length:,} blocks",
                    'PENDING_TXS': pending_txs,
                    'CONNECTED_PEERS': len(active_peers),
                    'NODE_ROLE': 'MAIN' if is_main_node else 'PEER',
                    'UPTIME': uptime_readable,
                    'DIFFICULTY': f"{self.blockchain.target_difficulty} {difficulty_status}",
                    'SYNC_STATUS': blockchain_health
                },
                
                # === OVERVIEW SECTION ===
                'status': 'online',
                'summary': {
                    'node_health': '✅ Operational',
                    'network_status': network_health,
                    'blockchain_status': blockchain_health,
                    'node_role': node_role,
                    'uptime': uptime_readable
                },
                
                # === NODE INFORMATION ===
                'node_info': {
                    'node_id': self.node_id,
                    'api_port': self.api_port,
                    'api_url': f"http://localhost:{self.api_port}",
                    'uptime_seconds': int(uptime_seconds),
                    'uptime_readable': uptime_readable,
                    'version': '1.0',
                    'thread_safe': True,
                    'api_calls_handled': self._stats['api_calls']
                },
                
                # === BLOCKCHAIN STATUS ===
                'blockchain': {
                    'chain_length': blockchain_length,
                    'status': blockchain_status,
                    'status_message': blockchain_health,
                    'latest_block_index': blockchain_length - 1 if blockchain_length > 0 else None,
                    'pending_transactions': pending_txs,
                    'mining_difficulty': self.blockchain.target_difficulty,
                    'difficulty_status': difficulty_status,
                    'genesis_initialized': blockchain_length > 0
                },
                
                # === NETWORK STATUS ===
                'network': {
                    'status': network_status,
                    'status_message': network_health,
                    'active_peers': len(active_peers),
                    'peer_urls': list(active_peers),
                    'is_main_node': is_main_node,
                    'peer_limits': {
                        'minimum_peers': self.peer_manager._min_peers,
                        'target_peers': self.peer_manager._target_peers,
                        'maximum_peers': self.peer_manager._max_peers
                    },
                    'discovery': {
                        'enabled': self.peer_manager._continuous_discovery_enabled,
                        'interval_seconds': self.peer_manager._peer_discovery_interval,
                        'scan_range': f"ports {self.peer_manager._discovery_range[0]}-{self.peer_manager._discovery_range[1]-1}",
                        'total_discoveries': peer_stats.get('discovery_attempts', 0),
                        'successful_connections': peer_stats.get('successful_connections', 0),
                        'failed_connections': peer_stats.get('failed_connections', 0)
                    }
                },
                
                # === SYNCHRONIZATION STATUS ===
                'sync_status': {
                    'blockchain_sync': {
                        'enabled': self.peer_manager._blockchain_sync_enabled,
                        'interval_seconds': self.peer_manager._blockchain_sync_interval,
                        'successful_syncs': self._stats.get('successful_syncs', 0)
                    },
                    'mempool_sync': {
                        'enabled': self.peer_manager._mempool_sync_enabled,
                        'interval_seconds': self.peer_manager._mempool_sync_interval
                    }
                },
                
                # === PERFORMANCE METRICS ===
                'performance': {
                    'blocks_processed': self._stats.get('blocks_processed', 0),
                    'transactions_processed': self._stats.get('transactions_processed', 0),
                    'average_response_time': '< 100ms',  # Placeholder - could be calculated
                    'memory_usage': 'Normal',  # Placeholder - could use psutil
                    'connection_pool_size': len(self.peer_manager._connection_pool._pools)
                },
                
                # === QUICK ACTIONS ===
                'actions': {
                    'available_endpoints': {
                        'mine_block': f"POST {self.api_port}/mine_block",
                        'send_transaction': f"POST {self.api_port}/broadcast_transaction", 
                        'get_blockchain': f"GET {self.api_port}/blockchain",
                        'sync_blockchain': f"POST {self.api_port}/sync_blockchain",
                        'discover_peers': f"POST {self.api_port}/discover_peers"
                    },
                    'health_check_url': f"http://localhost:{self.api_port}/status"
                },
                
                # === LEGACY COMPATIBILITY ===
                'node_id': self.node_id,
                'blockchain_length': blockchain_length,
                'pending_transactions': pending_txs,
                'peers': len(active_peers),
                'target_difficulty': self.blockchain.target_difficulty,
                'uptime': uptime_seconds,
                'thread_safe': True,
                'api_calls': self._stats['api_calls']
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
            <h1>🌐 ChainCore Blockchain Node</h1>
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
                    self.peer_manager.broadcast_to_peers(
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
                    self.peer_manager.broadcast_to_peers(
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
                
                # CRITICAL: Synchronize with network before creating mining template
                print(f"🔄 SYNC CHECK: Ensuring latest blockchain state before mining")
                sync_result = self._sync_with_network_before_mining()
                if sync_result['blocks_added'] > 0:
                    print(f"   📥 Synchronized: Added {sync_result['blocks_added']} blocks from network")
                    print(f"   📊 Updated chain length: {self.blockchain.get_chain_length()}")
                else:
                    print(f"   ✅ Already synchronized with network")
                
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
            """Thread-safe block submission"""
            self._increment_api_calls()
            
            try:
                data = request.get_json()
                block_data = data.get('block', data)  # Handle both formats
                
                # Use Block.from_dict for proper mining attribution preservation
                block = Block.from_dict(block_data)
                
                # If no mining node was preserved, use current node as fallback
                if not hasattr(block, '_mining_metadata') or not block._mining_metadata.get('mining_node'):
                    if not hasattr(block, '_mining_metadata'):
                        block._mining_metadata = {}
                    block._mining_metadata['mining_node'] = f"Node-{self.api_port}"
                
                # CRITICAL: Verify this is the next sequential block
                current_chain_length = self.blockchain.get_chain_length()
                if block.index != current_chain_length:
                    return jsonify({
                        'status': 'rejected', 
                        'error': f'Invalid block index #{block.index}, expected #{current_chain_length}',
                        'reason': 'invalid_block_sequence'
                    }), 409
                
                # Check if locally mined for priority handling
                is_locally_mined = request.headers.get('X-Local-Mining') == 'true'
                
                # BLOCKCHAIN CONSENSUS: First valid block wins
                if is_locally_mined:
                    # Local block - broadcast immediately to claim priority
                    print(f"🏁 LOCAL BLOCK MINED: Broadcasting Block #{block.index} to network")
                    self.peer_manager.broadcast_to_peers(
                        '/submit_block',
                        {'block': block_data},
                        timeout=5.0  # Fast broadcast for priority
                    )
                
                # Attempt to add block (this validates the block)
                if self.blockchain.add_block(block):
                    # Extract miner information
                    miner_address = "unknown"
                    if block.transactions and block.transactions[0].outputs:
                        miner_address = block.transactions[0].outputs[0].recipient_address
                    
                    # Log successful block acceptance
                    mining_source = "LOCALLY MINED" if is_locally_mined else f"RECEIVED from peer"
                    print(f"✅ BLOCK ACCEPTED: #{block.index} ({mining_source})")
                    print(f"   ⛏️  Mined by: {miner_address}")
                    print(f"   📊 Chain length: {self.blockchain.get_chain_length()}")
                    
                    # Broadcast to remaining peers if received from another node
                    if not is_locally_mined:
                        self.peer_manager.broadcast_to_peers(
                            '/submit_block',
                            {'block': block_data},
                            timeout=3.0,
                            exclude_sender=True  # Don't send back to sender
                        )
                    
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
        
        @self.app.route('/peers', methods=['GET'])
        @synchronized("api_peers", LockOrder.NETWORK, mode='read')
        def get_peers():
            """Thread-safe peer information"""
            self._increment_api_calls()
            
            peer_info = self.peer_manager.get_all_peers()
            active_peers = self.peer_manager.get_active_peers()
            
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
                
                discovered = self.peer_manager.discover_peers(
                    port_range=range(port_start, port_end),
                    host=host
                )
                
                return jsonify({
                    'status': 'completed',
                    'discovered_peers': discovered,
                    'active_peers': len(self.peer_manager.get_active_peers())
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
            
            try:
                sync_result = self.peer_manager.sync_with_best_peer()
                
                if sync_result:
                    peer_url, chain_data = sync_result
                    
                    # Convert chain data to blocks
                    new_chain = []
                    for block_data in chain_data:
                        transactions = [Transaction.from_dict(tx) for tx in block_data['transactions']]
                        block = Block(
                            block_data['index'],
                            transactions,
                            block_data['previous_hash'],
                            block_data['timestamp'],
                            block_data.get('nonce', 0),
                            block_data.get('target_difficulty', BLOCKCHAIN_DIFFICULTY)
                        )
                        new_chain.append(block)
                    
                    # Use industry-standard smart sync instead of destructive replace_chain
                    current_length = self.blockchain.get_chain_length()
                    if self.blockchain.smart_sync_with_peer_chain(chain_data, peer_url):
                        new_length = self.blockchain.get_chain_length()
                        return jsonify({
                            'status': 'synced',
                            'peer': peer_url,
                            'old_length': current_length,
                            'new_length': new_length,
                            'mining_history': 'preserved'
                        })
                    else:
                        return jsonify({
                            'status': 'sync_failed',
                            'error': 'Smart sync validation failed'
                        }), 400
                else:
                    return jsonify({
                        'status': 'no_peers',
                        'error': 'No suitable peers found for sync'
                    }), 400
                    
            except Exception as e:
                logger.error(f"Sync error: {e}")
                return jsonify({
                    'status': 'error',
                    'error': str(e)
                }), 500
        
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
            """Comprehensive thread-safe statistics"""
            self._increment_api_calls()
            
            blockchain_stats = self.blockchain.get_stats()
            peer_stats = self.peer_manager.get_stats()
            
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
        
        # Configure continuous peer discovery with proper settings
        from src.config import CONTINUOUS_DISCOVERY_INTERVAL
        self.peer_manager.configure_continuous_discovery(
            enabled=True, 
            interval=CONTINUOUS_DISCOVERY_INTERVAL
        )
        
        # Configure enhanced automatic blockchain synchronization for late-joining nodes
        self.peer_manager.configure_blockchain_sync(enabled=True, interval=15.0)  # More frequent sync
        self.peer_manager.set_blockchain_reference(self.blockchain)
        self.peer_manager.set_sync_callback(self._perform_enhanced_automatic_sync)
        
        # Configure aggressive initial sync for late-joining nodes
        self._configure_late_joiner_support()
        
        # Configure mempool synchronization
        self.peer_manager.configure_mempool_sync(enabled=True, interval=15.0)
        self.peer_manager.set_mempool_callback(self._add_synced_transaction)
        
        # Configure network statistics synchronization
        self.peer_manager.configure_network_stats_sync(enabled=True, interval=60.0)
        
        # Start API server in background first (fix race condition)
        import threading
        self._start_api_server_background()
        
        # Wait briefly for API server to initialize
        import time
        time.sleep(1.0)
        
        # Configure self-awareness for enhanced peer discovery  
        self_url = f"http://localhost:{self.api_port}"
        
        # Enhanced peer discovery with main node detection
        if discover_peers:
            logger.info("🔍 Starting Enhanced Peer Discovery...")
            logger.info(f"   🆔 This node: {self_url}")
            logger.info("   🌐 Scanning for existing nodes...")
            
            # Add small delay before discovery to prevent thundering herd
            startup_delay = __import__('random').uniform(1.0, 4.0)
            time.sleep(startup_delay)
            
            self.peer_manager.set_self_url(self_url)
            discovered = self.peer_manager.discover_peers()
            
            if discovered > 0:
                logger.info(f"🎉 Successfully connected to {discovered} existing nodes!")
                main_status = "MAIN NODE" if self.peer_manager.get_main_node_status() else "PEER NODE"
                logger.info(f"   🏆 Node role: {main_status}")
            else:
                logger.info("📡 No existing nodes found - this is the first node in the network!")
                logger.info("   🏆 Node role: MAIN NODE (bootstrap)")
        else:
            self.peer_manager.set_self_url(self_url)
        
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
            if max_peer_length > current_length + 5:
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
        """Enhanced automatic sync that preserves mining attribution and updates balances"""
        try:
            logger.debug("🔄 Starting enhanced automatic blockchain sync")
            
            # Get current chain length
            current_length = self.blockchain.get_chain_length()
            
            # Get peer blockchain info with mining attribution preservation
            peer_sync_result = self.peer_manager.sync_with_best_peer_enhanced()
            
            if peer_sync_result:
                peer_url_result, chain_data = peer_sync_result
                
                logger.info(f"📡 Enhanced sync with peer: {peer_url_result}")
                logger.info(f"📊 Current chain length: {current_length}")
                logger.info(f"📊 Peer chain length: {len(chain_data)}")
                
                # Use industry-standard smart sync with enhanced features
                if self.blockchain.smart_sync_with_peer_chain(chain_data, peer_url_result):
                    new_length = self.blockchain.get_chain_length()
                    logger.info(f"🎉 Enhanced Blockchain Sync Successful!")
                    logger.info(f"   📊 Chain updated: {current_length} -> {new_length} blocks")
                    logger.info(f"   🌐 Source: {peer_url_result}")
                    logger.info(f"   💾 Mining history: PRESERVED")
                    logger.info(f"   💰 Wallet balances: UPDATED")
                    
                    # Update stats
                    self._stats['successful_syncs'] = self._stats.get('successful_syncs', 0) + 1
                    self._stats['last_sync_time'] = time.time()
                    logger.info(f"   📈 Total successful syncs: {self._stats['successful_syncs']}")
                else:
                    logger.error("❌ Enhanced Smart Sync Failed!")
                    logger.error("   🔍 Chain validation failed or sync error occurred")
                    self._stats['failed_syncs'] = self._stats.get('failed_syncs', 0) + 1
            else:
                logger.info("⚠️  Enhanced Automatic Sync: No suitable peers available for sync")
                
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
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
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
        p2p_port=args.p2p_port
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
            node.cleanup()
            print("✅ Shutdown complete. Thank you for using ChainCore!")
        except:
            pass

if __name__ == "__main__":
    main()