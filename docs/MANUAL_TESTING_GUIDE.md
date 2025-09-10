# 🧪 ChainCore Blockchain Manual Testing Guide

Complete step-by-step testing protocol to verify all blockchain functionality.

## 📋 Pre-Test Setup

### 1. Environment Preparation
```bash
cd /Users/ayush/Desktop/ChainCore
source venv/bin/activate

# Clean slate - kill any running processes
pkill -f network_node.py
pkill -f mining_client.py
sleep 2

# Verify configuration
python3 tests/test_difficulty_config.py
```

**✅ Expected**: All 5/5 tests pass, difficulty = 1

---

## 🌐 Phase 1: Single Node Testing

### Step 1.1: Start First Node
```bash
# Terminal 1:
python3 src/nodes/network_node.py --node-id core0 --api-port 5000 --p2p-port 8000
```

**Track These Outputs:**
- [ ] "Thread-safe network node initialized: core0"
- [ ] "Genesis block created and UTXO set initialized" 
- [ ] "Starting API server on port 5000"
- [ ] No error messages

### Step 1.2: Test Basic API
```bash
# Terminal 2:
curl -s http://localhost:5000/status | python3 -m json.tool
```

**✅ Expected Response:**
```json
{
  "api_calls": 1,
  "blockchain_length": 1,
  "node_id": "core0",
  "peers": 0,
  "pending_transactions": 0,
  "target_difficulty": 1,
  "thread_safe": true,
  "uptime": [some number]
}
```

**Track These Values:**
- [ ] `blockchain_length: 1` (genesis block)
- [ ] `target_difficulty: 1` (our config)
- [ ] `thread_safe: true`
- [ ] `peers: 0` (no other nodes yet)

### Step 1.3: Test Blockchain Data
```bash
curl -s http://localhost:5000/blockchain | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Blockchain length: {data[\"length\"]}')
print(f'Genesis block hash: {data[\"chain\"][0][\"hash\"][:16]}...')
print(f'Genesis difficulty: {data[\"chain\"][0][\"target_difficulty\"]}')
print(f'Genesis transactions: {len(data[\"chain\"][0][\"transactions\"])}')
"
```

**✅ Expected Output:**
```
Blockchain length: 1
Genesis block hash: [16 hex chars]...
Genesis difficulty: 1
Genesis transactions: 1
```

**Track These Values:**
- [ ] Length exactly 1
- [ ] Difficulty matches config (1)
- [ ] Genesis block has 1 coinbase transaction

### Step 1.4: Test Mining API
```bash
curl -s -X POST http://localhost:5000/mine_block \
  -H "Content-Type: application/json" \
  -d '{"miner_address": "test_miner"}' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Status: {data[\"status\"]}')
print(f'Template difficulty: {data[\"target_difficulty\"]}')
print(f'Block index: {data[\"block_template\"][\"index\"]}')
print(f'Previous hash: {data[\"block_template\"][\"previous_hash\"][:16]}...')
"
```

**✅ Expected Output:**
```
Status: template_created
Template difficulty: 1
Block index: 1
Previous hash: [16 hex chars]...
```

**Track These Values:**
- [ ] Status is "template_created"
- [ ] Difficulty matches config (1)
- [ ] Block index is 1 (next block)
- [ ] Previous hash exists

---

## ⛏️ Phase 2: Mining Testing

### Step 2.1: Start Mining Client
```bash
# Terminal 3:
python3 src/clients/mining_client.py --wallet test_miner_address --node http://localhost:5000
```

**Track These Outputs:**
- [ ] "🎯 Mining for address: test_miner_address"
- [ ] "🔗 Connected to node: http://localhost:5000"
- [ ] "Target difficulty: 1 leading zeros"
- [ ] NO "target_difficulty" errors

### Step 2.2: Monitor Mining Progress
```bash
# Terminal 4 (watch blockchain growth):
watch -n 2 'curl -s http://localhost:5000/status | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"📊 Block Length: {data[\"blockchain_length\"]} | Difficulty: {data[\"target_difficulty\"]} | Uptime: {data[\"uptime\"]:.0f}s\")
"'
```

