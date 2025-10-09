#!/usr/bin/env python3
"""
Diagnostic script to check mining balance issues
"""
import sys
sys.path.append('src')

from data.simple_connection import get_simple_db_manager

def diagnose_mining_balance_issue():
    """Diagnose why mining balances aren't updating"""
    print("🔍 DIAGNOSING MINING BALANCE ISSUE")
    print("=" * 50)
    
    db = get_simple_db_manager()
    
    # 1. Check if we have any blocks in database
    print("\n1. CHECKING BLOCKS TABLE:")
    blocks = db.execute_query("SELECT COUNT(*) as count FROM blocks", fetch_one=True)
    block_count = blocks['count'] if blocks else 0
    print(f"   Total blocks in database: {block_count}")
    
    if block_count > 0:
        # Show recent blocks
        recent_blocks = db.execute_query("""
            SELECT block_index, hash, miner_address, transaction_count, created_at 
            FROM blocks 
            ORDER BY block_index DESC 
            LIMIT 5
        """, fetch_all=True)
        
        print("   Recent blocks:")
        for block in recent_blocks:
            print(f"     Block #{block['block_index']}: miner={block['miner_address'][:16] if block['miner_address'] else 'None'}...")
    
    # 2. Check if we have any transactions
    print("\n2. CHECKING TRANSACTIONS TABLE:")
    transactions = db.execute_query("SELECT COUNT(*) as count FROM transactions", fetch_one=True)
    tx_count = transactions['count'] if transactions else 0
    print(f"   Total transactions in database: {tx_count}")
    
    if tx_count > 0:
        # Show coinbase transactions
        coinbase_txs = db.execute_query("""
            SELECT transaction_id, block_index, total_amount, is_coinbase, outputs_json
            FROM transactions 
            WHERE is_coinbase = TRUE
            ORDER BY block_index DESC 
            LIMIT 5
        """, fetch_all=True)
        
        print("   Recent coinbase transactions:")
        for tx in coinbase_txs:
            print(f"     Block #{tx['block_index']}: {tx['total_amount']} CC (coinbase: {tx['is_coinbase']})")
            
            # Check the outputs to see the recipient
            import json
            outputs = json.loads(tx['outputs_json']) if tx['outputs_json'] else []
            for output in outputs:
                recipient = output.get('recipient_address', 'unknown')
                amount = output.get('amount', 0)
                print(f"       → {amount} CC to {recipient[:16]}...{recipient[-8:] if len(recipient) > 16 else ''}")
    
    # 3. Check if we have any UTXOs
    print("\n3. CHECKING UTXOS TABLE:")
    utxos = db.execute_query("SELECT COUNT(*) as count FROM utxos", fetch_one=True)
    utxo_count = utxos['count'] if utxos else 0
    print(f"   Total UTXOs in database: {utxo_count}")
    
    if utxo_count > 0:
        # Show unspent UTXOs
        unspent_utxos = db.execute_query("""
            SELECT recipient_address, amount, block_index, is_spent, transaction_id
            FROM utxos 
            WHERE is_spent = FALSE
            ORDER BY block_index DESC 
            LIMIT 10
        """, fetch_all=True)
        
        print("   Recent unspent UTXOs:")
        for utxo in unspent_utxos:
            recipient = utxo['recipient_address']
            amount = utxo['amount']
            block = utxo['block_index']
            print(f"     Block #{block}: {amount} CC → {recipient[:16]}...{recipient[-8:] if len(recipient) > 16 else ''}")
    
    # 4. Check balance calculation for a specific address
    print("\n4. TESTING BALANCE CALCULATION:")
    
    # Get a mining address from recent coinbase transactions
    test_address = None
    if tx_count > 0:
        recent_coinbase = db.execute_query("""
            SELECT outputs_json FROM transactions 
            WHERE is_coinbase = TRUE 
            ORDER BY block_index DESC 
            LIMIT 1
        """, fetch_one=True)
        
        if recent_coinbase and recent_coinbase['outputs_json']:
            import json
            outputs = json.loads(recent_coinbase['outputs_json'])
            if outputs:
                test_address = outputs[0].get('recipient_address')
    
    if test_address:
        print(f"   Testing address: {test_address}")
        
        # Manual balance calculation
        manual_balance = db.execute_query("""
            SELECT COALESCE(SUM(amount), 0) as balance
            FROM utxos 
            WHERE recipient_address = %s AND is_spent = FALSE
        """, (test_address,), fetch_one=True)
        
        balance = manual_balance['balance'] if manual_balance else 0
        print(f"   Manual balance calculation: {balance} CC")
        
        # Check UTXOs for this address
        address_utxos = db.execute_query("""
            SELECT utxo_key, amount, block_index, is_spent, transaction_id
            FROM utxos 
            WHERE recipient_address = %s
            ORDER BY block_index DESC
        """, (test_address,), fetch_all=True)
        
        print(f"   UTXOs for this address: {len(address_utxos)}")
        for utxo in address_utxos[:5]:  # Show first 5
            spent_status = "SPENT" if utxo['is_spent'] else "UNSPENT"
            print(f"     {utxo['utxo_key']}: {utxo['amount']} CC ({spent_status})")
    
    # 5. Check if address_balances view is populated
    print("\n5. CHECKING ADDRESS_BALANCES VIEW:")
    try:
        view_balances = db.execute_query("""
            SELECT address, balance, utxo_count 
            FROM address_balances 
            ORDER BY balance DESC 
            LIMIT 10
        """, fetch_all=True)
        
        if view_balances:
            print(f"   Address balances view has {len(view_balances)} entries:")
            for addr_bal in view_balances:
                addr = addr_bal['address']
                balance = addr_bal['balance']
                utxo_count = addr_bal['utxo_count']
                print(f"     {addr[:16]}...{addr[-8:] if len(addr) > 16 else ''}: {balance} CC ({utxo_count} UTXOs)")
        else:
            print("   Address balances view is empty")
            
        # Try refreshing the view
        print("   Refreshing materialized view...")
        db.execute_query("REFRESH MATERIALIZED VIEW address_balances")
        print("   ✅ View refreshed")
        
    except Exception as e:
        print(f"   ❌ Error with address_balances view: {e}")
    
    # 6. Summary and recommendations
    print("\n6. DIAGNOSTIC SUMMARY:")
    print("=" * 30)
    
    if block_count == 0:
        print("❌ NO BLOCKS: No blocks found in database")
        print("   → Mining may not be storing blocks to database")
        print("   → Check if database_enabled is True in blockchain")
        
    elif tx_count == 0:
        print("❌ NO TRANSACTIONS: Blocks exist but no transactions stored")
        print("   → Block storage is working but transaction storage is failing")
        print("   → Check _add_block_transactions method")
        
    elif utxo_count == 0:
        print("❌ NO UTXOS: Transactions exist but no UTXOs created")
        print("   → Transaction storage working but UTXO creation failing")
        print("   → Check _update_utxos method in TransactionDAO")
        
    else:
        print("✅ DATABASE STRUCTURE: Blocks, transactions, and UTXOs are being created")
        if test_address and balance > 0:
            print("✅ BALANCE CALCULATION: Balances are calculating correctly")
            print("   → The system is working properly")
            print("   → Check that you're querying the right address")
        else:
            print("⚠️  BALANCE ISSUE: UTXOs exist but balance calculation may be wrong")
            print("   → Check if you're using the correct miner address")
            print("   → Verify the /balance endpoint is working")
    
    print("\n" + "=" * 50)
    print("🏁 DIAGNOSTIC COMPLETE")

if __name__ == "__main__":
    diagnose_mining_balance_issue()