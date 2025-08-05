# ChainCore Multi-Terminal Workflow

Complete guide for running ChainCore blockchain across multiple terminals with manual node control and automatic P2P synchronization.

## 🖥️ **Manual Terminal Setup - Full Control**

### **Terminal 1: First Node**
```bash
cd /Users/ayush/Desktop/chain
source venv/bin/activate
python3 network_node.py --node-id core1 --api-port 5000 --p2p-port 8000

# Output shows:
# 🚀 Starting Network Node core1
#    P2P Port: 8000
#    API Port: 5000
#    Blockchain: 1 blocks
# ✅ Node running!
```

### **Terminal 2: Second Node (Auto-Syncs with First)**
```bash
cd /Users/ayush/Desktop/chain
source venv/bin/activate
python3 network_node.py --node-id core2 --api-port 5001 --p2p-port 8001

# Node automatically discovers and syncs with core1
```

### **Terminal 3: Third Node (Auto-Syncs with Network)**
```bash
cd /Users/ayush/Desktop/chain
source venv/bin/activate
python3 network_node.py --node-id core3 --api-port 5002 --p2p-port 8002

# Node automatically discovers and syncs with existing network
```

### **Terminal 4: Wallet Operations**
```bash
cd /Users/ayush/Desktop/chain
source venv/bin/activate

# Check balances (initially 0)
python3 wallet_client.py balance --wallet miner.json
python3 wallet_client.py balance --wallet miner1.json
python3 wallet_client.py balance --wallet miner2.json
python3 wallet_client.py balance --wallet alice.json
python3 wallet_client.py balance --wallet bob.json

# Create additional wallets if needed
python3 wallet_client.py create --wallet new_user.json
```

### **Terminal 5: Competitive Mining Setup**
```bash
cd /Users/ayush/Desktop/chain
source venv/bin/activate

# Create multiple miners for competition
python3 mining_client.py create --wallet miner1.json
python3 mining_client.py create --wallet miner2.json

# Get miner addresses
MINER1=$(python3 -c "import json; print(json.load(open('miner1.json'))['address'])")
MINER2=$(python3 -c "import json; print(json.load(open('miner2.json'))['address'])")

echo "Miner1: $MINER1"
echo "Miner2: $MINER2"
```

### **Terminal 6: API Testing & Monitoring**
```bash
# Check network status and synchronization
curl http://localhost:5000/status
curl http://localhost:5001/status
curl http://localhost:5002/status
curl http://localhost:5003/status
curl http://localhost:5004/status
curl http://localhost:5005/status

# Check peer connections
curl http://localhost:5000/peers
curl http://localhost:5001/peers
curl http://localhost:5002/peers

# Check balances via API (use actual addresses)
curl http://localhost:5000/balance/17PVoFzAniw34i839GRDzA4gjm9neJRet8  # Miner
curl http://localhost:5000/balance/1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu   # Alice
curl http://localhost:5000/balance/171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7  # Bob

# Get blockchain info
curl http://localhost:5000/blockchain

# Check transaction pool
curl http://localhost:5000/transaction_pool

# Monitor UTXOs
curl http://localhost:5000/utxos/17PVoFzAniw34i839GRDzA4gjm9neJRet8
```

### **Terminal 7: Transaction Operations**
```bash
cd /Users/ayush/Desktop/chain
source venv/bin/activate

# Send transactions between wallets (wait for mining rewards first)
python3 wallet_client.py send --wallet miner.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 50 --fee 1.0
python3 wallet_client.py send --wallet alice.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 25 --fee 0.5

# Send to different nodes for load balancing
python3 wallet_client.py send --wallet miner.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 30 --node http://localhost:5001
python3 wallet_client.py send --wallet alice.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 15 --node http://localhost:5002

# Check transaction history
python3 wallet_client.py history --wallet alice.json
python3 wallet_client.py history --wallet bob.json
python3 wallet_client.py history --wallet miner.json
```

## 🔄 **Complete Manual Workflow Example**

### **Step 1: Start First Node (Terminal 1)**
```bash
cd /Users/ayush/Desktop/chain
source venv/bin/activate
python3 network_node.py --node-id core1 --api-port 5000 --p2p-port 8000
```

### **Step 2: Start Additional Nodes (Terminals 2 & 3)**
```bash
# Terminal 2
cd /Users/ayush/Desktop/chain
source venv/bin/activate
python3 network_node.py --node-id core2 --api-port 5001 --p2p-port 8001

# Terminal 3  
cd /Users/ayush/Desktop/chain
source venv/bin/activate
python3 network_node.py --node-id core3 --api-port 5002 --p2p-port 8002
```

### **Step 3: Verify Network Sync (Terminal 4)**
```bash
cd /Users/ayush/Desktop/chain
source venv/bin/activate

# Check all nodes are synchronized
curl http://localhost:5000/status
curl http://localhost:5001/status
curl http://localhost:5002/status

# Verify peer connections
curl http://localhost:5000/peers
```

