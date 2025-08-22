"""
Transaction Data Access Object for ChainCore
Handles all database operations related to transactions and UTXOs
"""

import json
import logging
from typing import List, Dict, Optional, Any
from decimal import Decimal

from .connection import get_db_manager
from ..blockchain.bitcoin_transaction import Transaction

logger = logging.getLogger(__name__)

class TransactionDAO:
    """Data Access Object for transactions and UTXOs"""
    
    def __init__(self):
        self.db = get_db_manager()
    
    def add_transaction(self, transaction: Transaction, block_id: int, block_index: int) -> bool:
        """Add a transaction to the database"""
        try:
            # Calculate transaction details
            total_amount = sum(output.amount for output in transaction.outputs)
            is_coinbase = transaction.is_coinbase()
            
            # Insert transaction
            query = """
                INSERT INTO transactions (
                    transaction_id, block_id, block_index, transaction_type,
                    inputs_json, outputs_json, total_amount, is_coinbase, timestamp
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            params = (
                transaction.tx_id,
                block_id,
                block_index,
                'coinbase' if is_coinbase else 'transfer',
                json.dumps([inp.to_dict() for inp in transaction.inputs]),
                json.dumps([out.to_dict() for out in transaction.outputs]),
                float(total_amount),
                is_coinbase,
                float(transaction.timestamp)
            )
            
            result = self.db.execute_query(query, params, fetch_one=True)
            
            if result:
                # Update UTXOs
                self._update_utxos(transaction, block_index)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error adding transaction {transaction.tx_id}: {e}")
            return False
    
    def _update_utxos(self, transaction: Transaction, block_index: int):
        """Update UTXO set for this transaction"""
        try:
            # Mark spent UTXOs (from inputs)
            if not transaction.is_coinbase():
                for tx_input in transaction.inputs:
                    utxo_key = f"{tx_input.tx_id}:{tx_input.output_index}"
                    
                    query = """
                        UPDATE utxos 
                        SET is_spent = TRUE, spent_in_transaction = %s
                        WHERE utxo_key = %s
                    """
                    self.db.execute_query(query, (transaction.tx_id, utxo_key))
            
            # Add new UTXOs (from outputs)
            for i, output in enumerate(transaction.outputs):
                utxo_key = f"{transaction.tx_id}:{i}"
                
                query = """
                    INSERT INTO utxos (
                        utxo_key, transaction_id, output_index, 
                        recipient_address, amount, block_index
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """
                params = (
                    utxo_key,
                    transaction.tx_id,
                    i,
                    output.recipient_address,
                    float(output.amount),
                    block_index
                )
                
                self.db.execute_query(query, params)
                
        except Exception as e:
            logger.error(f"Error updating UTXOs for transaction {transaction.tx_id}: {e}")
    
    def get_transaction_by_id(self, tx_id: str) -> Optional[Dict]:
        """Get a transaction by its ID"""
        try:
            query = """
                SELECT * FROM transactions WHERE transaction_id = %s
            """
            result = self.db.execute_query(query, (tx_id,), fetch_one=True)
            
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error getting transaction {tx_id}: {e}")
            return None
    
    def get_transactions_by_block(self, block_index: int) -> List[Dict]:
        """Get all transactions in a block"""
        try:
            query = """
                SELECT * FROM transactions 
                WHERE block_index = %s
                ORDER BY id
            """
            results = self.db.execute_query(query, (block_index,), fetch_all=True)
            
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"Error getting transactions for block {block_index}: {e}")
            return []
    
    def get_transactions_by_address(self, address: str, limit: int = 100) -> List[Dict]:
        """Get transactions involving a specific address"""
        try:
            query = """
                SELECT DISTINCT t.* FROM transactions t
                WHERE t.inputs_json::text LIKE %s 
                   OR t.outputs_json::text LIKE %s
                ORDER BY t.timestamp DESC
                LIMIT %s
            """
            
            search_pattern = f'%{address}%'
            results = self.db.execute_query(
                query, 
                (search_pattern, search_pattern, limit), 
                fetch_all=True
            )
            
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"Error getting transactions for address {address}: {e}")
            return []
    
    def get_balance(self, address: str) -> float:
        """Get current balance for an address"""
        try:
            query = """
                SELECT COALESCE(SUM(amount), 0) as balance
                FROM utxos 
                WHERE recipient_address = %s AND is_spent = FALSE
            """
            result = self.db.execute_query(query, (address,), fetch_one=True)
            
            if result:
                return float(result[0])
            return 0.0
            
        except Exception as e:
            logger.error(f"Error getting balance for address {address}: {e}")
            return 0.0
    
    def get_utxos_for_address(self, address: str) -> List[Dict]:
        """Get all unspent UTXOs for an address"""
        try:
            query = """
                SELECT * FROM utxos 
                WHERE recipient_address = %s AND is_spent = FALSE
                ORDER BY amount DESC
            """
            results = self.db.execute_query(query, (address,), fetch_all=True)
            
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"Error getting UTXOs for address {address}: {e}")
            return []
    
    def get_transaction_statistics(self) -> Dict[str, Any]:
        """Get comprehensive transaction statistics"""
        try:
            query = """
                SELECT 
                    COUNT(*) as total_transactions,
                    COUNT(*) FILTER (WHERE is_coinbase = TRUE) as coinbase_transactions,
                    COUNT(*) FILTER (WHERE is_coinbase = FALSE) as transfer_transactions,
                    AVG(total_amount) as avg_transaction_amount,
                    SUM(total_amount) as total_value_transferred,
                    MAX(total_amount) as largest_transaction,
                    COUNT(DISTINCT block_index) as blocks_with_transactions
                FROM transactions
            """
            result = self.db.execute_query(query, fetch_one=True)
            
            if result:
                stats = dict(result)
                
                # Get top addresses by transaction count
                query2 = """
                    SELECT 
                        recipient_address,
                        COUNT(*) as transaction_count,
                        SUM(amount) as total_received
                    FROM utxos
                    GROUP BY recipient_address
                    ORDER BY transaction_count DESC
                    LIMIT 10
                """
                top_addresses = self.db.execute_query(query2, fetch_all=True)
                stats['top_addresses'] = [dict(row) for row in top_addresses] if top_addresses else []
                
                return stats
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting transaction statistics: {e}")
            return {}
    
    def get_utxo_statistics(self) -> Dict[str, Any]:
        """Get UTXO set statistics"""
        try:
            query = """
                SELECT 
                    COUNT(*) as total_utxos,
                    COUNT(*) FILTER (WHERE is_spent = FALSE) as unspent_utxos,
                    COUNT(*) FILTER (WHERE is_spent = TRUE) as spent_utxos,
                    SUM(amount) FILTER (WHERE is_spent = FALSE) as total_unspent_value,
                    AVG(amount) FILTER (WHERE is_spent = FALSE) as avg_utxo_value,
                    COUNT(DISTINCT recipient_address) as unique_addresses
                FROM utxos
            """
            result = self.db.execute_query(query, fetch_one=True)
            
            if result:
                return dict(result)
            return {}
            
        except Exception as e:
            logger.error(f"Error getting UTXO statistics: {e}")
            return {}
    
    def refresh_address_balances(self):
        """Refresh the materialized view for address balances"""
        try:
            query = "REFRESH MATERIALIZED VIEW address_balances"
            self.db.execute_query(query)
            logger.info("✅ Address balances materialized view refreshed")
            
        except Exception as e:
            logger.error(f"Error refreshing address balances: {e}")
    
    def get_rich_list(self, limit: int = 100) -> List[Dict]:
        """Get addresses with highest balances"""
        try:
            # First refresh the materialized view
            self.refresh_address_balances()
            
            query = """
                SELECT * FROM address_balances
                ORDER BY balance DESC
                LIMIT %s
            """
            results = self.db.execute_query(query, (limit,), fetch_all=True)
            
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"Error getting rich list: {e}")
            return []