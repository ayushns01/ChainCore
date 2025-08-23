#!/usr/bin/env python3
"""
Thread-Safe Network and Peer Management
Enterprise-grade networking with connection pooling and rate limiting
"""

import threading
import time
import requests
import logging
import socket
from typing import Set, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from contextlib import contextmanager
import concurrent.futures
import queue

from .thread_safety import (
    LockManager, LockOrder, synchronized, AtomicCounter, 
    TransactionQueue, MemoryBarrier, lock_manager
)

logger = logging.getLogger(__name__)

@dataclass
class PeerInfo:
    """Thread-safe peer information"""
    url: str
    last_seen: float = 0.0
    failures: int = 0
    response_time: float = 0.0
    version: str = ""
    chain_length: int = 0
    is_active: bool = False
    connection_count: int = 0
    
class ConnectionPool:
    """
    Thread-safe HTTP connection pool
    Reduces connection overhead and implements rate limiting
    """
    
    def __init__(self, max_connections: int = 100, max_per_host: int = 10):
        self._pools: Dict[str, requests.Session] = {}
        self._pool_lock = threading.RLock()
        self._max_connections = max_connections
        self._max_per_host = max_per_host
        self._connection_counts: Dict[str, AtomicCounter] = defaultdict(AtomicCounter)
        self._rate_limiters: Dict[str, 'RateLimiter'] = {}
        
    def get_session(self, host: str) -> requests.Session:
        """Get or create session for host with connection pooling"""
        with self._pool_lock:
            if host not in self._pools:
                if len(self._pools) >= self._max_connections:
                    # Remove least used session
                    least_used = min(self._connection_counts.items(), key=lambda x: x[1].value)
                    del self._pools[least_used[0]]
                    del self._connection_counts[least_used[0]]
                
                session = requests.Session()
                # Configure session with enterprise settings
                adapter = requests.adapters.HTTPAdapter(
                    pool_connections=self._max_per_host,
                    pool_maxsize=self._max_per_host,
                    max_retries=3
                )
                session.mount('http://', adapter)
                session.mount('https://', adapter)
                
                self._pools[host] = session
                
                # Initialize rate limiter for this host
                self._rate_limiters[host] = RateLimiter(requests_per_second=10, burst_size=20)
            
            self._connection_counts[host].increment()
            return self._pools[host]
    
    def release_session(self, host: str):
        """Release session (decrement usage counter)"""
        if host in self._connection_counts:
            # Just track usage, actual cleanup happens in get_session
            pass
    
    @contextmanager
    def request(self, url: str, **kwargs):
        """Context manager for making requests with rate limiting"""
        import urllib.parse
        
        parsed = urllib.parse.urlparse(url)
        host = f"{parsed.scheme}://{parsed.netloc}"
        
        # Apply rate limiting
        if host in self._rate_limiters:
            if not self._rate_limiters[host].acquire():
                raise requests.exceptions.Timeout("Rate limit exceeded")
        
        session = self.get_session(host)
        
        try:
            yield session
        finally:
            self.release_session(host)

class RateLimiter:
    """Token bucket rate limiter for preventing network abuse"""
    
    def __init__(self, requests_per_second: float, burst_size: int):
        self._rate = requests_per_second
        self._burst = burst_size
        self._tokens = burst_size
        self._last_update = time.time()
        self._lock = threading.Lock()
    
    def acquire(self, timeout: Optional[float] = 5.0) -> bool:
        """Acquire rate limiting token"""
        start_time = time.time()
        
        while True:
            with self._lock:
                now = time.time()
                # Add tokens based on elapsed time
                elapsed = now - self._last_update
                self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
                self._last_update = now
                
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return True
            
            # Check timeout before waiting
            if timeout and (time.time() - start_time) > timeout:
                return False
            
            # Wait for next token, but not longer than remaining timeout
            wait_time = min(1.0 / self._rate, 0.1)  # Max 100ms wait
            if timeout:
                remaining_time = timeout - (time.time() - start_time)
                if remaining_time <= 0:
                    return False
                wait_time = min(wait_time, remaining_time)
            
            time.sleep(wait_time)

