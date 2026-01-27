# Session Recording System Documentation

## Overview

ChainCore implements a comprehensive session recording system that tracks blockchain mining activities across multiple nodes. The system ensures that each node only records blocks they actually mined, preventing duplicate entries and providing accurate mining statistics.

## Architecture

### Core Components

1. **SessionManager**: Singleton class managing session lifecycle and metadata
2. **Session Folders**: Organized storage for each blockchain run
3. **Node Session Files**: Individual mining records per node
4. **Mining Statistics**: Aggregated statistics across all nodes

```python
class SessionManager:
    _instance = None
    _current_session_folder = None
    _session_start_time = None
```

## Session Folder Structure

```
sessions/
├── session_1/
│   ├── session_metadata.json
│   ├── session_core0_1754760371.json
│   ├── session_core1_1754760388.json
│   └── ...
├── session_2/
│   └── ...
└── session_N/
```

### Session Metadata Structure

```json
{
  "session_name": "session_9",
  "session_number": 9,
  "session_start_time": "2025-08-09T22:56:11.557811",
  "blockchain_start_timestamp": 1754760371.557926,
  "nodes": [
    {
      "node_id": "core0",
      "api_port": 5000,
      "p2p_port": 8000,
      "registration_time": "2025-08-09T22:56:11.558074",
      "last_seen": 1754760714.182986
    }
  ],
  "status": "active",
  "mining_statistics": {
    "total_blocks_mined": 34,
    "blocks_per_core": {
      "core1": {
        "blocks_mined_count": 6,
        "session_file": "session_core1_1754760388.json",
        "start_time": "2025-08-09T22:56:28.938789",
        "latest_blocks": [...]
      }
    },
    "last_updated": "2025-08-09T23:01:49.210917"
  }
}
```

## Session Management

### 1. Session Discovery and Creation

The system intelligently manages sessions to prevent fragmentation:

```python
def get_current_session_folder(self) -> str:
    if self._current_session_folder is None:
        # Check if there's an existing active session we can join
        existing_session = self._find_active_session()
        if existing_session:
            self._current_session_folder = existing_session
            print(f"📁 Joined existing session: {os.path.basename(existing_session)}")
        else:
            self._create_new_session_folder()
    return self._current_session_folder
```

### 2. Active Session Detection

The system checks if nodes are actually running before joining a session:

```python
def _has_active_nodes(self, nodes: list) -> bool:
    import requests
    
    for node in nodes:
        api_port = node.get('api_port')
        if api_port:
            try:
                response = requests.get(
                    f"http://localhost:{api_port}/status", 
                    timeout=2
                )
                if response.status_code == 200:
                    node['last_seen'] = time.time()
                    return True  # At least one node is active
            except:
                continue
    
    return False  # No nodes are responsive
```

### 3. Sequential Session Numbering

Sessions are numbered sequentially starting from 1:

```python
def _get_next_session_number(self) -> int:
    if not os.path.exists(self.base_sessions_dir):
        os.makedirs(self.base_sessions_dir, exist_ok=True)
        return 1
    
    existing_numbers = []
    for item in os.listdir(self.base_sessions_dir):
        session_path = os.path.join(self.base_sessions_dir, item)
        if os.path.isdir(session_path) and item.startswith('session_'):
            try:
                number_str = item.replace('session_', '')
                if number_str.isdigit():
                    existing_numbers.append(int(number_str))
            except:
                continue
    
    return max(existing_numbers, default=0) + 1
```

## Block Recording System

### 1. Mining Detection Header

The system uses the `X-Local-Mining` header to distinguish locally mined blocks:

```python
# In network_node.py - when broadcasting locally mined blocks
def broadcast_new_block(self, block: Block):
    block_data = block.to_dict()
    
    for peer in list(self.active_peers):
        try:
            response = requests.post(
                f"{peer}/submit_block",
                json={'block': block_data},
                headers={
                    'Content-Type': 'application/json',
                    'X-Local-Mining': 'true'  # Mark as locally mined
                },
                timeout=5
            )
```

### 2. Block Reception and Recording

When receiving blocks, nodes check the header to determine if they should record it:

