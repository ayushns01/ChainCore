#!/usr/bin/env python3
"""
ChainCore Networking Module
Enhanced P2P networking with full-mesh connectivity, gossiping, and persistent peers
"""

from .peer_manager import (
    EnhancedPeerManager,
    PeerInfo,
    PeerStorage,
    OutboundConnectionManager,
    initialize_peer_manager,
    get_peer_manager
)

# Alias for backward compatibility
PeerManager = EnhancedPeerManager

__all__ = [
    'EnhancedPeerManager',
    'PeerManager',
    'PeerInfo', 
    'PeerStorage',
    'OutboundConnectionManager',
    'initialize_peer_manager',
    'get_peer_manager'
]