### **Step 4: Start Competitive Mining (Terminals 5 & 6)**
```bash
# Terminal 5: Miner1 on Node 1
cd /Users/ayush/Desktop/chain
source venv/bin/activate
python3 mining_client.py --wallet 1GukayKD1hRAXnQaJYKVwQcwCvVzsUbcJj --node http://localhost:5000

# Terminal 6: Miner2 on Node 2 (COMPETITIVE)
cd /Users/ayush/Desktop/chain
source venv/bin/activate
python3 mining_client.py --wallet 18NDhHYAa3bx3jAZkc7HZf3vKr1JrwVXG3 --node http://localhost:5001
```

### **Step 5: Monitor Mining Competition (Terminal 7)**
```bash
cd /Users/ayush/Desktop/chain
source venv/bin/activate

# Wait for blocks to be mined, then check balances
curl http://localhost:5000/balance/17PVoFzAniw34i839GRDzA4gjm9neJRet8  # Miner
curl http://localhost:5000/balance/1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu   # Alice
curl http://localhost:5000/balance/171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7  # Bob

# Check blockchain growth
curl -s http://localhost:5000/status | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Blocks: {data[\"blockchain_length\"]}, Peers: {data[\"peers\"]}')
"
```

### **Step 6: Send Transactions (Terminal 8)**
```bash
cd /Users/ayush/Desktop/chain
source venv/bin/activate

# Wait for mining rewards, then send transactions
python3 wallet_client.py send --wallet miner.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 75 --fee 1.0
python3 wallet_client.py send --wallet alice.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 25 --fee 0.5

# Check final balances
python3 wallet_client.py balance --wallet alice.json
python3 wallet_client.py balance --wallet bob.json
python3 wallet_client.py balance --wallet miner.json
```

### **Step 7: Verify Network Synchronization (Terminal 9)**
```bash
# Check transaction was processed across all nodes
curl http://localhost:5000/transaction_pool
curl http://localhost:5001/transaction_pool
curl http://localhost:5002/transaction_pool

# Verify balances are consistent across all nodes
echo "=== Alice Balance Across All Nodes ==="
curl http://localhost:5000/balance/1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu
curl http://localhost:5001/balance/1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu
curl http://localhost:5002/balance/1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu

# Check blockchain synchronization
echo "=== Blockchain Length Across All Nodes ==="
for port in 5000 5001 5002; do
  echo -n "Node $port: "
  curl -s http://localhost:$port/status | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'{data[\"blockchain_length\"]} blocks')
"
done
```

## 🔗 **P2P Network Management**

### **Automatic Features**
- **✅ Auto Peer Discovery**: Nodes automatically find each other on ports 5000-5005
- **✅ Blockchain Sync**: Nodes sync to longest chain every 30 seconds
- **✅ Transaction Broadcasting**: Transactions spread across all connected peers
- **✅ Block Propagation**: New blocks automatically sync across network

### **Manual Peer Management**
```bash
# View current peers
curl http://localhost:5000/peers

# Add custom peer (if using non-standard ports)
curl -X POST http://localhost:5000/add_peer \
  -H "Content-Type: application/json" \
  -d '{"peer_url": "http://localhost:5003"}'

# Check peer connections across all nodes
for port in 5000 5001 5002; do
  echo "Node $port peers:"
  curl -s http://localhost:$port/peers | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'  Connected to {data[\"peer_count\"]} peers')
for peer in data['peers']:
    print(f'  - {peer}')
"
done
```

### **Network Expansion**
```bash
# Start additional nodes on any available ports
python3 network_node.py --node-id core4 --api-port 5003 --p2p-port 8003
python3 network_node.py --node-id core5 --api-port 5004 --p2p-port 8004

# Nodes automatically discover and sync with existing network
```

## 🎯 **API Commands Reference**

### **Node Status**
```bash
# Basic status
curl http://localhost:5000/status

# Formatted JSON
curl -s http://localhost:5000/status | python3 -m json.tool
```

### **Balance Checking**
```bash
# Check single balance
curl http://localhost:5000/balance/1A2B3C...

# Check across all nodes
for port in 5000 5001 5002; do
  echo "Node $port:"
  curl http://localhost:$port/balance/1A2B3C...
done
```

### **Blockchain Data**
```bash
# Full blockchain
curl http://localhost:5000/blockchain

# Just block count
curl -s http://localhost:5000/blockchain | jq '.length'

# Latest block
curl -s http://localhost:5000/blockchain | jq '.chain[-1]'
```

### **Transaction Pool**
```bash
# Pending transactions
curl http://localhost:5000/transaction_pool

# Count pending
curl -s http://localhost:5000/transaction_pool | jq '.count'
```

### **UTXOs**
```bash
# Get UTXOs for address
curl http://localhost:5000/utxos/1A2B3C...

# Count UTXOs
curl -s http://localhost:5000/utxos/1A2B3C... | jq '.utxos | length'
```

## 🔧 **Multi-Node Load Testing**