**Track These Changes:**
- [ ] blockchain_length increases: 1 → 2 → 3 → 4...
- [ ] Mining terminal shows: "✅ Block X mined successfully!"
- [ ] Blocks mine every 1-10 seconds (difficulty=1)

### Step 2.3: Verify Mined Blocks & Mining Attribution
```bash
# Quick summary with miner tracking:
python3 src/tools/quick_blockchain_check.py summary

# OR detailed real-time monitoring:
python3 src/monitoring/blockchain_monitor.py monitor

# OR manual verification:
curl -s http://localhost:5000/blockchain | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Total blocks: {len(data[\"chain\"])}')
for i, block in enumerate(data['chain']):
    try:
        miner = block['transactions'][0]['outputs'][0]['recipient_address'][:20] + '...'
    except:
        miner = 'unknown'
    print(f'Block {i}: miner={miner}, difficulty={block[\"target_difficulty\"]}, hash={block[\"hash\"][:16]}...')
"
```

**✅ Expected Output:**
```
Total blocks: 4
Block 0: difficulty=1, txs=1, hash=[genesis hash]...
Block 1: difficulty=1, txs=1, hash=[block1 hash]...
Block 2: difficulty=1, txs=1, hash=[block2 hash]...
Block 3: difficulty=1, txs=1, hash=[block3 hash]...
```

**Track These Values:**
- [ ] Block count increases
- [ ] All blocks have difficulty=1
- [ ] Each block has 1 transaction (coinbase)
- [ ] Block hashes start with "0" (difficulty=1)

---

## 👥 Phase 3: Multi-Node Network Testing

### Step 3.1: Start Second Node
```bash
# Terminal 5:
python3 src/nodes/network_node.py --node-id core1 --api-port 5001 --p2p-port 8001
```

**Track These Outputs:**
- [ ] Node starts successfully
- [ ] "Discovered X peers" (should find core0)
- [ ] No connection errors

### Step 3.2: Check Peer Discovery
```bash
# Check core0 peers:
curl -s http://localhost:5000/peers | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Core0 active peers: {data[\"peer_count\"]}')
print(f'Peer list: {data[\"active_peers\"]}')
"

# Check core1 peers:
curl -s http://localhost:5001/peers | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Core1 active peers: {data[\"peer_count\"]}')
print(f'Peer list: {data[\"active_peers\"]}')
"
```

**✅ Expected Output:**
```
Core0 active peers: 1
Peer list: ['http://localhost:5001']
Core1 active peers: 1  
Peer list: ['http://localhost:5000']
```

**Track These Values:**
- [ ] Both nodes show 1 peer
- [ ] Peer URLs are correct
- [ ] No connection failures

### Step 3.3: Check Blockchain Sync & Hash Chain Integrity
```bash
# Compare blockchain lengths:
echo "Core0 length: $(curl -s http://localhost:5000/status | python3 -c 'import sys,json; print(json.load(sys.stdin)[\"blockchain_length\"])')"
echo "Core1 length: $(curl -s http://localhost:5001/status | python3 -c 'import sys,json; print(json.load(sys.stdin)[\"blockchain_length\"])')"

# Verify hash chain integrity:
python3 src/tools/quick_blockchain_check.py hashchain http://localhost:5000
python3 src/tools/quick_blockchain_check.py hashchain http://localhost:5001

# Compare nodes for synchronization:
python3 src/tools/quick_blockchain_check.py compare http://localhost:5000 http://localhost:5001
```

**✅ Expected Output:**
```
Core0 length: 5
Core1 length: 5
```

**Track These Values:**
- [ ] Both nodes have same blockchain length
- [ ] Lengths match the mining progress

### Step 3.4: Start Mining on Second Node
```bash
# Terminal 6:
python3 src/clients/mining_client.py --wallet second_miner_address --node http://localhost:5001
```

**Track Competitive Mining:**
- [ ] Both miners compete for blocks
- [ ] Blocks come from different miners alternately
- [ ] No mining conflicts or errors

