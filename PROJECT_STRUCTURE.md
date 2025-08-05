# ChainCore - Clean Project Structure

## 📁 **Core Files**

### **Blockchain Engine**
- `network_node.py` - Main blockchain node with REST API
- `mining_client.py` - Proof-of-Work mining client  
- `wallet_client.py` - Wallet management and transactions

### **Core Libraries**
- `src/blockchain/bitcoin_transaction.py` - Transaction and UTXO system
- `src/crypto/ecdsa_crypto.py` - ECDSA cryptography (Bitcoin-compatible)

### **Configuration**
- `requirements.txt` - Python dependencies

### **Wallet Files**
- `miner.json` - Primary mining wallet (1CcUyVAiHT2dGP4ESxWqsDKFzazkQ2UW3n)
- `miner1.json` - Mining wallet 1 (1GukayKD1hRAXnQaJYKVwQcwCvVzsUbcJj) 
- `miner2.json` - Mining wallet 2 (18NDhHYAa3bx3jAZkc7HZf3vKr1JrwVXG3)
- `alice.json` - Test user wallet (15vuSyM7ZFUNqBibgwHUgbkva4FDDn6pXq)
- `bob.json` - Test user wallet (1FzanzSbcH7sik5kzymbdTrNci6h5HxBCe)

### **Documentation**
- `README.md` - Project overview and quick start
- `TERMINAL_GUIDE.md` - Complete multi-terminal workflow
- `TXN_TESTING.md` - 20-transaction testing suite
- `PROJECT_STRUCTURE.md` - This file

### **Environment**
- `venv/` - Python virtual environment

## 🗑️ **Removed Files**

**Unnecessary Documentation:**
- `BITCOIN_README.md` - Redundant technical docs
- `COMMANDS.md` - Redundant command reference  
- `ai_context.md` - Development notes

**Demo/Test Files:**
- `api_demo.py` - Demo script (functionality in TERMINAL_GUIDE.md)
- `quick_start.py` - Test script (replaced by TXN_TESTING.md)
- `simple_test.py` - Basic test (redundant)

**Old Wallet Files:**
- ~~Temporarily removed but restored upon request~~

## ✅ **Clean Architecture**

**Total Files:** 14 essential files + documentation
**Core Components:** 3 main Python modules  
**Wallet Files:** 5 pre-created wallets for testing
**Dependencies:** 5 required packages
**Documentation:** 4 comprehensive guides

**The project is now streamlined with only essential blockchain components.**