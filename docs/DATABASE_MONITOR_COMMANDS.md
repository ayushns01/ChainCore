# 🗄️ ChainCore Database Monitor Commands

Complete guide for monitoring your ChainCore blockchain database in real-time.

---

## 📋 **Quick Reference**

| Command | Description | Duration |
|---------|-------------|----------|
| `python src/monitoring/database_monitor.py --status-only` | Show current database state | 5 seconds |
| `python src/monitoring/database_monitor.py` | Start real-time monitoring | Continuous |
| `python src/monitoring/database_monitor.py --interval 5` | Monitor with 5-second refresh | Continuous |

---

## 🚀 **Basic Commands**

### **Check Database Status**
```bash
python src/monitoring/database_monitor.py --status-only
```
**Output:**
```
🗄️ CURRENT DATABASE STATE
========================================
📁 Database: chaincore_blockchain
💾 Size: 45,234 bytes
⛓️  Blockchain: 15 blocks
📦 Latest Block: #14
   Hash: a1b2c3d4...89abcdef
   Miner: Node-5001
💰 Top Balances:
   1A1zP1eP5QGefi2D...: 750.00 CC
   1BvBMSEYstWetqTF...: 500.00 CC
```

### **Start Real-time Monitoring**
```bash
python src/monitoring/database_monitor.py
```
**Output:**
```
🚀 ChainCore Database Monitor Starting...
============================================================
✅ Connected to PostgreSQL database
📊 Initial blockchain length: 12
🔄 Monitoring every 2.0s (Press Ctrl+C to stop)
============================================================

[14:25:30] 📊 Chain: 12 blocks | Monitoring...
[14:25:35] 🎉 NEW BLOCK(S) DETECTED!
   📦 Block #12
      🏷️  Hash: a1b2c3d4...89abcdef
      ⛏️  Miner: Node-5001 (1A1zP1eP5QGefi2D...)
      💎 Difficulty: 4
      📝 Transactions: 1
      ⏰ Time: 14:25:34
         💰 Coinbase: +50.00 CC → 1A1zP1eP5QGefi2D...

📊 BLOCKCHAIN SUMMARY
   ⛓️  Total Blocks: 13
   ⛏️  Active Miners: 2
   💰 Total UTXOs: 25
   💵 Total Value: 650.00 CC
   ⏰ Monitor Runtime: 0h 2m 15s
   🏆 Top Miners:
      #1 Node-5001: 8 blocks
      #2 Node-5002: 5 blocks
```

---

## ⚙️ **Advanced Options**

### **Custom Refresh Interval**
```bash
# Monitor every 5 seconds (slower, less CPU usage)
python src/monitoring/database_monitor.py --interval 5

# Monitor every 0.5 seconds (faster, more CPU usage)
python src/monitoring/database_monitor.py --interval 0.5
```

### **Help Command**
```bash
python src/monitoring/database_monitor.py --help
```

---

## 🎯 **Usage Scenarios**

### **Scenario 1: Quick Health Check**
```bash
# Before starting mining
python src/monitoring/database_monitor.py --status-only
```
**Use when:** Verifying database is working before mining.

### **Scenario 2: Development/Testing**
```bash
# Watch blocks in real-time during development
python src/monitoring/database_monitor.py --interval 1
```
**Use when:** Testing mining, debugging blockchain issues.

### **Scenario 3: Production Monitoring**
```bash
# Longer intervals for production monitoring
python src/monitoring/database_monitor.py --interval 10
```
**Use when:** Production monitoring without high resource usage.

---

## 📊 **Understanding the Output**

### **Status Display Elements**

| Element | Meaning | Example |
|---------|---------|---------|
| `📁 Database` | PostgreSQL database name | `chaincore_blockchain` |
| `💾 Size` | Database file size | `45,234 bytes` |
| `⛓️ Blockchain` | Number of blocks stored | `15 blocks` |
| `📦 Latest Block` | Most recent block info | `#14` |
| `💰 Top Balances` | Richest addresses | `750.00 CC` |

