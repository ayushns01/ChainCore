# P2P Synchronization and Communication System

## Overview

ChainCore uses an HTTP-based peer-to-peer communication system for blockchain synchronization and transaction propagation. Unlike traditional P2P protocols that use raw TCP sockets, this implementation leverages HTTP REST APIs for simplicity, reliability, and debugging ease.

## Architecture

### Network Node Structure

Each network node (`NetworkNode` class in `network_node.py`) operates as both:
- **HTTP Server**: Exposes REST API endpoints for peer communication
- **HTTP Client**: Makes requests to other nodes for synchronization

```python
class NetworkNode:
    def __init__(self, api_port: int):
        self.api_port = api_port
        self.peers: Set[str] = set()  # All known peers
        self.active_peers: Set[str] = set()  # Currently reachable peers
        self.blockchain = Blockchain()
        self.transaction_pool: List[Transaction] = []
```

### Peer Discovery Mechanism

#### 1. Port-Based Discovery
The system discovers peers by testing common ports (5000-5011):

```python
def _discover_active_peers(self, verbose=True):
    common_ports = [5000, 5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009, 5010, 5011]
    
    for port in common_ports:
        if port != self.api_port:  # Don't add self as peer
            peer_url = f"http://localhost:{port}"
            try:
                response = requests.get(f"{peer_url}/status", timeout=2)
                if response.status_code == 200:
                    self.peers.add(peer_url)
                    self.active_peers.add(peer_url)
            except:
                # Remove peer if it was previously active but now unreachable
                self.active_peers.discard(peer_url)
```

#### 2. Peer Exchange Protocol
Nodes share their peer lists with each other:

```python
def _process_peer_exchange(self, peer_urls, verbose=True):
    for peer_url in peer_urls:
        if peer_url not in self.peers and not peer_url.endswith(f":{self.api_port}"):
            try:
                response = requests.get(f"{peer_url}/status", timeout=2)
                if response.status_code == 200:
                    self.peers.add(peer_url)
                    self.active_peers.add(peer_url)
            except:
                pass  # Peer not reachable
```

## Synchronization Protocols

### 1. Startup Synchronization

When a node starts, it performs startup synchronization to prevent genesis forks:

```python
def _startup_sync(self):
    if len(self.active_peers) == 0:
        print("📡 No peers found - starting as genesis node")
        return
    
    print("🔄 Performing startup synchronization...")
    self._sync_with_peers_blocking()
    
    # If we still only have genesis block but peers have more, force sync
    if len(self.blockchain.chain) == 1 and len(self.active_peers) > 0:
        print("⚠️  Only have genesis block - attempting network sync...")
        time.sleep(2)
        self._sync_with_peers_blocking()
```

### 2. Blockchain Synchronization

#### Length-Based Chain Selection
The system implements the longest chain rule:

```python
def _sync_with_peers_blocking(self):
    import requests
    
    best_chain_length = len(self.blockchain.chain)
    best_peer = None
    
    for peer in list(self.active_peers):
        try:
            response = requests.get(f"{peer}/chain", timeout=5)
            if response.status_code == 200:
                peer_chain_data = response.json()
                peer_chain_length = len(peer_chain_data.get('chain', []))
                
                if peer_chain_length > best_chain_length:
                    best_chain_length = peer_chain_length
                    best_peer = peer
        except:
            self.active_peers.discard(peer)
```

#### Chain Validation and Replacement
When a longer valid chain is found:

```python
if best_peer and best_chain_length > len(self.blockchain.chain):
    try:
        response = requests.get(f"{best_peer}/chain", timeout=10)
        peer_chain_data = response.json()
        
        if self._validate_chain(peer_chain_data['chain']):
            print(f"🔄 Replacing chain with longer valid chain from {best_peer}")
            self.blockchain.chain = [self._dict_to_block(block_data) for block_data in peer_chain_data['chain']]
            self._rebuild_utxo_set()
```

### 3. Transaction Pool Synchronization

