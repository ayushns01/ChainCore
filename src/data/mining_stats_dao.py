"""
Mining Statistics Data Access Object for ChainCore
Handles all database operations related to mining statistics
"""

import logging
from typing import Dict, Optional, List, Any
from datetime import datetime
import time

from .simple_connection import get_simple_db_manager

logger = logging.getLogger(__name__)

class MiningStatsDAO:
    """Data Access Object for mining statistics"""
    
    def __init__(self):
        self.db = get_simple_db_manager()
    
    def record_mining_stats(self, 
                          node_id: str, 
                          block_id: int, 
                          mining_duration_seconds: float,
                          hash_attempts: int,
                          hash_rate: float,
                          mining_started_at: float,
                          mining_completed_at: float) -> bool:
        """Record mining statistics for a block"""
        try:
            query = """
                INSERT INTO mining_stats (
                    node_id, block_id, mining_duration_seconds, 
                    hash_attempts, hash_rate, 
                    mining_started_at, mining_completed_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            # Convert timestamps to datetime objects
            started_at = datetime.fromtimestamp(mining_started_at)
            completed_at = datetime.fromtimestamp(mining_completed_at)
            
            params = (
                node_id,
                block_id, 
                mining_duration_seconds,
                hash_attempts,
                hash_rate,
                started_at,
                completed_at
            )
            
            self.db.execute_query(query, params)
            logger.info(f"✅ Mining stats recorded for block {block_id} by {node_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error recording mining stats: {e}")
            return False
    
    def get_mining_stats_by_node(self, node_id: str, limit: int = 100) -> List[Dict]:
        """Get mining statistics for a specific node"""
        try:
            query = """
                SELECT ms.*, b.block_index, b.hash as block_hash
                FROM mining_stats ms
                JOIN blocks b ON ms.block_id = b.id
                WHERE ms.node_id = %s
                ORDER BY ms.mining_completed_at DESC
                LIMIT %s
            """
            
            results = self.db.execute_query(query, (node_id, limit), fetch_all=True)
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"Error getting mining stats for {node_id}: {e}")
            return []
    
    def get_overall_mining_stats(self) -> Dict[str, Any]:
        """Get overall mining statistics across all nodes"""
        try:
            query = """
                SELECT 
                    COUNT(*) as total_mining_sessions,
                    COUNT(DISTINCT node_id) as unique_miners,
                    AVG(mining_duration_seconds) as avg_mining_duration,
                    AVG(hash_rate) as avg_hash_rate,
                    SUM(hash_attempts) as total_hash_attempts,
                    MIN(mining_started_at) as first_mining_session,
                    MAX(mining_completed_at) as latest_mining_session
                FROM mining_stats
            """
            
            result = self.db.execute_query(query, fetch_one=True)
            
            if result:
                stats = dict(result)
                
                # Get node-wise breakdown
                node_query = """
                    SELECT 
                        node_id,
                        COUNT(*) as blocks_mined,
                        AVG(mining_duration_seconds) as avg_mining_time,
                        AVG(hash_rate) as avg_hash_rate,
                        SUM(hash_attempts) as total_hash_attempts
                    FROM mining_stats
                    GROUP BY node_id
                    ORDER BY blocks_mined DESC
                """
                
                node_stats = self.db.execute_query(node_query, fetch_all=True)
                stats['node_breakdown'] = [dict(row) for row in node_stats] if node_stats else []
                
                return stats
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting overall mining stats: {e}")
            return {}
    
    def get_recent_mining_activity(self, hours: int = 24) -> List[Dict]:
        """Get recent mining activity within specified hours"""
        try:
            query = """
                SELECT 
                    ms.*,
                    b.block_index,
                    b.hash as block_hash,
                    b.miner_address
                FROM mining_stats ms
                JOIN blocks b ON ms.block_id = b.id
                WHERE ms.mining_completed_at >= NOW() - INTERVAL '%s hours'
                ORDER BY ms.mining_completed_at DESC
            """
            
            results = self.db.execute_query(query, (hours,), fetch_all=True)
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"Error getting recent mining activity: {e}")
            return []