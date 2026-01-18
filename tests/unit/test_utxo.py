"""
Tests for UTXO (Unspent Transaction Output) model.
Tests spending, validation, and state management.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.bitcoin_transaction import Transaction, TransactionInput, TransactionOutput
from src.crypto.ecdsa_crypto import ECDSAKeyPair


class TestUTXOCreation:
    """Test UTXO creation from transactions"""
    
    def test_coinbase_creates_single_utxo(self):
        """Coinbase transaction creates one UTXO"""
        tx = Transaction.create_coinbase_transaction("miner", 50.0, 1)
        
        utxos = []
        for i, output in enumerate(tx.outputs):
            utxos.append({
                "key": f"{tx.tx_id}:{i}",
                "amount": output.amount,
                "address": output.recipient_address
            })
            
        assert len(utxos) == 1
        assert utxos[0]["amount"] == 50.0
        
    def test_transaction_creates_multiple_utxos(self):
        """Transaction with multiple outputs creates multiple UTXOs"""
        tx = Transaction()
        tx.add_output(30.0, "alice")
        tx.add_output(15.0, "bob")
        tx.add_output(5.0, "charlie")
        
        utxos = []
        for i, output in enumerate(tx.outputs):
            utxos.append(f"{tx.tx_id}:{i}")
            
        assert len(utxos) == 3
        
    def test_utxo_key_format(self):
        """UTXO key should be tx_id:output_index"""
        tx = Transaction()
        tx.add_output(10.0, "alice")
        
        utxo_key = f"{tx.tx_id}:0"
        
        assert ":" in utxo_key
        assert utxo_key.endswith(":0")


class TestUTXOSpending:
    """Test UTXO spending mechanics"""
    
    def test_spending_removes_utxo(self):
        """Spending a UTXO removes it from the set"""
        utxo_set = {
            "abc:0": {"amount": 50.0, "address": "alice"},
            "def:0": {"amount": 30.0, "address": "bob"}
        }
        
        # Spend alice's UTXO
        spent_key = "abc:0"
        del utxo_set[spent_key]
        
        assert spent_key not in utxo_set
        assert len(utxo_set) == 1
        
    def test_spending_creates_new_utxos(self):
        """Spending creates new UTXOs from outputs"""
        utxo_set = {"old_tx:0": {"amount": 100.0, "address": "alice"}}
        
        # Create spending transaction
        tx = Transaction()
        tx.add_input("old_tx", 0)
        tx.add_output(60.0, "bob")
        tx.add_output(39.0, "alice")  # Change
        
        # Remove spent UTXO
        del utxo_set["old_tx:0"]
        
        # Add new UTXOs
        for i, out in enumerate(tx.outputs):
            utxo_set[f"{tx.tx_id}:{i}"] = {"amount": out.amount, "address": out.recipient_address}
            
        assert "old_tx:0" not in utxo_set
        assert len(utxo_set) == 2
        
    def test_partial_spend_with_change(self):
        """Spending part of UTXO requires change output"""
        utxo_set = {"tx1:0": {"amount": 100.0, "address": "alice"}}
        
        tx = Transaction()
        tx.add_input("tx1", 0)
        tx.add_output(30.0, "bob")      # Payment
        tx.add_output(69.0, "alice")    # Change (1.0 fee)
        
        input_value = utxo_set["tx1:0"]["amount"]
        output_value = tx.get_total_output_value()
        fee = input_value - output_value
        
        assert fee == 1.0


class TestUTXOValidation:
    """Test UTXO validation rules"""
    
    def test_cannot_spend_nonexistent_utxo(self):
        """Cannot reference UTXO that doesn't exist"""
        utxo_set = {"real:0": {"amount": 50.0, "address": "alice"}}
        
        tx = Transaction()
        tx.add_input("fake:0", 0)  # Doesn't exist
        
        utxo_key = f"{tx.inputs[0].tx_id}:{tx.inputs[0].output_index}"
        exists = utxo_key in utxo_set
        
        assert exists is False
        
    def test_input_value_from_utxo(self):
        """Input value comes from referenced UTXO"""
        utxo_set = {
            "tx1:0": {"amount": 50.0, "address": "alice"},
            "tx2:1": {"amount": 25.0, "address": "alice"}
        }
        
        tx = Transaction()
        tx.add_input("tx1", 0)
        tx.add_input("tx2", 1)
        
        total_input = tx.get_total_input_value(utxo_set)
        assert total_input == 75.0
        
    def test_outputs_cannot_exceed_inputs(self):
        """Total outputs cannot exceed total inputs"""
        utxo_set = {"tx1:0": {"amount": 50.0, "address": "alice"}}
        
        tx = Transaction()
        tx.add_input("tx1", 0)
        tx.add_output(60.0, "bob")  # More than input!
        
        input_value = tx.get_total_input_value(utxo_set)
        output_value = tx.get_total_output_value()
        
        is_valid = output_value <= input_value
        assert is_valid is False


