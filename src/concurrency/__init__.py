#!/usr/bin/env python3
"""
ChainCore Thread Safety Module
Concurrency and race condition prevention

Usage:
    from src.concurrency import ThreadSafeBlockchain, ThreadSafePeerManager, ThreadSafeMiner
    
Features:
    - Reader-Writer locks with deadlock detection
    - Atomic operations with MVCC
    - Connection pooling and rate limiting
    - Mining work coordination
    - Comprehensive monitoring and statistics
"""

# Core thread safety primitives
from .thread_safety import (
    LockManager, LockOrder, AdvancedRWLock, AtomicCounter,
    TransactionQueue, MemoryBarrier, DeadlockDetector,
    synchronized, Transaction, lock_manager, deadlock_detector
)

# Thread-safe blockchain components
from .blockchain_safe import (
    ThreadSafeBlockchain, ThreadSafeUTXOSet, ChainStats
)

# Thread-safe networking
from .network_safe import (
    ThreadSafePeerManager, ConnectionPool, RateLimiter,
    PeerInfo, peer_manager
)

# Thread-safe mining
from .mining_safe import (
    ThreadSafeMiner, WorkCoordinator, MiningPool, 
    MiningWork, MiningResult, mining_pool
)


__all__ = [
    # Core primitives
    'LockManager', 'LockOrder', 'AdvancedRWLock', 'AtomicCounter',
    'TransactionQueue', 'MemoryBarrier', 'DeadlockDetector',
    'synchronized', 'Transaction', 'lock_manager', 'deadlock_detector',
    
    # Blockchain
    'ThreadSafeBlockchain', 'ThreadSafeUTXOSet', 'ChainStats',
    
    # Networking
    'ThreadSafePeerManager', 'ConnectionPool', 'RateLimiter',
    'PeerInfo', 'peer_manager',
    
    # Mining
    'ThreadSafeMiner', 'WorkCoordinator', 'MiningPool',
    'MiningWork', 'MiningResult', 'mining_pool',
]