# ChainCore Usage Guide

## 🎯 Overview

ChainCore uses the **original blockchain architecture** with separate network nodes and mining clients, just like Bitcoin. This provides maximum flexibility and follows established blockchain patterns.

## 📜 **STANDARD WORKFLOW**

### **1. Start Network Nodes**
```bash
# Terminal 1 - Node 1
python src/nodes/network_node.py --node-id core1 --api-port 5001

# Terminal 2 - Node 2  
python src/nodes/network_node.py --node-id core2 --api-port 5002

# Terminal 3 - Node 3
python src/nodes/network_node.py --node-id core3 --api-port 5003
```

### **2. Create Wallets** 
```bash
# Create miner wallets
python src/clients/wallet_client.py create --wallet miner1.json
python src/clients/wallet_client.py create --wallet miner2.json  
python src/clients/wallet_client.py create --wallet miner3.json
```

### **3. Start Mining Clients**
```bash
# Terminal 4 - Miner 1
python src/clients/mining_client.py --wallet MINER1_ADDRESS --node http://localhost:5001

# Terminal 5 - Miner 2
python src/clients/mining_client.py --wallet MINER2_ADDRESS --node http://localhost:5002

# Terminal 6 - Miner 3  
python src/clients/mining_client.py --wallet MINER3_ADDRESS --node http://localhost:5003
```

### **4. Send Transactions**
```bash
# Send transactions using wallet client
python src/clients/wallet_client.py send --wallet miner1.json --to RECIPIENT_ADDRESS --amount 25
```


## 🔧 **All Commands**

### **Network Node Commands**
```bash
python src/nodes/network_node.py --help
python src/nodes/network_node.py --node-id core1 --api-port 5001 --p2p-port 8001
python src/nodes/network_node.py --no-discover --debug --quiet
```

### **Mining Client Commands**  
```bash
python src/clients/mining_client.py --help
python src/clients/mining_client.py --wallet ADDRESS --node http://localhost:5001
python src/clients/mining_client.py --wallet ADDRESS --stats --quiet
```

### **Wallet Client Commands**
```bash  
python src/clients/wallet_client.py --help
python src/clients/wallet_client.py create --wallet miner.json
python src/clients/wallet_client.py send --wallet miner.json --to ADDRESS --amount 50
```

---

## ⚡ **Multi-Miner Testing**

### **Automated Multi-Miner Test**
```bash
# Run dynamic test (asks how many miners)
python tests/test_competitive_mining.py

# Example output:
🎯 How many mining nodes to create? (default 3): 10
🏗️  Setting up 10-node competitive mining network...
```

### **Manual Multi-Miner Setup**
```bash
# Start multiple network nodes
for i in {1..5}; do
  python src/nodes/network_node.py --node-id core$i --api-port $((5000+i)) &
done

# Start multiple mining clients
for i in {1..5}; do
  python src/clients/mining_client.py --wallet ADDRESS_$i --node http://localhost:$((5000+i)) &
done
```

---

## 📊 **Monitoring Multiple Miners**

### **Check All Nodes**
```bash
# Check status of multiple nodes
for port in {5001..5010}; do
  echo "Node on port $port:"
  curl -s http://localhost:$port/status | jq '.blockchain_length'
  echo
done
```

### **Real-Time Network Monitoring**
```bash
# Watch blockchain growth
watch -n 2 'for port in {5001..5010}; do echo -n "Port $port: "; curl -s http://localhost:$port/status | jq -r ".blockchain_length // 0"; done'
```

---

## 🏆 **Key Features**

### **✅ Blockchain Architecture**
- Separate network nodes and mining clients
- Clean separation of concerns
- Bitcoin-style architecture
- Maximum flexibility and control

### **✅ Unlimited Miners**
- Support for 100+ mining clients
- Automatic peer discovery up to port 5100
- Dynamic network topology
- Scalable peer management

### **✅ Enterprise Features**
- Thread-safe operations
- UTXO transaction model
- Bitcoin-compatible cryptography
- Comprehensive API endpoints

---

## 🔄 **Network Topology**

### **ChainCore Architecture:**
```
Node1 ←→ Node2 ←→ Node3 ←→ ... ←→ NodeN
  ↑       ↑       ↑               ↑
Miner1  Miner2  Miner3           MinerN
 ⛏️      ⛏️      ⛏️             ⛏️
```

**Network Nodes** maintain the blockchain and handle API requests  
**Mining Clients** connect to nodes and perform proof-of-work  
**Clean Separation** allows for flexible deployment and scaling

---

## 🎯 **Best Practices**

### **For Development:**
- Start with 3-5 nodes for testing
- Use separate terminals for each component
- Monitor logs for debugging
- Use `--debug` flag for detailed output

### **For Production:**
- Deploy nodes and miners on separate machines
- Use proper wallet security
- Monitor network health
- Scale miners based on network difficulty

### **For Testing:**
- Use the automated test script
- Create temporary wallets
- Clean up processes after testing
- Monitor resource usage

---

## ✅ **ChainCore Features**

✅ **mining_client.py** - Bitcoin-style separate mining process  
✅ **network_node.py** - Full-featured blockchain node  
✅ **wallet_client.py** - Secure wallet management  
✅ **Unlimited miners** - Support for 100+ miners  
✅ **Peer discovery** - Automatic network formation  
✅ **Thread safety** - Concurrency control with locks  
✅ **UTXO model** - Prevents double-spending  
✅ **Bitcoin cryptography** - Industry-standard security  

Your ChainCore blockchain supports **unlimited competitive miners** with the proven **separate client architecture**! 🎉