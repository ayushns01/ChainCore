"""
Node Data Access Object for ChainCore
Handles all database operations related to network nodes
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from .simple_connection import get_simple_db_manager

logger = logging.getLogger(__name__)

class NodeDAO:
    """Data Access Object for network nodes"""
    
    def __init__(self):
        self.db = get_simple_db_manager()
    
    def register_node(self, node_id: str, api_port: int, p2p_port: int = None) -> bool:
        """Register a new node or update existing node as active"""
        try:
            # Create node URL
            node_url = f"http://localhost:{api_port}"
            
            # Check if node already exists
            existing_node = self.get_node_by_id(node_id)
            
            if existing_node:
                # Update existing node to active status
                query = """
                    UPDATE nodes 
                    SET node_url = %s, api_port = %s, status = 'active', last_seen = CURRENT_TIMESTAMP
                    WHERE node_id = %s
                """
                params = (node_url, api_port, node_id)
                self.db.execute_query(query, params)
                logger.info(f"✅ Updated existing node {node_id} to active status")
            else:
                # Insert new node
                query = """
                    INSERT INTO nodes (node_id, node_url, api_port, status, last_seen)
                    VALUES (%s, %s, %s, 'active', CURRENT_TIMESTAMP)
                """
                params = (node_id, node_url, api_port)
                self.db.execute_query(query, params)
                logger.info(f"✅ Registered new node {node_id} at {node_url}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error registering node {node_id}: {e}")
            return False
    
    def deregister_node(self, node_id: str) -> bool:
        """Mark a node as inactive"""
        try:
            query = """
                UPDATE nodes 
                SET status = 'inactive', last_seen = CURRENT_TIMESTAMP
                WHERE node_id = %s
            """
            self.db.execute_query(query, (node_id,))
            logger.info(f"✅ Deregistered node {node_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deregistering node {node_id}: {e}")
            return False
    
    def update_node_heartbeat(self, node_id: str) -> bool:
        """Update node's last_seen timestamp"""
        try:
            query = """
                UPDATE nodes 
                SET last_seen = CURRENT_TIMESTAMP
                WHERE node_id = %s AND status = 'active'
            """
            result = self.db.execute_query(query, (node_id,))
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating heartbeat for node {node_id}: {e}")
            return False
    
    def get_node_by_id(self, node_id: str) -> Optional[Dict]:
        """Get node information by node ID"""
        try:
            query = "SELECT * FROM nodes WHERE node_id = %s"
            result = self.db.execute_query(query, (node_id,), fetch_one=True)
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"❌ Error getting node {node_id}: {e}")
            return None
    
    def get_active_nodes(self) -> List[Dict]:
        """Get all active nodes"""
        try:
            query = """
                SELECT * FROM nodes 
                WHERE status = 'active' 
                ORDER BY last_seen DESC
            """
            results = self.db.execute_query(query, fetch_all=True)
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"❌ Error getting active nodes: {e}")
            return []
    
    def get_all_nodes(self) -> List[Dict]:
        """Get all nodes regardless of status"""
        try:
            query = "SELECT * FROM nodes ORDER BY created_at DESC"
            results = self.db.execute_query(query, fetch_all=True)
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"❌ Error getting all nodes: {e}")
            return []
    
    def update_mining_stats(self, node_id: str, blocks_mined_increment: int = 1, 
                           reward_amount: float = 0.0) -> bool:
        """Update mining statistics for a node"""
        try:
            query = """
                UPDATE nodes 
                SET blocks_mined = blocks_mined + %s,
                    total_rewards = total_rewards + %s,
                    last_seen = CURRENT_TIMESTAMP
                WHERE node_id = %s
            """
            params = (blocks_mined_increment, reward_amount, node_id)
            self.db.execute_query(query, params)
            logger.info(f"✅ Updated mining stats for node {node_id}: +{blocks_mined_increment} blocks, +{reward_amount} rewards")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating mining stats for node {node_id}: {e}")
            return False
    
    def cleanup_inactive_nodes(self, inactive_threshold_minutes: int = 60) -> int:
        """Mark nodes as inactive if they haven't been seen for a while"""
        try:
            query = """
                UPDATE nodes 
                SET status = 'inactive'
                WHERE status = 'active' 
                AND last_seen < CURRENT_TIMESTAMP - INTERVAL '%s minutes'
            """
            result = self.db.execute_query(query, (inactive_threshold_minutes,))
            
            # Get count of updated nodes
            count_query = """
                SELECT COUNT(*) as count FROM nodes 
                WHERE status = 'inactive' 
                AND last_seen < CURRENT_TIMESTAMP - INTERVAL '%s minutes'
            """
            count_result = self.db.execute_query(count_query, (inactive_threshold_minutes,), fetch_one=True)
            inactive_count = count_result['count'] if count_result else 0
            
            if inactive_count > 0:
                logger.info(f"✅ Marked {inactive_count} nodes as inactive")
            
            return inactive_count
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up inactive nodes: {e}")
            return 0
    
    def get_node_statistics(self) -> Dict[str, Any]:
        """Get comprehensive node statistics"""
        try:
            stats = {}
            
            # Basic counts
            total_query = "SELECT COUNT(*) as count FROM nodes"
            active_query = "SELECT COUNT(*) as count FROM nodes WHERE status = 'active'"
            inactive_query = "SELECT COUNT(*) as count FROM nodes WHERE status = 'inactive'"
            
            stats['total_nodes'] = self.db.execute_query(total_query, fetch_one=True)['count']
            stats['active_nodes'] = self.db.execute_query(active_query, fetch_one=True)['count']
            stats['inactive_nodes'] = self.db.execute_query(inactive_query, fetch_one=True)['count']
            
            # Mining statistics
            mining_query = """
                SELECT 
                    SUM(blocks_mined) as total_blocks_mined,
                    SUM(total_rewards) as total_rewards_distributed,
                    AVG(blocks_mined) as avg_blocks_per_node,
                    MAX(blocks_mined) as max_blocks_by_node
                FROM nodes
            """
            mining_stats = self.db.execute_query(mining_query, fetch_one=True)
            if mining_stats:
                stats.update(dict(mining_stats))
            
            # Top miners
            top_miners_query = """
                SELECT node_id, blocks_mined, total_rewards
                FROM nodes 
                WHERE blocks_mined > 0
                ORDER BY blocks_mined DESC 
                LIMIT 5
            """
            top_miners = self.db.execute_query(top_miners_query, fetch_all=True)
            stats['top_miners'] = [dict(row) for row in top_miners] if top_miners else []
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting node statistics: {e}")
            return {}