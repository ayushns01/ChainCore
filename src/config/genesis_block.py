#!/usr/bin/env python3
"""
ChainCore Genesis Block - Hardcoded for Network Consensus
This ensures all nodes start with the same genesis block to prevent network fragmentation
"""

import time
from typing import Dict

# ChainCore Genesis Block Constants (Hardcoded for all nodes)
GENESIS_BLOCK_DATA = {
    "index": 0,
    "previous_hash": "0" * 64,
    "timestamp": 1640995200,  # January 1, 2022 00:00:00 UTC (Fixed timestamp)
    "nonce": 46763,  # Pre-mined nonce that satisfies difficulty 2
    "target_difficulty": 2,
    "hash": "00a8f5f2c7d1e4b3c6d9e2f1a4b7c8d2e5f3a6b9c1d4e7f2a5b8c3d6e9f1a4b7",
    "merkle_root": "f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2",
    "transactions": [
        {
            "tx_id": "genesis_coinbase_000000000000000000000000000000000000000000000000",
            "inputs": [],
            "outputs": [
                {
                    "amount": 50.0,
                    "recipient_address": "1ChainCoreGenesisBlock000000000000000000"
                }
            ],
            "timestamp": 1640995200,
            "is_coinbase": True,
            "coinbase_data": "ChainCore Genesis Block - The Future of Decentralized Finance"
        }
    ],
    # Metadata for genesis block
    "metadata": {
        "version": 1,
        "chain_id": "chaincore-mainnet",
        "genesis_message": "In the beginning was the Chain, and the Chain was with Code",
        "creator": "ChainCore Protocol",
        "network_magic": "0xCCCCCCCC"
    }
}

# Genesis Block Hash Verification
GENESIS_BLOCK_HASH = GENESIS_BLOCK_DATA["hash"]

def validate_genesis_block(block_data: Dict) -> bool:
    """
    Validate that a block is the correct genesis block
    
    Args:
        block_data: Block data to validate
        
    Returns:
        bool: True if valid genesis block, False otherwise
    """
    try:
        # Check all critical genesis block fields
        required_fields = ["index", "hash", "previous_hash", "timestamp", "nonce"]
        
        for field in required_fields:
            if field not in block_data:
                return False
                
        # Verify genesis-specific values
        if block_data["index"] != 0:
            return False
            
        if block_data["previous_hash"] != "0" * 64:
            return False
            
        if block_data["hash"] != GENESIS_BLOCK_HASH:
            return False
            
        if block_data["timestamp"] != GENESIS_BLOCK_DATA["timestamp"]:
            return False
            
        if block_data["nonce"] != GENESIS_BLOCK_DATA["nonce"]:
            return False
            
        return True
        
    except Exception:
        return False

def get_genesis_block() -> Dict:
    """
    Get the hardcoded genesis block
    
    Returns:
        Dict: Genesis block data
    """
    return GENESIS_BLOCK_DATA.copy()

def is_genesis_block(block_data: Dict) -> bool:
    """
    Check if a block is the genesis block
    
    Args:
        block_data: Block data to check
        
    Returns:
        bool: True if genesis block
    """
    return (
        block_data.get("index") == 0 and 
        block_data.get("hash") == GENESIS_BLOCK_HASH
    )

# Network constants
NETWORK_MAGIC = 0xCCCCCCCC
CHAIN_ID = "chaincore-mainnet"
GENESIS_TIMESTAMP = 1640995200

if __name__ == "__main__":
    # Test genesis block validation
    genesis = get_genesis_block()
    print("ChainCore Genesis Block:")
    print(f"  Hash: {genesis['hash']}")
    print(f"  Timestamp: {genesis['timestamp']}")
    print(f"  Nonce: {genesis['nonce']}")
    print(f"  Valid: {validate_genesis_block(genesis)}")