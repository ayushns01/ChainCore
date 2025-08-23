# Peer Management and Networking Documentation

## Overview

ChainCore's peer management system is built on HTTP-based networking, providing robust peer discovery, connection management, and network resilience. This system ensures nodes can dynamically discover each other, maintain active connections, and handle network failures gracefully.

## Architecture Components

### 1. Peer Management Core Classes

```python
class NetworkNode:
    def __init__(self, api_port: int):
        self.api_port = api_port
        self.peers: Set[str] = set()           # All known peer URLs
        self.active_peers: Set[str] = set()    # Currently responsive peers
        self.last_peer_discovery = 0           # Timestamp of last discovery
```

### 2. Peer Storage Structure

- **`peers`**: Set of all discovered peer URLs (persistent across discovery cycles)
- **`active_peers`**: Subset of peers that are currently reachable
- **Dynamic Management**: Peers are automatically added/removed based on responsiveness

## Peer Discovery System

### 1. Port-Based Discovery

The system probes common ports to find active nodes:

```python
def _discover_active_peers(self, verbose=True):
    """Discover and add only active peer nodes"""
    import requests
    import time
    
    self.last_peer_discovery = time.time()
    common_ports = [5000, 5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009, 5010, 5011]
    newly_discovered = 0
    
    for port in common_ports:
        if port != self.api_port:  # Don't add self as peer
            peer_url = f"http://localhost:{port}"
            try:
                # Test if peer is active with short timeout
                response = requests.get(f"{peer_url}/status", timeout=2)
                if response.status_code == 200:
                    if peer_url not in self.peers:
                        newly_discovered += 1
                        if verbose:
                            print(f"✅ Discovered new peer: {peer_url}")
                    self.peers.add(peer_url)
                    self.active_peers.add(peer_url)
                    
                    # Try to get peer's peer list for peer exchange
                    try:
                        peer_response = requests.get(f"{peer_url}/peers", timeout=2)
                        if peer_response.status_code == 200:
                            peer_data = peer_response.json()
                            self._process_peer_exchange(peer_data.get('active_peers', []), verbose=False)
                    except:
                        pass  # Peer exchange failed, but peer is still valid
                        
            except:
                # Remove peer if it was previously active but now unreachable
                if peer_url in self.active_peers:
                    self.active_peers.discard(peer_url)
                    if verbose:
                        print(f"⚠️ Peer became inactive: {peer_url}")
    
    if verbose:
        print(f"🔗 Peer discovery complete: {len(self.active_peers)} active peers ({newly_discovered} new)")
```

### 2. Peer Exchange Protocol

Nodes share their peer lists with each other to accelerate network discovery:

```python
def _process_peer_exchange(self, peer_urls, verbose=True):
    """Process peer URLs received from peer exchange"""
    import requests
    
    newly_discovered = 0
    for peer_url in peer_urls:
        if peer_url not in self.peers and not peer_url.endswith(f":{self.api_port}"):
            try:
                # Verify the peer is actually reachable
                response = requests.get(f"{peer_url}/status", timeout=2)
                if response.status_code == 200:
                    self.peers.add(peer_url)
                    self.active_peers.add(peer_url)
                    newly_discovered += 1
                    if verbose:
                        print(f"🤝 Added peer via exchange: {peer_url}")
            except:
                pass  # Peer not reachable
    
    if verbose and newly_discovered > 0:
        print(f"🔄 Peer exchange added {newly_discovered} new peers")
```

### 3. Discovery Timing and Triggers

- **Startup Discovery**: Immediate peer discovery when node starts
- **Periodic Discovery**: Can be triggered as needed
- **Event-Driven Discovery**: Triggered during synchronization operations

## Connection Management

### 1. Health Check System

All peer communications include implicit health checks:

```python
# In synchronization methods
for peer in list(self.active_peers):  # Create copy to modify during iteration
    try:
        response = requests.get(f"{peer}/chain", timeout=5)
        if response.status_code == 200:
            # Peer is healthy, process response
            peer_chain_data = response.json()
            # ... process data ...
        else:
            # Peer responded but with error
            print(f"⚠️ Peer {peer} returned error: {response.status_code}")
    except:
        # Peer is unreachable, remove from active list
        self.active_peers.discard(peer)
        print(f"❌ Peer {peer} unreachable during sync")
```

### 2. Automatic Peer Cleanup

Unreachable peers are automatically removed from active peer lists:

```python
def _sync_with_peers_blocking(self):
    import requests
    
    best_chain_length = len(self.blockchain.chain)
    best_peer = None
    
    for peer in list(self.active_peers):  # Copy to avoid modification during iteration
        try:
            response = requests.get(f"{peer}/chain", timeout=5)
            if response.status_code == 200:
                # Peer is active, process response
                # ...
            else:
                print(f"⚠️ Peer {peer} returned error {response.status_code}")
        except:
            # Remove inactive peer
            self.active_peers.discard(peer)
            print(f"❌ Removed inactive peer: {peer}")
```

