# ChainCore - Enterprise-Grade Blockchain Network

A complete, production-ready blockchain implementation featuring enterprise-grade thread safety, multi-node architecture, and comprehensive cryptocurrency functionality.

## 🏗️ **Architecture Overview**

ChainCore implements a distributed blockchain network with clear separation of concerns:

- **🌐 Network Nodes**: Thread-safe blockchain processors with enterprise-grade concurrency control
- **💼 Wallet Clients**: Self-sovereign cryptocurrency wallets with ECDSA key management
- **⛏️ Mining Clients**: Proof-of-Work miners with configurable difficulty and hash rate monitoring
- **🔐 Cryptographic Security**: Industry-standard ECDSA signatures using secp256k1 curve
- **📡 API-First Design**: REST API endpoints for all blockchain operations
- **🧵 Thread Safety**: Advanced concurrency control with deadlock detection and MVCC

## 🎯 **Core Components**

### Network Layer
- **Multi-node P2P network** with peer discovery and synchronization
- **Thread-safe blockchain state** with reader-writer locks and MVCC
- **Connection pooling** and rate limiting for scalable peer management
- **Atomic block validation** and consensus mechanisms

### Transaction System
- **UTXO-based model** preventing double-spending attacks
- **Merkle tree verification** for transaction integrity
- **Bitcoin-compatible transaction format** with inputs, outputs, and scripts
- **Mempool management** with priority-based transaction selection

### Mining Infrastructure
- **Configurable Proof-of-Work** with adjustable difficulty targeting
- **Real-time hash rate monitoring** and performance statistics
- **Work coordination** between multiple miners
- **Block template generation** with coinbase rewards

### Wallet Management
- **Hierarchical Deterministic (HD) wallets** with ECDSA key pairs
- **Address generation** and validation
- **Transaction signing** and broadcast capabilities
- **Balance tracking** across multiple addresses

## 📁 **Project Structure**

```
ChainCore/
├── network_node.py              # Main blockchain network node
├── mining_client.py             # Proof-of-Work mining client
├── wallet_client.py             # Cryptocurrency wallet interface
├── blockchain_monitor.py        # Real-time blockchain analysis
├── src/
│   ├── blockchain/
│   │   ├── block.py             # Block structure and validation
│   │   ├── bitcoin_transaction.py  # Transaction system
│   │   └── blockchain_monitor.py   # Blockchain tracking
│   ├── concurrency/
│   │   ├── thread_safety.py     # Enterprise thread safety
│   │   ├── blockchain_safe.py   # Thread-safe blockchain
│   │   ├── mining_safe.py       # Thread-safe mining
│   │   └── network_safe.py      # Thread-safe networking
│   ├── crypto/
│   │   └── ecdsa_crypto.py      # ECDSA cryptographic functions
│   └── config.py                # Centralized configuration
└── test-scripts/                # Comprehensive testing suite
```

## 🚀 **Getting Started**

### Prerequisites
```bash
python3 -pip install -r requirements.txt
```

### Multi-Terminal Network Setup

**Terminal 1: Network Node**
```bash
python3 network_node.py --port 5000
```

**Terminal 2: Additional Nodes**
```bash
python3 network_node.py --port 5001 --peers http://localhost:5000
python3 network_node.py --port 5002 --peers http://localhost:5000,http://localhost:5001
```

**Terminal 3: Wallet Operations**
```bash
# Create wallets
python3 wallet_client.py create --wallet miner.json
python3 wallet_client.py create --wallet alice.json

# Check balance
python3 wallet_client.py balance --wallet miner.json

# Send transactions
python3 wallet_client.py send --wallet miner.json --to <address> --amount 25.0 --fee 0.5
```

**Terminal 4: Mining Operations**
```bash
# Start mining with miner wallet
python3 mining_client.py --wallet <miner_address> --node http://localhost:5000
```

**Terminal 5: Blockchain Monitoring**
```bash
# Real-time blockchain analysis
python3 blockchain_monitor.py --node http://localhost:5000
```

## 🔧 **Configuration**

### Blockchain Parameters
- **Block Time**: Configurable difficulty adjustment
- **Block Reward**: Adjustable coinbase rewards
- **Transaction Fees**: Market-driven fee structure
- **Network Difficulty**: Automatic adjustment based on hash rate

### Thread Safety Settings
- **Lock Timeout**: Configurable deadlock prevention
- **MVCC Snapshots**: Isolation level configuration
- **Connection Pooling**: Scalable peer management
- **Rate Limiting**: DoS protection mechanisms

## 🛡️ **Security Features**

### Cryptographic Security
- **ECDSA Digital Signatures** using secp256k1 curve
- **SHA-256 Double Hashing** for block and transaction integrity
- **Merkle Tree Verification** for efficient block validation
- **Address Validation** with checksum verification

### Network Security
- **Peer Authentication** and connection validation
- **Rate Limiting** for DoS attack prevention
- **Input Validation** for all API endpoints
- **Thread Safety** preventing race conditions and data corruption

### Consensus Security
- **Proof-of-Work Validation** ensuring computational investment
- **Double-Spend Prevention** through UTXO verification
- **Block Chain Integrity** with cryptographic linking
- **Fork Resolution** through longest chain rule

## 📊 **Monitoring & Analytics**

### Real-Time Metrics
- **Network hash rate** and mining statistics
- **Transaction throughput** and confirmation times
- **Peer connectivity** and network topology
- **Memory pool** size and transaction prioritization

### Blockchain Analysis
- **Block explorer** functionality with transaction history
- **Address balance** tracking across the network
- **Transaction flow** analysis and visualization
- **Network performance** statistics and optimization

## 🧪 **Testing Suite**

### Comprehensive Testing
- **Unit tests** for individual components
- **Integration tests** for network operations
- **Load testing** for scalability validation
- **Security testing** for vulnerability assessment

### Test Categories
```bash
# Basic functionality
python3 test-scripts/simple_mining_test.py

# Network synchronization
python3 test_blockchain_sync.py

# Competitive mining
python3 test_competitive_mining.py

# Peer discovery
python3 test_peer_discovery.py
```

## 🌟 **Enterprise Features**

### Scalability
- **Horizontal scaling** with multiple network nodes
- **Load balancing** across node infrastructure
- **Efficient data structures** for high-throughput operations
- **Memory optimization** for long-running network nodes

### Reliability
- **Fault tolerance** with redundant node architecture
- **Graceful degradation** under network partitions
- **Data consistency** through ACID transaction properties
- **Automatic recovery** from node failures

### Observability
- **Comprehensive logging** with configurable levels
- **Performance metrics** and operational statistics
- **Health checks** and system monitoring
- **Debugging tools** for network analysis

## 💰 **ChainCoin (CC) Economics**

ChainCore implements a complete cryptocurrency ecosystem:

- **Native Currency**: ChainCoin (CC) with decimal precision
- **Mining Rewards**: Block rewards for successful miners
- **Transaction Fees**: Market-driven fee structure
- **Economic Incentives**: Balanced tokenomics for network security

## 🤝 **Contributing**

ChainCore follows enterprise development practices:

- **Code Quality**: Comprehensive testing and documentation
- **Security Review**: Regular security audits and vulnerability assessments
- **Performance Optimization**: Continuous performance monitoring and improvement
- **Community Standards**: Industry best practices and coding standards

---

ChainCore represents a production-ready blockchain implementation suitable for enterprise deployment, educational purposes, and cryptocurrency research. The codebase demonstrates advanced software engineering practices including thread safety, distributed systems design, and cryptographic security.