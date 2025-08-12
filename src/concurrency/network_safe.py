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
            self._rate_limiters[host].acquire()
        
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
            
            if timeout and (time.time() - start_time) > timeout:
                return False
            
            # Wait for next token
            time.sleep(1.0 / self._rate)

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
        
        # Statistics
        self._stats = {
            'discovery_attempts': AtomicCounter(),
            'successful_connections': AtomicCounter(),
            'failed_connections': AtomicCounter(),
            'peer_timeouts': AtomicCounter()
        }
        
        logger.info("Thread-safe peer manager initialized")
    
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
        
        logger.info(f"Peer added: {peer_url}")
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
        """Periodic health check for all peers"""
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
        
        except Exception as e:
            logger.error(f"Health check error: {e}")
        
        finally:
            # Schedule next health check
            self._health_monitor = threading.Timer(30.0, self._health_check)
            self._health_monitor.daemon = True
            self._health_monitor.start()
    
    def _check_peer_health(self, peer_url: str) -> bool:
        """Check individual peer health"""
        try:
            with self._connection_pool.request(f"{peer_url}/status") as session:
                start_time = time.time()
                response = session.get(f"{peer_url}/status", timeout=5)
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
        """Update peer active status"""
        with self._peers_lock.write_lock():
            if peer_url in self._peers:
                peer_info = self._peers[peer_url]
                
                if is_healthy:
                    peer_info.is_active = True
                    peer_info.failures = 0
                    
                    with self._active_lock.write_lock():
                        self._active_peers.add(peer_url)
                else:
                    peer_info.failures += 1
                    
                    # Remove from active peers after 3 failures
                    if peer_info.failures >= 3:
                        peer_info.is_active = False
                        with self._active_lock.write_lock():
                            self._active_peers.discard(peer_url)
    
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
    
    def discover_peers(self, port_range: range = range(5000, 5012), host: str = "localhost") -> int:
        """
        Thread-safe peer discovery with rate limiting
        Returns number of new peers discovered
        """
        discovered_count = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            
            for port in port_range:
                peer_url = f"http://{host}:{port}"
                
                # Skip self
                if peer_url in self._peers:
                    continue
                
                future = executor.submit(self._try_discover_peer, peer_url)
                futures.append(future)
            
            for future in concurrent.futures.as_completed(futures, timeout=30):
                try:
                    if future.result():
                        discovered_count += 1
                except Exception as e:
                    logger.debug(f"Peer discovery error: {e}")
        
        logger.info(f"Peer discovery complete: {discovered_count} new peers")
        return discovered_count
    
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
    
    def broadcast_to_peers(self, endpoint: str, data: dict, timeout: float = 10.0) -> Dict[str, bool]:
        """
        Thread-safe broadcasting to all active peers
        Returns dict of peer_url -> success_status
        """
        active_peers = self.get_active_peers()
        results = {}
        
        if not active_peers:
            logger.warning("No active peers for broadcasting")
            return results
        
        # Use thread pool for concurrent broadcasting
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
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
            'peer_timeouts': self._stats['peer_timeouts'].value
        }
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            if hasattr(self, '_health_monitor'):
                self._health_monitor.cancel()
        except:
            pass
        
        logger.info("Peer manager cleanup complete")

# Global peer manager instance
peer_manager = ThreadSafePeerManager()