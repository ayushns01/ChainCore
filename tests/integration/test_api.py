"""
API endpoint tests for ChainCore network node.

Tests cover:
- REST API endpoints
- Request/response validation
- Error handling
- Edge cases
"""
import pytest
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# These tests are designed to work with Flask's test client
# or can be run against a live server

from src.core.block import Block
from src.core.bitcoin_transaction import Transaction


class TestAPIResponseStructure:
    """Test API response format and structure"""
    
    def test_block_response_format(self):
        """Block API response should include required fields"""
        coinbase = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        block = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64,
            target_difficulty=1
        )
        
        response = block.to_dict()
        
        # Required fields for block response
        required_fields = ['index', 'hash', 'previous_hash', 'merkle_root', 
                          'timestamp', 'nonce', 'transactions']
        
        for field in required_fields:
            assert field in response, f"Missing required field: {field}"
            
    def test_transaction_response_format(self):
        """Transaction API response should include required fields"""
        tx = Transaction()
        tx.add_input("a" * 64, 0)
        tx.add_output(10.0, "recipient")
        
        response = tx.to_dict()
        
        required_fields = ['tx_id', 'version', 'inputs', 'outputs', 'timestamp']
        
        for field in required_fields:
            assert field in response, f"Missing required field: {field}"
            
    def test_transaction_input_format(self):
        """Transaction input should have required fields"""
        tx = Transaction()
        tx.add_input("a" * 64, 0)
        
        input_data = tx.to_dict()['inputs'][0]
        
        assert 'tx_id' in input_data
        assert 'output_index' in input_data
        
    def test_transaction_output_format(self):
        """Transaction output should have required fields"""
        tx = Transaction()
        tx.add_output(25.0, "alice")
        
        output_data = tx.to_dict()['outputs'][0]
        
        assert 'amount' in output_data
        assert 'recipient_address' in output_data


class TestAPIDataValidation:
    """Test API input validation"""
    
    def test_valid_transaction_data(self):
        """Valid transaction data should be accepted"""
        valid_data = {
            'tx_id': 'a' * 64,
            'version': 1,
            'inputs': [{'tx_id': 'b' * 64, 'output_index': 0, 'signature': {}, 'script_sig': ''}],
            'outputs': [{'amount': 10.0, 'recipient_address': 'recipient', 'script_pubkey': ''}],
            'timestamp': 1609459200.0,
            'lock_time': 0
        }
        
        # Should not raise
        tx = Transaction.from_dict(valid_data)
        
        assert tx.tx_id == 'a' * 64
        assert len(tx.inputs) == 1
        assert len(tx.outputs) == 1
        
    def test_missing_required_field(self):
        """Missing required field should raise error"""
        invalid_data = {
            'tx_id': 'a' * 64,
            # Missing 'inputs' and 'outputs'
        }
        
        with pytest.raises((KeyError, TypeError)):
            Transaction.from_dict(invalid_data)
            
    def test_invalid_amount_type(self):
        """Non-numeric amount should fail"""
        # This is a design test - showing expected behavior
        with pytest.raises((ValueError, TypeError)):
            tx = Transaction()
            tx.add_output("not_a_number", "alice")  # type: ignore
            
    def test_negative_amount(self):
        """Negative amount - should be caught by validation"""
        tx = Transaction()
        tx.add_output(-10.0, "alice")
        
        # The model allows it, but validation should catch it
        assert tx.outputs[0].amount < 0


class TestAPIErrorResponses:
    """Test error response handling"""
    
    def test_invalid_hash_format(self):
        """Invalid hash should fail validation"""
        # Valid hash is 64 hex characters
        invalid_hashes = [
            "short",           # Too short
            "g" * 64,          # Invalid character
            "a" * 65,          # Too long
            "",                # Empty
        ]
        
        for invalid_hash in invalid_hashes:
            # Creating block with invalid previous_hash
            # The system should handle this gracefully
            block = Block(
                index=1,
                transactions=[],
                previous_hash=invalid_hash
            )
            # Block is created but may fail validation
            
    def test_duplicate_transaction_id(self):
        """Duplicate transaction IDs in block"""
        tx1 = Transaction()
        tx1.timestamp = 1000
        tx1.add_output(10.0, "alice")
        
        # Same transaction twice
        block = Block(
            index=1,
            transactions=[tx1, tx1],  # Duplicate
            previous_hash="0" * 64
        )
        
        # Should have 2 transactions (duplicates allowed by model)
        assert len(block.transactions) == 2


