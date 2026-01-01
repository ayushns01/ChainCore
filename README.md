# ChainCore

A production-ready blockchain implementation in Python with PostgreSQL integration, enterprise-grade thread safety, multi-node networking, and advanced mining capabilities.

## 🚀 Overview

ChainCore is a full-featured blockchain platform implementing a complete cryptocurrency system with Bitcoin-compatible cryptography, UTXO transaction model, and proof-of-work consensus. Built with production-grade architecture, it demonstrates enterprise-level blockchain development practices.

### Key Features

- **🗄️ Database-Driven Architecture**: PostgreSQL integration with comprehensive DAO layer
- **🔒 Thread-Safe Operations**: Enterprise-grade concurrency control with reader-writer locks
- **🌐 Multi-Node Network**: P2P networking with automatic peer discovery and consensus
- **⛏️ Advanced Mining**: Multi-core proof-of-work with 50-80% performance optimization
- **📊 Real-Time Monitoring**: Database monitoring and blockchain analytics
- **🔐 Bitcoin-Compatible Cryptography**: ECDSA signatures and address formats
- **💼 Complete Wallet System**: Full wallet management with transaction support
- **🔄 Industry-Standard Sync**: Bitcoin-style blockchain synchronization with fork resolution

## 📋 Table of Contents

- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Usage Guide](#-usage-guide)
- [API Reference](#-api-reference)
- [Configuration](#-configuration)
- [Monitoring](#-monitoring)
- [Testing](#-testing)
- [Project Structure](#-project-structure)
- [Security Features](#-security-features)
- [Performance](#-performance)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

## 🏗️ Architecture

### Core Components

#### 1. **Blockchain Core** (`src/core/`)
- **Block Implementation**: SHA-256 proof-of-work with Merkle trees
- **Transaction System**: UTXO model with ECDSA signatures
- **Blockchain Sync**: Industry-standard synchronization with fork resolution
- **Consensus**: Longest valid chain rule with difficulty adjustment

#### 2. **Database Layer** (`src/data/`)
- **PostgreSQL Integration**: Complete schema with 6 tables
- **DAO Pattern**: Data Access Objects for all entities
- **Connection Pooling**: Enterprise-grade connection management
- **ACID Compliance**: Transaction integrity and atomic operations

**Database Schema**:
```
blocks              - Blockchain blocks with mining metadata
transactions        - All blockchain transactions with UTXO references
utxos              - Unspent transaction outputs for balance calculations
nodes              - Network node registration and tracking
mining_stats       - Mining performance and attribution data
address_balances   - Cached balance data for quick queries
```

#### 3. **Network Nodes** (`src/nodes/network_node.py`)
- **RESTful API**: Complete HTTP API for blockchain operations
- **P2P Networking**: Automatic peer discovery and management
- **Thread Safety**: Comprehensive locking for concurrent access
- **Database Persistence**: All blockchain state persisted to PostgreSQL

#### 4. **Mining Client** (`src/clients/mining_client.py`)
- **Multi-Core Mining**: Automatic CPU detection and parallel processing
- **Performance Optimized**: 50-80% faster with optimized serialization
- **Address Validation**: Bitcoin-style ECDSA address verification
- **Network Resilience**: Timeout protection and exponential backoff

#### 5. **Wallet Client** (`src/clients/wallet_client.py`)
- **Wallet Management**: Create and manage blockchain wallets
- **Transaction Creation**: Send funds with proper UTXO management
- **Balance Queries**: Real-time balance and transaction history
- **Multi-Node Support**: Connect to any node in the network

#### 6. **Thread Safety** (`src/concurrency/`)
- **Reader-Writer Locks**: Concurrent read access, exclusive writes
- **Deadlock Prevention**: Lock ordering and timeout detection
- **MVCC Isolation**: Multi-version concurrency control
- **Atomic Operations**: Critical section protection

## 📦 Prerequisites

- **Python 3.8+** (tested with Python 3.14)
- **PostgreSQL 12+** (required for blockchain data persistence)
- **macOS/Linux/Windows** (cross-platform compatible)

## 🔧 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd ChainCore
```

### 2. Set Up Python Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up PostgreSQL Database

**Install PostgreSQL** (macOS with Homebrew):
```bash
brew install postgresql@14
brew services start postgresql@14
```

**Create Database and User**:
```bash
createdb chaincore_blockchain
psql -d chaincore_blockchain -c "CREATE USER chaincore_user WITH PASSWORD 'chaincore_secure_2024';"
psql -d chaincore_blockchain -c "GRANT ALL PRIVILEGES ON DATABASE chaincore_blockchain TO chaincore_user;"
psql -d chaincore_blockchain -c "GRANT ALL ON SCHEMA public TO chaincore_user;"
```

**Initialize Database Schema**:
```bash
psql -U chaincore_user -d chaincore_blockchain -h localhost -f database_setup.sql
```

### 5. Verify Installation
```bash
# Test database connection
python -c "from src.data.simple_connection import get_simple_db_manager; print('✅ Database connection successful!')"
```

## 🚀 Quick Start

### Complete 6-Terminal Setup

#### Terminal 1: Database Monitor
```bash
source .venv/bin/activate
python src/monitoring/database_monitor.py
```

#### Terminal 2: Bootstrap Node (core0)
```bash
source .venv/bin/activate
python src/nodes/network_node.py --node-id core0 --api-port 5000 --p2p-port 8000
```

#### Terminal 3: Peer Node 1 (core1)
```bash
source .venv/bin/activate
python src/nodes/network_node.py --node-id core1 --api-port 5001 --p2p-port 8001 --bootstrap-nodes http://localhost:5000
```

#### Terminal 4: Peer Node 2 (core2)
```bash
source .venv/bin/activate
python src/nodes/network_node.py --node-id core2 --api-port 5002 --p2p-port 8002 --bootstrap-nodes http://localhost:5000
```

#### Terminal 5: Mining Client
```bash
source .venv/bin/activate
python src/clients/mining_client.py --wallet 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa --node http://localhost:5000
```

#### Terminal 6: Wallet Operations
```bash
source .venv/bin/activate

# Create wallets
python src/clients/wallet_client.py create --wallet alice.json
python src/clients/wallet_client.py create --wallet bob.json

# Check wallet info
python src/clients/wallet_client.py info --wallet alice.json

# Check balance (after mining some blocks)
python src/clients/wallet_client.py balance --wallet alice.json --node http://localhost:5000

# Send transaction
python src/clients/wallet_client.py send --wallet alice.json --node http://localhost:5000 --to <BOB_ADDRESS> --amount 10.0 --fee 0.5
```

### Verify Network Consensus
```bash
# Check all nodes have identical blockchain length
curl -s http://localhost:5000/status | grep "blockchain_length"
curl -s http://localhost:5001/status | grep "blockchain_length"
curl -s http://localhost:5002/status | grep "blockchain_length"
# All should show the same blockchain_length
```

## 📖 Usage Guide

### Network Node Commands

**Start a Network Node**:
```bash
python src/nodes/network_node.py --node-id <NODE_ID> --api-port <PORT> --p2p-port <P2P_PORT>
```

**Options**:
- `--node-id`: Unique identifier for the node (e.g., core0, core1)
- `--api-port`: HTTP API port (default: 5000)
- `--p2p-port`: P2P communication port (default: 8000)
- `--bootstrap-nodes`: Comma-separated list of bootstrap node URLs
- `--no-discover`: Disable automatic peer discovery
- `--debug`: Enable debug logging
- `--quiet`: Reduce console output

### Mining Client Commands

**Start Mining**:
```bash
python src/clients/mining_client.py --wallet <ADDRESS> --node <NODE_URL>
```

**Options**:
- `--wallet`: Miner's wallet address (required)
- `--node`: Node URL to connect to (default: http://localhost:5000)
- `--stats`: Show mining statistics
- `--quiet`: Reduce console output

### Wallet Client Commands

**Create Wallet**:
```bash
python src/clients/wallet_client.py create --wallet <FILENAME>
```

**Check Balance**:
```bash
python src/clients/wallet_client.py balance --wallet <FILENAME> --node <NODE_URL>
```

**Send Transaction**:
```bash
python src/clients/wallet_client.py send --wallet <FILENAME> --node <NODE_URL> --to <ADDRESS> --amount <AMOUNT> --fee <FEE>
```

**View Wallet Info**:
```bash
python src/clients/wallet_client.py info --wallet <FILENAME>
```

**Transaction History**:
```bash
python src/clients/wallet_client.py history --wallet <FILENAME>
```

## 🌐 API Reference

### Node Endpoints

#### Status and Information

**GET /status**
```bash
curl http://localhost:5000/status
```
Returns node status and blockchain information.

**GET /**
```bash
curl http://localhost:5000/
```
Human-readable status page (browser-friendly).

**GET /blockchain**
```bash
curl http://localhost:5000/blockchain | python3 -m json.tool
```
Complete blockchain data.

**GET /stats**
```bash
curl http://localhost:5000/stats
```
Detailed node statistics.

#### Transactions

**GET /balance/<address>**
```bash
curl http://localhost:5000/balance/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
```
Check address balance.

**GET /utxos/<address>**
```bash
curl http://localhost:5000/utxos/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
```
Get unspent transaction outputs for address.

**POST /add_transaction**
```bash
curl -X POST http://localhost:5000/add_transaction \
  -H "Content-Type: application/json" \
  -d @transaction.json
```
Submit new transaction to the network.

**GET /transaction_pool**
```bash
curl http://localhost:5000/transaction_pool
```
View pending transactions.

#### Mining

**POST /mine_block**
```bash
curl -X POST http://localhost:5000/mine_block \
  -H "Content-Type: application/json" \
  -d '{"miner_address":"1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"}'
```
Get mining template.

**POST /submit_block**
```bash
curl -X POST http://localhost:5000/submit_block \
  -H "Content-Type: application/json" \
  -H "X-Local-Mining: true" \
  -d @block_data.json
```
Submit mined block.

**GET /blocks/range?start=X&end=Y**
```bash
curl "http://localhost:5000/blocks/range?start=0&end=10"
```
Get block range.

#### P2P Network

**GET /peers**
```bash
curl http://localhost:5000/peers
```
List connected peers.

**POST /discover_peers**
```bash
curl -X POST http://localhost:5000/discover_peers
```
Trigger peer discovery.

**POST /addpeer**
```bash
curl -X POST http://localhost:5000/addpeer \
  -H "Content-Type: application/json" \
  -d '{"peer_url":"http://localhost:5001"}'
```
Manually add peer.

**GET /getpeers**
```bash
curl http://localhost:5000/getpeers
```
Get peers for sharing.

## ⚙️ Configuration

### Mining Difficulty

Edit `src/config.py` to adjust mining difficulty:

```python
# Mining difficulty - number of leading zeros required in block hash
BLOCKCHAIN_DIFFICULTY = 1  # "0" prefix - very fast (development)
BLOCKCHAIN_DIFFICULTY = 2  # "00" prefix - fast
BLOCKCHAIN_DIFFICULTY = 3  # "000" prefix - moderate (recommended)
BLOCKCHAIN_DIFFICULTY = 4  # "0000" prefix - slow
```

**Important**: Restart all nodes after changing difficulty.

### Network Settings

```python
# Network configuration in src/config.py
DEFAULT_API_PORT = 5000
DEFAULT_P2P_PORT = 8000
PEER_DISCOVERY_RANGE = (5000, 5100)  # Port range for peer discovery

# Peer management
MIN_PEERS = 2          # Minimum peers to maintain
TARGET_PEERS = 6       # Optimal peer count
MAX_PEERS = 12         # Maximum peer connections
```

### Mining Settings

```python
# Mining configuration in src/config.py
BLOCK_REWARD = 50.0                  # Coins per block
TARGET_BLOCK_TIME = 10.0             # Seconds between blocks
MINING_ROUND_DURATION = 12.0         # Mining round duration
MINING_TIMEOUT = 20                  # Mining timeout in seconds
```

### Database Configuration

Edit `src/data/config.py` for database settings:

```python
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'chaincore_blockchain',
    'user': 'chaincore_user',
    'password': 'chaincore_secure_2024'
}
```

## 📊 Monitoring

### Database Monitor

**Continuous Monitoring**:
```bash
python src/monitoring/database_monitor.py
```

**Single Status Check**:
```bash
python src/monitoring/database_monitor.py --status-only
```

**Custom Refresh Interval**:
```bash
python src/monitoring/database_monitor.py --interval 5
```

### Network Monitoring

**Real-Time Network Status**:
```bash
while true; do
  clear
  echo "🔗 ChainCore Network Status - $(date)"
  echo "========================================"
  for port in 5000 5001 5002; do
    echo -n "Node $port: "
    curl -s http://localhost:$port/status | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'Blocks: {data[\"blockchain_length\"]}, Peers: {data[\"active_peers\"]}')
except:
    print('❌ Offline')
" 2>/dev/null
  done
  sleep 5
done
```

**Check All Nodes**:
```bash
for port in {5000..5010}; do
  echo "Node on port $port:"
  curl -s http://localhost:$port/status | jq '.blockchain_length'
  echo
done
```

## 🧪 Testing

### Run Test Suite

**Activate Environment**:
```bash
source .venv/bin/activate
```

**Integration Tests**:
```bash
python tests/test_integration.py
python tests/test_mining_end_to_end.py
python tests/test_database_blockchain.py
```

**Network Tests**:
```bash
python tests/test_multi_node_network.py
python tests/test_enhanced_p2p.py
python tests/test_peer_discovery.py
```

**Mining Tests**:
```bash
python tests/test_competitive_mining.py
python tests/test_multicore_mining.py
python tests/test_mining_balance_flow.py
```

**Database Tests**:
```bash
python tests/test_database_connection.py
python tests/test_database_mining.py
```

### Development Commands

**Test Database Connectivity**:
```bash
python tests/test_database_connection.py
```

**Debug Mining Process**:
```bash
python tests/debug_mining.py
```

**Verify Blockchain Synchronization**:
```bash
python tests/test_blockchain_sync.py
```

## 📁 Project Structure

```
ChainCore/
├── src/
│   ├── clients/              # Mining and wallet clients
│   │   ├── mining_client.py  # Multi-core mining implementation
│   │   └── wallet_client.py  # Wallet management
│   ├── core/                 # Blockchain core components
│   │   ├── block.py          # Block implementation
│   │   ├── blockchain_sync.py # Blockchain synchronization
│   │   └── bitcoin_transaction.py # Transaction system
│   ├── crypto/               # Cryptographic functions
│   │   └── ecdsa_crypto.py   # ECDSA signatures and addresses
│   ├── data/                 # Database layer (DAO pattern)
│   │   ├── block_dao.py      # Block database operations
│   │   ├── transaction_dao.py # Transaction and UTXO management
│   │   ├── node_dao.py       # Node registration and tracking
│   │   ├── mining_stats_dao.py # Mining statistics
│   │   ├── address_balance_dao.py # Balance caching
│   │   ├── simple_connection.py # Database connection
│   │   └── config.py         # Database configuration
│   ├── concurrency/          # Thread safety implementation
│   │   ├── blockchain_safe.py # Thread-safe blockchain
│   │   ├── mining_safe.py    # Thread-safe mining
│   │   ├── network_safe.py   # Thread-safe networking
│   │   └── thread_safety.py  # Core thread safety primitives
│   ├── monitoring/           # Real-time monitoring tools
│   │   ├── database_monitor.py # Database monitoring
│   │   └── blockchain_monitor.py # Network monitoring
│   ├── network/              # P2P networking
│   │   ├── peer_manager.py   # Peer discovery and management
│   │   └── connection_cleaner.py # Connection management
│   ├── nodes/                # Network node implementation
│   │   └── network_node.py   # Full-featured blockchain node
│   ├── services/             # Shared services
│   │   └── mining_coordinator.py # Mining coordination
│   ├── wallets/              # Example wallet files
│   └── config.py             # Global configuration
├── tests/                    # Comprehensive test suite (50 files)
├── docs/                     # Documentation (9 guides)
│   ├── COMPLETE_USAGE_GUIDE.md
│   ├── CONFIGURATION_GUIDE.md
│   ├── DATABASE_MONITOR_COMMANDS.md
│   ├── MANUAL_TESTING_GUIDE.md
│   ├── MINING_DIFFICULTY_ANALYSIS.md
│   ├── SESSION_RECORDING_SYSTEM.md
│   ├── TERMINAL_COMMANDS.md
│   ├── TERMINAL_GUIDE.md
│   └── TRACKING_COMMANDS.md
├── database_setup.sql        # PostgreSQL schema
├── requirements.txt          # Python dependencies
└── README.md
```

## 🔐 Security Features

### Cryptographic Security

- **ECDSA Signatures**: Bitcoin-compatible secp256k1 transaction signing
- **Address Validation**: Comprehensive Bitcoin-style address verification with checksums
- **Double SHA-256**: Secure proof-of-work hashing algorithm
- **Privacy Protection**: Address sanitization in logs and console output

### Network Security

- **URL Validation**: Secure endpoint verification for all network connections
- **Connection Timeouts**: Protection against slow or malicious nodes
- **Input Validation**: Comprehensive API parameter validation on all endpoints
- **Rate Limiting**: Protection against spam and denial-of-service attacks
- **Peer Authentication**: Validation of network peers before connection

### Database Security

- **Parameterized Queries**: SQL injection prevention on all database operations
- **Connection Pooling**: Secure database connection management
- **Transaction Integrity**: ACID compliance with rollback protection
- **Access Control**: Role-based database permissions

### Thread Safety

- **Reader-Writer Locks**: Concurrent read access with exclusive write protection
- **Deadlock Detection**: Automatic detection and prevention mechanisms
- **Atomic Operations**: Critical section protection for blockchain state
- **MVCC Isolation**: Multi-version concurrency control for consistent reads

## 📈 Performance

### Multi-Core Mining

- **Automatic CPU Detection**: Detects available CPU cores
- **CPU Core Affinity**: Reduces context switching overhead
- **Parallel Proof-of-Work**: Distributes work across all cores
- **50-80% Performance Improvement**: Compared to single-core mining

**Performance Metrics**:
```
Single-Core:  ~10,000 hashes/second
Multi-Core:   ~50,000+ hashes/second (8-core CPU)
Speedup:      5-8x depending on CPU architecture
```

### Database Optimization

- **Connection Pooling**: High-performance database access
- **Indexed Queries**: Optimized schema with proper indexing on all lookup fields
- **DAO Pattern**: Efficient data access with strategic caching
- **Atomic Operations**: Thread-safe database interactions

### Network Optimization

- **Efficient Peer Discovery**: Concurrent scanning with configurable timeouts
- **Adaptive Timeouts**: Based on network size and conditions
- **Smart Caching**: Template management to reduce redundant requests
- **Bounded Data Structures**: Prevents memory leaks in long-running nodes

## 🛠️ Troubleshooting

### Common Issues

#### 1. Database Connection Failed

**Check PostgreSQL is Running**:
```bash
brew services list | grep postgresql
# Start if not running
brew services start postgresql@14
```

**Test Connection**:
```bash
psql -U chaincore_user -d chaincore_blockchain -h localhost -c "SELECT 1;"
```

**Reset Database** (if needed):
```bash
dropdb chaincore_blockchain
createdb chaincore_blockchain
psql -U chaincore_user -d chaincore_blockchain -h localhost -f database_setup.sql
```

#### 2. Module Not Found Errors

**Ensure Virtual Environment is Activated**:
```bash
source .venv/bin/activate
which python
# Should show: /path/to/ChainCore/.venv/bin/python
```

**Reinstall Dependencies**:
```bash
pip install -r requirements.txt
```

#### 3. Port Already in Use

**Check What's Using the Port**:
```bash
lsof -i :5000
```

**Kill Conflicting Processes**:
```bash
pkill -f "network_node.py"
```

#### 4. Mining Not Working

**Check Node is Responding**:
```bash
curl -s http://localhost:5000/status
```

**Verify Blockchain Length**:
```bash
curl -s http://localhost:5000/status | grep blockchain_length
```

**Test Mining Endpoint**:
```bash
curl -X POST http://localhost:5000/mine_block \
  -H "Content-Type: application/json" \
  -d '{"miner_address": "test"}'
```

#### 5. Nodes Not Syncing

**Check Peer Connections**:
```bash
curl -s http://localhost:5000/peers
```

**Force Peer Discovery**:
```bash
curl -X POST http://localhost:5000/discover_peers
```

**Verify Network Connectivity**:
```bash
# Test connection between nodes
curl -s http://localhost:5001/status
curl -s http://localhost:5002/status
```

### Process Management

**Stop All ChainCore Processes**:
```bash
pkill -f "network_node.py|mining_client.py|database_monitor.py"
```

**Check Running Processes**:
```bash
ps aux | grep -E "(network_node|mining_client|database_monitor)" | grep -v grep
```

**Clean Restart**:
```bash
source .venv/bin/activate
python src/monitoring/database_monitor.py &
sleep 2
python src/nodes/network_node.py --node-id core0 --api-port 5000 --p2p-port 8000 &
sleep 5
python src/nodes/network_node.py --node-id core1 --api-port 5001 --p2p-port 8001 --bootstrap-nodes http://localhost:5000 &
```

## 🎯 Success Indicators

Your ChainCore network is working correctly when you see:

✅ **Database Connected**: Database monitor shows blockchain data  
✅ **Nodes Synced**: All nodes show identical `blockchain_length`  
✅ **Peer Connections**: Nodes show `active_peers > 0`  
✅ **Mining Active**: Database monitor shows new blocks being mined  
✅ **Transactions Processing**: Wallet operations complete successfully  

## 🎓 Use Cases

### Educational
- **Blockchain Learning**: Complete cryptocurrency implementation for study
- **Academic Research**: Consensus algorithms and distributed systems
- **Computer Science**: Cryptography and network programming
- **Teaching**: Demonstrate blockchain concepts with working code

### Development
- **Blockchain Development**: Foundation for blockchain applications
- **Testing Environment**: Safe environment for blockchain experimentation
- **Prototype Development**: Rapid blockchain prototype development
- **API Integration**: Learn blockchain API development

### Production
- **Private Networks**: Enterprise blockchain networks
- **Consortium Chains**: Multi-organization blockchain networks
- **Research Platforms**: Academic and corporate research environments
- **Internal Tools**: Blockchain-based internal systems

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Complete Usage Guide](docs/COMPLETE_USAGE_GUIDE.md)**: Full usage instructions
- **[Configuration Guide](docs/CONFIGURATION_GUIDE.md)**: Mining difficulty and system configuration
- **[Database Monitor Commands](docs/DATABASE_MONITOR_COMMANDS.md)**: Real-time monitoring guide
- **[Terminal Guide](docs/TERMINAL_GUIDE.md)**: Multi-terminal setup guide
- **[Terminal Commands](docs/TERMINAL_COMMANDS.md)**: Updated multi-node network commands
- **[Manual Testing Guide](docs/MANUAL_TESTING_GUIDE.md)**: Comprehensive testing procedures
- **[Mining Difficulty Analysis](docs/MINING_DIFFICULTY_ANALYSIS.md)**: Difficulty tuning guide

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add comprehensive docstrings
- Include unit tests for new features
- Update documentation as needed
- Maintain backward compatibility when possible

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- Bitcoin Core for cryptographic standards and UTXO model inspiration
- PostgreSQL community for robust database system
- Python cryptography library maintainers
- Open source blockchain community

## 📞 Support

For questions, issues, or contributions:

- **GitHub Issues**: Report bugs and request features
- **Documentation**: Comprehensive guides in `docs/` directory
- **Examples**: Working examples throughout the codebase
- **Tests**: 50+ test files demonstrating usage

---

**ChainCore** - A modern, secure, and scalable blockchain platform built for education, development, and production use.

Built with ❤️ using Python, PostgreSQL, and Bitcoin-compatible cryptography.
