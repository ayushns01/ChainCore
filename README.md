# ChainCore

A comprehensive, production-ready blockchain implementation built in Python with advanced features including thread-safe operations, multi-core mining, P2P networking, and distributed consensus mechanisms.

## =€ Project Overview

ChainCore is a full-featured blockchain platform that implements a complete cryptocurrency system with:

- **Secure Blockchain Architecture**: Bitcoin-style UTXO model with ECDSA cryptographic signatures
- **Thread-Safe Operations**: Comprehensive concurrency control with reader-writer locks and MVCC
- **Multi-Core Mining**: Optimized proof-of-work mining with parallel processing and CPU affinity
- **P2P Network Layer**: Robust peer discovery, connection management, and network synchronization
- **Distributed Consensus**: Fork resolution, chain reorganization, and network-wide consensus
- **Database Integration**: PostgreSQL support with connection pooling and transaction management
- **RESTful API**: Complete HTTP API for blockchain interaction and monitoring
- **Advanced Monitoring**: Real-time blockchain tracking, statistics, and network analysis

## <× Architecture

### Core Components

#### 1. Network Node (`network_node.py`)
The main blockchain node that handles:
- **Thread-safe blockchain operations** with deadlock detection
- **P2P network management** with automatic peer discovery
- **API server** with comprehensive REST endpoints
- **Mining coordination** and block validation
- **Real-time synchronization** with network consensus

#### 2. Mining Client (`mining_client.py`)
High-performance mining implementation featuring:
- **Multi-core mining** with worker thread pools
- **CPU core affinity** for optimal performance
- **Intelligent template refresh** and network state monitoring
- **Exponential backoff** and retry mechanisms
- **Mining coordination** to prevent conflicts

#### 3. Blockchain Core (`src/blockchain/`)
- **Block structure** with Merkle trees and metadata preservation
- **UTXO management** with snapshot isolation
- **Transaction validation** with ECDSA verification
- **Chain synchronization** with fork resolution
- **Mining attribution** tracking and statistics

#### 4. Cryptography (`src/crypto/`)
- **ECDSA signatures** for transaction security
- **Double SHA-256 hashing** for proof-of-work
- **Address validation** with Bitcoin-style format
- **Secure random number generation**

#### 5. P2P Networking (`src/networking/`)
- **Peer discovery** with configurable port scanning
- **Connection management** with health monitoring
- **Broadcast protocols** for transaction and block propagation
- **Network-wide statistics** collection and sharing

#### 6. Concurrency Control (`src/concurrency/`)
- **Thread-safe wrappers** for all blockchain operations
- **Reader-writer locks** with priority handling
- **Deadlock detection** and prevention
- **MVCC for UTXOs** with transaction isolation

### Database Layer (`src/database/`)
- **PostgreSQL integration** with SQLAlchemy ORM
- **Connection pooling** for high-performance access
- **Block and transaction storage** with indexing
- **Mining statistics** tracking and analysis

## =€ Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL (optional, for persistent storage)
- Required Python packages (see `requirements.txt`)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd ChainCore
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Optional - Set up PostgreSQL:**
   ```bash
   # Create database
   createdb chaincore
   
   # Configure connection in src/database/config.py
   ```

### Quick Start

1. **Start a blockchain node:**
   ```bash
   python network_node.py --node-id core1 --api-port 5001
   ```

2. **Start additional nodes for P2P network:**
   ```bash
   python network_node.py --node-id core2 --api-port 5002
   python network_node.py --node-id core3 --api-port 5003
   ```

3. **Start mining:**
   ```bash
   python mining_client.py --wallet 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa --node http://localhost:5001
   ```

4. **Monitor the blockchain:**
   ```bash
   python blockchain_monitor.py --nodes http://localhost:5001,http://localhost:5002
   ```

## =' Configuration

### Node Configuration
Key configuration options in `src/config.py`:
- **BLOCKCHAIN_DIFFICULTY**: Mining difficulty (default: 3)
- **BLOCK_REWARD**: Mining reward (default: 50.0)
- **TARGET_BLOCK_TIME**: Target time between blocks (default: 10s)
- **PEER_DISCOVERY_RANGE**: Port range for peer discovery

### Mining Configuration
Configure mining parameters:
- **Multi-core workers**: Auto-detected CPU cores
- **CPU affinity**: Enabled for optimal performance  
- **Mining timeout**: Configurable per-attempt timeout
- **Template refresh**: Automatic stale template detection

### Network Configuration
P2P networking settings:
- **MIN_PEERS**: Minimum peer connections (default: 2)
- **TARGET_PEERS**: Optimal peer count (default: 6)
- **MAX_PEERS**: Maximum connections (default: 12)

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

## =Ê Monitoring and Analytics

### Blockchain Monitor (`blockchain_monitor.py`)
Real-time monitoring dashboard with:
- **Live blockchain statistics**
- **Mining activity tracking**
- **Network health monitoring**
- **Transaction flow analysis**
- **Multi-node comparison**

### Database Monitor (`database_monitor.py`)
Database-level monitoring including:
- **Block and transaction counts**
- **Mining statistics and attribution**
- **Performance metrics**
- **Chain integrity verification**

### Network Analysis (`blockchain_tracker_with_json.py`)
Comprehensive network analysis:
- **Chain exploration and validation**
- **Mining distribution analysis**
- **Transaction pattern analysis**
- **JSON export for external analysis**

## = Security Features

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

## =€ Performance Optimization

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

## >ê Development and Testing

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
- `alice.json` - Example wallet configuration
- `bob.json` - Example wallet configuration  
- `miner1.json`, `miner2.json` - Mining configurations

## =È Use Cases

### Educational
- **Blockchain learning** and experimentation
- **Cryptocurrency concepts** demonstration
- **Distributed systems** research
- **Consensus algorithms** study

### Development
- **Blockchain application** development
- **Smart contract** platform foundation
- **Cryptocurrency** implementation
- **P2P network** research

### Production
- **Private blockchain** networks
- **Consortium chains** for organizations
- **Testing environments** for blockchain applications
- **Research platforms** for academic institutions

## > Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## =Ä License

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

## =Þ Support

For questions, issues, or contributions:
- **GitHub Issues**: Report bugs and request features
- **Documentation**: Comprehensive code documentation
- **Examples**: Working examples in the repository
- **Community**: Join discussions and share experiences

---

**ChainCore** - A modern, secure, and scalable blockchain platform built for education, development, and production use.