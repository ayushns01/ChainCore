# ChainCore Complete Command Reference A-Z

## 🔧 **Environment Setup**
```bash
cd /Users/ayush/Desktop/chain
source venv/bin/activate
```

---

## 🅰️ **A - API Commands**

### **API Status Checks**
```bash
# Check node status
curl http://localhost:5000/status
curl http://localhost:5001/status
curl http://localhost:5002/status

# Formatted JSON output
curl -s http://localhost:5000/status | python3 -m json.tool
```

### **API Balance Checks**
```bash
# Check balances via API
curl http://localhost:5000/balance/17PVoFzAniw34i839GRDzA4gjm9neJRet8  # Miner
curl http://localhost:5000/balance/1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu   # Alice
curl http://localhost:5000/balance/171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7  # Bob
```

### **API Blockchain Data**
```bash
# Get full blockchain
curl http://localhost:5000/blockchain

# Get blockchain length
curl -s http://localhost:5000/blockchain | python3 -c "import sys,json; data=json.load(sys.stdin); print('Total blocks:', len(data['chain']))"
```

---

## 🅱️ **B - Balance Commands**

### **Check Wallet Balances**
```bash
# Check balances using wallet files
python3 wallet_client.py balance --wallet alice.json
python3 wallet_client.py balance --wallet bob.json
python3 wallet_client.py balance --wallet miner.json

# Check balance on specific node
python3 wallet_client.py balance --wallet alice.json --node http://localhost:5001
```

### **Balance Monitoring Loop**
```bash
# Monitor all balances in real-time
while true; do
  echo "=== Balance Update $(date) ==="
  echo -n "Miner: "; curl -s http://localhost:5000/balance/17PVoFzAniw34i839GRDzA4gjm9neJRet8
  echo -n "Alice: "; curl -s http://localhost:5000/balance/1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu
  echo -n "Bob:   "; curl -s http://localhost:5000/balance/171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7
  sleep 10
done
```

---

## 🅲 **C - Create & Configuration**

### **Create Wallets**
```bash
# Create new wallets
python3 wallet_client.py create --wallet alice.json
python3 wallet_client.py create --wallet bob.json
python3 wallet_client.py create --wallet miner.json
python3 wallet_client.py create --wallet new_user.json
```

### **Check Connection**
```bash
# Test node connections
curl --max-time 5 http://localhost:5000/status
curl --max-time 5 http://localhost:5001/status
curl --max-time 5 http://localhost:5002/status
```

---

## 🆔 **D - Demo & Debug**

### **Demo Commands**
```bash
# Run complete automated demo
python3 api_demo.py

# Run basic functionality test
python3 simple_test.py

# Quick start script
python3 quick_start.py
```

### **Debug Network**
```bash
# Check what's running on ports
lsof -i :5000
lsof -i :5001
lsof -i :5002

# Check process status
ps aux | grep network_node
ps aux | grep mining_client
```

---

## 🇪 **E - Environment & Exit**

### **Environment Setup**
```bash
# Activate Python environment
source venv/bin/activate

# Check Python version
python3 --version

# Install dependencies
pip install -r requirements.txt
```

### **Exit/Stop Commands**
```bash
# Stop network gracefully (Ctrl+C in network terminal)
# Or force stop all processes
pkill -f "network_node.py"
pkill -f "mining_client.py"
```

---

## 🇫 **F - File Operations**

### **File Checks**
```bash
# List all files
ls -la

# Check wallet files
ls -la *.json

# View wallet contents
cat alice.json
cat bob.json
cat miner.json
```

---

## 🇬 **G - Get Information**

### **Get Node Information**
```bash
# Get detailed node status
curl -s http://localhost:5000/status | python3 -m json.tool

# Get peer count
curl -s http://localhost:5000/status | python3 -c "import sys,json; print('Peers:', json.load(sys.stdin)['peers'])"
```

### **Get Wallet Information**
```bash
# Get wallet details
python3 wallet_client.py info --wallet alice.json
python3 wallet_client.py info --wallet bob.json
python3 wallet_client.py info --wallet miner.json
```

---

## 🇭 **H - History & Help**

### **Transaction History**
```bash
# View transaction history
python3 wallet_client.py history --wallet alice.json
python3 wallet_client.py history --wallet bob.json
python3 wallet_client.py history --wallet miner.json
```

### **Help Commands**
```bash
# Get help for wallet client
python3 wallet_client.py --help

# Get help for mining client
python3 mining_client.py --help

# Get help for network node
python3 network_node.py --help
```

---

## 🇮 **I - Info & Inspection**

