#!/usr/bin/env python3
"""
ChainCore Consensus Module
Local network consensus mechanisms for multi-terminal testing
"""

from .mining_coordinator import LocalMiningCoordinator, get_mining_coordinator, mining_coordinator

__all__ = [
    'LocalMiningCoordinator', 
    'get_mining_coordinator',
    'mining_coordinator'
]