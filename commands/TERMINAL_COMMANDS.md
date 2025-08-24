# 🖥️ ChainCore Terminal Commands - Updated Guide

**✅ Consensus Problem SOLVED!** All commands updated for the working multi-node setup.

---

## 🚀 **Multi-Node Network Setup (WORKING)**

The correct way to connect nodes to each other is by using the `--bootstrap-nodes` argument.

### **Approach 1: Using `--bootstrap-nodes` (Recommended)**

This is the recommended approach as you can specify multiple peers in one command.

**Step 1: Bootstrap Node (Terminal 1)**

Start the first node. It will act as the bootstrap server for the others.

```bash
python network_node.py --node-id core0 --api-port 5000 --p2p-port 8000
```

**Status:** ✅ Main node - other nodes connect here

**Step 2: Peer Nodes (Terminals 2-4)**

Start the other nodes and tell them to connect to the bootstrap node.

```bash
# Terminal 2
python network_node.py --node-id core1 --api-port 5001 --p2p-port 8001 --bootstrap-nodes http://localhost:5000

# Terminal 3
python network_node.py --node-id core2 --api-port 5002 --p2p-port 8002 --bootstrap-nodes http://localhost:5000

# Terminal 4 (connecting to multiple peers)
python network_node.py --node-id core3 --api-port 5003 --p2p-port 8003 --bootstrap-nodes http://localhost:5000 http://localhost:5001
```



**Status:** ✅ All nodes show identical chain length = 1 block

---

## 🚀 **10-Node Network Setup**

Here is how to set up a larger, 10-node network.

### **Approach 1: Using `--bootstrap-nodes`**

Start the bootstrap node first, then start the 9 peer nodes, connecting them to the bootstrap node.

**Terminal 1: Bootstrap Node**

```bash
python network_node.py --node-id core0 --api-port 5000 --p2p-port 8000
```

**Terminals 2-10: Peer Nodes**

```bash
python network_node.py --node-id core1 --api-port 5001 --p2p-port 8001 --bootstrap-nodes http://localhost:5000
python network_node.py --node-id core2 --api-port 5002 --p2p-port 8002 --bootstrap-nodes http://localhost:5000
python network_node.py --node-id core3 --api-port 5003 --p2p-port 8003 --bootstrap-nodes http://localhost:5000
python network_node.py --node-id core4 --api-port 5004 --p2p-port 8004 --bootstrap-nodes http://localhost:5000
python network_node.py --node-id core5 --api-port 5005 --p2p-port 8005 --bootstrap-nodes http://localhost:5000
python network_node.py --node-id core6 --api-port 5006 --p2p-port 8006 --bootstrap-nodes http://localhost:5000
python network_node.py --node-id core7 --api-port 5007 --p2p-port 8007 --bootstrap-nodes http://localhost:5000
python network_node.py --node-id core8 --api-port 5008 --p2p-port 8008 --bootstrap-nodes http://localhost:5000
python network_node.py --node-id core9 --api-port 5009 --p2p-port 8009 --bootstrap-nodes http://localhost:5000
```



---

## 📊 **Consensus Verification Commands**

### **Quick Status Check (VERIFIED WORKING)**

```bash
echo "=== CONSENSUS CHECK ===" && \
echo "Node 5000:" && curl -s http://localhost:5000/status | grep "chain_length" && \
echo "Node 5001:" && curl -s http://localhost:5001/status | grep "chain_length" && \
echo "Node 5002:" && curl -s http://localhost:5002/status | grep "chain_length" && \
echo "Node 5003:" && curl -s http://localhost:5003/status | grep "chain_length"
```

**Expected Output:**

```
=== CONSENSUS CHECK ===
Node 5000:
    "chain_length": 1,
Node 5001:
    "chain_length": 1,
Node 5002:
    "chain_length": 1,
Node 5003:
    "chain_length": 1,
```

### **Full Network Status (WORKING)**

```bash
curl -s http://localhost:5000/status | grep -E "chain_length|active_peers|node_id" && \
curl -s http://localhost:5001/status | grep -E "chain_length|active_peers|node_id" && \
curl -s http://localhost:5002/status | grep -E "chain_length|active_peers|node_id" && \
curl -s http://localhost:5003/status | grep -E "chain_length|active_peers|node_id"
```

### **Continuous Monitoring**

