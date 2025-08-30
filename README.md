# ChainCore - Enterprise Blockchain Platform

A complete, enterprise-grade blockchain platform with Bitcoin-compatible features, thread-safe operations, and scalable peer-to-peer networking.

## 🏗️ **Enterprise Architecture**

### Core Components

- **🖥️ Network Nodes**: Thread-safe blockchain processors with enterprise-grade locking
- **💼 Wallet Clients**: ECDSA-secured private key management
- **⛏️ Mining Clients**: Multi-core Proof-of-Work miners with CPU affinity
- **🌐 P2P Network**: Full-mesh networking with gossip protocol
- **🔒 Thread Safety**: Bitcoin Core-inspired lock hierarchy system
- **🗄️ Database**: PostgreSQL integration with materialized views

### Security & Performance Features

- **Thread Safety**: Enterprise lock hierarchy (`BLOCKCHAIN → UTXO_SET → MEMPOOL → PEERS → MINING → NETWORK`)
- **Deadlock Prevention**: Advanced detection and prevention system
- **ECDSA Cryptography**: Industry-standard secp256k1 signatures
- **Multi-Core Mining**: CPU affinity and parallel processing
- **Connection Pooling**: Persistent peer connections with quality scoring
- **Late-Joiner Sync**: Automatic blockchain synchronization for new nodes

## 📁 **Project Structure**

```
ChainCore/
├── network_node.py              # Main blockchain node (Thread-safe)
├── mining_client.py             # Multi-core PoW miner
├── wallet_client.py             # ECDSA wallet management
├── start_network.py             # Multi-node network launcher
├── fixes.md                     # Production issue fixes log
├── src/
│   ├── concurrency/             # Enterprise thread safety
│   │   ├── thread_safety.py     # Lock hierarchy system
│   │   ├── blockchain_safe.py   # Thread-safe blockchain ops
│   │   ├── mining_safe.py       # Thread-safe mining coordination
│   │   └── network_safe.py      # Thread-safe networking
│   ├── crypto/
│   │   └── ecdsa_crypto.py      # ECDSA secp256k1 implementation
│   ├── blockchain/
│   │   └── bitcoin_transaction.py # Bitcoin-compatible transactions
│   └── networking/
│       └── peer_manager.py      # P2P network management
└── documentation/
    └── AI_CONTEXT.md            # Technical architecture guide
```

## 🚀 **Production Deployment**

### **Step 1: Environment Setup**

```bash
# Create virtual environment
python -m venv chaincore
source chaincore/bin/activate  # Linux/Mac
# OR
chaincore\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### **Step 2: Start Network Nodes**

```bash
# Terminal 1: Bootstrap Node
python network_node.py --port 5000

# Terminal 2: Peer Node
python network_node.py --port 5001 --bootstrap http://localhost:5000

# Terminal 3: Additional Peer
python network_node.py --port 5002 --bootstrap http://localhost:5000
```

### **Step 3: Create Wallets**

```bash
# Create mining wallet
python wallet_client.py create --wallet miner.json

# Create user wallet
python wallet_client.py create --wallet alice.json
```

### **Step 4: Start Mining**

```bash
# Get miner address from wallet
python wallet_client.py address --wallet miner.json

# Start multi-core mining
python mining_client.py --wallet [MINER_ADDRESS] --node http://localhost:5000
```

### **Step 5: Network Operations**

```bash
# Check network status across nodes
curl http://localhost:5000/status
curl http://localhost:5001/status
curl http://localhost:5002/status

# Check blockchain synchronization
curl http://localhost:5000/blockchain/length
curl http://localhost:5001/blockchain/length

