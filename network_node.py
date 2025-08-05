#!/usr/bin/env python3
"""
ChainCore Network Node - Pure Blockchain Processor
Focuses on network consensus and transaction processing
No wallets attached - users connect via API
"""

import sys
import os
import json
import time
import asyncio
import threading
import argparse
from datetime import datetime
from typing import Dict, List, Set
from flask import Flask, request, jsonify
import websockets

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.blockchain.bitcoin_transaction import Transaction
from src.crypto.ecdsa_crypto import hash_data, double_sha256

class Block:
    def __init__(self, index: int, transactions: List[Transaction], previous_hash: str, 
                 timestamp: float = None, nonce: int = 0, target_difficulty: int = 4):
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

class Blockchain:
    def __init__(self):
        self.chain: List[Block] = []
        self.transaction_pool: List[Transaction] = []
        self.utxo_set: Dict[str, Dict] = {}
        self.target_difficulty = 6
        self.block_reward = 50.0
        
        self._create_genesis_block()
    
    def _create_genesis_block(self):
        genesis_tx = Transaction.create_coinbase_transaction("genesis", self.block_reward, 0)
        genesis_block = Block(0, [genesis_tx], "0" * 64, target_difficulty=self.target_difficulty)
        
        # Mine genesis block
        while not genesis_block.is_valid_hash():
            genesis_block.nonce += 1
            genesis_block.hash = genesis_block._calculate_hash()
        
        self.chain.append(genesis_block)
        self._update_utxo_set(genesis_block)
    
    def add_transaction(self, transaction: Transaction) -> bool:
        if self._validate_transaction(transaction):
            self.transaction_pool.append(transaction)
            return True
        return False
    
    def _validate_transaction(self, transaction: Transaction) -> bool:
        if transaction.is_coinbase():
            return False
        
        # Check UTXOs exist and transaction is properly signed
        for i, tx_input in enumerate(transaction.inputs):
            utxo_key = f"{tx_input.tx_id}:{tx_input.output_index}"
            if utxo_key not in self.utxo_set:
                return False
            
            if not transaction.verify_input_signature(i, "", self.utxo_set):
                return False
        
        return True
    
    def create_block_template(self, miner_address: str) -> Block:
        """Create block template for mining"""
        # Get transactions from pool (limit to 1000 for block size)
        transactions = self.transaction_pool[:1000]
        
        # Calculate total fees
        total_fees = sum(tx.get_fee(self.utxo_set) for tx in transactions)
        
        # Create coinbase transaction
        coinbase_tx = Transaction.create_coinbase_transaction(
            miner_address, 
            self.block_reward + total_fees,
            len(self.chain)
        )
        
        # Create block
        all_transactions = [coinbase_tx] + transactions
        new_block = Block(
            len(self.chain),
            all_transactions,
            self.chain[-1].hash,
            target_difficulty=self.target_difficulty
        )
        
        return new_block
    
    def add_block(self, block: Block) -> bool:
        """Add mined block to chain"""
        if self._validate_block(block):
            self.chain.append(block)
            self._update_utxo_set(block)
            
            # Remove mined transactions from pool
            mined_tx_ids = {tx.tx_id for tx in block.transactions if not tx.is_coinbase()}
            self.transaction_pool = [tx for tx in self.transaction_pool if tx.tx_id not in mined_tx_ids]
            
            return True
        return False
    
    def _validate_block(self, block: Block) -> bool:
        # Check block hash is valid
        if not block.is_valid_hash():
            print(f"❌ Block validation failed: Invalid hash")
            return False
        
        # Check previous hash
        if block.previous_hash != self.chain[-1].hash:
            print(f"❌ Block validation failed: Previous hash mismatch")
            print(f"   Expected: {self.chain[-1].hash[:16]}...")
            print(f"   Got: {block.previous_hash[:16]}...")
            return False
        
        # Check index  
        if block.index != len(self.chain):
            print(f"❌ Block validation failed: Index mismatch")
            print(f"   Expected: {len(self.chain)}")
            print(f"   Got: {block.index}")
            return False
        
        # Validate all transactions
        for tx in block.transactions:
            if tx.is_coinbase():
                continue
            if not self._validate_transaction(tx):
                print(f"❌ Block validation failed: Invalid transaction {tx.tx_id[:16]}...")
                return False
        
        return True
    
    def _update_utxo_set(self, block: Block):
        # Remove spent UTXOs
        for tx in block.transactions:
            if not tx.is_coinbase():
                for tx_input in tx.inputs:
                    utxo_key = f"{tx_input.tx_id}:{tx_input.output_index}"
                    if utxo_key in self.utxo_set:
                        del self.utxo_set[utxo_key]
        
        # Add new UTXOs
        for tx in block.transactions:
            for i, tx_output in enumerate(tx.outputs):
                utxo_key = f"{tx.tx_id}:{i}"
                self.utxo_set[utxo_key] = {
                    'amount': tx_output.amount,
                    'recipient_address': tx_output.recipient_address,
                    'tx_id': tx.tx_id,
                    'output_index': i,
                    'block_height': block.index
                }
    
    def get_balance(self, address: str) -> float:
        balance = 0.0
        for utxo in self.utxo_set.values():
            if utxo['recipient_address'] == address:
                balance += utxo['amount']
        return balance
    
    def get_utxos_for_address(self, address: str) -> List[Dict]:
        utxos = []
        for utxo_key, utxo in self.utxo_set.items():
            if utxo['recipient_address'] == address:
                utxos.append({
                    'tx_id': utxo['tx_id'],
                    'output_index': utxo['output_index'],
                    'amount': utxo['amount'],
                    'block_height': utxo['block_height']
                })
        return utxos

