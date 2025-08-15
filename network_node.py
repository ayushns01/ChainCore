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
    
    def _setup_api_routes(self):
        """Setup all API routes with thread safety"""
        
        @self.app.route('/status', methods=['GET'])
        @synchronized("api_status", LockOrder.NETWORK, mode='read')
        def get_status():
            """Thread-safe status endpoint"""
            self._increment_api_calls()
            
            peer_stats = self.peer_manager.get_stats()
            return jsonify({
                'node_id': self.node_id,
                'blockchain_length': self.blockchain.get_chain_length(),
                'pending_transactions': len(self.blockchain.get_transaction_pool_copy()),
                'peers': len(self.peer_manager.get_active_peers()),
                'target_difficulty': self.blockchain.target_difficulty,
                'uptime': time.time() - self._stats['uptime_start'],
                'thread_safe': True,
                'api_calls': self._stats['api_calls'],
                'peer_discovery': {
                    'total_peers': peer_stats['total_peers'],
                    'active_peers': peer_stats['active_peers'],
                    'continuous_discovery_enabled': self.peer_manager._continuous_discovery_enabled,
                    'discovery_interval': self.peer_manager._peer_discovery_interval,
                    'peer_limits': {
                        'min_peers': self.peer_manager._min_peers,
                        'target_peers': self.peer_manager._target_peers,
                        'max_peers': self.peer_manager._max_peers
                    }
                },
                'blockchain_sync': {
                    'auto_sync_enabled': self.peer_manager._blockchain_sync_enabled,
                    'sync_interval': self.peer_manager._blockchain_sync_interval,
                    'successful_syncs': self._stats.get('successful_syncs', 0),
                    'failed_syncs': self._stats.get('failed_syncs', 0),
                    'last_sync_time': self._stats.get('last_sync_time', 0)
                },
                'mempool_sync': {
                    'enabled': self.peer_manager._mempool_sync_enabled,
                    'interval': self.peer_manager._mempool_sync_interval,
                    'syncs_completed': self.peer_manager._stats['mempool_syncs'].value
                },
                'network_stats_sync': {
                    'enabled': self.peer_manager._network_stats_sync_enabled,
                    'interval': self.peer_manager._network_stats_sync_interval,
                    'syncs_completed': self.peer_manager._stats['network_stats_syncs'].value
                }
            })
        
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
            """Thread-safe mining block template"""
            self._increment_api_calls()
            
            try:
                data = request.get_json() or {}
                miner_address = data.get('miner_address', 'unknown')
                
                # Create block template
                block_template = self.blockchain.create_block_template(miner_address)
                
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
                
                # Reconstruct block
                transactions = [Transaction.from_dict(tx) for tx in block_data['transactions']]
                block = Block(
                    block_data['index'],
                    transactions,
                    block_data['previous_hash'],
                    block_data.get('timestamp'),
                    block_data.get('nonce', 0),
                    block_data.get('target_difficulty', BLOCKCHAIN_DIFFICULTY)
                )
                
                # Validate and add block
                if self.blockchain.add_block(block):
                    # Extract miner address for logging
                    miner_address = "unknown"
                    if block.transactions and block.transactions[0].outputs:
                        miner_address = block.transactions[0].outputs[0].recipient_address
                    
                    # Check if locally mined for broadcasting
                    is_locally_mined = request.headers.get('X-Local-Mining') == 'true'
                    
                    # Broadcast to peers (except sender)
                    if is_locally_mined:
                        self.peer_manager.broadcast_to_peers(
                            '/submit_block',
                            {'block': block_data},
                            timeout=10.0
                        )
                    
                    with self._stats_lock:
                        self._stats['blocks_processed'] += 1
                    
                    return jsonify({
                        'status': 'accepted',
                        'block_hash': block.hash
                    })
                else:
                    return jsonify({
                        'status': 'rejected',
                        'error': 'Invalid block'
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
                    
                    # Replace chain if valid and longer
                    current_length = self.blockchain.get_chain_length()
                    if len(new_chain) > current_length:
                        if self.blockchain.replace_chain(new_chain):
                            return jsonify({
                                'status': 'synced',
                                'peer': peer_url,
                                'old_length': current_length,
                                'new_length': len(new_chain)
                            })
                        else:
                            return jsonify({
                                'status': 'sync_failed',
                                'error': 'Chain validation failed'
                            }), 400
                    else:
                        return jsonify({
                            'status': 'no_sync_needed',
                            'current_length': current_length,
                            'peer_length': len(new_chain)
                        })
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
    
    
    def start_api_server(self, debug: bool = False):
        """Start Flask API server with enhanced error handling"""
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
        
        # Configure automatic blockchain synchronization
        self.peer_manager.configure_blockchain_sync(enabled=True, interval=30.0)
        self.peer_manager.set_blockchain_reference(self.blockchain)
        self.peer_manager.set_sync_callback(self._perform_automatic_sync)
        
        # Configure mempool synchronization
        self.peer_manager.configure_mempool_sync(enabled=True, interval=15.0)
        self.peer_manager.set_mempool_callback(self._add_synced_transaction)
        
        # Configure network statistics synchronization
        self.peer_manager.configure_network_stats_sync(enabled=True, interval=60.0)
        
        # Configure self-awareness for peer discovery  
        self.peer_manager._self_url = f"http://localhost:{self.api_port}"
        
        # Discover peers if requested
        if discover_peers:
            logger.info("Discovering peers...")
            discovered = self.peer_manager.discover_peers()
            logger.info(f"Discovered {discovered} peers")
        
        # Start API server
        logger.info("🚀 Starting ChainCore Network Node...")
        logger.info(f"   🌐 API Server starting on port {self.api_port}")
        logger.info("   🔄 All sync mechanisms activated")
        logger.info("   🎯 Ready to accept connections!")
        self.start_api_server()
    
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
                
                # Replace chain if the new one is longer and valid
                if len(new_chain) > current_length:
                    if self.blockchain.replace_chain(new_chain):
                        logger.info(f"🎉 Automatic Blockchain Sync Successful!")
                        logger.info(f"   📊 Chain updated: {current_length} -> {len(new_chain)} blocks")
                        logger.info(f"   🌐 Source: {peer_url_result}")
                        
                        # Update stats
                        self._stats['successful_syncs'] = self._stats.get('successful_syncs', 0) + 1
                        self._stats['last_sync_time'] = time.time()
                        logger.info(f"   📈 Total successful syncs: {self._stats['successful_syncs']}")
                    else:
                        logger.error("❌ Automatic Sync Failed!")
                        logger.error("   🔍 Chain validation failed - rejected invalid chain")
                        self._stats['failed_syncs'] = self._stats.get('failed_syncs', 0) + 1
                else:
                    logger.info("ℹ️  Automatic Sync: Our chain is already up-to-date")
            else:
                logger.info("⚠️  Automatic Sync: No suitable peers available for sync")
                
        except Exception as e:
            logger.error(f"Error in automatic blockchain sync: {e}")
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