class TestUTXOSet:
    """Test UTXO set management"""
    
    def test_empty_utxo_set(self):
        """Empty UTXO set at genesis"""
        utxo_set = {}
        assert len(utxo_set) == 0
        
    def test_genesis_coinbase_initializes_utxo(self):
        """Genesis coinbase creates first UTXO"""
        utxo_set = {}
        
        genesis_tx = Transaction.create_coinbase_transaction("satoshi", 50.0, 0)
        
        for i, out in enumerate(genesis_tx.outputs):
            utxo_set[f"{genesis_tx.tx_id}:{i}"] = {
                "amount": out.amount,
                "address": out.recipient_address
            }
            
        assert len(utxo_set) == 1
        
    def test_utxo_set_grows_with_blocks(self):
        """UTXO set grows as blocks are added"""
        utxo_set = {}
        
        # Add 5 coinbase transactions
        for height in range(5):
            tx = Transaction.create_coinbase_transaction(f"miner_{height}", 50.0, height)
            for i, out in enumerate(tx.outputs):
                utxo_set[f"{tx.tx_id}:{i}"] = {"amount": out.amount}
                
        assert len(utxo_set) == 5
        
    def test_utxo_lookup_by_address(self):
        """Find UTXOs belonging to an address"""
        utxo_set = {
            "tx1:0": {"amount": 50.0, "address": "alice"},
            "tx2:0": {"amount": 30.0, "address": "bob"},
            "tx3:0": {"amount": 20.0, "address": "alice"},
        }
        
        alice_utxos = {k: v for k, v in utxo_set.items() if v["address"] == "alice"}
        alice_balance = sum(u["amount"] for u in alice_utxos.values())
        
        assert len(alice_utxos) == 2
        assert alice_balance == 70.0


class TestUTXOBalance:
    """Test balance calculations from UTXO set"""
    
    def test_balance_from_utxos(self):
        """Calculate address balance from UTXOs"""
        utxo_set = {
            "tx1:0": {"amount": 100.0, "address": "alice"},
            "tx2:0": {"amount": 50.0, "address": "alice"},
            "tx3:0": {"amount": 25.0, "address": "bob"},
        }
        
        def get_balance(address):
            return sum(v["amount"] for v in utxo_set.values() if v["address"] == address)
            
        assert get_balance("alice") == 150.0
        assert get_balance("bob") == 25.0
        assert get_balance("charlie") == 0.0
        
    def test_balance_decreases_after_spend(self):
        """Balance decreases when UTXO is spent"""
        utxo_set = {"tx1:0": {"amount": 100.0, "address": "alice"}}
        
        initial_balance = utxo_set["tx1:0"]["amount"]
        
        # Alice spends
        del utxo_set["tx1:0"]
        
        final_balance = sum(v["amount"] for v in utxo_set.values() if v.get("address") == "alice")
        
        assert initial_balance == 100.0
        assert final_balance == 0.0
        
    def test_balance_after_receiving(self):
        """Balance increases when receiving payment"""
        utxo_set = {}
        
        # Bob receives payment
        tx = Transaction()
        tx.add_output(75.0, "bob")
        
        utxo_set[f"{tx.tx_id}:0"] = {"amount": 75.0, "address": "bob"}
        
        bob_balance = sum(v["amount"] for v in utxo_set.values() if v["address"] == "bob")
        assert bob_balance == 75.0


class TestTransactionChain:
    """Test chained transactions through UTXO model"""
    
    def test_spend_chain(self):
        """Chain of spends: A -> B -> C"""
        utxo_set = {}
        
        # Coinbase to Alice
        tx1 = Transaction.create_coinbase_transaction("alice", 50.0, 1)
        utxo_set[f"{tx1.tx_id}:0"] = {"amount": 50.0, "address": "alice"}
        
        # Alice pays Bob
        tx2 = Transaction()
        tx2.add_input(tx1.tx_id, 0)
        tx2.add_output(40.0, "bob")
        tx2.add_output(9.0, "alice")  # Change
        
        del utxo_set[f"{tx1.tx_id}:0"]
        utxo_set[f"{tx2.tx_id}:0"] = {"amount": 40.0, "address": "bob"}
        utxo_set[f"{tx2.tx_id}:1"] = {"amount": 9.0, "address": "alice"}
        
        # Bob pays Charlie
        tx3 = Transaction()
        tx3.add_input(tx2.tx_id, 0)
        tx3.add_output(35.0, "charlie")
        tx3.add_output(4.0, "bob")  # Change
        
        del utxo_set[f"{tx2.tx_id}:0"]
        utxo_set[f"{tx3.tx_id}:0"] = {"amount": 35.0, "address": "charlie"}
        utxo_set[f"{tx3.tx_id}:1"] = {"amount": 4.0, "address": "bob"}
        
        # Final balances
        def balance(addr):
            return sum(v["amount"] for v in utxo_set.values() if v["address"] == addr)
            
        assert balance("alice") == 9.0
        assert balance("bob") == 4.0
        assert balance("charlie") == 35.0
        
    def test_consolidation_transaction(self):
        """Consolidate multiple UTXOs into one"""
        utxo_set = {
            "tx1:0": {"amount": 10.0, "address": "alice"},
            "tx2:0": {"amount": 20.0, "address": "alice"},
            "tx3:0": {"amount": 30.0, "address": "alice"},
        }
        
        # Consolidate all into one UTXO
        tx = Transaction()
        tx.add_input("tx1", 0)
        tx.add_input("tx2", 0)
        tx.add_input("tx3", 0)
        tx.add_output(59.0, "alice")  # 1.0 fee
        
        # Apply
        del utxo_set["tx1:0"]
        del utxo_set["tx2:0"]
        del utxo_set["tx3:0"]
        utxo_set[f"{tx.tx_id}:0"] = {"amount": 59.0, "address": "alice"}
        
        assert len(utxo_set) == 1
        
    def test_split_transaction(self):
        """Split one UTXO into many"""
        utxo_set = {"big:0": {"amount": 100.0, "address": "whale"}}
        
        tx = Transaction()
        tx.add_input("big", 0)
        for i in range(10):
            tx.add_output(9.0, f"recipient_{i}")
        # 10.0 left as fee
        
        del utxo_set["big:0"]
        for i, out in enumerate(tx.outputs):
            utxo_set[f"{tx.tx_id}:{i}"] = {"amount": out.amount, "address": out.recipient_address}
            
        assert len(utxo_set) == 10
