#!/usr/bin/env python3
"""
ChainCore Configuration Module
Centralized blockchain configuration and constants
"""

# Blockchain Core Configuration
BLOCKCHAIN_DIFFICULTY = 4  # Leading zeros required in hash
BLOCK_REWARD = 50.0  # CC (ChainCore) reward per block
BLOCK_SIZE_LIMIT = 1024 * 1024  # 1MB block size limit

# Difficulty Adjustment System
DIFFICULTY_ADJUSTMENT_ENABLED = True
TARGET_BLOCK_TIME = 60  # seconds per block target
DIFFICULTY_ADJUSTMENT_INTERVAL = 10  # blocks between difficulty adjustments
MAX_DIFFICULTY_CHANGE = 2  # maximum difficulty change per adjustment
MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 15

# Peer Discovery Configuration - Enhanced for Large Networks
PEER_DISCOVERY_ENABLED = True
CONTINUOUS_DISCOVERY_INTERVAL = 30  # seconds between discovery attempts
MAX_PEERS = 200  # Support up to 200 nodes in network
MIN_PEERS = 3
TARGET_PEERS = 20  # Target 20 active peers for better consensus
PEER_DISCOVERY_RANGE = (5000, 5200)  # Port range for peer discovery (200 ports)
PEER_DISCOVERY_BATCH_SIZE = 50  # Discover peers in batches for performance
PEER_DISCOVERY_PARALLEL_WORKERS = 20  # Parallel workers for peer discovery

# Network Configuration - Enhanced for Large Networks
NETWORK_MAGIC = 0xCCCCCCCC
PROTOCOL_VERSION = 1
DEFAULT_PORT = 5000

# Large Network Performance Optimization
SYNC_BATCH_SIZE = 100  # Number of blocks to sync at once
SYNC_PARALLEL_REQUESTS = 5  # Parallel sync requests to peers
PEER_HEALTH_CHECK_INTERVAL = 60  # Health check frequency for peers
NETWORK_TIMEOUT_SCALING = True  # Scale timeouts based on network size
BASE_TIMEOUT = 5.0  # Base timeout for network operations
MAX_TIMEOUT = 30.0  # Maximum timeout for large networks

# Mining Configuration
MAX_TRANSACTIONS_PER_BLOCK = 1000
COINBASE_MATURITY = 100  # blocks before coinbase can be spent

# Mining Coordination Configuration
TARGET_BLOCK_TIME = 10.0  # seconds per block for local testing
MINING_ROUND_DURATION = 12.0  # seconds per mining round

def get_difficulty() -> int:
    """Get current blockchain difficulty"""
    return BLOCKCHAIN_DIFFICULTY

def get_mining_target() -> str:
    """Get mining target string (zeros prefix)"""
    return "0" * BLOCKCHAIN_DIFFICULTY

def get_all_config() -> dict:
    """Get all configuration as dictionary"""
    return {
        'blockchain_difficulty': BLOCKCHAIN_DIFFICULTY,
        'block_reward': BLOCK_REWARD,
        'block_size_limit': BLOCK_SIZE_LIMIT,
        'difficulty_adjustment_enabled': DIFFICULTY_ADJUSTMENT_ENABLED,
        'target_block_time': TARGET_BLOCK_TIME,
        'difficulty_adjustment_interval': DIFFICULTY_ADJUSTMENT_INTERVAL,
        'max_difficulty_change': MAX_DIFFICULTY_CHANGE,
        'min_difficulty': MIN_DIFFICULTY,
        'max_difficulty': MAX_DIFFICULTY,
        'peer_discovery_enabled': PEER_DISCOVERY_ENABLED,
        'continuous_discovery_interval': CONTINUOUS_DISCOVERY_INTERVAL,
        'max_peers': MAX_PEERS,
        'min_peers': MIN_PEERS,
        'target_peers': TARGET_PEERS,
        'network_magic': NETWORK_MAGIC,
        'protocol_version': PROTOCOL_VERSION,
        'default_port': DEFAULT_PORT,
        'max_transactions_per_block': MAX_TRANSACTIONS_PER_BLOCK,
        'coinbase_maturity': COINBASE_MATURITY
    }