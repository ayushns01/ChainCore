# ChainCore

A ground-up blockchain implementation in Python featuring PostgreSQL persistence, thread-safe operations, multi-node networking, and proof-of-work mining.

## 🚀 Project Overview

ChainCore is a learning-focused blockchain implementation that demonstrates core cryptocurrency concepts:

- **Database-Driven Architecture**: PostgreSQL integration with comprehensive DAO layer
- **Thread-Safe Operations**: Concurrency control with reader-writer locks and atomic operations
- **Multi-Node Network**: P2P networking with automatic peer discovery and consensus
- **Enhanced Mining Client**: Optimized proof-of-work with address validation and privacy protection
- **Real-Time Monitoring**: Database monitoring and blockchain analytics
- **ECDSA Security**: Bitcoin-compatible cryptographic signatures and address formats
- **RESTful API**: Complete HTTP API for blockchain interaction and wallet operations

## 🏗️ Architecture

### Core Components

#### 1. Database Layer (`src/data/`)
- **PostgreSQL Integration**: Complete database schema with tables for blocks, transactions, UTXOs, nodes, and mining stats
- **DAO Pattern**: Data Access Objects for all blockchain entities (BlockDAO, TransactionDAO, NodeDAO, etc.)
- **Connection Pooling**: Database connection management with psycopg2
- **Transaction Integrity**: ACID compliance and atomic operations

#### 2. Network Nodes (`src/nodes/network_node.py`)
- **Multi-node Support**: Bootstrap and peer nodes with automatic discovery
- **Thread-safe Operations**: Blockchain operations with comprehensive locking
- **Database Integration**: All blockchain state persisted to PostgreSQL
- **RESTful API**: HTTP endpoints for all blockchain operations
- **Fork Resolution**: Bitcoin-style longest/heaviest chain consensus

#### 3. Enhanced Mining Client (`src/clients/mining_client.py`)
- **Competitive Mining**: Miners compete independently (no coordinator)
- **Address Validation**: Bitcoin-style ECDSA address verification
- **Privacy Protection**: Address sanitization in logs and console output
- **Performance Optimization**: 50-80% faster mining with optimized serialization
- **Network Security**: URL validation, timeout protection, and retry logic

#### 4. Blockchain Sync (`src/core/blockchain_sync.py`)
- **Fork Resolution**: Enhanced fork handling using cumulative work comparison
- **Chain Reorganization**: Automatic reorg when longer valid chain is found
- **Mining Attribution**: Preserves miner information during chain switches
- **UTXO Consistency**: Maintains balance integrity through reorgs

#### 5. Wallet Client (`src/clients/wallet_client.py`)
- **Wallet Management**: Create, manage, and operate blockchain wallets
- **Transaction Creation**: Send funds with proper UTXO management
- **Balance Queries**: Real-time balance and transaction history
- **Multi-node Support**: Connect to any node in the network

#### 6. Real-time Monitoring (`src/monitoring/`)
- **Database Monitor**: Real-time blockchain database monitoring
- **Network Analytics**: Multi-node network health and consensus tracking
- **Mining Statistics**: Performance metrics and mining distribution analysis

### Database Schema

The system uses PostgreSQL with the following tables:
- **blocks**: Blockchain blocks with mining metadata
- **transactions**: All blockchain transactions with UTXO references
- **utxos**: Unspent transaction outputs for balance calculations
- **nodes**: Network node registration and tracking
- **mining_stats**: Mining performance and attribution data
- **address_balances**: Cached balance data for quick queries

## 🚀 Getting Started

### Prerequisites

