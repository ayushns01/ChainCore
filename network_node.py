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
from datetime import datetime
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

class Block:
    """Original Block class - kept for compatibility"""
    def __init__(self, index: int, transactions: List[Transaction], previous_hash: str, 
                 timestamp: float = None, nonce: int = 0, target_difficulty: int = BLOCKCHAIN_DIFFICULTY):
        self.index = index
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.timestamp = timestamp or time.time()
        self.nonce = nonce
        self.target_difficulty = target_difficulty
        self.merkle_root = self._calculate_merkle_root()
        self.hash = self._calculate_hash()
    
    def _calculate_merkle_root(self) -> str:
        if not self.transactions:
            return "0" * 64
        
        tx_hashes = [tx.tx_id for tx in self.transactions]
        
        while len(tx_hashes) > 1:
            if len(tx_hashes) % 2 == 1:
                tx_hashes.append(tx_hashes[-1])
            
            new_hashes = []
            for i in range(0, len(tx_hashes), 2):
                combined = tx_hashes[i] + tx_hashes[i + 1]
                new_hashes.append(double_sha256(combined))
            
            tx_hashes = new_hashes
        
        return tx_hashes[0] if tx_hashes else "0" * 64
    
    def _calculate_hash(self) -> str:
        block_data = {
            'index': self.index,
            'previous_hash': self.previous_hash,
            'merkle_root': self.merkle_root,
            'timestamp': self.timestamp,
            'nonce': self.nonce,
            'target_difficulty': self.target_difficulty
        }
        return double_sha256(json.dumps(block_data, sort_keys=True))
    
    def is_valid_hash(self) -> bool:
        target = "0" * self.target_difficulty
        return self.hash.startswith(target)
    
    def to_dict(self) -> Dict:
        return {
            'index': self.index,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp,
            'nonce': self.nonce,
            'target_difficulty': self.target_difficulty,
            'merkle_root': self.merkle_root,
            'hash': self.hash
        }

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
        
        
        logger.info(f"Thread-safe network node initialized: {self.node_id}")
    
    def _setup_api_routes(self):
        """Setup all API routes with thread safety"""
        
        @self.app.route('/status', methods=['GET'])
        @synchronized("api_status", LockOrder.NETWORK, mode='read')
        def get_status():
            """Thread-safe status endpoint"""
            self._increment_api_calls()
            
            return jsonify({
                'node_id': self.node_id,
                'blockchain_length': self.blockchain.get_chain_length(),
                'pending_transactions': len(self.blockchain.get_transaction_pool_copy()),
                'peers': len(self.peer_manager.get_active_peers()),
                'target_difficulty': self.blockchain.target_difficulty,
                'uptime': time.time() - self._stats['uptime_start'],
                'thread_safe': True,
                'api_calls': self._stats['api_calls']
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
                    
                    # Log block if locally mined
                    is_locally_mined = request.headers.get('X-Local-Mining') == 'true'
                    if is_locally_mined:
                        self._log_block_mined(block, miner_address)
                    
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
                'lock_stats': lock_manager.get_all_stats()
            })
    
    def _increment_api_calls(self):
        """Thread-safe API call counter"""
        with self._stats_lock:
            self._stats['api_calls'] += 1
    
    def _log_block_mined(self, block: Block, miner_address: str):
        """Log mined block with thread safety"""
        try:
            block_data = {
                'block_index': block.index,
                'block_hash': block.hash,
                'previous_hash': block.previous_hash,
                'miner_address': miner_address,
                'timestamp': datetime.fromtimestamp(block.timestamp).isoformat(),
                'nonce': block.nonce,
                'difficulty': block.target_difficulty,
                'transaction_count': len(block.transactions),
                'has_transactions': len(block.transactions) > 1,
                'transactions': [
                    {
                        'tx_id': tx.tx_id,
                        'is_coinbase': tx.is_coinbase(),
                        'amount': sum(output.amount for output in tx.outputs) if tx.outputs else 0
                    } for tx in block.transactions
                ]
            }
            
            
                
        except Exception as e:
            logger.error(f"Error logging mined block: {e}")
    
    def start_api_server(self, debug: bool = False):
        """Start Flask API server"""
        try:
            self.app.run(
                host='0.0.0.0',
                port=self.api_port,
                debug=debug,
                threaded=True,
                use_reloader=False
            )
        except Exception as e:
            logger.error(f"API server error: {e}")
    
    def start(self, discover_peers: bool = True):
        """Start the thread-safe network node"""
        logger.info(f"Starting thread-safe network node: {self.node_id}")
        
        # Discover peers if requested
        if discover_peers:
            logger.info("Discovering peers...")
            discovered = self.peer_manager.discover_peers()
            logger.info(f"Discovered {discovered} peers")
        
        # Start API server
        logger.info(f"Starting API server on port {self.api_port}")
        self.start_api_server()
    
    def cleanup(self):
        """Cleanup node resources"""
        logger.info(f"Cleaning up node: {self.node_id}")
        
        self.peer_manager.cleanup()
        
        logger.info("Node cleanup complete")

def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(description='Thread-Safe ChainCore Network Node')
    parser.add_argument('--node-id', default='core0', help='Node identifier')
    parser.add_argument('--api-port', type=int, default=5000, help='API server port')
    parser.add_argument('--p2p-port', type=int, default=8000, help='P2P communication port')
    parser.add_argument('--no-discover', action='store_true', help='Skip peer discovery')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and start node
    node = ThreadSafeNetworkNode(
        node_id=args.node_id,
        api_port=args.api_port,
        p2p_port=args.p2p_port
    )
    
    try:
        node.start(discover_peers=not args.no_discover)
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Node error: {e}")
    finally:
        node.cleanup()

if __name__ == "__main__":
    main()