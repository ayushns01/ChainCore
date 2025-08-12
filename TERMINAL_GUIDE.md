# ChainCore Blockchain - Complete Terminal Guide

Complete step-by-step guide to run the ChainCore blockchain with **enterprise-grade thread safety**.

## 🔧 Prerequisites

1. **Python Environment Setup**

```bash
cd /Users/ayush/Desktop/ChainCore
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Verify Project Structure**

## 🚀 Starting Network Nodes

### Terminal 1: Start First Network Node

```bash
cd /Users/ayush/Desktop/ChainCore
source venv/bin/activate
python3 network_node.py --node-id core0 --api-port 5000 --p2p-port 8000
```

### Terminal 2: Start Second Network Node

```bash
cd /Users/ayush/Desktop/ChainCore
source venv/bin/activate
python3 network_node.py --node-id core1 --api-port 5001 --p2p-port 8001
```

### Terminal 3: Start Third Network Node

```bash
cd /Users/ayush/Desktop/ChainCore
source venv/bin/activate
python3 network_node.py --node-id core2 --api-port 5002 --p2p-port 8002
```

### Terminal 4: Additional Nodes (Optional)

```bash
python3 network_node.py --node-id core3 --api-port 5003 --p2p-port 8003
python3 network_node.py --node-id core4 --api-port 5004 --p2p-port 8004
python3 network_node.py --node-id core5 --api-port 5005 --p2p-port 8005
python3 network_node.py --node-id core6 --api-port 5006 --p2p-port 8006
python3 network_node.py --node-id core7 --api-port 5007 --p2p-port 8007
python3 network_node.py --node-id core8 --api-port 5008 --p2p-port 8008
python3 network_node.py --node-id core9 --api-port 5009 --p2p-port 8009
python3 network_node.py --node-id core10 --api-port 5010 --p2p-port 8010
python3 network_node.py --node-id core11 --api-port 5011 --p2p-port 8011
```

### 🔍 Node Options

```bash
# Enable debug logging
python3 network_node.py --node-id core1 --api-port 5000 --p2p-port 8000 --debug

# Skip peer discovery on startup
python3 network_node.py --node-id core1 --api-port 5000 --p2p-port 8000 --no-discover
```

## 💳 Wallet Operations

### Terminal 5: Create Wallets

```bash
cd /Users/ayush/Desktop/ChainCore
source venv/bin/activate

# Create wallet files (if they don't exist)
python3 wallet_client.py create --wallet alice.json
python3 wallet_client.py create --wallet bob.json
python3 wallet_client.py create --wallet miner1.json
python3 wallet_client.py create --wallet miner2.json

# Check wallet information
python3 wallet_client.py info --wallet alice.json
python3 wallet_client.py info --wallet bob.json
python3 wallet_client.py info --wallet miner1.json
python3 wallet_client.py info --wallet miner2.json
```

### Wallet Commands

```bash
# Check balance
python3 wallet_client.py balance --wallet alice.json --node http://localhost:5000

# Send transaction
python3 wallet_client.py send --wallet alice.json --node http://localhost:5000 --to BOB_ADDRESS --amount 10.0 --fee 0.5

# Transaction history
python3 wallet_client.py history --wallet alice.json --node http://localhost:5000
```

## ⛏️ Mining Operations

### Terminal 6: Start Miners

```bash
cd /Users/ayush/Desktop/ChainCore
source venv/bin/activate

# Start miner with wallet address
python3 mining_client.py --wallet MINER_ADDRESS --node http://localhost:5000

