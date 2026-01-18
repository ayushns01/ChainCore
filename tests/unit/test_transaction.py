"""
Unit tests for Transaction model (UTXO-based).

Tests cover:
- Transaction creation and structure
- UTXO input/output handling
- Coinbase transaction special cases
- Transaction signing and verification
- Fee calculation
- Serialization/deserialization
"""
import pytest
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.bitcoin_transaction import Transaction, TransactionInput, TransactionOutput
from src.crypto.ecdsa_crypto import ECDSAKeyPair


class TestTransactionInput:
    """Test TransactionInput class"""
    
    def test_input_creation(self):
        """Create a basic transaction input"""
        tx_input = TransactionInput(
            tx_id="a" * 64,
            output_index=0
        )
        
        assert tx_input.tx_id == "a" * 64
        assert tx_input.output_index == 0
        assert tx_input.signature == {}
        
    def test_input_with_signature(self):
        """Create input with pre-existing signature"""
        sig = {"signature": "abc123", "public_key": "def456"}
        
        tx_input = TransactionInput(
            tx_id="a" * 64,
            output_index=0,
            signature=sig
        )
        
        assert tx_input.signature == sig
        
    def test_input_to_dict(self):
        """Serialize input to dictionary"""
        tx_input = TransactionInput(
            tx_id="a" * 64,
            output_index=1
        )
        
        data = tx_input.to_dict()
        
        assert data['tx_id'] == "a" * 64
        assert data['output_index'] == 1
        
    def test_input_from_dict(self):
        """Deserialize input from dictionary"""
        data = {
            'tx_id': "b" * 64,
            'output_index': 2,
            'signature': {},
            'script_sig': ""
        }
        
        tx_input = TransactionInput.from_dict(data)
        
        assert tx_input.tx_id == "b" * 64
        assert tx_input.output_index == 2


class TestTransactionOutput:
    """Test TransactionOutput class"""
    
    def test_output_creation(self):
        """Create a basic transaction output"""
        tx_output = TransactionOutput(
            amount=10.5,
            recipient_address="recipient_addr"
        )
        
        assert tx_output.amount == 10.5
        assert tx_output.recipient_address == "recipient_addr"
        
    def test_output_to_dict(self):
        """Serialize output to dictionary"""
        tx_output = TransactionOutput(
            amount=25.0,
            recipient_address="alice"
        )
        
        data = tx_output.to_dict()
        
        assert data['amount'] == 25.0
        assert data['recipient_address'] == "alice"
        
    def test_output_from_dict(self):
        """Deserialize output from dictionary"""
        data = {
            'amount': 100.0,
            'recipient_address': "bob",
            'script_pubkey': ""
        }
        
        tx_output = TransactionOutput.from_dict(data)
        
        assert tx_output.amount == 100.0
        assert tx_output.recipient_address == "bob"


class TestTransactionCreation:
    """Test Transaction creation and basic operations"""
    
    def test_empty_transaction(self):
        """Create an empty transaction"""
        tx = Transaction()
        
        assert tx.inputs == []
        assert tx.outputs == []
        assert tx.tx_id is not None
        
    def test_add_input(self):
        """Add input to transaction"""
        tx = Transaction()
        
        tx.add_input("a" * 64, 0)
        
        assert len(tx.inputs) == 1
        assert tx.inputs[0].tx_id == "a" * 64
        assert tx.inputs[0].output_index == 0
        
    def test_add_output(self):
        """Add output to transaction"""
        tx = Transaction()
        
        tx.add_output(50.0, "recipient")
        
        assert len(tx.outputs) == 1
        assert tx.outputs[0].amount == 50.0
        assert tx.outputs[0].recipient_address == "recipient"
        
    def test_multiple_inputs_outputs(self):
        """Transaction with multiple inputs and outputs"""
        tx = Transaction()
        
        tx.add_input("a" * 64, 0)
        tx.add_input("b" * 64, 1)
        tx.add_output(30.0, "alice")
        tx.add_output(20.0, "bob")
        
        assert len(tx.inputs) == 2
        assert len(tx.outputs) == 2
        
    def test_tx_id_recalculates_on_modification(self):
        """TX ID should update when transaction is modified"""
        tx = Transaction()
        original_id = tx.tx_id
        
        tx.add_output(10.0, "alice")
        
        assert tx.tx_id != original_id


