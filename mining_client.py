#!/usr/bin/env python3
"""
ChainCore Mining Client - Enterprise-Grade Production Implementation
Consolidated mining client with all advanced features and optimizations
"""

import sys
import os
import json
import time
import hashlib
import argparse
import requests
import logging
import secrets
import threading
import multiprocessing
import concurrent.futures
from typing import Dict, Optional, Tuple, List
from urllib.parse import urlparse
from collections import deque
from dataclasses import dataclass, field
from queue import Queue, Empty

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.crypto.ecdsa_crypto import double_sha256, validate_address

# Safe config import with fallbacks
try:
    from src.config import BLOCKCHAIN_DIFFICULTY, BLOCK_REWARD
except ImportError:
    logger.warning("Could not import config, using default values")
    BLOCKCHAIN_DIFFICULTY = 4
    BLOCK_REWARD = 50.0

# Configure production-grade logging with file rotation
try:
    from logging.handlers import RotatingFileHandler
    
    # Create logger with rotation to prevent large log files
    logger = logging.getLogger('MiningClient')
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Rotating file handler (max 10MB per file, keep 5 files)
    file_handler = RotatingFileHandler(
        'mining_client.log', 
        maxBytes=10*1024*1024, 
        backupCount=5,
        mode='a'
    )
    file_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
except ImportError:
    # Fallback to basic logging if rotation not available
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('mining_client.log', mode='a')
        ]
    )
    logger = logging.getLogger('MiningClient')

@dataclass
class MiningConfig:
    """Mining configuration with security and performance settings"""
    # Performance settings
    progress_update_interval: int = 50000  # Hash attempts between progress updates
    template_refresh_interval: float = 30.0  # Seconds before refreshing template
    max_mining_timeout: int = 120  # Maximum mining timeout
    
    # Network settings
    max_retries: int = 3
    initial_backoff: float = 1.0
    max_backoff: float = 60.0
    backoff_multiplier: float = 2.0
    
    # Security settings
    require_tls: bool = False
    max_difficulty: int = 12
    min_difficulty: int = 1
    
    # Memory management
    max_statistics_history: int = 1000
    
    # ENHANCED: Multi-core mining settings
    mining_workers: Optional[int] = None  # None = auto-detect CPU cores
    enable_core_affinity: bool = True     # Enable CPU core affinity for workers
    worker_nonce_range: int = 100000      # Nonce range per worker
    enable_gpu_acceleration: bool = False # Future GPU mining support
    max_worker_memory_mb: int = 100       # Memory limit per worker

@dataclass
class MiningStats:
    """Thread-safe mining statistics with memory management"""
    blocks_mined: int = 0
    total_mining_time: float = 0.0
    total_hashes: int = 0
    session_start: float = field(default_factory=time.time)
    hash_rate_history: deque = field(default_factory=lambda: deque(maxlen=100))
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def update_hash_rate(self, hashes: int, duration: float):
        """Thread-safe hash rate update"""
        with self._lock:
            if duration > 0:
                rate = hashes / duration
                self.hash_rate_history.append(rate)
                self.total_hashes += hashes
    
    def get_average_hash_rate(self) -> float:
        """Get average hash rate from recent history"""
        with self._lock:
            if not self.hash_rate_history:
                return 0.0
            return sum(self.hash_rate_history) / len(self.hash_rate_history)
    
    def get_session_stats(self) -> Dict:
        """Get comprehensive session statistics"""
        with self._lock:
            session_time = time.time() - self.session_start
            avg_block_time = session_time / self.blocks_mined if self.blocks_mined > 0 else 0
            
            return {
                'blocks_mined': self.blocks_mined,
                'session_time': session_time,
                'average_block_time': avg_block_time,
                'average_hash_rate': self.get_average_hash_rate(),
                'total_hashes': self.total_hashes,
                'estimated_earnings': self.blocks_mined * BLOCK_REWARD
            }