### 3. Connection Timeouts

Different operations use appropriate timeouts:

```python
# Quick health checks (peer discovery)
response = requests.get(f"{peer_url}/status", timeout=2)

# Standard operations (transaction broadcast)
response = requests.post(f"{peer}/receive_transaction", 
                        json={'transaction': tx_data},
                        timeout=5)

# Heavy operations (blockchain sync)
response = requests.get(f"{peer}/chain", timeout=10)
```

## Network API Endpoints

### 1. Peer Information Endpoints

```python
@app.route('/peers', methods=['GET'])
def get_peers():
    return jsonify({
        'peers': list(node.peers),                    # All known peers
        'active_peers': list(node.active_peers),      # Currently active peers
        'peer_count': len(node.active_peers)          # Active peer count
    })

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify({
        'node_id': node.node_id,
        'blockchain_length': len(node.blockchain.chain),
        'pending_transactions': len(node.blockchain.transaction_pool),
        'peers': len(node.peers),                     # Peer count for health check
        'target_difficulty': node.blockchain.target_difficulty
    })
```

### 2. Data Synchronization Endpoints

```python
@app.route('/chain', methods=['GET'])
def get_blockchain():
    response = jsonify({
        'length': len(node.blockchain.chain),
        'chain': [block.to_dict() for block in node.blockchain.chain]
    })
    response.headers['X-Blockchain-Length'] = str(len(node.blockchain.chain))
    return response

@app.route('/transactions', methods=['GET'])
def get_transactions():
    return jsonify({
        'transactions': [tx.to_dict() for tx in node.blockchain.transaction_pool]
    })
```

### 3. Data Reception Endpoints

```python
@app.route('/receive_transaction', methods=['POST'])
def receive_transaction():
    """Receive transaction from peer (no re-broadcasting)"""
    try:
        tx_data = request.get_json()
        transaction = Transaction.from_dict(tx_data)
        
        if node.blockchain.add_transaction(transaction):
            # Trigger lightweight sync check when receiving new transactions
            if len(node.active_peers) > 0:
                threading.Thread(target=node._quick_sync_check, daemon=True).start()
            return jsonify({'status': 'accepted', 'tx_id': transaction.tx_id})
        else:
            return jsonify({'status': 'rejected', 'error': 'Invalid transaction'}), 400
            
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/submit_block', methods=['POST'])
def submit_block():
    try:
        block_data = request.get_json()
        
        # Check if this block was actually mined by this node or received from peer
        is_locally_mined = request.headers.get('X-Local-Mining') == 'true'
        
        # Reconstruct and validate block
        transactions = [Transaction.from_dict(tx) for tx in block_data['transactions']]
        block = Block(
            block_data['index'],
            transactions,
            block_data['previous_hash'],
            block_data.get('timestamp'),
            block_data.get('nonce', 0),
            block_data.get('target_difficulty', 4)
        )
        
        # Validate block
        if node.blockchain.add_block(block):
            # Extract miner address from coinbase transaction
            miner_address = block.transactions[0].outputs[0].recipient_address if block.transactions else "unknown"
            
            # Clean up transaction pool
            confirmed_tx_ids = {tx.tx_id for tx in block.transactions}
            node.blockchain.transaction_pool = [
                tx for tx in node.blockchain.transaction_pool 
                if tx.tx_id not in confirmed_tx_ids
            ]
            
            # Record block if locally mined
            if is_locally_mined:
                node._log_block_mined(block, miner_address)
            
            # Broadcast to other peers (except sender)
            sender_port = request.environ.get('SERVER_PORT')
            node._broadcast_block_to_peers(block, exclude_port=sender_port)
            
            return jsonify({'status': 'accepted', 'block_hash': block.hash})
        else:
            return jsonify({'status': 'rejected', 'error': 'Invalid block'}), 400
            
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500
```

## Broadcasting Mechanisms

### 1. Transaction Broadcasting

```python
def _broadcast_transaction_to_peers(self, transaction):
    """Broadcast transaction to active peer nodes only"""
    import requests
    failed_peers = set()
    
    for peer in list(self.active_peers):  # Use only active peers
        try:
            response = requests.post(
                f"{peer}/receive_transaction", 
                json=transaction.to_dict(),
                timeout=10,  # Increased timeout to 10 seconds
                headers={'Content-Type': 'application/json'}
            )
            if response.status_code != 200:
                print(f"⚠️ Peer {peer} rejected transaction")
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Failed to broadcast to {peer}: {str(e)[:50]}...")
            failed_peers.add(peer)
    
    # Remove failed peers from active list
    self.active_peers -= failed_peers
    if failed_peers:
        print(f"🔌 Removed {len(failed_peers)} inactive peers from active list")
```