class TestCoinbaseTransaction:
    """Test coinbase (mining reward) transactions"""
    
    def test_create_coinbase_transaction(self):
        """Create a coinbase transaction"""
        tx = Transaction.create_coinbase_transaction(
            miner_address="miner_wallet",
            reward=50.0,
            block_height=1
        )
        
        assert tx.is_coinbase() is True
        assert len(tx.outputs) >= 1
        assert tx.outputs[0].amount == 50.0
        assert tx.outputs[0].recipient_address == "miner_wallet"
        
    def test_coinbase_special_input(self):
        """Coinbase has special null input"""
        tx = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        assert len(tx.inputs) == 1
        assert tx.inputs[0].tx_id == "0" * 64
        assert tx.inputs[0].output_index == 0xFFFFFFFF
        
    def test_is_coinbase_false_for_regular_tx(self):
        """Regular transaction is not coinbase"""
        tx = Transaction()
        tx.add_input("a" * 64, 0)
        tx.add_output(10.0, "bob")
        
        assert tx.is_coinbase() is False
        
    def test_coinbase_at_different_heights(self):
        """Coinbase transactions at different heights are different"""
        tx1 = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        tx2 = Transaction.create_coinbase_transaction("miner", 50.0, 2)
        
        # Different block heights should produce different tx_ids
        assert tx1.tx_id != tx2.tx_id


class TestTransactionSigning:
    """Test ECDSA transaction signing"""
    
    def test_sign_input(self):
        """Sign a transaction input"""
        keypair = ECDSAKeyPair()
        tx = Transaction()
        tx.add_input("a" * 64, 0)
        tx.add_output(10.0, "bob")
        
        tx.sign_input(0, keypair)
        
        assert tx.inputs[0].signature != {}
        assert 'signature' in tx.inputs[0].signature
        assert 'public_key' in tx.inputs[0].signature
        
    def test_sign_multiple_inputs(self):
        """Sign multiple inputs with same keypair"""
        keypair = ECDSAKeyPair()
        tx = Transaction()
        tx.add_input("a" * 64, 0)
        tx.add_input("b" * 64, 1)
        tx.add_output(20.0, "bob")
        
        tx.sign_input(0, keypair)
        tx.sign_input(1, keypair)
        
        assert tx.inputs[0].signature != {}
        assert tx.inputs[1].signature != {}
        
    def test_sign_with_different_keypairs(self):
        """Sign different inputs with different keypairs"""
        alice = ECDSAKeyPair()
        bob = ECDSAKeyPair()
        
        tx = Transaction()
        tx.add_input("a" * 64, 0)  # Alice's UTXO
        tx.add_input("b" * 64, 0)  # Bob's UTXO
        tx.add_output(30.0, "charlie")
        
        tx.sign_input(0, alice)
        tx.sign_input(1, bob)
        
        # Different public keys in signatures
        assert tx.inputs[0].signature['public_key'] != tx.inputs[1].signature['public_key']
        
    def test_sign_invalid_input_index(self):
        """Signing non-existent input should raise error"""
        keypair = ECDSAKeyPair()
        tx = Transaction()
        tx.add_input("a" * 64, 0)
        
        with pytest.raises(ValueError):
            tx.sign_input(5, keypair)  # Index out of range


class TestTransactionValues:
    """Test transaction value calculations"""
    
    def test_get_total_output_value(self):
        """Calculate total output value"""
        tx = Transaction()
        tx.add_output(30.0, "alice")
        tx.add_output(20.0, "bob")
        tx.add_output(5.0, "charlie")
        
        assert tx.get_total_output_value() == 55.0
        
    def test_get_total_input_value(self):
        """Calculate total input value from UTXO set"""
        tx = Transaction()
        tx.add_input("a" * 64, 0)
        tx.add_input("b" * 64, 0)
        
        utxo_set = {
            "a" * 64 + ":0": {"amount": 50.0, "recipient_address": "alice"},
            "b" * 64 + ":0": {"amount": 30.0, "recipient_address": "bob"},
        }
        
        assert tx.get_total_input_value(utxo_set) == 80.0
        
    def test_get_fee(self):
        """Calculate transaction fee"""
        tx = Transaction()
        tx.add_input("a" * 64, 0)
        tx.add_output(45.0, "bob")  # Spending 45 of 50
        
        utxo_set = {
            "a" * 64 + ":0": {"amount": 50.0, "recipient_address": "alice"},
        }
        
        assert tx.get_fee(utxo_set) == 5.0  # 50 - 45 = 5 fee
        
    def test_coinbase_fee_is_zero(self):
        """Coinbase transactions have no fee"""
        tx = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        assert tx.get_fee({}) == 0.0
        
    def test_missing_utxo_returns_zero(self):
        """Missing UTXO should contribute 0 to input value"""
        tx = Transaction()
        tx.add_input("missing" * 8, 0)
        
        utxo_set = {}  # Empty - UTXO not found
        
        assert tx.get_total_input_value(utxo_set) == 0.0


