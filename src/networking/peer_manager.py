#!/usr/bin/env python3
"""
Enhanced Peer-to-Peer Network Manager
Implements full-mesh blockchain networking with gossiping, persistent storage, and active connections
"""

import json
import os
import time
import threading
import requests
import logging
import socket
import random
from typing import Set, Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from contextlib import contextmanager
import concurrent.futures
import queue
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class PeerInfo:
    """Enhanced peer information with quality metrics"""
    url: str
    node_id: str = ""
    last_seen: float = 0.0
    first_seen: float = 0.0
    failures: int = 0
    successes: int = 0
    response_time: float = 0.0
    version: str = ""
    chain_length: int = 0
    is_active: bool = False
    connection_count: int = 0
    peer_score: float = 0.0
    services: List[str] = field(default_factory=list)
    user_agent: str = ""
    protocol_version: str = "1.0"
    height: int = 0
    
    def __post_init__(self):
        if self.first_seen == 0.0:
            self.first_seen = time.time()
        self.update_score()
    
    def update_score(self):
        """Calculate peer quality score (0-100)"""
        if self.successes + self.failures == 0:
            self.peer_score = 50.0  # Neutral for new peers
            return
            
        success_rate = self.successes / (self.successes + self.failures)
        age_factor = min(1.0, (time.time() - self.first_seen) / 86400)  # Up to 1 day
        response_factor = max(0.1, 1.0 - (self.response_time / 5.0))  # 5s max good response
        
        self.peer_score = (success_rate * 60 + age_factor * 20 + response_factor * 20)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PeerInfo':
        """Create from dictionary"""
        return cls(**data)

class PeerStorage:
    """Persistent peer storage manager"""
    
    def __init__(self, storage_path: str = "peers.json"):
        self.storage_path = storage_path
        self._lock = threading.RLock()
    
    def save_peers(self, peers: Dict[str, PeerInfo]) -> bool:
        """Save peers to persistent storage"""
        try:
            with self._lock:
                peer_data = {url: peer.to_dict() for url, peer in peers.items()}
                with open(self.storage_path, 'w') as f:
                    json.dump({
                        'version': '1.0',
                        'last_updated': time.time(),
                        'peers': peer_data
                    }, f, indent=2)
                logger.debug(f"Saved {len(peers)} peers to {self.storage_path}")
                return True
        except Exception as e:
            logger.error(f"Failed to save peers: {e}")
            return False
    
    def load_peers(self) -> Dict[str, PeerInfo]:
        """Load peers from persistent storage"""
        try:
            with self._lock:
                if not os.path.exists(self.storage_path):
                    return {}
                
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                
                peers = {}
                for url, peer_data in data.get('peers', {}).items():
                    try:
                        peers[url] = PeerInfo.from_dict(peer_data)
                    except Exception as e:
                        logger.warning(f"Failed to load peer {url}: {e}")
                
                logger.info(f"Loaded {len(peers)} peers from {self.storage_path}")
                return peers
        except Exception as e:
            logger.error(f"Failed to load peers: {e}")
            return {}