---

## 💳 Phase 4: Wallet & Transaction Testing

### Step 4.1: Create Test Wallets
```bash
# Create wallet files:
python3 src/clients/wallet_client.py create --wallet alice.json
python3 src/clients/wallet_client.py create --wallet bob.json

# Check wallet info:
python3 src/clients/wallet_client.py info --wallet alice.json
python3 src/clients/wallet_client.py info --wallet bob.json
```

**Track Wallet Creation:**
- [ ] Wallets created successfully
- [ ] Each wallet has unique address
- [ ] Private/public keys generated

### Step 4.2: Check Initial Balances
```bash
ALICE_ADDR=$(python3 -c "import json; print(json.load(open('src/wallets/alice.json'))['address'])")
BOB_ADDR=$(python3 -c "import json; print(json.load(open('src/wallets/bob.json'))['address'])")

echo "Alice address: $ALICE_ADDR"
echo "Bob address: $BOB_ADDR"

# Check balances:
python3 src/clients/wallet_client.py balance --wallet alice.json --node http://localhost:5000
python3 src/clients/wallet_client.py balance --wallet bob.json --node http://localhost:5000
```

**✅ Expected Output:**
```
Alice address: [bitcoin address]
Bob address: [bitcoin address]
Alice balance: 0.0
Bob balance: 0.0
```

**Track Initial State:**
- [ ] Valid Bitcoin-style addresses
- [ ] Both balances are 0.0 (no coins yet)

### Step 4.3: Mine to Alice's Address
```bash
# Stop current miners (Ctrl+C in their terminals)
# Start mining to Alice:
python3 src/clients/mining_client.py --wallet $ALICE_ADDR --node http://localhost:5000
```

**Track Mining Rewards:**
- [ ] Mining continues successfully
- [ ] Alice should start receiving rewards

### Step 4.4: Check Alice's Growing Balance
```bash
# Check balance after 3-4 blocks:
python3 src/clients/wallet_client.py balance --wallet alice.json --node http://localhost:5000
```

**✅ Expected Output:**
```
Address: [Alice's address]
Balance: 150.0  # (3 blocks × 50.0 reward)
```

**Track Balance Growth:**
- [ ] Alice's balance increases by 50.0 per block
- [ ] Bob's balance remains 0.0

### Step 4.5: Test Transaction Creation
```bash
# Send 25.0 from Alice to Bob:
python3 src/clients/wallet_client.py send \
  --wallet alice.json \
  --node http://localhost:5000 \
  --to $BOB_ADDR \
  --amount 25.0 \
  --fee 1.0
```

**Track Transaction:**
- [ ] Transaction created successfully
- [ ] No "insufficient funds" errors
- [ ] Transaction added to mempool

### Step 4.6: Check Transaction Pool
```bash
curl -s http://localhost:5000/transaction_pool | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Pending transactions: {data[\"count\"]}')
if data['count'] > 0:
    tx = data['transactions'][0]
    print(f'Transaction ID: {tx[\"tx_id\"][:16]}...')
    print(f'Inputs: {len(tx[\"inputs\"])}, Outputs: {len(tx[\"outputs\"])}')
"
```

**✅ Expected Output:**
```
Pending transactions: 1
Transaction ID: [16 hex chars]...
Inputs: 1, Outputs: 2
```