class ThreadSafePeerManager:
    """
    Enterprise-grade peer management with health monitoring
    """
    
    def __init__(self):
        self._peers: Dict[str, PeerInfo] = {}
        self._active_peers: Set[str] = set()
        
        # Separate locks for different operations to reduce contention
        self._peers_lock = lock_manager.get_lock("peer_registry", LockOrder.PEERS)
        self._active_lock = lock_manager.get_lock("active_peers", LockOrder.PEERS)
        
        # Connection pool for efficient networking
        self._connection_pool = ConnectionPool(max_connections=50)
        
        # Health monitoring
        self._health_monitor = threading.Timer(30.0, self._health_check)
        self._health_monitor.daemon = True
        self._health_monitor.start()
        
        # Peer discovery queue
        self._discovery_queue = queue.Queue(maxsize=1000)
        self._discovery_worker = threading.Thread(target=self._discovery_worker, daemon=True)
        self._discovery_worker.start()
        
        # Continuous peer discovery settings
        self._continuous_discovery_enabled = True
        self._last_peer_discovery = 0
        self._peer_discovery_interval = 60.0  # Try to discover peers every 60 seconds
        
        # Blockchain synchronization settings
        self._blockchain_sync_enabled = True
        self._last_blockchain_sync = 0
        self._blockchain_sync_interval = 30.0  # Check blockchain sync every 30 seconds
        
        # Mempool synchronization settings
        self._mempool_sync_enabled = True
        self._last_mempool_sync = 0
        self._mempool_sync_interval = 15.0  # Sync mempool every 15 seconds
        
        # Network statistics synchronization
        self._network_stats_sync_enabled = True
        self._last_network_stats_sync = 0
        self._network_stats_sync_interval = 60.0  # Sync network stats every 60 seconds
        
        # Peer count management and discovery configuration
        try:
            from ..config import MIN_PEERS, TARGET_PEERS, MAX_PEERS, PEER_DISCOVERY_RANGE
        except ImportError:
            # Fallback for direct script execution
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
            from src.config import MIN_PEERS, TARGET_PEERS, MAX_PEERS, PEER_DISCOVERY_RANGE
        self._min_peers = MIN_PEERS
        self._target_peers = TARGET_PEERS  
        self._max_peers = MAX_PEERS
        self._discovery_range = PEER_DISCOVERY_RANGE  # Fix for missing attribute
        
        # Self-awareness for peer discovery
        self._self_url = None  # Will be set by network node
        self._is_main_node = False  # Track if this is the main coordinator node
        
        # Enhanced discovery settings for robust peer finding
        self._discovery_timeout = 3.0  # Fast discovery timeout
        self._max_discovery_workers = 20  # More workers for faster scanning
        self._backoff_multiplier = 1.5  # Exponential backoff for failed peers
        self._max_backoff = 300.0  # Max 5 minutes backoff
        
        # Statistics
        self._stats = {
            'discovery_attempts': AtomicCounter(),
            'successful_connections': AtomicCounter(),
            'failed_connections': AtomicCounter(),
            'peer_timeouts': AtomicCounter(),
            'mempool_syncs': AtomicCounter(),
            'network_stats_syncs': AtomicCounter(),
            'orphaned_blocks_found': AtomicCounter()
        }
        
        # Network-wide statistics aggregation
        self._network_wide_stats = {
            'total_nodes': 0,
            'total_hash_rate': 0.0,
            'average_block_time': 0.0,
            'network_difficulty': 0,
            'last_aggregation': 0
        }
        self._network_stats_lock = threading.RLock()
        
        logger.info("[NET] ChainCore Peer Network Manager Initialized")
        logger.info(f"   [TARGET] Target Peers: {self._target_peers} (Min: {self._min_peers}, Max: {self._max_peers})")
        logger.info(f"   [SEARCH] Peer Discovery: Every {self._peer_discovery_interval}s")
        logger.info(f"   [SYNC] Blockchain Sync: Every {self._blockchain_sync_interval}s")
        logger.info(f"   [MEMPOOL] Mempool Sync: Every {self._mempool_sync_interval}s")
        logger.info(f"   [STATS] Network Stats: Every {self._network_stats_sync_interval}s")
        logger.info("[READY] Ready for peer connections!")
    
    @synchronized("peer_registry", LockOrder.PEERS, mode='write')
    def add_peer(self, peer_url: str, peer_info: Optional[PeerInfo] = None) -> bool:
        """Thread-safe peer addition"""
        if peer_url in self._peers:
            # Update existing peer
            if peer_info:
                self._peers[peer_url] = peer_info
            return True
        
        # Add new peer
        if not peer_info:
            peer_info = PeerInfo(url=peer_url, last_seen=time.time())
        
        self._peers[peer_url] = peer_info
        
        # Queue for health check
        try:
            self._discovery_queue.put(peer_url, timeout=1.0)
        except queue.Full:
            logger.warning("Discovery queue full, peer health check delayed")
        
        logger.info(f"[PEER] New Peer Added: {peer_url}")
        logger.info(f"   [STATS] Total Peers: {len(self._peers)}")
        logger.info(f"   [OK] Active Peers: {len(self._active_peers)}")
        
        # Show network status
        if len(self._active_peers) < self._min_peers:
            logger.info("   [WARN]  Network Status: Under-connected (seeking more peers)")
        elif len(self._active_peers) >= self._target_peers:
            logger.info("   [TARGET] Network Status: Well-connected")
        return True
    
    @synchronized("peer_registry", LockOrder.PEERS, mode='read')
    def get_peer_info(self, peer_url: str) -> Optional[PeerInfo]:
        """Get peer information thread-safely"""
        return self._peers.get(peer_url)
    
    @synchronized("active_peers", LockOrder.PEERS, mode='read')
    def get_active_peers(self) -> Set[str]:
        """Get set of active peers"""
        return self._active_peers.copy()
    
    @synchronized("peer_registry", LockOrder.PEERS, mode='read')
    def get_all_peers(self) -> Dict[str, PeerInfo]:
        """Get all registered peers"""
        return self._peers.copy()
    
    def _health_check(self):
        """Periodic health check for all peers and continuous discovery when isolated"""
        try:
            all_peers = self.get_all_peers()
            
            # Use thread pool for concurrent health checks
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = {
                    executor.submit(self._check_peer_health, url): url 
                    for url in all_peers.keys()
                }
                
                for future in concurrent.futures.as_completed(futures, timeout=30):
                    peer_url = futures[future]
                    try:
                        is_healthy = future.result()
                        self._update_peer_status(peer_url, is_healthy)
                    except Exception as e:
                        logger.error(f"Health check failed for {peer_url}: {e}")
                        self._update_peer_status(peer_url, False)
            
            # Check if we need to trigger peer discovery
            active_count = len(self.get_active_peers())
            self._check_and_trigger_peer_discovery(active_count)
            
            # Check if we need to trigger blockchain synchronization
            self._check_and_trigger_blockchain_sync(active_count)
            
            # Check if we need to trigger mempool synchronization
            self._check_and_trigger_mempool_sync(active_count)
            
            # Check if we need to trigger network stats synchronization
            self._check_and_trigger_network_stats_sync(active_count)
        
        except Exception as e:
            logger.error(f"Health check error: {e}")
        
        finally:
            # Schedule next health check
            self._health_monitor = threading.Timer(30.0, self._health_check)
            self._health_monitor.daemon = True
            self._health_monitor.start()
    
    def _check_and_trigger_peer_discovery(self, active_peer_count: int):
        """Trigger peer discovery based on network needs"""
        current_time = time.time()
        
        # Check if we should run peer discovery
        should_discover = (
            self._continuous_discovery_enabled and
            current_time - self._last_peer_discovery > self._peer_discovery_interval and
            self._should_discover_more_peers(active_peer_count)
        )
        
        if should_discover:
            discovery_reason = self._get_discovery_reason(active_peer_count)
            logger.info(f"Triggering peer discovery: {discovery_reason}")
            self._last_peer_discovery = current_time
            
            # Run discovery in background to avoid blocking health check
            discovery_thread = threading.Thread(
                target=self._background_peer_discovery,
                daemon=True
            )
            discovery_thread.start()
    
    def _should_discover_more_peers(self, active_peer_count: int) -> bool:
        """Determine if we should discover more peers"""
        total_known_peers = len(self._peers)
        
        # Always discover if we have fewer than minimum peers
        if active_peer_count < self._min_peers:
            return True
            
        # Discover if we're below target and don't know enough peers to reach max
        if active_peer_count < self._target_peers and total_known_peers < self._max_peers:
            return True
            
        # Always try to discover new peers periodically to find network changes
        return True  # Continuous discovery for network resilience
    
    def _get_discovery_reason(self, active_peer_count: int) -> str:
        """Get human-readable reason for peer discovery"""
        if active_peer_count == 0:
            return "node is isolated (0 active peers)"
        elif active_peer_count < self._min_peers:
            return f"below minimum peers ({active_peer_count}/{self._min_peers})"
        elif active_peer_count < self._target_peers:
            return f"below target peers ({active_peer_count}/{self._target_peers})"
        else:
            return f"periodic network scan ({active_peer_count} current peers)"
    
    def _background_peer_discovery(self):
        """Background peer discovery when node is isolated"""
        try:
            logger.info("[SEARCH] Starting Automated Peer Discovery...")
            logger.info(f"   [TARGET] Looking for peers in range {self._discovery_range}")
            
            discovered_count = self.discover_peers()
            
            if discovered_count > 0:
                logger.info(f"🎉 Peer Discovery Successful!")
                logger.info(f"   ➕ Found {discovered_count} new peer(s)")
                logger.info(f"   [STATS] Total Network: {len(self._active_peers)} active peers")
            else:
                logger.info("[SEARCH] Peer Discovery Complete - No new peers found")
                logger.info(f"   [STATS] Current Network: {len(self._active_peers)} active peers")
                
        except Exception as e:
            logger.error(f"Background peer discovery error: {e}")
    
    def _check_and_trigger_blockchain_sync(self, active_peer_count: int):
        """Trigger blockchain synchronization with peers when needed"""
        current_time = time.time()
        
        # Only sync if we have peers and sync is enabled
        if (active_peer_count > 0 and 
            self._blockchain_sync_enabled and
            current_time - self._last_blockchain_sync > self._blockchain_sync_interval):
            
            logger.info(f"[SYNC] Blockchain Synchronization Check Started")
            logger.info(f"   [NET] Active Peers: {active_peer_count}")
            logger.info("   [SEARCH] Checking for longer chains...")
            self._last_blockchain_sync = current_time
            
            # Run sync check in background
            sync_thread = threading.Thread(
                target=self._background_blockchain_sync,
                daemon=True
            )
            sync_thread.start()
    
    def _background_blockchain_sync(self):
        """Background blockchain synchronization check"""
        try:
            logger.debug("Starting background blockchain sync check...")
            
            # Get current blockchain length from our node
            current_length = self._get_local_blockchain_length()
            if current_length is None:
                logger.debug("Could not get local blockchain length, skipping sync")
                return
            
            # Check peers for longer chains
            best_peer, best_length = self._find_peer_with_longer_chain(current_length)
            
            if best_peer and best_length > current_length:
                logger.info(f"Found longer chain at {best_peer}: {best_length} vs our {current_length}")
                self._perform_blockchain_sync(best_peer, current_length, best_length)
            else:
                logger.debug(f"Blockchain sync check complete: our chain ({current_length}) is up to date")
                
        except Exception as e:
            logger.error(f"Background blockchain sync error: {e}")
    
    def _get_local_blockchain_length(self) -> Optional[int]:
        """Get blockchain length from our local node"""
        try:
            # This will need to be set by the network node
            if hasattr(self, '_blockchain_ref') and self._blockchain_ref:
                return self._blockchain_ref.get_chain_length()
            else:
                logger.debug("No blockchain reference available")
                return None
        except Exception as e:
            logger.error(f"Error getting local blockchain length: {e}")
            return None
    
    def _find_peer_with_longer_chain(self, current_length: int) -> Tuple[Optional[str], int]:
        """Find peer with the longest chain that's longer than ours"""
        active_peers = self.get_active_peers()
        best_peer = None
        best_length = current_length
        
        for peer_url in active_peers:
            try:
                response = requests.get(f"{peer_url}/status", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    peer_length = data.get('blockchain_length', 0)
                    
                    if peer_length > best_length:
                        best_peer = peer_url
                        best_length = peer_length
                        
            except Exception as e:
                logger.debug(f"Could not check chain length for {peer_url}: {e}")
        
        return best_peer, best_length
    
    def _perform_blockchain_sync(self, peer_url: str, current_length: int, peer_length: int):
        """Perform actual blockchain synchronization with a peer"""
        try:
            logger.info(f"Syncing blockchain with {peer_url} ({current_length} -> {peer_length})")
            
            # This will trigger the network node to perform the sync
            if hasattr(self, '_sync_callback') and self._sync_callback:
                self._sync_callback(peer_url, current_length, peer_length)
            else:
                logger.debug("No sync callback available - manual sync required")
                
        except Exception as e:
            logger.error(f"Error performing blockchain sync: {e}")
    
    def set_blockchain_reference(self, blockchain_ref):
        """Set reference to local blockchain for length checks"""
        self._blockchain_ref = blockchain_ref
        logger.debug("Blockchain reference set for automatic sync")
    
    def set_sync_callback(self, sync_callback):
        """Set callback function for performing blockchain sync"""
        self._sync_callback = sync_callback
        logger.debug("Sync callback set for automatic sync")
    
    def configure_blockchain_sync(self, enabled: bool = True, interval: float = 30.0):
        """Configure automatic blockchain synchronization"""
        self._blockchain_sync_enabled = enabled
        self._blockchain_sync_interval = interval
        logger.info(f"[SYNC] Blockchain Sync Configuration Updated:")
        logger.info(f"   Status: {'[OK] Enabled' if enabled else '[DISABLED] Disabled'}")
        logger.info(f"   Interval: {interval} seconds")
    
    def _check_and_trigger_mempool_sync(self, active_peer_count: int):
        """Trigger mempool synchronization with peers when needed"""
        current_time = time.time()
        
        # Only sync if we have peers and sync is enabled
        if (active_peer_count > 0 and 
            self._mempool_sync_enabled and
            current_time - self._last_mempool_sync > self._mempool_sync_interval):
            
            logger.info(f"[MEMPOOL] Mempool Synchronization Started")
            logger.info(f"   [NET] Syncing with {active_peer_count} peer(s)")
            logger.info("   [SEARCH] Checking for new transactions...")
            self._last_mempool_sync = current_time
            
            # Run mempool sync in background
            sync_thread = threading.Thread(
                target=self._background_mempool_sync,
                daemon=True
            )
            sync_thread.start()
    
    def _background_mempool_sync(self):
        """Background mempool synchronization with peers"""
        try:
            active_peers = self.get_active_peers()
            if not active_peers:
                return
            
            # Get local mempool if blockchain reference is set
            local_mempool = set()
            if hasattr(self, '_blockchain_ref') and self._blockchain_ref:
                local_pool = self._blockchain_ref.get_transaction_pool_copy()
                local_mempool = {tx.tx_id for tx in local_pool}
            
            # Sync with each peer
            for peer_url in list(active_peers)[:3]:  # Limit to 3 peers for efficiency
                try:
                    self._sync_mempool_with_peer(peer_url, local_mempool)
                except Exception as e:
                    logger.error(f"Mempool sync error with {peer_url}: {e}")
            
            self._stats['mempool_syncs'].increment()
            logger.info(f"[OK] Mempool Synchronization Complete")
            logger.info(f"   [NET] Synced with {len(active_peers)} peer(s)")
            logger.info(f"   [STATS] Sync Count: {self._stats['mempool_syncs'].value}")
            
        except Exception as e:
            logger.error(f"Background mempool sync error: {e}")
    
    def _sync_mempool_with_peer(self, peer_url: str, local_mempool: set):
        """Sync mempool with a specific peer"""
        try:
            # Get peer's transaction pool
            response = requests.get(f"{peer_url}/transaction_pool", timeout=5)
            if response.status_code != 200:
                return
            
            peer_data = response.json()
            peer_transactions = peer_data.get('transactions', [])
            
            # Find transactions we don't have
            new_transactions = []
            for tx_data in peer_transactions:
                tx_id = tx_data.get('tx_id')
                if tx_id and tx_id not in local_mempool:
                    new_transactions.append(tx_data)
            
            # Add new transactions to our local pool via callback
            if new_transactions and hasattr(self, '_mempool_callback') and self._mempool_callback:
                for tx_data in new_transactions:
                    try:
                        self._mempool_callback(tx_data, peer_url)
                    except Exception as e:
                        logger.error(f"Error adding transaction from {peer_url}: {e}")
                        
                logger.info(f"➕ Added {len(new_transactions)} new transaction(s) from {peer_url}")
                for tx in new_transactions[:3]:  # Show first 3
                    logger.info(f"   [MEMPOOL] Transaction: {tx.get('tx_id', 'Unknown')[:16]}...")
            
        except Exception as e:
            logger.error(f"Error syncing mempool with {peer_url}: {e}")
    
    def _check_and_trigger_network_stats_sync(self, active_peer_count: int):
        """Trigger network statistics synchronization when needed"""
        current_time = time.time()
        
        # Only sync if we have peers and sync is enabled
        if (active_peer_count > 0 and 
            self._network_stats_sync_enabled and
            current_time - self._last_network_stats_sync > self._network_stats_sync_interval):
            
            logger.info(f"[STATS] Network Statistics Synchronization Started")
            logger.info(f"   [NET] Collecting stats from {active_peer_count} peer(s)")
            logger.info("   📈 Aggregating network performance data...")
            self._last_network_stats_sync = current_time
            
            # Run network stats sync in background
            sync_thread = threading.Thread(
                target=self._background_network_stats_sync,
                daemon=True
            )
            sync_thread.start()
    
    def _background_network_stats_sync(self):
        """Background network statistics aggregation"""
        try:
            active_peers = self.get_active_peers()
            if not active_peers:
                return
            
            # Collect stats from all peers
            network_stats = {
                'total_nodes': 1,  # Include ourselves
                'total_hash_rate': 0.0,
                'block_times': [],
                'difficulties': [],
                'peer_counts': [],
                'chain_lengths': []
            }
            
            # Add our own stats if blockchain reference is available
            if hasattr(self, '_blockchain_ref') and self._blockchain_ref:
                chain_length = self._blockchain_ref.get_chain_length()
                network_stats['chain_lengths'].append(chain_length)
            
            # Collect from peers
            for peer_url in active_peers:
                try:
                    self._collect_peer_stats(peer_url, network_stats)
                except Exception as e:
                    logger.error(f"Error collecting stats from {peer_url}: {e}")
            
            # Update aggregated network stats
            self._update_network_wide_stats(network_stats)
            self._stats['network_stats_syncs'].increment()
            
            logger.info(f"[OK] Network Statistics Synchronization Complete")
            logger.info(f"   [NET] Collected from {len(active_peers)} peer(s)")
            logger.info(f"   [STATS] Total Network Nodes: {network_stats['total_nodes']}")
            logger.info(f"   📈 Chain Lengths: {min(network_stats['chain_lengths'])} - {max(network_stats['chain_lengths'])}" if network_stats['chain_lengths'] else "   📈 No chain data")
            logger.info(f"   [SYNC] Sync Count: {self._stats['network_stats_syncs'].value}")
            
        except Exception as e:
            logger.error(f"Background network stats sync error: {e}")
    
    def _collect_peer_stats(self, peer_url: str, network_stats: dict):
        """Collect statistics from a specific peer"""
        try:
            # Get general status
            response = requests.get(f"{peer_url}/status", timeout=5)
            if response.status_code == 200:
                status_data = response.json()
                network_stats['total_nodes'] += 1
                network_stats['chain_lengths'].append(status_data.get('blockchain_length', 0))
                network_stats['peer_counts'].append(status_data.get('peers', 0))
            
            # Get detailed stats if available
            try:
                stats_response = requests.get(f"{peer_url}/stats", timeout=5)
                if stats_response.status_code == 200:
                    stats_data = stats_response.json()
                    # Extract relevant stats for network aggregation
                    node_stats = stats_data.get('node_stats', {})
                    blockchain_stats = stats_data.get('blockchain_stats', {})
                    
                    # Note: Hash rate would need to be reported by mining clients
                    # This is a placeholder for future mining stats integration
                    
            except Exception:
                pass  # Stats endpoint might not exist on all peers
                
        except Exception as e:
            logger.error(f"Error collecting stats from {peer_url}: {e}")
    
    def _update_network_wide_stats(self, collected_stats: dict):
        """Update the aggregated network-wide statistics"""
        with self._network_stats_lock:
            self._network_wide_stats.update({
                'total_nodes': collected_stats['total_nodes'],
                'max_chain_length': max(collected_stats['chain_lengths']) if collected_stats['chain_lengths'] else 0,
                'min_chain_length': min(collected_stats['chain_lengths']) if collected_stats['chain_lengths'] else 0,
                'avg_peers_per_node': sum(collected_stats['peer_counts']) / len(collected_stats['peer_counts']) if collected_stats['peer_counts'] else 0,
                'last_aggregation': time.time()
            })
    
    def configure_mempool_sync(self, enabled: bool = True, interval: float = 15.0):
        """Configure automatic mempool synchronization"""
        self._mempool_sync_enabled = enabled
        self._mempool_sync_interval = interval
        logger.info(f"[MEMPOOL] Mempool Sync Configuration Updated:")
        logger.info(f"   Status: {'[OK] Enabled' if enabled else '[DISABLED] Disabled'}")
        logger.info(f"   Interval: {interval} seconds")
    
    def configure_network_stats_sync(self, enabled: bool = True, interval: float = 60.0):
        """Configure automatic network statistics synchronization"""
        self._network_stats_sync_enabled = enabled
        self._network_stats_sync_interval = interval
        logger.info(f"[STATS] Network Stats Sync Configuration Updated:")
        logger.info(f"   Status: {'[OK] Enabled' if enabled else '[DISABLED] Disabled'}")
        logger.info(f"   Interval: {interval} seconds")
    
    def set_mempool_callback(self, callback):
        """Set callback function for adding synced transactions to local mempool"""
        self._mempool_callback = callback
        logger.debug("Mempool callback set for automatic sync")
    
    def get_network_wide_stats(self) -> dict:
        """Get aggregated network-wide statistics"""
        with self._network_stats_lock:
            return self._network_wide_stats.copy()
    
    def _check_peer_health(self, peer_url: str) -> bool:
        """Check individual peer health with adaptive timeouts"""
        try:
            # Get peer info to determine appropriate timeout
            timeout = self._get_adaptive_timeout(peer_url)
            
            with self._connection_pool.request(f"{peer_url}/status") as session:
                start_time = time.time()
                response = session.get(f"{peer_url}/status", timeout=timeout)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    # Update peer info with response data
                    try:
                        peer_data = response.json()
                        with self._peers_lock.write_lock():
                            if peer_url in self._peers:
                                peer_info = self._peers[peer_url]
                                peer_info.last_seen = time.time()
                                peer_info.response_time = response_time
                                peer_info.chain_length = peer_data.get('blockchain_length', 0)
                                peer_info.failures = 0
                        
                        self._stats['successful_connections'].increment()
                        return True
                    except Exception as e:
                        logger.warning(f"Failed to parse peer response from {peer_url}: {e}")
                        return False
                else:
                    logger.warning(f"Peer {peer_url} returned status {response.status_code}")
                    return False
                    
        except requests.exceptions.Timeout:
            logger.warning(f"Peer {peer_url} timed out")
            self._stats['peer_timeouts'].increment()
            return False
        except requests.exceptions.RequestException as e:
            logger.warning(f"Peer {peer_url} connection failed: {e}")
            self._stats['failed_connections'].increment()
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking peer {peer_url}: {e}")
            return False
    
    def _update_peer_status(self, peer_url: str, is_healthy: bool):
        """Update peer active status with atomic operations and exponential backoff"""
        # Use consistent lock ordering: peers_lock then active_lock
        with self._peers_lock.write_lock():
            if peer_url not in self._peers:
                return
                
            peer_info = self._peers[peer_url]
            
            if is_healthy:
                # Peer is healthy - reset failure count and mark active
                peer_info.is_active = True
                peer_info.failures = 0
                peer_info.last_seen = time.time()
                
                # Add to active peers atomically
                with self._active_lock.write_lock():
                    self._active_peers.add(peer_url)
                    
                logger.debug(f"[OK] Peer {peer_url} marked as healthy")
                
            else:
                # Peer is unhealthy - increment failures and apply backoff
                peer_info.failures += 1
                current_time = time.time()
                
                # Calculate exponential backoff delay
                backoff_delay = min(
                    self._max_backoff,
                    (self._backoff_multiplier ** peer_info.failures) * 10.0
                )
                
                # Remove from active peers after 3 failures
                if peer_info.failures >= 3:
                    peer_info.is_active = False
                    
                    with self._active_lock.write_lock():
                        self._active_peers.discard(peer_url)
                    
                    logger.info(f"[DISABLED] Peer {peer_url} marked as inactive (failures: {peer_info.failures})")
                else:
                    logger.debug(f"[WARN]  Peer {peer_url} health check failed (failures: {peer_info.failures}, backoff: {backoff_delay:.1f}s)")
    
    def _discovery_worker(self):
        """Background worker for peer discovery"""
        while True:
            try:
                peer_url = self._discovery_queue.get(timeout=60)
                if peer_url:
                    self._stats['discovery_attempts'].increment()
                    is_healthy = self._check_peer_health(peer_url)
                    self._update_peer_status(peer_url, is_healthy)
                    self._discovery_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Discovery worker error: {e}")
    
    def discover_peers(self, port_range: range = None, host: str = "localhost") -> int:
        """
        ENHANCED: Scalable peer discovery for large multi-node networks (N > 2)
        Returns number of new peers discovered
        """
        # Use configured port range if none provided (now supports 200+ nodes)
        if port_range is None:
            port_range = range(*self._discovery_range)
        
        discovered_count = 0
        current_active_peers = len(self.get_active_peers())
        discovered_nodes = []  # Track discovered nodes for main node selection
        
        # ENHANCED: Batch discovery for large networks to prevent overwhelming
        from ..config import PEER_DISCOVERY_BATCH_SIZE, PEER_DISCOVERY_PARALLEL_WORKERS
        batch_size = PEER_DISCOVERY_BATCH_SIZE
        max_workers = min(PEER_DISCOVERY_PARALLEL_WORKERS, len(port_range))
        
        logger.info(f"[SEARCH] Starting Scalable Multi-Node Peer Discovery")
        logger.info(f"   [STATS] Current: {current_active_peers} active peers")
        logger.info(f"   [TARGET] Scanning: ports {port_range.start}-{port_range.stop-1} ({len(port_range)} total)")
        logger.info(f"   📦 Batch size: {batch_size} ports per batch")
        logger.info(f"   ⚡ Workers: {max_workers}")
        
        # Process discovery in batches for better performance with large networks
        port_list = list(port_range)
        for batch_start in range(0, len(port_list), batch_size):
            batch_ports = port_list[batch_start:batch_start + batch_size]
            
            logger.debug(f"[SEARCH] Processing batch: ports {batch_ports[0]}-{batch_ports[-1]}")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit discovery tasks for this batch
                future_to_url = {}
                
                for port in batch_ports:
                    peer_url = f"http://{host}:{port}"
                    
                    # Skip self URL
                    if self._is_self_url(peer_url):
                        logger.debug(f"   ⏭️  Skipping self URL: {peer_url}")
                        continue
                    
                    future = executor.submit(self._try_discover_peer_enhanced, peer_url)
                    future_to_url[future] = peer_url
            
                # Process completed futures with timeout handling
                completed_futures = 0
                timeout_duration = 10.0  # 10 second timeout per batch
                
                try:
                    for future in concurrent.futures.as_completed(future_to_url.keys(), timeout=timeout_duration):
                        completed_futures += 1
                        peer_url = future_to_url[future]
                        
                        try:
                            peer_info = future.result()
                            if peer_info:
                                discovered_count += 1
                                discovered_nodes.append((peer_url, peer_info))
                                logger.info(f"   [OK] Found peer: {peer_url} (chain: {peer_info.chain_length})")
                                
                                # Early exit if we have enough peers
                                if len(self._peers) >= self._max_peers:
                                    logger.info(f"   [TARGET] Reached max peers ({self._max_peers}), stopping discovery")
                                    return discovered_count  # Exit completely
                                    
                        except Exception as e:
                            logger.debug(f"   [DISABLED] Discovery failed for {peer_url}: {e}")
                            self._stats['failed_connections'].increment()
                
                except concurrent.futures.TimeoutError:
                    logger.debug(f"   ⏰ Batch timeout after {timeout_duration}s")
                
                # Cancel any remaining futures to prevent resource leaks
                for future in future_to_url.keys():
                    if not future.done():
                        future.cancel()
            
            # Small delay between batches to prevent overwhelming the network
            if batch_start + batch_size < len(port_list):
                time.sleep(0.1)
            remaining_futures = [f for f in future_to_url.keys() if not f.done()]
            if remaining_futures:
                logger.debug(f"   [SYNC] Cancelling {len(remaining_futures)} unfinished futures")
                for future in remaining_futures:
                    future.cancel()
        
        # Determine main node based on discovery results
        self._determine_main_node(discovered_nodes)
        
        final_active_peers = len(self.get_active_peers())
        logger.info(f"🎉 Peer Discovery Complete!")
        logger.info(f"   📈 Discovered: {discovered_count} new peers")
        logger.info(f"   [STATS] Active peers: {current_active_peers} → {final_active_peers}")
        logger.info(f"   🏆 Main node: {'Yes' if self._is_main_node else 'No'}")
        
        return discovered_count
    
    def _try_discover_peer_enhanced(self, peer_url: str) -> Optional[PeerInfo]:
        """Enhanced peer discovery with better error handling and info gathering"""
        try:
            # Use adaptive timeout for discovery too
            timeout = self._get_adaptive_timeout(peer_url)
            
            with self._connection_pool.request(f"{peer_url}/status") as session:
                response = session.get(f"{peer_url}/status", timeout=timeout)
                
                if response.status_code == 200:
                    peer_data = response.json()
                    
                    # Create comprehensive peer info
                    peer_info = PeerInfo(
                        url=peer_url,
                        last_seen=time.time(),
                        chain_length=peer_data.get('blockchain_length', 0),
                        version=peer_data.get('version', ''),
                        is_active=True,
                        failures=0,
                        response_time=response.elapsed.total_seconds() if response.elapsed else 0.0
                    )
                    
                    # Add peer to our registry
                    self.add_peer(peer_url, peer_info)
                    
                    # Mark as active
                    with self._active_lock.write_lock():
                        self._active_peers.add(peer_url)
                    
                    self._stats['successful_connections'].increment()
                    return peer_info
                    
        except requests.exceptions.Timeout:
            logger.debug(f"Timeout discovering {peer_url}")
            self._stats['peer_timeouts'].increment()
        except requests.exceptions.ConnectionError:
            logger.debug(f"Connection refused by {peer_url}")
            self._stats['failed_connections'].increment()
        except Exception as e:
            logger.debug(f"Discovery error for {peer_url}: {e}")
            self._stats['failed_connections'].increment()
        
        return None
    
    def _determine_main_node(self, discovered_nodes: List[Tuple[str, PeerInfo]]):
        """Determine if this node should be the main coordinator node"""
        # FIXED: Only bootstrap node (port 5000) or nodes with no bootstrap should be main
        current_port = self._extract_port(self._self_url) if self._self_url else 0
        
        # Bootstrap node (port 5000) is always main if it exists
        if current_port == 5000:
            self._is_main_node = True
            logger.info("🏆 This node is the MAIN NODE (bootstrap node: port 5000)")
            return
        
        # Check if bootstrap node exists in discovered nodes
        bootstrap_exists = any(self._extract_port(node[0]) == 5000 for node in discovered_nodes)
        
        if bootstrap_exists:
            # Bootstrap exists, we are peer
            self._is_main_node = False
            logger.info("👥 This node is a PEER NODE (bootstrap node exists at port 5000)")
        elif not discovered_nodes:
            # No other nodes and we're not bootstrap - we become main
            self._is_main_node = True
            logger.info("🏆 This node is the MAIN NODE (no other nodes found)")
        else:
            # Use lowest port logic as fallback
            all_nodes = [(self._self_url, self._get_self_info())] + discovered_nodes
            all_nodes = [node for node in all_nodes if node[0]]  # Filter out None URLs
            
            if all_nodes:
                main_node_url = min(all_nodes, key=lambda x: self._extract_port(x[0]))[0]
                self._is_main_node = (main_node_url == self._self_url)
                
                if self._is_main_node:
                    logger.info(f"🏆 This node is the MAIN NODE (lowest port: {self._extract_port(self._self_url)})")
                else:
                    main_port = self._extract_port(main_node_url)
                    logger.info(f"👥 This node is a PEER NODE (main node: port {main_port})")
    
    def _extract_port(self, url: str) -> int:
        """Extract port number from URL"""
        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(url)
            return parsed.port or 80
        except:
            return 999999  # High number for invalid URLs
    
    def _get_self_info(self) -> PeerInfo:
        """Get info about this node"""
        return PeerInfo(
            url=self._self_url or "",
            last_seen=time.time(),
            chain_length=0,  # Will be updated by blockchain reference
            is_active=True,
            failures=0
        )
    
    def _is_self_url(self, peer_url: str) -> bool:
        """Check if a URL points to this node itself"""
        # Check against self URL if configured
        if self._self_url and peer_url == self._self_url:
            return True
        
        # Extract port and check if it matches our port
        if self._self_url:
            try:
                self_port = self._extract_port(self._self_url)
                peer_port = self._extract_port(peer_url)
                if self_port == peer_port:
                    return True
            except:
                pass
            
        return False
    
    def set_self_url(self, self_url: str):
        """Set this node's URL for self-awareness in peer discovery"""
        self._self_url = self_url
        logger.info(f"🆔 Node self-URL set: {self_url}")
        
        # Trigger immediate peer discovery to find existing nodes
        if self._continuous_discovery_enabled:
            discovery_thread = threading.Thread(
                target=self._immediate_peer_discovery,
                daemon=True,
                name=f"PeerDiscovery-{self._extract_port(self_url)}"
            )
            discovery_thread.start()
    
    def _immediate_peer_discovery(self):
        """Immediate peer discovery when node starts with enhanced coordination"""
        try:
            # Enhanced thundering herd prevention with exponential backoff
            import random
            import time
            
            # Base delay with jitter to spread out discovery attempts
            base_delay = random.uniform(3.0, 10.0)  # 3-10 second base delay
            
            # Additional delay based on port number to further spread nodes
            if hasattr(self, '_self_url') and self._self_url:
                try:
                    port = self._extract_port(self._self_url)
                    port_offset = (port % 20) * 0.5  # 0-10 second additional delay based on port
                    total_delay = base_delay + port_offset
                except:
                    total_delay = base_delay
            else:
                total_delay = base_delay
            
            logger.info(f"[READY] Starting peer discovery in {total_delay:.1f} seconds (thundering herd prevention)...")
            time.sleep(total_delay)
            
            # Retry logic with exponential backoff
            max_retries = 3
            retry_delay = 5.0
            
            for attempt in range(max_retries):
                try:
                    logger.info(f"[SEARCH] Peer discovery attempt {attempt + 1}/{max_retries}...")
                    discovered = self.discover_peers()
                    
                    if discovered > 0:
                        logger.info(f"🎉 Successfully connected to {discovered} existing nodes")
                        return  # Success, exit retry loop
                    else:
                        logger.info("📡 No existing nodes found")
                        if attempt < max_retries - 1:
                            logger.info(f"   ⏳ Retrying in {retry_delay:.1f} seconds...")
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                        else:
                            logger.info("   [FIRST] This appears to be the first node in the network")
                    
                except Exception as e:
                    logger.error(f"Discovery attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        logger.info(f"   ⏳ Retrying in {retry_delay:.1f} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        logger.error("   [DISABLED] All discovery attempts failed")
                        raise
                
        except Exception as e:
            logger.error(f"Error in immediate peer discovery: {e}")
    
    def _extract_port(self, url: str) -> int:
        """Extract port number from URL"""
        try:
            import re
            match = re.search(r':(\d+)', url)
            return int(match.group(1)) if match else 5000
        except:
            return 5000
    
    def _get_adaptive_timeout(self, peer_url: str) -> float:
        """Get adaptive timeout based on peer history and network conditions"""
        base_timeout = 8.0  # Increased from 5.0 to be more forgiving
        
        with self._peers_lock.read_lock():
            if peer_url in self._peers:
                peer_info = self._peers[peer_url]
                
                # Adjust based on historical response time
                if hasattr(peer_info, 'response_time') and peer_info.response_time:
                    # Use 3x the average response time, with min/max bounds
                    adaptive_timeout = max(base_timeout, peer_info.response_time * 3.0)
                    adaptive_timeout = min(adaptive_timeout, 20.0)  # Cap at 20 seconds
                    return adaptive_timeout
                
                # Increase timeout for peers with previous failures
                if hasattr(peer_info, 'failures') and peer_info.failures > 0:
                    failure_multiplier = 1.0 + (peer_info.failures * 0.5)  # +50% per failure
                    return min(base_timeout * failure_multiplier, 15.0)  # Cap at 15 seconds
        
        return base_timeout
    
    def get_main_node_status(self) -> bool:
        """Check if this node is the main coordinator node"""
        return self._is_main_node
    
    def _try_discover_peer(self, peer_url: str) -> bool:
        """Try to discover a single peer"""
        try:
            with self._connection_pool.request(f"{peer_url}/status") as session:
                response = session.get(f"{peer_url}/status", timeout=3)
                
                if response.status_code == 200:
                    peer_data = response.json()
                    peer_info = PeerInfo(
                        url=peer_url,
                        last_seen=time.time(),
                        chain_length=peer_data.get('blockchain_length', 0),
                        is_active=True
                    )
                    
                    self.add_peer(peer_url, peer_info)
                    
                    with self._active_lock.write_lock():
                        self._active_peers.add(peer_url)
                    
                    return True
                    
        except Exception:
            pass  # Silent failure for discovery
        
        return False
    
    def broadcast_to_peers(self, endpoint: str, data: dict, timeout: float = 10.0, 
                          exclude_sender: bool = False, sender_url: str = None) -> Dict[str, bool]:
        """
        Enhanced thread-safe broadcasting to all active peers for multi-node networks
        Returns dict of peer_url -> success_status
        """
        active_peers = self.get_active_peers()
        
        # Exclude sender to prevent broadcast loops in multi-node networks
        if exclude_sender and sender_url:
            active_peers = [peer for peer in active_peers if peer != sender_url]
        
        results = {}
        
        if not active_peers:
            logger.warning("No active peers for broadcasting")
            return results
        
        # ENHANCED: Scale worker count based on network size
        max_workers = min(len(active_peers), 20)  # Scale up to 20 workers for large networks
        
        logger.info(f"[NET] Broadcasting to {len(active_peers)} peers with {max_workers} workers")
        
        # Use thread pool for concurrent broadcasting
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._broadcast_to_peer, peer_url, endpoint, data, timeout): peer_url
                for peer_url in active_peers
            }
            
            for future in concurrent.futures.as_completed(futures, timeout=timeout + 5):
                peer_url = futures[future]
                try:
                    success = future.result()
                    results[peer_url] = success
                    
                    if not success:
                        # Mark peer as potentially unhealthy
                        self._update_peer_status(peer_url, False)
                
                except Exception as e:
                    logger.error(f"Broadcast to {peer_url} failed: {e}")
                    results[peer_url] = False
        
        success_count = sum(results.values())
        logger.info(f"Broadcast complete: {success_count}/{len(active_peers)} peers successful")
        
        return results
    
    def configure_continuous_discovery(self, enabled: bool = True, interval: float = 30.0):
        """Configure continuous peer discovery when node is isolated"""
        self._continuous_discovery_enabled = enabled
        self._peer_discovery_interval = interval
        logger.info(f"Continuous peer discovery: {'enabled' if enabled else 'disabled'}, interval: {interval}s")
    
    def _broadcast_to_peer(self, peer_url: str, endpoint: str, data: dict, timeout: float) -> bool:
        """Broadcast to single peer"""
        try:
            with self._connection_pool.request(f"{peer_url}{endpoint}") as session:
                response = session.post(
                    f"{peer_url}{endpoint}",
                    json=data,
                    headers={'Content-Type': 'application/json'},
                    timeout=timeout
                )
                
                if response.status_code == 200:
                    return True
                else:
                    logger.warning(f"Peer {peer_url} returned {response.status_code} for {endpoint}")
                    return False
                    
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout broadcasting to {peer_url}")
            return False
        except Exception as e:
            logger.error(f"Error broadcasting to {peer_url}: {e}")
            return False
    
    def sync_with_best_peer(self) -> Optional[Tuple[str, List]]:
        """
        Thread-safe synchronization with the peer having the longest chain
        Returns (peer_url, blockchain_data) or None if no suitable peer found
        """
        active_peers = self.get_active_peers()
        
        if not active_peers:
            logger.warning("No active peers for synchronization")
            return None
        
        best_peer = None
        max_chain_length = 0
        
        # Find peer with longest chain
        for peer_url in active_peers:
            try:
                with self._connection_pool.request(f"{peer_url}/status") as session:
                    response = session.get(f"{peer_url}/status", timeout=5)
                    
                    if response.status_code == 200:
                        peer_data = response.json()
                        chain_length = peer_data.get('blockchain_length', 0)
                        
                        if chain_length > max_chain_length:
                            max_chain_length = chain_length
                            best_peer = peer_url
            
            except Exception as e:
                logger.warning(f"Failed to get chain length from {peer_url}: {e}")
        
        if not best_peer:
            logger.warning("No suitable peer found for synchronization")
            return None
        
        # Download blockchain from best peer
        try:
            with self._connection_pool.request(f"{best_peer}/blockchain") as session:
                response = session.get(f"{best_peer}/blockchain", timeout=60)
                
                if response.status_code == 200:
                    blockchain_data = response.json()
                    logger.info(f"Synchronized with {best_peer}: {len(blockchain_data.get('chain', []))} blocks")
                    return best_peer, blockchain_data.get('chain', [])
                else:
                    logger.error(f"Failed to sync with {best_peer}: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Sync error with {best_peer}: {e}")
            return None
    
    def get_stats(self) -> Dict[str, int]:
        """Get networking statistics"""
        return {
            'total_peers': len(self._peers),
            'active_peers': len(self._active_peers),
            'discovery_attempts': self._stats['discovery_attempts'].value,
            'successful_connections': self._stats['successful_connections'].value,
            'failed_connections': self._stats['failed_connections'].value,
            'peer_timeouts': self._stats['peer_timeouts'].value,
            'network_status': self._get_network_status()
        }
    
    def _get_network_status(self) -> str:
        """Get current network connectivity status"""
        active_count = len(self._active_peers)
        
        if active_count == 0:
            return "isolated"
        elif active_count < self._min_peers:
            return "under-connected"
        elif active_count < self._target_peers:
            return "establishing"
        elif active_count >= self._target_peers:
            return "well-connected"
        else:
            return "optimal"
    
    def get_detailed_peer_info(self) -> Dict:
        """Get detailed information about all peers"""
        active_peers = self.get_active_peers()
        
        peer_details = []
        for peer_url, peer_info in self._peers.items():
            peer_details.append({
                'url': peer_url,
                'is_active': peer_url in active_peers,
                'failures': peer_info.failures,
                'last_seen': peer_info.last_seen,
                'connection_time': peer_info.connection_time
            })
        
        return {
            'total_known_peers': len(self._peers),
            'active_peers': len(active_peers),
            'network_status': self._get_network_status(),
            'peer_details': peer_details,
            'discovery_enabled': self._continuous_discovery_enabled,
            'next_discovery_in': max(0, self._peer_discovery_interval - (time.time() - self._last_peer_discovery))
        }
    
    def cleanup(self):
        """Enhanced cleanup of peer manager resources"""
        try:
            # Stop health monitoring
            if hasattr(self, '_health_monitor') and self._health_monitor:
                self._health_monitor.cancel()
                logger.debug("Health monitor stopped")
            
            # Clear all peer data
            with self._peers_lock.write_lock():
                self._peers.clear()
                
            with self._active_lock.write_lock():
                self._active_peers.clear()
                
            # Close connection pool sessions
            try:
                with self._connection_pool._pool_lock:
                    for session in self._connection_pool._pools.values():
                        session.close()
                    self._connection_pool._pools.clear()
                    logger.debug("Connection pool cleaned up")
            except:
                pass  # Ignore cleanup errors
                
            logger.info("🧹 Peer manager cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during peer manager cleanup: {e}")
            pass
        
        logger.info("Peer manager cleanup complete")

# Global peer manager instance
peer_manager = ThreadSafePeerManager()