### **Inspect Blockchain**
```bash
# Get latest block info
curl -s http://localhost:5000/blockchain | python3 -c "
import sys, json
data = json.load(sys.stdin)
latest = data['chain'][-1]
print(f'Latest Block: {latest[\"index\"]}')
print(f'Hash: {latest[\"hash\"][:20]}...')
print(f'Transactions: {len(latest[\"transactions\"])}')
"
```

### **Inspect UTXOs**
```bash
# Get UTXOs for addresses
curl http://localhost:5000/utxos/17PVoFzAniw34i839GRDzA4gjm9neJRet8
curl http://localhost:5000/utxos/1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu
curl http://localhost:5000/utxos/171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7
```

---

## 🇯 **J - JSON Operations**

### **JSON Formatted Outputs**
```bash
# Pretty print status
curl -s http://localhost:5000/status | python3 -m json.tool

# Pretty print blockchain
curl -s http://localhost:5000/blockchain | python3 -m json.tool | head -50

# Pretty print transaction pool
curl -s http://localhost:5000/transaction_pool | python3 -m json.tool
```

---

## 🇰 **K - Kill Processes**

### **Kill Network Processes**
```bash
# Kill all network nodes
pkill -f "network_node.py"

# Kill all mining clients
pkill -f "mining_client.py"

# Kill specific process by PID (replace XXXX)
kill XXXX

# Force kill if needed
pkill -9 -f "python3.*network_node"
```

---

## 🇱 **L - Load Testing & Loops**

### **Load Testing**
```bash
# Distribute operations across nodes
python3 wallet_client.py balance --wallet alice.json --node http://localhost:5000
python3 wallet_client.py balance --wallet bob.json --node http://localhost:5001
python3 wallet_client.py balance --wallet miner.json --node http://localhost:5002

# Round-robin API calls
for i in {1..10}; do
  port=$((5000 + (i % 3)))
  echo "Request $i -> Node $port"
  curl http://localhost:$port/status
done
```

### **Monitoring Loops**
```bash
# Network status loop
while true; do
  clear
  echo "🌐 ChainCore Network Status - $(date)"
  echo "================================"
  for port in 5000 5001 5002; do
    echo -n "Node $port: "
    curl -s http://localhost:$port/status 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'Blocks: {data[\"blockchain_length\"]}, Pending: {len(data.get(\"pending_transactions\", []))}')
except:
    print('Offline')
" 2>/dev/null
  done
  sleep 5
done
```

---

## 🇲 **M - Mining Commands**

### **Start Mining**
```bash
# Mine with existing wallets
python3 mining_client.py --wallet 17PVoFzAniw34i839GRDzA4gjm9neJRet8 --node http://localhost:5000
python3 mining_client.py --wallet 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --node http://localhost:5001
python3 mining_client.py --wallet 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --node http://localhost:5002
```

### **Multiple Miners**
```bash
# Start multiple miners in background
python3 mining_client.py --wallet 17PVoFzAniw34i839GRDzA4gjm9neJRet8 --node http://localhost:5000 &
python3 mining_client.py --wallet 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --node http://localhost:5001 &
python3 mining_client.py --wallet 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --node http://localhost:5002 &
```

### **Mining Stats**
```bash
# Get mining statistics (if implemented)
python3 mining_client.py --wallet 17PVoFzAniw34i839GRDzA4gjm9neJRet8 --stats
```

---

## 🇳 **N - Network Commands**

### **Start Network**
```bash
# Start 3-node network
python3 start_network.py

# Start individual nodes
python3 network_node.py --node-id node1 --api-port 5000 --p2p-port 8000
python3 network_node.py --node-id node2 --api-port 5001 --p2p-port 8001
python3 network_node.py --node-id node3 --api-port 5002 --p2p-port 8002
```

### **Network Status**
```bash
# Check all nodes
for port in 5000 5001 5002; do
  echo "Node $port:"
  curl -s http://localhost:$port/status | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'  Status: Online')
    print(f'  Blocks: {data[\"blockchain_length\"]}')
    print(f'  Peers: {data[\"peers\"]}')
    print(f'  Pending: {data[\"pending_transactions\"]}')
except:
    print('  Status: Offline')
"
done
```

---

## 🇴 **O - Operations**

### **Basic Operations Workflow**
```bash
# Complete operational workflow
# Terminal 1: Start network
python3 start_network.py

# Terminal 2: Start mining
python3 mining_client.py --wallet 17PVoFzAniw34i839GRDzA4gjm9neJRet8 --node http://localhost:5000

# Terminal 3: Send transactions
python3 wallet_client.py send --wallet miner.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 50

# Terminal 4: Monitor
curl http://localhost:5000/status
```

---

## 🇵 **P - Pool & Processes**