# Example with real addresses (replace with your wallet addresses)
python3 mining_client.py --wallet 1CcUyVAiHT2dGP4ESxWqsDKFzazkQ2UW3n --node http://localhost:5000
python3 mining_client.py --wallet 1GukayKD1hRAXnQaJYKVwQcwCvVzsUbcJj --node http://localhost:5001
```

### Multiple Competitive Miners

```bash
# Terminal 7-12: Additional miners for competition
python3 mining_client.py --wallet 18NDhHYAa3bx3jAZkc7HZf3vKr1JrwVXG3 --node http://localhost:5000
python3 mining_client.py --wallet 1GukayKD1hRAXnQaJYKVwQcwCvVzsUbcJj --node http://localhost:5001
python3 mining_client.py --wallet 1CcUyVAiHT2dGP4ESxWqsDKFzazkQ2UW3n --node http://localhost:5002
python3 mining_client.py --wallet 18NDhHYAa3bx3jAZkc7HZf3vKr1JrwVXG3 --node http://localhost:5003
python3 mining_client.py --wallet 1GukayKD1hRAXnQaJYKVwQcwCvVzsUbcJj --node http://localhost:5004
python3 mining_client.py --wallet 1CcUyVAiHT2dGP4ESxWqsDKFzazkQ2UW3n --node http://localhost:5005
python3 mining_client.py --wallet 18NDhHYAa3bx3jAZkc7HZf3vKr1JrwVXG3 --node http://localhost:5006
python3 mining_client.py --wallet 1GukayKD1hRAXnQaJYKVwQcwCvVzsUbcJj --node http://localhost:5007
python3 mining_client.py --wallet 1CcUyVAiHT2dGP4ESxWqsDKFzazkQ2UW3n --node http://localhost:5007
python3 mining_client.py --wallet 18NDhHYAa3bx3jAZkc7HZf3vKr1JrwVXG3 --node http://localhost:5008
python3 mining_client.py --wallet 1GukayKD1hRAXnQaJYKVwQcwCvVzsUbcJj --node http://localhost:5009
python3 mining_client.py --wallet 1CcUyVAiHT2dGP4ESxWqsDKFzazkQ2UW3n --node http://localhost:5010
```

## 🌐 Network Monitoring & API Commands

### Check Network Status

```bash
# Basic status
curl http://localhost:5000/status
curl http://localhost:5001/status
curl http://localhost:5002/status
curl http://localhost:5003/status
curl http://localhost:5004/status
curl http://localhost:5005/status
curl http://localhost:5006/status


# Detailed statistics (NEW - Thread Safety Stats)
curl http://localhost:5000/stats | python3 -m json.tool

# Check peer connections
curl http://localhost:5000/peers | python3 -m json.tool
```

### Blockchain Operations

```bash
# Get full blockchain
curl http://localhost:5000/blockchain | python3 -m json.tool

# Check transaction pool
curl http://localhost:5000/transaction_pool | python3 -m json.tool

# Get balance
curl http://localhost:5000/balance/ADDRESS | python3 -m json.tool

# Get UTXOs for address
curl http://localhost:5000/utxos/ADDRESS | python3 -m json.tool

# Get transaction history (NEW)
curl http://localhost:5000/transactions/ADDRESS | python3 -m json.tool
```

### Network Management

```bash
# Force peer discovery
curl -X POST http://localhost:5000/discover_peers -H "Content-Type: application/json" -d '{"port_start": 5000, "port_end": 5010}'

# Manual blockchain sync
curl -X POST http://localhost:5000/sync_now

# Check peer health
curl http://localhost:5000/peer_health | python3 -m json.tool
```

### Session Management (NEW)

```bash
# Get current session info
curl http://localhost:5000/session_info | python3 -m json.tool

# List all sessions
curl http://localhost:5000/sessions | python3 -m json.tool

# Get mining statistics
curl http://localhost:5000/mining_stats | python3 -m json.tool

# Update mining statistics manually
curl -X POST http://localhost:5000/update_mining_stats
```

### Mining Operations

```bash
# Get block template for mining
curl -X POST http://localhost:5000/mine_block -H "Content-Type: application/json" -d '{"miner_address": "YOUR_ADDRESS"}'

# Submit mined block
curl -X POST http://localhost:5000/submit_block -H "Content-Type: application/json" -H "X-Local-Mining: true" -d '@block_data.json'
```

### Transaction Operations

```bash
# Add/broadcast transaction
curl -X POST http://localhost:5000/add_transaction -H "Content-Type: application/json" -d '@transaction.json'

