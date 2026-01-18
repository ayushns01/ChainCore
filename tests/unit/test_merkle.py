"""
Tests for Merkle Tree implementation.
Tests tree construction, root calculation, and proof verification.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.block import Block
from src.core.bitcoin_transaction import Transaction
from src.crypto.ecdsa_crypto import double_sha256


class TestMerkleRootCalculation:
    """Test Merkle root computation"""
    
    def test_single_transaction_merkle(self):
        """Single tx merkle root equals tx hash"""
        tx = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        block = Block(index=1, transactions=[tx], previous_hash="0" * 64)
        
        assert block.merkle_root == tx.tx_id
        
    def test_two_transaction_merkle(self):
        """Two tx merkle root is hash of concatenated hashes"""
        tx1 = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        tx2 = Transaction()
        tx2.add_output(10.0, "alice")
        
        block = Block(index=1, transactions=[tx1, tx2], previous_hash="0" * 64)
        
        expected = double_sha256(tx1.tx_id + tx2.tx_id)
        assert block.merkle_root == expected
        
    def test_four_transaction_merkle(self):
        """Four tx builds balanced tree"""
        txs = []
        for i in range(4):
            tx = Transaction()
            tx.timestamp = 1000 + i
            tx.add_output(float(i), f"addr_{i}")
            txs.append(tx)
            
        block = Block(index=1, transactions=txs, previous_hash="0" * 64)
        
        # Level 1: hash pairs
        h01 = double_sha256(txs[0].tx_id + txs[1].tx_id)
        h23 = double_sha256(txs[2].tx_id + txs[3].tx_id)
        
        # Level 2 (root): hash of level 1
        expected_root = double_sha256(h01 + h23)
        
        assert block.merkle_root == expected_root
        
    def test_odd_transaction_count(self):
        """Odd tx count duplicates last hash"""
        txs = []
        for i in range(3):
            tx = Transaction()
            tx.timestamp = 1000 + i
            tx.add_output(float(i), f"addr_{i}")
            txs.append(tx)
            
        block = Block(index=1, transactions=txs, previous_hash="0" * 64)
        
        # Level 1: tx2 duplicated
        h01 = double_sha256(txs[0].tx_id + txs[1].tx_id)
        h22 = double_sha256(txs[2].tx_id + txs[2].tx_id)  # Duplicated
        
        expected_root = double_sha256(h01 + h22)
        
        assert block.merkle_root == expected_root
        
    def test_empty_transaction_merkle(self):
        """Empty tx list produces zero hash"""
        block = Block(index=0, transactions=[], previous_hash="0" * 64)
        
        assert block.merkle_root == "0" * 64


class TestMerkleRootProperties:
    """Test properties of Merkle roots"""
    
    def test_merkle_root_deterministic(self):
        """Same transactions always produce same root"""
        tx = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        block1 = Block(index=1, transactions=[tx], previous_hash="0" * 64, timestamp=1000)
        block2 = Block(index=1, transactions=[tx], previous_hash="0" * 64, timestamp=1000)
        
        assert block1.merkle_root == block2.merkle_root
        
    def test_merkle_root_format(self):
        """Merkle root is 64 hex characters"""
        tx = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        block = Block(index=1, transactions=[tx], previous_hash="0" * 64)
        
        assert len(block.merkle_root) == 64
        assert all(c in '0123456789abcdef' for c in block.merkle_root)
        
    def test_different_tx_order_different_root(self):
        """Transaction order affects merkle root"""
        tx1 = Transaction()
        tx1.timestamp = 1000
        tx1.add_output(10.0, "alice")
        
        tx2 = Transaction()
        tx2.timestamp = 2000
        tx2.add_output(20.0, "bob")
        
        block1 = Block(index=1, transactions=[tx1, tx2], previous_hash="0" * 64)
        block2 = Block(index=1, transactions=[tx2, tx1], previous_hash="0" * 64)
        
        assert block1.merkle_root != block2.merkle_root
        
    def test_modified_tx_changes_root(self):
        """Modifying any transaction changes root"""
        tx1 = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        tx2 = Transaction.create_coinbase_transaction("miner", 51.0, 1)  # Different amount
        
        block1 = Block(index=1, transactions=[tx1], previous_hash="0" * 64)
        block2 = Block(index=1, transactions=[tx2], previous_hash="0" * 64)
        
        assert block1.merkle_root != block2.merkle_root


class TestMerkleTreeStructure:
    """Test Merkle tree structure for different sizes"""
    
    def test_power_of_two_transactions(self):
        """2^n transactions form perfect binary tree"""
        for n in [1, 2, 4, 8]:
            txs = []
            for i in range(n):
                tx = Transaction()
                tx.timestamp = i
                tx.add_output(float(i), f"addr_{i}")
                txs.append(tx)
                
            block = Block(index=1, transactions=txs, previous_hash="0" * 64)
            
            assert len(block.merkle_root) == 64
            
    def test_non_power_of_two(self):
        """Non 2^n transactions handled correctly"""
        for n in [3, 5, 7, 9]:
            txs = []
            for i in range(n):
                tx = Transaction()
                tx.timestamp = i
                tx.add_output(float(i), f"addr_{i}")
                txs.append(tx)
                
            block = Block(index=1, transactions=txs, previous_hash="0" * 64)
            
            assert len(block.merkle_root) == 64


class TestMerkleRootInBlock:
    """Test Merkle root integration in block"""
    
    def test_merkle_root_in_block_hash(self):
        """Merkle root affects block hash"""
        tx1 = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        tx2 = Transaction.create_coinbase_transaction("miner", 25.0, 1)
        
        block1 = Block(index=1, transactions=[tx1], previous_hash="0" * 64, timestamp=1000, nonce=0)
        block2 = Block(index=1, transactions=[tx2], previous_hash="0" * 64, timestamp=1000, nonce=0)
        
        # Different merkle roots lead to different block hashes
        assert block1.merkle_root != block2.merkle_root
        assert block1.hash != block2.hash
        
    def test_merkle_root_stored_in_block(self):
        """Block stores computed merkle root"""
        tx = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        block = Block(index=1, transactions=[tx], previous_hash="0" * 64)
        
        assert hasattr(block, 'merkle_root')
        assert block.merkle_root is not None
        
    def test_merkle_root_in_serialization(self):
        """Merkle root included in block serialization"""
        tx = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        block = Block(index=1, transactions=[tx], previous_hash="0" * 64)
        
        data = block.to_dict()
        
        assert 'merkle_root' in data
        assert data['merkle_root'] == block.merkle_root
