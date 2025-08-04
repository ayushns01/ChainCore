#!/usr/bin/env python3
"""
ChainCore API Demo - Complete Multi-Node Workflow
Demonstrates API-driven blockchain operations across multiple nodes
"""

import requests
import subprocess
import time
import json
import sys

class ChainCoreDemo:
    def __init__(self):
        self.nodes = [
            "http://localhost:5000",
            "http://localhost:5001", 
            "http://localhost:5002"
        ]
        self.wallets = {}
    
    def check_nodes(self):
        """Check if nodes are running"""
        print("🔍 Checking network nodes...")
        
        active_nodes = []
        for i, node in enumerate(self.nodes):
            try:
                response = requests.get(f"{node}/status", timeout=3)
                if response.status_code == 200:
                    status = response.json()
                    print(f"  ✅ Node {i+1}: {node} - {status['blockchain_length']} blocks")
                    active_nodes.append(node)
                else:
                    print(f"  ❌ Node {i+1}: {node} - Not responding")
            except:
                print(f"  ❌ Node {i+1}: {node} - Connection failed")
        
        if not active_nodes:
            print("\n❌ No nodes are running!")
            print("Start nodes with: python3 start_network.py")
            return False
        
        print(f"\n✅ {len(active_nodes)} nodes active")
        return True
    
    def create_wallets(self):
        """Create test wallets"""
        print("\n💼 Creating wallets via CLI...")
        
        wallets = ["alice", "bob", "miner"]
        
        for wallet_name in wallets:
            filename = f"{wallet_name}_wallet.json"
            cmd = f"python3 wallet_client.py create --wallet {filename}"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Load wallet to get address
                try:
                    with open(filename, 'r') as f:
                        wallet_data = json.load(f)
                        address = wallet_data['address']
                        self.wallets[wallet_name] = {
                            'file': filename,
                            'address': address
                        }
                    print(f"  ✅ {wallet_name}: {address[:20]}...")
                except:
                    print(f"  ❌ Failed to load {wallet_name} wallet")
            else:
                print(f"  ❌ Failed to create {wallet_name} wallet")
                return False
        
        return True
    
    def start_mining(self):
        """Start mining via API"""
        if 'miner' not in self.wallets:
            print("❌ Miner wallet not found")
            return False
        
        miner_address = self.wallets['miner']['address']
        node = self.nodes[0]  # Use first node for mining
        
        print(f"\n⛏️  Starting mining on {node}...")
        print(f"   Miner address: {miner_address[:20]}...")
        
        # Start mining client in background
        cmd = f"python3 mining_client.py --wallet {miner_address} --node {node}"
        
        mining_process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        print("   ✅ Mining started in background")
        return mining_process
    
    def check_balances(self):
        """Check balances via API"""
        print("\n💰 Checking balances via API...")
        
        for name, wallet in self.wallets.items():
            address = wallet['address']
            
            # Try different nodes to test load balancing
            node_idx = hash(name) % len(self.nodes)
            node = self.nodes[node_idx]
            
            try:
                response = requests.get(f"{node}/balance/{address}")
                if response.status_code == 200:
                    balance = response.json()['balance']
                    print(f"  {name}: {balance} CC (via {node})")
                else:
                    print(f"  ❌ Failed to get {name} balance")
            except:
                print(f"  ❌ Connection error for {name}")
    
    def send_transaction(self):
        """Send transaction via API"""
        if 'miner' not in self.wallets or 'alice' not in self.wallets:
            print("❌ Required wallets not found")
            return False
        
        print(f"\n📤 Sending transaction via API...")
        
        # Check miner has funds first
        miner_address = self.wallets['miner']['address']
        try:
            response = requests.get(f"{self.nodes[0]}/balance/{miner_address}")
            balance = response.json()['balance']
            
            if balance < 10:
                print(f"❌ Miner has insufficient funds: {balance} CC")
                return False
        except:
            print("❌ Could not check miner balance")
            return False
        
        # Send via wallet client API
        alice_address = self.wallets['alice']['address']
        miner_file = self.wallets['miner']['file']
        
        cmd = f"python3 wallet_client.py send --wallet {miner_file} --to {alice_address} --amount 25 --fee 0.5"
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("  ✅ Transaction sent successfully!")
            return True
        else:
            print(f"  ❌ Transaction failed: {result.stderr}")
            return False
    
    def monitor_network(self):
        """Monitor network status via API"""
        print(f"\n📊 Network monitoring via API...")
        
        for i, node in enumerate(self.nodes):
            try:
                response = requests.get(f"{node}/status")
                if response.status_code == 200:
                    status = response.json()
                    print(f"  Node {i+1}: {status['blockchain_length']} blocks, {status['pending_transactions']} pending")
                else:
                    print(f"  Node {i+1}: API error")
            except:
                print(f"  Node {i+1}: Connection failed")
    
    def get_blockchain_info(self):
        """Get blockchain information via API"""
        print(f"\n🔗 Blockchain information...")
        
        try:
            response = requests.get(f"{self.nodes[0]}/blockchain")
            if response.status_code == 200:
                blockchain = response.json()
                
                total_transactions = 0
                for block in blockchain['chain']:
                    total_transactions += len(block['transactions'])
                
                print(f"  📊 Total blocks: {blockchain['length']}")
                print(f"  📊 Total transactions: {total_transactions}")
                print(f"  📊 Latest block hash: {blockchain['chain'][-1]['hash'][:20]}...")
            else:
                print("  ❌ Failed to get blockchain info")
        except:
            print("  ❌ Connection error")
    
    def run_demo(self):
        """Run complete API demo"""
        print("🚀 ChainCore Multi-Node API Demo")
        print("=" * 60)
        
        # Step 1: Check nodes
        if not self.check_nodes():
            return
        
        # Step 2: Create wallets
        if not self.create_wallets():
            return
        
        # Step 3: Start mining
        mining_process = self.start_mining()
        if not mining_process:
            return
        
        # Step 4: Wait for some blocks
        print(f"\n⏳ Waiting for blocks to be mined...")
        time.sleep(20)
        
        # Step 5: Check balances
        self.check_balances()
        
        # Step 6: Send transaction
        self.send_transaction()
        
        # Step 7: Wait for confirmation
        print(f"\n⏳ Waiting for transaction confirmation...")
        time.sleep(10)
        
        # Step 8: Check final balances
        self.check_balances()
        
        # Step 9: Monitor network
        self.monitor_network()
        
        # Step 10: Get blockchain info
        self.get_blockchain_info()
        
        # Cleanup
        print(f"\n🧹 Stopping mining...")
        mining_process.terminate()
        
        print(f"\n" + "=" * 60)
        print("🎉 ChainCore API Demo Complete!")
        
        print(f"\n💡 Manual API Commands:")
        print("  # Node status")
        print("  curl http://localhost:5000/status")
        print("  curl http://localhost:5001/status")
        print("  curl http://localhost:5002/status")
        print()
        print("  # Check balances")
        for name, wallet in self.wallets.items():
            print(f"  curl http://localhost:5000/balance/{wallet['address']}")
        print()
        print("  # Get blockchain")
        print("  curl http://localhost:5000/blockchain")
        print()
        print("  # Transaction pool")
        print("  curl http://localhost:5000/transaction_pool")
        
        # Cleanup files
        for wallet in self.wallets.values():
            try:
                import os
                os.remove(wallet['file'])
            except:
                pass

def main():
    demo = ChainCoreDemo()
    demo.run_demo()

if __name__ == "__main__":
    main()