**Track Transaction Pool:**
- [ ] 1 pending transaction
- [ ] Transaction has valid structure
- [ ] 1 input (Alice's UTXO), 2 outputs (Bob + change)

### Step 4.7: Wait for Transaction Mining
```bash
# Continue mining - transaction should be included in next block
# Watch for balance changes:
watch -n 3 '
echo "Alice: $(python3 src/clients/wallet_client.py balance --wallet alice.json --node http://localhost:5000 | grep Balance)"
echo "Bob:   $(python3 src/clients/wallet_client.py balance --wallet bob.json --node http://localhost:5000 | grep Balance)"
echo "Pool:  $(curl -s http://localhost:5000/transaction_pool | python3 -c \"import sys,json; print(f\"Pending: {json.load(sys.stdin)[\\\"count\\\"]}\")\")
'
```

**Track Transaction Confirmation:**
- [ ] Transaction pool count drops to 0
- [ ] Alice balance decreases by ~26.0 (25 + 1 fee)
- [ ] Bob balance increases to 25.0
- [ ] Alice continues getting mining rewards

---

## 📊 Phase 5: Advanced Network Testing

### Step 5.1: Add Third Node
```bash
# Terminal 7:
python3 src/nodes/network_node.py --node-id core2 --api-port 5002 --p2p-port 8002
```

**Track 3-Node Network:**
- [ ] Core2 discovers both existing nodes
- [ ] All nodes show 2 peers each
- [ ] Blockchain syncs across all 3 nodes

### Step 5.2: Test Network-Wide Sync
```bash
# Force sync test:
curl -X POST http://localhost:5002/sync_now

# Check all nodes have same length:
for port in 5000 5001 5002; do
  echo "Node $port: $(curl -s http://localhost:$port/status | python3 -c 'import sys,json; print(f\"Length: {json.load(sys.stdin)[\"blockchain_length\"]}\")')"
done
```

**✅ Expected Output:**
```
Node 5000: Length: 8
Node 5001: Length: 8  
Node 5002: Length: 8
```

**Track Network Sync:**
- [ ] All nodes report same blockchain length
- [ ] Sync completes without errors

### Step 5.3: Test Load Distribution
```bash
# Start miners on different nodes:
python3 src/clients/mining_client.py --wallet miner1_addr --node http://localhost:5000 &
python3 src/clients/mining_client.py --wallet miner2_addr --node http://localhost:5001 &  
python3 src/clients/mining_client.py --wallet miner3_addr --node http://localhost:5002 &
```

**Track Distributed Mining:**
- [ ] Multiple miners compete simultaneously
- [ ] Blocks mined by different miners
- [ ] All nodes accept blocks from any miner

---

## 🔍 Phase 6: Thread Safety & Performance Testing

### Step 6.1: Check Thread Safety Statistics
```bash
curl -s http://localhost:5000/stats | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('🔒 Thread Safety Stats:')
print(f'  API Calls: {data[\"node_stats\"][\"api_calls\"]}')
print(f'  Uptime: {data[\"node_stats\"][\"uptime\"]:.1f}s')
print('  Lock Statistics:')
total_contentions = 0
for lock, stats in data['lock_stats'].items():
    contentions = stats['contentions']
    acquisitions = stats['acquisitions']
    total_contentions += contentions
    print(f'    {lock}: {acquisitions} acq, {contentions} cont')
print(f'  Total Contentions: {total_contentions}')
"
```

**✅ Expected Output:**
```
🔒 Thread Safety Stats:
  API Calls: 45
  Uptime: 120.5s
  Lock Statistics:
    blockchain_chain: 25 acq, 0 cont
    transaction_pool: 15 acq, 0 cont
    utxo_set: 30 acq, 0 cont
    [... other locks ...]
  Total Contentions: 0
```

**Track Thread Safety:**
- [ ] Total contentions = 0 (perfect thread safety)
- [ ] Multiple lock acquisitions (system is active)
- [ ] No deadlock warnings

### Step 6.2: Stress Test API Calls
```bash
# Rapid API calls to test concurrency:
for i in {1..20}; do
  curl -s http://localhost:5000/status &
  curl -s http://localhost:5001/status &  
  curl -s http://localhost:5002/status &
done
wait

# Check stats again:
curl -s http://localhost:5000/stats | python3 -c "
import sys, json
data = json.load(sys.stdin)
total_contentions = sum(stats['contentions'] for stats in data['lock_stats'].values())
print(f'Total contentions after stress test: {total_contentions}')
"
```

**Track Stress Test:**
- [ ] All API calls complete successfully
- [ ] Contentions remain 0 after stress test
- [ ] No deadlocks or hangs

---

## 📋 Test Results Checklist

### ✅ Basic Functionality
- [ ] Nodes start without errors
- [ ] Genesis block created correctly  
- [ ] API endpoints respond properly
- [ ] Configuration system works (difficulty=1)

### ✅ Mining System
- [ ] Mining clients connect successfully
- [ ] Blocks mined with correct difficulty
- [ ] Mining rewards distributed properly
- [ ] Competitive mining works

### ✅ Network Operations  
- [ ] Peer discovery works automatically
- [ ] Blockchain syncs across nodes
- [ ] Multiple nodes operate simultaneously
- [ ] Network resilient to node additions

### ✅ Transaction System
- [ ] Wallets created and managed correctly
- [ ] Balances tracked accurately  
- [ ] Transactions created and broadcast
- [ ] Transaction pool management works
- [ ] UTXO system functions properly

### ✅ Thread Safety
- [ ] Zero lock contentions under normal load
- [ ] Zero lock contentions under stress
- [ ] No deadlocks or race conditions
- [ ] Concurrent operations work flawlessly

### ✅ Performance
- [ ] Blocks mine in expected timeframe (1-10s for difficulty=1)
- [ ] API responses are fast (<100ms)
- [ ] Memory usage stable over time
- [ ] No resource leaks detected

---

## 🎯 Success Criteria

Your blockchain is **FULLY FUNCTIONAL** if:

1. **All phases complete without errors**
2. **Blockchain length increases consistently**  
3. **Multiple nodes stay synchronized**
4. **Transactions process correctly**
5. **Zero thread contentions throughout testing**
6. **Mining works competitively across nodes**

## 🚨 Troubleshooting

If any test fails:

1. **Check configuration**: `python3 tests/test_difficulty_config.py`
2. **Verify logs**: Look for ERROR messages in node terminals  
3. **Check ports**: `lsof -i :5000` (ensure no conflicts)
4. **Restart clean**: Kill all processes and restart from Step 1.1

---

## 🔍 Blockchain Tracking & Verification Commands

### Real-Time Monitoring:
```bash
# Live block mining monitor with miner attribution:
python3 src/monitoring/blockchain_monitor.py monitor

# Monitor specific node with 2-second updates:
python3 src/monitoring/blockchain_monitor.py monitor http://localhost:5001 2
```

### Quick Checks:
```bash
# Block summary with mining distribution:
python3 src/tools/quick_blockchain_check.py summary

# Hash chain integrity verification:
python3 src/tools/quick_blockchain_check.py hashchain

# Compare two nodes for synchronization:
python3 src/tools/quick_blockchain_check.py compare http://localhost:5000 http://localhost:5001
```

### Full Analysis:
```bash
# Complete blockchain analysis:
python3 src/monitoring/blockchain_monitor.py analyze

# Detailed comparison of two nodes:
python3 src/monitoring/blockchain_monitor.py compare http://localhost:5000 http://localhost:5001
```

### Manual Hash Chain Verification:
```bash
# Verify previous_hash links manually:
curl -s http://localhost:5000/blockchain | python3 -c "
import sys, json
data = json.load(sys.stdin)
blocks = data['chain']
print('Hash Chain Verification:')
for i in range(1, len(blocks)):
    prev_hash_correct = blocks[i]['previous_hash'] == blocks[i-1]['hash']
    status = '✅' if prev_hash_correct else '❌'
    print(f'Block #{i}: {status} prev_hash linkage')
"
```

### Track Mining Attribution:
```bash
# Show which miner mined each block:
curl -s http://localhost:5000/blockchain | python3 -c "
import sys, json
data = json.load(sys.stdin)
blocks = data['chain']
print('Mining Attribution:')
for block in blocks:
    try:
        miner = block['transactions'][0]['outputs'][0]['recipient_address']
        print(f'Block #{block[\"index\"]}: {miner[:25]}...')
    except:
        print(f'Block #{block[\"index\"]}: unknown miner')
"
```

---

**🏆 Completing this entire guide proves your blockchain is production-ready!**