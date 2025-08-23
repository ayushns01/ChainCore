# ChainCore Configuration Guide

## 🎛️ Changing Blockchain Difficulty

### Single Configuration Point
All blockchain parameters are now centralized in `/src/config.py`. To change the mining difficulty:

**Step 1:** Edit the configuration file
```bash
nano /Users/ayush/Desktop/ChainCore/src/config.py
```

**Step 2:** Change the difficulty value
```python
# Change this single line to adjust mining difficulty across entire system
BLOCKCHAIN_DIFFICULTY = 1  # Easy:   "0" prefix
BLOCKCHAIN_DIFFICULTY = 2  # Medium: "00" prefix  
BLOCKCHAIN_DIFFICULTY = 3  # Hard:   "000" prefix
BLOCKCHAIN_DIFFICULTY = 4  # Harder: "0000" prefix
BLOCKCHAIN_DIFFICULTY = 5  # Hardest:"00000" prefix (original)
```

**Step 3:** Restart all nodes and miners
```bash
# Stop everything
pkill -f network_node.py
pkill -f mining_client.py

# Start nodes (they'll automatically use new difficulty)
python3 network_node.py --node-id core0 --api-port 5000 --p2p-port 8000 &
python3 network_node.py --node-id core1 --api-port 5001 --p2p-port 8001 &

# Start miners (they'll automatically use new difficulty)
python3 mining_client.py --wallet YOUR_WALLET --node http://localhost:5000 &
```

## 🔧 Configuration Components Updated

### ✅ Automatically Updated Components:
- **Network Nodes**: All API endpoints use centralized difficulty
- **Blockchain Engine**: Genesis and new blocks use centralized difficulty  
- **Mining System**: Work coordination uses centralized difficulty
- **Block Templates**: Created with centralized difficulty
- **Block Validation**: Validates against centralized difficulty

### 📋 Configuration File Structure:

```python
# /src/config.py
BLOCKCHAIN_DIFFICULTY = 2      # Main setting - change this
BLOCK_REWARD = 50.0           # Mining reward
DEFAULT_TRANSACTION_FEE = 0.01 # Transaction fees
MINING_TIMEOUT = 60           # Mining timeout
MAX_BLOCK_SIZE = 1000         # Max transactions per block
```

## 📊 Difficulty Impact

| Difficulty | Hash Prefix | Relative Effort | Laptop Mining Time |
|------------|-------------|-----------------|-------------------|
| 1          | "0"         | 1x (easiest)    | ~1 second         |
| 2          | "00"        | 16x             | ~10 seconds       |
| 3          | "000"       | 256x            | ~2 minutes        |
| 4          | "0000"      | 4,096x          | ~30 minutes       |
| 5          | "00000"     | 65,536x         | ~8 hours          |

## 🔍 Verification Commands

### Check Current Difficulty:
```bash
curl -s http://localhost:5000/status | python3 -c "import sys,json; print('Current difficulty:', json.load(sys.stdin)['target_difficulty'])"
```

### Test Mining API:
```bash
curl -s -X POST http://localhost:5000/mine_block -H "Content-Type: application/json" -d '{"miner_address":"test"}' | python3 -c "import sys,json; data=json.load(sys.stdin); print('API difficulty:', data.get('target_difficulty'))"
```

### Monitor Mining Progress:
```bash
# Watch blockchain length increase
watch 'curl -s http://localhost:5000/status | python3 -c "import sys,json; data=json.load(sys.stdin); print(f\"Length: {data[\"blockchain_length\"]}, Difficulty: {data[\"target_difficulty\"]}\")"'
```

## ⚠️ Important Notes

1. **Always restart nodes** after changing configuration
2. **Lower difficulty = faster mining** but less security
3. **Higher difficulty = slower mining** but more security  
4. **Difficulty 1-2** recommended for development/testing
5. **Difficulty 4-5** recommended for production networks

## 🚀 Quick Difficulty Settings

### Development (Fast Mining):
```python
BLOCKCHAIN_DIFFICULTY = 1  # Blocks every few seconds
```

### Testing (Moderate Mining):
```python
BLOCKCHAIN_DIFFICULTY = 2  # Blocks every 10-30 seconds  
```

### Production (Secure Mining):
```python
BLOCKCHAIN_DIFFICULTY = 4  # Blocks every 10-30 minutes
```

## 🔧 Troubleshooting

### Issue: Nodes still show old difficulty
**Solution**: Restart all nodes - they cache the configuration

### Issue: Mining not working
**Solution**: Check that mining client and node show same difficulty:
```bash
# Check node difficulty
curl -s http://localhost:5000/status | grep target_difficulty

# Check mining template difficulty  
curl -s -X POST http://localhost:5000/mine_block -d '{"miner_address":"test"}' | grep target_difficulty
```

### Issue: Blocks not being mined
**Solution**: Lower difficulty temporarily for testing:
```python
BLOCKCHAIN_DIFFICULTY = 1  # Very easy for debugging
```

---

**🎯 Remember**: One configuration file controls everything. Change `BLOCKCHAIN_DIFFICULTY` in `/src/config.py` and restart nodes!