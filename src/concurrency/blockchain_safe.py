#!/usr/bin/env python3
"""
Thread-Safe Blockchain Implementation
Replaces the original Blockchain class with enterprise-grade thread safety
"""

import threading
import time
import copy
import logging
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
from contextlib import contextmanager

# Import our thread safety framework
from .thread_safety import (
    LockManager, LockOrder, synchronized, AtomicCounter, 
    TransactionQueue, MemoryBarrier, deadlock_detector, Transaction as TxContext,
    lock_manager, AdvancedRWLock
)

logger = logging.getLogger(__name__)

@dataclass
class ChainStats:
    """Thread-safe blockchain statistics"""
    blocks_processed: int = 0
    transactions_processed: int = 0
    utxo_count: int = 0
    orphaned_blocks: int = 0
    
class ThreadSafeUTXOSet:
    """
    Thread-safe UTXO set with optimistic locking and snapshot isolation
    Based on Bitcoin Core's UTXO management
    """
    
    def __init__(self):
        self._utxos: Dict[str, Dict] = {}
        self._dirty_utxos: Set[str] = set()  # Track modified UTXOs
        self._snapshot_cache: Dict[int, Dict[str, Dict]] = {}
        self._version_counter = AtomicCounter()
        self._lock = AdvancedRWLock("utxo_set", LockOrder.UTXO_SET)
        
    @synchronized("utxo_set", LockOrder.UTXO_SET, mode='read')
    def get_utxo(self, key: str) -> Optional[Dict]:
        """Thread-safe UTXO retrieval"""
        return copy.deepcopy(self._utxos.get(key))
    
    @synchronized("utxo_set", LockOrder.UTXO_SET, mode='read') 
    def contains(self, key: str) -> bool:
        """Check if UTXO exists"""
        return key in self._utxos
    
    @synchronized("utxo_set", LockOrder.UTXO_SET, mode='read')
    def get_balance(self, address: str) -> float:
        """Calculate balance for address"""
        balance = 0.0
        for utxo_key, utxo_data in self._utxos.items():
            if utxo_data['address'] == address:
                balance += utxo_data['amount']
        return balance
    
    @synchronized("utxo_set", LockOrder.UTXO_SET, mode='read')
    def get_utxos_for_address(self, address: str) -> List[Dict]:
        """Get all UTXOs for an address"""
        utxos = []
        for utxo_key, utxo_data in self._utxos.items():
            if utxo_data['address'] == address:
                utxo_copy = copy.deepcopy(utxo_data)
                utxo_copy['key'] = utxo_key
                utxos.append(utxo_copy)
        return utxos
    
    def atomic_update(self, updates: Dict[str, Optional[Dict]]) -> bool:
        """
        Atomic UTXO update with conflict detection
        Returns False if conflicts detected, True if successful
        """
        lock = lock_manager.get_lock("utxo_set", LockOrder.UTXO_SET)
        
        with lock.write_lock():
            # Check for conflicts with dirty UTXOs
            conflicts = set(updates.keys()) & self._dirty_utxos
            if conflicts:
                logger.warning(f"UTXO conflicts detected: {conflicts}")
                return False
            
            # Mark UTXOs as dirty
            self._dirty_utxos.update(updates.keys())
            
            try:
                # Apply updates
                for key, value in updates.items():
                    if value is None:
                        # Remove UTXO
                        self._utxos.pop(key, None)
                    else:
                        # Add/Update UTXO
                        self._utxos[key] = copy.deepcopy(value)
                
                # Increment version for snapshot isolation
                self._version_counter.increment()
                MemoryBarrier.write_barrier()
                
                return True
                
            finally:
                # Clear dirty flags
                self._dirty_utxos.difference_update(updates.keys())
    
    @synchronized("utxo_set", LockOrder.UTXO_SET, mode='read')
    def create_snapshot(self) -> Tuple[int, Dict[str, Dict]]:
        """Create a consistent snapshot of UTXO set"""
        version = self._version_counter.value
        snapshot = copy.deepcopy(self._utxos)
        
        # Cache snapshot for reuse
        if len(self._snapshot_cache) > 5:
            # Remove oldest snapshot
            oldest_version = min(self._snapshot_cache.keys())
            del self._snapshot_cache[oldest_version]
        
        self._snapshot_cache[version] = snapshot
        return version, snapshot
    
    def get_snapshot(self, version: int) -> Optional[Dict[str, Dict]]:
        """Retrieve a cached snapshot"""
        return self._snapshot_cache.get(version)

