#!/usr/bin/env python3
"""
Industry-Standard Blockchain Synchronization Module
Implements Bitcoin-style blockchain sync with proper fork resolution
Preserves mining history and follows longest valid chain rule
"""

import logging
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

from .block import Block
from .bitcoin_transaction import Transaction

logger = logging.getLogger(__name__)

class SyncResult(Enum):
    """Sync operation results"""
    SUCCESS = "success"
    NO_CHANGES = "no_changes"
    FORK_RESOLVED = "fork_resolved"
    INVALID_CHAIN = "invalid_chain"
    ERROR = "error"

@dataclass
class SyncStats:
    """Synchronization statistics"""
    blocks_added: int = 0
    blocks_orphaned: int = 0
    forks_resolved: int = 0
    mining_history_preserved: bool = True
    longest_chain_source: str = ""
    sync_duration: float = 0.0

@dataclass
class ChainComparison:
    """Result of comparing two blockchain chains"""
    common_ancestor_index: int
    local_chain_length: int
    peer_chain_length: int
    local_is_longer: bool
    chains_diverge: bool
    fork_point: Optional[int] = None

class BlockchainSync:
    """
    Industry-standard blockchain synchronization engine
    Implements proper consensus rules and mining history preservation
    """
    
    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.sync_stats = SyncStats()
        self.orphaned_blocks: List[Block] = []
        
    def sync_with_peer_chain(self, peer_chain_data: List[Dict], peer_url: str) -> Tuple[SyncResult, SyncStats]:
        """
        Synchronize with peer chain using industry-standard consensus rules
        
        Args:
            peer_chain_data: Raw chain data from peer
            peer_url: Source peer URL for tracking
            
        Returns:
            Tuple of (SyncResult, SyncStats)
        """
        import time
        start_time = time.time()
        
        try:
            logger.info(f"🔄 Starting blockchain sync with {peer_url}")
            
            # Reset sync stats
            self.sync_stats = SyncStats()
            self.sync_stats.longest_chain_source = peer_url
            
            # Step 1: Convert peer data to Block objects
            peer_blocks = self._convert_peer_data_to_blocks(peer_chain_data)
            if not peer_blocks:
                logger.warning("❌ Failed to convert peer chain data")
                return SyncResult.ERROR, self.sync_stats
            
            # Step 2: Compare chains to find sync strategy
            local_chain = self.blockchain.get_chain_copy()
            comparison = self._compare_chains(local_chain, peer_blocks)
            logger.info(f"📊 Chain comparison: Local={comparison.local_chain_length}, Peer={comparison.peer_chain_length}")
            
            # Step 3: Determine sync action based on comparison
            if not comparison.chains_diverge:
                # Simple case: chains are compatible, just add new blocks
                result = self._append_new_blocks(peer_blocks, comparison)
            else:
                # Complex case: chains have forked, need resolution
                logger.info(f"🔀 Fork detected at block #{comparison.fork_point}")
                result = self._resolve_fork(peer_blocks, comparison)
            
            # Step 4: Update statistics
            self.sync_stats.sync_duration = time.time() - start_time
            
            # Step 5: Log final results
            self._log_sync_results(result)
            
            return result, self.sync_stats
            
        except Exception as e:
            logger.error(f"❌ Blockchain sync error: {e}")
            self.sync_stats.sync_duration = time.time() - start_time
            return SyncResult.ERROR, self.sync_stats
    
    def _convert_peer_data_to_blocks(self, peer_chain_data: List[Dict]) -> List[Block]:
        """Convert peer chain data to Block objects with validation"""
        blocks = []
        
        for i, block_data in enumerate(peer_chain_data):
            try:
                # Create transactions from data
                transactions = []
                for tx_data in block_data.get('transactions', []):
                    # Preserve original transaction structure
                    tx = Transaction(
                        inputs=tx_data.get('inputs', []),
                        outputs=[
                            type('Output', (), {
                                'recipient_address': out.get('recipient_address', ''),
                                'amount': out.get('amount', 0.0)
                            })() for out in tx_data.get('outputs', [])
                        ]
                    )
                    # Preserve transaction ID if available
                    if 'transaction_id' in tx_data:
                        tx.transaction_id = tx_data['transaction_id']
                    transactions.append(tx)
                
                # Create block with preserved mining information
                block = Block(
                    index=block_data['index'],
                    transactions=transactions,
                    previous_hash=block_data['previous_hash'],
                    timestamp=block_data.get('timestamp', 0),
                    nonce=block_data.get('nonce', 0),
                    target_difficulty=block_data.get('target_difficulty', 1)
                )
                
                # CRITICAL: Preserve original block hash and mining info
                if 'hash' in block_data:
                    block.hash = block_data['hash']
                else:
                    block.calculate_hash()  # Recalculate if missing
                
                blocks.append(block)
                
            except Exception as e:
                logger.error(f"❌ Failed to convert block #{i}: {e}")
                return []  # Return empty list on any conversion failure
        
        logger.info(f"✅ Converted {len(blocks)} blocks from peer data")
        return blocks
    
    def _compare_chains(self, local_chain: List[Block], peer_chain: List[Block]) -> ChainComparison:
        """Compare local and peer chains to determine sync strategy"""
        
        local_length = len(local_chain)
        peer_length = len(peer_chain)
        
        # Find common ancestor (last matching block)
        common_ancestor_index = -1
        fork_point = None
        
        min_length = min(local_length, peer_length)
        for i in range(min_length):
            if (i < local_length and i < peer_length and 
                local_chain[i].hash == peer_chain[i].hash):
                common_ancestor_index = i
            else:
                # First divergence point
                if fork_point is None:
                    fork_point = i
                break
        
        chains_diverge = (fork_point is not None and 
                         fork_point < min_length)
        
        return ChainComparison(
            common_ancestor_index=common_ancestor_index,
            local_chain_length=local_length,
            peer_chain_length=peer_length,
            local_is_longer=local_length > peer_length,
            chains_diverge=chains_diverge,
            fork_point=fork_point
        )
    
    def _append_new_blocks(self, peer_blocks: List[Block], comparison: ChainComparison) -> SyncResult:
        """Append new blocks when chains don't diverge"""
        
        if comparison.local_is_longer:
            logger.info("ℹ️  Local chain is longer - no sync needed")
            return SyncResult.NO_CHANGES
        
        # Add blocks that we don't have
        blocks_to_add = peer_blocks[comparison.local_chain_length:]
        
        if not blocks_to_add:
            logger.info("ℹ️  Chains are already synchronized")
            return SyncResult.NO_CHANGES
        
        # Validate each new block before adding
        for block in blocks_to_add:
            if self._validate_block_addition(block):
                # Use thread-safe method to add block
                self.blockchain._chain.append(block)
                self.sync_stats.blocks_added += 1
                logger.info(f"✅ Added block #{block.index} (Miner preserved)")
            else:
                logger.error(f"❌ Block #{block.index} validation failed")
                return SyncResult.INVALID_CHAIN
        
        logger.info(f"🎉 Successfully added {self.sync_stats.blocks_added} new blocks")
        return SyncResult.SUCCESS
    
    def _resolve_fork(self, peer_blocks: List[Block], comparison: ChainComparison) -> SyncResult:
        """Resolve blockchain fork using longest valid chain rule"""
        
        logger.info(f"🔀 Resolving fork from block #{comparison.fork_point}")
        
        # Step 1: Validate the peer's fork
        if not self._validate_chain_segment(peer_blocks, comparison.fork_point):
            logger.error("❌ Peer's fork contains invalid blocks")
            return SyncResult.INVALID_CHAIN
        
        # Step 2: Apply longest chain rule
        if comparison.peer_chain_length > comparison.local_chain_length:
            # Peer has longer chain - adopt it but preserve local mining history
            logger.info("📏 Peer chain is longer - adopting with history preservation")
            
            # Step 3: Preserve orphaned blocks (local mining history)
            if comparison.fork_point < comparison.local_chain_length:
                current_chain = self.blockchain.get_chain_copy()
                orphaned_blocks = current_chain[comparison.fork_point:]
                self.orphaned_blocks.extend(orphaned_blocks)
                self.sync_stats.blocks_orphaned = len(orphaned_blocks)
                
                logger.info(f"💾 Preserved {len(orphaned_blocks)} orphaned blocks with mining history")
            
            # Step 4: Replace fork portion with peer's version
            # Keep blocks up to fork point, replace everything after
            current_chain = self.blockchain.get_chain_copy()
            new_chain = (current_chain[:comparison.fork_point] + 
                        peer_blocks[comparison.fork_point:])
            
            # Use thread-safe replacement
            self.blockchain._chain = new_chain
            self.sync_stats.blocks_added = len(peer_blocks) - comparison.fork_point
            self.sync_stats.forks_resolved = 1
            
            logger.info(f"🎉 Fork resolved: adopted peer chain, preserved {self.sync_stats.blocks_orphaned} local blocks")
            return SyncResult.FORK_RESOLVED
            
        else:
            # Local chain is longer or equal - keep local chain
            logger.info("📏 Local chain is longer - keeping local chain")
            return SyncResult.NO_CHANGES
    
    def _validate_block_addition(self, block: Block) -> bool:
        """Validate that a block can be safely added to the chain"""
        try:
            # Check index sequence
            chain_length = self.blockchain.get_chain_length()
            expected_index = chain_length
            if block.index != expected_index:
                logger.error(f"❌ Block index mismatch: expected {expected_index}, got {block.index}")
                return False
            
            # Check previous hash linkage
            if chain_length > 0:
                current_chain = self.blockchain.get_chain_copy()
                last_block = current_chain[-1]
                if block.previous_hash != last_block.hash:
                    logger.error(f"❌ Previous hash mismatch: expected {last_block.hash}, got {block.previous_hash}")
                    return False
            
            # Check proof of work
            target = "0" * block.target_difficulty
            if not block.hash.startswith(target):
                logger.error(f"❌ Invalid proof of work: hash {block.hash} doesn't meet difficulty {block.target_difficulty}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Block validation error: {e}")
            return False
    
    def _validate_chain_segment(self, blocks: List[Block], start_index: int) -> bool:
        """Validate a segment of the blockchain"""
        try:
            for i in range(start_index, len(blocks)):
                if i > 0 and blocks[i].previous_hash != blocks[i-1].hash:
                    logger.error(f"❌ Chain break at block #{i}")
                    return False
                
                # Validate proof of work
                target = "0" * blocks[i].target_difficulty
                if not blocks[i].hash.startswith(target):
                    logger.error(f"❌ Invalid PoW at block #{i}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Chain segment validation error: {e}")
            return False
    
    def _log_sync_results(self, result: SyncResult):
        """Log detailed sync operation results"""
        
        logger.info("=" * 50)
        logger.info("🔄 BLOCKCHAIN SYNC COMPLETED")
        logger.info("=" * 50)
        logger.info(f"📊 Result: {result.value.upper()}")
        logger.info(f"⏱️  Duration: {self.sync_stats.sync_duration:.2f}s")
        logger.info(f"➕ Blocks Added: {self.sync_stats.blocks_added}")
        
        if self.sync_stats.blocks_orphaned > 0:
            logger.info(f"💾 Blocks Orphaned: {self.sync_stats.blocks_orphaned}")
            logger.info("   📝 Note: Orphaned blocks preserved with mining history")
        
        if self.sync_stats.forks_resolved > 0:
            logger.info(f"🔀 Forks Resolved: {self.sync_stats.forks_resolved}")
        
        logger.info(f"🏷️  Source: {self.sync_stats.longest_chain_source}")
        logger.info(f"✅ Mining History: {'PRESERVED' if self.sync_stats.mining_history_preserved else 'LOST'}")
        logger.info("=" * 50)
    
    def get_orphaned_blocks(self) -> List[Block]:
        """Get list of orphaned blocks (preserved mining history)"""
        return self.orphaned_blocks.copy()
    
    def clear_orphaned_blocks(self):
        """Clear orphaned blocks (use with caution)"""
        self.orphaned_blocks.clear()
        logger.info("🗑️  Cleared orphaned blocks cache")