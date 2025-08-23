# ChainCore Transaction Testing Commands

## 🧪 **TXN Testing - 20 Transaction Commands**

### **Prerequisites**

```bash
# Ensure network is running
python3 start_network.py

# Ensure mining is active
python3 mining_client.py --wallet 17PVoFzAniw34i839GRDzA4gjm9neJRet8 --node http://localhost:5000
```

---

## 💰 **Test Group 1: Basic Transfer Tests (1-5)**

### **Test 1: Miner to Alice - Small Amount**

```bash
python3 wallet_client.py send --wallet miner.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 10 --fee 0.1
```

### **Test 2: Miner to Bob - Medium Amount**

```bash
python3 wallet_client.py send --wallet miner.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 25 --fee 0.2
```

### **Test 3: Alice to Bob - Forward Chain**

```bash
python3 wallet_client.py send --wallet alice.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 5 --fee 0.1
```

### **Test 4: Bob to Alice - Reverse Chain**

```bash
python3 wallet_client.py send --wallet bob.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 8 --fee 0.1
```

### **Test 5: Miner to Alice - Large Amount**

```bash
python3 wallet_client.py send --wallet miner.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 75 --fee 0.5
```

---

## 🔄 **Test Group 2: Multi-Node Distribution (6-10)**

### **Test 6: Transaction via Node 2**

```bash
python3 wallet_client.py send --wallet alice.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 12 --fee 0.2 --node http://localhost:5001
```

### **Test 7: Transaction via Node 3**

```bash
python3 wallet_client.py send --wallet bob.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 15 --fee 0.3 --node http://localhost:5002
```

### **Test 8: Round-Robin Node Usage**

```bash
python3 wallet_client.py send --wallet miner.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 20 --fee 0.1 --node http://localhost:5000
```

### **Test 9: Cross-Node Validation**

```bash
python3 wallet_client.py send --wallet alice.json --to 17PVoFzAniw34i839GRDzA4gjm9neJRet8 --amount 30 --fee 0.4 --node http://localhost:5001
```

### **Test 10: Load Balance Test**

```bash
python3 wallet_client.py send --wallet bob.json --to 17PVoFzAniw34i839GRDzA4gjm9neJRet8 --amount 18 --fee 0.2 --node http://localhost:5002
```

---

## 💸 **Test Group 3: Fee Variation Tests (11-15)**

### **Test 11: Minimum Fee**

```bash
python3 wallet_client.py send --wallet miner.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 5 --fee 0.001
```

### **Test 12: Standard Fee**

```bash
python3 wallet_client.py send --wallet alice.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 7 --fee 0.1
```

### **Test 13: High Fee**

```bash
python3 wallet_client.py send --wallet bob.json --to 17PVoFzAniw34i839GRDzA4gjm9neJRet8 --amount 6 --fee 1.0
```

### **Test 14: Premium Fee**

```bash
python3 wallet_client.py send --wallet miner.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 40 --fee 2.5
```

### **Test 15: Micro Fee Test**

```bash
python3 wallet_client.py send --wallet alice.json --to 17PVoFzAniw34i839GRDzA4gjm9neJRet8 --amount 3 --fee 0.01
```

---

## 🎯 **Test Group 4: Precision & Edge Cases (16-20)**

### **Test 16: Decimal Precision Test**

```bash
python3 wallet_client.py send --wallet miner.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 12.5 --fee 0.25
```

### **Test 17: High Precision Amount**

```bash
python3 wallet_client.py send --wallet alice.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 0.1234 --fee 0.0567
```

### **Test 18: Maximum Precision**

```bash
python3 wallet_client.py send --wallet bob.json --to 17PVoFzAniw34i839GRDzA4gjm9neJRet8 --amount 1.12345678 --fee 0.87654321
```

### **Test 19: Large Round Number**

```bash
python3 wallet_client.py send --wallet miner.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 100 --fee 1.0
```

### **Test 20: Final Balance Sweep**

```bash
python3 wallet_client.py send --wallet alice.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 50 --fee 0.5
```

---

## 📊 **Verification Commands**

### **After Each Test Group, Run:**

```bash
# Check all balances
echo "=== Balance Check ==="
python3 wallet_client.py balance --wallet alice.json
python3 wallet_client.py balance --wallet bob.json
python3 wallet_client.py balance --wallet miner.json

# Check transaction pool
echo "=== Transaction Pool ==="
curl http://localhost:5000/transaction_pool

# Check blockchain status
echo "=== Network Status ==="
curl http://localhost:5000/status
curl http://localhost:5001/status
curl http://localhost:5002/status
```