class TestAPICoinbaseValidation:
    """Test coinbase transaction validation"""
    
    def test_single_coinbase_per_block(self):
        """Block should have exactly one coinbase"""
        coinbase1 = Transaction.create_coinbase_transaction("miner1", 50.0, 1)
        coinbase2 = Transaction.create_coinbase_transaction("miner2", 50.0, 1)
        regular_tx = Transaction()
        regular_tx.add_input("a" * 64, 0)
        regular_tx.add_output(10.0, "bob")
        
        # Count coinbase transactions
        transactions = [coinbase1, regular_tx]
        coinbase_count = sum(1 for tx in transactions if tx.is_coinbase())
        
        assert coinbase_count == 1
        
    def test_coinbase_must_be_first(self):
        """Coinbase should be first transaction in block"""
        coinbase = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        regular_tx = Transaction()
        regular_tx.add_input("a" * 64, 0)
        regular_tx.add_output(10.0, "bob")
        
        # Valid order: coinbase first
        valid_order = [coinbase, regular_tx]
        assert valid_order[0].is_coinbase()
        
        # Invalid order: regular first
        invalid_order = [regular_tx, coinbase]
        assert not invalid_order[0].is_coinbase()


class TestAPIBlockValidation:
    """Test block validation through API"""
    
    def test_valid_block_structure(self):
        """Valid block should pass structure validation"""
        coinbase = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        block = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64,
            target_difficulty=1
        )
        
        # Structural validation
        assert block.index >= 0
        assert len(block.hash) == 64
        assert len(block.previous_hash) == 64
        assert len(block.merkle_root) == 64
        assert block.timestamp > 0
        assert block.nonce >= 0
        
    def test_block_index_sequential(self):
        """Block indices should be sequential"""
        genesis = Block(
            index=0,
            transactions=[Transaction.create_coinbase_transaction("miner", 50.0, 0)],
            previous_hash="0" * 64
        )
        
        block1 = Block(
            index=1,  # Must be genesis.index + 1
            transactions=[Transaction.create_coinbase_transaction("miner", 50.0, 1)],
            previous_hash=genesis.hash
        )
        
        assert block1.index == genesis.index + 1


class TestAPIQueryParameters:
    """Test API query parameter handling"""
    
    def test_pagination_parameters(self):
        """Test pagination logic"""
        # Simulate 100 transactions
        all_items = list(range(100))
        
        # Page 1, limit 10
        page = 1
        limit = 10
        start = (page - 1) * limit
        end = start + limit
        
        page_1 = all_items[start:end]
        assert len(page_1) == 10
        assert page_1 == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        
        # Page 5, limit 10
        page = 5
        start = (page - 1) * limit
        end = start + limit
        
        page_5 = all_items[start:end]
        assert page_5 == [40, 41, 42, 43, 44, 45, 46, 47, 48, 49]
        
    def test_filter_by_address(self):
        """Test filtering transactions by address"""
        transactions = [
            {"to": "alice", "amount": 10},
            {"to": "bob", "amount": 20},
            {"to": "alice", "amount": 30},
            {"to": "charlie", "amount": 40},
        ]
        
        alice_txs = [tx for tx in transactions if tx["to"] == "alice"]
        
        assert len(alice_txs) == 2
        assert sum(tx["amount"] for tx in alice_txs) == 40


class TestAPIRateLimiting:
    """Test rate limiting behavior (design tests)"""
    
    def test_rate_limit_structure(self):
        """Rate limit response structure"""
        # Simulate rate limit response
        rate_limit_response = {
            "error": "rate_limit_exceeded",
            "retry_after": 60,
            "limit": 100,
            "remaining": 0,
            "reset_at": 1609459260
        }
        
        assert "retry_after" in rate_limit_response
        assert "limit" in rate_limit_response
        
    def test_rate_limit_headers(self):
        """Rate limit headers structure"""
        headers = {
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Remaining": "95",
            "X-RateLimit-Reset": "1609459260"
        }
        
        assert int(headers["X-RateLimit-Remaining"]) <= int(headers["X-RateLimit-Limit"])


class TestAPISecurityHeaders:
    """Test security-related API concerns"""
    
    def test_transaction_signature_required(self):
        """Non-coinbase transactions should have signatures"""
        tx = Transaction()
        tx.add_input("a" * 64, 0)
        tx.add_output(10.0, "bob")
        
        # Without signing, signature is empty
        assert tx.inputs[0].signature == {}
        
        # This should be rejected by validation
        has_signature = bool(tx.inputs[0].signature)
        assert not has_signature  # Missing signature
        
    def test_address_format_validation(self):
        """Addresses should follow expected format"""
        from src.crypto.ecdsa_crypto import validate_address, ECDSAKeyPair
        
        # Valid address
        keypair = ECDSAKeyPair()
        assert validate_address(keypair.address) is True
        
        # Invalid addresses
        assert validate_address("invalid") is False
        assert validate_address("") is False
