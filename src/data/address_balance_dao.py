"""
Address Balance Data Access Object for ChainCore
Handles all database operations related to address balances
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from .simple_connection import get_simple_db_manager

logger = logging.getLogger(__name__)

class AddressBalanceDAO:
    """Data Access Object for address balances"""
    
    def __init__(self):
        self.db = get_simple_db_manager()
    
    def insert_new_address(self, address: str, initial_balance: float = 0.0) -> bool:
        """Insert a new address into the address_balances table"""
        try:
            query = """
                INSERT INTO address_balances (
                    address, balance, utxo_count, last_activity_block, updated_at
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (address) DO NOTHING
            """
            params = (
                address,
                initial_balance,
                0,  # utxo_count starts at 0
                0,  # last_activity_block starts at 0 (no activity yet)
                datetime.now()
            )
            
            rows_affected = self.db.execute_query(query, params)
            
            if rows_affected > 0:
                logger.info(f"✅ New address inserted into address_balances: {address}")
                return True
            else:
                logger.info(f"ℹ️ Address already exists in address_balances: {address}")
                return True  # Still consider success since address is tracked
                
        except Exception as e:
            logger.error(f"❌ Failed to insert new address {address}: {e}")
            return False
    
    def get_address_balance(self, address: str) -> Optional[Dict[str, Any]]:
        """Get balance information for a specific address"""
        try:
            query = """
                SELECT address, balance, utxo_count, last_activity_block, updated_at
                FROM address_balances 
                WHERE address = %s
            """
            result = self.db.execute_query(query, (address,), fetch_one=True)
            
            if result:
                return {
                    'address': result['address'],
                    'balance': float(result['balance']),
                    'utxo_count': result['utxo_count'],
                    'last_activity_block': result['last_activity_block'],
                    'updated_at': result['updated_at']
                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get address balance for {address}: {e}")
            return None
    
    def address_exists(self, address: str) -> bool:
        """Check if an address exists in the address_balances table"""
        try:
            query = "SELECT 1 FROM address_balances WHERE address = %s"
            result = self.db.execute_query(query, (address,), fetch_one=True)
            return result is not None
            
        except Exception as e:
            logger.error(f"❌ Failed to check address existence for {address}: {e}")
            return False
    
    def update_address_balance(self, address: str, new_balance: float, 
                             utxo_count: int, last_activity_block: int = 0) -> bool:
        """Update balance information for an existing address"""
        try:
            query = """
                UPDATE address_balances 
                SET balance = %s, utxo_count = %s, last_activity_block = %s, updated_at = %s
                WHERE address = %s
            """
            params = (
                new_balance,
                utxo_count,
                last_activity_block,
                datetime.now(),
                address
            )
            
            rows_affected = self.db.execute_query(query, params)
            
            if rows_affected > 0:
                logger.debug(f"✅ Updated address balance: {address} -> {new_balance}")
                return True
            else:
                logger.warning(f"⚠️ No rows updated for address: {address}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to update address balance for {address}: {e}")
            return False
    
    def ensure_address_tracked(self, address: str, initial_balance: float = 0.0) -> bool:
        """Ensure an address is tracked in the address_balances table (insert if not exists)"""
        try:
            if not self.address_exists(address):
                return self.insert_new_address(address, initial_balance)
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to ensure address tracking for {address}: {e}")
            return False
    
    def get_all_addresses(self) -> list:
        """Get all addresses from the address_balances table"""
        try:
            query = """
                SELECT address, balance, utxo_count, last_activity_block, updated_at
                FROM address_balances 
                ORDER BY updated_at DESC
            """
            results = self.db.execute_query(query, fetch_all=True)
            
            if results:
                return [
                    {
                        'address': row['address'],
                        'balance': float(row['balance']),
                        'utxo_count': row['utxo_count'],
                        'last_activity_block': row['last_activity_block'],
                        'updated_at': row['updated_at']
                    }
                    for row in results
                ]
            return []
            
        except Exception as e:
            logger.error(f"❌ Failed to get all addresses: {e}")
            return []
    
    def refresh_all_balances(self) -> bool:
        """Trigger the refresh_address_balances SQL function to rebuild all balances"""
        try:
            query = "SELECT refresh_address_balances()"
            self.db.execute_query(query)
            logger.info("✅ Address balances refreshed from blockchain data")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to refresh address balances: {e}")
            return False