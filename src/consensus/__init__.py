#!/usr/bin/env python3
"""
ChainCore Consensus Module
Local network consensus mechanisms for multi-terminal testing
"""

from .fork_resolver import LocalForkResolver, get_fork_resolver, fork_resolver
from .mining_coordinator import LocalMiningCoordinator, get_mining_coordinator, mining_coordinator

__all__ = [
    'LocalForkResolver',
    'LocalMiningCoordinator', 
    'get_fork_resolver',
    'get_mining_coordinator',
    'fork_resolver',
    'mining_coordinator'
]