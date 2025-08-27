#!/usr/bin/env python3
"""
ChainCore Networking Module
Enhanced P2P networking with full-mesh connectivity, gossiping, and persistent peers
"""

from .peer_manager import (
    PeerNetworkManager,
    PeerInfo,
    PeerStorage,
    OutboundConnectionManager,
    initialize_peer_manager,
    get_peer_manager
)

# Alias for backward compatibility
PeerManager = PeerNetworkManager

__all__ = [
    'PeerNetworkManager',
    'PeerManager',
    'PeerInfo', 
    'PeerStorage',
    'OutboundConnectionManager',
    'initialize_peer_manager',
    'get_peer_manager'
]