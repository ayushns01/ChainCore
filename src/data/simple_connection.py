"""
Simplified database connection for ChainCore
No connection pooling - direct connections with proper timeouts
"""

import psycopg2
import psycopg2.extras
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class SimpleDBManager:
    """Simple database manager without connection pooling"""
    
    def __init__(self):
        self.config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'chaincore_blockchain',
            'user': 'chaincore_user',
            'password': 'chaincore_secure_2024',
            'connect_timeout': 5,
            'sslmode': 'prefer'
        }
        self._initialized = False
    
    def initialize(self):
        """Test connection and mark as initialized"""
        if self._initialized:
            return
            
        try:
            # Test connection
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result[0] != 1:
                    raise Exception("Database test query failed")
                cursor.close()
            
            self._initialized = True
            logger.info("✅ Simple database connection initialized")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get a direct database connection"""
        connection = None
        try:
            connection = psycopg2.connect(**self.config)
            yield connection
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"Database connection failed: {e}")
            raise
        finally:
            if connection:
                connection.close()
    
    @contextmanager
    def get_cursor(self, commit=True):
        """Get a database cursor with automatic commit/rollback"""
        with self.get_connection() as conn:
            try:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                yield cursor
                if commit:
                    conn.commit()
            except Exception as e:
                conn.rollback()
                raise
            finally:
                cursor.close()
    
    def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False, 
                     fetch_all: bool = False) -> Optional[Any]:
        """Execute a SQL query"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, params)
                
                if fetch_one:
                    return cursor.fetchone()
                elif fetch_all:
                    return cursor.fetchall()
                else:
                    return cursor.rowcount
                    
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def test_connection_health(self) -> bool:
        """Test if database connection is healthy"""
        try:
            result = self.execute_query("SELECT 1", fetch_one=True)
            return result is not None and result[0] == 1
        except Exception:
            return False
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get database connection information"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        current_database() as database_name,
                        current_user as user_name,
                        version() as postgresql_version
                """)
                result = cursor.fetchone()
                
                return {
                    'database_name': result['database_name'],
                    'user_name': result['user_name'],
                    'postgresql_version': result['postgresql_version'],
                    'connection_type': 'simple'
                }
        except Exception as e:
            logger.error(f"Failed to get connection info: {e}")
            return {}

# Global simple database manager
simple_db_manager = SimpleDBManager()

def get_simple_db_manager() -> SimpleDBManager:
    """Get the global simple database manager"""
    return simple_db_manager

def init_simple_database():
    """Initialize the simple database connection"""
    simple_db_manager.initialize()

def test_simple_database_connection() -> bool:
    """Test simple database connection"""
    try:
        simple_db_manager.initialize()
        return simple_db_manager.test_connection_health()
    except Exception as e:
        logger.error(f"Simple database connection test failed: {e}")
        return False