class NetworkNode:
    def __init__(self, node_id: str, p2p_port: int, api_port: int):
        self.node_id = node_id
        self.blockchain = Blockchain()
        self.p2p_port = p2p_port
        self.api_port = api_port
        self.peers: Set[str] = set()
        self.app = Flask(__name__)
        
        # Session tracking
        self.session_start_time = datetime.now()
        self.session_id = f"session_{self.node_id}_{int(time.time())}"
        self.session_file = f"sessions/{self.session_id}.json"
        self.session_data = {
            "session_id": self.session_id,
            "node_id": self.node_id,
            "start_time": self.session_start_time.isoformat(),
            "blocks_mined": []
        }
        self._init_session_file()
        
        # Add peer nodes for synchronization (scan common ports)
        common_ports = [5000, 5001, 5002, 5003, 5004, 5005]
        for port in common_ports:
            if port != api_port:  # Don't add self as peer
                self.peers.add(f"http://localhost:{port}")
        
        self._setup_api_routes()
    
    def _init_session_file(self):
        """Initialize session tracking file"""
        os.makedirs("sessions", exist_ok=True)
        with open(self.session_file, 'w') as f:
            json.dump(self.session_data, f, indent=2)
    
    def _log_block_mined(self, block: 'Block', miner_address: str):
        """Log a mined block to the session file"""
        block_info = {
            "block_index": block.index,
            "block_hash": block.hash,
            "previous_hash": block.previous_hash,
            "miner_address": miner_address,
            "mined_by_node": self.node_id,
            "timestamp": datetime.now().isoformat(),
            "nonce": block.nonce,
            "difficulty": block.target_difficulty,
            "transaction_count": len(block.transactions),
            "has_transactions": len(block.transactions) > 1,  # More than just coinbase
            "transactions": [
                {
                    "tx_id": tx.tx_id,
                    "is_coinbase": tx.is_coinbase(),
                    "amount": sum(output.amount for output in tx.outputs) if tx.outputs else 0
                } for tx in block.transactions
            ]
        }
        
        self.session_data["blocks_mined"].append(block_info)
        
        # Update session file
        with open(self.session_file, 'w') as f:
            json.dump(self.session_data, f, indent=2)
        
        print(f"📝 Block {block.index} logged to session: {self.session_file}")
    
    def _setup_api_routes(self):
        @self.app.route('/status', methods=['GET'])
        def get_status():
            return jsonify({
                'node_id': self.node_id,
                'blockchain_length': len(self.blockchain.chain),
                'pending_transactions': len(self.blockchain.transaction_pool),
                'peers': len(self.peers),
                'target_difficulty': self.blockchain.target_difficulty
            })
        
        @self.app.route('/blockchain', methods=['GET'])
        def get_blockchain():
            response = jsonify({
                'chain': [block.to_dict() for block in self.blockchain.chain],
                'length': len(self.blockchain.chain)
            })
            response.headers['X-Blockchain-Length'] = str(len(self.blockchain.chain))
            return response
        
        @self.app.route('/balance/<address>', methods=['GET'])
        def get_balance(address):
            balance = self.blockchain.get_balance(address)
            return jsonify({'address': address, 'balance': balance})
        
        @self.app.route('/utxos/<address>', methods=['GET'])
        def get_utxos(address):
            utxos = self.blockchain.get_utxos_for_address(address)
            return jsonify({'address': address, 'utxos': utxos})
        
        @self.app.route('/broadcast_transaction', methods=['POST'])
        def broadcast_transaction():
            try:
                tx_data = request.get_json()
                transaction = Transaction.from_dict(tx_data)
                
                if self.blockchain.add_transaction(transaction):
                    # Broadcast transaction to peer nodes
                    self._broadcast_transaction_to_peers(transaction)
                    return jsonify({'status': 'accepted', 'tx_id': transaction.tx_id})
                else:
                    return jsonify({'status': 'rejected', 'error': 'Invalid transaction'}), 400
                    
            except Exception as e:
                return jsonify({'status': 'error', 'error': str(e)}), 500
        
        @self.app.route('/receive_transaction', methods=['POST'])
        def receive_transaction():
            """Receive transaction from peer (no re-broadcasting)"""
            try:
                tx_data = request.get_json()
                transaction = Transaction.from_dict(tx_data)
                
                if self.blockchain.add_transaction(transaction):
                    return jsonify({'status': 'accepted', 'tx_id': transaction.tx_id})
                else:
                    return jsonify({'status': 'rejected', 'error': 'Invalid transaction'}), 400
                    
            except Exception as e:
                return jsonify({'status': 'error', 'error': str(e)}), 500
        
        @self.app.route('/mine_block', methods=['POST'])
        def mine_block():
            try:
                data = request.get_json()
                miner_address = data.get('miner_address')
                
                if not miner_address:
                    return jsonify({'error': 'miner_address required'}), 400
                
                # Create block template
                block_template = self.blockchain.create_block_template(miner_address)
                
                return jsonify({
                    'block_template': block_template.to_dict(),
                    'target_difficulty': self.blockchain.target_difficulty
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/submit_block', methods=['POST'])
        def submit_block():
            try:
                block_data = request.get_json()
                
                # Reconstruct block
                transactions = [Transaction.from_dict(tx) for tx in block_data['transactions']]
                block = Block(
                    block_data['index'],
                    transactions,
                    block_data['previous_hash'],
                    block_data['timestamp'],
                    block_data['nonce'],
                    block_data['target_difficulty']
                )
                # Preserve the mined hash and merkle root from the submitted data
                block.hash = block_data['hash']
                block.merkle_root = block_data['merkle_root']
                
                if self.blockchain.add_block(block):
                    # Extract miner address from coinbase transaction
                    miner_address = block.transactions[0].outputs[0].recipient_address if block.transactions else "unknown"
                    
                    # Log the mined block to session
                    self._log_block_mined(block, miner_address)
                    
                    # Broadcast block to peer nodes for faster distribution  
                    self._broadcast_block_to_peers(block)
                    print(f"✅ Block {block.index} accepted and broadcasted: {block.hash[:16]}...")
                    return jsonify({'status': 'accepted', 'block_hash': block.hash})
                else:
                    print(f"❌ Block {block.index} rejected: {block.hash[:16]}...")
                    return jsonify({'status': 'rejected', 'error': 'Block validation failed'}), 400
                    
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/transaction_pool', methods=['GET'])
        def get_transaction_pool():
            return jsonify({
                'transactions': [tx.to_dict() for tx in self.blockchain.transaction_pool],
                'count': len(self.blockchain.transaction_pool)
            })
        
        @self.app.route('/debug_utxos', methods=['GET'])
        def debug_utxos():
            return jsonify({
                'utxo_count': len(self.blockchain.utxo_set),
                'all_utxos': self.blockchain.utxo_set
            })
        
        @self.app.route('/peers', methods=['GET'])
        def get_peers():
            return jsonify({
                'peers': list(self.peers),
                'peer_count': len(self.peers)
            })
        
        @self.app.route('/add_peer', methods=['POST'])
        def add_peer():
            try:
                data = request.get_json()
                peer_url = data.get('peer_url')
                if peer_url and peer_url not in self.peers:
                    # Verify peer is reachable
                    import requests
                    response = requests.get(f"{peer_url}/status", timeout=5)
                    if response.status_code == 200:
                        self.peers.add(peer_url)
                        return jsonify({'status': 'success', 'message': f'Added peer {peer_url}'})
                    else:
                        return jsonify({'status': 'error', 'message': 'Peer not reachable'}), 400
                else:
                    return jsonify({'status': 'error', 'message': 'Invalid or duplicate peer'}), 400
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/session', methods=['GET'])
        def get_session_data():
            """Get current session mining data"""
            return jsonify(self.session_data)
        
        @self.app.route('/sessions', methods=['GET'])
        def list_sessions():
            """List all available session files"""
            session_files = []
            if os.path.exists('sessions'):
                for filename in os.listdir('sessions'):
                    if filename.endswith('.json'):
                        filepath = os.path.join('sessions', filename)
                        with open(filepath, 'r') as f:
                            try:
                                session_info = json.load(f)
                                session_files.append({
                                    'filename': filename,
                                    'session_id': session_info.get('session_id'),
                                    'node_id': session_info.get('node_id'),
                                    'start_time': session_info.get('start_time'),
                                    'blocks_mined_count': len(session_info.get('blocks_mined', []))
                                })
                            except:
                                continue
            return jsonify({'sessions': session_files})
    
    def _broadcast_transaction_to_peers(self, transaction):
        """Broadcast transaction to peer nodes"""
        import requests
        for peer in self.peers:
            try:
                # Add header to prevent broadcast loops
                requests.post(
                    f"{peer}/receive_transaction", 
                    json=transaction.to_dict(),
                    timeout=2
                )
            except:
                pass  # Ignore failed broadcasts
    
    def _broadcast_block_to_peers(self, block):
        """Broadcast block to peer nodes"""
        import requests
        for peer in self.peers:
            try:
                requests.post(
                    f"{peer}/submit_block",
                    json=block.to_dict(),
                    timeout=2
                )
            except:
                pass  # Ignore failed broadcasts
    
    def _sync_with_peers(self):
        """Synchronize blockchain with peers"""
        import requests
        try:
            longest_chain = None
            max_length = len(self.blockchain.chain)
            
            for peer in self.peers:
                try:
                    response = requests.get(f"{peer}/blockchain", timeout=5)
                    if response.status_code == 200:
                        peer_data = response.json()
                        if peer_data['length'] > max_length:
                            max_length = peer_data['length']
                            longest_chain = peer_data['chain']
                except:
                    continue
            
            # Replace chain if we found a longer valid chain
            if longest_chain and max_length > len(self.blockchain.chain):
                print(f"🔄 Syncing blockchain from peers ({max_length} blocks)")
                # Reconstruct blockchain from peer data
                self.blockchain.chain = []
                for block_data in longest_chain:
                    transactions = [Transaction.from_dict(tx) for tx in block_data['transactions']]
                    block = Block(
                        block_data['index'],
                        transactions,
                        block_data['previous_hash'],
                        block_data['timestamp'],
                        block_data['nonce'],
                        block_data['target_difficulty']
                    )
                    self.blockchain.chain.append(block)
                
                # Rebuild UTXO set
                self.blockchain.utxo_set = {}
                for block in self.blockchain.chain:
                    self.blockchain._update_utxo_set(block)
                print(f"✅ Blockchain synced to {len(self.blockchain.chain)} blocks")
        except Exception as e:
            print(f"⚠️ Sync error: {e}")
    
    def _periodic_sync(self):
        """Periodically sync with peers"""
        import time
        time.sleep(5)  # Wait for startup
        while True:
            try:
                self._sync_with_peers()
                time.sleep(30)  # Sync every 30 seconds
            except:
                time.sleep(30)
    
    def start_api_server(self):
        """Start REST API server"""
        print(f"🌐 Starting API server on port {self.api_port}")
        self.app.run(host='0.0.0.0', port=self.api_port, debug=False, threaded=True)
    
    def run(self):
        """Run the node"""
        print(f"🚀 Starting Network Node {self.node_id}")
        print(f"   P2P Port: {self.p2p_port}")
        print(f"   API Port: {self.api_port}")
        print(f"   Blockchain: {len(self.blockchain.chain)} blocks")
        
        # Start API server
        api_thread = threading.Thread(target=self.start_api_server, daemon=True)
        api_thread.start()
        
        # Start periodic sync with peers
        sync_thread = threading.Thread(target=self._periodic_sync, daemon=True)  
        sync_thread.start()
        
        print("✅ Node running!")
        print("📡 API Endpoints:")
        print(f"   GET  /status - Node status")
        print(f"   GET  /blockchain - Full blockchain")
        print(f"   GET  /balance/<address> - Address balance")
        print(f"   POST /broadcast_transaction - Submit transaction")
        print(f"   POST /mine_block - Get mining template")
        print(f"   POST /submit_block - Submit mined block")
        print(f"   GET  /session - Current session mining data")
        print(f"   GET  /sessions - List all session files")
        
        try:
            # Keep main thread alive
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Node shutting down...")

def main():
    parser = argparse.ArgumentParser(description='Bitcoin-style Network Node')
    parser.add_argument('--node-id', default='node1', help='Node identifier')
    parser.add_argument('--p2p-port', type=int, default=8000, help='P2P port')
    parser.add_argument('--api-port', type=int, default=5000, help='API port')
    
    args = parser.parse_args()
    
    node = NetworkNode(args.node_id, args.p2p_port, args.api_port)
    node.run()

if __name__ == '__main__':
    import time
    main()