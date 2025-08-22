"""
Block Data Access Object for ChainCore
Handles all database operations related to blockchain blocks
"""

import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from .connection import get_db_manager
from ..blockchain.block import Block

logger = logging.getLogger(__name__)

class BlockDAO:
    """Data Access Object for blockchain blocks"""
    
    def __init__(self):
        self.db = get_db_manager()
    
    def add_block(self, block: Block) -> bool:
        """Add a new block to the database"""
        try:
            # Prepare block data
            block_data = block.to_dict()
            
            # Extract mining information
            miner_node = "unknown"
            miner_address = "unknown"
            
            if hasattr(block, '_mining_metadata') and block._mining_metadata:
                miner_node = block._mining_metadata.get('mining_node', 'unknown')
                miner_address = block._mining_metadata.get('miner_address', 'unknown')
            
            # If miner_address is still unknown, try to get from coinbase transaction
            if miner_address == "unknown" and block.transactions:
                coinbase_tx = block.transactions[0]
                if coinbase_tx.outputs:
                    miner_address = coinbase_tx.outputs[0].recipient_address
            
            # Insert block using stored function
            query = """
                SELECT add_block(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                block.index,
                block.hash,
                block.previous_hash,
                block.merkle_root,
                float(block.timestamp),
                block.nonce,
                block.target_difficulty,
                miner_node,
                miner_address,
                json.dumps(block_data)
            )
            
            result = self.db.execute_query(query, params, fetch_one=True)
            block_id = result[0] if result else None
            
            if block_id:
                # Add transactions for this block
                self._add_block_transactions(block, block_id)
                
                logger.info(f"✅ Block #{block.index} added to database (ID: {block_id})")
                logger.info(f"   🏷️  Hash: {block.hash[:16]}...")
                logger.info(f"   ⛏️  Miner: {miner_node} ({miner_address[:16]}...)")
                logger.info(f"   📝 Transactions: {len(block.transactions)}")
                
                return True
            else:
                logger.error(f"❌ Failed to add block #{block.index} to database")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error adding block #{block.index} to database: {e}")
            return False
    
    def _add_block_transactions(self, block: Block, block_id: int):
        """Add all transactions for a block"""
        try:
            from .transaction_dao import TransactionDAO
            tx_dao = TransactionDAO()
            
            for tx in block.transactions:
                tx_dao.add_transaction(tx, block_id, block.index)
                
        except Exception as e:
            logger.error(f"Error adding transactions for block #{block.index}: {e}")
    
    def get_block_by_index(self, block_index: int) -> Optional[Dict]:
        """Get a block by its index"""
        try:
            query = """
                SELECT * FROM blocks WHERE block_index = %s
            """
            result = self.db.execute_query(query, (block_index,), fetch_one=True)
            
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error getting block #{block_index}: {e}")
            return None
    
    def get_block_by_hash(self, block_hash: str) -> Optional[Dict]:
        """Get a block by its hash"""
        try:
            query = """
                SELECT * FROM blocks WHERE hash = %s
            """
            result = self.db.execute_query(query, (block_hash,), fetch_one=True)
            
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error getting block by hash {block_hash}: {e}")
            return None
    
    def get_latest_block(self) -> Optional[Dict]:
        """Get the latest block"""
        try:
            query = """
                SELECT * FROM blocks 
                ORDER BY block_index DESC 
                LIMIT 1
            """
            result = self.db.execute_query(query, fetch_one=True)
            
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest block: {e}")
            return None
    
    def get_blockchain_length(self) -> int:
        """Get the current blockchain length"""
        try:
            query = """
                SELECT COUNT(*) as length FROM blocks
            """
            result = self.db.execute_query(query, fetch_one=True)
            
            if result:
                return result[0]
            return 0
            
        except Exception as e:
            logger.error(f"Error getting blockchain length: {e}")
            return 0
    
    def get_blocks_range(self, start_index: int, end_index: int) -> List[Dict]:
        """Get a range of blocks"""
        try:
            query = """
                SELECT * FROM blocks 
                WHERE block_index >= %s AND block_index <= %s
                ORDER BY block_index ASC
            """
            results = self.db.execute_query(query, (start_index, end_index), fetch_all=True)
            
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"Error getting blocks range {start_index}-{end_index}: {e}")
            return []
    
    def get_blocks_by_miner(self, miner_node: str, limit: int = 100) -> List[Dict]:
        """Get blocks mined by a specific node"""
        try:
            query = """
                SELECT * FROM blocks 
                WHERE miner_node = %s
                ORDER BY block_index DESC
                LIMIT %s
            """
            results = self.db.execute_query(query, (miner_node, limit), fetch_all=True)
            
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"Error getting blocks for miner {miner_node}: {e}")
            return []
    
    def get_mining_statistics(self) -> Dict[str, Any]:
        """Get comprehensive mining statistics"""
        try:
            query = """
                SELECT 
                    COUNT(*) as total_blocks,
                    COUNT(DISTINCT miner_node) as unique_miners,
                    AVG(difficulty) as avg_difficulty,
                    MIN(timestamp) as first_block_time,
                    MAX(timestamp) as latest_block_time,
                    SUM(transaction_count) as total_transactions
                FROM blocks
            """
            result = self.db.execute_query(query, fetch_one=True)
            
            if result:
                stats = dict(result)
                
                # Get mining distribution
                query2 = """
                    SELECT 
                        miner_node,
                        COUNT(*) as blocks_mined,
                        AVG(difficulty) as avg_difficulty,
                        SUM(transaction_count) as transactions_processed
                    FROM blocks
                    GROUP BY miner_node
                    ORDER BY blocks_mined DESC
                """
                distribution = self.db.execute_query(query2, fetch_all=True)
                stats['mining_distribution'] = [dict(row) for row in distribution] if distribution else []
                
                return stats
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting mining statistics: {e}")
            return {}
    
    def verify_blockchain_integrity(self) -> Dict[str, Any]:
        """Verify blockchain integrity by checking hash chain"""
        try:
            query = """
                SELECT 
                    block_index,
                    hash,
                    previous_hash,
                    LAG(hash) OVER (ORDER BY block_index) as expected_previous_hash
                FROM blocks
                ORDER BY block_index
            """
            results = self.db.execute_query(query, fetch_all=True)
            
            issues = []
            total_blocks = 0
            
            for row in results:
                total_blocks += 1
                if row['block_index'] > 0:  # Skip genesis block
                    if row['previous_hash'] != row['expected_previous_hash']:
                        issues.append({
                            'block_index': row['block_index'],
                            'issue': 'hash_mismatch',
                            'expected': row['expected_previous_hash'],
                            'actual': row['previous_hash']
                        })
            
            return {
                'total_blocks': total_blocks,
                'integrity_issues': issues,
                'is_valid': len(issues) == 0
            }
            
        except Exception as e:
            logger.error(f"Error verifying blockchain integrity: {e}")
            return {'error': str(e), 'is_valid': False}
    
    def get_block_count_by_difficulty(self) -> List[Dict]:
        """Get block count grouped by difficulty"""
        try:
            query = """
                SELECT 
                    difficulty,
                    COUNT(*) as block_count,
                    AVG(transaction_count) as avg_transactions
                FROM blocks
                GROUP BY difficulty
                ORDER BY difficulty
            """
            results = self.db.execute_query(query, fetch_all=True)
            
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"Error getting difficulty statistics: {e}")
            return []