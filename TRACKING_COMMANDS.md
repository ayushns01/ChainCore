# 📊 ChainCore Blockchain Tracking Commands Reference

## 🚀 Quick Commands for Testing

### **Start Blockchain & Mining:**
```bash
# Clean start
pkill -f network_node.py && pkill -f mining_client.py

# Start node
python3 network_node.py --node-id core0 --api-port 5000 --p2p-port 8000 &

# Start mining
python3 mining_client.py --wallet test_miner --node http://localhost:5000 &
```

### **Real-Time Monitoring:**
```bash
# Live blockchain monitor (shows new blocks as they're mined)
python3 blockchain_monitor.py monitor

# Quick block summary with miners
python3 quick_blockchain_check.py summary

# Hash chain integrity check
python3 quick_blockchain_check.py hashchain
```

### **Generate & Save Complete Analysis:**
```bash
# Full analysis saved to JSON file
python3 blockchain_tracker_with_json.py analyze

# Custom filename
python3 blockchain_tracker_with_json.py analyze http://localhost:5000 my_blockchain_report.json

# Quick analysis without saving
python3 blockchain_tracker_with_json.py quick
```

### **Compare Multiple Nodes:**
```bash
# Start second node
python3 network_node.py --node-id core1 --api-port 5001 --p2p-port 8001 &

# Compare synchronization
python3 quick_blockchain_check.py compare http://localhost:5000 http://localhost:5001

# Detailed comparison
python3 blockchain_monitor.py compare http://localhost:5000 http://localhost:5001
```

### **Manual Verification Commands:**
```bash
# Check which miner mined each block
curl -s http://localhost:5000/blockchain | python3 -c "
import sys, json
data = json.load(sys.stdin)
for block in data['chain']:
    try:
        miner = block['transactions'][0]['outputs'][0]['recipient_address']
        print(f'Block #{block[\"index\"]}: {miner[:30]}...')
    except:
        print(f'Block #{block[\"index\"]}: unknown miner')
"

# Verify previous_hash chain
curl -s http://localhost:5000/blockchain | python3 -c "
import sys, json
data = json.load(sys.stdin)
blocks = data['chain']
print('Hash Chain Verification:')
for i in range(1, len(blocks)):
    prev_correct = blocks[i]['previous_hash'] == blocks[i-1]['hash']
    status = '✅' if prev_correct else '❌'
    print(f'Block #{i}: {status} hash linkage')
"

# Check difficulty compliance
curl -s http://localhost:5000/blockchain | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('Difficulty Compliance:')
for block in data['chain']:
    required = '0' * block['target_difficulty']
    meets_difficulty = block['hash'].startswith(required)
    status = '✅' if meets_difficulty else '❌'
    print(f'Block #{block[\"index\"]}: {status} difficulty {block[\"target_difficulty\"]}')
"
```

## 📋 What Each Tool Shows You:

### **blockchain_monitor.py monitor**
- 🆕 NEW blocks as they're mined in real-time
- ⛏️ Which miner mined each block  
- 🔗 Hash chain integrity verification
- 📊 Mining distribution every 5 blocks
- 🎯 Difficulty validation

### **quick_blockchain_check.py summary**
- 📦 All blocks with miner attribution
- ⛏️ Mining distribution percentages
- ✅/❌ Hash and previous_hash validation
- 📊 Quick overview statistics

### **blockchain_tracker_with_json.py analyze**
- 💾 Complete analysis saved to JSON file
- 📈 Detailed statistics and metrics
- 🔍 Comprehensive validation report
- 📊 Mining performance analysis
- 🕐 Time-based analysis

## 🎯 Key Things to Track:

### **Block Mining Attribution:**
- [ ] Each block shows correct miner address
- [ ] Mining rewards distributed correctly
- [ ] No "unknown" miners (except genesis)
- [ ] Fair distribution across multiple miners

### **Hash Chain Integrity:**
- [ ] Block #0: `previous_hash = "0000...000"` (64 zeros)
- [ ] Block #N: `previous_hash = hash of Block #(N-1)`
- [ ] All hashes start with required zeros (difficulty)
- [ ] Sequential block indices: 0, 1, 2, 3...

### **Network Synchronization:**
- [ ] All nodes have same blockchain length
- [ ] All nodes have identical block hashes
- [ ] Blocks propagate across network quickly
- [ ] No fork conditions detected

### **Mining Performance:**
- [ ] Blocks mined within expected timeframe
- [ ] Multiple miners competing successfully
- [ ] Difficulty adjustments working correctly
- [ ] Transaction fees calculated properly

## 📊 Sample JSON Output Structure:

```json
{
  "analysis_metadata": {
    "timestamp": "2025-08-12T19:45:23",
    "node_url": "http://localhost:5000",
    "total_blocks_analyzed": 8
  },
  "blockchain_summary": {
    "total_blocks": 8,
    "genesis_block_hash": "00b5674c...",
    "latest_block_hash": "0a8f7d2e...",
    "difficulty_range": {"min": 1, "max": 1, "current": 1}
  },
  "detailed_blocks": [
    {
      "block_index": 0,
      "miner_address": "genesis",
      "mining_reward": 50.0,
      "validation": {
        "hash_meets_difficulty": true,
        "previous_hash_correct": true,
        "index_correct": true
      }
    }
  ],
  "mining_distribution": {
    "1CcUyVAiHT2dGP4ESxWqsDKFzazkQ2UW3n": {
      "blocks_mined": 3,
      "percentage": 37.5,
      "total_rewards": 150.5,
      "block_indices": [1, 3, 6]
    }
  },
  "hash_chain_integrity": {
    "total_blocks": 8,
    "valid_blocks": 8,
    "invalid_blocks": 0,
    "overall_status": "perfect"
  },
  "statistics": {
    "total_transactions": 11,
    "total_mining_rewards": 402.0,
    "average_block_time": 125.28,
    "unique_miners": 4,
    "most_productive_miner": "1CcUyVAiHT2dGP4ESxWqsDKFzazkQ2UW3n"
  }
}
```

## 🔧 Troubleshooting:

### **If tracking tools show errors:**
```bash
# Check if node is running
curl -s http://localhost:5000/status

# Restart tracking with different node
python3 blockchain_monitor.py monitor http://localhost:5001
```

### **If hash chain shows issues:**
```bash
# Check for node synchronization problems
python3 quick_blockchain_check.py compare http://localhost:5000 http://localhost:5001

# Restart nodes to resync
pkill -f network_node.py
python3 network_node.py --node-id core0 --api-port 5000 --p2p-port 8000
```

---

**💡 Tip**: Use `blockchain_tracker_with_json.py analyze` to generate comprehensive reports for blockchain auditing and performance analysis!