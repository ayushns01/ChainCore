import hashlib
import os
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
import base58
import json

class ECDSAKeyPair:
    """Bitcoin-style ECDSA key pair"""
    
    def __init__(self, private_key=None):
        if private_key is None:
            self.private_key = ec.generate_private_key(ec.SECP256K1(), default_backend())
        else:
            self.private_key = private_key
        
        self.public_key = self.private_key.public_key()
        self.address = self._generate_address()
    
    def _generate_address(self):
        """Generate Bitcoin-style address from public key"""
        # Get public key bytes
        public_key_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        
        # Hash with SHA256 then RIPEMD160
        sha256_hash = hashlib.sha256(public_key_bytes).digest()
        ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
        
        # Add version byte (0x00 for mainnet)
        versioned_hash = b'\x00' + ripemd160_hash
        
        # Double SHA256 for checksum
        checksum = hashlib.sha256(hashlib.sha256(versioned_hash).digest()).digest()[:4]
        
        # Combine and encode with Base58
        address_bytes = versioned_hash + checksum
        return base58.b58encode(address_bytes).decode('utf-8')
    
    def sign(self, message):
        """Sign message with private key"""
        if isinstance(message, str):
            message = message.encode('utf-8')
        
        message_hash = hashlib.sha256(message).digest()
        signature = self.private_key.sign(message_hash, ec.ECDSA(hashes.SHA256()))
        
        return {
            'signature': signature.hex(),
            'public_key': self.get_public_key_hex(),
            'message_hash': message_hash.hex()
        }
    
    def get_public_key_hex(self):
        """Get public key as hex string"""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        ).hex()
    
    def get_private_key_hex(self):
        """Get private key as hex string"""
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).hex()
    
    def to_dict(self):
        """Serialize to dictionary"""
        return {
            'private_key': self.get_private_key_hex(),
            'public_key': self.get_public_key_hex(),
            'address': self.address
        }
    
    @classmethod
    def from_dict(cls, data):
        """Deserialize from dictionary"""
        private_key_pem = bytes.fromhex(data['private_key'])
        private_key = serialization.load_pem_private_key(
            private_key_pem,
            password=None,
            backend=default_backend()
        )
        return cls(private_key)

def verify_signature(signature_data, message, public_key_hex):
    """Verify ECDSA signature"""
    try:
        if isinstance(message, str):
            message = message.encode('utf-8')
        
        message_hash = hashlib.sha256(message).digest()
        
        # Reconstruct public key
        public_key_bytes = bytes.fromhex(public_key_hex)
        public_key = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256K1(), public_key_bytes
        )
        
        # Verify signature
        signature_bytes = bytes.fromhex(signature_data['signature'])
        public_key.verify(signature_bytes, message_hash, ec.ECDSA(hashes.SHA256()))
        
        return True
    except Exception as e:
        print(f"Verification error: {e}")
        return False

def hash_data(data):
    """SHA256 hash function"""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()

def double_sha256(data):
    """Double SHA256 (Bitcoin-style)"""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(hashlib.sha256(data).digest()).hexdigest()

def validate_address(address):
    """Validate Bitcoin-style address"""
    try:
        # Decode Base58
        decoded = base58.b58decode(address)
        
        # Check length
        if len(decoded) != 25:
            return False
        
        # Split address and checksum
        address_bytes = decoded[:-4]
        checksum = decoded[-4:]
        
        # Verify checksum
        expected_checksum = hashlib.sha256(hashlib.sha256(address_bytes).digest()).digest()[:4]
        
        return checksum == expected_checksum
    except:
        return False