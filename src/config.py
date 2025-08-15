#!/usr/bin/env python3
"""
ChainCore Configuration Module
Centralized configuration for blockchain parameters
"""

# ==========================================
# BLOCKCHAIN CONFIGURATION
# ==========================================

# Mining difficulty - standardized across all nodes for competitive mining
BLOCKCHAIN_DIFFICULTY = 4  # Consistent difficulty for fair competition

# Dynamic difficulty adjustment settings
DIFFICULTY_ADJUSTMENT_ENABLED = True
TARGET_BLOCK_TIME = 10.0  # seconds
DIFFICULTY_ADJUSTMENT_INTERVAL = 10  # blocks
MAX_DIFFICULTY_CHANGE = 4  # maximum change per adjustment
MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 12

# Block reward for miners
BLOCK_REWARD = 50.0

# Transaction fees
DEFAULT_TRANSACTION_FEE = 0.01

# Network settings
DEFAULT_API_PORT = 5000
DEFAULT_P2P_PORT = 8000
PEER_DISCOVERY_RANGE = (5000, 5100)  # Extended range for 100+ nodes

# Enhanced peer management settings (supports unlimited miners)
MIN_PEERS = 1          # Minimum peers to maintain (allow single node)
TARGET_PEERS = 10      # Optimal number of peers  
MAX_PEERS = 50         # Maximum peers (increased for better network)
CONTINUOUS_DISCOVERY_INTERVAL = 30  # Faster discovery - every 30 seconds

# Peer discovery optimization
DISCOVERY_TIMEOUT = 3.0          # Fast timeout for peer discovery
MAX_DISCOVERY_WORKERS = 20       # More concurrent workers
PEER_HEALTH_CHECK_INTERVAL = 30  # Health check every 30 seconds
PEER_FAILURE_THRESHOLD = 3       # Remove peer after 3 failures

# Mining settings
MINING_TIMEOUT = 60  # seconds
MAX_BLOCK_SIZE = 1000  # max transactions per block

# Thread safety settings
LOCK_TIMEOUT = 10.0  # seconds
DEADLOCK_DETECTION_ENABLED = True


def get_difficulty() -> int:
    """Get current blockchain difficulty setting"""
    return BLOCKCHAIN_DIFFICULTY

def get_mining_target(difficulty: int = None) -> str:
    """Get mining target string (leading zeros)"""
    if difficulty is None:
        difficulty = BLOCKCHAIN_DIFFICULTY
    return "0" * difficulty

def validate_difficulty(difficulty: int) -> bool:
    """Validate difficulty setting"""
    return 1 <= difficulty <= 10  # Reasonable range

def get_all_config() -> dict:
    """Get all configuration as dictionary"""
    return {
        'blockchain_difficulty': BLOCKCHAIN_DIFFICULTY,
        'block_reward': BLOCK_REWARD,
        'default_transaction_fee': DEFAULT_TRANSACTION_FEE,
        'default_api_port': DEFAULT_API_PORT,
        'default_p2p_port': DEFAULT_P2P_PORT,
        'peer_discovery_range': PEER_DISCOVERY_RANGE,
        'mining_timeout': MINING_TIMEOUT,
        'max_block_size': MAX_BLOCK_SIZE,
        'lock_timeout': LOCK_TIMEOUT,
        'deadlock_detection_enabled': DEADLOCK_DETECTION_ENABLED,
    }

# Backwards compatibility - keep the original variable name
# This allows existing code to work without changes
BLOCKCHAIN_DIFFICULTY = BLOCKCHAIN_DIFFICULTY