```python
def sync_transaction_pool_with_peers(self):
    for peer in list(self.active_peers):
        try:
            response = requests.get(f"{peer}/transactions", timeout=5)
            if response.status_code == 200:
                peer_transactions = response.json().get('transactions', [])
                
                for tx_data in peer_transactions:
                    tx = Transaction.from_dict(tx_data)
                    if (tx.tx_id not in [t.tx_id for t in self.transaction_pool] and
                        self.blockchain.validate_transaction(tx)):
                        self.transaction_pool.append(tx)
        except:
            self.active_peers.discard(peer)
```

## Communication Protocols

### 1. Block Broadcasting

When a node mines a new block, it broadcasts it to all active peers:

```python
def broadcast_new_block(self, block: Block):
    block_data = block.to_dict()
    
    for peer in list(self.active_peers):
        try:
            response = requests.post(
                f"{peer}/submit_block",
                json={'block': block_data},
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            if response.status_code != 200:
                print(f"⚠️ Failed to broadcast block to {peer}")
        except:
            print(f"❌ Peer {peer} unreachable during block broadcast")
            self.active_peers.discard(peer)
```

### 2. Transaction Broadcasting

New transactions are propagated across the network:

```python
def broadcast_transaction(self, transaction: Transaction):
    tx_data = transaction.to_dict()
    
    for peer in list(self.active_peers):
        try:
            response = requests.post(
                f"{peer}/add_transaction",
                json={'transaction': tx_data},
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
        except:
            self.active_peers.discard(peer)
```

### 3. Block Reception and Validation

When receiving a new block from peers:

```python
@app.route('/submit_block', methods=['POST'])
def submit_block():
    try:
        data = request.json
        block_data = data['block']
        
        # Convert dict to Block object
        block = node._dict_to_block(block_data)
        
        # Validate block
        if node.blockchain.add_block(block):
            # Extract miner address from coinbase transaction
            miner_address = block.transactions[0].outputs[0].recipient_address if block.transactions else "unknown"
            
            # Record block if mined locally
            is_locally_mined = request.headers.get('X-Local-Mining') == 'true'
            if is_locally_mined:
                miner_address = block.transactions[0].outputs[0].recipient_address if block.transactions else "unknown"
                node._log_block_mined(block, miner_address)
            
            return jsonify({'status': 'accepted', 'block_hash': block.hash}), 200
        else:
            return jsonify({'error': 'Invalid block'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

## API Endpoints

### Core Synchronization Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/status` | GET | Node health check and basic info |
| `/chain` | GET | Get full blockchain |
| `/peers` | GET | Get list of active peers |
| `/transactions` | GET | Get current transaction pool |
| `/submit_block` | POST | Receive new block from peers |
| `/add_transaction` | POST | Receive new transaction from peers |

### Peer Management Endpoints

```python
@app.route('/peers', methods=['GET'])
def get_peers():
    return jsonify({
        'peers': list(node.peers),
        'active_peers': list(node.active_peers),
        'peer_count': len(node.active_peers)
    })
```

## Fault Tolerance

### 1. Peer Health Monitoring
- Nodes are automatically removed from active peer list if unreachable
- Regular health checks during synchronization
- Timeout-based connection management (2-5 second timeouts)

### 2. Network Resilience
- Multiple synchronization attempts during startup
- Graceful handling of peer failures during broadcasts
- Automatic peer re-discovery

### 3. Chain Integrity
- Full chain validation before replacement
- UTXO set rebuilding after chain updates
- Transaction pool cleanup after new blocks

## Performance Characteristics

### Advantages of HTTP-Based P2P
1. **Simplicity**: Standard HTTP libraries, easy debugging
2. **Firewall Friendly**: Uses standard HTTP ports
3. **Stateless**: No persistent connections to manage
4. **RESTful**: Clear request/response semantics

### Scalability Considerations
- Broadcast complexity: O(n) where n = number of active peers
- Synchronization efficiency: Only syncs with longest chain peer
- Memory efficient: No persistent connection overhead

## Security Features

### 1. Block Validation
Every received block undergoes full validation:
- Proof of Work verification
- Previous hash linking
- Transaction validity
- UTXO consistency

### 2. Transaction Validation
All transactions are validated before inclusion:
- Signature verification
- Input/output balance
- Double-spend prevention
- UTXO availability

### 3. Peer Trust Model
- No implicit trust in peers
- Longest valid chain wins
- Full verification of all received data