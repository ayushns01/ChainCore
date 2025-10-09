#!/usr/bin/env python3
"""
Test transaction storage directly
"""
import sys
sys.path.append('src')

from data.transaction_dao import TransactionDAO
from data.simple_connection import get_simple_db_manager
from core.bitcoin_transaction import Transaction, TransactionInput, TransactionOutput
import time

def test_transaction_storage():
    """Test adding a transaction directly to the database"""
    print("🧪 TESTING TRANSACTION STORAGE")
    print("=" * 40)
    
    db = get_simple_db_manager()
    tx_dao = TransactionDAO()
    
    # Create a test coinbase transaction
    print("\n1. Creating test coinbase transaction...")
    
    # Coinbase input
    coinbase_input = TransactionInput(
        tx_id="0" * 64,
        output_index=0xFFFFFFFF,
        signature="coinbase_signature"
    )
    
    # Coinbase output
    miner_address = "18NDhHYAa3bx3jAZkc7HZf3vKr1JrwVXG3"  # Your miner address
    coinbase_output = TransactionOutput(
        recipient_address=miner_address,
        amount=50.0
    )
    
    # Create transaction
    tx = Transaction(
        inputs=[coinbase_input],
        outputs=[coinbase_output],
        timestamp=time.time()
    )
    
    print(f"   Transaction ID: {tx.tx_id}")
    print(f"   Is coinbase: {tx.is_coinbase()}")
    print(f"   Amount: {sum(output.amount for output in tx.outputs)} CC")
    print(f"   Recipient: {miner_address}")
    
    # Test transaction storage
    print("\n2. Testing transaction storage...")
    
    try:
        # First check if we can call to_dict on inputs/outputs
        print("   Testing input serialization...")
        input_dicts = [inp.to_dict() for inp in tx.inputs]
        print(f"   ✅ Input serialization: {len(input_dicts)} inputs")
        
        print("   Testing output serialization...")
        output_dicts = [out.to_dict() for out in tx.outputs]
        print(f"   ✅ Output serialization: {len(output_dicts)} outputs")
        
        # Try to add the transaction
        print("   Adding transaction to database...")
        success = tx_dao.add_transaction(tx, block_id=999, block_index=999)
        
        if success:
            print("   ✅ Transaction added successfully!")
            
            # Verify it was stored
            print("\n3. Verifying transaction storage...")
            stored_tx = tx_dao.get_transaction_by_id(tx.tx_id)
            if stored_tx:
                print(f"   ✅ Transaction found in database:")
                print(f"      ID: {stored_tx['transaction_id']}")
                print(f"      Type: {stored_tx['transaction_type']}")
                print(f"      Amount: {stored_tx['total_amount']}")
                print(f"      Coinbase: {stored_tx['is_coinbase']}")
            else:
                print("   ❌ Transaction not found in database")
            
            # Check UTXOs
            print("\n4. Checking UTXO creation...")
            utxos = tx_dao.get_utxos_for_address(miner_address)
            print(f"   UTXOs for {miner_address}: {len(utxos)}")
            
            for utxo in utxos:
                print(f"      {utxo['utxo_key']}: {utxo['amount']} CC")
            
            # Check balance
            print("\n5. Checking balance calculation...")
            balance = tx_dao.get_balance(miner_address)
            print(f"   Balance for {miner_address}: {balance} CC")
            
        else:
            print("   ❌ Transaction add failed")
            
    except Exception as e:
        print(f"   ❌ Error during transaction test: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
    
    # Cleanup - remove test transaction
    print("\n6. Cleaning up test data...")
    try:
        db.execute_query("DELETE FROM utxos WHERE transaction_id = %s", (tx.tx_id,))
        db.execute_query("DELETE FROM transactions WHERE transaction_id = %s", (tx.tx_id,))
        print("   ✅ Test data cleaned up")
    except Exception as e:
        print(f"   ⚠️ Cleanup error: {e}")
    
    print("\n" + "=" * 40)
    print("🏁 TRANSACTION STORAGE TEST COMPLETE")

if __name__ == "__main__":
    test_transaction_storage()