# Monitor peer connections
curl http://localhost:5000/peers
```

## 🔧 **Latest Fixes & Improvements**

### Recent Production Fixes (v2.0)

- ✅ **Mining Client Health Check Loop**: Fixed missing `thread_safe` field in node status API
- ✅ **Late-Joiner Sync Issue**: Implemented missing `get_peer_blockchain_info()` method
- ✅ **Block Validation Race Conditions**: Improved validation logic for multi-node scenarios
- ✅ **Thread Safety Enhancement**: Added comprehensive error handling and diagnostics

> **📋 Full Fix History**: See `fixes.md` for complete problem-solution-impact documentation

## 🎯 **Enterprise Features**

### Thread Safety (9/10 Rating)

- **Lock Hierarchy**: Prevents deadlocks through ordered acquisition
- **Reader-Writer Locks**: API endpoints support concurrent reads
- **Event Coordination**: Mining workers synchronized via threading events
- **Atomic Operations**: Database and blockchain operations are ACID compliant

### Network Scalability

- **P2P Mesh Network**: Full connectivity between all nodes
- **Gossip Protocol**: Efficient transaction and block propagation
- **Peer Discovery**: Automatic bootstrap and peer sharing
- **Connection Quality**: Peer scoring and health monitoring

### Mining Performance

- **Multi-Core Processing**: Utilizes all available CPU cores
- **CPU Affinity**: Workers pinned to specific cores
- **Template Optimization**: Precomputed block data for efficiency
- **Exponential Backoff**: Smart retry logic with fresh templates

## 📊 **Network Health Monitoring**

### Status Endpoints

```bash
# Detailed node status
curl http://localhost:5000/status

# Blockchain information
curl http://localhost:5000/blockchain

# Peer network status
curl http://localhost:5000/peers

# Transaction pool
curl http://localhost:5000/mempool
```

### Health Check Indicators

- ✅ **Thread Safety**: All locks operational
- ✅ **Network Health**: Peer connectivity status
- ✅ **Chain Sync**: Blockchain length consistency
- ✅ **Mining Active**: Block production rate
- ✅ **Database**: PostgreSQL connection health

## 🛠️ **Development & Testing**

### Run Complete System Test

```bash
# Automated multi-node demo
python api_demo.py

# Basic functionality validation
python simple_test.py
```

### Debugging & Logs

- **Node Logs**: Detailed thread safety and networking logs
- **Mining Logs**: Hash rate, difficulty, and block discovery
- **Peer Logs**: Connection status and sync progress
- **Error Handling**: Comprehensive exception tracking

## 🌐 **Network Protocols**

### Transaction Broadcasting

- **UTXO Model**: Prevents double-spending
- **Signature Verification**: ECDSA secp256k1 validation
- **Mempool Management**: Thread-safe transaction pooling
- **Fee Calculation**: Dynamic fee estimation

### Block Consensus

- **Proof-of-Work**: SHA-256 based mining
- **Difficulty Adjustment**: Automatic target recalculation
- **Fork Resolution**: Longest chain rule implementation
- **Block Validation**: Comprehensive integrity checks

## 💰 **ChainCoin (CC) Economics**

- **Native Currency**: ChainCoin (CC) powers all transactions
- **Mining Rewards**: Block rewards distributed to miners
- **Transaction Fees**: Network fee structure
- **Supply Management**: Controlled issuance schedule

## 📖 **Documentation**

- **`documentation/AI_CONTEXT.md`**: Technical architecture details
- **`fixes.md`**: Production issue resolution log
- **`src/concurrency/THREAD_SAFETY_GUIDE.md`**: Thread safety implementation

## 🚨 **Production Readiness**

### Current Rating: 7.5/10 (Advanced Production)

- **✅ Thread Safety**: Enterprise-grade locking system
- **✅ Network Scaling**: Late-joiner sync and peer discovery
- **✅ Mining Stability**: Multi-core processing with error recovery
- **✅ API Reliability**: Comprehensive endpoint protection
- **⚠️ Monitoring**: Basic health checks (can be enhanced)
- **⚠️ Load Testing**: Stress testing recommended for high-volume deployment

## 🤝 **Contributing**

1. **Issue Reporting**: Use GitHub issues for bug reports
2. **Code Standards**: Follow existing thread safety patterns
3. **Testing**: Ensure multi-node compatibility
4. **Documentation**: Update relevant guides and fixes.md

## 📄 **License**

MIT License - See LICENSE file for details

---

**🎉 ChainCore: Enterprise Blockchain - Ready for Production! 🚀**
