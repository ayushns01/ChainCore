# Bitcoin-Style Blockchain - Production Ready

A complete Bitcoin-compatible blockchain implementation with proper architecture separation.

## 🚀 **Key Features**

### **✅ Bitcoin-Compatible Architecture**
- **ECDSA signatures** (secp256k1 curve)
- **Bitcoin-style addresses** (Base58Check encoding)
- **UTXO transaction model**
- **Proof-of-Work mining**
- **Proper node-wallet separation**

### **🏗️ Clean Architecture**
- **Network Nodes**: Process transactions, maintain blockchain (no wallets)
- **Wallet Clients**: Users control their own private keys
- **Mining Clients**: Earn block rewards in separate wallets
- **Multi-node P2P network** (JSON-RPC over HTTP)

## 📁 **Project Structure**

```
├── network_node.py          # Pure network node (like Bitcoin Core)
├── wallet_client.py         # Standalone wallet (like Electrum)
├── mining_client.py         # Mining software (like mining pools)
├── src/
│   ├── crypto/
│   │   └── ecdsa_crypto.py  # Bitcoin-compatible ECDSA
│   └── blockchain/
│       └── bitcoin_transaction.py  # Bitcoin-style transactions
├── quick_start.py           # Quick test script
└── simple_test.py          # Basic functionality test
```

## 🚀 **Quick Start**

### **1. Install Dependencies**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### **2. Run Simple Test**
```bash
python3 simple_test.py
```

### **3. Start Network Node**
```bash
# Terminal 1: Start blockchain network node
python3 network_node.py --api-port 5000
```

### **4. Create Wallet**
```bash
# Terminal 2: Create your wallet
python3 wallet_client.py create --wallet my_wallet.json

# Note the address output, you'll need it for mining
```

### **5. Start Mining**
```bash
# Terminal 3: Start mining (replace with your address)
python3 mining_client.py --wallet 1HrMVwZmcNxoTp4FQ2S3KrwkNri51oTZXh
```

### **6. Send Transactions**
```bash
# Create another wallet for testing
python3 wallet_client.py create --wallet friend.json

# Send coins (replace addresses with actual ones)
python3 wallet_client.py send --wallet my_wallet.json \
  --to 1AWo3Koe42yNcZPVgAKiEpjqYvZ7V8KJfR --amount 10
```

## 📖 **Command Reference**

### **Network Node Commands**
```bash
# Start node
python3 network_node.py --node-id node1 --api-port 5000

# Start multiple nodes
python3 network_node.py --node-id node1 --api-port 5000 &
python3 network_node.py --node-id node2 --api-port 5001 &
python3 network_node.py --node-id node3 --api-port 5002 &
```

### **Wallet Commands**
```bash
# Create wallet
python3 wallet_client.py create --wallet my_wallet.json

# Check balance  
python3 wallet_client.py balance --wallet my_wallet.json

# Send transaction
python3 wallet_client.py send --wallet my_wallet.json \
  --to RECIPIENT_ADDRESS --amount 25.5 --fee 0.001

# Get wallet info
python3 wallet_client.py info --wallet my_wallet.json

# Transaction history
python3 wallet_client.py history --wallet my_wallet.json
```

### **Mining Commands**
```bash
# Start mining
python3 mining_client.py --wallet YOUR_ADDRESS

# Connect to different node
python3 mining_client.py --wallet YOUR_ADDRESS --node http://localhost:5001

# Mining stats
python3 mining_client.py --wallet YOUR_ADDRESS --stats
```

## 🌐 **REST API Endpoints**

### **Node Status**
```bash
# Get blockchain status
curl http://localhost:5000/status

# Get full blockchain
curl http://localhost:5000/blockchain
```

### **Address Operations**
```bash
# Check balance
curl http://localhost:5000/balance/ADDRESS

# Get UTXOs
curl http://localhost:5000/utxos/ADDRESS
```

### **Transaction Operations**
```bash
# Broadcast transaction
curl -X POST http://localhost:5000/broadcast_transaction \
  -H "Content-Type: application/json" \
  -d @transaction.json

# Get transaction pool
curl http://localhost:5000/transaction_pool
```

### **Mining Operations**
```bash
# Get mining template
curl -X POST http://localhost:5000/mine_block \
  -H "Content-Type: application/json" \
  -d '{"miner_address": "YOUR_ADDRESS"}'

# Submit mined block
curl -X POST http://localhost:5000/submit_block \
  -H "Content-Type: application/json" \
  -d @mined_block.json
```

## 🔐 **Security Features**

### **Bitcoin-Compatible Cryptography**
- **ECDSA**: secp256k1 elliptic curve (same as Bitcoin)
- **SHA256**: Double SHA256 hashing for blocks
- **Base58Check**: Address encoding with checksum
- **Private Key Control**: Users own their keys, not the nodes

### **Transaction Security**
- **Digital Signatures**: All transactions cryptographically signed
- **UTXO Model**: Prevents double-spending
- **Script System**: Basic scripting for outputs
- **Fee System**: Economic incentives for miners