# Alternative endpoint for wallet compatibility
curl -X POST http://localhost:5000/broadcast_transaction -H "Content-Type: application/json" -d '@transaction.json'
```

## 📊 Real-Time Monitoring

### Continuous Network Status

```bash
# Real-time monitoring loop
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
    thread_safe = '🔒' if data.get('thread_safe') else '⚠️'
    print(f'{thread_safe} Blocks: {data[\"blockchain_length\"]}, Pending: {data[\"pending_transactions\"]}, Peers: {data[\"peers\"]}, API Calls: {data.get(\"api_calls\", 0)}')
except:
    print('❌ Offline')
" 2>/dev/null
  done

  echo ""
  echo "Press Ctrl+C to stop monitoring"
  sleep 5
done
```

### Balance Monitoring

```bash
# Monitor balances in real-time
while true; do
  clear
  echo "💰 Wallet Balances - $(date)"
  echo "================================="

  if [ -f alice.json ]; then
    ALICE_ADDR=$(python3 -c "import json; print(json.load(open('alice.json'))['address'])")
    echo "Alice   ($ALICE_ADDR): $(curl -s http://localhost:5000/balance/$ALICE_ADDR | python3 -c "import sys,json; print(json.load(sys.stdin)['balance'])")"
  fi

  if [ -f bob.json ]; then
    BOB_ADDR=$(python3 -c "import json; print(json.load(open('bob.json'))['address'])")
    echo "Bob     ($BOB_ADDR): $(curl -s http://localhost:5000/balance/$BOB_ADDR | python3 -c "import sys,json; print(json.load(sys.stdin)['balance'])")"
  fi

  if [ -f miner1.json ]; then
    MINER1_ADDR=$(python3 -c "import json; print(json.load(open('miner1.json'))['address'])")
    echo "Miner1  ($MINER1_ADDR): $(curl -s http://localhost:5000/balance/$MINER1_ADDR | python3 -c "import sys,json; print(json.load(sys.stdin)['balance'])")"
  fi

  sleep 10
done
```

### Thread Safety Monitoring (NEW)

```bash
# Monitor thread safety statistics
while true; do
  clear
  echo "🔒 Thread Safety Statistics - $(date)"
  echo "======================================"

  curl -s http://localhost:5000/stats | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'API Calls: {data[\"node_stats\"][\"api_calls\"]}')
    print(f'Uptime: {data[\"node_stats\"][\"uptime\"]:.1f}s')
    print(f'')
    print('Lock Statistics:')
    for lock, stats in list(data['lock_stats'].items())[:5]:
        print(f'  {lock}: {stats[\"acquisitions\"]} acq, {stats[\"contentions\"]} cont')
    print(f'')
    print(f'Peer Stats: {data[\"peer_stats\"][\"active_peers\"]} active')
    print(f'Session: {data[\"session_stats\"][\"current_session\"]}')
except Exception as e:
    print(f'Error: {e}')
"

  sleep 3
done
```

## ⚙️ Configuration

### Adjust Mining Difficulty (For Weak Hardware)

Edit `/Users/ayush/Desktop/ChainCore/src/config.py`:

```python
# Change this single line to adjust mining difficulty across entire system
BLOCKCHAIN_DIFFICULTY = 1  # Very easy  - "0" prefix (recommended for laptops)
BLOCKCHAIN_DIFFICULTY = 2  # Easy      - "00" prefix
BLOCKCHAIN_DIFFICULTY = 3  # Medium    - "000" prefix
BLOCKCHAIN_DIFFICULTY = 4  # Hard      - "0000" prefix
BLOCKCHAIN_DIFFICULTY = 5  # Very hard - "00000" prefix (original)
```

**⚠️ Important**: Restart all nodes after changing difficulty:

```bash
pkill -f network_node.py && pkill -f mining_client.py
# Then restart your nodes
```

See `CONFIGURATION_GUIDE.md` for complete instructions.

### Performance Tuning

```bash
# Enable debug mode for detailed logs
python3 network_node.py --node-id core1 --api-port 5000 --p2p-port 8000 --debug

