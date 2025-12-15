#!/usr/bin/env python3
"""
Debug transaction validation step by step
"""

import sys
import os
import requests
import json

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.core.bitcoin_transaction import Transaction, TransactionInput, TransactionOutput
from src.crypto.ecdsa_crypto import ECDSAKeyPair, validate_address

def debug_transaction_validation():
    print("🔍 Debug Transaction Validation")
    print("=" * 50)
    
    # Load miner2 wallet
    print("1. Loading miner2 wallet...")
    try:
        with open("src/wallets/miner2.json", 'r') as f:
            wallet_data = json.load(f)
        
        # Create keypair from wallet using the same method as wallet_client
        keypair = ECDSAKeyPair.from_dict(wallet_data['keypair'])
        address = wallet_data['address']
        
        print(f"   ✅ Wallet loaded: {address}")
        
    except Exception as e:
        print(f"   ❌ Failed to load wallet: {e}")
        return
    
    # Get UTXOs from node
    print("\n2. Fetching UTXOs from node...")
    try:
        response = requests.get(f"http://localhost:5001/utxos/{address}")
        if response.status_code == 200:
            utxo_data = response.json()
            utxos = utxo_data.get('utxos', [])
            print(f"   ✅ Found {len(utxos)} UTXOs")
            if len(utxos) > 0:
                print(f"   💰 First UTXO: {utxos[0]['amount']} CC")
                print(f"   🔑 UTXO Key: {utxos[0]['key'][:32]}...")
        else:
            print(f"   ❌ Failed to get UTXOs: {response.status_code}")
            return
            
    except Exception as e:
        print(f"   ❌ Error getting UTXOs: {e}")
        return
    
    if not utxos:
        print("   ❌ No UTXOs available")
        return
    
    # Create transaction manually
    print("\n3. Creating transaction manually...")
    
    try:
        # Set transaction parameters (same as original failed transaction)
        recipient = "1CcUyVAiHT2dGP4ESxWqsDKFzazkQ2UW3n"
        amount = 500.0
        fee = 0.5
        
        # Select enough UTXOs to cover 500.5 CC (need 11 UTXOs @ 50 CC each)
        needed_amount = amount + fee  # 500.5 CC
        selected_utxos = []
        total_input = 0.0
        
        for utxo in utxos:
            selected_utxos.append(utxo)
            total_input += utxo['amount']
            if total_input >= needed_amount:
                break
        
        if total_input < needed_amount:
            print(f"   ❌ Insufficient UTXOs: need {needed_amount}, have {total_input}")
            return
            
        print(f"   💰 Selected {len(selected_utxos)} UTXOs totaling {total_input} CC")
        
        transaction = Transaction()
        
        # Add multiple inputs
        for i, utxo in enumerate(selected_utxos):
            print(f"   📥 Adding input {i}: {utxo['tx_id'][:16]}...:{utxo['output_index']} ({utxo['amount']} CC)")
            transaction.add_input(utxo['tx_id'], utxo['output_index'])
        
        # Add outputs
        print(f"   📤 Adding output: {amount} CC to {recipient}")
        transaction.add_output(amount, recipient)
        
        # Calculate and add change
        change = total_input - needed_amount
        if change > 0:
            print(f"   💰 Adding change: {change} CC to {address}")
            transaction.add_output(change, address)
        
        print(f"   🆔 Transaction ID: {transaction.tx_id[:16]}...")
        
    except Exception as e:
        print(f"   ❌ Error creating transaction: {e}")
        return
    
    # Sign transaction
    print("\n4. Signing transaction...")
    try:
        print(f"   🔑 Signing input 0 with keypair...")
        print(f"   📝 Keypair type: {type(keypair)}")
        print(f"   📝 Has sign method: {hasattr(keypair, 'sign')}")
        
        # Try to sign a simple test message first
        try:
            test_sig = keypair.sign("test message")
            print(f"   ✅ Test signature successful: {test_sig['signature'][:16]}...")
        except Exception as test_e:
            print(f"   ❌ Test signature failed: {test_e}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
            return
        
        # Now try the actual transaction signing - sign all inputs
        for i in range(len(transaction.inputs)):
            print(f"   🔑 Signing input {i}...")
            transaction.sign_input(i, keypair)
        
        # Check signatures
        all_signed = True
        for i, tx_input in enumerate(transaction.inputs):
            signature = tx_input.signature
            if signature:
                print(f"   ✅ Input {i} signature created: {signature.get('signature', 'no sig')[:16]}...")
            else:
                print(f"   ❌ Input {i} signature missing")
                all_signed = False
        
        if not all_signed:
            print(f"   ❌ Not all inputs signed")
            return
            
    except Exception as e:
        print(f"   ❌ Error signing transaction: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return
    
    # Validate recipient address
    print("\n5. Validating recipient address...")
    try:
        if validate_address(recipient):
            print(f"   ✅ Valid recipient address: {recipient}")
        else:
            print(f"   ❌ Invalid recipient address: {recipient}")
            return
    except Exception as e:
        print(f"   ❌ Error validating address: {e}")
        return
    
    # Check transaction structure
    print("\n6. Checking transaction structure...")
    try:
        tx_dict = transaction.to_dict()
        print(f"   ✅ Transaction serializable")
        print(f"   📝 Inputs: {len(tx_dict['inputs'])}")
        print(f"   📝 Outputs: {len(tx_dict['outputs'])}")
        print(f"   💰 Total output: {sum(out['amount'] for out in tx_dict['outputs'])}")
        
        # Check if total output <= total input
        input_total = sum(utxo['amount'] for utxo in utxos[:len(transaction.inputs)])
        output_total = sum(out['amount'] for out in tx_dict['outputs'])
        
        if output_total <= input_total:
            print(f"   ✅ Valid amounts: {output_total} <= {input_total}")
        else:
            print(f"   ❌ Invalid amounts: {output_total} > {input_total}")
            return
            
    except Exception as e:
        print(f"   ❌ Error checking transaction structure: {e}")
        return
    
    # Test manual signature verification
    print("\n7. Testing signature verification...")
    try:
        # Get UTXO set for verification
        utxo_set = {}
        for utxo in selected_utxos:  # Use selected UTXOs instead of all UTXOs
            key = f"{utxo['tx_id']}:{utxo['output_index']}"
            utxo_set[key] = {
                'recipient_address': utxo['recipient_address'],
                'amount': utxo['amount'],
                'tx_id': utxo['tx_id'],
                'output_index': utxo['output_index']
            }
        
        # Verify all signatures
        all_valid = True
        for i in range(len(transaction.inputs)):
            valid_sig = transaction.verify_input_signature(i, "", utxo_set)
            if valid_sig:
                print(f"   ✅ Input {i} signature verification passed")
            else:
                print(f"   ❌ Input {i} signature verification failed")
                all_valid = False
        
        if not all_valid:
            print(f"   ❌ Some signatures failed verification")
            return
            
    except Exception as e:
        print(f"   ❌ Error verifying signature: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return
    
    # Submit transaction to node
    print("\n8. Submitting transaction to node...")
    try:
        tx_dict = transaction.to_dict()
        
        response = requests.post(
            "http://localhost:5001/add_transaction",
            json=tx_dict,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"   📡 HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Transaction accepted!")
            print(f"   🆔 TX ID: {result.get('tx_id', 'unknown')}")
        else:
            result = response.json()
            print(f"   ❌ Transaction rejected:")
            print(f"   📄 Response: {json.dumps(result, indent=2)}")
            
    except Exception as e:
        print(f"   ❌ Error submitting transaction: {e}")
        return

if __name__ == "__main__":
    debug_transaction_validation()