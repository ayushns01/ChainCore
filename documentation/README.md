# ChainCore - Multi-Node Blockchain

A complete, production-ready blockchain with proper node-wallet separation and multi-terminal workflow.

## 🚀 **Architecture**

- **🖥️ Network Nodes**: Pure blockchain processors (no wallets attached)
- **💼 Wallet Clients**: Users control their private keys
- **⛏️ Mining Clients**: Earn block rewards independently  
- **🔐 ECDSA Crypto**: Industry-standard signatures (secp256k1)
- **📡 API-Driven**: All operations via REST API

## 📁 **Project Files**

```
├── network_node.py          # ChainCore network node
├── wallet_client.py         # Standalone wallet client
├── mining_client.py         # Proof-of-Work miner
├── start_network.py         # Multi-node launcher
├── api_demo.py             # Complete API demo
├── TERMINAL_GUIDE.md       # Multi-terminal workflow
├── src/
│   ├── crypto/
│   │   └── ecdsa_crypto.py  # ECDSA implementation
│   └── blockchain/
│       └── bitcoin_transaction.py  # Transaction system
└── simple_test.py          # Basic functionality test
```

## ⚡ **Multi-Terminal Quick Start**

### **Terminal 1: Start Network**
```bash
source venv/bin/activate
python3 start_network.py
# Starts 3 nodes: localhost:5000, :5001, :5002
```

### **Terminal 2: Create Wallets**
```bash
python3 wallet_client.py create --wallet alice.json
python3 wallet_client.py create --wallet miner.json
```

### **Terminal 3: Start Mining**
```bash
python3 mining_client.py --wallet MINER_ADDRESS --node http://localhost:5000
```

### **Terminal 4: API Operations**
```bash
# Check network status
curl http://localhost:5000/status
curl http://localhost:5001/status
curl http://localhost:5002/status

# Check balances
curl http://localhost:5000/balance/ALICE_ADDRESS
curl http://localhost:5001/balance/MINER_ADDRESS
```

### **Terminal 5: Send Transactions**
```bash
python3 wallet_client.py send --wallet miner.json --to ALICE_ADDRESS --amount 50
```

## 🎯 **Key Features**

✅ **Multi-Node Network**: 3+ connected blockchain nodes  
✅ **API-Driven**: All operations via REST endpoints  
✅ **Terminal Workflow**: Multiple terminals for different roles  
✅ **Load Balancing**: Distribute operations across nodes  
✅ **Real Mining**: Proof-of-Work with adjustable difficulty  
✅ **UTXO Model**: Prevents double-spending  
✅ **ECDSA Security**: Industry-standard cryptography  

## 🖥️ **Complete Demo**

```bash
# Automated multi-node demo
python3 api_demo.py
```

## 📖 **Documentation**

- **`TERMINAL_GUIDE.md`**: Complete multi-terminal workflow
- **`BITCOIN_README.md`**: Technical API reference

## 💰 **Currency: ChainCoin (CC)**

All transactions use ChainCoin (CC) as the native currency.

## 🎉 **Multi-Node Success!**

Your blockchain now runs across multiple terminals with API-driven operations! 🚀