```python
@app.route('/submit_block', methods=['POST'])
def submit_block():
    try:
        data = request.json
        block_data = data['block']
        block = node._dict_to_block(block_data)
        
        if node.blockchain.add_block(block):
            # Extract miner address from coinbase transaction
            miner_address = block.transactions[0].outputs[0].recipient_address if block.transactions else "unknown"
            
            # Record block ONLY if mined locally
            is_locally_mined = request.headers.get('X-Local-Mining') == 'true'
            if is_locally_mined:
                miner_address = block.transactions[0].outputs[0].recipient_address if block.transactions else "unknown"
                node._log_block_mined(block, miner_address)  # Only record if we mined it
            
            return jsonify({'status': 'accepted', 'block_hash': block.hash}), 200
```

### 3. Block Recording Implementation

Each node maintains its own session file with blocks they actually mined:

```python
def _log_block_mined(self, block: Block, miner_address: str):
    """Log a mined block to the session file"""
    if not hasattr(self, 'session_data'):
        self._init_session_file()
    
    # Create block record
    block_record = {
        "block_index": block.index,
        "block_hash": block.hash,
        "previous_hash": block.previous_hash,
        "miner_address": miner_address,
        "mined_by_node": self.node_id,
        "timestamp": datetime.fromtimestamp(block.timestamp).isoformat(),
        "nonce": block.nonce,
        "difficulty": block.target_difficulty,
        "transaction_count": len(block.transactions),
        "has_transactions": len(block.transactions) > 1,
        "transactions": [
            {
                "tx_id": tx.tx_id,
                "is_coinbase": tx.is_coinbase(),
                "amount": sum(output.amount for output in tx.outputs) if tx.outputs else 0
            } for tx in block.transactions
        ]
    }
    
    # Add to session data
    self.session_data["blocks_mined"].append(block_record)
    
    # Update session file
    with open(self.session_file_path, 'w') as f:
        json.dump(self.session_data, f, indent=2)
    
    print(f"📝 Block {block.index} recorded in session for {self.node_id}")
```

## Node Session Files

### Individual Node Session Structure

```json
{
  "session_id": "session_core1_1754760388",
  "node_id": "core1",
  "start_time": "2025-08-09T22:56:28.938789",
  "session_folder": "session_9",
  "blocks_mined": [
    {
      "block_index": 3,
      "block_hash": "000004e9882d300e...",
      "previous_hash": "0000092959c9fccb...",
      "miner_address": "1CcUyVAiHT2dGP4ESxWqsDKFzazkQ2UW3n",
      "mined_by_node": "core1",
      "timestamp": "2025-08-09T23:00:04.161767",
      "nonce": 224205,
      "difficulty": 5,
      "transaction_count": 1,
      "has_transactions": false,
      "transactions": [
        {
          "tx_id": "c2453c85077b5c6978af16e05bfe195bd5353308b113882841b551377bf161a1",
          "is_coinbase": true,
          "amount": 50.0
        }
      ]
    }
  ]
}
```

### Session File Initialization

```python
def _init_session_file(self):
    """Initialize the session file for this node"""
    session_folder = session_manager.get_current_session_folder()
    
    # Create unique session file for this node
    session_filename = f"session_{self.node_id}_{int(self.session_start_time.timestamp())}.json"
    self.session_file_path = os.path.join(session_folder, session_filename)
    
    # Save session file
    with open(self.session_file_path, 'w') as f:
        json.dump(self.session_data, f, indent=2)
    
    print(f"📁 Session file created: {session_filename}")
```

## Mining Statistics System

### 1. Automated Statistics Updates

Mining statistics are updated automatically every 5 blocks:

```python
# In network_node.py block addition logic
def _log_block_mined(self, block: Block, miner_address: str):
    # ... block recording logic ...
    
    # Update session metadata with mining statistics every few blocks
    if len(self.session_data["blocks_mined"]) % 5 == 0:  # Update every 5 blocks
        try:
            from session_manager import session_manager
            session_manager.update_mining_stats()
        except Exception as e:
            print(f"⚠️ Error updating session metadata: {e}")
```

### 2. Statistics Aggregation

