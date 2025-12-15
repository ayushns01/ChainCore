"""
Database configuration for ChainCore
"""

import os
from typing import Dict, Any

# Database connection settings
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5431)),
    'database': os.getenv('DB_NAME', 'chaincore_blockchain'),
    'user': os.getenv('DB_USER', 'chaincore_user'),
    'password': os.getenv('DB_PASSWORD', 'chaincore_secure_2024'),
    'sslmode': os.getenv('DB_SSLMODE', 'prefer'),
    
    # Connection pool settings
    'pool_size': 10,
    'max_overflow': 20,
    'pool_timeout': 30,
    'pool_recycle': 3600,
    'echo': False  # Set to True for SQL debugging
}

def get_database_url() -> str:
    """Get PostgreSQL connection URL"""
    config = DATABASE_CONFIG
    return (f"postgresql://{config['user']}:{config['password']}"
            f"@{config['host']}:{config['port']}/{config['database']}")

def get_psycopg2_config() -> Dict[str, Any]:
    """Get psycopg2 connection parameters"""
    return {
        'host': DATABASE_CONFIG['host'],
        'port': DATABASE_CONFIG['port'],
        'database': DATABASE_CONFIG['database'],
        'user': DATABASE_CONFIG['user'],
        'password': DATABASE_CONFIG['password'],
        'sslmode': DATABASE_CONFIG['sslmode']
    }

# Test connection settings
TEST_DATABASE_CONFIG = DATABASE_CONFIG.copy()
TEST_DATABASE_CONFIG['database'] = 'chaincore_test'

def get_test_database_url() -> str:
    """Get test database connection URL"""
    config = TEST_DATABASE_CONFIG
    return (f"postgresql://{config['user']}:{config['password']}"
            f"@{config['host']}:{config['port']}/{config['database']}")