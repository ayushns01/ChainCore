#!/usr/bin/env python3
"""
Quick verification script for nodes table mining statistics
"""
import sys
sys.path.append('src')

from data.simple_connection import get_simple_db_manager

def verify_mining_stats():
    """Quick check of mining statistics in nodes table"""
    db = get_simple_db_manager()
    
    print("📊 NODES TABLE MINING STATISTICS")
    print("=" * 60)
    
    # Get all nodes with their stats
    nodes = db.execute_query("""
        SELECT 
            node_id, 
            status, 
            blocks_mined, 
            total_rewards, 
            api_port,
            last_seen,
            created_at
        FROM nodes 
        ORDER BY blocks_mined DESC, created_at DESC
    """, fetch_all=True)
    
    if nodes:
        print(f"\nFound {len(nodes)} registered nodes:\n")
        
        # Header
        print(f"{'NODE_ID':<15} {'STATUS':<8} {'BLOCKS':<7} {'REWARDS':<10} {'PORT':<6} {'LAST_SEEN':<20}")
        print("-" * 70)
        
        total_blocks = 0
        total_rewards = 0
        
        for node in nodes:
            node_id = node['node_id'][:14]  # Truncate long IDs
            status = node['status']
            blocks = node['blocks_mined'] or 0
            rewards = float(node['total_rewards']) if node['total_rewards'] else 0.0
            port = node['api_port'] or 0
            last_seen = str(node['last_seen'])[:19] if node['last_seen'] else 'Never'
            
            total_blocks += blocks
            total_rewards += rewards
            
            # Color coding for status
            status_icon = {
                'active': '✅',
                'mining': '⛏️',
                'inactive': '⭕'
            }.get(status, '❓')
            
            print(f"{node_id:<15} {status_icon}{status:<7} {blocks:<7} {rewards:<10.1f} {port:<6} {last_seen}")
        
        print("-" * 70)
        print(f"{'TOTALS':<15} {'NETWORK':<8} {total_blocks:<7} {total_rewards:<10.1f}")
        
        # Additional statistics
        active_nodes = sum(1 for node in nodes if node['status'] == 'active')
        mining_nodes = sum(1 for node in nodes if node['status'] == 'mining')
        inactive_nodes = sum(1 for node in nodes if node['status'] == 'inactive')
        
        print(f"\n📈 NETWORK SUMMARY:")
        print(f"   Total Nodes: {len(nodes)}")
        print(f"   Active: {active_nodes} | Mining: {mining_nodes} | Inactive: {inactive_nodes}")
        print(f"   Total Blocks Mined: {total_blocks}")
        print(f"   Total Rewards Distributed: {total_rewards}")
        
        if total_blocks > 0:
            avg_reward_per_block = total_rewards / total_blocks
            print(f"   Average Reward per Block: {avg_reward_per_block:.1f}")
    
    else:
        print("\n❌ No nodes currently registered in the database")
        print("\nTo register nodes, start network nodes:")
        print("python src/nodes/network_node.py --node-id <name> --api-port <port>")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    verify_mining_stats()