class TestTransactionSerialization:
    """Test transaction serialization/deserialization"""
    
    def test_to_dict_structure(self):
        """to_dict should include all fields"""
        tx = Transaction()
        tx.add_input("a" * 64, 0)
        tx.add_output(10.0, "bob")
        
        data = tx.to_dict()
        
        assert 'tx_id' in data
        assert 'version' in data
        assert 'inputs' in data
        assert 'outputs' in data
        assert 'timestamp' in data
        
    def test_serialization_roundtrip(self):
        """Transaction should survive serialization/deserialization"""
        original = Transaction()
        original.add_input("a" * 64, 0)
        original.add_output(25.0, "alice")
        
        data = original.to_dict()
        restored = Transaction.from_dict(data)
        
        assert restored.tx_id == original.tx_id
        assert len(restored.inputs) == len(original.inputs)
        assert len(restored.outputs) == len(original.outputs)
        assert restored.outputs[0].amount == 25.0
        
    def test_json_serialization(self):
        """Transaction should be JSON-serializable"""
        tx = Transaction()
        tx.add_input("a" * 64, 0)
        tx.add_output(10.0, "bob")
        
        # Should not raise
        json_str = json.dumps(tx.to_dict())
        restored_data = json.loads(json_str)
        
        assert restored_data['tx_id'] == tx.tx_id
        
    def test_coinbase_serialization_roundtrip(self):
        """Coinbase transaction should survive roundtrip"""
        original = Transaction.create_coinbase_transaction("miner", 50.0, 100)
        
        data = original.to_dict()
        restored = Transaction.from_dict(data)
        
        assert restored.is_coinbase() is True
        assert restored.tx_id == original.tx_id


class TestTransactionHash:
    """Test transaction hashing behavior"""
    
    def test_hash_deterministic(self):
        """Same transaction data should produce same hash"""
        tx1 = Transaction()
        tx1.timestamp = 1000  # Fix timestamp
        tx1.add_input("a" * 64, 0)
        tx1.add_output(10.0, "bob")
        
        tx2 = Transaction()
        tx2.timestamp = 1000
        tx2.add_input("a" * 64, 0)
        tx2.add_output(10.0, "bob")
        
        # Force recalculation
        tx1.tx_id = tx1._calculate_hash()
        tx2.tx_id = tx2._calculate_hash()
        
        assert tx1.tx_id == tx2.tx_id
        
    def test_hash_changes_with_amount(self):
        """Different amounts should produce different hashes"""
        tx1 = Transaction()
        tx1.timestamp = 1000
        tx1.add_output(10.0, "bob")
        
        tx2 = Transaction()
        tx2.timestamp = 1000
        tx2.add_output(20.0, "bob")
        
        assert tx1.tx_id != tx2.tx_id
        
    def test_hash_format(self):
        """TX hash should be 64 character hex string"""
        tx = Transaction()
        tx.add_output(10.0, "bob")
        
        assert len(tx.tx_id) == 64
        assert all(c in '0123456789abcdef' for c in tx.tx_id)


class TestTransactionSize:
    """Test transaction size calculations"""
    
    def test_get_size_positive(self):
        """Transaction size should be positive"""
        tx = Transaction()
        tx.add_input("a" * 64, 0)
        tx.add_output(10.0, "bob")
        
        assert tx.get_size() > 0
        
    def test_size_increases_with_outputs(self):
        """More outputs should increase size"""
        tx1 = Transaction()
        tx1.add_output(10.0, "bob")
        
        tx2 = Transaction()
        tx2.add_output(10.0, "bob")
        tx2.add_output(20.0, "alice")
        tx2.add_output(30.0, "charlie")
        
        assert tx2.get_size() > tx1.get_size()


class TestTransactionEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_zero_amount_output(self):
        """Zero amount output (dust)"""
        tx = Transaction()
        tx.add_output(0.0, "bob")
        
        assert tx.outputs[0].amount == 0.0
        
    def test_very_small_amount(self):
        """Very small satoshi-level amounts"""
        tx = Transaction()
        tx.add_output(0.00000001, "bob")  # 1 satoshi
        
        assert tx.outputs[0].amount == 0.00000001
        
    def test_large_amount(self):
        """Large amount transaction"""
        tx = Transaction()
        tx.add_output(21_000_000.0, "whale")  # Max Bitcoin supply
        
        assert tx.outputs[0].amount == 21_000_000.0
        
    def test_empty_recipient_address(self):
        """Empty recipient address (burn address)"""
        tx = Transaction()
        tx.add_output(10.0, "")
        
        assert tx.outputs[0].recipient_address == ""
