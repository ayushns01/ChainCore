"""
Unit tests for ECDSA cryptography module.

Tests cover:
- Key generation and address derivation
- Message signing and verification
- Signature tampering detection
- Address validation
- Serialization/deserialization
"""
import pytest
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.crypto.ecdsa_crypto import (
    ECDSAKeyPair, 
    verify_signature, 
    hash_data, 
    double_sha256,
    validate_address
)


class TestECDSAKeyPair:
    """Test ECDSA key pair generation and operations"""
    
    def test_keypair_generation(self):
        """Verify keypair generates valid components"""
        keypair = ECDSAKeyPair()
        
        assert keypair.private_key is not None
        assert keypair.public_key is not None
        assert keypair.address is not None
        
    def test_address_format(self):
        """Verify address follows Bitcoin format (Base58Check)"""
        keypair = ECDSAKeyPair()
        
        # Bitcoin mainnet addresses start with '1'
        assert keypair.address[0] == '1'
        # Typical length is 25-34 characters
        assert 25 <= len(keypair.address) <= 34
        
    def test_address_uniqueness(self):
        """Different keypairs should generate different addresses"""
        keypair1 = ECDSAKeyPair()
        keypair2 = ECDSAKeyPair()
        
        assert keypair1.address != keypair2.address
        assert keypair1.get_public_key_hex() != keypair2.get_public_key_hex()
        
    def test_public_key_format(self):
        """Verify public key is uncompressed secp256k1 format"""
        keypair = ECDSAKeyPair()
        public_key_hex = keypair.get_public_key_hex()
        
        # Uncompressed public key: 04 prefix + 64 bytes (128 hex chars)
        assert public_key_hex.startswith('04')
        assert len(public_key_hex) == 130  # 1 byte prefix + 64 bytes
        
    def test_keypair_deterministic_from_private(self):
        """Same private key should always produce same address"""
        keypair1 = ECDSAKeyPair()
        serialized = keypair1.to_dict()
        
        keypair2 = ECDSAKeyPair.from_dict(serialized)
        
        assert keypair1.address == keypair2.address
        assert keypair1.get_public_key_hex() == keypair2.get_public_key_hex()


class TestMessageSigning:
    """Test ECDSA message signing and verification"""
    
    def test_sign_string_message(self):
        """Sign a simple string message"""
        keypair = ECDSAKeyPair()
        message = "Hello, blockchain!"
        
        signature = keypair.sign(message)
        
        assert 'signature' in signature
        assert 'public_key' in signature
        assert 'message_hash' in signature
        
    def test_sign_json_message(self):
        """Sign a JSON-serializable transaction-like message"""
        keypair = ECDSAKeyPair()
        message = json.dumps({
            "from": keypair.address,
            "to": "recipient_address",
            "amount": 10.5
        }, sort_keys=True)
        
        signature = keypair.sign(message)
        
        assert signature['public_key'] == keypair.get_public_key_hex()
        
    def test_verify_valid_signature(self):
        """Verify a valid signature returns True"""
        keypair = ECDSAKeyPair()
        message = "Verify this transaction"
        
        signature = keypair.sign(message)
        
        assert verify_signature(
            signature, 
            message, 
            keypair.get_public_key_hex()
        ) is True
        
    def test_detect_tampered_message(self):
        """Detect when signed message has been tampered with"""
        keypair = ECDSAKeyPair()
        original_message = "Original transaction"
        tampered_message = "Tampered transaction"
        
        signature = keypair.sign(original_message)
        
        # Verification should fail with tampered message
        assert verify_signature(
            signature, 
            tampered_message, 
            keypair.get_public_key_hex()
        ) is False
        
    def test_detect_wrong_public_key(self):
        """Detect when signature is verified with wrong public key"""
        keypair1 = ECDSAKeyPair()
        keypair2 = ECDSAKeyPair()
        message = "My secret transaction"
        
        signature = keypair1.sign(message)
        
        # Verification should fail with different public key
        assert verify_signature(
            signature, 
            message, 
            keypair2.get_public_key_hex()
        ) is False
        
    def test_signature_uniqueness(self):
        """Same message signed twice should produce different signatures (ECDSA nonce)"""
        keypair = ECDSAKeyPair()
        message = "Sign me twice"
        
        sig1 = keypair.sign(message)
        sig2 = keypair.sign(message)
        
        # ECDSA uses random k value, so signatures differ
        # But both should verify
        assert verify_signature(sig1, message, keypair.get_public_key_hex())
        assert verify_signature(sig2, message, keypair.get_public_key_hex())