## ⛏️ **Mining & Consensus**

### **Proof-of-Work**
- **Target Difficulty**: Adjustable leading zeros requirement
- **Nonce Finding**: Brute force hash computation
- **Block Rewards**: 50 BTC per block + transaction fees
- **Difficulty Adjustment**: Every 10 blocks

### **Block Structure**
```json
{
  "index": 123,
  "previous_hash": "0000abc123...",
  "merkle_root": "def456...",
  "timestamp": 1691234567,
  "nonce": 142857,
  "target_difficulty": 4,
  "transactions": [...],
  "hash": "0000123abc..."
}
```

## 🔧 **Multi-Node Setup**

### **3-Node Network**
```bash
# Terminal 1: Bootstrap node
python3 network_node.py --node-id bootstrap --api-port 5000

# Terminal 2: Node 2  
python3 network_node.py --node-id node2 --api-port 5001

# Terminal 3: Node 3
python3 network_node.py --node-id node3 --api-port 5002

# All nodes can process transactions independently
```

### **Load Balancing**
```bash
# Wallets can connect to any node
python3 wallet_client.py balance --wallet alice.json --node http://localhost:5000
python3 wallet_client.py balance --wallet alice.json --node http://localhost:5001

# Miners can mine on any node
python3 mining_client.py --wallet ADDR1 --node http://localhost:5000 &
python3 mining_client.py --wallet ADDR2 --node http://localhost:5001 &
```

## 📊 **Performance**

### **Specifications**
- **Block Time**: ~60 seconds (adjustable difficulty)
- **Block Size**: ~1000 transactions per block
- **Transaction Throughput**: ~16 TPS (transactions per second)
- **Address Space**: 2^160 possible addresses
- **Hash Rate**: Depends on CPU (typically 1000-10000 H/s)

### **Scalability**
- **Node Scaling**: Add more nodes for redundancy
- **Wallet Scaling**: Unlimited wallet clients per node
- **Mining Scaling**: Multiple miners can work simultaneously
- **Geographic Distribution**: Nodes can run anywhere

## 🔄 **Comparison with Bitcoin**

| Feature | Bitcoin | This Implementation |
|---------|---------|-------------------|
| **Signature Algorithm** | ECDSA secp256k1 | ✅ ECDSA secp256k1 |
| **Address Format** | Base58Check | ✅ Base58Check |
| **Transaction Model** | UTXO | ✅ UTXO |
| **Consensus** | Proof-of-Work | ✅ Proof-of-Work |
| **Block Structure** | Standard | ✅ Bitcoin-compatible |
| **Node Architecture** | Core + Wallet separation | ✅ Proper separation |
| **P2P Network** | TCP/IP | HTTP JSON-RPC |
| **Script System** | Bitcoin Script | Basic scripting |
| **Network Effects** | Global | Local/Private |

## 🛠️ **Development**

### **Testing**
```bash
# Run all tests
python3 -m pytest tests/

# Test specific components
python3 tests/test_ecdsa.py
python3 tests/test_transactions.py
python3 tests/test_mining.py
```

### **Adding Features**
1. **Smart Contracts**: Extend script system
2. **Light Clients**: SPV (Simplified Payment Verification)
3. **WebSocket P2P**: Real-time peer communication
4. **Database Storage**: Persistent blockchain storage
5. **Web Interface**: Browser-based wallet

### **Configuration**
Create `config.json`:
```json
{
  "network": {
    "difficulty": 4,
    "block_reward": 50,
    "max_block_size": 1000
  },
  "node": {
    "api_port": 5000,
    "p2p_port": 8000
  }
}
```

## 🎯 **Use Cases**

### **Educational**
- Learn blockchain fundamentals
- Understand Bitcoin internals  
- Practice cryptocurrency development
- Experiment with consensus algorithms

### **Development**
- Private blockchain networks
- Corporate cryptocurrency systems
- Prototype new blockchain features
- Testing and simulation

### **Production** (with enhancements)
- Private company coins
- Gaming currencies
- Loyalty point systems
- Academic research platforms

## ⚠️ **Production Considerations**

### **Current Limitations**
- **HTTP P2P**: Not as robust as TCP
- **Memory Storage**: No persistent database
- **Basic Scripts**: Limited smart contract capability
- **Single Machine**: Designed for local testing

### **For Production Use**
1. Add persistent database (PostgreSQL/MongoDB)
2. Implement TCP/WebSocket P2P networking
3. Add comprehensive logging/monitoring
4. Implement proper key management (HSM)
5. Add rate limiting and DDoS protection
6. Create web/mobile wallet interfaces

## 📄 **License**

Educational/Research use. Based on Bitcoin's design principles.

---

## 🎉 **Success!**

You now have a **fully functional Bitcoin-style blockchain** with:
- ✅ **Proper architecture** (nodes ≠ wallets)  
- ✅ **Bitcoin-compatible crypto** (ECDSA)
- ✅ **Multi-node support**  
- ✅ **Real mining** (Proof-of-Work)
- ✅ **Secure transactions** (UTXO model)

**This is how real blockchains work!** 🚀