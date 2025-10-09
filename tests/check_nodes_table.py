#!/usr/bin/env python3
"""
Quick script to check nodes table structure
"""
import sys
sys.path.append('src')

from data.simple_connection import get_simple_db_manager

def check_nodes_table():
    db = get_simple_db_manager()
    
    # Check if nodes table exists
    table_check = db.execute_query(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'nodes'",
        fetch_one=True
    )
    
    if table_check:
        print("✅ NODES TABLE EXISTS")
        
        # Get column information
        columns = db.execute_query(
            """SELECT column_name, data_type, is_nullable, column_default 
               FROM information_schema.columns 
               WHERE table_schema = 'public' AND table_name = 'nodes' 
               ORDER BY ordinal_position""",
            fetch_all=True
        )
        
        print("\nNODES TABLE STRUCTURE:")
        for col in columns:
            print(f"  - {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'})")
            if col['column_default']:
                print(f"    DEFAULT: {col['column_default']}")
        
        # Check sample data
        sample = db.execute_query("SELECT * FROM nodes LIMIT 3", fetch_all=True)
        print(f"\nSAMPLE DATA ({len(sample)} rows):")
        for row in sample:
            print(f"  {dict(row)}")
            
    else:
        print("❌ NODES TABLE DOES NOT EXIST")
        
        # Show existing tables
        tables = db.execute_query(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name",
            fetch_all=True
        )
        print("\nEXISTING TABLES:")
        for table in tables:
            print(f"  - {table['table_name']}")

if __name__ == "__main__":
    check_nodes_table()