class OutboundConnectionManager:
    """Manages active outbound connections to peers"""
    
    def __init__(self, target_connections: int = 8, max_connections: int = 12):
        self.target_connections = target_connections
        self.max_connections = max_connections
        self._connections: Dict[str, requests.Session] = {}
        self._connection_health: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._health_check_thread = None
        self._running = False
    
    def start_connection_management(self):
        """Start the connection health monitoring thread"""
        if self._running:
            return
        
        self._running = True
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True,
            name="ConnectionHealthMonitor"
        )
        self._health_check_thread.start()
        logger.info(f"Started outbound connection manager (target: {self.target_connections})")
    
    def stop_connection_management(self):
        """Stop the connection management"""
        self._running = False
        if self._health_check_thread:
            self._health_check_thread.join(timeout=5)
    
    def add_connection(self, peer_url: str) -> bool:
        """Add an outbound connection to a peer"""
        with self._lock:
            if len(self._connections) >= self.max_connections:
                # Remove lowest quality connection
                worst_peer = min(self._connection_health.items(), key=lambda x: x[1])
                self.remove_connection(worst_peer[0])
            
            if peer_url not in self._connections:
                session = requests.Session()
                session.headers.update({
                    'User-Agent': 'ChainCore/1.0',
                    'Connection': 'keep-alive'
                })
                
                self._connections[peer_url] = session
                self._connection_health[peer_url] = 1.0
                logger.debug(f"Added outbound connection to {peer_url}")
                return True
            return False
    
    def remove_connection(self, peer_url: str):
        """Remove an outbound connection"""
        with self._lock:
            if peer_url in self._connections:
                self._connections[peer_url].close()
                del self._connections[peer_url]
                del self._connection_health[peer_url]
                logger.debug(f"Removed outbound connection to {peer_url}")
    
    def get_connection(self, peer_url: str) -> Optional[requests.Session]:
        """Get an existing connection or None"""
        with self._lock:
            return self._connections.get(peer_url)
    
    def get_active_connections(self) -> List[str]:
        """Get list of active outbound connections"""
        with self._lock:
            return list(self._connections.keys())
    
    def _health_check_loop(self):
        """Background health checking for outbound connections"""
        while self._running:
            try:
                with self._lock:
                    connections_to_check = list(self._connections.keys())
                
                for peer_url in connections_to_check:
                    try:
                        response = requests.get(
                            f"{peer_url}/status",
                            timeout=5,
                            headers={'User-Agent': 'ChainCore/1.0'}
                        )
                        if response.status_code == 200:
                            with self._lock:
                                self._connection_health[peer_url] = min(1.0, 
                                    self._connection_health.get(peer_url, 0.5) + 0.1)
                        else:
                            with self._lock:
                                self._connection_health[peer_url] = max(0.0,
                                    self._connection_health.get(peer_url, 0.5) - 0.2)
                    except Exception:
                        with self._lock:
                            self._connection_health[peer_url] = max(0.0,
                                self._connection_health.get(peer_url, 0.5) - 0.3)
                
                # Remove unhealthy connections
                with self._lock:
                    unhealthy_peers = [url for url, health in self._connection_health.items() 
                                     if health < 0.1]
                    for peer_url in unhealthy_peers:
                        self.remove_connection(peer_url)
                
                time.sleep(30)  # Health check every 30 seconds
                
            except Exception as e:
                logger.error(f"Connection health check error: {e}")
                time.sleep(10)

