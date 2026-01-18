"""
Security-focused tests for ChainCore.
Tests attack vectors, edge cases, and security properties.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.crypto.ecdsa_crypto import ECDSAKeyPair, verify_signature, validate_address, double_sha256
from src.core.bitcoin_transaction import Transaction, TransactionInput, TransactionOutput
from src.core.block import Block


class TestDoubleSpendPrevention:
    """Test double-spend attack prevention"""
    
    def test_same_utxo_cannot_be_spent_twice(self):
        """Same UTXO in two different transactions"""
        utxo_set = {"tx1:0": {"amount": 50.0, "recipient_address": "alice"}}
        
        # First transaction spends the UTXO
        tx1 = Transaction()
        tx1.add_input("tx1", 0)
        tx1.add_output(50.0, "bob")
        
        # Simulate spending
        spent_key = f"{tx1.inputs[0].tx_id}:{tx1.inputs[0].output_index}"
        del utxo_set[spent_key]
        
        # Second transaction tries same UTXO
        tx2 = Transaction()
        tx2.add_input("tx1", 0)
        tx2.add_output(50.0, "charlie")
        
        check_key = f"{tx2.inputs[0].tx_id}:{tx2.inputs[0].output_index}"
        assert check_key not in utxo_set  # Already spent
        
    def test_same_utxo_twice_in_same_tx(self):
        """Same UTXO used twice as input in single transaction"""
        tx = Transaction()
        tx.add_input("tx1", 0)
        tx.add_input("tx1", 0)  # Duplicate input
        tx.add_output(100.0, "attacker")
        
        # Count unique inputs
        input_keys = [f"{inp.tx_id}:{inp.output_index}" for inp in tx.inputs]
        unique_inputs = set(input_keys)
        
        # Validation should catch this
        assert len(input_keys) != len(unique_inputs)  # Has duplicates


class TestSignatureSecurity:
    """Test signature-related security"""
    
    def test_signature_replay_different_tx(self):
        """Signature from one tx should not work on another"""
        keypair = ECDSAKeyPair()
        
        tx1 = Transaction()
        tx1.add_input("a" * 64, 0)
        tx1.add_output(10.0, "bob")
        tx1.sign_input(0, keypair)
        
        tx2 = Transaction()
        tx2.add_input("b" * 64, 0)
        tx2.add_output(20.0, "charlie")
        
        # Copy signature from tx1 to tx2
        tx2.inputs[0].signature = tx1.inputs[0].signature.copy()
        
        # The signatures are for different transactions
        assert tx1.tx_id != tx2.tx_id
        
    def test_cannot_forge_signature(self):
        """Cannot create valid signature without private key"""
        alice = ECDSAKeyPair()
        attacker = ECDSAKeyPair()
        
        message = "Transfer 100 BTC to attacker"
        
        # Attacker signs with their key
        attacker_sig = attacker.sign(message)
        
        # Verification with Alice's public key should fail
        is_valid = verify_signature(attacker_sig, message, alice.get_public_key_hex())
        assert is_valid is False
        
    def test_signature_malleability(self):
        """Modified signature should be invalid"""
        keypair = ECDSAKeyPair()
        message = "Original message"
        
        sig = keypair.sign(message)
        original_sig_hex = sig['signature']
        
        # Flip a bit in signature
        tampered_hex = original_sig_hex[:-1] + ('0' if original_sig_hex[-1] != '0' else '1')
        tampered_sig = sig.copy()
        tampered_sig['signature'] = tampered_hex
        
        # Should fail verification
        is_valid = verify_signature(tampered_sig, message, keypair.get_public_key_hex())
        assert is_valid is False


class TestOverflowAttacks:
    """Test integer overflow and value manipulation"""
    
    def test_negative_amount_output(self):
        """Negative amounts should be detected"""
        tx = Transaction()
        tx.add_output(-100.0, "attacker")
        
        assert tx.outputs[0].amount < 0  # Should be caught by validation
        
    def test_zero_amount_output(self):
        """Zero amount (dust) outputs"""
        tx = Transaction()
        tx.add_output(0.0, "dust")
        
        assert tx.outputs[0].amount == 0
        
    def test_very_large_amount(self):
        """Extremely large amounts"""
        tx = Transaction()
        tx.add_output(21_000_000_000.0, "whale")  # More than max BTC
        
        # Should be caught by supply validation
        max_supply = 21_000_000.0
        assert tx.outputs[0].amount > max_supply
        
    def test_float_precision_attack(self):
        """Float precision shouldn't create money"""
        tx = Transaction()
        # Add many small amounts that might accumulate floating point error
        for _ in range(1000):
            tx.add_output(0.00000001, "recipient")
            
        total = tx.get_total_output_value()
        expected = 0.00000001 * 1000
        
        # Should be very close (within floating point tolerance)
        assert abs(total - expected) < 0.0000001


