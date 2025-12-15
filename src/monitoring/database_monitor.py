#!/usr/bin/env python3
"""
Real-time ChainCore Database Monitor
Watch blocks being stored in PostgreSQL as they're mined
"""

import sys
import os
import time
import threading
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.data.simple_connection import get_simple_db_manager
from src.data.block_dao import BlockDAO
from src.data.transaction_dao import TransactionDAO

class DatabaseMonitor:
    """Real-time monitor for ChainCore PostgreSQL database"""
    
    def __init__(self):
        self.db_manager = get_simple_db_manager()
        self.block_dao = BlockDAO()
        self.tx_dao = TransactionDAO()
        
        # Tracking state
        self.last_block_count = 0
        self.last_tx_count = 0
        self.start_time = time.time()
        self.running = False
    
    def start_monitoring(self, refresh_interval: float = 2.0):
        """Start real-time monitoring"""
        print("ChainCore Database Monitor Starting...")
        print("=" * 60)
        
        try:
            self.db_manager.initialize()
            print("Connected to PostgreSQL database")
            # Show which database we're monitoring using actual config
            conn_info = self.db_manager.get_connection_info()
            db_name = conn_info.get('database_name', 'unknown')
            user_name = conn_info.get('user_name', 'unknown')
            print(f"Monitoring database: {db_name} (shared by all nodes)")
            print(f"Connection: postgresql://{user_name}:***@{self.db_manager.config['host']}:{self.db_manager.config['port']}/{db_name}")
        except Exception as e:
            print(f"Database connection failed: {e}")
            print("Ensure PostgreSQL is running and chaincore database exists")
            return
        
        self.running = True
        self.last_block_count = self.block_dao.get_blockchain_length()
        
        print(f"Initial blockchain length: {self.last_block_count}")
        print(f"Monitoring every {refresh_interval}s (Press Ctrl+C to stop)")
        print("=" * 60)
        
        try:
            while self.running:
                self._check_for_updates()
                time.sleep(refresh_interval)
                
        except KeyboardInterrupt:
            print("\nMonitor stopped by user")
            self.running = False
    
    def _check_for_updates(self):
        """Check for new blocks and transactions"""
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            
            # Check blocks
            current_block_count = self.block_dao.get_blockchain_length()
            if current_block_count > self.last_block_count:
                # New blocks detected!
                new_blocks = current_block_count - self.last_block_count
                print(f"\n[{current_time}] NEW BLOCK(S) DETECTED!")
                
                # Get details of new blocks
                for i in range(self.last_block_count, current_block_count):
                    block_data = self.block_dao.get_block_by_index(i)
                    if block_data:
                        self._display_new_block(block_data)
                
                self.last_block_count = current_block_count
                self._display_summary()
            else:
                # FIXED: No new blocks, show network status
                print(f"[{current_time}] Chain: {current_block_count} blocks | Monitoring...")
                self._show_network_activity()
        
        except Exception as e:
            print(f"Monitor error: {e}")
    
    def _show_network_activity(self):
        """Show which nodes are currently active"""
        import requests
        active_nodes = []
        
        # Check common node ports
        for port in range(5000, 5010):
            try:
                response = requests.get(f"http://localhost:{port}/status", timeout=1)
                if response.status_code == 200:
                    data = response.json()
                    node_id = data.get('node_id', f'port-{port}')
                    chain_length = data.get('blockchain_length', 0)
                    peers = data.get('peers', 0)
                    active_nodes.append(f"{node_id}(chain: {chain_length}, peers: {peers})")
            except:
                continue
        
        if active_nodes:
            print(f"   Active nodes: {', '.join(active_nodes)}")
        else:
            print(f"   No active nodes detected - database may not be updating")
    
    def _display_new_block(self, block_data):
        """Display details of a new block"""
        try:
            print(f"   Block #{block_data['block_index']}")
            print(f"      Hash: {block_data['hash'][:16]}...{block_data['hash'][-8:]}")
            print(f"      Miner: {block_data['miner_node']} ({block_data['miner_address'][:16]}...)")
            print(f"      Difficulty: {block_data['difficulty']}")
            print(f"      Transactions: {block_data.get('transaction_count', 0)}")
            print(f"      Time: {datetime.fromtimestamp(block_data['timestamp']).strftime('%H:%M:%S')}")
            
            # Show transactions in this block
            transactions = self.tx_dao.get_transactions_by_block(block_data['block_index'])
            for tx in transactions:
                if tx['is_coinbase']:
                    print(f"         Coinbase: +{tx['total_amount']:.2f} CC -> {block_data['miner_address'][:16]}...")
                else:
                    print(f"         Transfer: {tx['total_amount']:.2f} CC")
            
        except Exception as e:
            print(f"      Error displaying block: {e}")
    
    def _display_summary(self):
        """Display current blockchain summary"""
        try:
            stats = self.block_dao.get_mining_statistics()
            utxo_stats = self.tx_dao.get_utxo_statistics()
            
            runtime = time.time() - self.start_time
            runtime_str = f"{int(runtime//3600)}h {int((runtime%3600)//60)}m {int(runtime%60)}s"
            
            print("\nBLOCKCHAIN SUMMARY")
            print(f"   Total Blocks: {stats.get('total_blocks', 0)}")
            print(f"   Active Miners: {stats.get('unique_miners', 0)}")
            print(f"   Total UTXOs: {utxo_stats.get('unspent_utxos', 0)}")
            print(f"   Total Value: {utxo_stats.get('total_unspent_value', 0):.2f} CC")
            print(f"   Monitor Runtime: {runtime_str}")
            
            # Show mining distribution
            distribution = stats.get('mining_distribution', [])
            if distribution:
                print(f"   Top Miners:")
                for i, miner in enumerate(distribution[:3], 1):
                    print(f"      #{i} {miner['miner_node']}: {miner['blocks_mined']} blocks")
            
            print("=" * 60)
            
        except Exception as e:
            print(f"Error displaying summary: {e}")
    
    def display_current_state(self):
        """Display current database state"""
        print("\nCURRENT DATABASE STATE")
        print("=" * 40)
        
        try:
            # Connection info
            conn_info = self.db_manager.get_connection_info()
            print(f"Database: {conn_info.get('database_name')}")
            print(f"Size: {conn_info.get('database_size_bytes', 0):,} bytes")
            
            # Blockchain stats
            block_count = self.block_dao.get_blockchain_length()
            print(f"Blockchain: {block_count} blocks")
            
            if block_count > 0:
                latest = self.block_dao.get_latest_block()
                if latest:
                    print(f"Latest Block: #{latest['block_index']}")
                    print(f"   Hash: {latest['hash'][:16]}...{latest['hash'][-8:]}")
                    print(f"   Miner: {latest['miner_node']}")
                    
            # Rich list
            rich_list = self.tx_dao.get_rich_list(3)
            if rich_list:
                print(f"Top Balances:")
                for addr in rich_list:
                    print(f"   {addr['address'][:16]}...: {addr['balance']:.2f} CC")
            
        except Exception as e:
            print(f"Error displaying state: {e}")

def main():
    """Main monitor function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ChainCore Database Monitor')
    parser.add_argument('--interval', type=float, default=2.0, help='Refresh interval in seconds')
    parser.add_argument('--status-only', action='store_true', help='Show current status and exit')
    
    args = parser.parse_args()
    
    monitor = DatabaseMonitor()
    
    if args.status_only:
        monitor.display_current_state()
    else:
        print("ChainCore PostgreSQL Database Monitor")
        print("   Watch blocks being stored in real-time!")
        print("   Start mining in another terminal to see live updates")
        print("")
        
        monitor.start_monitoring(args.interval)

if __name__ == "__main__":
    main()
