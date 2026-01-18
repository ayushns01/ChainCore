"""
Unit tests for Block class.

Tests cover:
- Block creation and field validation
- Merkle root calculation
- Proof-of-work validation
- Hash computation and verification
- Block serialization/deserialization
"""
import pytest
import json
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.block import Block
from src.core.bitcoin_transaction import Transaction, TransactionInput, TransactionOutput
from src.crypto.ecdsa_crypto import double_sha256


class TestBlockCreation:
    """Test block instantiation and field initialization"""
    
    def test_block_basic_creation(self):
        """Create a basic block with required fields"""
        coinbase = Transaction.create_coinbase_transaction("miner_address", 50.0, 1)
        
        block = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64,
            target_difficulty=1
        )
        
        assert block.index == 1
        assert block.previous_hash == "0" * 64
        assert len(block.transactions) == 1
        assert block.target_difficulty == 1
        
    def test_block_auto_calculates_hash(self):
        """Block hash should be calculated automatically"""
        coinbase = Transaction.create_coinbase_transaction("miner_address", 50.0, 1)
        
        block = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64
        )
        
        assert block.hash is not None
        assert len(block.hash) == 64
        
    def test_block_auto_calculates_merkle_root(self):
        """Merkle root should be calculated from transactions"""
        coinbase = Transaction.create_coinbase_transaction("miner_address", 50.0, 1)
        
        block = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64
        )
        
        assert block.merkle_root is not None
        assert len(block.merkle_root) == 64
        
    def test_block_timestamp_auto_generated(self):
        """Timestamp should be set automatically if not provided"""
        coinbase = Transaction.create_coinbase_transaction("miner_address", 50.0, 1)
        before = time.time()
        
        block = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64
        )
        
        after = time.time()
        assert before <= block.timestamp <= after
        
    def test_block_custom_timestamp(self):
        """Custom timestamp should be respected"""
        coinbase = Transaction.create_coinbase_transaction("miner_address", 50.0, 1)
        custom_time = 1609459200.0  # 2021-01-01 00:00:00 UTC
        
        block = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64,
            timestamp=custom_time
        )
        
        assert block.timestamp == custom_time


class TestMerkleRoot:
    """Test Merkle tree root calculation"""
    
    def test_merkle_root_single_tx(self):
        """Merkle root with single transaction"""
        tx = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        block = Block(index=1, transactions=[tx], previous_hash="0" * 64)
        
        # Single tx merkle root should be tx hash
        assert block.merkle_root == tx.tx_id
        
    def test_merkle_root_two_tx(self):
        """Merkle root with two transactions"""
        tx1 = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        tx2 = Transaction()
        tx2.add_output(10.0, "alice")
        
        block = Block(index=1, transactions=[tx1, tx2], previous_hash="0" * 64)
        
        # Merkle root should be hash of combined tx hashes
        expected = double_sha256(tx1.tx_id + tx2.tx_id)
        assert block.merkle_root == expected
        
    def test_merkle_root_odd_transactions(self):
        """Merkle root with odd number of transactions (requires duplication)"""
        tx1 = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        tx2 = Transaction()
        tx2.add_output(10.0, "alice")
        tx3 = Transaction()
        tx3.add_output(20.0, "bob")
        
        block = Block(index=1, transactions=[tx1, tx2, tx3], previous_hash="0" * 64)
        
        # Should handle odd count by duplicating last hash
        assert block.merkle_root is not None
        assert len(block.merkle_root) == 64
        
    def test_merkle_root_empty_transactions(self):
        """Merkle root with no transactions"""
        block = Block(index=0, transactions=[], previous_hash="0" * 64)
        
        # Empty merkle root should be zeros
        assert block.merkle_root == "0" * 64
        
    def test_merkle_root_deterministic(self):
        """Same transactions should produce same merkle root"""
        tx = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        block1 = Block(index=1, transactions=[tx], previous_hash="0" * 64, timestamp=1000)
        block2 = Block(index=1, transactions=[tx], previous_hash="0" * 64, timestamp=1000)
        
        assert block1.merkle_root == block2.merkle_root


class TestProofOfWork:
    """Test proof-of-work validation"""
    
    def test_valid_hash_difficulty_1(self):
        """Block hash starting with one zero is valid for difficulty 1"""
        coinbase = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        # Create block with easy difficulty
        block = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64,
            target_difficulty=1
        )
        
        # Mine the block (find valid nonce)
        while not block.hash.startswith("0"):
            block.nonce += 1
            block.hash = block._calculate_hash()
            
        assert block.is_valid_hash() is True
        
    def test_invalid_hash_insufficient_zeros(self):
        """Block hash not meeting difficulty should be invalid"""
        coinbase = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        block = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64,
            target_difficulty=4  # Requires 4 leading zeros
        )
        
        # Without mining, hash likely won't meet difficulty
        # Force a non-compliant hash for testing
        block.hash = "1" + "0" * 63  # Doesn't start with zeros
        
        assert block.is_valid_hash() is False
        
    def test_calculate_block_work(self):
        """Work calculation should scale with difficulty"""
        coinbase = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        block1 = Block(index=1, transactions=[coinbase], previous_hash="0" * 64, target_difficulty=1)
        block2 = Block(index=1, transactions=[coinbase], previous_hash="0" * 64, target_difficulty=2)
        
        # Higher difficulty = exponentially more work
        assert block2.calculate_block_work() > block1.calculate_block_work()
        assert block2.calculate_block_work() == 2 * block1.calculate_block_work()