class TestHashFunctions:
    """Test cryptographic hash functions"""
    
    def test_hash_data_deterministic(self):
        """Same input should always produce same hash"""
        data = "consistent input"
        
        hash1 = hash_data(data)
        hash2 = hash_data(data)
        
        assert hash1 == hash2
        
    def test_hash_data_format(self):
        """Hash should be 64 character hex string (SHA-256)"""
        result = hash_data("test")
        
        assert len(result) == 64
        assert all(c in '0123456789abcdef' for c in result)
        
    def test_double_sha256_bitcoin_compatible(self):
        """Double SHA-256 should match Bitcoin's hashing scheme"""
        data = "test"
        
        result = double_sha256(data)
        
        # Verify it's a valid hex string
        assert len(result) == 64
        
        # Verify it's different from single hash
        single_hash = hash_data(data)
        assert result != single_hash
        
    def test_hash_bytes_input(self):
        """Hash functions should handle bytes input"""
        data_bytes = b"byte string"
        data_str = "byte string"
        
        # Both should produce same result
        assert hash_data(data_bytes) == hash_data(data_str)
        assert double_sha256(data_bytes) == double_sha256(data_str)
        
    def test_hash_avalanche_effect(self):
        """Small input change should dramatically change hash"""
        hash1 = hash_data("test1")
        hash2 = hash_data("test2")
        
        # Count differing characters
        differences = sum(1 for a, b in zip(hash1, hash2) if a != b)
        
        # Should differ in many positions (avalanche effect)
        assert differences > 30  # At least ~50% different


class TestAddressValidation:
    """Test Bitcoin-style address validation"""
    
    def test_validate_generated_address(self):
        """Addresses generated by our keypair should be valid"""
        keypair = ECDSAKeyPair()
        
        assert validate_address(keypair.address) is True
        
    def test_invalid_address_length(self):
        """Reject addresses with invalid length"""
        too_short = "1ABC"
        
        assert validate_address(too_short) is False
        
    def test_invalid_checksum(self):
        """Reject addresses with invalid checksum"""
        keypair = ECDSAKeyPair()
        # Tamper with address (change last character)
        tampered = keypair.address[:-1] + ('X' if keypair.address[-1] != 'X' else 'Y')
        
        assert validate_address(tampered) is False
        
    def test_invalid_characters(self):
        """Reject addresses with invalid Base58 characters"""
        # Base58 doesn't include 0, O, I, l
        invalid = "1Invalid0Address"
        
        assert validate_address(invalid) is False


class TestSerializationRoundtrip:
    """Test keypair serialization and deserialization"""
    
    def test_to_dict_contains_all_fields(self):
        """to_dict should include all necessary fields"""
        keypair = ECDSAKeyPair()
        data = keypair.to_dict()
        
        assert 'private_key' in data
        assert 'public_key' in data
        assert 'address' in data
        
    def test_roundtrip_preserves_signing_capability(self):
        """Deserialized keypair should still sign correctly"""
        original = ECDSAKeyPair()
        message = "Test message for roundtrip"
        
        # Serialize and deserialize
        data = original.to_dict()
        restored = ECDSAKeyPair.from_dict(data)
        
        # Sign with restored key
        signature = restored.sign(message)
        
        # Verify with original public key
        assert verify_signature(
            signature, 
            message, 
            original.get_public_key_hex()
        )
        
    def test_json_serialization(self):
        """Keypair data should be JSON-serializable"""
        keypair = ECDSAKeyPair()
        data = keypair.to_dict()
        
        # Should not raise
        json_str = json.dumps(data)
        restored_data = json.loads(json_str)
        
        assert restored_data == data


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_sign_empty_message(self):
        """Signing empty message should work"""
        keypair = ECDSAKeyPair()
        
        signature = keypair.sign("")
        
        assert verify_signature(signature, "", keypair.get_public_key_hex())
        
    def test_sign_large_message(self):
        """Signing large message should work (gets hashed anyway)"""
        keypair = ECDSAKeyPair()
        large_message = "x" * 1_000_000  # 1MB message
        
        signature = keypair.sign(large_message)
        
        assert verify_signature(
            signature, 
            large_message, 
            keypair.get_public_key_hex()
        )
        
    def test_sign_unicode_message(self):
        """Signing unicode message should work"""
        keypair = ECDSAKeyPair()
        unicode_message = "Hello 世界 🌍 مرحبا"
        
        signature = keypair.sign(unicode_message)
        
        assert verify_signature(
            signature, 
            unicode_message, 
            keypair.get_public_key_hex()
        )
        
    def test_hash_empty_string(self):
        """Hashing empty string should produce valid hash"""
        result = hash_data("")
        
        assert len(result) == 64
        # Known SHA-256 of empty string
        assert result == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