- **Python 3.8+** (tested with Python 3.14)
- **PostgreSQL 12+** (required for blockchain data persistence)
- **macOS/Linux/Windows** (cross-platform compatible)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd ChainCore
   ```

2. **Set up Python virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up PostgreSQL database:**
   ```bash
   # Install PostgreSQL (macOS with Homebrew)
   brew install postgresql
   brew services start postgresql
   
   # Create database and user
   createdb chaincore_blockchain
   psql -d chaincore_blockchain -c "CREATE USER chaincore_user WITH PASSWORD 'chaincore_secure_2024';"
   psql -d chaincore_blockchain -c "GRANT ALL PRIVILEGES ON DATABASE chaincore_blockchain TO chaincore_user;"
   psql -d chaincore_blockchain -c "GRANT ALL ON SCHEMA public TO chaincore_user;"
   
   # Initialize database schema
   psql -U chaincore_user -d chaincore_blockchain -h localhost -f database_setup.sql
   ```

5. **Verify setup:**
   ```bash
   # Test database connection
   python -c "from src.data.simple_connection import get_simple_db_manager; print('✅ Database connection successful!')"
   ```

## 🖥️ Quick Start

### 1. Start Database Monitor
```bash
# Terminal 1 - Monitor blockchain database in real-time
source .venv/bin/activate
python src/monitoring/database_monitor.py
```

### 2. Start Network Nodes
```bash
# Terminal 2 - Bootstrap Node (core0)
source .venv/bin/activate
python src/nodes/network_node.py --node-id core0 --api-port 5000 --p2p-port 8000

# Terminal 3 - Peer Node 1 (core1)
source .venv/bin/activate
python src/nodes/network_node.py --node-id core1 --api-port 5001 --p2p-port 8001 --bootstrap-nodes http://localhost:5000

# Terminal 4 - Peer Node 2 (core2)
source .venv/bin/activate
python src/nodes/network_node.py --node-id core2 --api-port 5002 --p2p-port 8002 --bootstrap-nodes http://localhost:5000
```

### 3. Verify Network Consensus
```bash
# Check all nodes have identical blockchain length
curl -s http://localhost:5000/status | grep "blockchain_length"
curl -s http://localhost:5001/status | grep "blockchain_length"
curl -s http://localhost:5002/status | grep "blockchain_length"
# All should show: "blockchain_length": 1
```

### 4. Start Mining
```bash
# Terminal 5 - Mining Client
source .venv/bin/activate
python src/clients/mining_client.py --wallet 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa --node http://localhost:5000
```

### 5. Create and Use Wallets
```bash
# Terminal 6 - Wallet Operations
source .venv/bin/activate

# Create wallets
python src/clients/wallet_client.py create --wallet alice.json
python src/clients/wallet_client.py create --wallet bob.json

# Check wallet info
python src/clients/wallet_client.py info --wallet alice.json
python src/clients/wallet_client.py info --wallet bob.json

# Check balances (after mining some blocks)
python src/clients/wallet_client.py balance --wallet alice.json --node http://localhost:5000

# Send transaction
python src/clients/wallet_client.py send --wallet alice.json --node http://localhost:5000 --to BOB_ADDRESS --amount 10.0 --fee 0.5
```

## 📊 Configuration

### Mining Difficulty
Edit `src/config.py` to adjust mining difficulty:
```python
# Easy mining for development (recommended)
BLOCKCHAIN_DIFFICULTY = 1  # "0" prefix - very fast
BLOCKCHAIN_DIFFICULTY = 2  # "00" prefix - fast  
BLOCKCHAIN_DIFFICULTY = 3  # "000" prefix - moderate
BLOCKCHAIN_DIFFICULTY = 4  # "0000" prefix - slow
```

**Important:** Restart all nodes after changing difficulty.

### Database Configuration
Database settings are in `src/data/config.py`:
```python
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'chaincore_blockchain',
    'user': 'chaincore_user',
    'password': 'chaincore_secure_2024'
}
```

## 🌐 API Reference

### Node Status
```bash
# Basic status
curl http://localhost:5000/status

# Pretty-printed JSON
curl -s http://localhost:5000/status | python3 -m json.tool

# Blockchain data
curl http://localhost:5000/blockchain | python3 -m json.tool
```

### Wallet Operations
```bash
# Check balance
curl http://localhost:5000/balance/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa

# Get UTXOs
curl http://localhost:5000/utxos/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa

# Transaction history
curl http://localhost:5000/transactions/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
```

### Mining Operations
```bash
# Get block template
curl -X POST http://localhost:5000/mine_block \
  -H "Content-Type: application/json" \
  -d '{"miner_address":"1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"}'

# Submit mined block
curl -X POST http://localhost:5000/submit_block \
  -H "Content-Type: application/json" \
  -H "X-Local-Mining: true" \
  -d '@block_data.json'
```

### Network Management
```bash
# View connected peers
curl http://localhost:5000/peers

# Force peer discovery
curl -X POST http://localhost:5000/discover_peers

# Transaction pool
curl http://localhost:5000/transaction_pool
```

## < API Reference

### Node Endpoints

#### Status and Information

- `GET /status` - Node status and blockchain info
- `GET /` - Human-readable status page (browser-friendly)
- `GET /blockchain` - Complete blockchain data
- `GET /stats` - Detailed node statistics

#### Transactions

- `POST /add_transaction` - Submit new transaction
- `GET /transaction_pool` - View pending transactions
- `GET /balance/<address>` - Check address balance
- `GET /utxos/<address>` - Get UTXOs for address

#### Mining

- `POST /mine_block` - Get mining template
- `POST /submit_block` - Submit mined block
- `GET /blocks/range?start=X&end=Y` - Get block range

#### P2P Network

- `GET /peers` - List connected peers
- `POST /discover_peers` - Trigger peer discovery
- `POST /addpeer` - Manually add peer
- `GET /getpeers` - Get peers for sharing

### Example Usage

```bash
# Check node status
curl http://localhost:5001/status

# Get blockchain data
curl http://localhost:5001/blockchain

# Check balance
curl http://localhost:5001/balance/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa

# Get mining template
curl -X POST http://localhost:5001/mine_block \
  -H "Content-Type: application/json" \
  -d '{"miner_address":"1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"}'
```

## 🔍 Monitoring and Analytics

### Database Monitor
Real-time blockchain database monitoring:
```bash
# Continuous monitoring
python src/monitoring/database_monitor.py

# Single status check
python src/monitoring/database_monitor.py --status-only

# Custom refresh interval
python src/monitoring/database_monitor.py --interval 5
```

### Network Monitoring
```bash
# Real-time network status
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

## 🛠️ Troubleshooting

### Common Issues

**1. Database Connection Failed**
```bash
# Check PostgreSQL is running
brew services list | grep postgresql
# Start if not running
brew services start postgresql@14

# Test connection
psql -U chaincore_user -d chaincore_blockchain -h localhost -c "SELECT 1;"
```

**2. Module Not Found Errors**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate
# Verify Python environment
which python
# Should show: /path/to/ChainCore/.venv/bin/python
```

**3. Port Already in Use**
```bash
# Check what's using the port
lsof -i :5000
# Kill conflicting processes
pkill -f "network_node.py"
```

**4. Mining Not Working**
```bash
# Check node is responding
curl -s http://localhost:5000/status
# Verify blockchain length > 0
curl -s http://localhost:5000/status | grep blockchain_length
# Test mining endpoint
curl -X POST http://localhost:5000/mine_block -H "Content-Type: application/json" -d '{"miner_address": "test"}'
```

### Process Management
```bash
# Stop all ChainCore processes
pkill -f "network_node.py|mining_client.py|database_monitor.py"

# Check running processes
ps aux | grep -E "(network_node|mining_client|database_monitor)" | grep -v grep