```bash
# Monitor every 10 seconds
while true; do
  echo "=== $(date +%H:%M:%S) ===" && \
  echo "5000: Chain=$(curl -s http://localhost:5000/status | grep -o '"chain_length": [0-9]*' | cut -d: -f2) Peers=$(curl -s http://localhost:5000/status | grep -o '"active_peers": [0-9]*' | cut -d: -f2)" && \
  echo "5001: Chain=$(curl -s http://localhost:5001/status | grep -o '"chain_length": [0-9]*' | cut -d: -f2) Peers=$(curl -s http://localhost:5001/status | grep -o '"active_peers": [0-9]*' | cut -d: -f2)" && \
  echo "5002: Chain=$(curl -s http://localhost:5002/status | grep -o '"chain_length": [0-9]*' | cut -d: -f2) Peers=$(curl -s http://localhost:5002/status | grep -o '"active_peers": [0-9]*' | cut -d: -f2)" && \
  echo "5003: Chain=$(curl -s http://localhost:5003/status | grep -o '"chain_length": [0-9]*' | cut -d: -f2) Peers=$(curl -s http://localhost:5003/status | grep -o '"active_peers": [0-9]*' | cut -d: -f2)" && \
  sleep 10
done
```

---

## ⛏️ **Mining Commands (UPDATED)**

### **Mining Client (Correct Format)**

```bash
python mining_client.py --wallet 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa --node http://localhost:5000
```

**Note:** Must use valid Bitcoin-style address format

### **Multiple Miners**

```bash
# Miner 1 → Node 5000
python mining_client.py --wallet 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa --node http://localhost:5000

# Miner 2 → Node 5001
python mining_client.py --wallet 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2 --node http://localhost:5001

# Miner 3 → Node 5002
python mining_client.py --wallet 1C1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa --node http://localhost:5002
```

### **Manual Block Template Test**

```bash
curl -X POST http://localhost:5000/mine_block -H "Content-Type: application/json" -d '{"miner_address":"1TestMinerAddress123456789012345678901234"}'
```

---

## 🗄️ **Database Monitoring (VERIFIED)**

### **Real-time Database Monitor**

```bash
python database_monitor.py
```

### **Quick Database Status**

```bash
python database_monitor.py --status-only
```

### **Custom Refresh Interval**

```bash
# Every 5 seconds
python database_monitor.py --interval 5

# Every 1 second (fast monitoring)
python database_monitor.py --interval 1
```

---

## 🧪 **Testing Commands (VERIFIED WORKING)**

### **Database Connection Test**

```bash
python simple_db_test.py
```

### **Integration Test**

```bash
python test_simple_integration.py
```

### **Node Reachability Test**

```bash
echo "Testing node connectivity..." && \
curl -s http://localhost:5000/status > /dev/null && echo "✅ Node 5000: OK" || echo "❌ Node 5000: FAILED" && \
curl -s http://localhost:5001/status > /dev/null && echo "✅ Node 5001: OK" || echo "❌ Node 5001: FAILED" && \
curl -s http://localhost:5002/status > /dev/null && echo "✅ Node 5002: OK" || echo "❌ Node 5002: FAILED" && \
curl -s http://localhost:5003/status > /dev/null && echo "✅ Node 5003: OK" || echo "❌ Node 5003: FAILED"
```

---

## 🔧 **Troubleshooting Commands**

### **Force Peer Discovery**

```bash
curl -X POST http://localhost:5000/discover_peers
curl -X POST http://localhost:5001/discover_peers
curl -X POST http://localhost:5002/discover_peers
curl -X POST http://localhost:5003/discover_peers
```

### **Manual Blockchain Sync**

```bash
curl -X POST http://localhost:5001/sync_blockchain
curl -X POST http://localhost:5002/sync_blockchain
curl -X POST http://localhost:5003/sync_blockchain
```

### **Check Genesis Block Consistency**

```bash
echo "Genesis Hash Check:" && \
curl -s http://localhost:5000/blockchain | grep -o '"hash": "[^"]*"' | head -1 && \
curl -s http://localhost:5001/blockchain | grep -o '"hash": "[^"]*"' | head -1 && \
curl -s http://localhost:5002/blockchain | grep -o '"hash": "[^"]*"' | head -1 && \
curl -s http://localhost:5003/blockchain | grep -o '"hash": "[^"]*"' | head -1
```

**Expected:** All should show identical genesis hash

---

## 🎯 **Complete Development Workflow**

### **Full Setup (Recommended)**