class PeerNetworkManager:
    """Enhanced P2P network manager with gossiping and full-mesh connectivity"""
    
    def __init__(self, node_id: str, api_port: int, bootstrap_nodes: List[str] = None):
        self.node_id = node_id
        self.api_port = api_port
        self.bootstrap_nodes = bootstrap_nodes or []
        
        # Peer storage and management
        self._peers: Dict[str, PeerInfo] = {}
        self._active_peers: Set[str] = set()
        self._storage = PeerStorage(f"peers_{node_id}.json")
        self._connection_manager = OutboundConnectionManager()
        
        # Synchronization
        self._lock = threading.RLock()
        self._discovery_thread = None
        self._gossip_thread = None
        self._running = False
        
        # Configuration
        self.max_peers = 200
        self.target_outbound_connections = 8
        self.discovery_interval = 30
        self.gossip_interval = 60
        self.peer_exchange_batch_size = 50
        
        # Load persisted peers
        self._load_persisted_peers()
    
    def start(self):
        """Start the peer management system"""
        if self._running:
            return
        
        self._running = True
        self._connection_manager.start_connection_management()
        
        # Start discovery thread
        self._discovery_thread = threading.Thread(
            target=self._discovery_loop,
            daemon=True,
            name=f"PeerDiscovery-{self.node_id}"
        )
        self._discovery_thread.start()
        
        # Start gossip thread
        self._gossip_thread = threading.Thread(
            target=self._gossip_loop,
            daemon=True,
            name=f"PeerGossip-{self.node_id}"
        )
        self._gossip_thread.start()
        
        logger.info(f"Enhanced peer manager started for node {self.node_id}")
        
        # Bootstrap with initial nodes
        if self.bootstrap_nodes:
            self._bootstrap_network()
    
    def stop(self):
        """Stop the peer management system"""
        self._running = False
        self._connection_manager.stop_connection_management()
        
        if self._discovery_thread:
            self._discovery_thread.join(timeout=5)
        if self._gossip_thread:
            self._gossip_thread.join(timeout=5)
        
        self._save_peers()
        logger.info(f"Peer manager stopped for node {self.node_id}")
    
    def _load_persisted_peers(self):
        """Load peers from persistent storage"""
        persisted_peers = self._storage.load_peers()
        with self._lock:
            self._peers.update(persisted_peers)
            # Mark persisted peers as inactive initially
            for peer in self._peers.values():
                peer.is_active = False
        logger.info(f"Loaded {len(persisted_peers)} persisted peers")
    
    def _save_peers(self):
        """Save current peers to persistent storage"""
        with self._lock:
            self._storage.save_peers(self._peers)
    
    def _bootstrap_network(self):
        """Bootstrap with initial seed nodes with retry logic"""
        logger.info(f"Bootstrapping network with {len(self.bootstrap_nodes)} seed nodes")

        for seed_url in self.bootstrap_nodes:
            max_attempts = 3
            for attempt in range(max_attempts):
                logger.info(f"Attempting to connect to bootstrap node {seed_url} (attempt {attempt + 1}/{max_attempts})")
                try:
                    if self.add_peer(seed_url):
                        logger.info(f"Successfully connected to bootstrap node {seed_url}")
                        # Request peers from seed node
                        self._request_peers_from_node(seed_url)
                        break  # Success, move to next seed node
                except Exception as e:
                    logger.warning(f"Error bootstrapping with {seed_url} on attempt {attempt + 1}: {e}")

                if attempt < max_attempts - 1:
                    time.sleep(3) # Wait 3 seconds before retrying
            else:
                logger.error(f"Failed to connect to bootstrap node {seed_url} after {max_attempts} attempts.")
    
    def add_peer(self, peer_url: str, peer_info: Optional[PeerInfo] = None) -> bool:
        """Add a peer to the network and return True if successful"""
        if peer_url == f"http://localhost:{self.api_port}":
            return False  # Don't add ourselves
        
        with self._lock:
            if peer_url not in self._peers:
                if peer_info is None:
                    peer_info = PeerInfo(url=peer_url, first_seen=time.time())
                
                self._peers[peer_url] = peer_info
                logger.info(f"[PEER] Added new peer: {peer_url}")
            
            # Health check the peer
            health_check_ok = self._health_check_peer(peer_url)

            if health_check_ok:
                # Maintain outbound connections
                if len(self._connection_manager.get_active_connections()) < self.target_outbound_connections:
                    self._connection_manager.add_connection(peer_url)
            
            return health_check_ok
    
    def _health_check_peer(self, peer_url: str):
        """Perform health check on a peer"""
        try:
            start_time = time.time()
            response = requests.get(
                f"{peer_url}/status",
                timeout=5,
                headers={'User-Agent': f'ChainCore-{self.node_id}/1.0'}
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                status_data = response.json()
                
                # Reset failure count on successful health check
                with self._lock:
                    if peer_url in self._peers:
                        self._peers[peer_url].is_active = True
                        self._peers[peer_url].last_seen = time.time()
                        self._peers[peer_url].failure_count = 0  # Reset failures
                        self._peers[peer_url].response_time = response_time
                
                with self._lock:
                    if peer_url in self._peers:
                        peer = self._peers[peer_url]
                        peer.last_seen = time.time()
                        peer.response_time = response_time
                        peer.successes += 1
                        peer.is_active = True
                        peer.version = status_data.get('version', '')
                        peer.chain_length = status_data.get('blockchain_length', 0)
                        peer.node_id = status_data.get('node_id', '')
                        peer.update_score()
                        
                        self._active_peers.add(peer_url)
                        
                logger.debug(f"Peer {peer_url} health check: OK (score: {peer.peer_score:.1f})")
                return True
            else:
                self._mark_peer_failure(peer_url)
                return False
                
        except Exception as e:
            self._mark_peer_failure(peer_url)
            logger.debug(f"Peer {peer_url} health check failed: {e}")
            return False
    
    def _mark_peer_failure(self, peer_url: str):
        """Mark a peer as having failed a health check"""
        with self._lock:
            if peer_url in self._peers:
                peer = self._peers[peer_url]
                peer.failures += 1
                peer.update_score()
                
                if peer.failures >= 5:
                    peer.is_active = False
                    self._active_peers.discard(peer_url)
                    self._connection_manager.remove_connection(peer_url)
                    logger.debug(f"Peer {peer_url} marked as inactive (failures: {peer.failures})")
    
    def _discovery_loop(self):
        """Background peer discovery loop"""
        while self._running:
            try:
                self._discover_new_peers()
                self._maintain_peer_connections()
                time.sleep(self.discovery_interval)
            except Exception as e:
                logger.error(f"Discovery loop error: {e}")
                time.sleep(10)
    
    def _discover_new_peers(self):
        """Discover new peers through various methods"""
        # Method 1: Port scanning (limited range for local testing)
        self._discover_by_port_scan()
        
        # Method 2: Peer exchange with active peers
        self._discover_through_peer_exchange()
    
    def _discover_by_port_scan(self):
        """Discover peers by scanning common ports"""
        port_range = range(5000, 5020)  # Limited for local testing
        active_found = 0
        reconnected = 0
        
        for port in port_range:
            if not self._running:
                break
            
            peer_url = f"http://localhost:{port}"
            if port != self.api_port:
                try:
                    response = requests.get(f"{peer_url}/status", timeout=2)
                    if response.status_code == 200:
                        if peer_url not in self._peers:
                            self.add_peer(peer_url)
                            active_found += 1
                        else:
                            # Reconnect to previously known but inactive peers
                            with self._lock:
                                if peer_url in self._peers and not self._peers[peer_url].is_active:
                                    self._peers[peer_url].is_active = True
                                    self._peers[peer_url].last_seen = time.time()
                                    self._peers[peer_url].failure_count = 0
                                    if peer_url not in self._active_peers:
                                        self._active_peers.add(peer_url)
                                    reconnected += 1
                except:
                    # Mark failed peers as inactive instead of removing them
                    with self._lock:
                        if peer_url in self._peers:
                            peer = self._peers[peer_url]
                            peer.failure_count = peer.failure_count + 1 if hasattr(peer, 'failure_count') else 1
                            if peer.failure_count >= 3:  # After 3 failures, mark inactive
                                peer.is_active = False
                                self._active_peers.discard(peer_url)
        
        if active_found > 0 or reconnected > 0:
            logger.info(f"[SEARCH] Port scan: {active_found} new peers, {reconnected} reconnected")
    
    def _discover_through_peer_exchange(self):
        """Discover peers by asking active peers for their peer lists"""
        with self._lock:
            active_peers = list(self._active_peers)
        
        new_peers_found = 0
        for peer_url in active_peers[:5]:  # Ask up to 5 peers
            try:
                new_peers_found += self._request_peers_from_node(peer_url)
            except Exception as e:
                logger.debug(f"Peer exchange with {peer_url} failed: {e}")
        
        if new_peers_found > 0:
            logger.info(f"[SEARCH] Peer exchange discovered {new_peers_found} new peers")
    
    def _request_peers_from_node(self, peer_url: str) -> int:
        """Request peer list from a specific node"""
        try:
            response = requests.get(
                f"{peer_url}/getpeers",
                timeout=5,
                headers={'User-Agent': f'ChainCore-{self.node_id}/1.0'}
            )
            
            if response.status_code == 200:
                peer_data = response.json()
                peers = peer_data.get('peers', [])
                
                new_peers_added = 0
                for peer_info_dict in peers:
                    peer_url_new = peer_info_dict.get('url')
                    if peer_url_new and peer_url_new not in self._peers:
                        try:
                            peer_info = PeerInfo.from_dict(peer_info_dict)
                            if self.add_peer(peer_url_new, peer_info):
                                new_peers_added += 1
                        except Exception as e:
                            logger.debug(f"Failed to add peer {peer_url_new}: {e}")
                
                return new_peers_added
        except Exception as e:
            logger.debug(f"Failed to request peers from {peer_url}: {e}")
        
        return 0
    
    def _maintain_peer_connections(self):
        """Maintain optimal number of outbound connections"""
        active_connections = self._connection_manager.get_active_connections()
        
        if len(active_connections) < self.target_outbound_connections:
            # Need more connections
            with self._lock:
                # Get best peers not currently connected
                available_peers = []
                for url, peer in self._peers.items():
                    if peer.is_active and url not in active_connections:
                        available_peers.append((url, peer.peer_score))
                
                # Sort by score and connect to best peers
                available_peers.sort(key=lambda x: x[1], reverse=True)
                
                needed = self.target_outbound_connections - len(active_connections)
                for peer_url, score in available_peers[:needed]:
                    self._connection_manager.add_connection(peer_url)
                    logger.debug(f"Added outbound connection to {peer_url} (score: {score:.1f})")
    
    def _gossip_loop(self):
        """Background peer gossiping loop"""
        while self._running:
            try:
                self._gossip_peers()
                time.sleep(self.gossip_interval)
            except Exception as e:
                logger.error(f"Gossip loop error: {e}")
                time.sleep(10)
    
    def _gossip_peers(self):
        """Share our peer list with active peers"""
        with self._lock:
            active_peers = list(self._active_peers)
            our_peers = list(self._peers.values())
        
        if not active_peers or not our_peers:
            return
        
        # Select best peers to share (by score)
        best_peers = sorted(our_peers, key=lambda p: p.peer_score, reverse=True)
        peers_to_share = best_peers[:self.peer_exchange_batch_size]
        
        # Share with random active peers
        targets = random.sample(active_peers, min(3, len(active_peers)))
        
        for target_url in targets:
            try:
                self._share_peers_with_node(target_url, peers_to_share)
            except Exception as e:
                logger.debug(f"Failed to gossip with {target_url}: {e}")
    
    def _share_peers_with_node(self, target_url: str, peers_to_share: List[PeerInfo]):
        """Share peer list with a specific node"""
        try:
            peer_data = [peer.to_dict() for peer in peers_to_share]
            
            response = requests.post(
                f"{target_url}/sharepeers",
                json={
                    'node_id': self.node_id,
                    'peers': peer_data,
                    'timestamp': time.time()
                },
                timeout=10,
                headers={'User-Agent': f'ChainCore-{self.node_id}/1.0'}
            )
            
            if response.status_code == 200:
                logger.debug(f"Shared {len(peers_to_share)} peers with {target_url}")
            
        except Exception as e:
            logger.debug(f"Failed to share peers with {target_url}: {e}")
    
    def handle_peer_share(self, sender_node_id: str, shared_peers: List[Dict]) -> Dict:
        """Handle incoming peer sharing from other nodes"""
        new_peers_added = 0
        
        try:
            for peer_dict in shared_peers:
                peer_url = peer_dict.get('url')
                if peer_url and peer_url not in self._peers:
                    try:
                        peer_info = PeerInfo.from_dict(peer_dict)
                        if self.add_peer(peer_url, peer_info):
                            new_peers_added += 1
                    except Exception as e:
                        logger.debug(f"Failed to process shared peer {peer_url}: {e}")
            
            logger.info(f"Received {len(shared_peers)} peers from {sender_node_id}, added {new_peers_added}")
            
            # Save peers periodically
            if new_peers_added > 0:
                self._save_peers()
            
            return {
                'status': 'success',
                'peers_received': len(shared_peers),
                'new_peers_added': new_peers_added
            }
            
        except Exception as e:
            logger.error(f"Error handling peer share from {sender_node_id}: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_peers_for_sharing(self) -> List[Dict]:
        """Get peer list formatted for sharing"""
        with self._lock:
            # Share our best peers
            peers = sorted(self._peers.values(), key=lambda p: p.peer_score, reverse=True)
            return [peer.to_dict() for peer in peers[:self.peer_exchange_batch_size]]

    def get_active_peers(self) -> Set[str]:
        """Get set of active peers for backward compatibility"""
        with self._lock:
            return self._active_peers.copy()
    
    def get_peer_blockchain_info(self, peer_url: str, timeout: int = 10) -> Optional[Dict]:
        """Get blockchain information from a specific peer"""
        try:
            # Get connection for the peer
            connection = self.get_connection(peer_url)
            if not connection:
                logger.warning(f"No connection available for peer: {peer_url}")
                return None
            
            # Request blockchain data from peer
            response = connection.get(f"{peer_url}/api/blockchain", timeout=timeout)
            
            if response.status_code == 200:
                blockchain_data = response.json()
                
                # Update peer info with current chain length
                with self._lock:
                    if peer_url in self._peers:
                        if 'chain' in blockchain_data:
                            self._peers[peer_url].chain_length = len(blockchain_data['chain'])
                        self._peers[peer_url].last_seen = time.time()
                        self._peers[peer_url].successes += 1
                
                logger.info(f"Retrieved blockchain info from {peer_url}: {len(blockchain_data.get('chain', []))} blocks")
                return blockchain_data
            else:
                logger.warning(f"Failed to get blockchain info from {peer_url}: HTTP {response.status_code}")
                with self._lock:
                    if peer_url in self._peers:
                        self._peers[peer_url].failures += 1
                return None
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout getting blockchain info from {peer_url}")
            with self._lock:
                if peer_url in self._peers:
                    self._peers[peer_url].failures += 1
            return None
        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection error getting blockchain info from {peer_url}")
            with self._lock:
                if peer_url in self._peers:
                    self._peers[peer_url].failures += 1
            return None
        except Exception as e:
            logger.error(f"Error getting blockchain info from {peer_url}: {e}")
            with self._lock:
                if peer_url in self._peers:
                    self._peers[peer_url].failures += 1
            return None

    def get_status(self) -> Dict:
        """Get peer manager status"""
        with self._lock:
            return {
                'total_peers': len(self._peers),
                'active_peers': len(self._active_peers),
                'outbound_connections': len(self._connection_manager.get_active_connections()),
                'target_connections': self.target_outbound_connections,
                'peer_list': [
                    {
                        'url': url,
                        'active': peer.is_active,
                        'score': peer.peer_score,
                        'failures': peer.failures,
                        'chain_length': peer.chain_length
                    }
                    for url, peer in self._peers.items()
                ]
            }
    
    def broadcast_to_peers(self, endpoint: str, data: Dict, timeout: int = 5) -> Dict:
        """Broadcast data to all active peers"""
        results = {}
        
        with self._lock:
            active_peers = list(self._active_peers)
        
        def send_to_peer(peer_url: str):
            try:
                response = requests.post(
                    f"{peer_url}/{endpoint}",
                    json=data,
                    timeout=timeout,
                    headers={'User-Agent': f'ChainCore-{self.node_id}/1.0'}
                )
                return peer_url, response.status_code == 200
            except Exception as e:
                logger.debug(f"Broadcast to {peer_url} failed: {e}")
                return peer_url, False
        
        # Use thread pool for parallel broadcasting
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(send_to_peer, peer_url) for peer_url in active_peers]
            
            for future in concurrent.futures.as_completed(futures):
                peer_url, success = future.result()
                results[peer_url] = success
        
        successful = sum(1 for success in results.values() if success)
        logger.info(f"Broadcast to {successful}/{len(active_peers)} peers successful")
        
        return {
            'total_peers': len(active_peers),
            'successful': successful,
            'results': results
        }

# Global instance (will be initialized by network node)
peer_manager: Optional[PeerNetworkManager] = None

def initialize_peer_manager(node_id: str, api_port: int, bootstrap_nodes: List[str] = None):
    """Initialize the global peer manager"""
    global peer_manager
    peer_manager = PeerNetworkManager(node_id, api_port, bootstrap_nodes)
    return peer_manager

def get_peer_manager() -> Optional[PeerNetworkManager]:
    """Get the global peer manager instance"""
    return peer_manager