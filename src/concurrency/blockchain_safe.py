#!/usr/bin/env python3
"""
Thread-Safe Blockchain Implementation
Replaces the original Blockchain class with enterprise-grade thread safety
With PostgreSQL persistence
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
    lock_manager, RWLock
)

logger = logging.getLogger(__name__)

# Database integration
try:
    from ..database.simple_connection import get_simple_db_manager
    from ..database.block_dao import BlockDAO
    from ..database.transaction_dao import TransactionDAO
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    logger.warning("Database components not available - running in memory-only mode")

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
        self._lock = RWLock("utxo_set", LockOrder.UTXO_SET)
        
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
    Thread-safe blockchain implementation
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
        try:
            from ..config import (
                BLOCKCHAIN_DIFFICULTY, BLOCK_REWARD, DIFFICULTY_ADJUSTMENT_ENABLED,
                TARGET_BLOCK_TIME, DIFFICULTY_ADJUSTMENT_INTERVAL, MAX_DIFFICULTY_CHANGE,
                MIN_DIFFICULTY, MAX_DIFFICULTY
            )
        except ImportError:
            # Fallback for direct script execution
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
            from src.config import (
                BLOCKCHAIN_DIFFICULTY, BLOCK_REWARD, DIFFICULTY_ADJUSTMENT_ENABLED,
                TARGET_BLOCK_TIME, DIFFICULTY_ADJUSTMENT_INTERVAL, MAX_DIFFICULTY_CHANGE,
                MIN_DIFFICULTY, MAX_DIFFICULTY
            )
        self.target_difficulty = BLOCKCHAIN_DIFFICULTY
        self.block_reward = BLOCK_REWARD
        self.difficulty_adjustment_enabled = DIFFICULTY_ADJUSTMENT_ENABLED
        self.target_block_time = TARGET_BLOCK_TIME
        self.difficulty_adjustment_interval = DIFFICULTY_ADJUSTMENT_INTERVAL
        self.max_difficulty_change = MAX_DIFFICULTY_CHANGE
        self.min_difficulty = MIN_DIFFICULTY
        self.max_difficulty = MAX_DIFFICULTY
        
        # Statistics and monitoring
        self._stats = ChainStats()
        self._stats_lock = threading.Lock()
        
        # Blockchain state versioning for stale block detection
        self._chain_state_version = 0  # Incremented on every chain modification
        self._last_block_hash = ""     # Hash of last block for quick change detection
        self._chain_tip_timestamp = 0  # Timestamp of last block addition
        self._state_version_lock = threading.RLock()  # Lock for state version updates
        
        # Block validation cache
        self._validation_cache: Dict[str, bool] = {}
        self._cache_lock = threading.RLock()
        
        # Orphaned block management
        self._orphaned_blocks: List = []
        self._orphaned_blocks_lock = threading.RLock()
        self._max_orphaned_blocks = 100  # Limit memory usage
        
        # Database integration (optional)
        self.database_enabled = False
        self.block_dao = None
        self.tx_dao = None
        
        if DATABASE_AVAILABLE:
            try:
                self.db_manager = get_simple_db_manager()
                self.db_manager.initialize()
                self.block_dao = BlockDAO()
                self.tx_dao = TransactionDAO()
                self.database_enabled = True
                logger.info("[DB] Database integration enabled (simple connection)")
            except Exception as e:
                logger.warning(f"Database initialization failed: {e}")
                logger.info("Continuing in memory-only mode")
        
        # Initialize blockchain - try to load from database first, then create genesis
        self._initialize_blockchain_from_database_or_genesis()
        
        logger.info("[BLOCKCHAIN] ChainCore Blockchain System Initialized")
        logger.info(f"   [DIFFICULTY] Target Difficulty: {self.target_difficulty} leading zeros")
        logger.info(f"   [REWARD] Block Reward: {self.block_reward} CC")
        logger.info(f"   [DB] Database: {'Enabled' if self.database_enabled else 'Memory Only'}")
        logger.info(f"   [ADJUST] Difficulty Adjustment: {'Enabled' if self.difficulty_adjustment_enabled else 'Disabled'}")
        if self.difficulty_adjustment_enabled:
            logger.info(f"   [TIME] Target Block Time: {self.target_block_time}s")
            logger.info(f"   [CONFIG] Adjustment Interval: Every {self.difficulty_adjustment_interval} blocks")
    
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
    
    def _initialize_blockchain_from_database_or_genesis(self):
        """Initialize blockchain by loading from database or creating genesis block"""
        try:
            # Try to load existing blockchain from database
            if self.database_enabled and self._load_blockchain_from_database():
                logger.info("[DATABASE] Loaded existing blockchain from database")
                return
        except Exception as e:
            logger.warning(f"[DATABASE] Failed to load from database: {e}")
        
        # If database loading failed, create genesis block
        self._create_genesis_block()
    
    def _load_blockchain_from_database(self):
        """Load blockchain state from database if available"""
        if not self.database_enabled or not hasattr(self, 'db_manager'):
            return False
        
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    # Check if we have any blocks in database
                    cur.execute("SELECT COUNT(*) FROM blocks")
                    block_count = cur.fetchone()[0]
                    
                    if block_count > 0:
                        # Load blocks in order
                        cur.execute("SELECT block_data FROM blocks ORDER BY block_index ASC")
                        block_rows = cur.fetchall()
                        
                        # TODO: Implement full block reconstruction from database
                        # For now, return False to force genesis creation
                        logger.info(f"[DATABASE] Found {block_count} blocks in database")
                        return False  # Skip database loading for now
                    
                    return False
        except Exception as e:
            logger.error(f"[DATABASE] Error loading blockchain: {e}")
            return False
    
    def _create_genesis_block(self):
        """Create hardcoded genesis block for network consensus"""
        try:
            from ..blockchain.bitcoin_transaction import Transaction
            from ..blockchain.block import Block
            from ..config.genesis_block import get_genesis_block, GENESIS_BLOCK_HASH
        except ImportError:
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
            from src.blockchain.bitcoin_transaction import Transaction
            from src.blockchain.block import Block
            from src.config.genesis_block import get_genesis_block, GENESIS_BLOCK_HASH
        
        with self._chain_lock.write_lock():
            if len(self._chain) == 0:  # Double-check pattern
                logger.info("[GENESIS] Loading Hardcoded Genesis Block...")
                
                # Get the hardcoded genesis block data
                genesis_data = get_genesis_block()
                
                # Create genesis transaction from hardcoded data
                tx_data = genesis_data["transactions"][0]
                genesis_tx = Transaction.create_coinbase_transaction(
                    tx_data["outputs"][0]["recipient_address"],
                    tx_data["outputs"][0]["amount"],
                    tx_data["timestamp"]
                )
                
                # Override with hardcoded transaction ID for consistency
                genesis_tx.tx_id = tx_data["tx_id"]
                
                # Create genesis block with hardcoded values
                genesis_block = Block(
                    index=genesis_data["index"],
                    transactions=[genesis_tx],
                    previous_hash=genesis_data["previous_hash"],
                    target_difficulty=genesis_data["target_difficulty"]
                )
                
                # Set hardcoded values for network consensus
                genesis_block.timestamp = genesis_data["timestamp"]
                genesis_block.nonce = genesis_data["nonce"]
                genesis_block.hash = genesis_data["hash"]
                genesis_block.merkle_root = genesis_data["merkle_root"]
                
                # Add metadata for tracking
                genesis_block._genesis_metadata = genesis_data["metadata"]
                
                # Verify the genesis block hash is correct
                if genesis_block.hash != GENESIS_BLOCK_HASH:
                    raise ValueError(f"Genesis block hash mismatch: {genesis_block.hash} != {GENESIS_BLOCK_HASH}")
                
                logger.info("[OK] Genesis Block Verification Successful!")
                logger.info(f"   [HASH] Hash: {genesis_block.hash}")
                logger.info(f"   [NONCE] Nonce: {genesis_block.nonce:,}")
                logger.info(f"   [TIME] Timestamp: {genesis_block.timestamp}")
                logger.info(f"   [CHAIN] Chain ID: {genesis_data['metadata']['chain_id']}")
                
                self._chain.append(genesis_block)
                
                # Update UTXO set atomically with genesis transaction
                utxo_updates = {}
                for i, output in enumerate(genesis_tx.outputs):
                    utxo_key = f"{genesis_tx.tx_id}:{i}"
                    utxo_updates[utxo_key] = {
                        'amount': output.amount,
                        'address': output.recipient_address,
                        'tx_id': genesis_tx.tx_id,
                        'output_index': i,
                        'is_genesis': True  # Mark as genesis UTXO
                    }
                
                self.utxo_set.atomic_update(utxo_updates)
                
                with self._stats_lock:
                    self._stats.blocks_processed += 1
                    self._stats.transactions_processed += 1
                
                logger.info("[GENESIS] Genesis Block Successfully Added to Chain")
                logger.info(f"   [UTXO] Genesis UTXO: {genesis_data['transactions'][0]['outputs'][0]['amount']} CC")
                logger.info(f"   [ADDRESS] Genesis Address: {genesis_data['transactions'][0]['outputs'][0]['recipient_address']}")
                logger.info(f"   [LENGTH] Blockchain Length: {len(self._chain)} block(s)")
                logger.info("[NETWORK] Network Consensus Genesis Block Loaded!")
                logger.info("[READY] Blockchain Ready for Transactions!")
    
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
        _, utxo_snapshot = self.utxo_set.create_snapshot()
        
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
    
    def _calculate_new_difficulty(self) -> int:
        """Calculate new difficulty based on recent block times"""
        if not self.difficulty_adjustment_enabled:
            return self.target_difficulty
        
        chain_length = len(self._chain)
        if chain_length < self.difficulty_adjustment_interval:
            return self.target_difficulty
        
        # Only adjust every N blocks
        if chain_length % self.difficulty_adjustment_interval != 0:
            return self.target_difficulty
        
        # Get the last N blocks for timing analysis
        recent_blocks = self._chain[-self.difficulty_adjustment_interval:]
        if len(recent_blocks) < 2:
            return self.target_difficulty
        
        # Calculate actual time taken for the interval
        start_time = recent_blocks[0].timestamp
        end_time = recent_blocks[-1].timestamp
        actual_time = end_time - start_time
        
        # Calculate expected time
        expected_time = self.target_block_time * (len(recent_blocks) - 1)
        
        if expected_time <= 0:
            return self.target_difficulty
        
        # Calculate adjustment ratio
        ratio = actual_time / expected_time
        
        # Determine new difficulty
        current_difficulty = self.target_difficulty
        
        if ratio < 0.5:  # Blocks coming too fast - increase difficulty
            new_difficulty = min(current_difficulty + self.max_difficulty_change, self.max_difficulty)
        elif ratio > 2.0:  # Blocks coming too slow - decrease difficulty  
            new_difficulty = max(current_difficulty - self.max_difficulty_change, self.min_difficulty)
        elif ratio < 0.75:  # Moderately too fast
            new_difficulty = min(current_difficulty + 1, self.max_difficulty)
        elif ratio > 1.5:  # Moderately too slow
            new_difficulty = max(current_difficulty - 1, self.min_difficulty)
        else:
            new_difficulty = current_difficulty  # No change needed
        
        if new_difficulty != current_difficulty:
            logger.info(f"[ADJUST] Dynamic Difficulty Adjustment Triggered!")
            logger.info(f"   [DIFF] Old Difficulty: {current_difficulty} -> New Difficulty: {new_difficulty}")
            logger.info(f"   [TIME] Block Time Ratio: {ratio:.2f} (Actual: {actual_time:.1f}s, Expected: {expected_time:.1f}s)")
            logger.info(f"   [TARGET] Target: {'Faster' if ratio < 1.0 else 'Slower'} block times detected")
            logger.info(f"   🔧 Mining difficulty {'increased' if new_difficulty > current_difficulty else 'decreased'} to maintain {self.target_block_time}s target")
            
            # Update our target difficulty
            self.target_difficulty = new_difficulty
        
        return new_difficulty
    
    def _handle_orphaned_block(self, block):
        """Handle blocks that can't be added to main chain (orphaned blocks)"""
        with self._orphaned_blocks_lock:
            # Check if we already have this orphaned block
            for orphaned in self._orphaned_blocks:
                if orphaned.hash == block.hash:
                    return
            
            # Add to orphaned blocks list
            self._orphaned_blocks.append(block)
            
            # Limit memory usage by removing oldest orphaned blocks
            while len(self._orphaned_blocks) > self._max_orphaned_blocks:
                self._orphaned_blocks.pop(0)
            
            with self._stats_lock:
                self._stats.orphaned_blocks += 1
            
            logger.info(f"🔀 Block {block.index} Orphaned (Fork Detected)")
            logger.info(f"   [HASH] Block Hash: {block.hash[:16]}...{block.hash[-8:]}")
            logger.info(f"   🔄 Previous Hash: {block.previous_hash[:16]}...")
            logger.info(f"   📦 Orphaned blocks stored: {len(self._orphaned_blocks)}/{self._max_orphaned_blocks}")
    
    def get_orphaned_blocks(self) -> List:
        """Get list of orphaned blocks"""
        with self._orphaned_blocks_lock:
            return copy.deepcopy(self._orphaned_blocks)
    
    def _attempt_orphan_recovery(self):
        """Try to recover orphaned blocks when new chain segments arrive"""
        with self._orphaned_blocks_lock:
            if not self._orphaned_blocks:
                return
            
            recovered_blocks = []
            remaining_orphans = []
            
            for orphaned_block in self._orphaned_blocks:
                # Check if this orphaned block can now connect to our chain
                if self._can_connect_orphaned_block(orphaned_block):
                    try:
                        if self._validate_block(orphaned_block):
                            recovered_blocks.append(orphaned_block)
                            logger.info(f"🔄 Orphaned Block {orphaned_block.index} Successfully Recovered!")
                            logger.info(f"   📋 Hash: {orphaned_block.hash[:16]}...{orphaned_block.hash[-8:]}")
                            logger.info(f"   🔗 Now connects to main chain")
                        else:
                            remaining_orphans.append(orphaned_block)
                    except Exception as e:
                        logger.error(f"Error recovering orphaned block: {e}")
                        remaining_orphans.append(orphaned_block)
                else:
                    remaining_orphans.append(orphaned_block)
            
            self._orphaned_blocks = remaining_orphans
            
            # Try to add recovered blocks
            for block in recovered_blocks:
                try:
                    self.add_block(block)
                except Exception as e:
                    logger.error(f"Failed to add recovered block: {e}")
    
    def _can_connect_orphaned_block(self, block) -> bool:
        """Check if an orphaned block can now connect to the main chain"""
        # Check if the block's previous_hash matches any block in our chain
        for chain_block in self._chain:
            if chain_block.hash == block.previous_hash:
                return True
        return False
    
    def _could_be_orphaned_block(self, block) -> bool:
        """Check if a block could be orphaned rather than just invalid"""
        try:
            # Basic structure validation (without chain connection check)
            if not hasattr(block, 'hash') or not hasattr(block, 'previous_hash'):
                return False
            
            if not hasattr(block, 'index') or not hasattr(block, 'transactions'):
                return False
            
            # Check if block has valid proof of work
            if not block.is_valid_hash():
                return False
            
            # If we get here, the block is structurally valid but couldn't connect
            # to our current chain - it's likely an orphaned block
            return True
            
        except Exception:
            return False

    @synchronized("blockchain_chain", LockOrder.BLOCKCHAIN, mode='write')
    def add_block(self, block, allow_reorganization: bool = True) -> bool:
        """
        Thread-safe block addition with immediate fork resolution and longest chain rule
        """
        current_chain_length = len(self._chain)
        
        # Handle different block scenarios
        if block.index == current_chain_length:
            # Normal sequential block - check for immediate conflicts
            if self._check_for_competing_blocks(block):
                logger.info(f"⚡ RACING BLOCKS: Multiple blocks for position #{block.index}")
                # Implement immediate longest chain rule
                if self._should_accept_competing_block(block):
                    logger.info(f"[ACCEPT] Accepting competing block (better chain)")
                    return self._add_sequential_block(block)
                else:
                    logger.info(f"❌ Rejecting competing block (keeping current)")
                    return False
            else:
                # No conflict, add normally
                return self._add_sequential_block(block)
                
        elif block.index < current_chain_length and allow_reorganization:
            # Potential fork - immediate evaluation for chain reorganization
            logger.info(f"🍴 Fork detected: Block #{block.index} vs chain length {current_chain_length}")
            
            # Immediate fork resolution instead of just storing
            if self._should_trigger_chain_reorganization(block):
                logger.info(f"🔄 CHAIN REORGANIZATION: Switching to longer fork")
                return self._perform_chain_reorganization(block)
            else:
                # Store for potential future reorganization
                if self._validate_block(block, allow_non_sequential=True):
                    self._handle_orphaned_block(block)
                    logger.info(f"Fork block stored as orphaned for potential future reorganization")
                return False
                
        elif block.index > current_chain_length:
            # Future block - should not happen at this level
            logger.warning(f"Future block #{block.index} rejected (chain length: {current_chain_length})")
            return False
        else:
            # Other cases
            if self._could_be_orphaned_block(block):
                self._handle_orphaned_block(block)
            return False
    
    def _add_sequential_block(self, block) -> bool:
        """Add the next sequential block to the chain"""
        if not self._validate_block(block):
            # Check if this could be an orphaned block (valid but can't connect)
            if self._could_be_orphaned_block(block):
                self._handle_orphaned_block(block)
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
            # Update state version when chain is modified
            self._update_chain_state_version(block)
            logger.info(f"Block {block.index} added to chain (state version: {self._chain_state_version})")
        
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
            
            # Perform difficulty adjustment after successful block addition
            self._calculate_new_difficulty()
            
            logger.info(f"[SUCCESS] Block {block.index} Successfully Added to Blockchain!")
            logger.info(f"   [HASH] Block Hash: {block.hash[:16]}...{block.hash[-8:]}")
            logger.info(f"   [TXN] Transactions: {len(block.transactions)} ({len([tx for tx in block.transactions if not tx.is_coinbase()])} user + 1 coinbase)")
            logger.info(f"   [LENGTH] Chain Length: {len(self._chain)} blocks")
            logger.info(f"   [UTXO] Total UTXO Count: {len(self.utxo_set._utxos)}")
            
            # Show transaction pool update
            with self._pool_lock.read_lock():
                remaining_txs = len(self._transaction_pool)
            logger.info(f"   📝 Transaction Pool: {remaining_txs} pending transactions")
            
            # Store block in database (non-blocking)
            self._store_block_in_database(block)
        
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
            
            logger.info(f"🔄 Blockchain Replacement Successful!")
            logger.info(f"   📊 New Chain Length: {len(new_chain)} blocks")
            logger.info(f"   🔗 Latest Block: {new_chain[-1].hash[:16]}...{new_chain[-1].hash[-8:]}")
            logger.info(f"   💰 Total UTXOs: {len(self.utxo_set._utxos)}")
            logger.info("   🔍 Checking for orphaned block recovery...")
            
            # Attempt to recover orphaned blocks after chain replacement
            orphan_count_before = len(self._orphaned_blocks) if hasattr(self, '_orphaned_blocks') else 0
            self._attempt_orphan_recovery()
            orphan_count_after = len(self._orphaned_blocks) if hasattr(self, '_orphaned_blocks') else 0
            recovered = orphan_count_before - orphan_count_after
            
            if recovered > 0:
                logger.info(f"   ✨ Recovered {recovered} orphaned block(s) into main chain!")
            else:
                logger.info("   📦 No orphaned blocks could be recovered")
        else:
            logger.error("Chain replacement failed - rolled back")
        
        return success
    
    @synchronized("blockchain_chain", LockOrder.BLOCKCHAIN, mode='write') 
    def replace_chain_if_valid(self, new_chain: List) -> bool:
        """
        Replace chain only if the new chain is valid and longer/heavier
        Used for fork resolution
        """
        try:
            if not new_chain:
                return False
            
            current_length = len(self._chain)
            new_length = len(new_chain)
            
            # Only replace if new chain is longer
            if new_length <= current_length:
                logger.debug(f"Chain replacement skipped: new chain not longer ({new_length} vs {current_length})")
                return False
            
            # Validate the new chain
            if not self._validate_full_chain(new_chain):
                logger.warning("Chain replacement failed: new chain is invalid")
                return False
            
            logger.info(f"🔄 Replacing chain: {current_length} -> {new_length} blocks")
            
            # Backup current chain
            backup_chain = self._chain.copy()
            backup_utxos = self._utxo_set.copy()
            
            try:
                # Replace the chain
                self._chain = new_chain.copy()
                
                # Rebuild UTXO set from new chain
                self._rebuild_utxo_set()
                
                logger.info(f"✅ Chain replacement successful")
                return True
                
            except Exception as e:
                logger.error(f"Chain replacement failed, rolling back: {e}")
                # Restore backup
                self._chain = backup_chain
                self._utxo_set = backup_utxos
                return False
                
        except Exception as e:
            logger.error(f"Error in replace_chain_if_valid: {e}")
            return False
    
    def smart_sync_with_peer_chain(self, peer_chain_data: List[Dict], peer_url: str) -> bool:
        """
        Industry-standard blockchain sync that preserves mining history
        Uses proper fork resolution and doesn't destroy local mining attribution
        """
        try:
            # Import the new sync module
            from ..blockchain.blockchain_sync import BlockchainSync, SyncResult
            
            logger.info(f"🔄 Starting smart sync with {peer_url}")
            
            # Create sync engine
            sync_engine = BlockchainSync(self)
            
            # Perform sync
            result, stats = sync_engine.sync_with_peer_chain(peer_chain_data, peer_url)
            
            if result == SyncResult.SUCCESS or result == SyncResult.FORK_RESOLVED:
                # Update blockchain statistics
                with self._stats_lock:
                    self._stats.blocks_processed = len(self._chain)
                    self._stats.utxo_count = len(self.utxo_set._utxos)
                    if stats.blocks_orphaned > 0:
                        self._stats.orphaned_blocks += stats.blocks_orphaned
                
                # Clear caches after successful sync
                with self._cache_lock:
                    self._validation_cache.clear()
                
                logger.info(f"✅ Smart sync completed successfully!")
                logger.info(f"   📊 Result: {result.value}")
                return True
                
            elif result == SyncResult.NO_CHANGES:
                logger.info("ℹ️  Smart sync: No changes needed")
                return True
            else:
                logger.warning(f"⚠️  Smart sync failed: {result.value}")
                return False
                
        except Exception as e:
            logger.error(f"Smart sync error: {e}")
            return False
                
    def _check_for_competing_blocks(self, new_block) -> bool:
        """Check if there are competing blocks for the same position"""
        try:
            # Check orphaned blocks for same index
            if hasattr(self, '_orphaned_blocks'):
                for orphaned in self._orphaned_blocks:
                    if orphaned.index == new_block.index and orphaned.hash != new_block.hash:
                        logger.info(f"Found competing block at position #{new_block.index}")
                        return True
            return False
        except Exception as e:
            logger.error(f"Error checking for competing blocks: {e}")
            return False
    
    def _should_accept_competing_block(self, new_block) -> bool:
        """Determine if a competing block should be accepted based on proof-of-work"""
        try:
            # Simple rule: accept block with better (more difficult) hash or timestamp
            current_block = self._chain[-1] if self._chain else None
            if not current_block:
                return True
            
            # Compare difficulty/work - in a real blockchain this would be more sophisticated
            new_work = self._calculate_block_work(new_block)
            current_work = self._calculate_block_work(current_block)
            
            if new_work > current_work:
                logger.info(f"New block has better work: {new_work} vs {current_work}")
                return True
            elif new_work == current_work:
                # Tie-breaker: earlier timestamp wins (first to mine)
                if new_block.timestamp < current_block.timestamp:
                    logger.info(f"New block mined earlier: {new_block.timestamp} vs {current_block.timestamp}")
                    return True
                else:
                    # Hash-based tie breaker (lexicographically smaller hash wins)
                    if new_block.hash < current_block.hash:
                        logger.info(f"New block wins hash tie-breaker")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error evaluating competing block: {e}")
            return False
    
    def _should_trigger_chain_reorganization(self, fork_block) -> bool:
        """Determine if a fork block should trigger chain reorganization"""
        try:
            # For now, only reorganize if we have a significantly longer fork
            # This is a simplified implementation - production would be more sophisticated
            
            # Check if this could be part of a longer chain by looking at orphaned blocks
            if not hasattr(self, '_orphaned_blocks'):
                return False
            
            # Build potential fork chain from orphaned blocks
            fork_chain = self._build_potential_fork_chain(fork_block)
            current_chain_length = len(self._chain)
            
            # Only reorganize if fork is longer
            if len(fork_chain) > current_chain_length:
                logger.info(f"Fork chain is longer: {len(fork_chain)} vs {current_chain_length}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error evaluating chain reorganization: {e}")
            return False
    
    def _perform_chain_reorganization(self, fork_block) -> bool:
        """Perform chain reorganization to switch to a longer fork"""
        try:
            logger.warning("⚠️  Chain reorganization not fully implemented - storing as orphaned")
            # For now, just store as orphaned until full reorganization is implemented
            if self._validate_block(fork_block, allow_non_sequential=True):
                self._handle_orphaned_block(fork_block)
            return False
            
        except Exception as e:
            logger.error(f"Error performing chain reorganization: {e}")
            return False
    
    def _build_potential_fork_chain(self, fork_block) -> list:
        """Build a potential fork chain from orphaned blocks"""
        try:
            # Simplified implementation - just return the single block for now
            return [fork_block]
            
        except Exception as e:
            logger.error(f"Error building fork chain: {e}")
            return []
    
    def _calculate_block_work(self, block) -> int:
        """Calculate the work/difficulty of a block"""
        try:
            # Simple work calculation based on difficulty
            difficulty = getattr(block, 'target_difficulty', 1)
            return 2 ** difficulty
            
        except Exception as e:
            logger.error(f"Error calculating block work: {e}")
            return 1
    
    def _update_chain_state_version(self, new_block=None):
        """Update blockchain state version for stale block detection"""
        try:
            with self._state_version_lock:
                self._chain_state_version += 1
                
                if new_block:
                    self._last_block_hash = new_block.hash
                    self._chain_tip_timestamp = new_block.timestamp
                elif self._chain:
                    # Update from current chain tip
                    latest_block = self._chain[-1]
                    self._last_block_hash = latest_block.hash
                    self._chain_tip_timestamp = latest_block.timestamp
                else:
                    self._last_block_hash = ""
                    self._chain_tip_timestamp = 0
                
                logger.debug(f"Chain state version updated to {self._chain_state_version}")
                
        except Exception as e:
            logger.error(f"Error updating chain state version: {e}")
    
    def get_chain_state_snapshot(self) -> Dict:
        """Get current blockchain state snapshot for template creation"""
        try:
            with self._state_version_lock:
                return {
                    'state_version': self._chain_state_version,
                    'chain_length': len(self._chain),
                    'last_block_hash': self._last_block_hash,
                    'tip_timestamp': self._chain_tip_timestamp,
                    'snapshot_time': time.time()
                }
        except Exception as e:
            logger.error(f"Error getting chain state snapshot: {e}")
            return {
                'state_version': 0,
                'chain_length': 0,
                'last_block_hash': "",
                'tip_timestamp': 0,
                'snapshot_time': time.time()
            }
    
    def is_state_stale(self, template_state: Dict, max_age_seconds: int = 120) -> bool:
        """Check if a mining template state is stale compared to current chain state"""
        try:
            current_state = self.get_chain_state_snapshot()
            
            # Check if state version has changed (chain was modified)
            if template_state.get('state_version', 0) != current_state['state_version']:
                logger.info(f"State version mismatch: template {template_state.get('state_version')} vs current {current_state['state_version']}")
                return True
            
            # Check if chain length has changed
            if template_state.get('chain_length', 0) != current_state['chain_length']:
                logger.info(f"Chain length changed: template {template_state.get('chain_length')} vs current {current_state['chain_length']}")
                return True
            
            # Check if template is too old
            template_time = template_state.get('snapshot_time', 0)
            current_time = time.time()
            if current_time - template_time > max_age_seconds:
                logger.info(f"Template too old: {current_time - template_time:.1f}s (max: {max_age_seconds}s)")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking state staleness: {e}")
            return True  # Assume stale if we can't verify
    
    def merge_peer_blocks(self, peer_blocks: List, validate: bool = True) -> int:
        """
        Merge new blocks from peer while preserving existing mining history
        Returns number of blocks successfully added
        """
        blocks_added = 0
        
        try:
            with self._chain_lock.write_lock():
                current_length = len(self._chain)
                
                for block in peer_blocks:
                    # Skip blocks we already have
                    if block.index < current_length:
                        continue
                    
                    # Validate block if requested
                    if validate and not self._validate_single_block(block, self._chain):
                        logger.warning(f"⚠️  Skipping invalid block #{block.index}")
                        continue
                    
                    # Add block to chain
                    self._chain.append(block)
                    blocks_added += 1
                    
                    logger.info(f"✅ Merged block #{block.index} (mining history preserved)")
                
                # Update statistics
                if blocks_added > 0:
                    with self._stats_lock:
                        self._stats.blocks_processed = len(self._chain)
                    
                    logger.info(f"🎉 Merged {blocks_added} new blocks successfully")
                
        except Exception as e:
            logger.error(f"❌ Block merge error: {e}")
            
        return blocks_added
    
    def _validate_single_block(self, block, chain: List) -> bool:
        """Validate a single block against the given chain"""
        try:
            # Check index sequence
            expected_index = len(chain)
            if block.index != expected_index:
                return False
            
            # Check previous hash linkage
            if len(chain) > 0:
                last_block = chain[-1]
                if block.previous_hash != last_block.hash:
                    return False
            
            # Check proof of work
            target = "0" * getattr(block, 'target_difficulty', 1)
            if not block.hash.startswith(target):
                return False
            
            return True
            
        except Exception:
            return False
    
    def get_fork_info(self) -> Dict:
        """Get information about any orphaned blocks (preserved mining history)"""
        try:
            from ..blockchain.blockchain_sync import BlockchainSync
            sync_engine = BlockchainSync(self)
            orphaned_blocks = sync_engine.get_orphaned_blocks()
            
            return {
                'has_orphaned_blocks': len(orphaned_blocks) > 0,
                'orphaned_count': len(orphaned_blocks),
                'orphaned_mining_history': [
                    {
                        'block_index': block.index,
                        'miner_preserved': True,
                        'timestamp': getattr(block, 'timestamp', 0)
                    } for block in orphaned_blocks
                ]
            }
        except Exception as e:
            logger.error(f"Error getting fork info: {e}")
            return {'has_orphaned_blocks': False, 'orphaned_count': 0}
    
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
    
    def get_block_by_index(self, index: int):
        """Get block by index with thread safety"""
        with self._chain_lock.read_lock():
            if 0 <= index < len(self._chain):
                return self._chain[index]
            return None
    
    def get_blocks_range(self, start: int, end: int) -> List:
        """Get range of blocks with thread safety"""
        with self._chain_lock.read_lock():
            if start < 0:
                start = 0
            if end >= len(self._chain):
                end = len(self._chain) - 1
            return self._chain[start:end+1] if start <= end else []
    
    def get_chain_info(self) -> Dict:
        """Get chain information"""
        with self._chain_lock.read_lock():
            if not self._chain:
                return {
                    'length': 0,
                    'genesis_hash': None,
                    'latest_hash': None,
                    'latest_timestamp': None
                }
            
            latest_block = self._chain[-1]
            genesis_block = self._chain[0]
            
            return {
                'length': len(self._chain),
                'genesis_hash': genesis_block.hash,
                'latest_hash': latest_block.hash,
                'latest_timestamp': latest_block.timestamp,
                'latest_index': latest_block.index
            }
    
    def create_block_template(self, miner_address: str, mining_node: str = None):
        """
        Create mining block template with thread safety and state versioning
        """
        # Capture current blockchain state for template validation
        template_state = self.get_chain_state_snapshot()
        
        with self._pool_lock.read_lock():
            # Get transactions from pool (limit for block size)
            transactions = self._transaction_pool[:1000].copy()
        
        # Calculate fees with UTXO snapshot
        _, utxo_snapshot = self.utxo_set.create_snapshot()
        total_fees = 0.0
        
        for tx in transactions:
            try:
                fee = tx.get_fee({"utxo_set": utxo_snapshot})
                total_fees += fee
            except:
                continue
        
        # Create coinbase transaction
        try:
            from ..blockchain.bitcoin_transaction import Transaction
        except ImportError:
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
            from src.blockchain.bitcoin_transaction import Transaction
        coinbase_tx = Transaction.create_coinbase_transaction(
            miner_address, 
            self.block_reward + total_fees,
            self.get_chain_length()
        )
        
        # Create block template
        with self._chain_lock.read_lock():
            all_transactions = [coinbase_tx] + transactions
            
            # Import Block from proper module
            try:
                from ..blockchain.block import Block
            except ImportError:
                import sys, os
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
                from src.blockchain.block import Block
            
            new_block = Block(
                len(self._chain),
                all_transactions,
                self._chain[-1].hash if self._chain else "0" * 64,
                target_difficulty=self.target_difficulty,
                mining_node=mining_node
            )
        
        # Add state versioning metadata to block template
        if not hasattr(new_block, '_template_metadata'):
            new_block._template_metadata = {}
        
        new_block._template_metadata.update({
            'creation_state': template_state,
            'created_at': time.time(),
            'fees_included': total_fees,
            'template_version': template_state['state_version']
        })
        
        logger.info(f"Block template created: index={new_block.index}, txs={len(all_transactions)}, fees={total_fees}, state_v{template_state['state_version']}")
        return new_block
    
    def _store_block_in_database(self, block):
        """Store block in PostgreSQL database (non-blocking, preserves all functionality)"""
        if not self.database_enabled:
            logger.debug(f"Database not enabled - block #{block.index} not stored to database")
            return
            
        try:
            # Store block in database in background thread to avoid blocking
            import threading
            
            def store_block():
                try:
                    logger.info(f"🔄 Attempting to store block #{block.index} in database...")
                    success = self.block_dao.add_block(block)
                    if success:
                        logger.info(f"💾 Block #{block.index} successfully stored in database")
                    else:
                        logger.warning(f"⚠️  Failed to store block #{block.index} in database - add_block returned False")
                except Exception as e:
                    logger.error(f"❌ Database storage error for block #{block.index}: {e}")
                    import traceback
                    logger.error(f"Database storage traceback: {traceback.format_exc()}")
            
            # Store in background thread
            storage_thread = threading.Thread(target=store_block, daemon=True)
            storage_thread.start()
            logger.info(f"📤 Started database storage thread for block #{block.index}")
            
        except Exception as e:
            logger.error(f"Error creating database storage thread: {e}")
            import traceback
            logger.error(f"Thread creation traceback: {traceback.format_exc()}")
    
    def get_database_statistics(self) -> Dict:
        """Get statistics from database"""
        if not self.database_enabled:
            return {'database_enabled': False}
            
        try:
            block_stats = self.block_dao.get_mining_statistics()
            tx_stats = self.tx_dao.get_transaction_statistics() 
            utxo_stats = self.tx_dao.get_utxo_statistics()
            
            return {
                'database_enabled': True,
                'blockchain_stats': block_stats,
                'transaction_stats': tx_stats,
                'utxo_stats': utxo_stats
            }
        except Exception as e:
            logger.error(f"Error getting database statistics: {e}")
            return {'database_enabled': True, 'error': str(e)}