### 2. Block Broadcasting

```python
def _broadcast_block_to_peers(self, block):
    """Broadcast block to active peer nodes only"""
    import requests
    failed_peers = set()
    
    for peer in list(self.active_peers):  # Use only active peers
        try:
            response = requests.post(
                f"{peer}/submit_block",
                json=block.to_dict(),
                timeout=10,  # Increased timeout to 10 seconds
                headers={
                    'Content-Type': 'application/json',
                    'X-Local-Mining': 'false'  # Mark as peer-received block, not locally mined
                }
            )
            if response.status_code != 200:
                print(f"⚠️ Peer {peer} rejected block")
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Failed to broadcast block to {peer}: {str(e)[:50]}...")
            failed_peers.add(peer)
    
    # Remove failed peers from active list
    self.active_peers -= failed_peers
    if failed_peers:
        print(f"🔌 Removed {len(failed_peers)} inactive peers from active list")
```

## Network Resilience Features

### 1. Automatic Peer Recovery

Peers are automatically re-added when they become available:

```python
# During peer discovery
for port in common_ports:
    if port != self.api_port:
        peer_url = f"http://localhost:{port}"
        try:
            response = requests.get(f"{peer_url}/status", timeout=2)
            if response.status_code == 200:
                if peer_url not in self.peers:
                    newly_discovered += 1
                    print(f"✅ Discovered new peer: {peer_url}")
                self.peers.add(peer_url)            # Add to all known peers
                self.active_peers.add(peer_url)     # Add to active peers
```

### 2. Graceful Degradation

The network continues to operate even with peer failures:

```python
# Mining operations continue even without peers
if len(self.active_peers) > 0:
    self._sync_with_peers_blocking()  # Sync if peers available
else:
    print("📡 No peers available - operating independently")

# Block creation proceeds regardless of network state
block_template = self.blockchain.create_block_template(miner_address)
```

### 3. Split-Brain Prevention

The system prevents network partitions through:

- **Startup Synchronization**: Nodes sync with network before accepting transactions
- **Longest Chain Rule**: Always adopt the longest valid chain
- **Continuous Synchronization**: Regular sync checks during operation

```python
def _startup_sync(self):
    """Synchronize with network on startup to prevent genesis forks"""
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
    
    print(f"✅ Startup sync complete - blockchain length: {len(self.blockchain.chain)}")
```

## Performance Optimization

### 1. Efficient Peer Lists

```python
# Use sets for O(1) lookup and modification
self.peers: Set[str] = set()
self.active_peers: Set[str] = set()

# Create copies when iterating to allow modification
for peer in list(self.active_peers):
    # Safe to modify self.active_peers during iteration
```

### 2. Timeout Management

Different timeouts for different operations:

```python
# Quick operations (2 seconds)
response = requests.get(f"{peer_url}/status", timeout=2)

# Standard operations (5 seconds)
response = requests.post(f"{peer}/receive_transaction", json=data, timeout=5)

# Heavy operations (10+ seconds)
response = requests.get(f"{peer}/chain", timeout=10)
```

### 3. Asynchronous Operations

Non-blocking sync operations:

```python
# Trigger lightweight sync check without blocking
if len(self.active_peers) > 0:
    threading.Thread(target=self._quick_sync_check, daemon=True).start()
```

## Monitoring and Diagnostics

### 1. Peer Status Monitoring

```python
@app.route('/network_info', methods=['GET'])
def get_network_info():
    return jsonify({
        'total_peers': len(node.peers),
        'active_peers': len(node.active_peers),
        'peer_list': list(node.active_peers),
        'last_discovery': node.last_peer_discovery,
        'network_health': 'healthy' if len(node.active_peers) > 0 else 'isolated'
    })
```

### 2. Connection Diagnostics

The system provides detailed logging for peer operations:

```python
print(f"🔗 Peer discovery complete: {len(self.active_peers)} active peers ({newly_discovered} new)")
print(f"✅ Discovered new peer: {peer_url}")
print(f"⚠️ Peer became inactive: {peer_url}")
print(f"🤝 Added peer via exchange: {peer_url}")
print(f"❌ Removed inactive peer: {peer}")
```

### 3. Network Health Assessment

- **Peer Count Tracking**: Monitor number of active peers
- **Response Time Monitoring**: Track peer response times
- **Failure Rate Analysis**: Monitor peer failure rates during operations

This comprehensive peer management system ensures robust networking with automatic discovery, health monitoring, and graceful failure handling, making the ChainCore network resilient to node failures and network partitions.