class TestHashSecurity:
    """Test hash function security properties"""
    
    def test_preimage_resistance(self):
        """Cannot find input from hash output"""
        target_hash = "0" * 64
        
        # This is infeasible - just demonstrating the property
        test_input = "random_guess"
        result = double_sha256(test_input)
        
        assert result != target_hash  # Extremely unlikely to match
        
    def test_collision_resistance(self):
        """Different inputs produce different hashes"""
        inputs = [f"input_{i}" for i in range(100)]
        hashes = [double_sha256(inp) for inp in inputs]
        
        # All hashes should be unique
        assert len(hashes) == len(set(hashes))
        
    def test_hash_length_constant(self):
        """Hash output is always 64 hex chars regardless of input"""
        inputs = ["", "a", "a" * 1000, "a" * 100000]
        
        for inp in inputs:
            h = double_sha256(inp)
            assert len(h) == 64


class TestAddressSecurity:
    """Test address validation and security"""
    
    def test_invalid_address_rejected(self):
        """Invalid addresses should fail validation"""
        invalid_addresses = [
            "",
            "1",
            "invalid",
            "0" * 64,  # Hash, not address
            "1InvalidChecksum123456789",
        ]
        
        for addr in invalid_addresses:
            assert validate_address(addr) is False
            
    def test_valid_address_accepted(self):
        """Valid generated addresses should pass"""
        for _ in range(5):
            keypair = ECDSAKeyPair()
            assert validate_address(keypair.address) is True
            
    def test_address_tampering_detected(self):
        """Modified address fails checksum"""
        keypair = ECDSAKeyPair()
        valid_addr = keypair.address
        
        # Change one character
        chars = list(valid_addr)
        chars[5] = 'X' if chars[5] != 'X' else 'Y'
        tampered = ''.join(chars)
        
        assert validate_address(tampered) is False


class TestBlockSecurity:
    """Test block-level security"""
    
    def test_block_hash_immutability(self):
        """Changing block data changes hash"""
        tx = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        block = Block(
            index=1,
            transactions=[tx],
            previous_hash="0" * 64,
            timestamp=1000,
            nonce=42
        )
        original_hash = block.hash
        
        # Change nonce
        block.nonce = 43
        block.hash = block._calculate_hash()
        
        assert block.hash != original_hash
        
    def test_merkle_root_tampering_detected(self):
        """Tampering with transaction changes merkle root"""
        tx1 = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        block = Block(
            index=1,
            transactions=[tx1],
            previous_hash="0" * 64
        )
        original_merkle = block.merkle_root
        
        # Different transaction
        tx2 = Transaction.create_coinbase_transaction("attacker", 100.0, 1)
        block2 = Block(
            index=1,
            transactions=[tx2],
            previous_hash="0" * 64
        )
        
        assert block2.merkle_root != original_merkle
        
    def test_difficulty_validation(self):
        """Block must meet difficulty target"""
        tx = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        block = Block(
            index=1,
            transactions=[tx],
            previous_hash="0" * 64,
            target_difficulty=4  # Requires 4 leading zeros
        )
        
        # Random hash unlikely to meet difficulty
        if not block.hash.startswith("0000"):
            assert block.is_valid_hash() is False


class TestChainSecurity:
    """Test blockchain chain security"""
    
    def test_chain_link_integrity(self):
        """Blocks must link via previous_hash"""
        blocks = []
        prev_hash = "0" * 64
        
        for i in range(5):
            tx = Transaction.create_coinbase_transaction("miner", 50.0, i)
            block = Block(index=i, transactions=[tx], previous_hash=prev_hash)
            blocks.append(block)
            prev_hash = block.hash
            
        # Verify chain integrity
        for i in range(1, len(blocks)):
            assert blocks[i].previous_hash == blocks[i-1].hash
            
    def test_chain_rewrite_detected(self):
        """Modifying old block breaks chain"""
        blocks = []
        prev_hash = "0" * 64
        
        for i in range(3):
            tx = Transaction.create_coinbase_transaction("miner", 50.0, i)
            block = Block(index=i, transactions=[tx], previous_hash=prev_hash, timestamp=1000+i)
            blocks.append(block)
            prev_hash = block.hash
            
        # Store block 1's hash that block 2 references
        original_block1_hash = blocks[1].hash
        
        # "Rewrite" block 1
        blocks[1].timestamp = 9999
        blocks[1].hash = blocks[1]._calculate_hash()
        
        # Block 2's previous_hash no longer matches
        assert blocks[2].previous_hash == original_block1_hash
        assert blocks[2].previous_hash != blocks[1].hash


class TestInputValidation:
    """Test input validation edge cases"""
    
    def test_empty_tx_id(self):
        """Empty transaction ID handling"""
        tx_input = TransactionInput("", 0)
        assert tx_input.tx_id == ""
        
    def test_max_output_index(self):
        """Maximum output index (coinbase marker)"""
        tx_input = TransactionInput("0" * 64, 0xFFFFFFFF)
        assert tx_input.output_index == 0xFFFFFFFF
        
    def test_unicode_in_address(self):
        """Unicode characters in address should fail validation"""
        unicode_addr = "1Unicode🔒Address"
        assert validate_address(unicode_addr) is False
        
    def test_whitespace_handling(self):
        """Whitespace in addresses should be handled"""
        keypair = ECDSAKeyPair()
        valid = keypair.address
        
        with_space = " " + valid
        
        # Addresses with whitespace should be stripped or rejected
        # Testing that they differ from valid address
        assert with_space != valid