### **Transaction History Check:**

```bash
# View transaction histories
python3 wallet_client.py history --wallet alice.json
python3 wallet_client.py history --wallet bob.json
python3 wallet_client.py history --wallet miner.json
```

---

## 🔄 **Automated Testing Script**

### **Run All 20 Tests Automatically:**

```bash
#!/bin/bash
# Save as run_txn_tests.sh

echo "🧪 Starting ChainCore Transaction Testing Suite"
echo "=============================================="

# Test Group 1: Basic Transfer Tests
echo "📋 Test Group 1: Basic Transfer Tests"
python3 wallet_client.py send --wallet miner.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 10 --fee 0.1
sleep 2
python3 wallet_client.py send --wallet miner.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 25 --fee 0.2
sleep 2
python3 wallet_client.py send --wallet alice.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 5 --fee 0.1
sleep 2
python3 wallet_client.py send --wallet bob.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 8 --fee 0.1
sleep 2
python3 wallet_client.py send --wallet miner.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 75 --fee 0.5
sleep 5

echo "📊 Group 1 Balance Check:"
python3 wallet_client.py balance --wallet alice.json
python3 wallet_client.py balance --wallet bob.json
python3 wallet_client.py balance --wallet miner.json
sleep 3

# Test Group 2: Multi-Node Distribution
echo "📋 Test Group 2: Multi-Node Distribution"
python3 wallet_client.py send --wallet alice.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 12 --fee 0.2 --node http://localhost:5001
sleep 2
python3 wallet_client.py send --wallet bob.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 15 --fee 0.3 --node http://localhost:5002
sleep 2
python3 wallet_client.py send --wallet miner.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 20 --fee 0.1 --node http://localhost:5000
sleep 2
python3 wallet_client.py send --wallet alice.json --to 17PVoFzAniw34i839GRDzA4gjm9neJRet8 --amount 30 --fee 0.4 --node http://localhost:5001
sleep 2
python3 wallet_client.py send --wallet bob.json --to 17PVoFzAniw34i839GRDzA4gjm9neJRet8 --amount 18 --fee 0.2 --node http://localhost:5002
sleep 5

echo "📊 Group 2 Balance Check:"
python3 wallet_client.py balance --wallet alice.json
python3 wallet_client.py balance --wallet bob.json
python3 wallet_client.py balance --wallet miner.json
sleep 3

# Test Group 3: Fee Variation Tests
echo "📋 Test Group 3: Fee Variation Tests"
python3 wallet_client.py send --wallet miner.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 5 --fee 0.001
sleep 2
python3 wallet_client.py send --wallet alice.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 7 --fee 0.1
sleep 2
python3 wallet_client.py send --wallet bob.json --to 17PVoFzAniw34i839GRDzA4gjm9neJRet8 --amount 6 --fee 1.0
sleep 2
python3 wallet_client.py send --wallet miner.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 40 --fee 2.5
sleep 2
python3 wallet_client.py send --wallet alice.json --to 17PVoFzAniw34i839GRDzA4gjm9neJRet8 --amount 3 --fee 0.01
sleep 5

echo "📊 Group 3 Balance Check:"
python3 wallet_client.py balance --wallet alice.json
python3 wallet_client.py balance --wallet bob.json
python3 wallet_client.py balance --wallet miner.json
sleep 3

# Test Group 4: Precision & Edge Cases
echo "📋 Test Group 4: Precision & Edge Cases"
python3 wallet_client.py send --wallet miner.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 12.5 --fee 0.25
sleep 2
python3 wallet_client.py send --wallet alice.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 0.1234 --fee 0.0567
sleep 2
python3 wallet_client.py send --wallet bob.json --to 17PVoFzAniw34i839GRDzA4gjm9neJRet8 --amount 1.12345678 --fee 0.87654321
sleep 2
python3 wallet_client.py send --wallet miner.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 100 --fee 1.0
sleep 2
python3 wallet_client.py send --wallet alice.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 50 --fee 0.5
sleep 5

echo "📊 Final Balance Check:"
python3 wallet_client.py balance --wallet alice.json
python3 wallet_client.py balance --wallet bob.json
python3 wallet_client.py balance --wallet miner.json

echo "🎉 Transaction Testing Suite Complete!"
```

---

## 📈 **Expected Results**

### **Success Indicators:**

- ✅ All transactions show "Transaction sent successfully!"
- ✅ Balances update correctly after each test group
- ✅ Transaction pool empties as blocks are mined
- ✅ All nodes maintain synchronized blockchain state

### **Test Metrics:**