### **Transaction Pool**
```bash
# Check pending transactions
curl http://localhost:5000/transaction_pool
curl http://localhost:5001/transaction_pool
curl http://localhost:5002/transaction_pool

# Count pending transactions
curl -s http://localhost:5000/transaction_pool | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Pending transactions: {len(data[\"transactions\"])}')
"
```

### **Process Management**
```bash
# List all blockchain processes
ps aux | grep -E "(network_node|mining_client|wallet_client)"

# Kill specific processes
pkill -f "mining_client.py"
pkill -f "network_node.py"
```

---

## 🇶 **Q - Quick Commands**

### **Quick Status Check**
```bash
# One-liner status check
echo "Network Status:"; curl -s http://localhost:5000/status 2>/dev/null && echo "✅ Online" || echo "❌ Offline"
```

### **Quick Balance Check**
```bash
# Quick balance summary
echo "=== Quick Balance Check ==="
echo -n "Miner: "; curl -s http://localhost:5000/balance/17PVoFzAniw34i839GRDzA4gjm9neJRet8 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['balance'])" 2>/dev/null || echo "Error"
echo -n "Alice: "; curl -s http://localhost:5000/balance/1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['balance'])" 2>/dev/null || echo "Error"
echo -n "Bob:   "; curl -s http://localhost:5000/balance/171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['balance'])" 2>/dev/null || echo "Error"
```

---

## 🇷 **R - Restart & Reset**

### **Restart Network**
```bash
# Full restart sequence
pkill -f "network_node.py"
sleep 2
python3 start_network.py
```

### **Reset Everything**
```bash
# Nuclear reset - kill everything and restart
pkill -f "network_node.py"
pkill -f "mining_client.py"
sleep 3
python3 start_network.py
```

---

## 🇸 **S - Send & Status**

### **Send Transactions**
```bash
# Basic transactions
python3 wallet_client.py send --wallet miner.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 50
python3 wallet_client.py send --wallet alice.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 25

# With custom fee
python3 wallet_client.py send --wallet miner.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 75 --fee 1.0

# To specific node
python3 wallet_client.py send --wallet alice.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 10 --node http://localhost:5002
```

### **Status Monitoring**
```bash
# Continuous status monitoring
watch -n 5 'curl -s http://localhost:5000/status | python3 -m json.tool'
```

---

## 🇹 **T - Testing & Troubleshooting**

### **Test Network Connectivity**
```bash
# Test all endpoints
echo "Testing Node 1:"; curl -s http://localhost:5000/status >/dev/null && echo "✅ OK" || echo "❌ Failed"
echo "Testing Node 2:"; curl -s http://localhost:5001/status >/dev/null && echo "✅ OK" || echo "❌ Failed"
echo "Testing Node 3:"; curl -s http://localhost:5002/status >/dev/null && echo "✅ OK" || echo "❌ Failed"
```

### **Troubleshooting**
```bash
# Check for port conflicts
lsof -i :5000 -i :5001 -i :5002

# Check system resources
top | grep -E "(Python|python3)"

# Check network connections
netstat -an | grep 500
```

---

## 🇺 **U - UTXO & Updates**

### **UTXO Operations**
```bash
# Get UTXOs for all addresses
echo "=== UTXO Status ==="
curl -s http://localhost:5000/utxos/17PVoFzAniw34i839GRDzA4gjm9neJRet8 | python3 -c "import sys,json; data=json.load(sys.stdin); print(f'Miner UTXOs: {len(data[\"utxos\"])}')"
curl -s http://localhost:5000/utxos/1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu | python3 -c "import sys,json; data=json.load(sys.stdin); print(f'Alice UTXOs: {len(data[\"utxos\"])}')"
curl -s http://localhost:5000/utxos/171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 | python3 -c "import sys,json; data=json.load(sys.stdin); print(f'Bob UTXOs: {len(data[\"utxos\"])}')"
```

---

## 🇻 **V - Verify & Validate**

### **Verify Network Synchronization**
```bash
# Check if all nodes have same blockchain length
echo "=== Synchronization Check ==="
for port in 5000 5001 5002; do
  echo -n "Node $port: "
  curl -s http://localhost:$port/status | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'{data[\"blockchain_length\"]} blocks, {data[\"peers\"]} peers')
except:
    print('Offline')
"
done
```

### **Validate Balances Across Nodes**
```bash
# Verify Alice's balance is consistent across all nodes
echo "=== Alice's Balance Verification ==="
for port in 5000 5001 5002; do
  echo -n "Node $port: "
  curl -s http://localhost:$port/balance/1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu | python3 -c "import sys,json; print(json.load(sys.stdin)['balance'])" 2>/dev/null || echo "Error"
done
```