# Clean restart
source .venv/bin/activate
python src/monitoring/database_monitor.py &
sleep 2
python src/nodes/network_node.py --node-id core0 --api-port 5000 --p2p-port 8000 &
sleep 5
python src/nodes/network_node.py --node-id core1 --api-port 5001 --p2p-port 8001 --bootstrap-nodes http://localhost:5000 &
```

## 📁 Project Structure

```
ChainCore/
├── src/
│   ├── clients/           # Mining and wallet clients
│   │   ├── mining_client.py
│   │   └── wallet_client.py
│   ├── core/              # Blockchain core components
│   │   ├── block.py
│   │   ├── blockchain_sync.py
│   │   └── bitcoin_transaction.py
│   ├── crypto/            # Cryptographic functions
│   │   └── ecdsa_crypto.py
│   ├── data/              # Database layer (DAO pattern)
│   │   ├── block_dao.py
│   │   ├── transaction_dao.py
│   │   ├── node_dao.py
│   │   ├── mining_stats_dao.py
│   │   ├── address_balance_dao.py
│   │   ├── simple_connection.py
│   │   └── config.py
│   ├── monitoring/        # Real-time monitoring tools
│   │   └── database_monitor.py
│   ├── network/           # P2P networking
│   ├── nodes/             # Network node implementation
│   │   └── network_node.py
│   └── config/            # Configuration files
├── tests/                 # Test suite
├── docs/                  # Documentation
│   ├── DATABASE_MONITOR_COMMANDS.md
│   ├── TERMINAL_GUIDE.md
│   ├── TERMINAL_COMMANDS.md
│   └── CONFIGURATION_GUIDE.md
├── database_setup.sql     # Database schema
├── requirements.txt       # Python dependencies
└── README.md
```

## 🔐 Security Features

### Cryptographic Security
- **ECDSA Signatures**: Bitcoin-compatible transaction signing
- **Address Validation**: Comprehensive Bitcoin-style address verification
- **Double SHA-256**: Secure proof-of-work hashing
- **Privacy Protection**: Address sanitization in logs

### Network Security
- **URL Validation**: Secure endpoint verification
- **Connection Timeouts**: Protection against slow/malicious nodes
- **Input Validation**: Comprehensive API parameter validation
- **Rate Limiting**: Protection against spam and DoS attacks

### Database Security
- **Parameterized Queries**: SQL injection prevention
- **Connection Pooling**: Secure database connection management
- **Transaction Integrity**: ACID compliance and rollback protection
- **Access Control**: Role-based database permissions

## 📈 Performance Features

### Enhanced Mining Client
- **50-80% Performance Improvement**: Optimized JSON serialization
- **Address Validation**: Pre-mining wallet verification
- **Template Staleness Detection**: Prevents wasted mining effort
- **Exponential Backoff**: Network resilience with intelligent retry
- **Memory Management**: Bounded statistics prevent memory leaks

### Database Optimization
- **Connection Pooling**: High-performance database access
- **Indexed Queries**: Optimized database schema with proper indexing
- **DAO Pattern**: Efficient data access with caching where appropriate
- **Atomic Operations**: Thread-safe database interactions

## 🧪 Testing & Development

### Running Tests
```bash
# Activate environment
source .venv/bin/activate

# Run comprehensive test suite
python tests/test_integration.py
python tests/test_mining_end_to_end.py
python tests/test_database_blockchain.py
python tests/test_multi_node_network.py
```

### Development Commands
```bash
# Test database connectivity
python tests/test_database_connection.py

# Debug mining process
python tests/debug_mining.py