- **Total Transactions**: 20
- **Total Amount Transferred**: ~500+ CC
- **Total Fees Paid**: ~15+ CC
- **Node Distribution**: Tests across all 3 nodes
- **Fee Range**: 0.001 to 2.5 CC
- **Amount Range**: 0.1234 to 100 CC

### **Monitoring Commands:**

```bash
# Monitor during testing
watch -n 5 'echo "=== Live Status ==="; curl -s http://localhost:5000/status | python3 -c "import sys,json; data=json.load(sys.stdin); print(f\"Blocks: {data[\"blockchain_length\"]}, Pending: {data[\"pending_transactions\"]}\")"; echo "=== Live Balances ==="; curl -s http://localhost:5000/balance/17PVoFzAniw34i839GRDzA4gjm9neJRet8 | python3 -c "import sys,json; print(f\"Miner: {json.load(sys.stdin)[\"balance\"]} CC\")"; curl -s http://localhost:5000/balance/1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu | python3 -c "import sys,json; print(f\"Alice: {json.load(sys.stdin)[\"balance\"]} CC\")"; curl -s http://localhost:5000/balance/171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 | python3 -c "import sys,json; print(f\"Bob: {json.load(sys.stdin)[\"balance\"]} CC\")"'
```

---

## 🎯 **Manual Testing Tips**

1. **Wait between test groups** for blocks to be mined
2. **Check balances** after each group to verify correctness
3. **Monitor transaction pool** to see pending transactions
4. **Use different nodes** to test network synchronization
5. **Vary fees** to test transaction prioritization
6. **Test edge cases** with decimal precision

**Start mining before running tests to ensure transactions get confirmed!**

python3 wallet_client.py send --wallet miner.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 25.0 --fee 0.5
sleep 1
python3 wallet_client.py send --wallet miner.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 30.0 --fee 0.75
sleep 1
python3 wallet_client.py send --wallet miner.json --to 1GukayKD1hRAXnQaJYKVwQcwCvVzsUbcJj --amount 15.0 --fee 0.25
sleep 1
python3 wallet_client.py send --wallet miner.json --to 18NDhHYAa3bx3jAZkc7HZf3vKr1JrwVXG3 --amount 20.0 --fee 0.3
sleep 1
python3 wallet_client.py send --wallet miner.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 5.5 --fee 0.1
sleep 2
python3 wallet_client.py send --wallet miner.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 8.25 --fee 0.15
sleep 1
python3 wallet_client.py send --wallet miner.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 2.1 --fee 0.05
sleep 1
python3 wallet_client.py send --wallet miner.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 3.75 --fee 0.08
sleep 1
python3 wallet_client.py send --wallet miner.json --to 1GukayKD1hRAXnQaJYKVwQcwCvVzsUbcJj --amount 1.0 --fee 0.02
sleep 1
python3 wallet_client.py send --wallet miner.json --to 18NDhHYAa3bx3jAZkc7HZf3vKr1JrwVXG3 --amount 4.5 --fee 0.12
sleep 2
python3 wallet_client.py send --wallet miner.json --to 17PVoFzAniw34i839GRDzA4gjm9neJRet8 --amount 7.25 --fee 0.18
sleep 1
python3 wallet_client.py send --wallet miner.json --to 17PVoFzAniw34i839GRDzA4gjm9neJRet8 --amount 6.8 --fee 0.2
sleep 1
python3 wallet_client.py send --wallet alice.json --to 17PVoFzAniw34i839GRDzA4gjm9neJRet8 --amount 12.0 --fee 0.4
sleep 1
python3 wallet_client.py send --wallet bob.json --to 1GukayKD1hRAXnQaJYKVwQcwCvVzsUbcJj --amount 18.5 --fee 0.6
sleep 1
python3 wallet_client.py send --wallet miner.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 9.99 --fee 0.01
sleep 2
python3 wallet_client.py send --wallet miner1.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 5.25 --fee 0.25
sleep 1
python3 wallet_client.py send --wallet miner2.json --to 1A2CJakwh4n6F7D9Ci8CKmHhRcas7gtFfu --amount 3.14159 --fee 0.07
sleep 1
python3 wallet_client.py send --wallet alice.json --to 171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7 --amount 15.75 --fee 0.35
sleep 1
python3 wallet_client.py send --wallet bob.json --to 18NDhHYAa3bx3jAZkc7HZf3vKr1JrwVXG3 --amount 2.0 --fee 1.0
sleep 1
python3 wallet_client.py send --wallet miner2.json --to 1GukayKD1hRAXnQaJYKVwQcwCvVzsUbcJj --amount 10.5 --fee 0.5