class ThreadSafeBlockchain:
    """
    Enterprise-grade thread-safe blockchain implementation
    Uses reader-writer locks, atomic operations, and snapshot isolation
    """
    
    def __init__(self):
        # Core blockchain data with proper initialization
        self._chain: List = []
        self._chain_lock = lock_manager.get_lock("blockchain_chain", LockOrder.BLOCKCHAIN)
        
        # Thread-safe transaction pool
        self._transaction_queue = TransactionQueue(maxsize=10000)
        self._transaction_pool: List = []
        self._pool_lock = lock_manager.get_lock("transaction_pool", LockOrder.MEMPOOL)
        
        # Thread-safe UTXO management
        self.utxo_set = ThreadSafeUTXOSet()
        
        # Blockchain configuration - import from centralized config
        from ..config import BLOCKCHAIN_DIFFICULTY, BLOCK_REWARD
        self.target_difficulty = BLOCKCHAIN_DIFFICULTY
        self.block_reward = BLOCK_REWARD
        
        # Statistics and monitoring
        self._stats = ChainStats()
        self._stats_lock = threading.Lock()
        
        # Block validation cache
        self._validation_cache: Dict[str, bool] = {}
        self._cache_lock = threading.RLock()
        
        # Initialize with genesis block
        self._create_genesis_block()
        
        logger.info("Thread-safe blockchain initialized")
    
    @synchronized("blockchain_chain", LockOrder.BLOCKCHAIN, mode='read')
    def get_transaction_history(self, address: str) -> List[Dict]:
        """Get transaction history for an address with thread safety"""
        transactions = []
        
        # Go through all blocks in the chain
        for block in self._chain:
            for tx in block.transactions:
                # Check if this transaction involves the address
                involved_as_recipient = False
                involved_as_sender = False
                amount_received = 0.0
                amount_sent = 0.0
                
                # Check outputs (receiving transactions)
                for output in tx.outputs:
                    if output.recipient_address == address:
                        involved_as_recipient = True
                        amount_received += output.amount
                
                # Check inputs (sending transactions) - only for non-coinbase transactions
                if not tx.is_coinbase():
                    for tx_input in tx.inputs:
                        # Check historical UTXO ownership by looking at the referenced transaction
                        referenced_tx = self._find_transaction_by_id(tx_input.tx_id)
                        if referenced_tx and tx_input.output_index < len(referenced_tx.outputs):
                            if referenced_tx.outputs[tx_input.output_index].recipient_address == address:
                                involved_as_sender = True
                                amount_sent += referenced_tx.outputs[tx_input.output_index].amount
                
                # Determine transaction type and amount
                if involved_as_recipient and involved_as_sender:
                    # Internal transaction (change)
                    net_amount = amount_received - amount_sent
                    if net_amount > 0:
                        tx_type = "received"
                        amount = net_amount
                    elif net_amount < 0:
                        tx_type = "sent"
                        amount = abs(net_amount)
                    else:
                        tx_type = "internal"
                        amount = 0
                elif involved_as_recipient:
                    tx_type = "received"
                    amount = amount_received
                elif involved_as_sender:
                    tx_type = "sent" 
                    amount = amount_sent
                else:
                    # Not involved in this transaction
                    continue
                
                # Add transaction to history
                transactions.append({
                    'tx_id': tx.tx_id,
                    'block_height': block.index,
                    'timestamp': block.timestamp,
                    'type': tx_type,
                    'amount': amount,
                    'is_coinbase': tx.is_coinbase(),
                    'block_hash': block.hash
                })
        
        # Sort by block height (most recent first)
        transactions.sort(key=lambda x: x['block_height'], reverse=True)
        return transactions
    
    @synchronized("blockchain_chain", LockOrder.BLOCKCHAIN, mode='read')
    def _find_transaction_by_id(self, tx_id: str):
        """Find a transaction by ID in the blockchain"""
        for block in self._chain:
            for tx in block.transactions:
                if tx.tx_id == tx_id:
                    return tx
        return None
    
    def _create_genesis_block(self):
        """Create genesis block with proper locking"""
        from ..blockchain.bitcoin_transaction import Transaction
        
        with self._chain_lock.write_lock():
            if len(self._chain) == 0:  # Double-check pattern
                genesis_tx = Transaction.create_coinbase_transaction("genesis", self.block_reward, 0)
                
                # Import Block here to avoid circular imports
                import sys, os
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
                from network_node import Block
                
                genesis_block = Block(0, [genesis_tx], "0" * 64, target_difficulty=self.target_difficulty)
                
                # Mine genesis block
                while not genesis_block.is_valid_hash():
                    genesis_block.nonce += 1
                    genesis_block.hash = genesis_block._calculate_hash()
                
                self._chain.append(genesis_block)
                
                # Update UTXO set atomically
                utxo_updates = {}
                for i, output in enumerate(genesis_tx.outputs):
                    utxo_key = f"{genesis_tx.tx_id}:{i}"
                    utxo_updates[utxo_key] = {
                        'amount': output.amount,
                        'address': output.recipient_address,
                        'tx_id': genesis_tx.tx_id,
                        'output_index': i
                    }
                
                self.utxo_set.atomic_update(utxo_updates)
                
                with self._stats_lock:
                    self._stats.blocks_processed += 1
                    self._stats.transactions_processed += 1
                
                logger.info("Genesis block created and UTXO set initialized")
    
    @synchronized("transaction_pool", LockOrder.MEMPOOL, mode='write')
    def add_transaction(self, transaction) -> bool:
        """
        Thread-safe transaction addition with validation
        """
        if self._validate_transaction(transaction):
            # Check for double-spending in pool
            tx_inputs = {f"{inp.tx_id}:{inp.output_index}" for inp in transaction.inputs}
            
            for existing_tx in self._transaction_pool:
                existing_inputs = {f"{inp.tx_id}:{inp.output_index}" for inp in existing_tx.inputs}
                if tx_inputs & existing_inputs:  # Intersection check
                    logger.warning(f"Double-spending detected in mempool: {transaction.tx_id}")
                    return False
            
            self._transaction_pool.append(transaction)
            self._transaction_queue.put(transaction, timeout=1.0)
            
            with self._stats_lock:
                self._stats.transactions_processed += 1
            
            logger.info(f"Transaction {transaction.tx_id} added to pool")
            return True
        
        return False
    
    def _validate_transaction(self, transaction) -> bool:
        """
        Thread-safe transaction validation with UTXO snapshot
        """
        if transaction.is_coinbase():
            return True  # Coinbase transactions are always valid
        
        # Create UTXO snapshot for consistent validation
        version, utxo_snapshot = self.utxo_set.create_snapshot()
        
        try:
            # Validate all inputs exist and are unspent
            for i, tx_input in enumerate(transaction.inputs):
                utxo_key = f"{tx_input.tx_id}:{tx_input.output_index}"
                
                if utxo_key not in utxo_snapshot:
                    logger.warning(f"UTXO not found: {utxo_key}")
                    return False
                
                # Verify signature
                if not transaction.verify_input_signature(i, "", {"utxo_set": utxo_snapshot}):
                    logger.warning(f"Invalid signature for input {i}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Transaction validation error: {e}")
            return False
    
    @synchronized("blockchain_chain", LockOrder.BLOCKCHAIN, mode='write')
    def add_block(self, block) -> bool:
        """
        Thread-safe block addition with atomic UTXO updates
        """
        if not self._validate_block(block):
            return False
        
        # Use transaction context for atomic operations
        tx_context = TxContext()
        
        # Prepare UTXO updates
        utxo_updates = {}
        
        # Remove spent UTXOs and add new ones
        for transaction in block.transactions:
            if not transaction.is_coinbase():
                # Mark inputs as spent (remove from UTXO set)
                for tx_input in transaction.inputs:
                    utxo_key = f"{tx_input.tx_id}:{tx_input.output_index}"
                    utxo_updates[utxo_key] = None  # None means delete
            
            # Add outputs as new UTXOs
            for i, output in enumerate(transaction.outputs):
                utxo_key = f"{transaction.tx_id}:{i}"
                utxo_updates[utxo_key] = {
                    'amount': output.amount,
                    'address': output.recipient_address,
                    'tx_id': transaction.tx_id,
                    'output_index': i
                }
        
        # Add operations to transaction
        def add_block_op():
            self._chain.append(block)
            logger.info(f"Block {block.index} added to chain")
        
        def rollback_block_op():
            if self._chain and self._chain[-1].hash == block.hash:
                self._chain.pop()
                logger.info(f"Block {block.index} rolled back")
        
        def update_utxo_op():
            if not self.utxo_set.atomic_update(utxo_updates):
                raise RuntimeError("UTXO update conflict")
        
        def update_stats_op():
            with self._stats_lock:
                self._stats.blocks_processed += 1
                self._stats.utxo_count = len(self.utxo_set._utxos)
        
        # Add operations to transaction
        tx_context.add_operation(add_block_op, rollback_block_op)
        tx_context.add_operation(update_utxo_op)
        tx_context.add_operation(update_stats_op)
        
        # Commit transaction
        success = tx_context.commit()
        
        if success:
            # Remove confirmed transactions from pool
            with self._pool_lock.write_lock():
                confirmed_tx_ids = {tx.tx_id for tx in block.transactions if not tx.is_coinbase()}
                self._transaction_pool = [
                    tx for tx in self._transaction_pool 
                    if tx.tx_id not in confirmed_tx_ids
                ]
            
            # Clear validation cache
            with self._cache_lock:
                self._validation_cache.clear()
            
            logger.info(f"Block {block.index} successfully added and committed")
        
        return success
    
    def _validate_block(self, block) -> bool:
        """
        Thread-safe block validation with caching
        """
        # Check cache first
        with self._cache_lock:
            if block.hash in self._validation_cache:
                return self._validation_cache[block.hash]
        
        try:
            # Basic block validation
            if not block.is_valid_hash():
                logger.warning(f"Block {block.index} has invalid hash")
                return False
            
            # Check if block already exists (lock already held by caller)
            if block.index < len(self._chain):
                existing_block = self._chain[block.index]
                if existing_block.hash == block.hash:
                    return False  # Duplicate
                else:
                    logger.warning(f"Fork detected at block {block.index}")
                    return False
            
            # Check previous hash connection
            if block.index > 0 and block.previous_hash != self._chain[-1].hash:
                logger.warning(f"Block {block.index} previous hash mismatch")
                return False
            
            # Check index sequence
            if block.index != len(self._chain):
                logger.warning(f"Block {block.index} index mismatch")
                return False
            
            # Validate all transactions in block
            for transaction in block.transactions:
                if not transaction.is_coinbase() and not self._validate_transaction(transaction):
                    logger.warning(f"Invalid transaction in block: {transaction.tx_id}")
                    return False
            
            # Cache validation result
            with self._cache_lock:
                self._validation_cache[block.hash] = True
            
            return True
            
        except Exception as e:
            logger.error(f"Block validation error: {e}")
            with self._cache_lock:
                self._validation_cache[block.hash] = False
            return False
    
    @synchronized("blockchain_chain", LockOrder.BLOCKCHAIN, mode='write')
    def replace_chain(self, new_chain: List) -> bool:
        """
        Thread-safe chain replacement with atomic UTXO rebuild
        """
        if not self._validate_chain(new_chain):
            return False
        
        logger.info(f"Replacing chain: {len(self._chain)} -> {len(new_chain)} blocks")
        
        # Create transaction context for atomic operation
        tx_context = TxContext()
        
        # Store old chain for rollback
        old_chain = copy.deepcopy(self._chain)
        old_utxos = copy.deepcopy(self.utxo_set._utxos)
        
        def replace_chain_op():
            self._chain.clear()
            self._chain.extend(new_chain)
        
        def rollback_chain_op():
            self._chain.clear()
            self._chain.extend(old_chain)
        
        def rebuild_utxo_op():
            # Clear current UTXO set
            self.utxo_set._utxos.clear()
            
            # Rebuild from new chain
            for block in new_chain:
                utxo_updates = {}
                
                for transaction in block.transactions:
                    # Remove spent UTXOs (except for genesis block)
                    if not transaction.is_coinbase() and block.index > 0:
                        for tx_input in transaction.inputs:
                            utxo_key = f"{tx_input.tx_id}:{tx_input.output_index}"
                            utxo_updates[utxo_key] = None
                    
                    # Add new UTXOs
                    for i, output in enumerate(transaction.outputs):
                        utxo_key = f"{transaction.tx_id}:{i}"
                        utxo_updates[utxo_key] = {
                            'amount': output.amount,
                            'address': output.recipient_address,
                            'tx_id': transaction.tx_id,
                            'output_index': i
                        }
                
                # Apply updates
                for key, value in utxo_updates.items():
                    if value is None:
                        self.utxo_set._utxos.pop(key, None)
                    else:
                        self.utxo_set._utxos[key] = value
        
        def rollback_utxo_op():
            self.utxo_set._utxos.clear()
            self.utxo_set._utxos.update(old_utxos)
        
        # Add operations to transaction
        tx_context.add_operation(replace_chain_op, rollback_chain_op)
        tx_context.add_operation(rebuild_utxo_op, rollback_utxo_op)
        
        # Commit transaction
        success = tx_context.commit()
        
        if success:
            # Clear transaction pool and caches
            with self._pool_lock.write_lock():
                self._transaction_pool.clear()
            
            with self._cache_lock:
                self._validation_cache.clear()
            
            with self._stats_lock:
                self._stats.blocks_processed = len(new_chain)
                self._stats.utxo_count = len(self.utxo_set._utxos)
            
            logger.info(f"Chain replacement successful: {len(new_chain)} blocks")
        else:
            logger.error("Chain replacement failed - rolled back")
        
        return success
    
    def _validate_chain(self, chain: List) -> bool:
        """Validate entire blockchain"""
        if not chain:
            return False
        
        # Validate genesis block
        if chain[0].index != 0 or chain[0].previous_hash != "0" * 64:
            return False
        
        # Validate chain linkage
        for i in range(1, len(chain)):
            if (chain[i].index != i or 
                chain[i].previous_hash != chain[i-1].hash or 
                not chain[i].is_valid_hash()):
                return False
        
        return True
    
    @synchronized("blockchain_chain", LockOrder.BLOCKCHAIN, mode='read')
    def get_chain_copy(self) -> List:
        """Get a thread-safe copy of the blockchain"""
        return copy.deepcopy(self._chain)
    
    @synchronized("blockchain_chain", LockOrder.BLOCKCHAIN, mode='read')
    def get_chain_length(self) -> int:
        """Get current chain length"""
        return len(self._chain)
    
    @synchronized("transaction_pool", LockOrder.MEMPOOL, mode='read')
    def get_transaction_pool_copy(self) -> List:
        """Get a thread-safe copy of transaction pool"""
        return copy.deepcopy(self._transaction_pool)
    
    def get_stats(self) -> ChainStats:
        """Get blockchain statistics"""
        with self._stats_lock:
            return copy.deepcopy(self._stats)
    
    def create_block_template(self, miner_address: str):
        """
        Create mining block template with thread safety
        """
        with self._pool_lock.read_lock():
            # Get transactions from pool (limit for block size)
            transactions = self._transaction_pool[:1000].copy()
        
        # Calculate fees with UTXO snapshot
        version, utxo_snapshot = self.utxo_set.create_snapshot()
        total_fees = 0.0
        
        for tx in transactions:
            try:
                fee = tx.get_fee({"utxo_set": utxo_snapshot})
                total_fees += fee
            except:
                continue
        
        # Create coinbase transaction
        from ..blockchain.bitcoin_transaction import Transaction
        coinbase_tx = Transaction.create_coinbase_transaction(
            miner_address, 
            self.block_reward + total_fees,
            self.get_chain_length()
        )
        
        # Create block template
        with self._chain_lock.read_lock():
            all_transactions = [coinbase_tx] + transactions
            
            # Import Block to avoid circular dependency
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
            from network_node import Block
            
            new_block = Block(
                len(self._chain),
                all_transactions,
                self._chain[-1].hash if self._chain else "0" * 64,
                target_difficulty=self.target_difficulty
            )
        
        logger.info(f"Block template created: index={new_block.index}, txs={len(all_transactions)}, fees={total_fees}")
        return new_block