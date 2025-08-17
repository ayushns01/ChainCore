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
    """Enhanced Block class with industry-standard mining attribution"""
    def __init__(self, index: int, transactions: List[Transaction], previous_hash: str, 
                 timestamp: float = None, nonce: int = 0, target_difficulty: int = BLOCKCHAIN_DIFFICULTY,
                 mining_node: str = None):
        self.index = index
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.timestamp = timestamp or time.time()
        self.nonce = nonce
        self.target_difficulty = target_difficulty
        self.merkle_root = self._calculate_merkle_root()
        self.hash = self._calculate_hash()
        
        # INDUSTRY STANDARD: Store complete mining attribution
        self._mining_metadata = {
            'mining_node': mining_node or 'unknown',
            'created_at': time.time(),
            'mining_attribution_preserved': True
        }
        
        # Extract miner address from coinbase transaction
        if transactions and len(transactions) > 0:
            coinbase_tx = transactions[0]
            if hasattr(coinbase_tx, 'outputs') and len(coinbase_tx.outputs) > 0:
                self._mining_metadata['miner_address'] = coinbase_tx.outputs[0].recipient_address
                self._mining_metadata['mining_reward'] = coinbase_tx.outputs[0].amount
    
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
        """Validate that block hash meets target difficulty requirement"""
        target = "0" * self.target_difficulty
        return self.hash.startswith(target)
    
    def calculate_block_work(self) -> int:
        """Calculate cumulative work for this block (industry standard)"""
        # Work = 2^256 / (target + 1)
        # For simplicity, we use 2^difficulty as work measure
        return 2 ** self.target_difficulty
    
    def validate_proof_of_work(self) -> bool:
        """Comprehensive PoW validation following Bitcoin Core standards"""
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
        """Convert block to dictionary with complete mining attribution preserved"""
        block_dict = {
            'index': self.index,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp,
            'nonce': self.nonce,
            'target_difficulty': self.target_difficulty,
            'merkle_root': self.merkle_root,
            'hash': self.hash
        }
        
        # CRITICAL: Include mining attribution in serialization for sync preservation
        if hasattr(self, '_mining_metadata') and self._mining_metadata:
            # Add mining node information to block data for sync
            if 'mining_node' in self._mining_metadata:
                block_dict['mining_node'] = self._mining_metadata['mining_node']
            
            # Add complete mining metadata for industry-standard preservation
            block_dict['mining_metadata'] = {
                'mining_node': self._mining_metadata.get('mining_node', 'unknown'),
                'miner_address': self._mining_metadata.get('miner_address', 'unknown'),
                'mining_reward': self._mining_metadata.get('mining_reward', 0),
                'attribution_preserved': True
            }
        
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
        
        # CRITICAL: Preserve original hash to maintain blockchain integrity
        if 'hash' in block_dict:
            block.hash = block_dict['hash']
        
        # INDUSTRY STANDARD: Restore complete mining metadata if available
        if 'mining_metadata' in block_dict and isinstance(block_dict['mining_metadata'], dict):
            metadata = block_dict['mining_metadata']
            block._mining_metadata.update({
                'miner_address': metadata.get('miner_address', 'unknown'),
                'mining_reward': metadata.get('mining_reward', 0),
                'attribution_preserved': metadata.get('attribution_preserved', True),
                'sync_source': metadata.get('sync_source', 'unknown'),
                'preserved_from_sync': metadata.get('preserved_from_sync', True)
            })
        
        return block