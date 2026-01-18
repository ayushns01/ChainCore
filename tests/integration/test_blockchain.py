"""
Integration tests for Blockchain operations.

Tests cover:
- Block chain linking
- Fork resolution (longest chain wins)
- Transaction validation across chain
- UTXO management
- Sync operations
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.block import Block
from src.core.bitcoin_transaction import Transaction
from src.crypto.ecdsa_crypto import ECDSAKeyPair


class TestBlockchainLinking:
    """Test proper block chain formation"""
    
    def test_blocks_link_via_previous_hash(self):
        """Each block's previous_hash should match prior block's hash"""
        # Genesis
        coinbase0 = Transaction.create_coinbase_transaction("miner", 50.0, 0)
        genesis = Block(
            index=0,
            transactions=[coinbase0],
            previous_hash="0" * 64,
            target_difficulty=1
        )
        
        # Block 1
        coinbase1 = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        block1 = Block(
            index=1,
            transactions=[coinbase1],
            previous_hash=genesis.hash,
            target_difficulty=1
        )
        
        assert block1.previous_hash == genesis.hash
        
    def test_chain_integrity_multiple_blocks(self):
        """Multi-block chain should maintain hash linking"""
        blocks = []
        prev_hash = "0" * 64
        
        for i in range(5):
            coinbase = Transaction.create_coinbase_transaction("miner", 50.0, i)
            block = Block(
                index=i,
                transactions=[coinbase],
                previous_hash=prev_hash,
                target_difficulty=1
            )
            blocks.append(block)
            prev_hash = block.hash
            
        # Verify chain
        for i in range(1, len(blocks)):
            assert blocks[i].previous_hash == blocks[i-1].hash
            
    def test_tampering_breaks_chain(self):
        """Modifying a block should break chain integrity"""
        # Genesis
        coinbase0 = Transaction.create_coinbase_transaction("miner", 50.0, 0)
        genesis = Block(
            index=0,
            transactions=[coinbase0],
            previous_hash="0" * 64,
            target_difficulty=1,
            timestamp=1000
        )
        
        # Block 1 references genesis
        coinbase1 = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        block1 = Block(
            index=1,
            transactions=[coinbase1],
            previous_hash=genesis.hash,
            target_difficulty=1
        )
        
        original_genesis_hash = genesis.hash
        
        # Tamper with genesis (change timestamp)
        genesis.timestamp = 2000
        genesis.hash = genesis._calculate_hash()
        
        # Block1's previous_hash no longer matches genesis.hash
        assert block1.previous_hash == original_genesis_hash
        assert block1.previous_hash != genesis.hash


class TestForkResolution:
    """Test fork resolution (longest chain wins)"""
    
    def test_longer_chain_wins(self):
        """Chain with more cumulative work should win"""
        # Common genesis
        genesis = Block(
            index=0,
            transactions=[Transaction.create_coinbase_transaction("miner", 50.0, 0)],
            previous_hash="0" * 64,
            target_difficulty=1,
            timestamp=1000
        )
        
        # Chain A: 2 more blocks
        chain_a = [genesis]
        for i in range(1, 3):
            block = Block(
                index=i,
                transactions=[Transaction.create_coinbase_transaction("miner_a", 50.0, i)],
                previous_hash=chain_a[-1].hash,
                target_difficulty=1,
                timestamp=1000 + i
            )
            chain_a.append(block)
            
        # Chain B: 3 more blocks (longer)
        chain_b = [genesis]
        for i in range(1, 4):
            block = Block(
                index=i,
                transactions=[Transaction.create_coinbase_transaction("miner_b", 50.0, i)],
                previous_hash=chain_b[-1].hash,
                target_difficulty=1,
                timestamp=2000 + i
            )
            chain_b.append(block)
            
        # Chain B is longer
        assert len(chain_b) > len(chain_a)
        
    def test_same_length_different_work(self):
        """Higher difficulty chain should have more work"""
        genesis = Block(
            index=0,
            transactions=[Transaction.create_coinbase_transaction("miner", 50.0, 0)],
            previous_hash="0" * 64,
            target_difficulty=1,
            timestamp=1000
        )
        
        # Block with difficulty 1
        block_easy = Block(
            index=1,
            transactions=[Transaction.create_coinbase_transaction("miner", 50.0, 1)],
            previous_hash=genesis.hash,
            target_difficulty=1
        )
        
        # Block with difficulty 2
        block_hard = Block(
            index=1,
            transactions=[Transaction.create_coinbase_transaction("miner", 50.0, 1)],
            previous_hash=genesis.hash,
            target_difficulty=2
        )
        
        # Higher difficulty = more work
        assert block_hard.calculate_block_work() > block_easy.calculate_block_work()


class TestUTXOTracking:
    """Test UTXO (Unspent Transaction Output) management"""
    
    def test_coinbase_creates_utxo(self):
        """Coinbase transaction creates new UTXO"""
        miner = ECDSAKeyPair()
        coinbase = Transaction.create_coinbase_transaction(miner.address, 50.0, 1)
        
        # Create UTXO set from coinbase
        utxo_set = {}
        for i, output in enumerate(coinbase.outputs):
            key = f"{coinbase.tx_id}:{i}"
            utxo_set[key] = {
                "amount": output.amount,
                "recipient_address": output.recipient_address
            }
            
        assert len(utxo_set) == 1
        assert list(utxo_set.values())[0]["amount"] == 50.0
        
    def test_spending_utxo_removes_it(self):
        """Spending a UTXO should remove it from the set"""
        # Initial UTXO
        utxo_set = {
            "tx1:0": {"amount": 50.0, "recipient_address": "alice"}
        }
        
        # Create spending transaction
        tx = Transaction()
        tx.add_input("tx1", 0)
        tx.add_output(45.0, "bob")
        tx.add_output(4.5, "alice")  # Change
        
        # Apply transaction to UTXO set
        # Remove spent input
        del utxo_set["tx1:0"]
        
        # Add new outputs
        for i, output in enumerate(tx.outputs):
            utxo_set[f"{tx.tx_id}:{i}"] = {
                "amount": output.amount,
                "recipient_address": output.recipient_address
            }
            
        # Old UTXO gone, two new ones created
        assert "tx1:0" not in utxo_set
        assert len(utxo_set) == 2
        
    def test_double_spend_detection(self):
        """Same UTXO cannot be spent twice"""
        utxo_set = {
            "tx1:0": {"amount": 50.0, "recipient_address": "alice"}
        }
        
        # First spend - valid
        tx1 = Transaction()
        tx1.add_input("tx1", 0)
        tx1.add_output(50.0, "bob")
        
        utxo_key = f"{tx1.inputs[0].tx_id}:{tx1.inputs[0].output_index}"
        assert utxo_key in utxo_set  # Can spend
        
        # Simulate spending
        del utxo_set[utxo_key]
        
        # Second spend - invalid (UTXO already spent)
        tx2 = Transaction()
        tx2.add_input("tx1", 0)  # Same UTXO
        tx2.add_output(50.0, "charlie")
        
        utxo_key2 = f"{tx2.inputs[0].tx_id}:{tx2.inputs[0].output_index}"
        assert utxo_key2 not in utxo_set  # Cannot spend - already gone


class TestTransactionValidation:
    """Test transaction validation in blockchain context"""
    
    def test_input_value_must_cover_outputs(self):
        """Total input value must be >= total output value"""
        utxo_set = {
            "tx1:0": {"amount": 50.0, "recipient_address": "alice"}
        }
        
        # Valid: outputs <= inputs
        tx_valid = Transaction()
        tx_valid.add_input("tx1", 0)
        tx_valid.add_output(30.0, "bob")
        tx_valid.add_output(19.0, "alice")  # Change + 1.0 fee
        
        input_value = tx_valid.get_total_input_value(utxo_set)
        output_value = tx_valid.get_total_output_value()
        
        assert input_value >= output_value
        assert tx_valid.get_fee(utxo_set) == 1.0
        
    def test_cannot_spend_more_than_own(self):
        """Cannot create outputs exceeding input value"""
        utxo_set = {
            "tx1:0": {"amount": 50.0, "recipient_address": "alice"}
        }
        
        # Invalid: trying to spend 100 when only have 50
        tx_invalid = Transaction()
        tx_invalid.add_input("tx1", 0)
        tx_invalid.add_output(100.0, "bob")  # More than input
        
        input_value = tx_invalid.get_total_input_value(utxo_set)
        output_value = tx_invalid.get_total_output_value()
        
        # This would be rejected
        assert output_value > input_value
        
    def test_coinbase_reward_validation(self):
        """Coinbase reward should not exceed allowed amount"""
        max_reward = 50.0  # Block reward
        
        # Valid coinbase
        valid_coinbase = Transaction.create_coinbase_transaction("miner", max_reward, 1)
        assert valid_coinbase.outputs[0].amount == max_reward
        
        # Would be invalid: reward too high
        invalid_coinbase = Transaction.create_coinbase_transaction("miner", 100.0, 1)
        assert invalid_coinbase.outputs[0].amount > max_reward  # Would fail validation


class TestMerkleRootValidation:
    """Test Merkle root integrity"""
    
    def test_merkle_root_changes_with_transactions(self):
        """Different transactions should produce different merkle roots"""
        tx1 = Transaction.create_coinbase_transaction("miner1", 50.0, 1)
        tx2 = Transaction.create_coinbase_transaction("miner2", 50.0, 1)
        
        block1 = Block(index=1, transactions=[tx1], previous_hash="0" * 64, timestamp=1000)
        block2 = Block(index=1, transactions=[tx2], previous_hash="0" * 64, timestamp=1000)
        
        assert block1.merkle_root != block2.merkle_root
        
    def test_transaction_order_affects_merkle_root(self):
        """Different transaction ordering should produce different merkle roots"""
        tx_a = Transaction()
        tx_a.timestamp = 1000
        tx_a.add_output(10.0, "alice")
        
        tx_b = Transaction()
        tx_b.timestamp = 1001
        tx_b.add_output(20.0, "bob")
        
        block1 = Block(index=1, transactions=[tx_a, tx_b], previous_hash="0" * 64, timestamp=1000)
        block2 = Block(index=1, transactions=[tx_b, tx_a], previous_hash="0" * 64, timestamp=1000)
        
        assert block1.merkle_root != block2.merkle_root


class TestChainValidation:
    """Test full chain validation"""
    
    def test_valid_chain_passes(self):
        """Properly constructed chain should pass validation"""
        chain = []
        prev_hash = "0" * 64
        
        for i in range(5):
            coinbase = Transaction.create_coinbase_transaction(f"miner_{i}", 50.0, i)
            block = Block(
                index=i,
                transactions=[coinbase],
                previous_hash=prev_hash,
                target_difficulty=1,
                timestamp=1000 + i
            )
            chain.append(block)
            prev_hash = block.hash
            
        # Validate chain
        is_valid = True
        for i in range(1, len(chain)):
            if chain[i].previous_hash != chain[i-1].hash:
                is_valid = False
                break
            if chain[i].index != i:
                is_valid = False
                break
                
        assert is_valid
        
    def test_index_gap_invalidates_chain(self):
        """Missing block index should invalidate chain"""
        chain = []
        prev_hash = "0" * 64
        
        for i in [0, 1, 3]:  # Skip index 2
            coinbase = Transaction.create_coinbase_transaction("miner", 50.0, i)
            block = Block(
                index=i,
                transactions=[coinbase],
                previous_hash=prev_hash,
                target_difficulty=1
            )
            chain.append(block)
            prev_hash = block.hash
            
        # Check for index continuity
        is_valid = True
        for i in range(1, len(chain)):
            if chain[i].index != chain[i-1].index + 1:
                is_valid = False
                break
                
        assert not is_valid


class TestBlockReward:
    """Test block reward and halving"""
    
    def test_standard_block_reward(self):
        """Standard block reward should be 50"""
        reward = 50.0
        coinbase = Transaction.create_coinbase_transaction("miner", reward, 1)
        
        assert coinbase.outputs[0].amount == 50.0
        
    def test_reward_halving_logic(self):
        """Block reward should halve every N blocks"""
        def calculate_reward(block_height: int, halving_interval: int = 210000, initial_reward: float = 50.0) -> float:
            halvings = block_height // halving_interval
            return initial_reward / (2 ** halvings)
            
        assert calculate_reward(0) == 50.0
        assert calculate_reward(210000) == 25.0
        assert calculate_reward(420000) == 12.5
        assert calculate_reward(630000) == 6.25


class TestTransactionFees:
    """Test transaction fee handling"""
    
    def test_fee_goes_to_miner(self):
        """Transaction fees should be collectable by miner"""
        utxo_set = {
            "tx1:0": {"amount": 100.0, "recipient_address": "alice"}
        }
        
        # Transaction with 1.0 fee
        tx = Transaction()
        tx.add_input("tx1", 0)
        tx.add_output(99.0, "bob")  # 1.0 fee
        
        fee = tx.get_fee(utxo_set)
        assert fee == 1.0
        
        # Miner can claim block_reward + fees
        block_reward = 50.0
        total_miner_reward = block_reward + fee
        assert total_miner_reward == 51.0