---

## 🇼 **W - Wallet Operations**

### **Wallet Management**
```bash
# Create wallets
python3 wallet_client.py create --wallet user1.json
python3 wallet_client.py create --wallet user2.json

# Load and use wallets
python3 wallet_client.py info --wallet alice.json
python3 wallet_client.py balance --wallet alice.json
python3 wallet_client.py history --wallet alice.json

# Send between wallets
python3 wallet_client.py send --wallet alice.json --to BOB_ADDRESS --amount 10
```

---

## 🇽 **X - eXtended Operations**

### **Extended Monitoring Script**
```bash
# Create comprehensive monitoring script
cat > monitor.sh << 'EOF'
#!/bin/bash
while true; do
  clear
  echo "🌐 ChainCore Extended Monitor - $(date)"
  echo "=" * 60
  
  # Network Status
  echo "📡 Network Status:"
  for port in 5000 5001 5002; do
    status=$(curl -s http://localhost:$port/status 2>/dev/null)
    if [ $? -eq 0 ]; then
      blocks=$(echo $status | python3 -c "import sys,json; print(json.load(sys.stdin)['blockchain_length'])" 2>/dev/null)
      peers=$(echo $status | python3 -c "import sys,json; print(json.load(sys.stdin)['peers'])" 2>/dev/null)
      pending=$(echo $status | python3 -c "import sys,json; print(json.load(sys.stdin)['pending_transactions'])" 2>/dev/null)
      echo "  Node $port: ✅ $blocks blocks, $peers peers, $pending pending"
    else
      echo "  Node $port: ❌ Offline"
    fi
  done
  
  # Balance Status
  echo "💰 Balances:"
  miner_bal=$(curl -s http://localhost:5000/balance/17PVoFzAniw34i839GRDzA4gjm9neJRet8 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['balance'])" 2>/dev/null || echo "Error")
  alice_bal=$(curl -s http://localhost:5000/balance/1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['balance'])" 2>/dev/null || echo "Error")
  bob_bal=$(curl -s http://localhost:5000/balance/171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['balance'])" 2>/dev/null || echo "Error")
  
  echo "  Miner: $miner_bal CC"
  echo "  Alice: $alice_bal CC"
  echo "  Bob:   $bob_bal CC"
  
  sleep 10
done
EOF
chmod +x monitor.sh
./monitor.sh
```

---

## 🇾 **Y - Yield/Wait Operations**

### **Wait for Block Mining**
```bash
# Wait for next block to be mined
current_blocks=$(curl -s http://localhost:5000/status | python3 -c "import sys,json; print(json.load(sys.stdin)['blockchain_length'])")
echo "Current blocks: $current_blocks"
echo "Waiting for next block..."
while true; do
  new_blocks=$(curl -s http://localhost:5000/status | python3 -c "import sys,json; print(json.load(sys.stdin)['blockchain_length'])" 2>/dev/null)
  if [ "$new_blocks" -gt "$current_blocks" ]; then
    echo "✅ New block mined! Total blocks: $new_blocks"
    break
  fi
  sleep 5
done
```

---

## 🇿 **Z - Zero State & Cleanup**

### **Zero State Reset**
```bash
# Complete cleanup and reset to zero state
echo "🧹 Cleaning up ChainCore..."

# Kill all processes
pkill -f "network_node.py"
pkill -f "mining_client.py"
pkill -f "wallet_client.py"

# Wait for cleanup
sleep 3

# Remove any temporary files (optional)
# rm -f *.log

echo "✅ ChainCore reset to zero state"
echo "Ready to restart with: python3 start_network.py"
```

---

## 📋 **Complete Workflow Example**

### **Full A-Z Demonstration**
```bash
# A - Activate environment
source venv/bin/activate

# B - Begin network
python3 start_network.py

# C - Create mining (new terminal)
python3 mining_client.py --wallet 17PVoFzAniw34i839GRDzA4gjm9neJRet8 --node http://localhost:5000

# D - Demonstrate transactions (new terminal)
python3 wallet_client.py send --wallet miner.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 50

# E - Examine results
curl http://localhost:5000/balance/1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu

# F - Finish by stopping (Ctrl+C in network terminal)
```

---

## 🎯 **Pre-configured Addresses**
- **Miner**: `17PVoFzAniw34i839GRDzA4gjm9neJRet8`
- **Alice**: `1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu`
- **Bob**: `171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7`

## 🚀 **Network Endpoints**
- **Node 1**: `http://localhost:5000`
- **Node 2**: `http://localhost:5001`
- **Node 3**: `http://localhost:5002`

---

**All commands are ready to run! Start with Network commands, then Mining, then Transactions.**