# Verify blockchain synchronization
python tests/test_blockchain_sync.py
```

## 🚀 Use Cases

### Educational
- **Blockchain Learning**: Complete cryptocurrency implementation
- **Academic Research**: Consensus algorithms and distributed systems
- **Computer Science**: Cryptography and network programming

### Development
- **Blockchain Development**: Foundation for blockchain applications
- **Testing Environment**: Safe environment for blockchain experimentation
- **Prototype Development**: Rapid blockchain prototype development

## ⚠️ Known Limitations

This is an educational project with intentional simplifications:

- **Simplified P2P**: Uses HTTP polling rather than a full gossip protocol
- **No SPV Support**: Merkle proofs exist but light client verification is not implemented
- **Simplified Difficulty**: Basic leading-zeros difficulty rather than Bitcoin's full target calculation
- **No Script System**: Transactions use simplified validation rather than Bitcoin Script

These limitations are intentional to keep the codebase understandable while demonstrating core blockchain concepts.

## 📚 Documentation

- **[Terminal Guide](docs/TERMINAL_GUIDE.md)**: Complete multi-terminal setup guide
- **[Database Monitor Commands](docs/DATABASE_MONITOR_COMMANDS.md)**: Real-time monitoring guide
- **[Configuration Guide](docs/CONFIGURATION_GUIDE.md)**: Mining difficulty and system configuration
- **[Terminal Commands](docs/TERMINAL_COMMANDS.md)**: Updated multi-node network commands

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🎯 Success Indicators

Your ChainCore network is working correctly when you see:

✅ **Database Connected**: Database monitor shows blockchain data  
✅ **Nodes Synced**: All nodes show identical `blockchain_length`  
✅ **Peer Connections**: Nodes show `active_peers > 0`  
✅ **Mining Active**: Database monitor shows new blocks being mined  
✅ **Transactions Processing**: Wallet operations complete successfully  

---

**ChainCore** - A ground-up blockchain implementation in Python.

### Cryptographic Security

- **ECDSA signatures** for all transactions
- **Double SHA-256** hashing for blocks
- **Secure random nonce** generation
- **Address validation** and checksum verification

### Network Security

- **Input validation** on all API endpoints
- **Rate limiting** and connection management
- **Peer authentication** and validation
- **Protection against common attacks**

### Thread Safety

- **Comprehensive locking** mechanisms
- **Deadlock detection** and prevention
- **Atomic operations** for critical sections
- **MVCC isolation** for concurrent access

## =� Performance Optimization

### Multi-Core Mining

- **Automatic CPU detection** and optimal worker allocation
- **CPU core affinity** for reduced context switching
- **Parallel proof-of-work** computation
- **Intelligent work distribution**

### Network Optimization

- **Connection pooling** for database access
- **Efficient peer discovery** with concurrent scanning
- **Adaptive timeouts** based on network size
- **Smart caching** and template management

### Memory Management

- **Bounded data structures** to prevent memory leaks
- **Efficient serialization** and caching
- **Resource cleanup** on shutdown
- **Configurable limits** and thresholds

## >� Development and Testing

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test categories
python -m pytest tests/test_blockchain.py
python -m pytest tests/test_mining.py
python -m pytest tests/test_networking.py
```

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Enable verbose logging
python network_node.py --debug --verbose

# Single-core mining for testing
python mining_client.py --wallet <address> --single-core
```

### Configuration Files

The project includes example configuration files:

- `src/wallets/alice.json` - Example wallet configuration
- `src/wallets/bob.json` - Example wallet configuration
- `miner1.json`, `miner2.json` - Mining configurations

## =� Use Cases

### Educational

- **Blockchain learning** and experimentation
- **Cryptocurrency concepts** demonstration
- **Distributed systems** research
- **Consensus algorithms** study

### Development

- **Blockchain application** development
- **Cryptocurrency** implementation
- **P2P network** research

## > Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## =� License

This project is open source and available under the [MIT License](LICENSE).

## =. Future Roadmap

### Planned Features

- **Smart contracts** with virtual machine
- **WebSocket support** for real-time updates
- **GraphQL API** for advanced querying
- **Mobile wallet** integration
- **Lightning Network** style payment channels

### Performance Improvements

- **GPU mining** support
- **Advanced caching** mechanisms
- **Database sharding** for scalability
- **Network protocol** optimization

## =� Support

For questions, issues, or contributions:

- **GitHub Issues**: Report bugs and request features
- **Documentation**: Comprehensive code documentation
- **Examples**: Working examples in the repository
- **Community**: Join discussions and share experiences

---

**ChainCore** - A ground-up blockchain implementation in Python.
