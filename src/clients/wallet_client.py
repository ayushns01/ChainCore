#!/usr/bin/env python3
"""
ChainCore Wallet Client - Standalone Cryptocurrency Wallet
Users control their private keys and connect to network nodes via API
"""

import sys
import os
import json
import argparse
import requests
from typing import List, Dict, Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__))))

from src.crypto.ecdsa_crypto import ECDSAKeyPair, validate_address
from src.core.bitcoin_transaction import Transaction, TransactionInput, TransactionOutput

class WalletClient:
    def __init__(self, wallet_file: str = None, node_url: str = "http://localhost:5000"):
        self.node_url = node_url
        self.wallet_file = wallet_file
        self.keypair: Optional[ECDSAKeyPair] = None
        self.address: Optional[str] = None
        
        if wallet_file:
            # Check if wallet exists at specified path or in src/wallets
            wallet_exists = os.path.exists(wallet_file)
            if not wallet_exists and not os.path.isabs(wallet_file):
                wallets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'wallets')
                alt_path = os.path.join(wallets_dir, wallet_file)
                wallet_exists = os.path.exists(alt_path)
            
            if wallet_exists:
                self.load_wallet(wallet_file)
            else:
                self.create_wallet(wallet_file)
    
    def create_wallet(self, filename: str):
        """Create new wallet with ECDSA keypair"""
        print("🔐 Creating new wallet...")
        
        self.keypair = ECDSAKeyPair()
        self.address = self.keypair.address
        
        # Ensure wallet is saved in src/wallets directory
        if not os.path.isabs(filename):
            wallets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'wallets')
            os.makedirs(wallets_dir, exist_ok=True)
            filename = os.path.join(wallets_dir, filename)
        
        self.wallet_file = filename
        
        wallet_data = {
            'keypair': self.keypair.to_dict(),
            'address': self.address,
            'type': 'ECDSA',
            'version': '1.0'
        }
        
        with open(filename, 'w') as f:
            json.dump(wallet_data, f, indent=2)
        
        print(f"✅ Wallet created: {filename}")
        print(f"📍 Address: {self.address}")
        print(f"🔑 Public Key: {self.keypair.get_public_key_hex()[:32]}...")
    
    def load_wallet(self, filename: str):
        """Load existing wallet"""
        try:
            # If file doesn't exist at specified path, try src/wallets directory
            if not os.path.exists(filename) and not os.path.isabs(filename):
                wallets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'wallets')
                alt_filename = os.path.join(wallets_dir, filename)
                if os.path.exists(alt_filename):
                    filename = alt_filename
            
            with open(filename, 'r') as f:
                wallet_data = json.load(f)
            
            self.keypair = ECDSAKeyPair.from_dict(wallet_data['keypair'])
            self.address = wallet_data['address']
            self.wallet_file = filename
            
            print(f"✅ Wallet loaded: {filename}")
            print(f"📍 Address: {self.address}")
            
        except Exception as e:
            print(f"❌ Error loading wallet: {e}")
            raise
    
    def get_balance(self) -> float:
        """Get balance from blockchain node"""
        try:
            response = requests.get(f"{self.node_url}/balance/{self.address}", timeout=10)
            if response.status_code == 200:
                return response.json()['balance']
        except Exception as e:
            print(f"❌ Error getting balance: {e}")
        return 0.0
    
    def get_utxos(self) -> List[Dict]:
        """Get UTXOs for this address"""
        try:
            response = requests.get(f"{self.node_url}/utxos/{self.address}", timeout=10)
            if response.status_code == 200:
                return response.json()['utxos']
        except Exception as e:
            print(f"❌ Error getting UTXOs: {e}")
        return []
    
    def send_transaction(self, to_address: str, amount: float, fee: float = 0.001) -> bool:
        """Create and broadcast transaction"""
        if not validate_address(to_address):
            print(f"❌ Invalid recipient address: {to_address}")
            return False
        
        if amount <= 0:
            print(f"❌ Invalid amount: {amount}")
            return False
        
        # Get UTXOs
        utxos = self.get_utxos()
        if not utxos:
            balance = self.get_balance()
            print("❌ No UTXOs available for transaction")
            print(f"   💰 Wallet balance: {balance:.8f} CC")
            if balance > 0:
                print("   ⚠️  Balance exists but no spendable UTXOs found")
                print("   💡 This may indicate pending transactions or a synchronization issue")
            else:
                print("   💡 Wallet is empty - receive some coins first")
            return False
        
        # Select UTXOs
        selected_utxos = []
        total_selected = 0.0
        needed = amount + fee
        
        for utxo in utxos:
            selected_utxos.append(utxo)
            total_selected += utxo['amount']
            if total_selected >= needed:
                break
        
        if total_selected < needed:
            balance = self.get_balance()
            shortage = needed - total_selected
            print(f"❌ Insufficient funds for transaction")
            print(f"   💰 Wallet balance: {balance:.8f} CC")
            print(f"   💸 Amount to send: {amount:.8f} CC")
            print(f"   🏷️  Transaction fee: {fee:.8f} CC")
            print(f"   📊 Total needed: {needed:.8f} CC")
            print(f"   ⚠️  Short by: {shortage:.8f} CC")
            if len(utxos) == 0:
                print(f"   📦 No UTXOs available (wallet has no spendable funds)")
            else:
                print(f"   📦 Available UTXOs: {len(utxos)} (total: {total_selected:.8f} CC)")
            return False
        
        # Create transaction
        transaction = Transaction()
        
        # Add inputs
        for utxo in selected_utxos:
            transaction.add_input(utxo['tx_id'], utxo['output_index'])
        
        # Add outputs
        transaction.add_output(amount, to_address)
        
        # Add change output if needed
        change = total_selected - needed
        if change > 0:
            transaction.add_output(change, self.address)
        
        # Sign inputs
        for i in range(len(transaction.inputs)):
            transaction.sign_input(i, self.keypair)
        
        # Broadcast transaction
        return self._broadcast_transaction(transaction)
    
    def _broadcast_transaction(self, transaction: Transaction) -> bool:
        """Broadcast transaction to network"""
        try:
            tx_data = transaction.to_dict()
            response = requests.post(
                f"{self.node_url}/broadcast_transaction",
                json=tx_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ Transaction broadcasted!")
                print(f"📋 TX ID: {transaction.tx_id}")
                return True
            else:
                print(f"❌ Broadcast failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error broadcasting transaction: {e}")
            return False
    
    def get_transaction_history(self) -> List[Dict]:
        """Get transaction history for this address"""
        try:
            response = requests.get(f"{self.node_url}/transactions/{self.address}", timeout=10)
            if response.status_code == 200:
                return response.json()['transactions']
        except Exception as e:
            print(f"❌ Error getting transaction history: {e}")
        return []
    
    def get_wallet_info(self) -> Dict:
        """Get wallet information"""
        return {
            'address': self.address,
            'balance': self.get_balance(),
            'utxos': len(self.get_utxos()),
            'public_key': self.keypair.get_public_key_hex() if self.keypair else None,
            'wallet_file': self.wallet_file
        }

def main():
    parser = argparse.ArgumentParser(description='ChainCore Wallet Client')
    parser.add_argument('command', choices=['create', 'balance', 'send', 'info', 'history'], 
                       help='Command to execute')
    parser.add_argument('--wallet', '-w', required=True, help='Wallet file path')
    parser.add_argument('--node', '-n', default='http://localhost:5000', help='Node URL')
    parser.add_argument('--to', help='Recipient address (for send command)')
    parser.add_argument('--amount', type=float, help='Amount to send')
    parser.add_argument('--fee', type=float, default=0.001, help='Transaction fee')
    
    args = parser.parse_args()
    
    print("💼 ChainCore Wallet Client")
    print("=" * 40)
    
    if args.command == 'create':
        wallet = WalletClient(args.wallet, args.node)
        
    elif args.command == 'balance':
        wallet = WalletClient(args.wallet, args.node)
        balance = wallet.get_balance()
        print(f"💰 Balance: {balance} CC")
        
    elif args.command == 'send':
        if not args.to or not args.amount:
            print("❌ --to and --amount required for send command")
            return
        
        wallet = WalletClient(args.wallet, args.node)
        
        # Show current wallet status before attempting transaction
        balance = wallet.get_balance()
        print(f"💼 Wallet Balance: {balance:.8f} CC")
        print(f"📤 Sending {args.amount} CC to {args.to} (Fee: {args.fee} CC)")
        print(f"📊 Total required: {args.amount + args.fee:.8f} CC")
        print("-" * 50)
        
        if wallet.send_transaction(args.to, args.amount, args.fee):
            print("✅ Transaction sent successfully!")
            new_balance = wallet.get_balance()
            print(f"💰 New balance: {new_balance:.8f} CC")
        else:
            print("❌ Transaction failed!")
    
    elif args.command == 'info':
        wallet = WalletClient(args.wallet, args.node)
        info = wallet.get_wallet_info()
        
        print(f"📍 Address: {info['address']}")
        print(f"💰 Balance: {info['balance']} CC")
        print(f"📦 UTXOs: {info['utxos']}")
        print(f"🔑 Public Key: {info['public_key'][:32] if info['public_key'] else 'N/A'}...")
        
    elif args.command == 'history':
        wallet = WalletClient(args.wallet, args.node)
        history = wallet.get_transaction_history()
        
        print(f"📋 Transaction History ({len(history)} transactions):")
        if history:
            from datetime import datetime
            for tx in history[:10]:  # Show last 10
                timestamp = datetime.fromtimestamp(tx['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                coinbase_indicator = " (coinbase)" if tx.get('is_coinbase', False) else ""
                print(f"   {tx['tx_id'][:16]}... | {tx['amount']} CC | {tx['type']}{coinbase_indicator} | {timestamp} | Block #{tx['block_height']}")
        else:
            print("   No transactions found")

if __name__ == '__main__':
    main()