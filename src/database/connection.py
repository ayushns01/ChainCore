"""
Database connection management for ChainCore
Handles PostgreSQL connections with proper error handling and connection pooling
"""

import psycopg2
import psycopg2.pool
import psycopg2.extras
import logging
import threading
import time
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from .config import get_psycopg2_config, DATABASE_CONFIG

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages PostgreSQL database connections with connection pooling"""
    
    def __init__(self):
        self.connection_pool = None
        self._lock = threading.Lock()
        self._initialized = False
        
    def initialize(self):
        """Initialize the database connection pool"""
        if self._initialized:
            return
            
        with self._lock:
            if self._initialized:
                return
                
            try:
                config = get_psycopg2_config()
                
                # Create connection pool
                self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=DATABASE_CONFIG['pool_size'],
                    **config
                )
                
                # Test the connection
                self._test_connection()
                
                self._initialized = True
                logger.info("✅ Database connection pool initialized successfully")
                logger.info(f"   📊 Pool size: {DATABASE_CONFIG['pool_size']} connections")
                logger.info(f"   🎯 Connected to: {config['host']}:{config['port']}/{config['database']}")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize database connection: {e}")
                raise DatabaseConnectionError(f"Database initialization failed: {e}")
    
    def _test_connection(self):
        """Test database connection"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result[0] != 1:
                    raise Exception("Database test query failed")
    
    @contextmanager
    def get_connection(self):
        """Get a database connection from the pool"""
        if not self._initialized:
            self.initialize()
            
        connection = None
        try:
            connection = self.connection_pool.getconn()
            yield connection
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            if connection:
                self.connection_pool.putconn(connection)
    
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
        """Execute a SQL query with optional parameters"""
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
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise DatabaseOperationError(f"Query failed: {e}")
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Execute a query multiple times with different parameters"""
        try:
            with self.get_cursor() as cursor:
                cursor.executemany(query, params_list)
                return cursor.rowcount
                
        except Exception as e:
            logger.error(f"Batch query execution failed: {e}")
            raise DatabaseOperationError(f"Batch query failed: {e}")
    
    def test_connection_health(self) -> bool:
        """Test if database connection is healthy"""
        try:
            result = self.execute_query("SELECT 1", fetch_one=True)
            return result is not None and result[0] == 1
        except Exception:
            return False
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get information about database connections"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        current_database() as database_name,
                        current_user as user_name,
                        version() as postgresql_version,
                        pg_database_size(current_database()) as database_size
                """)
                result = cursor.fetchone()
                
                # Get connection count
                cursor.execute("""
                    SELECT count(*) as active_connections
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                """)
                conn_result = cursor.fetchone()
                
                return {
                    'database_name': result['database_name'],
                    'user_name': result['user_name'],
                    'postgresql_version': result['postgresql_version'],
                    'database_size_bytes': result['database_size'],
                    'active_connections': conn_result['active_connections'],
                    'pool_size': DATABASE_CONFIG['pool_size']
                }
                
        except Exception as e:
            logger.error(f"Failed to get connection info: {e}")
            return {}
    
    def close_all_connections(self):
        """Close all database connections"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("🔄 All database connections closed")

class DatabaseConnectionError(Exception):
    """Raised when database connection fails"""
    pass

class DatabaseOperationError(Exception):
    """Raised when database operation fails"""
    pass

# Global database manager instance
db_manager = DatabaseManager()

def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance"""
    return db_manager

def init_database():
    """Initialize the database connection"""
    db_manager.initialize()

def test_database_connection() -> bool:
    """Test database connection and return True if successful"""
    try:
        db_manager.initialize()
        return db_manager.test_connection_health()
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False