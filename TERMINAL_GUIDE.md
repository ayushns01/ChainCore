# ChainCore Blockchain - Complete Terminal Guide

Complete step-by-step guide to run the ChainCore blockchain from scratch.

## =� Prerequisites

1. **Python Environment Setup**
```bash
cd /Users/ayush/Desktop/chain
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Verify Project Structure**

### Terminal 1: Start First Network Node
cd /Users/ayush/Desktop/chain
source venv/bin/activate
python3 network_node.py --node-id core1 --api-port 5000 --p2p-port 8000


### Terminal 2: Start Second Network Node
cd /Users/ayush/Desktop/chain
source venv/bin/activate
python3 network_node.py --node-id core2 --api-port 5001 --p2p-port 8001


### Terminal 3: Start Third Network Node
cd /Users/ayush/Desktop/chain
source venv/bin/activate
python3 network_node.py --node-id core3 --api-port 5002 --p2p-port 8002


### Terminal 4: Create Wallets
cd /Users/ayush/Desktop/chain
source venv/bin/activate


# Create wallet files (if they don't exist)
python3 wallet_client.py create --wallet alice.json
python3 wallet_client.py create --wallet bob.json
python3 wallet_client.py create --wallet miner1.json
python3 wallet_client.py create --wallet miner2.json


# Check wallet addresses
python3 wallet_client.py info --wallet alice.json
python3 wallet_client.py info --wallet bob.json
python3 wallet_client.py info --wallet miner1.json
python3 wallet_client.py info --wallet miner2.json


### Terminal 5: Start First Miner
python3 mining_client.py --wallet 1CcUyVAiHT2dGP4ESxWqsDKFzazkQ2UW3n --node http://localhost:5000
python3 mining_client.py --wallet 1GukayKD1hRAXnQaJYKVwQcwCvVzsUbcJj --node http://localhost:5001
python3 mining_client.py --wallet 18NDhHYAa3bx3jAZkc7HZf3vKr1JrwVXG3 --node http://localhost:5002


# Get balance
curl http://localhost:5001/balance/1CcUyVAiHT2dGP4ESxWqsDKFzazkQ2UW3n
curl http://localhost:5001/balance/1GukayKD1hRAXnQaJYKVwQcwCvVzsUbcJj
curl http://localhost:5001/balance/18NDhHYAa3bx3jAZkc7HZf3vKr1JrwVXG3
curl http://localhost:5001/balance/15vuSyM7ZFUNqBibgwHUgbkva4FDDn6pXq
curl http://localhost:5001/balance/1FzanzSbcH7sik5kzymbdTrNci6h5HxBCe


# Start mining on Node 
python3 mining_client.py --wallet 1CcUyVAiHT2dGP4ESxWqsDKFzazkQ2UW3n --node http://localhost:5000
python3 mining_client.py --wallet 1GukayKD1hRAXnQaJYKVwQcwCvVzsUbcJj --node http://localhost:5001
python3 mining_client.py --wallet 18NDhHYAa3bx3jAZkc7HZf3vKr1JrwVXG3 --node http://localhost:5002


### Terminal 6: Start Second Miner (Competitive)
cd /Users/ayush/Desktop/chain
source venv/bin/activate


### Terminal 7: Monitor Network & Balances

# Check network status
curl http://localhost:5000/status 
curl http://localhost:5001/status 
curl http://localhost:5002/status 


# Check transaction pool
curl http://localhost:5000/transaction_pool
curl http://localhost:5001/transaction_pool
curl http://localhost:5002/transaction_pool

# Blockchain Status
curl http://localhost:5000/blockchain


























### Continuous Network Status (run in any terminal)
```bash
# Real-time monitoring loop
while true; do
  clear
  echo "< ChainCore Network Status - $(date)"
  echo "========================================="
  
  for port in 5000 5001 5002; do
    echo -n "Node $port: "
    curl -s http://localhost:$port/status | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'Blocks: {data[\"blockchain_length\"]}, Pending: {data[\"pending_transactions\"]}, Peers: {data[\"peers\"]}')