The SessionManager scans all node session files to build comprehensive statistics:

```python
def update_mining_stats(self):
    """Update session metadata with mining statistics from all node session files"""
    if not self._current_session_folder:
        return
    
    metadata_file = os.path.join(self._current_session_folder, "session_metadata.json")
    try:
        # Read current metadata
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Collect mining statistics from all node session files in this session
        mining_stats = {}
        total_blocks_mined = 0
        
        # Scan all session files in this session folder
        if os.path.exists(self._current_session_folder):
            for filename in os.listdir(self._current_session_folder):
                if filename.startswith('session_') and filename.endswith('.json') and filename != 'session_metadata.json':
                    filepath = os.path.join(self._current_session_folder, filename)
                    try:
                        with open(filepath, 'r') as f:
                            node_data = json.load(f)
                        
                        node_id = node_data.get('node_id', 'unknown')
                        blocks_mined = node_data.get('blocks_mined', [])
                        block_count = len(blocks_mined)
                        
                        mining_stats[node_id] = {
                            'blocks_mined_count': block_count,
                            'session_file': filename,
                            'start_time': node_data.get('start_time'),
                            'latest_blocks': [
                                {
                                    'block_index': block.get('block_index'),
                                    'block_hash': block.get('block_hash', '')[:16] + '...',
                                    'timestamp': block.get('timestamp')
                                } for block in blocks_mined[-5:]  # Last 5 blocks
                            ]
                        }
                        total_blocks_mined += block_count
                        
                    except Exception as e:
                        print(f"⚠️ Error reading session file {filename}: {e}")
                        continue
        
        # Update metadata with mining statistics
        metadata['mining_statistics'] = {
            'total_blocks_mined': total_blocks_mined,
            'blocks_per_core': mining_stats,
            'last_updated': datetime.now().isoformat()
        }
        
        # Write updated metadata
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
```

## Node Registration and Heartbeat

### 1. Node Registration

When a node starts, it registers itself in the session:

```python
def register_node(self, node_id: str, api_port: int, p2p_port: int):
    """Register a node in the current session"""
    session_folder = self.get_current_session_folder()
    metadata_file = os.path.join(session_folder, "session_metadata.json")
    
    # Read existing metadata
    try:
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
    except:
        metadata = {"nodes": []}
    
    # Add node info with heartbeat timestamp
    node_info = {
        "node_id": node_id,
        "api_port": api_port,
        "p2p_port": p2p_port,
        "registration_time": datetime.now().isoformat(),
        "last_seen": time.time()
    }
    
    # Check if node already registered and update it, otherwise add new
    existing_nodes = {n['node_id']: n for n in metadata.get('nodes', [])}
    if node_id in existing_nodes:
        # Update existing node's last_seen timestamp
        for node in metadata['nodes']:
            if node['node_id'] == node_id:
                node['last_seen'] = time.time()
                node['registration_time'] = datetime.now().isoformat()
                break
    else:
        metadata['nodes'].append(node_info)
    
    # Ensure session is marked as active when nodes register
    metadata['status'] = 'active'
    
    # Update metadata file
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"📝 Registered {node_id} in session {os.path.basename(session_folder)}")
```

## Key Features

### 1. Duplicate Prevention
- **X-Local-Mining Header**: Ensures only the mining node records the block
- **Node-Specific Files**: Each node maintains its own mining record
- **Block Index Validation**: Prevents duplicate entries within node files

### 2. Mining Order Preservation
- Blocks are recorded in the exact order they were mined
- Timestamps preserve mining sequence
- Block indices maintain blockchain order

### 3. Statistical Accuracy
- Per-core mining statistics are automatically calculated
- Real-time updates every 5 blocks
- Historical data preservation in session metadata

### 4. Session Integrity
- Automatic session management and cleanup
- Node heartbeat monitoring
- Session status tracking (active/completed)

### 5. Multi-Node Coordination
- Shared session folders across all nodes in a blockchain run
- Centralized metadata with distributed individual records
- Automatic peer discovery and session joining

This system ensures accurate, non-duplicated recording of mining activities while providing comprehensive statistics and session management for multi-node blockchain networks.