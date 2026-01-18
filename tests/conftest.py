"""
Pytest fixtures and test configuration for ChainCore test suite.
"""
import pytest
import sys
import os
import tempfile
import json
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crypto.ecdsa_crypto import ECDSAKeyPair
from src.core.bitcoin_transaction import Transaction, TransactionInput, TransactionOutput
from src.core.block import Block


# ============================================================================
# Cryptographic Fixtures
# ============================================================================

@pytest.fixture
def keypair():
    """Generate a fresh ECDSA keypair for testing"""
    return ECDSAKeyPair()


@pytest.fixture
def alice_keypair():
    """Fixed keypair for Alice (deterministic tests)"""
    return ECDSAKeyPair()


@pytest.fixture
def bob_keypair():
    """Fixed keypair for Bob (deterministic tests)"""
    return ECDSAKeyPair()


@pytest.fixture
def miner_keypair():
    """Fixed keypair for miner (deterministic tests)"""
    return ECDSAKeyPair()


# ============================================================================
# Transaction Fixtures
# ============================================================================

@pytest.fixture
def coinbase_tx(miner_keypair):
    """Create a valid coinbase transaction"""
    return Transaction.create_coinbase_transaction(miner_keypair.address, 50.0, block_height=1)


@pytest.fixture
def sample_utxo_set(coinbase_tx, miner_keypair):
    """Create a sample UTXO set with one spendable output"""
    utxo_set = {}
    for i, output in enumerate(coinbase_tx.outputs):
        utxo_key = f"{coinbase_tx.tx_id}:{i}"
        utxo_set[utxo_key] = {
            'amount': output.amount,
            'recipient_address': output.recipient_address,
            'tx_id': coinbase_tx.tx_id,
            'output_index': i
        }
    return utxo_set


@pytest.fixture
def simple_transaction(coinbase_tx, miner_keypair, alice_keypair):
    """Create a simple P2P transaction"""
    tx = Transaction()
    tx.add_input(coinbase_tx.tx_id, 0)
    tx.add_output(40.0, alice_keypair.address)  # Send 40 to Alice
    tx.add_output(9.5, miner_keypair.address)   # Change back to miner (0.5 fee)
    tx.sign_input(0, miner_keypair)
    return tx


# ============================================================================
# Block Fixtures
# ============================================================================

@pytest.fixture
def genesis_block():
    """Create a genesis block for testing"""
    coinbase = Transaction.create_coinbase_transaction("genesis_address", 50.0, block_height=0)
    return Block(
        index=0,
        transactions=[coinbase],
        previous_hash="0" * 64,
        timestamp=1609459200.0,  # Fixed timestamp for determinism
        target_difficulty=1  # Easy difficulty for tests
    )


@pytest.fixture
def sample_block(genesis_block, coinbase_tx):
    """Create a sample block following genesis"""
    return Block(
        index=1,
        transactions=[coinbase_tx],
        previous_hash=genesis_block.hash,
        target_difficulty=1
    )


# ============================================================================
# Database Fixtures (with cleanup)
# ============================================================================

@pytest.fixture
def temp_db_path():
    """Create a temporary database path"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        path = f.name
    yield path
    # Cleanup
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def mock_utxo_set():
    """Create a mock UTXO set for transaction validation tests"""
    return {
        "0" * 64 + ":0": {
            "amount": 100.0,
            "recipient_address": "test_address_1",
            "tx_id": "0" * 64,
            "output_index": 0
        },
        "a" * 64 + ":0": {
            "amount": 50.0,
            "recipient_address": "test_address_2",
            "tx_id": "a" * 64,
            "output_index": 0
        }
    }


# ============================================================================
# Network Test Fixtures
# ============================================================================

@pytest.fixture
def mock_peer_list():
    """Create mock peer list for network tests"""
    return [
        {"host": "127.0.0.1", "port": 5001, "node_id": "node_1"},
        {"host": "127.0.0.1", "port": 5002, "node_id": "node_2"},
        {"host": "127.0.0.1", "port": 5003, "node_id": "node_3"},
    ]


# ============================================================================
# Test Markers
# ============================================================================

def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "crypto: marks cryptography-related tests")
    config.addinivalue_line("markers", "concurrency: marks concurrency/threading tests")
    config.addinivalue_line("markers", "network: marks network-related tests")