except:
    print('Offline')
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
  echo "=� Wallet Balances - $(date)"
  echo "================================="
  
  ALICE_ADDR=$(python3 -c "import json; print(json.load(open('alice.json'))['address'])")
  BOB_ADDR=$(python3 -c "import json; print(json.load(open('bob.json'))['address'])")
  MINER1_ADDR=$(python3 -c "import json; print(json.load(open('miner1.json'))['address'])")
  MINER2_ADDR=$(python3 -c "import json; print(json.load(open('miner2.json'))['address'])")
  
  echo "Alice   ($ALICE_ADDR): $(curl -s http://localhost:5000/balance/$ALICE_ADDR | python3 -c "import sys,json; print(json.load(sys.stdin)['balance'])")"
  echo "Bob     ($BOB_ADDR): $(curl -s http://localhost:5000/balance/$BOB_ADDR | python3 -c "import sys,json; print(json.load(sys.stdin)['balance'])")"
  echo "Miner1  ($MINER1_ADDR): $(curl -s http://localhost:5000/balance/$MINER1_ADDR | python3 -c "import sys,json; print(json.load(sys.stdin)['balance'])")"
  echo "Miner2  ($MINER2_ADDR): $(curl -s http://localhost:5000/balance/$MINER2_ADDR | python3 -c "import sys,json; print(json.load(sys.stdin)['balance'])")"
  
  sleep 10
done
```

## <� Quick Commands Reference

### Check Network Health
```bash
# All nodes responding
curl http://localhost:5000/status
curl http://localhost:5001/status
curl http://localhost:5002/status

# Check peer connections
curl http://localhost:5000/peers
```

### Wallet Operations
```bash
# Check balance
python3 wallet_client.py balance --wallet alice.json

# Send transaction
python3 wallet_client.py send --wallet alice.json --to ADDRESS --amount 10.0 --fee 0.5

# Transaction history
python3 wallet_client.py history --wallet alice.json
```

### Mining Operations
```bash
# Start mining
python3 mining_client.py --wallet WALLET_ADDRESS --node http://localhost:5000

# Check mining rewards
curl http://localhost:5000/balance/WALLET_ADDRESS
```

### API Commands
```bash
# Get blockchain
curl http://localhost:5000/blockchain

# Transaction pool
curl http://localhost:5000/transaction_pool

# UTXOs for address
curl http://localhost:5000/utxos/ADDRESS
```

## =' Troubleshooting

### Node Not Starting
```bash
# Check if port is in use
lsof -i :5000

# Kill existing processes
pkill -f network_node.py
```

### Mining Not Working
```bash
# Check node is running
curl http://localhost:5000/status

# Verify wallet address format
python3 wallet_client.py info --wallet miner1.json
```

### Transaction Rejected
```bash
# Check balance first
python3 wallet_client.py balance --wallet sender.json

# Check transaction pool
curl http://localhost:5000/transaction_pool
```

## =� Shutdown

### Stop Everything
```bash
# Stop each terminal with Ctrl+C

# Or force kill all processes
pkill -f network_node.py
pkill -f mining_client.py
```

##  Success Indicators

Your blockchain is working correctly when you see:

1. **Nodes Running**: All 3 nodes respond to `/status` with peer connections
2. **Mining Active**: Terminal 5 & 6 show "Block X mined!" messages
3. **Balances Growing**: Miners accumulate 50 CC per block
4. **Transactions Processing**: Sent transactions appear in pools and get mined
5. **Network Sync**: All nodes show same blockchain length

**<� You now have a fully functional multi-node blockchain network!**

## =� Advanced Features

- **Load Balancing**: Connect wallets to different nodes
- **Competitive Mining**: Multiple miners compete for blocks
- **Transaction Broadcasting**: Transactions spread across all nodes
- **Automatic Sync**: Nodes sync every 30 seconds
- **Real-time Monitoring**: Live network status and balances

For more advanced operations, see `MINING_COMMANDS.md` and other documentation files.