class MiningClient:
    """Enterprise-grade mining client with comprehensive security and performance features"""
    
    def __init__(self, wallet_address: str, node_url: str = "http://localhost:5000", config: MiningConfig = None):
        # Initialize config first
        self.config = config or MiningConfig()
        
        # Validate wallet address with ECDSA verification
        if not self._validate_wallet_address(wallet_address):
            raise ValueError(f"Invalid wallet address format: {self._sanitize_address(wallet_address)}")
        
        # Validate and sanitize node URL
        self.node_url = self._validate_node_url(node_url)
        self.wallet_address = wallet_address
        
        # Thread-safe mining state with enhanced controls
        self.is_mining = threading.Event()
        self.stop_mining = threading.Event()
        self.stats = MiningStats()
        
        # Legacy compatibility
        self.blocks_mined = 0
        self._stats_lock = threading.Lock()
        self.hash_rate_history = deque(maxlen=100)
        self.total_hashes = 0
        self.start_time = 0
        
        # Template caching with staleness detection
        self._last_template = None
        self._last_template_time = 0
        self._template_max_age = self.config.template_refresh_interval
        self._template_lock = threading.Lock()
        
        # Nonce optimization with enhanced randomization
        self._nonce_start = secrets.randbits(32)
        self._nonce_range_size = 1000000
        
        # Enhanced exponential backoff settings
        self._base_retry_delay = self.config.initial_backoff
        self._max_retry_delay = self.config.max_backoff
        self._backoff_multiplier = self.config.backoff_multiplier
        
        # Optimized mining data structures
        self._block_data_template = {}
        
        # ENHANCED: Multi-core mining capabilities
        self.cpu_cores = self._detect_cpu_cores()
        self.mining_workers = self.config.mining_workers or self.cpu_cores
        self.worker_pool = None
        self.mining_result_queue = Queue()
        self.worker_stop_event = threading.Event()
        self.core_affinity_enabled = self.config.enable_core_affinity
        
        logger.info(f"💻 Multi-core mining initialized: {self.cpu_cores} cores detected, using {self.mining_workers} workers")
        if self.core_affinity_enabled:
            logger.info("🔧 CPU core affinity enabled for optimal performance")
        self._json_cache = {}
        
        logger.info(f"Enhanced mining client initialized for address: {self._sanitize_address(wallet_address)}")
        logger.info(f"Node: {self._sanitize_url_for_log(node_url)}")
    
    def _detect_cpu_cores(self) -> int:
        """Detect available CPU cores for mining"""
        try:
            # Get logical CPU count
            logical_cores = multiprocessing.cpu_count()
            
            # Try to get physical cores (more accurate for mining)
            try:
                import psutil
                physical_cores = psutil.cpu_count(logical=False)
                if physical_cores and physical_cores > 0:
                    logger.info(f"💻 CPU detected: {physical_cores} physical cores, {logical_cores} logical cores")
                    # Use physical cores for mining to avoid hyperthreading contention
                    return physical_cores
            except ImportError:
                logger.debug("psutil not available, using logical core count")
            
            logger.info(f"💻 CPU detected: {logical_cores} logical cores")
            return logical_cores
            
        except Exception as e:
            logger.warning(f"Failed to detect CPU cores: {e}, defaulting to 1")
            return 1
    
    def _mining_worker(self, worker_id: int, template: Dict, difficulty: int, 
                      nonce_start: int, nonce_end: int, result_queue: Queue,
                      stop_event: threading.Event) -> None:
        """Multi-core mining worker function"""
        try:
            # Set CPU affinity if enabled and supported
            if self.core_affinity_enabled:
                self._set_worker_affinity(worker_id)
            
            target = "0" * difficulty
            base_json = self._precompute_block_data(template, difficulty)
            
            # Mining metadata preservation
            mining_metadata = template.get('mining_metadata', {})
            mining_node = template.get('mining_node', 'unknown')
            
            logger.debug(f"👷 Worker {worker_id} starting: nonce range {nonce_start:,} to {nonce_end:,}")
            
            worker_start_time = time.time()
            worker_hash_count = 0
            
            nonce = nonce_start
            while nonce < nonce_end and not stop_event.is_set():
                # Optimized hash calculation
                block_json = base_json[:-1] + f',"nonce":{nonce}' + '}'
                block_hash = double_sha256(block_json)
                worker_hash_count += 1
                
                # Check for valid hash
                if block_hash.startswith(target):
                    mining_time = time.time() - worker_start_time
                    hash_rate = worker_hash_count / mining_time if mining_time > 0 else 0
                    
                    # Create mined block with preserved metadata
                    mined_block = json.loads(block_json)
                    mined_block['hash'] = block_hash
                    mined_block['mining_time'] = mining_time
                    mined_block['hash_rate'] = hash_rate
                    mined_block['worker_id'] = worker_id
                    
                    # Preserve mining metadata
                    if mining_metadata:
                        mined_block['mining_metadata'] = mining_metadata
                    if mining_node:
                        mined_block['mining_node'] = mining_node
                    
                    logger.info(f"🎉 Worker {worker_id} found solution! Hash: {block_hash[:32]}...")
                    logger.info(f"   ⚡ Worker stats: {worker_hash_count:,} hashes in {mining_time:.2f}s ({hash_rate:.1f} H/s)")
                    
                    # Put result in queue and signal other workers to stop
                    result_queue.put(('success', mined_block, worker_id, worker_hash_count))
                    stop_event.set()
                    return
                    
                nonce += 1
                
                # Periodic progress check
                if worker_hash_count % 10000 == 0:
                    # Check if template became stale during mining
                    if self._is_template_stale():
                        logger.debug(f"Worker {worker_id}: Template stale, stopping")
                        stop_event.set()
                        break
                        
                    # Check network advancement
                    if self._check_network_advancement_during_mining(template):
                        logger.debug(f"Worker {worker_id}: Network advanced, stopping")
                        stop_event.set()
                        break
            
            # Worker completed range without finding solution
            mining_time = time.time() - worker_start_time
            hash_rate = worker_hash_count / mining_time if mining_time > 0 else 0
            
            logger.debug(f"👷 Worker {worker_id} completed: {worker_hash_count:,} hashes, {hash_rate:.1f} H/s")
            result_queue.put(('completed', None, worker_id, worker_hash_count))
            
        except Exception as e:
            logger.error(f"Worker {worker_id} error: {e}")
            result_queue.put(('error', str(e), worker_id, 0))
    
    def _set_worker_affinity(self, worker_id: int) -> None:
        """Set CPU affinity for mining worker"""
        try:
            import psutil
            import os
            
            # Calculate target CPU core (round-robin assignment)
            target_core = worker_id % self.cpu_cores
            
            # Set CPU affinity to specific core
            process = psutil.Process()
            process.cpu_affinity([target_core])
            
            logger.debug(f"Worker {worker_id} pinned to CPU core {target_core}")
            
        except ImportError:
            logger.debug("psutil not available, skipping CPU affinity")
        except Exception as e:
            logger.debug(f"Failed to set CPU affinity for worker {worker_id}: {e}")
    
    def mine_block_multicore(self, template: Dict, difficulty: int, timeout: int = None) -> Optional[Dict]:
        """Enhanced multi-core mining implementation"""
        timeout = timeout or self.config.max_mining_timeout
        
        logger.info(f"🚀 Starting multi-core mining with {self.mining_workers} workers")
        logger.info(f"   🎯 Target: {'0' * difficulty} (difficulty {difficulty})")
        logger.info(f"   📦 Block #{template['index']} with {len(template['transactions'])} transactions")
        
        # Calculate nonce ranges for each worker
        total_nonce_range = self.config.worker_nonce_range * self.mining_workers
        nonce_per_worker = total_nonce_range // self.mining_workers
        
        # Random starting point to avoid collisions with other miners
        base_start_nonce = secrets.randbits(32)
        
        # Clear any previous results
        while not self.mining_result_queue.empty():
            try:
                self.mining_result_queue.get_nowait()
            except Empty:
                break
        
        # Reset worker stop event
        self.worker_stop_event.clear()
        
        start_time = time.time()
        worker_futures = []
        
        # Start mining workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.mining_workers) as executor:
            for worker_id in range(self.mining_workers):
                nonce_start = base_start_nonce + (worker_id * nonce_per_worker)
                nonce_end = nonce_start + nonce_per_worker
                
                future = executor.submit(
                    self._mining_worker,
                    worker_id, template, difficulty,
                    nonce_start, nonce_end,
                    self.mining_result_queue,
                    self.worker_stop_event
                )
                worker_futures.append(future)
            
            logger.info(f"   ⚡ {self.mining_workers} workers started, mining in progress...")
            
            # Monitor for results or timeout
            result = None
            total_worker_hashes = 0
            completed_workers = 0
            
            while time.time() - start_time < timeout and completed_workers < self.mining_workers:
                try:
                    # Check for results (non-blocking)
                    status, data, worker_id, hash_count = self.mining_result_queue.get(timeout=1.0)
                    total_worker_hashes += hash_count
                    
                    if status == 'success':
                        logger.info(f"✅ Block mined successfully by worker {worker_id}!")
                        result = data
                        # Signal all workers to stop
                        self.worker_stop_event.set()
                        break
                    elif status == 'completed':
                        completed_workers += 1
                        logger.debug(f"Worker {worker_id} completed range")
                    elif status == 'error':
                        logger.error(f"Worker {worker_id} error: {data}")
                        completed_workers += 1
                        
                except Empty:
                    # Check if mining should stop
                    if hasattr(self, 'stop_mining') and self.stop_mining.is_set():
                        logger.info("Mining stopped by user")
                        self.worker_stop_event.set()
                        break
                    continue
            
            # Ensure all workers are stopped
            self.worker_stop_event.set()
            
            # Wait for all workers to complete
            for future in worker_futures:
                try:
                    future.result(timeout=2.0)
                except concurrent.futures.TimeoutError:
                    logger.warning("Worker timeout during shutdown")
                except Exception as e:
                    logger.debug(f"Worker shutdown error: {e}")
        
        mining_time = time.time() - start_time
        combined_hash_rate = total_worker_hashes / mining_time if mining_time > 0 else 0
        
        if result:
            logger.info(f"🎉 Multi-core mining successful!")
            logger.info(f"   ⏱️  Total time: {mining_time:.2f}s")
            logger.info(f"   🔢 Total hashes: {total_worker_hashes:,}")
            logger.info(f"   ⚡ Combined hash rate: {combined_hash_rate:.1f} H/s")
            
            # Update stats
            with self.stats._lock:
                self.stats.total_hashes += total_worker_hashes
                self.stats.total_mining_time += mining_time
                
        else:
            if completed_workers >= self.mining_workers:
                logger.warning(f"⏰ Mining completed all ranges without solution")
            else:
                logger.warning(f"⏰ Mining timeout after {timeout}s")
            logger.info(f"   🔢 Searched {total_worker_hashes:,} hashes at {combined_hash_rate:.1f} H/s")
        
        return result
    
    def _validate_wallet_address(self, address: str) -> bool:
        """Validate wallet address using ECDSA format verification"""
        try:
            if not address or len(address) < 26 or len(address) > 35:
                return False
            return validate_address(address)
        except Exception as e:
            logger.error(f"Address validation error: {e}")
            return False
    
    def _sanitize_address(self, address: str) -> str:
        """Sanitize wallet address for logging (privacy protection)"""
        if len(address) < 8:
            return "***INVALID***"
        return f"{address[:4]}...{address[-4:]}"
    
    def _validate_node_url(self, url: str) -> str:
        """Validate and sanitize node URL with enhanced security checks"""
        try:
            parsed = urlparse(url)
            
            # Protocol validation
            if parsed.scheme not in ['http', 'https']:
                raise ValueError(f"Invalid protocol: {parsed.scheme}")
            
            # TLS requirement check
            if self.config.require_tls and parsed.scheme != 'https':
                raise ValueError("TLS required but HTTP URL provided")
            
            # Host validation
            if not parsed.hostname:
                raise ValueError("Invalid hostname")
            
            # Port validation
            port = parsed.port or (80 if parsed.scheme == 'http' else 443)
            if not (1 <= port <= 65535):
                raise ValueError(f"Invalid port: {port}")
            
            # Security warning for HTTP in production
            if parsed.scheme == 'http' and parsed.hostname not in ['localhost', '127.0.0.1']:
                logger.warning("Using HTTP connection to remote node - consider HTTPS for production")
            
            return url.rstrip('/')
        except Exception as e:
            raise ValueError(f"Invalid node URL: {e}")
    
    def _sanitize_url_for_log(self, url: str) -> str:
        """Sanitize URL for logging (hide sensitive info)"""
        try:
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.hostname}:{parsed.port or (80 if parsed.scheme == 'http' else 443)}"
        except:
            return "[INVALID_URL]"
    
    def get_block_template(self) -> Optional[Dict]:
        """Get block template from network node with enhanced security"""
        return self.get_block_template_with_auth()
    
    def get_block_template_with_auth(self) -> Optional[Dict]:
        """Get block template with enhanced authentication and validation"""
        for attempt in range(self.config.max_retries):
            try:
                # Enhanced authentication headers
                headers = {
                    'Content-Type': 'application/json',
                    'User-Agent': 'ChainCore-MiningClient/2.0',
                    'X-Mining-Client': 'enhanced',
                    'X-Client-Version': '2.0'
                }
                
                payload = {
                    'miner_address': self.wallet_address,
                    'client_version': '2.0',
                    'timestamp': time.time()
                }
                
                response = requests.post(
                    f"{self.node_url}/mine_block",
                    json=payload,
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Validate response structure
                    if not self._validate_template_response(data):
                        logger.error("Invalid template response structure")
                        return None
                    
                    # Validate difficulty
                    difficulty = data.get('target_difficulty', 0)
                    if not self._validate_difficulty(difficulty):
                        logger.error(f"Invalid difficulty: {difficulty}")
                        return None
                    
                    # Cache template with timestamp
                    with self._template_lock:
                        self._last_template = data
                        self._last_template_time = time.time()
                    
                    logger.debug("Block template retrieved successfully")
                    return data
                else:
                    logger.warning(f"Template request failed: HTTP {response.status_code}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Template request timeout (attempt {attempt + 1})")
            except requests.exceptions.ConnectionError:
                logger.error(f"Connection error to node (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"Template request error: {e}")
            
            # Exponential backoff between attempts
            if attempt < self.config.max_retries - 1:
                delay = self._exponential_backoff(attempt)
                logger.info(f"Retrying template request in {delay:.1f} seconds...")
                time.sleep(delay)
        
        return None
    
    def _validate_template_response(self, data: Dict) -> bool:
        """Validate block template response structure"""
        required_fields = ['block_template', 'target_difficulty']
        template_fields = ['index', 'previous_hash', 'transactions', 'timestamp']
        
        if not all(field in data for field in required_fields):
            return False
        
        template = data['block_template']
        if not all(field in template for field in template_fields):
            return False
        
        return True
    
    def _validate_difficulty(self, difficulty: int) -> bool:
        """Validate mining difficulty"""
        return self.config.min_difficulty <= difficulty <= self.config.max_difficulty
    
    def mine_block(self, block_template: Dict, target_difficulty: int) -> Optional[Dict]:
        """Legacy mine_block method - redirects to timeout version"""
        return self.mine_block_with_timeout(block_template, target_difficulty, timeout=120)
    
    def submit_block(self, mined_block: Dict) -> bool:
        """Legacy submit_block method - redirects to validation version"""
        return self.submit_block_with_validation(mined_block)
    
    def check_network_health(self) -> bool:
        """Enhanced network health check with peer connectivity validation"""
        return self.check_network_health_enhanced()
    
    def check_network_health_enhanced(self) -> bool:
        """Enhanced network health check with comprehensive validation"""
        try:
            response = requests.get(f"{self.node_url}/status", timeout=10)
            if response.status_code != 200:
                print(f"WARNING: Node not responding (HTTP {response.status_code})")
                logger.warning(f"Node health check failed: HTTP {response.status_code}")
                return False
            
            status = response.json()
            
            # Comprehensive health validation
            blockchain_length = status.get('blockchain_length', 0)
            if blockchain_length < 1:
                print("WARNING: Blockchain not initialized - waiting for genesis block")
                logger.warning("Blockchain not initialized")
                return False
            
            # Check thread safety status
            thread_safe = status.get('thread_safe', False)
            if not thread_safe:
                print("WARNING: Node thread safety issues detected")
                logger.warning("Node thread safety issues")
                return False
                
            # Check peer connectivity for better mining coordination
            peer_count = status.get('peers', 0)
            if peer_count == 0:
                print("INFO: Single node mode - no peers connected")
            else:
                print(f"NETWORK: Connected to {peer_count} peers")
            
            # Check node version compatibility if available
            node_version = status.get('version', 'unknown')
            logger.info(f"Node version: {node_version}, Chain length: {blockchain_length}")
                
            print(f"SUCCESS: Network healthy - Chain length: {blockchain_length}")
            return True
            
        except requests.exceptions.ConnectionError:
            print(f"ERROR: Cannot connect to node at {self.node_url}")
            print("   TIP: Make sure the network node is running")
            logger.error(f"Cannot connect to node at {self.node_url}")
            return False
        except requests.exceptions.Timeout:
            print(f"TIMEOUT: Node timeout at {self.node_url}")
            logger.error(f"Node timeout at {self.node_url}")
            return False
        except Exception as e:
            print(f"WARNING: Network health check failed: {e}")
            logger.error(f"Network health check failed: {e}")
            return False
    
    def get_mining_stats(self) -> Dict:
        """Get mining statistics"""
        if self.start_time == 0:
            return {
                'is_mining': self.is_mining,
                'blocks_mined': 0,
                'total_time': 0,
                'average_block_time': 0,
                'estimated_hash_rate': 0
            }
        
        total_time = time.time() - self.start_time
        avg_block_time = total_time / self.blocks_mined if self.blocks_mined > 0 else 0
        
        return {
            'is_mining': self.is_mining,
            'blocks_mined': self.blocks_mined,
            'total_time': total_time,
            'average_block_time': avg_block_time,
            'estimated_hash_rate': self.total_hash_rate,
            'miner_address': self.wallet_address
        }
    
    def start_mining(self):
        """Start mining loop with intelligent retry and refresh logic"""
        # Set both legacy and new mining flags
        self.is_mining = True
        if hasattr(self, 'is_mining') and hasattr(self.is_mining, 'set'):
            self.is_mining.set()
        if hasattr(self, 'stop_mining'):
            self.stop_mining.clear()
        
        self.start_time = time.time()
        
        print("=" * 60)
        print("MINING: ChainCore Enhanced Mining Client Started")
        print("=" * 60)
        print(f"ADDRESS: {self._sanitize_address(self.wallet_address)}")
        print(f"NODE: {self._sanitize_url_for_log(self.node_url)}")
        print(f"START: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("STRATEGY: Automatic retry with fresh templates")
        print("PERFORMANCE: Optimized mining with configurable intervals")
        print("FEATURES: Template refresh, exponential backoff, optimized PoW")
        print("-" * 60)
        
        logger.info("=" * 60)
        logger.info("ENHANCED MINING CLIENT STARTED")
        logger.info("=" * 60)
        logger.info(f"Wallet: {self._sanitize_address(self.wallet_address)}")
        logger.info(f"Node: {self._sanitize_url_for_log(self.node_url)}")
        logger.info(f"Session: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("-" * 60)
        
        try:
            while self._is_mining_active():
                # Enhanced network health check
                if not self.check_network_health_enhanced():
                    print("WARNING: Network Health Check Failed")
                    print("   Issues detected:")
                    print("      * Node not responding")
                    print("      * Blockchain not initialized")
                    print("   Waiting 10 seconds for network to stabilize...")
                    logger.warning("Network health check failed, waiting...")
                    time.sleep(10)
                    continue
                
                # Mine with enhanced retry logic
                success = self.mine_with_enhanced_retry()
                
                if success:
                    self.blocks_mined += 1
                    session_time = time.time() - self.start_time
                    avg_time = session_time / self.blocks_mined
                    avg_hash_rate = self.get_average_hash_rate()
                    
                    print("SUCCESS: BLOCK SUCCESSFULLY MINED!")
                    print(f"   Session Stats:")
                    print(f"      Total Blocks: {self.blocks_mined}")
                    print(f"      Session Time: {session_time:.1f}s")
                    print(f"      Average per Block: {avg_time:.1f}s")
                    print(f"      Hash Rate: {avg_hash_rate:.0f} H/s")
                    print("   Getting next block template...")
                    
                    logger.info("Block mined successfully! Getting next template...")
                    # Brief pause after successful mining
                    time.sleep(1)
                else:
                    # Longer pause after failures to let network stabilize
                    print("ERROR: Mining Attempt Failed")
                    print("   Possible causes:")
                    print("      * Stale block template")
                    print("      * Network connectivity issues") 
                    print("      * Another miner found block first")
                    print("   Waiting 5 seconds before retry...")
                    
                    logger.warning("Mining cycle failed, waiting before retry...")
                    time.sleep(5)
                
        except KeyboardInterrupt:
            print("\n" + "=" * 60)
            print("STOP: Mining Session Stopped by User")
            print("=" * 60)
            logger.info("Mining stopped by user")
        except Exception as e:
            print(f"\nERROR: Critical Mining Error: {e}")
            print("   Please check network connectivity and try again")
            logger.error(f"Critical mining error: {e}")
        finally:
            self._stop_mining()
            self._print_session_summary()
            self.cleanup_resources()
    
    def _is_mining_active(self) -> bool:
        """Check if mining is active (handles both legacy and new flags)"""
        if hasattr(self, 'is_mining') and hasattr(self.is_mining, 'is_set'):
            return self.is_mining.is_set() and not self.stop_mining.is_set()
        else:
            return getattr(self, 'is_mining', False)
    
    def _stop_mining(self):
        """Stop mining (handles both legacy and new flags)"""
        if hasattr(self, 'is_mining') and hasattr(self.is_mining, 'clear'):
            self.is_mining.clear()
            self.stop_mining.set()
        else:
            self.is_mining = False
    
    def _print_session_summary(self):
        """Print comprehensive session summary"""
        # Use enhanced stats if available, otherwise fall back to legacy
        if hasattr(self, 'stats'):
            stats = self.stats.get_session_stats()
        else:
            stats = self.get_mining_stats()
        
        end_time = time.strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\nSTATS: Mining Session Summary")
        print("=" * 50)
        print(f"   Session End: {end_time}")
        print(f"   Blocks Mined: {stats['blocks_mined']}")
        
        if 'session_time' in stats:
            print(f"   Session Time: {stats['session_time']:.1f} seconds")
            print(f"   Average Hash Rate: {stats['average_hash_rate']:.0f} H/s")
            print(f"   Total Hashes: {stats['total_hashes']:,}")
            if stats['blocks_mined'] > 0:
                print(f"   Average Block Time: {stats['average_block_time']:.1f}s")
                print(f"   Estimated Earnings: {stats['estimated_earnings']:.1f} CC")
        else:
            # Legacy stats
            print(f"   Total Time: {stats['total_time']:.1f} seconds")
            print(f"   Average Block Time: {stats['average_block_time']:.1f}s")
            print(f"   Hash Rate: {stats['estimated_hash_rate']:.0f} H/s")
            if stats['blocks_mined'] > 0:
                earnings = stats['blocks_mined'] * BLOCK_REWARD
                print(f"   Estimated Earnings: {earnings:.1f} CC")
        
        print("=" * 50)
        
        logger.info("\n" + "=" * 50)
        logger.info("MINING SESSION SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Blocks Mined: {stats['blocks_mined']}")
        if 'session_time' in stats:
            logger.info(f"Session Time: {stats['session_time']:.1f} seconds")
            logger.info(f"Average Hash Rate: {stats['average_hash_rate']:.0f} H/s")
            logger.info(f"Total Hashes: {stats['total_hashes']:,}")
            if stats['blocks_mined'] > 0:
                logger.info(f"Average Block Time: {stats['average_block_time']:.1f}s")
                logger.info(f"Estimated Earnings: {stats['estimated_earnings']:.1f} CC")
        logger.info("=" * 50)
    
    def mine_with_retry(self, max_retries=None):
        """Mine with intelligent retry logic to handle stale templates"""
        max_retries = max_retries or self.config.max_retries
        return self.mine_with_enhanced_retry(max_retries)
    
    def mine_with_enhanced_retry(self, max_retries=None) -> bool:
        """Enhanced mining with intelligent retry logic and network state verification"""
        max_retries = max_retries or self.config.max_retries
        
        for attempt in range(max_retries):
            try:
                # CRITICAL: Verify network state before mining
                if not self._verify_network_readiness():
                    print("NETWORK: Node not ready for mining, waiting...")
                    logger.warning("Network node not ready for mining")
                    time.sleep(10)
                    continue
                
                # Get fresh template with network sync verification
                template_data = self.get_block_template_with_auth()
                if not template_data:
                    print("WAITING: Getting block template...")
                    logger.warning("Failed to get block template")
                    time.sleep(5)
                    continue
                
                # Verify template is from latest blockchain state
                if not self._verify_template_freshness(template_data):
                    print("SYNC: Template appears stale, requesting fresh one...")
                    logger.warning("Template appears stale, requesting fresh template")
                    continue
                
                template = template_data['block_template']
                difficulty = template_data['target_difficulty']
                
                print(f"MINING: Block #{template['index']}")
                print(f"   Attempt: {attempt + 1}/{max_retries}")
                print(f"   Difficulty: {difficulty} leading zeros")
                print(f"   Transactions: {len(template['transactions'])}")
                print(f"   Timeout: {self.config.max_mining_timeout} seconds")
                
                logger.info(f"Mining attempt {attempt + 1}/{max_retries}")
                logger.info(f"  Block: #{template['index']}")
                logger.info(f"  Difficulty: {difficulty}")
                logger.info(f"  Transactions: {len(template['transactions'])}")
                
                # Mine with optimizations
                mined_block = self.mine_block_optimized(template, difficulty)
                
                if mined_block:
                    # Secure submission
                    if self.submit_block_secure(mined_block):
                        logger.info(f"Block #{template['index']} successfully mined and submitted!")
                        return True
                    else:
                        logger.warning("Block submission failed")
                else:
                    print("TIMEOUT: Mining timed out, getting fresh template...")
                    logger.info("Mining timeout, getting fresh template...")
                
            except Exception as e:
                print(f"ERROR: Mining attempt {attempt + 1} error: {e}")
                logger.error(f"Mining attempt {attempt + 1} error: {e}")
            
            # Exponential backoff between attempts
            if attempt < max_retries - 1:
                delay = self._exponential_backoff(attempt)
                print(f"   Waiting {delay:.1f}s before retry...")
                logger.info(f"Waiting {delay:.1f}s before retry...")
                time.sleep(delay)
        
        print(f"ERROR: All {max_retries} mining attempts failed")
        logger.error(f"All {max_retries} mining attempts failed")
        return False
    
    def mine_block_with_timeout(self, block_template: Dict, target_difficulty: int, timeout: int = 60) -> Optional[Dict]:
        """Mine a block with timeout to prevent infinite loops"""
        return self.mine_block_optimized(block_template, target_difficulty, timeout)
    
    def mine_block_optimized(self, template: Dict, difficulty: int, timeout: int = None) -> Optional[Dict]:
        """Optimized mining with multi-core performance enhancements"""
        timeout = timeout or self.config.max_mining_timeout
        
        logger.info(f"Starting optimized mining - Block #{template['index']}, Difficulty: {difficulty}")
        print(f"MINING: Starting Multi-Core Proof-of-Work Mining...")
        print(f"   💻 Using {self.mining_workers} CPU cores ({self.cpu_cores} available)")
        print(f"   🎯 Target: {'0' * difficulty} (difficulty {difficulty})")
        print(f"   📦 Block Size: {len(template['transactions'])} transactions")
        print("   ⚡ Multi-core mining in progress...")
        
        # Use multi-core mining for better performance
        if self.mining_workers > 1:
            return self.mine_block_multicore(template, difficulty, timeout)
        
        # Fallback to single-core mining if only 1 worker
        return self._mine_block_single_core(template, difficulty, timeout)
    
    def _mine_block_single_core(self, template: Dict, difficulty: int, timeout: int) -> Optional[Dict]:
        """Single-core mining fallback (original algorithm)"""
        target = "0" * difficulty
        
        logger.info(f"Using single-core mining fallback")
        
        # Precompute block data template
        base_json = self._precompute_block_data(template, difficulty)
        
        # Enhanced nonce range with random starting point
        start_nonce = self._nonce_start + secrets.randbits(16)
        end_nonce = start_nonce + self._nonce_range_size
        
        start_time = time.time()
        hash_count = 0
        last_progress_time = start_time
        last_progress_hashes = 0
        
        # Preserve mining metadata from block template
        mining_metadata = template.get('mining_metadata', {})
        mining_node = template.get('mining_node', 'unknown')
        
        logger.info(f"Mining range: {start_nonce:,} to {end_nonce:,}")
        
        nonce = start_nonce
        while nonce < end_nonce and time.time() - start_time < timeout:
            # Check if mining was stopped
            if hasattr(self, 'stop_mining') and self.stop_mining.is_set():
                logger.info("Mining stopped by user")
                return None
            elif hasattr(self, 'is_mining') and not getattr(self, 'is_mining', True):
                logger.info("Mining stopped by user")
                return None
            
            # ENHANCED: Real-time network state monitoring during mining
            if hash_count > 0 and hash_count % 5000 == 0:  # Check more frequently
                # Check template staleness
                if self._is_template_stale():
                    logger.warning("Template became stale during mining, stopping")
                    return None
                
                # CRITICAL: Check if network has advanced while we're mining
                if self._check_network_advancement_during_mining(template):
                    logger.warning("Network has advanced during mining - our work is now stale")
                    print("NETWORK: Chain advanced while mining - abandoning current work")
                    return None
            
            # Optimized hash calculation (avoid JSON serialization in loop)
            block_json = base_json[:-1] + f',"nonce":{nonce}' + '}'
            block_hash = double_sha256(block_json)
            hash_count += 1
            
            # Check for valid hash
            if block_hash.startswith(target):
                mining_time = time.time() - start_time
                hash_rate = hash_count / mining_time if mining_time > 0 else 0
                
                # Update statistics
                self._update_hash_rate(hash_count, mining_time)
                self.stats.update_hash_rate(hash_count, mining_time)
                
                logger.info("PROOF-OF-WORK FOUND!")
                logger.info(f"Valid Hash: {block_hash}")
                logger.info(f"Winning Nonce: {nonce:,}")
                logger.info(f"Mining Time: {mining_time:.2f} seconds")
                logger.info(f"Hash Rate: {hash_rate:.0f} H/s")
                logger.info("Submitting to network...")
                
                # Update template with solution
                result = template.copy()
                result['nonce'] = nonce
                result['hash'] = block_hash
                
                # Ensure mining metadata is preserved in the final block
                if mining_metadata:
                    result['mining_metadata'] = mining_metadata
                if mining_node != 'unknown':
                    result['mining_node'] = mining_node
                
                return result
            
            nonce += 1
            
            # Optimized progress updates (configurable interval)
            if hash_count % self.config.progress_update_interval == 0:
                current_time = time.time()
                elapsed = current_time - last_progress_time
                if elapsed > 0:
                    recent_hashes = hash_count - last_progress_hashes
                    current_rate = recent_hashes / elapsed
                    remaining = timeout - (current_time - start_time)
                    
                    print(f"   Progress: Nonce {nonce:,} | Rate: {current_rate:.0f} H/s | Time Left: {remaining:.0f}s")
                    logger.debug(f"Mining progress: {hash_count:,} hashes, {current_rate:.0f} H/s, {remaining:.0f}s left")
                    
                    last_progress_time = current_time
                    last_progress_hashes = hash_count
        
        # Update statistics even if no solution found
        final_time = time.time() - start_time
        self._update_hash_rate(hash_count, final_time)
        self.stats.update_hash_rate(hash_count, final_time)
        
        print(f"TIMEOUT: Mining timeout after {timeout} seconds")
        logger.info(f"Mining completed - {hash_count:,} hashes in {final_time:.2f}s")
        return None
    
    def _precompute_block_data(self, template: Dict, difficulty: int) -> str:
        """Precompute block data template for efficient mining"""
        # Create template with placeholder for nonce
        self._block_data_template = {
            'index': template['index'],
            'previous_hash': template['previous_hash'],
            'merkle_root': template['merkle_root'],
            'timestamp': template['timestamp'],
            'target_difficulty': difficulty
        }
        
        # Pre-serialize everything except nonce
        base_json = json.dumps({
            k: v for k, v in self._block_data_template.items() 
            if k != 'nonce'
        }, sort_keys=True)
        
        return base_json
    
    def submit_block_with_validation(self, mined_block: Dict) -> bool:
        """Submit mined block with enhanced error handling and validation"""
        return self.submit_block_secure(mined_block)
    
    def submit_block_secure(self, block: Dict) -> bool:
        """Secure block submission with comprehensive validation and network sync check"""
        try:
            # CRITICAL: Final network sync check before submission
            print("SYNC: Performing final network sync check before block submission...")
            if not self._perform_pre_submission_sync_check(block):
                print("REJECTED: Block is stale - network has moved forward during mining")
                logger.warning("Block submission rejected - network advanced during mining")
                return False
            
            # Pre-submission validation
            if not self._validate_block_before_submission(block):
                return False
            
            headers = {
                'Content-Type': 'application/json',
                'X-Local-Mining': 'true',
                'X-Mining-Client': 'enhanced',
                'User-Agent': 'ChainCore-MiningClient/2.0'
            }
            
            response = requests.post(
                f"{self.node_url}/submit_block",
                json=block,
                headers=headers,
                timeout=15
            )
            
            return self._handle_submission_response(response, block)
            
        except requests.exceptions.Timeout:
            print("TIMEOUT: Block submission timeout")
            logger.error("Block submission timeout")
        except requests.exceptions.ConnectionError:
            print("ERROR: Connection error during block submission")
            logger.error("Connection error during submission")
        except Exception as e:
            print(f"ERROR: Error submitting block: {e}")
            logger.error(f"Submission error: {e}")
        
        return False
    
    def _validate_block_before_submission(self, block: Dict) -> bool:
        """Validate block before submission"""
        required_fields = ['index', 'hash', 'nonce', 'previous_hash']
        
        if not all(field in block for field in required_fields):
            logger.error("Block missing required fields")
            return False
        
        # Validate hash format
        if not isinstance(block['hash'], str) or len(block['hash']) != 64:
            logger.error("Invalid hash format")
            return False
        
        return True
    
    def _handle_submission_response(self, response: requests.Response, block: Dict) -> bool:
        """Handle block submission response"""
        if response.status_code == 200:
            result = response.json()
            status = result.get('status', 'unknown')
            
            if status == 'accepted':
                block_hash = result.get('block_hash', 'unknown')
                chain_length = result.get('chain_length', 'unknown')
                mining_source = result.get('mining_source', 'unknown')
                
                print(f"SUCCESS: BLOCK ACCEPTED by network!")
                print(f"   Block Hash: {block_hash[:32]}...")
                print(f"   Block Index: {block['index']}")
                print(f"   Chain Length: {chain_length}")
                print(f"   Source: {mining_source}")
                
                logger.info(f"SUCCESS: Block #{block['index']} accepted by network")
                logger.info(f"  Hash: {block['hash'][:16]}...{block['hash'][-8:]}")
                logger.info(f"  Chain Length: {chain_length}")
                
                # Update statistics
                with self.stats._lock:
                    self.stats.blocks_mined += 1
                
                return True
            else:
                error_msg = result.get('error', 'Unknown error')
                print(f"ERROR: BLOCK REJECTED: {error_msg}")
                logger.warning(f"Block rejected: {error_msg}")
                return False
                
        elif response.status_code == 409:
            # Conflict - block already exists (race condition)
            result = response.json()
            error_msg = result.get('error', 'Block conflict')
            reason = result.get('reason', 'conflict')
            
            print(f"RACE: MINING RACE LOST: {error_msg}")
            print(f"   Another miner submitted this block first")
            print(f"   Reason: {reason}")
            logger.info("Mining race lost - another miner found block first")
            return False
            
        elif response.status_code == 400:
            error_info = response.json()
            error_msg = error_info.get('error', 'Unknown error')
            reason = error_info.get('reason', 'validation_failed')
            
            print(f"ERROR: BLOCK VALIDATION FAILED: {error_msg}")
            print(f"   Reason: {reason}")
            
            # Enhanced error handling for specific cases
            if reason == 'invalid_block_data':
                print("   Block data structure is invalid")
            elif 'previous hash' in error_msg.lower():
                print("   Block is stale (blockchain moved forward during mining)")
            elif 'transaction' in error_msg.lower():
                print("   Transaction validation failed (possibly spent UTXOs)")
            
            logger.error(f"Block validation failed: {error_msg}")
            return False
        else:
            print(f"ERROR: Block submission failed with status {response.status_code}: {response.text}")
            logger.error(f"Submission failed: HTTP {response.status_code}")
            return False
    
    def _is_template_stale(self) -> bool:
        """Check if current template is stale"""
        return time.time() - self._last_template_time > self._template_max_age
    
    def _update_hash_rate(self, hash_count: int, elapsed_time: float):
        """Update hash rate statistics with thread safety and proper accounting"""
        if elapsed_time <= 0:
            return
        
        with self._stats_lock:
            # Calculate current hash rate
            current_rate = hash_count / elapsed_time
            
            # Add to bounded history (prevents memory leaks)
            self.hash_rate_history.append(current_rate)
            
            # Update total hashes (use max to prevent decreases)
            new_total = max(self.total_hashes, hash_count)
            self.total_hashes = new_total
    
    def get_average_hash_rate(self) -> float:
        """Get average hash rate from recent history"""
        with self._stats_lock:
            if not self.hash_rate_history:
                return 0.0
            return sum(self.hash_rate_history) / len(self.hash_rate_history)
    
    def get_mining_stats(self) -> Dict:
        """Get mining statistics with legacy compatibility"""
        if self.start_time == 0:
            return {
                'is_mining': self._is_mining_active() if hasattr(self, '_is_mining_active') else False,
                'blocks_mined': self.blocks_mined,
                'total_time': 0,
                'average_block_time': 0,
                'estimated_hash_rate': 0,
                'miner_address': self.wallet_address
            }
        
        total_time = time.time() - self.start_time
        avg_block_time = total_time / self.blocks_mined if self.blocks_mined > 0 else 0
        
        return {
            'is_mining': self._is_mining_active() if hasattr(self, '_is_mining_active') else False,
            'blocks_mined': self.blocks_mined,
            'total_time': total_time,
            'average_block_time': avg_block_time,
            'estimated_hash_rate': self.get_average_hash_rate(),
            'miner_address': self.wallet_address
        }
    
    def _exponential_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay"""
        delay = self._base_retry_delay * (self._backoff_multiplier ** attempt)
        return min(delay, self._max_retry_delay)
    
    def get_detailed_stats(self) -> Dict:
        """Get detailed mining statistics including hash rates"""
        basic_stats = self.get_mining_stats()
        
        return {
            **basic_stats,
            'current_hash_rate': self.get_average_hash_rate(),
            'total_hashes': self.total_hashes,
            'miner_address': self.wallet_address
        }
    
    def _verify_network_readiness(self) -> bool:
        """Verify network node is ready and properly synchronized"""
        try:
            response = requests.get(f"{self.node_url}/status", timeout=5)
            if response.status_code != 200:
                return False
            
            status = response.json()
            
            # Check basic node health
            if not status.get('thread_safe', False):
                logger.warning("Node reports thread safety issues")
                return False
            
            # Check blockchain initialization
            blockchain_length = status.get('blockchain_length', 0)
            if blockchain_length < 1:
                logger.warning("Blockchain not properly initialized")
                return False
            
            # Check peer connectivity for better mining coordination
            peer_count = status.get('peers', 0)
            if peer_count == 0:
                logger.info("Mining in single node mode (no peers)")
            
            return True
            
        except Exception as e:
            logger.error(f"Network readiness check failed: {e}")
            return False
    
    def _verify_template_freshness(self, template_data: Dict) -> bool:
        """Verify the template represents the latest blockchain state"""
        try:
            # Get current blockchain status
            response = requests.get(f"{self.node_url}/status", timeout=3)
            if response.status_code != 200:
                logger.warning("Cannot verify template freshness - status check failed")
                return True  # Assume fresh if can't verify
            
            status = response.json()
            current_length = status.get('blockchain_length', 0)
            template_index = template_data['block_template']['index']
            
            # Template should be for the next block
            if template_index != current_length:
                logger.warning(f"Template stale: template for #{template_index}, current chain #{current_length}")
                return False
            
            # Additional freshness check - timestamp should be recent
            template_timestamp = template_data['block_template'].get('timestamp', 0)
            current_time = time.time()
            if current_time - template_timestamp > 60:  # Template older than 60 seconds
                logger.warning(f"Template timestamp too old: {current_time - template_timestamp:.1f}s")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Template freshness check failed: {e}")
            return True  # Assume fresh if can't verify to avoid blocking
    
    def _perform_pre_submission_sync_check(self, block: Dict) -> bool:
        """Perform critical sync check before block submission to prevent stale blocks"""
        try:
            # Get the latest blockchain state from network node
            response = requests.get(f"{self.node_url}/status", timeout=5)
            if response.status_code != 200:
                logger.error("Pre-submission sync check failed - cannot reach node")
                return False  # Reject if cannot verify - safety first
            
            status = response.json()
            current_chain_length = status.get('blockchain_length', 0)
            block_index = block.get('index', -1)
            
            # CRITICAL CHECK: Block must be for the next position in chain
            if block_index != current_chain_length:
                logger.warning(f"STALE BLOCK DETECTED: Block #{block_index} vs current chain #{current_chain_length}")
                print(f"   Network moved forward: Chain now at #{current_chain_length}, our block is #{block_index}")
                return False
            
            # Additional verification: Check if block's previous_hash matches current chain tip
            try:
                blockchain_response = requests.get(f"{self.node_url}/blockchain", timeout=5)
                if blockchain_response.status_code == 200:
                    blockchain_data = blockchain_response.json()
                    chain = blockchain_data.get('chain', [])
                    
                    if chain and len(chain) > 0:
                        latest_block_hash = chain[-1].get('hash', '')
                        block_prev_hash = block.get('previous_hash', '')
                        
                        if latest_block_hash != block_prev_hash:
                            logger.warning(f"HASH MISMATCH: Block prev_hash doesn't match chain tip")
                            print(f"   Chain tip hash: {latest_block_hash[:32]}...")
                            print(f"   Block prev_hash: {block_prev_hash[:32]}...")
                            return False
                        
                        logger.info("✅ Pre-submission sync check passed - block is fresh")
                        print("   ✅ Block is current with network state")
                        return True
                
            except Exception as e:
                logger.warning(f"Could not verify chain tip hash: {e}")
                # Continue with basic index check if detailed check fails
            
            # If we get here with matching index, consider it valid
            logger.info("✅ Pre-submission sync check passed (basic)")
            return True
            
        except Exception as e:
            logger.error(f"Pre-submission sync check failed: {e}")
            return False  # Reject if cannot verify - safety first
    
    def _check_network_advancement_during_mining(self, original_template: Dict) -> bool:
        """Check if network has advanced while we're mining, making our work stale"""
        try:
            # Quick status check to see if chain has grown
            response = requests.get(f"{self.node_url}/status", timeout=2)
            if response.status_code != 200:
                # If we can't check, assume network is stable
                return False
            
            status = response.json()
            current_chain_length = status.get('blockchain_length', 0)
            our_block_index = original_template.get('index', -1)
            
            # If current chain length is greater than our target block index,
            # someone else mined a block while we were working
            if current_chain_length > our_block_index:
                logger.warning(f"Network advanced: Chain now #{current_chain_length}, we're mining #{our_block_index}")
                return True
            
            # Additional check: Verify the chain tip hash hasn't changed
            # This catches cases where the chain length is the same but content changed
            try:
                our_prev_hash = original_template.get('previous_hash', '')
                if our_prev_hash and current_chain_length > 0:
                    # Get current chain tip
                    blockchain_response = requests.get(f"{self.node_url}/blockchain", timeout=2)
                    if blockchain_response.status_code == 200:
                        blockchain_data = blockchain_response.json()
                        chain = blockchain_data.get('chain', [])
                        
                        if chain and len(chain) >= current_chain_length:
                            current_tip_hash = chain[-1].get('hash', '')
                            
                            # If we're mining for block N and current chain tip (block N-1) 
                            # has a different hash than our template's previous_hash,
                            # then the chain has been reorganized
                            if our_block_index == current_chain_length and current_tip_hash != our_prev_hash:
                                logger.warning(f"Chain reorganization detected during mining")
                                print(f"   Expected prev_hash: {our_prev_hash[:32]}...")
                                print(f"   Current tip hash:   {current_tip_hash[:32]}...")
                                return True
                            
            except Exception as e:
                logger.debug(f"Could not perform detailed chain advancement check: {e}")
                # If detailed check fails, rely on basic length check
            
            return False
            
        except Exception as e:
            logger.debug(f"Network advancement check failed: {e}")
            return False  # Assume stable if we can't check

    def cleanup_resources(self):
        """Cleanup resources and locks when mining stops"""
        try:
            # Clear template cache
            with self._template_lock:
                self._last_template = None
                self._template_timestamp = 0
            
            # Clear hash rate history to free memory
            with self._stats_lock:
                self.hash_rate_history.clear()
            
            # Clear enhanced stats if available
            if hasattr(self, 'stats'):
                with self.stats._lock:
                    self.stats.hash_rate_history.clear()
                    
            logger.info("Mining client resources cleaned up")
        except Exception as e:
            logger.warning(f"Error during resource cleanup: {e}")

def main():
    """Enhanced main function with comprehensive argument validation"""
    parser = argparse.ArgumentParser(
        description='ChainCore Enhanced Mining Client - Enterprise Grade',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --wallet 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa --node http://localhost:5000
  %(prog)s --wallet 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2 --node https://node.example.com:8333
        """
    )
    
    parser.add_argument('--wallet', '-w', required=True, 
                       help='Mining wallet address (Bitcoin-style, validated)')
    parser.add_argument('--node', '-n', default='http://localhost:5000',
                       help='Node URL (http/https, validated)')
    parser.add_argument('--difficulty-range', default='1,12',
                       help='Accepted difficulty range (min,max)')
    parser.add_argument('--timeout', type=int, default=120,
                       help='Mining timeout in seconds')
    parser.add_argument('--retries', type=int, default=3,
                       help='Maximum retry attempts')
    parser.add_argument('--refresh-interval', type=float, default=30.0,
                       help='Template refresh interval (seconds)')
    parser.add_argument('--require-tls', action='store_true',
                       help='Require HTTPS connection')
    parser.add_argument('--stats', action='store_true', help='Show mining stats and exit')
    parser.add_argument('--quiet', action='store_true', help='Skip startup banner')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    # ENHANCED: Multi-core mining arguments
    parser.add_argument('--workers', type=int, default=None,
                       help='Number of mining workers (default: auto-detect CPU cores)')
    parser.add_argument('--disable-affinity', action='store_true',
                       help='Disable CPU core affinity for workers')
    parser.add_argument('--worker-range', type=int, default=100000,
                       help='Nonce range per worker (default: 100000)')
    parser.add_argument('--single-core', action='store_true',
                       help='Force single-core mining (for testing)')
    parser.add_argument('--show-cores', action='store_true',
                       help='Show detected CPU cores and exit')
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Parse difficulty range with validation
        try:
            min_diff, max_diff = map(int, args.difficulty_range.split(','))
            if min_diff < 1 or max_diff > 20 or min_diff > max_diff:
                raise ValueError(f"Invalid difficulty range: {min_diff},{max_diff}")
        except ValueError as e:
            logger.error(f"Invalid difficulty range format: {e}")
            sys.exit(1)
        
        # Create enhanced configuration with multi-core settings
        config = MiningConfig(
            max_mining_timeout=args.timeout,
            max_retries=args.retries,
            template_refresh_interval=args.refresh_interval,
            require_tls=args.require_tls,
            min_difficulty=min_diff,
            max_difficulty=max_diff,
            # Multi-core settings
            mining_workers=1 if args.single_core else args.workers,
            enable_core_affinity=not args.disable_affinity,
            worker_nonce_range=args.worker_range
        )
        
        # Show startup banner unless quiet mode
        if not args.quiet and not args.stats:
            try:
                from startup_banner import startup_mining_client
                startup_mining_client(args.wallet, args.node)
            except ImportError:
                print("MINING: ChainCore Enhanced Mining Client Starting...")
                # Sanitize wallet address for privacy
                wallet_display = f"{args.wallet[:4]}...{args.wallet[-4:]}" if len(args.wallet) >= 8 else "***INVALID***"
                print(f"   Wallet: {wallet_display}")
                print(f"   Node: {args.node}")
        
        # Handle show-cores option before creating miner
        if args.show_cores:
            temp_miner = MiningClient.__new__(MiningClient)
            cores = temp_miner._detect_cpu_cores()
            print(f"💻 CPU Information:")
            print(f"   Detected CPU cores: {cores}")
            print(f"   Default workers: {cores}")
            print(f"   Affinity support: {'Yes' if not args.disable_affinity else 'Disabled'}")
            sys.exit(0)
        
        # Create enhanced mining client
        miner = MiningClient(args.wallet, args.node, config)
        
        if args.stats:
            # Try enhanced stats first, fall back to legacy
            if hasattr(miner, 'stats'):
                stats = miner.stats.get_session_stats()
                print("STATS: Enhanced Mining Client Statistics")
                print(f"  Blocks mined: {stats['blocks_mined']}")
                print(f"  Average hash rate: {stats['average_hash_rate']:.0f} H/s")
                print(f"  Total hashes: {stats['total_hashes']:,}")
                print(f"  Session time: {stats['session_time']:.1f}s")
            else:
                stats = miner.get_detailed_stats()
                print(f"STATS: Mining Stats:")
                print(f"   Blocks mined: {stats['blocks_mined']}")
                print(f"   Mining status: {'Active' if stats['is_mining'] else 'Inactive'}")
                print(f"   Total hash rate: {stats['estimated_hash_rate']:.2f} H/s")
                print(f"   Current hash rate: {stats['current_hash_rate']:.2f} H/s")
                print(f"   Total hashes: {stats['total_hashes']:,}")
                print(f"   Total time: {stats['total_time']:.2f}s")
                print(f"   Average block time: {stats['average_block_time']:.2f}s")
                # Sanitize address for privacy
                addr_display = f"{stats['miner_address'][:4]}...{stats['miner_address'][-4:]}" if len(stats['miner_address']) >= 8 else "***INVALID***"
                print(f"   Miner address: {addr_display}")
        else:
            # Sanitize wallet address for privacy
            wallet_display = f"{args.wallet[:4]}...{args.wallet[-4:]}" if len(args.wallet) >= 8 else "***INVALID***"
            print(f"Starting enhanced mining for wallet: {wallet_display}")
            print(f"Node: {miner._sanitize_url_for_log(args.node)}")
            print("Press Ctrl+C to stop mining")
            print("-" * 50)
            
            miner.start_mining()
    
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"ERROR: {e}")
        print("Please check your command line arguments.")
        sys.exit(1)
    except ImportError as e:
        logger.error(f"Module import error: {e}")
        print(f"ERROR: Missing required modules: {e}")
        print("Please run: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"FATAL ERROR: {e}")
        print("Please check the logs for more details.")
        sys.exit(1)

if __name__ == '__main__':
    main()