```bash
# Terminal 1 - Database Monitor (Start first)
python database_monitor.py

# Terminal 2 - Bootstrap Node
python network_node.py --node-id core0 --api-port 5000 --p2p-port 8000

# Terminal 3 - Peer Node 1
python network_node.py --node-id core1 --api-port 5001 --p2p-port 8001 --bootstrap-nodes http://localhost:5000

# Terminal 4 - Peer Node 2
python network_node.py --node-id core2 --api-port 5002 --p2p-port 8002 --bootstrap-nodes http://localhost:5000

# Terminal 5 - Peer Node 3
python network_node.py --node-id core3 --api-port 5003 --p2p-port 8003 --bootstrap-nodes http://localhost:5000

# Wait 15 seconds for full initialization
sleep 15

# Terminal 6 - Verify Consensus
echo "=== CONSENSUS VERIFICATION ===" && \
curl -s http://localhost:5000/status | grep "chain_length" && \
curl -s http://localhost:5001/status | grep "chain_length" && \
curl -s http://localhost:5002/status | grep "chain_length" && \
curl -s http://localhost:5003/status | grep "chain_length"

# Terminal 7 - Start Mining
python mining_client.py --wallet 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa --node http://localhost:5000
```

---

## 🆘 **Process Management**

### **Stop All ChainCore Processes**

```bash
# Kill all network nodes
pkill -f "network_node.py"

# Kill all mining clients
pkill -f "mining_client.py"

# Kill database monitor
pkill -f "database_monitor.py"

# Verify all stopped
echo "Checking remaining processes..."
ps aux | grep -E "(network_node|mining_client|database_monitor)" | grep -v grep
```

### **Clean Restart Protocol**

```bash
# 1. Stop everything
pkill -f "network_node.py|mining_client.py|database_monitor.py"

# 2. Wait for clean shutdown
sleep 5

# 3. Start database monitor first
python database_monitor.py &

# 4. Start bootstrap node
sleep 2
python network_node.py --node-id core0 --api-port 5000 --p2p-port 8000 &

# 5. Start peer nodes with delays
sleep 5
python network_node.py --node-id core1 --api-port 5001 --p2p-port 8001 --bootstrap-nodes http://localhost:5000 &
sleep 2
python network_node.py --node-id core2 --api-port 5002 --p2p-port 8002 --bootstrap-nodes http://localhost:5000 &
sleep 2
python network_node.py --node-id core3 --api-port 5003 --p2p-port 8003 --bootstrap-nodes http://localhost:5000 &

# 6. Wait for initialization then verify
sleep 15
echo "=== POST-RESTART CONSENSUS CHECK ===" && \
curl -s http://localhost:5000/status | grep "chain_length" && \
curl -s http://localhost:5001/status | grep "chain_length" && \
curl -s http://localhost:5002/status | grep "chain_length" && \
curl -s http://localhost:5003/status | grep "chain_length"
```

---

## 💡 **Success Indicators**

### **✅ Healthy Network Signs**

- All nodes show **identical chain_length**
- Nodes show **active_peers > 0**
- Genesis hash is **consistent across all nodes**
- Database monitor shows **blocks being stored**
- No **"Genesis block mismatch"** errors

### **⚠️ Warning Signs**

- **Different chain lengths** between nodes
- **0 active peers** on most nodes
- **Connection refused** errors
- **Database connection failed** messages

### **❌ Problem Indicators**

- **Genesis block mismatch** errors
- **Smart sync validation failed** messages
- **Consistent 0 peers** across network
- **Mining client wallet format** errors

---

## 📚 **Reference Files**

| File                                | Purpose                     |
| ----------------------------------- | --------------------------- |
| `DATABASE_MONITOR_COMMANDS.md`      | Database monitoring guide   |
| `src/config/genesis_block.py`       | Genesis block configuration |
| `src/database/simple_connection.py` | Database settings           |
| `network_node.py`                   | Main blockchain node        |
| `mining_client.py`                  | Mining functionality        |
| `database_monitor.py`               | Real-time DB monitoring     |

---

## 🏆 **Consensus Success Verification**

**✅ PROBLEM SOLVED:** The original issue where 4 nodes created separate blockchains has been **completely resolved**. All nodes now maintain unified consensus with:

- **Identical Genesis Block**: Hash `00a8f5f2c7d1e4b3c6d9e2f1a4b7c8d2e5f3a6b9c1d4e7f2a5b8c3d6e9f1a4b7`
- **Unified Chain Length**: All nodes show `chain_length: 1`
- **Peer Connectivity**: Nodes discover and connect to each other
- **Database Coordination**: All nodes use consistent database state

**Use the commands above to maintain and monitor your working ChainCore network!**