# Skip initial peer discovery for faster startup
python3 network_node.py --node-id core1 --api-port 5000 --p2p-port 8000 --no-discover
```

## 🛠️ Troubleshooting

### Node Not Starting

```bash
# Check if port is in use
lsof -i :5000

# Kill existing processes
pkill -f network_node.py
pkill -f mining_client.py

# Check Python environment
which python3
source venv/bin/activate
```

### Thread Safety Issues

```bash
# Check thread safety status
curl http://localhost:5000/status | python3 -c "import sys,json; data=json.load(sys.stdin); print('Thread Safe:', data.get('thread_safe', False))"

# View lock statistics for contention issues
curl http://localhost:5000/stats | python3 -c "import sys,json; data=json.load(sys.stdin); print('Lock Stats:', data.get('lock_stats', {}))"
```

### Mining Not Working

```bash
# Check node is running and responsive
curl http://localhost:5000/status

# Verify wallet address format
python3 wallet_client.py info --wallet miner1.json

# Check mining template generation
curl -X POST http://localhost:5000/mine_block -H "Content-Type: application/json" -d '{"miner_address": "test"}'
```

### Transaction Issues

```bash
# Check balance first
python3 wallet_client.py balance --wallet sender.json --node http://localhost:5000

# Check transaction pool
curl http://localhost:5000/transaction_pool

# View transaction history
curl http://localhost:5000/transactions/ADDRESS
```

### Peer Connection Issues

```bash
# Force peer discovery
curl -X POST http://localhost:5000/discover_peers

# Check peer health
curl http://localhost:5000/peer_health

# Manual sync
curl -X POST http://localhost:5000/sync_now
```

## 🛑 Shutdown

### Stop Everything

```bash
# Stop each terminal with Ctrl+C

# Or force kill all processes
pkill -f network_node.py
pkill -f mining_client.py
pkill -f wallet_client.py
```

## ✅ Success Indicators

Your blockchain is working correctly when you see:

1. **Thread Safety Active**: Status shows `"thread_safe": true` 🔒
2. **Nodes Running**: All nodes respond to `/status` with peer connections
3. **Zero Contentions**: `/stats` shows `"contentions": 0` for all locks
4. **Mining Active**: Terminal shows "Block X mined!" messages
5. **Balances Growing**: Miners accumulate block rewards
6. **Transactions Processing**: Sent transactions appear in pools and get mined
7. **Network Sync**: All nodes show same blockchain length
8. **Session Tracking**: Sessions are recorded and statistics updated

**🚀 You now have a fully functional enterprise-grade blockchain network!**

## 🔥 Advanced Features

- **Enterprise Thread Safety**: Advanced reader-writer locks with deadlock detection
- **MVCC UTXO Management**: Snapshot isolation for concurrent operations
- **Atomic Operations**: All blockchain state changes are atomic
- **Connection Pooling**: Rate limiting and concurrent peer management
- **Session Management**: Cross-process file locking and session coordination
- **Real-time Monitoring**: Comprehensive lock statistics and performance metrics
- **Competitive Mining**: Multiple miners compete with work coordination
- **Transaction Broadcasting**: Transactions spread across all nodes with thread safety
- **Automatic Sync**: Nodes sync every 30 seconds with atomic operations
- **Load Balancing**: Connect wallets to different nodes safely

## 📈 Performance Benefits

- **Zero Lock Contentions**: Perfect thread safety without performance loss
- **Concurrent Operations**: Multiple API calls processed simultaneously
- **Microsecond Lock Times**: Enterprise-grade lock acquisition performance
- **Scalable Architecture**: Handles multiple nodes and miners efficiently
- **Fault Tolerant**: Deadlock detection and automatic recovery

For more advanced operations, see:

- `src/concurrency/THREAD_SAFETY_GUIDE.md` - Complete thread safety documentation
- `MINING_COMMANDS.md` - Mining operations guide
- `PEER_MANAGEMENT_NETWORKING.md` - Network operations guide
