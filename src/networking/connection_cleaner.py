#!/usr/bin/env python3
"""
Connection and Memory Management for Local Networks
Prevents memory leaks during long multi-terminal testing
"""

import time
import threading
import logging
from typing import Dict, Set, List
from collections import deque

logger = logging.getLogger(__name__)

class ConnectionCleaner:
    """Manages connection cleanup and memory usage for long-running tests"""
    
    def __init__(self):
        self._cleanup_thread = None
        self._running = False
        self._cleanup_interval = 60.0  # Clean every minute
        self._max_inactive_peers = 20
        self._max_connection_age = 300.0  # 5 minutes
        self._stats = {
            'cleanups_performed': 0,
            'peers_removed': 0,
            'connections_closed': 0
        }
        
    def start_cleanup(self):
        """Start the background cleanup thread"""
        if self._running:
            return
            
        self._running = True
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="ConnectionCleaner"
        )
        self._cleanup_thread.start()
        logger.info("Connection cleaner started")
    
    def stop_cleanup(self):
        """Stop the background cleanup"""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
        logger.info("Connection cleaner stopped")
    
    def _cleanup_loop(self):
        """Background cleanup loop"""
        while self._running:
            try:
                self._perform_cleanup()
                time.sleep(self._cleanup_interval)
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                time.sleep(10)  # Wait before retrying
    
    def _perform_cleanup(self):
        """Perform cleanup operations"""
        current_time = time.time()
        self._stats['cleanups_performed'] += 1
        
        # Get peer manager instances for cleanup
        from src.networking import get_peer_manager
        from src.concurrency import peer_manager as legacy_peer_manager
        
        enhanced_manager = get_peer_manager()
        
        if enhanced_manager:
            self._cleanup_enhanced_peer_manager(enhanced_manager, current_time)
        
        if legacy_peer_manager:
            self._cleanup_legacy_peer_manager(legacy_peer_manager, current_time)
        
        logger.debug(f"Cleanup completed: {self._stats}")
    
    def _cleanup_enhanced_peer_manager(self, manager, current_time: float):
        """Clean up enhanced peer manager"""
        with manager._lock:
            peers_to_remove = []
            
            # Find inactive peers
            for url, peer_info in manager._peers.items():
                age = current_time - peer_info.last_seen
                
                # Remove very old inactive peers
                if not peer_info.is_active and age > self._max_connection_age:
                    peers_to_remove.append(url)
                
                # Remove peers with too many failures
                elif peer_info.failures > 10 and peer_info.peer_score < 10:
                    peers_to_remove.append(url)
            
            # Limit total inactive peers
            inactive_peers = [url for url, peer in manager._peers.items() 
                            if not peer.is_active]
            
            if len(inactive_peers) > self._max_inactive_peers:
                # Remove oldest inactive peers
                inactive_by_age = sorted(inactive_peers, 
                                       key=lambda url: manager._peers[url].last_seen)
                excess_count = len(inactive_peers) - self._max_inactive_peers
                peers_to_remove.extend(inactive_by_age[:excess_count])
            
            # Remove selected peers
            for url in set(peers_to_remove):  # Remove duplicates
                if url in manager._peers:
                    del manager._peers[url]
                    manager._active_peers.discard(url)
                    manager._connection_manager.remove_connection(url)
                    self._stats['peers_removed'] += 1
            
            if peers_to_remove:
                logger.info(f"Cleaned up {len(peers_to_remove)} inactive peers")
    
    def _cleanup_legacy_peer_manager(self, manager, current_time: float):
        """Clean up legacy peer manager"""
        try:
            # Get all peers
            all_peers = manager.get_all_peers()
            active_peers = manager.get_active_peers()
            
            peers_to_remove = []
            
            for url, peer_info in all_peers.items():
                if url not in active_peers:
                    age = current_time - peer_info.last_seen
                    if age > self._max_connection_age:
                        peers_to_remove.append(url)
            
            # Remove old inactive peers (if manager supports it)
            if hasattr(manager, 'remove_peer'):
                for url in peers_to_remove:
                    manager.remove_peer(url)
                    self._stats['peers_removed'] += 1
                
                if peers_to_remove:
                    logger.info(f"Cleaned up {len(peers_to_remove)} legacy peers")
                    
        except Exception as e:
            logger.debug(f"Legacy peer cleanup error: {e}")
    
    def force_cleanup(self):
        """Force immediate cleanup"""
        logger.info("Forcing immediate cleanup")
        self._perform_cleanup()
    
    def get_cleanup_stats(self) -> Dict:
        """Get cleanup statistics"""
        return self._stats.copy()
    
    def reset_stats(self):
        """Reset cleanup statistics"""
        self._stats = {
            'cleanups_performed': 0,
            'peers_removed': 0,
            'connections_closed': 0
        }

# Global connection cleaner instance
connection_cleaner = ConnectionCleaner()

def start_connection_cleanup():
    """Start the global connection cleaner"""
    connection_cleaner.start_cleanup()

def stop_connection_cleanup():
    """Stop the global connection cleaner"""
    connection_cleaner.stop_cleanup()

def get_connection_cleaner() -> ConnectionCleaner:
    """Get the global connection cleaner instance"""
    return connection_cleaner