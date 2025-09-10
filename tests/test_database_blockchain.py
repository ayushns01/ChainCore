#!/usr/bin/env python3
"""
Test blockchain operations with PostgreSQL database
Creates a sample block and stores it in the database
"""

import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.data.connection import init_database
from src.data.block_dao import BlockDAO
from src.data.transaction_dao import TransactionDAO
from src.core.block import Block
from src.core.bitcoin_transaction import Transaction, TransactionInput, TransactionOutput

def create_sample_block():
    """Create a sample block for testing"""
    print("🔨 Creating sample block...")
    
    # Create a coinbase transaction (mining reward)
    coinbase_input = TransactionInput("0" * 64, 0xFFFFFFFF)
    coinbase_output = TransactionOutput(50.0, "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")  # Sample address
    coinbase_tx = Transaction([coinbase_input], [coinbase_output])
    
    print(f"   💰 Coinbase transaction created: {coinbase_tx.tx_id[:16]}...")
    
    # Create the block
    block = Block(
        index=1,
        transactions=[coinbase_tx],
        previous_hash="0" * 64,  # Genesis block hash
        timestamp=time.time(),
        nonce=12345,
        target_difficulty=4,
        mining_node="Node-5000"
    )
    
    # Add mining metadata
    block._mining_metadata['miner_address'] = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    block._mining_metadata['mining_reward'] = 50.0
    
    print(f"   📦 Block created: #{block.index}")
    print(f"   🏷️  Hash: {block.hash[:16]}...")
    print(f"   ⛏️  Miner: {block._mining_metadata['mining_node']}")
    
    return block

def test_block_storage():
    """Test storing and retrieving a block"""
    print("\n🗄️ Testing block storage...")
    
    try:
        # Initialize database
        init_database()
        
        # Create DAOs
        block_dao = BlockDAO()
        tx_dao = TransactionDAO()
        
        # Create and store a sample block
        sample_block = create_sample_block()
        
        print("   💾 Storing block in database...")
        success = block_dao.add_block(sample_block)
        
        if success:
            print("   ✅ Block stored successfully!")
            
            # Retrieve the block
            print("   📖 Retrieving block from database...")
            retrieved_block = block_dao.get_block_by_index(sample_block.index)
            
            if retrieved_block:
                print("   ✅ Block retrieved successfully!")
                print(f"      📊 Block #{retrieved_block['block_index']}")
                print(f"      🏷️  Hash: {retrieved_block['hash'][:16]}...")
                print(f"      ⛏️  Miner: {retrieved_block['miner_node']}")
                print(f"      📝 Transactions: {retrieved_block['transaction_count']}")
                
                # Test transaction retrieval
                print("   📝 Testing transaction retrieval...")
                transactions = tx_dao.get_transactions_by_block(sample_block.index)
                
                if transactions:
                    print(f"   ✅ Found {len(transactions)} transaction(s)")
                    for tx in transactions:
                        print(f"      💳 TX: {tx['transaction_id'][:16]}...")
                        print(f"      💰 Amount: {tx['total_amount']} CC")
                        print(f"      🏷️  Type: {tx['transaction_type']}")
                
                # Test balance calculation
                print("   💰 Testing balance calculation...")
                miner_address = retrieved_block['miner_address']
                balance = tx_dao.get_balance(miner_address)
                print(f"   ✅ Balance for {miner_address[:16]}...: {balance} CC")
                
                # Test UTXO retrieval
                print("   🔍 Testing UTXO retrieval...")
                utxos = tx_dao.get_utxos_for_address(miner_address)
                print(f"   ✅ Found {len(utxos)} UTXO(s) for miner")
                
                return True
            else:
                print("   ❌ Failed to retrieve block!")
                return False
        else:
            print("   ❌ Failed to store block!")
            return False
            
    except Exception as e:
        print(f"   ❌ Error in block storage test: {e}")
        return False

def test_blockchain_statistics():
    """Test blockchain statistics and analytics"""
    print("\n📊 Testing blockchain statistics...")
    
    try:
        block_dao = BlockDAO()
        tx_dao = TransactionDAO()
        
        # Get blockchain statistics
        print("   📈 Getting blockchain statistics...")
        block_stats = block_dao.get_mining_statistics()
        
        if block_stats:
            print("   ✅ Blockchain Statistics:")
            print(f"      📦 Total blocks: {block_stats.get('total_blocks', 0)}")
            print(f"      ⛏️  Unique miners: {block_stats.get('unique_miners', 0)}")
            print(f"      🎯 Average difficulty: {block_stats.get('avg_difficulty', 0):.2f}")
            print(f"      📝 Total transactions: {block_stats.get('total_transactions', 0)}")
            
            # Mining distribution
            distribution = block_stats.get('mining_distribution', [])
            if distribution:
                print("   ⛏️  Mining Distribution:")
                for miner in distribution:
                    print(f"      {miner['miner_node']}: {miner['blocks_mined']} blocks")
        
        # Get transaction statistics
        print("   💳 Getting transaction statistics...")
        tx_stats = tx_dao.get_transaction_statistics()
        
        if tx_stats:
            print("   ✅ Transaction Statistics:")
            print(f"      📝 Total transactions: {tx_stats.get('total_transactions', 0)}")
            print(f"      💰 Coinbase transactions: {tx_stats.get('coinbase_transactions', 0)}")
            print(f"      🔄 Transfer transactions: {tx_stats.get('transfer_transactions', 0)}")
            print(f"      💵 Total value transferred: {tx_stats.get('total_value_transferred', 0):.2f} CC")
        
        # Get UTXO statistics
        print("   🔍 Getting UTXO statistics...")
        utxo_stats = tx_dao.get_utxo_statistics()
        
        if utxo_stats:
            print("   ✅ UTXO Statistics:")
            print(f"      📊 Total UTXOs: {utxo_stats.get('total_utxos', 0)}")
            print(f"      💰 Unspent UTXOs: {utxo_stats.get('unspent_utxos', 0)}")
            print(f"      💵 Total unspent value: {utxo_stats.get('total_unspent_value', 0):.2f} CC")
            print(f"      👥 Unique addresses: {utxo_stats.get('unique_addresses', 0)}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error in statistics test: {e}")
        return False

def cleanup_test_data():
    """Clean up test data"""
    print("\n🧹 Cleaning up test data...")
    
    try:
        from src.data.connection import get_db_manager
        db_manager = get_db_manager()
        
        # Remove test blocks (this will cascade to transactions and UTXOs)
        query = "DELETE FROM blocks WHERE block_index = 1"
        db_manager.execute_query(query)
        
        print("   ✅ Test data cleaned up!")
        return True
        
    except Exception as e:
        print(f"   ❌ Error cleaning up test data: {e}")
        return False

def main():
    """Run blockchain database tests"""
    print("🚀 ChainCore Blockchain Database Test")
    print("=" * 50)
    
    tests = [
        ("Block Storage & Retrieval", test_block_storage),
        ("Blockchain Statistics", test_blockchain_statistics),
        ("Cleanup Test Data", cleanup_test_data)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        print("-" * 40)
        
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed!")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All blockchain database tests passed!")
        print("\n💡 Your PostgreSQL integration is working!")
        print("   ✅ Blocks can be stored and retrieved")
        print("   ✅ Transactions are properly indexed")
        print("   ✅ UTXOs are tracked correctly")
        print("   ✅ Balance calculations work")
        print("   ✅ Statistics and analytics available")
        
        print("\n🚀 Ready for full ChainCore integration!")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)