class TestBlockHash:
    """Test block hash computation"""
    
    def test_hash_deterministic(self):
        """Same block data should always produce same hash"""
        coinbase = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        block1 = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64,
            timestamp=1000,
            nonce=42
        )
        
        block2 = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64,
            timestamp=1000,
            nonce=42
        )
        
        assert block1.hash == block2.hash
        
    def test_hash_changes_with_nonce(self):
        """Different nonce should produce different hash"""
        coinbase = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        block1 = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64,
            timestamp=1000,
            nonce=1
        )
        
        block2 = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64,
            timestamp=1000,
            nonce=2
        )
        
        assert block1.hash != block2.hash
        
    def test_hash_changes_with_previous_hash(self):
        """Different previous_hash should produce different block hash"""
        coinbase = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        block1 = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64,
            timestamp=1000
        )
        
        block2 = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="a" * 64,
            timestamp=1000
        )
        
        assert block1.hash != block2.hash
        
    def test_hash_changes_with_timestamp(self):
        """Different timestamp should produce different hash"""
        coinbase = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        block1 = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64,
            timestamp=1000
        )
        
        block2 = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64,
            timestamp=2000
        )
        
        assert block1.hash != block2.hash


class TestBlockSerialization:
    """Test block serialization and deserialization"""
    
    def test_to_dict_contains_all_fields(self):
        """to_dict should include all essential fields"""
        coinbase = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        block = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64
        )
        
        data = block.to_dict()
        
        assert 'index' in data
        assert 'hash' in data
        assert 'previous_hash' in data
        assert 'merkle_root' in data
        assert 'timestamp' in data
        assert 'nonce' in data
        assert 'transactions' in data
        
    def test_serialization_roundtrip(self):
        """Block should survive serialization/deserialization"""
        coinbase = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        original = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64,
            timestamp=1000,
            nonce=42
        )
        
        # Serialize to dict
        data = original.to_dict()
        
        # Deserialize
        restored = Block.from_dict(data)
        
        assert restored.index == original.index
        assert restored.hash == original.hash
        assert restored.previous_hash == original.previous_hash
        assert restored.merkle_root == original.merkle_root
        
    def test_json_serialization(self):
        """Block should be JSON-serializable"""
        coinbase = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        block = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64
        )
        
        # Should not raise
        json_str = json.dumps(block.to_dict())
        restored_data = json.loads(json_str)
        
        assert restored_data['index'] == 1


class TestBlockMetadata:
    """Test block metadata and computed properties"""
    
    def test_transaction_count(self):
        """Transaction count should match actual count"""
        tx1 = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        tx2 = Transaction()
        tx2.add_output(10.0, "alice")
        
        block = Block(
            index=1,
            transactions=[tx1, tx2],
            previous_hash="0" * 64
        )
        
        assert block.transaction_count == 2
        
    def test_block_size_estimation(self):
        """Block size should be estimated"""
        coinbase = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        block = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64
        )
        
        # Should have some positive size
        assert block.block_size > 0
        # Base header + at least one transaction
        assert block.block_size >= 80  # Minimum header size
        
    def test_block_version(self):
        """Block should have version number"""
        coinbase = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        block = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64,
            version=2
        )
        
        assert block.version == 2


class TestGenesisBlock:
    """Test genesis block special cases"""
    
    def test_genesis_block_index_zero(self):
        """Genesis block should have index 0"""
        coinbase = Transaction.create_coinbase_transaction("genesis_miner", 50.0, 0)
        
        genesis = Block(
            index=0,
            transactions=[coinbase],
            previous_hash="0" * 64
        )
        
        assert genesis.index == 0
        
    def test_genesis_block_has_null_previous_hash(self):
        """Genesis block previous_hash should be zeros"""
        coinbase = Transaction.create_coinbase_transaction("genesis_miner", 50.0, 0)
        
        genesis = Block(
            index=0,
            transactions=[coinbase],
            previous_hash="0" * 64
        )
        
        assert genesis.previous_hash == "0" * 64


class TestBlockValidation:
    """Test block validation logic"""
    
    def test_validate_proof_of_work(self):
        """Valid proof-of-work should pass validation"""
        coinbase = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        block = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64,
            target_difficulty=1
        )
        
        # Mine until valid
        while not block.is_valid_hash():
            block.nonce += 1
            block.hash = block._calculate_hash()
            
        assert block.validate_proof_of_work() is True
        
    def test_recalculate_hash_matches(self):
        """Recalculated hash should match stored hash"""
        coinbase = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        block = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64,
            timestamp=1000,
            nonce=42
        )
        
        stored_hash = block.hash
        recalculated = block._calculate_hash()
        
        assert stored_hash == recalculated
