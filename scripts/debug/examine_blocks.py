#!/usr/bin/env python3
"""
Examine the blocks that were mined to see why they have no transactions
"""
import sys
sys.path.append('src')

from data.simple_connection import get_simple_db_manager
import json

def examine_mined_blocks():
    """Examine the structure of blocks that were mined"""
    print("🔍 EXAMINING MINED BLOCKS")
    print("=" * 40)
    
    db = get_simple_db_manager()
    
    # Get the raw block data
    print("\n1. GETTING BLOCK DATA FROM DATABASE:")
    blocks = db.execute_query("""
        SELECT 
            block_index, 
            hash, 
            miner_address, 
            transaction_count, 
            raw_data,
            created_at
        FROM blocks 
        ORDER BY block_index DESC 
        LIMIT 3
    """, fetch_all=True)
    
    for block in blocks:
        print(f"\n📦 BLOCK #{block['block_index']}:")
        print(f"   Hash: {block['hash'][:32]}...")
        print(f"   Miner: {block['miner_address']}")
        print(f"   Transaction Count: {block['transaction_count']}")
        print(f"   Created: {block['created_at']}")
        
        # Examine raw block data
        if block['raw_data']:
            try:
                raw_data = block['raw_data']
                if isinstance(raw_data, str):
                    raw_data = json.loads(raw_data)
                
                print(f"   Raw Data Structure:")
                print(f"      Index: {raw_data.get('index', 'missing')}")
                print(f"      Timestamp: {raw_data.get('timestamp', 'missing')}")
                print(f"      Previous Hash: {raw_data.get('previous_hash', 'missing')[:16]}..." if raw_data.get('previous_hash') else "      Previous Hash: missing")
                print(f"      Nonce: {raw_data.get('nonce', 'missing')}")
                print(f"      Difficulty: {raw_data.get('difficulty', 'missing')}")
                
                # Check transactions in raw data
                transactions = raw_data.get('transactions', [])
                print(f"      Transactions in raw_data: {len(transactions)}")
                
                if transactions:
                    print(f"      Transaction Details:")
                    for i, tx in enumerate(transactions):
                        tx_id = tx.get('tx_id', 'unknown')
                        inputs_count = len(tx.get('inputs', []))
                        outputs_count = len(tx.get('outputs', []))
                        is_coinbase = tx.get('is_coinbase', False)
                        
                        print(f"         TX {i+1}: {tx_id[:16]}... (coinbase: {is_coinbase})")
                        print(f"                Inputs: {inputs_count}, Outputs: {outputs_count}")
                        
                        # Show outputs for coinbase transactions
                        if is_coinbase and outputs_count > 0:
                            outputs = tx.get('outputs', [])
                            for j, output in enumerate(outputs):
                                recipient = output.get('recipient_address', 'unknown')
                                amount = output.get('amount', 0)
                                print(f"                Output {j+1}: {amount} CC → {recipient[:16]}...{recipient[-8:] if len(recipient) > 16 else ''}")
                else:
                    print(f"      ❌ NO TRANSACTIONS in raw block data!")
                    
            except Exception as e:
                print(f"   ❌ Error parsing raw data: {e}")
        else:
            print(f"   ❌ NO RAW DATA stored for this block")
    
    # Check if there's a pattern - maybe genesis block vs mined blocks
    print(f"\n2. ANALYZING BLOCK PATTERNS:")
    
    # Check genesis block
    genesis = db.execute_query("""
        SELECT block_index, transaction_count, raw_data 
        FROM blocks 
        WHERE block_index = 0 
        LIMIT 1
    """, fetch_one=True)
    
    if genesis:
        print(f"   Genesis Block (index 0):")
        print(f"      Transaction Count: {genesis['transaction_count']}")
        
        if genesis['raw_data']:
            try:
                genesis_data = genesis['raw_data']
                if isinstance(genesis_data, str):
                    genesis_data = json.loads(genesis_data)
                
                genesis_txs = genesis_data.get('transactions', [])
                print(f"      Transactions in genesis: {len(genesis_txs)}")
                
                if genesis_txs:
                    print(f"      Genesis has transactions - this is normal")
                else:
                    print(f"      Genesis has no transactions - this might be the issue")
                    
            except Exception as e:
                print(f"      Error parsing genesis data: {e}")
    
    # Check if recent blocks should have transactions
    recent_non_genesis = db.execute_query("""
        SELECT COUNT(*) as count 
        FROM blocks 
        WHERE block_index > 0 AND transaction_count > 0
    """, fetch_one=True)
    
    non_genesis_count = recent_non_genesis['count'] if recent_non_genesis else 0
    total_non_genesis = db.execute_query("""
        SELECT COUNT(*) as count 
        FROM blocks 
        WHERE block_index > 0
    """, fetch_one=True)['count']
    
    print(f"\n3. BLOCK TRANSACTION SUMMARY:")
    print(f"   Non-genesis blocks: {total_non_genesis}")
    print(f"   Non-genesis blocks with transactions: {non_genesis_count}")
    print(f"   Non-genesis blocks without transactions: {total_non_genesis - non_genesis_count}")
    
    if total_non_genesis > 0 and non_genesis_count == 0:
        print(f"\n❌ PROBLEM IDENTIFIED:")
        print(f"   All mined blocks (non-genesis) have 0 transactions!")
        print(f"   This means:")
        print(f"   1. Block templates are created without coinbase transactions")
        print(f"   2. OR coinbase transactions are not being included in blocks")
        print(f"   3. OR transactions are being stripped during block creation/storage")
        
        print(f"\n🔧 NEXT STEPS:")
        print(f"   1. Check block template creation in /mine_block endpoint")
        print(f"   2. Check if coinbase transactions are included in templates")
        print(f"   3. Check if transactions survive the mining process")
        print(f"   4. Check if _add_block_transactions is being called")
    
    print(f"\n" + "=" * 40)
    print("🏁 BLOCK EXAMINATION COMPLETE")

if __name__ == "__main__":
    examine_mined_blocks()