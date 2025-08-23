#!/usr/bin/env python3
"""
Block implementation for ChainCore blockchain
Separated to avoid circular imports
"""

import json
import time
from typing import Dict, List

from ..crypto.ecdsa_crypto import double_sha256
from ..config import BLOCKCHAIN_DIFFICULTY
from .bitcoin_transaction import Transaction


class Block:
    """Blockchain block containing transactions and proof-of-work validation"""
    def __init__(self, index: int, transactions: List[Transaction], previous_hash: str, 
                 timestamp: float = None, nonce: int = 0, target_difficulty: int = BLOCKCHAIN_DIFFICULTY,
                 mining_node: str = None, version: int = 1):
        self.index = index
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.timestamp = timestamp or time.time()
        self.nonce = nonce
        self.target_difficulty = target_difficulty
        self.version = version  # Block version for protocol upgrades
        
        # Calculate derived fields
        self.merkle_root = self._calculate_merkle_root()
        self.transaction_count = len(transactions)
        self.block_size = self._calculate_block_size()
        self.hash = self._calculate_hash()
        
        # Mining metadata for tracking block origins
        self._mining_metadata = {
            'mining_node': mining_node or 'unknown',
            'created_at': time.time(),
            'mining_attribution_preserved': True,
            'proof_of_work': {
                'difficulty': target_difficulty,
                'work_performed': self.calculate_block_work(),
                'target_bits': self._calculate_target_bits()
            }
        }
        
        # Block header containing essential block information
        self._block_header = {
            'version': self.version,
            'previous_block_hash': previous_hash,
            'merkle_root': self.merkle_root,
            'timestamp': self.timestamp,
            'bits': self._calculate_target_bits(),
            'nonce': nonce
        }
        
        # Extract miner information from coinbase transaction
        if transactions and len(transactions) > 0:
            coinbase_tx = transactions[0]
            if hasattr(coinbase_tx, 'outputs') and len(coinbase_tx.outputs) > 0:
                self._mining_metadata['miner_address'] = coinbase_tx.outputs[0].recipient_address
                self._mining_metadata['mining_reward'] = coinbase_tx.outputs[0].amount
                
        # Transaction analysis metadata
        self._transaction_metadata = {
            'total_transactions': self.transaction_count,
            'coinbase_transactions': sum(1 for tx in transactions if tx.is_coinbase()),
            'user_transactions': sum(1 for tx in transactions if not tx.is_coinbase()),
            'total_inputs': sum(len(tx.inputs) for tx in transactions if not tx.is_coinbase()),
            'total_outputs': sum(len(tx.outputs) for tx in transactions),
            'total_value_transferred': self._calculate_total_value()
        }
        
        # Network metadata
        self._network_metadata = {
            'chain_id': 'chaincore-mainnet',
            'network_magic': 0xCCCCCCCC,
            'created_timestamp': time.time(),
            'block_creation_node': mining_node or 'unknown'
        }
    
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
    
    def _calculate_block_size(self) -> int:
        """Calculate approximate block size in bytes"""
        # Rough estimation: each transaction ~250 bytes + block header ~80 bytes
        base_size = 80  # Block header
        tx_size = sum(250 for _ in self.transactions)  # Approximate transaction size
        return base_size + tx_size
    
    def _calculate_target_bits(self) -> str:
        """Calculate target bits representation for difficulty"""
        # Simplified bit representation
        return f"0x{(0x1d00ffff >> self.target_difficulty):08x}"
    
    def _calculate_total_value(self) -> float:
        """Calculate total value transferred in this block"""
        total_value = 0.0
        for tx in self.transactions:
            if not tx.is_coinbase():  # Exclude coinbase transactions
                total_value += sum(output.amount for output in tx.outputs)
        return total_value
    
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
        """Validate that block hash meets target difficulty requirement"""
        target = "0" * self.target_difficulty
        return self.hash.startswith(target)
    
    def calculate_block_work(self) -> int:
        """Calculate work performed for this block"""
        # Work = 2^256 / (target + 1)
        # For simplicity, we use 2^difficulty as work measure
        return 2 ** self.target_difficulty
    
    def validate_proof_of_work(self) -> bool:
        """Validate proof-of-work hash meets difficulty requirements"""
        try:
            # 1. Validate hash format and difficulty
            if not self.is_valid_hash():
                return False
            
            # 2. Recalculate hash to ensure integrity
            calculated_hash = self._calculate_hash()
            if calculated_hash != self.hash:
                return False
            
            # 3. Validate difficulty is reasonable (prevent difficulty manipulation)
            if self.target_difficulty < 1 or self.target_difficulty > 10:
                return False
            
            # 4. Validate nonce range (prevent negative nonce attacks)
            if self.nonce < 0:
                return False
            
            return True
            
        except Exception:
            return False
    
    def validate_block_structure(self) -> bool:
        """Validate block structure and basic integrity"""
        try:
            # 1. Validate basic fields
            if self.index < 0:
                return False
            
            if self.timestamp <= 0:
                return False
            
            # 2. Validate transactions exist
            if not self.transactions or len(self.transactions) == 0:
                return False
            
            # 3. Validate merkle root
            calculated_merkle = self._calculate_merkle_root()
            if calculated_merkle != self.merkle_root:
                return False
            
            # 4. Validate hash fields
            if not self.hash or len(self.hash) != 64:
                return False
            
            if not self.previous_hash or len(self.previous_hash) != 64:
                return False
            
            return True
            
        except Exception:
            return False
    
    def validate_block_full(self, previous_block=None) -> bool:
        """Full block validation including PoW and structure"""
        # 1. Validate block structure
        if not self.validate_block_structure():
            return False
        
        # 2. Validate proof of work
        if not self.validate_proof_of_work():
            return False
        
        # 3. Validate chain linkage if previous block provided
        if previous_block:
            if self.previous_hash != previous_block.hash:
                return False
            
            if self.index != previous_block.index + 1:
                return False
        
        return True
    
    def to_dict(self) -> Dict:
        """Convert block to dictionary format"""
        block_dict = {
            # Core block data
            'index': self.index,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp,
            'nonce': self.nonce,
            'target_difficulty': self.target_difficulty,
            'merkle_root': self.merkle_root,
            'hash': self.hash,
            'version': getattr(self, 'version', 1),
            
            # Enhanced block metadata
            'transaction_count': getattr(self, 'transaction_count', len(self.transactions)),
            'block_size': getattr(self, 'block_size', 0)
        }
        
        # Include mining metadata
        if hasattr(self, '_mining_metadata') and self._mining_metadata:
            block_dict['_mining_metadata'] = self._mining_metadata
            
            # Legacy compatibility - add mining_node at top level
            if 'mining_node' in self._mining_metadata:
                block_dict['mining_node'] = self._mining_metadata['mining_node']
        
        # Include block header metadata
        if hasattr(self, '_block_header') and self._block_header:
            block_dict['_block_header'] = self._block_header
            
        # Include transaction analysis metadata
        if hasattr(self, '_transaction_metadata') and self._transaction_metadata:
            block_dict['_transaction_metadata'] = self._transaction_metadata
            
        # Include network metadata
        if hasattr(self, '_network_metadata') and self._network_metadata:
            block_dict['_network_metadata'] = self._network_metadata
            
        # Include genesis metadata if present
        if hasattr(self, '_genesis_metadata') and self._genesis_metadata:
            block_dict['_genesis_metadata'] = self._genesis_metadata
        
        return block_dict
    
    @classmethod
    def from_dict(cls, block_dict: Dict) -> 'Block':
        """Create Block from dictionary with mining attribution preservation"""
        from .bitcoin_transaction import Transaction
        
        # Reconstruct transactions
        transactions = [Transaction.from_dict(tx_data) for tx_data in block_dict.get('transactions', [])]
        
        # Extract mining node information - try multiple sources
        mining_node = None
        if 'mining_node' in block_dict:
            mining_node = block_dict['mining_node']
        elif 'mining_metadata' in block_dict and isinstance(block_dict['mining_metadata'], dict):
            mining_node = block_dict['mining_metadata'].get('mining_node', 'unknown')
        
        # Create block with preserved mining attribution
        block = cls(
            index=block_dict['index'],
            transactions=transactions,
            previous_hash=block_dict['previous_hash'],
            timestamp=block_dict.get('timestamp', 0),
            nonce=block_dict.get('nonce', 0),
            target_difficulty=block_dict.get('target_difficulty', BLOCKCHAIN_DIFFICULTY),
            mining_node=mining_node
        )
        
        # Preserve original hash to maintain blockchain integrity
        if 'hash' in block_dict:
            block.hash = block_dict['hash']
        
        # Restore mining metadata if available
        if 'mining_metadata' in block_dict and isinstance(block_dict['mining_metadata'], dict):
            metadata = block_dict['mining_metadata']
            block._mining_metadata.update({
                'miner_address': metadata.get('miner_address', 'unknown'),
                'mining_reward': metadata.get('mining_reward', 0),
                'attribution_preserved': metadata.get('attribution_preserved', True),
                'sync_source': metadata.get('sync_source', 'unknown'),
                'preserved_from_sync': metadata.get('preserved_from_sync', True),
                # Mining statistics for database recording
                'mining_duration': metadata.get('mining_duration', 0.0),
                'hash_attempts': metadata.get('hash_attempts', 0),
                'hash_rate': metadata.get('hash_rate', 0.0),
                'mining_started_at': metadata.get('mining_started_at', block.timestamp),
                'mining_completed_at': metadata.get('mining_completed_at', block.timestamp),
                'worker_id': metadata.get('worker_id', 'unknown')
            })
        
        # Also check for _mining_metadata (our enhanced format)
        if '_mining_metadata' in block_dict and isinstance(block_dict['_mining_metadata'], dict):
            enhanced_metadata = block_dict['_mining_metadata']
            block._mining_metadata.update(enhanced_metadata)
        
        return block