import json
import time
from typing import List, Dict, Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.crypto.ecdsa_crypto import ECDSAKeyPair, verify_signature, hash_data, double_sha256

class TransactionInput:
    def __init__(self, tx_id: str, output_index: int, signature: Dict = None, script_sig: str = ""):
        self.tx_id = tx_id
        self.output_index = output_index
        self.signature = signature or {}
        self.script_sig = script_sig  # Bitcoin-style script
    
    def to_dict(self) -> Dict:
        return {
            'tx_id': self.tx_id,
            'output_index': self.output_index,
            'signature': self.signature,
            'script_sig': self.script_sig
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            data['tx_id'], 
            data['output_index'], 
            data.get('signature', {}),
            data.get('script_sig', '')
        )

class TransactionOutput:
    def __init__(self, amount: float, recipient_address: str, script_pubkey: str = ""):
        self.amount = amount
        self.recipient_address = recipient_address
        self.script_pubkey = script_pubkey  # Bitcoin-style script
    
    def to_dict(self) -> Dict:
        return {
            'amount': self.amount,
            'recipient_address': self.recipient_address,
            'script_pubkey': self.script_pubkey
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            data['amount'], 
            data['recipient_address'],
            data.get('script_pubkey', '')
        )

class Transaction:
    def __init__(self, inputs: List[TransactionInput] = None, outputs: List[TransactionOutput] = None, 
                 timestamp: float = None, tx_id: str = None, version: int = 1):
        self.version = version
        self.inputs = inputs or []
        self.outputs = outputs or []
        self.timestamp = timestamp or time.time()
        self.lock_time = 0  # Bitcoin-style lock time
        self.tx_id = tx_id or self._calculate_hash()
    
    def _calculate_hash(self) -> str:
        """Calculate transaction hash (Bitcoin-style double SHA256)"""
        tx_data = {
            'version': self.version,
            'inputs': [inp.to_dict() for inp in self.inputs],
            'outputs': [out.to_dict() for out in self.outputs],
            'lock_time': self.lock_time,
            'timestamp': self.timestamp
        }
        
        # Sort for deterministic hashing
        tx_string = json.dumps(tx_data, sort_keys=True)
        
        # Double SHA256 like Bitcoin
        return double_sha256(tx_string)
    
    def add_input(self, tx_id: str, output_index: int) -> TransactionInput:
        """Add input to transaction"""
        tx_input = TransactionInput(tx_id, output_index)
        self.inputs.append(tx_input)
        self.tx_id = self._calculate_hash()
        return tx_input
    
    def add_output(self, amount: float, recipient_address: str) -> TransactionOutput:
        """Add output to transaction"""
        tx_output = TransactionOutput(amount, recipient_address)
        self.outputs.append(tx_output)
        self.tx_id = self._calculate_hash()
        return tx_output
    
    def sign_input(self, input_index: int, keypair: ECDSAKeyPair, prev_output_script: str = ""):
        """Sign transaction input with ECDSA"""
        if input_index >= len(self.inputs):
            raise ValueError("Input index out of range")
        
        tx_input = self.inputs[input_index]
        
        # Create signing data (simplified version of Bitcoin's signing)
        signing_data = {
            'tx_id': self.tx_id,
            'input_tx_id': tx_input.tx_id,
            'input_index': tx_input.output_index,
            'script': prev_output_script
        }
        
        signing_string = json.dumps(signing_data, sort_keys=True)
        signature = keypair.sign(signing_string)
        
        tx_input.signature = signature
        tx_input.script_sig = f"SIG({signature['signature'][:16]}...) PUBKEY({signature['public_key'][:16]}...)"
    
    def verify_input_signature(self, input_index: int, prev_output_script: str = "", utxo_set: Dict = None) -> bool:
        """Verify transaction input signature"""
        if input_index >= len(self.inputs):
            return False
        
        tx_input = self.inputs[input_index]
        if not tx_input.signature:
            return False
        
        # Get UTXO to find the public key
        utxo_key = f"{tx_input.tx_id}:{tx_input.output_index}"
        if utxo_set and utxo_key in utxo_set:
            recipient_address = utxo_set[utxo_key]['recipient_address']
        else:
            return False
        
        # Create signing data
        signing_data = {
            'tx_id': self.tx_id,
            'input_tx_id': tx_input.tx_id,
            'input_index': tx_input.output_index,
            'script': prev_output_script
        }
        
        signing_string = json.dumps(signing_data, sort_keys=True)
        
        return verify_signature(
            tx_input.signature, 
            signing_string, 
            tx_input.signature['public_key']
        )
    
    def get_total_input_value(self, utxo_set: Dict) -> float:
        """Calculate total input value from UTXO set"""
        total = 0.0
        for tx_input in self.inputs:
            utxo_key = f"{tx_input.tx_id}:{tx_input.output_index}"
            if utxo_key in utxo_set:
                total += utxo_set[utxo_key]['amount']
        return total
    
    def get_total_output_value(self) -> float:
        """Calculate total output value"""
        return sum(output.amount for output in self.outputs)
    
    def get_fee(self, utxo_set: Dict) -> float:
        """Calculate transaction fee"""
        if self.is_coinbase():
            return 0.0
        
        input_value = self.get_total_input_value(utxo_set)
        output_value = self.get_total_output_value()
        return max(0, input_value - output_value)
    
    def is_coinbase(self) -> bool:
        """Check if this is a coinbase transaction"""
        return (len(self.inputs) == 1 and 
                self.inputs[0].tx_id == "0" * 64 and 
                self.inputs[0].output_index == 0xFFFFFFFF)
    
    def get_size(self) -> int:
        """Get transaction size in bytes (approximation)"""
        return len(json.dumps(self.to_dict()))
    
    def to_dict(self) -> Dict:
        """Serialize transaction to dictionary"""
        return {
            'version': self.version,
            'tx_id': self.tx_id,
            'inputs': [inp.to_dict() for inp in self.inputs],
            'outputs': [out.to_dict() for out in self.outputs],
            'lock_time': self.lock_time,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        """deserialize transaction from dictionary"""
        inputs = [TransactionInput.from_dict(inp) for inp in data['inputs']]
        outputs = [TransactionOutput.from_dict(out) for out in data['outputs']]
        
        tx = cls(inputs, outputs, data['timestamp'], data['tx_id'], data.get('version', 1))
        tx.lock_time = data.get('lock_time', 0)
        return tx
    
    @classmethod
    def create_coinbase_transaction(cls, miner_address: str, reward: float, block_height: int = 0) -> 'Transaction':
        """Create coinbase transaction (mining reward)"""
        # Coinbase input
        coinbase_input = TransactionInput("0" * 64, 0xFFFFFFFF)
        coinbase_input.script_sig = f"COINBASE_BLOCK_{block_height}"
        
        # Reward output
        reward_output = TransactionOutput(reward, miner_address)
        reward_output.script_pubkey = f"PAY_TO_ADDRESS({miner_address})"
        
        tx = cls([coinbase_input], [reward_output])
        return tx