### **Real-time Monitoring Elements**

| Element | Meaning | Example |
|---------|---------|---------|
| `🎉 NEW BLOCK(S) DETECTED!` | New block mined and stored | Block #12 |
| `🏷️ Hash` | Block hash (truncated) | `a1b2c3d4...89abcdef` |
| `⛏️ Miner` | Mining node and address | `Node-5001 (1A1z...)` |
| `💎 Difficulty` | Mining difficulty | `4` |
| `📝 Transactions` | Number of transactions | `1` |
| `💰 Coinbase` | Mining reward transaction | `+50.00 CC` |

---

## 🔧 **Troubleshooting**

### **Monitor Won't Start**
```bash
# Check database connection first
python tests/simple_db_test.py
```
**Solution:** Ensure PostgreSQL is running and credentials are correct.

### **No Blocks Appearing**
```bash
# Verify mining is active
python src/monitoring/database_monitor.py --status-only
```
**Solution:** Start mining client: `python src/clients/mining_client.py --wallet 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa --node http://localhost:5000`

### **Connection Errors**
```
❌ Database connection failed: connection refused
```
**Solution:** 
1. Start PostgreSQL: `net start postgresql-x64-16`
2. Verify credentials in `src/data/simple_connection.py`

---

## 🎮 **Multi-Terminal Setup**

### **Recommended Setup for Development**

**Terminal 1 - Database Monitor:**
```bash
python src/monitoring/database_monitor.py
```

**Terminal 2 - Network Node (Bootstrap/Main):**
```bash
python src/nodes/network_node.py --node-id core0 --api-port 5000 --p2p-port 8000
```

**Terminal 3 - Network Node (Peer):**
```bash
python src/nodes/network_node.py --node-id core1 --api-port 5001 --p2p-port 8001 --bootstrap-node http://localhost:5000
```

**Terminal 4 - Mining Client:**
```bash
python src/clients/mining_client.py --wallet 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa --node http://localhost:5000
```

**Terminal 5 - Additional Nodes (Optional):**
```bash
# Node 2
python src/nodes/network_node.py --node-id core2 --api-port 5002 --p2p-port 8002 --bootstrap-node http://localhost:5000

# Node 3
python src/nodes/network_node.py --node-id core3 --api-port 5003 --p2p-port 8003 --bootstrap-node http://localhost:5000
```

---

## 📈 **Monitoring Tips**

### **Performance Optimization**
- Use `--interval 5` or higher for production
- Use `--interval 1` for development/testing
- Press `Ctrl+C` to stop monitoring gracefully

### **Data Analysis**
- Monitor "Top Miners" to see mining distribution
- Watch "Total Value" to track economic activity
- Check "Active Miners" to see network participation

### **Debugging**
- Use `--status-only` to quickly check current state
- Compare blockchain length with network nodes
- Verify transactions are being processed correctly

---

## 🔗 **Related Commands**

| Command | Purpose |
|---------|---------|
| `python tests/simple_db_test.py` | Test database connectivity |
| `python tests/test_simple_integration.py` | Test full integration |
| `python src/nodes/network_node.py --help` | Network node options |
| `python src/clients/mining_client.py --help` | Mining client options |
| `curl -s http://localhost:5000/status \| grep chain_length` | Check node chain length |
| `curl -s http://localhost:5000/status \| grep active_peers` | Check node peer count |

---

## 💡 **Pro Tips**

1. **Always check status first:** Run `--status-only` before starting continuous monitoring
2. **Use appropriate intervals:** Faster intervals for testing, slower for production
3. **Monitor during development:** Keep monitor running while testing new features
4. **Watch for patterns:** Monitor mining distribution and transaction patterns
5. **Clean exit:** Always use `Ctrl+C` to stop monitoring cleanly

---

**📚 For more information, see:**
- `DATABASE_SETUP_GUIDE.md` - Initial database setup
- `MINING_GUIDE.md` - Mining configuration
- `NETWORK_GUIDE.md` - Network node setup