### **Distribute Operations Across Nodes**
```bash
# Use different nodes for different operations
python3 wallet_client.py balance --wallet alice.json --node http://localhost:5000
python3 wallet_client.py balance --wallet bob.json --node http://localhost:5001
python3 wallet_client.py balance --wallet miner.json --node http://localhost:5002

# Mine on different nodes
python3 mining_client.py --wallet ADDR1 --node http://localhost:5000 &
python3 mining_client.py --wallet ADDR2 --node http://localhost:5001 &
python3 mining_client.py --wallet ADDR3 --node http://localhost:5002 &
```

### **API Load Balancing**
```bash
# Round-robin status checks
for i in {1..10}; do
  port=$((5000 + (i % 3)))
  echo "Request $i -> Node $port"
  curl http://localhost:$port/status
done
```

## 🎮 **Automated Demo**

### **Run Complete Demo**
```bash
# Terminal 1: Start network
python3 start_network.py

# Terminal 2: Run automated demo
python3 api_demo.py
```

## 🛑 **Shutdown**

### **Stop Everything**
```bash
# Stop network (Terminal 1: Ctrl+C)
# Or force stop all
python3 start_network.py stop

# Kill any remaining processes
pkill -f "network_node.py"
pkill -f "mining_client.py"
```

## 📊 **Monitoring Dashboard**

### **Real-time Network Status**
```bash
# Create monitoring loop
while true; do
  clear
  echo "🌐 ChainCore Network Status - $(date)"
  echo "================================"
  
  for port in 5000 5001 5002; do
    echo -n "Node $port: "
    curl -s http://localhost:$port/status | jq -r '"Blocks: \(.blockchain_length), Pending: \(.pending_transactions)"' 2>/dev/null || echo "Offline"
  done
  
  echo ""
  sleep 5
done
```

## 🏁 **Competitive Mining Example**

### **Setup Multiple Miners (Latest Fix)**
```bash
# Terminal 5: Miner1 on Node 1  
python3 mining_client.py --wallet 17PVoFzAniw34i839GRDzA4gjm9neJRet8 --node http://localhost:5000

# Terminal 6: Miner2 on Node 2
python3 mining_client.py --wallet 1GukayKD1hRAXnQaJYKVwQcwCvVzsUbcJj --node http://localhost:5001

# Terminal 6: Miner2 on Node 2
python3 mining_client.py --wallet 18NDhHYAa3bx3jAZkc7HZf3vKr1JrwVXG3 --node http://localhost:5002

# Terminal 7: Monitor competition
watch -n 2 'echo "=== Mining Competition ===" && \
curl -s http://localhost:5000/balance/1GukayKD1hRAXnQaJYKVwQcwCvVzsUbcJj | jq ".balance" && \
curl -s http://localhost:5001/balance/18NDhHYAa3bx3jAZkc7HZf3vKr1JrwVXG3 | jq ".balance"'
```

### **Transaction Broadcasting Test**
```bash
# Send one transaction - should appear on ALL nodes
python3 wallet_client.py send --wallet miner1.json --to 18NDhHYAa3bx3jAZkc7HZf3vKr1JrwVXG3 --amount 0.01

# Verify transaction distributed to all nodes
echo "=== Transaction Pool Distribution ==="
for port in 5000 5001 5002; do
  echo "Node $port:"
  curl -s http://localhost:$port/status | jq '.pending_transactions'
done
```

## 🎯 **Success Indicators**

### **Network Health**
- ✅ All nodes responding to `/status` API calls
- ✅ Each node shows `"peers": N` (where N > 0)
- ✅ Identical `blockchain_length` across all nodes
- ✅ `/peers` endpoint shows connected nodes

### **Mining Competition (FIXED)**
- ✅ Multiple miners can compete simultaneously
- ✅ Transactions distributed to ALL nodes
- ✅ Any miner can win regardless of connected node
- ✅ Block validation shows detailed error messages
- ✅ Mining client shows "Block mined!" messages
- ✅ Winner's balance increases (50 CC per block)

### **Transaction Broadcasting (FIXED)**
- ✅ One transaction → appears on ALL nodes
- ✅ All miners see same transaction pool  
- ✅ Fastest miner wins and adds block
- ✅ Transaction removed from all pools after mining

### **P2P Synchronization**
- ✅ New nodes automatically discover existing network
- ✅ Blockchain syncs within 30 seconds
- ✅ Balances consistent across all nodes
- ✅ Blocks broadcast immediately after mining

### **Manual Control**
- ✅ Can start nodes individually in any order
- ✅ Can add nodes dynamically to running network
- ✅ Each node operates independently
- ✅ Network continues if individual nodes go offline

**Your ChainCore network is working when you have full manual control with automatic P2P synchronization!** 🚀

## 📚 **Additional Resources**

- **Complete Command Reference**: See `COMMANDS.md` for all available commands
- **Transaction Testing**: Use `TXN_TESTING.md` for 20 transaction test scenarios  
- **Technical Details**: Check `BITCOIN_README.md` for implementation details