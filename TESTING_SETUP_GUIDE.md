# ChainCore Testing Setup Guide
**Complete Testing Framework Implementation Plan**

*Generated on: November 13, 2025*  
*Repository: ChainCore (tier-1 branch)*  
*Current Status: Ad-hoc testing scripts → Comprehensive testing framework*

---

## 📊 **Executive Summary**

ChainCore currently has **40+ individual test scripts** but lacks a unified testing framework. This guide outlines the implementation of a comprehensive testing ecosystem that covers unit tests, integration tests, performance benchmarks, and automated CI/CD pipelines.

### **Current Testing Assets**
```
tests/
├── 📋 Unit Tests (15 files): test_database_*, test_difficulty_*, etc.
├── 🔧 Debug Scripts (10 files): debug_mining*, debug_block_*
├── ⚡ Performance Tests (8 files): test_multicore_*, test_competitive_*
├── 🌐 Integration Tests (7 files): test_integration*, test_blockchain_sync*
└── 🛠️ Utility Scripts (5 files): validate_*, verify_*, quick_*
```

---

## 🎯 **Testing Framework Architecture**

### **1. Test Categories & Structure**
```
tests/
├── unit/                    # Isolated component testing
│   ├── crypto/
│   ├── core/
│   ├── data/
│   ├── network/
│   └── conftest.py         # Shared fixtures
├── integration/            # Multi-component testing
│   ├── blockchain/
│   ├── mining/
│   ├── network/
│   └── database/
├── performance/            # Load and stress testing
│   ├── mining_benchmarks/
│   ├── network_stress/
│   └── database_performance/
├── e2e/                    # End-to-end scenarios
│   ├── full_network/
│   ├── transaction_flows/
│   └── multi_node_consensus/
├── fixtures/               # Test data and utilities
│   ├── wallets/
│   ├── blocks/
│   └── transactions/
└── reports/                # Test result artifacts
    ├── coverage/
    ├── performance/
    └── integration/
```

### **2. Technology Stack**
- **Testing Framework**: pytest (already in requirements.txt)
- **Coverage Analysis**: pytest-cov
- **Performance Testing**: pytest-benchmark
- **Async Testing**: pytest-asyncio (already included)
- **Database Testing**: pytest-postgresql
- **API Testing**: httpx/requests
- **Load Testing**: locust
- **CI/CD**: GitHub Actions

---

## 🔧 **Implementation Plan**

### **Phase 1: Foundation Setup (Week 1-2)**

#### **1.1 Enhanced Requirements**
```python
# Additional testing dependencies to add to requirements.txt
pytest-cov>=4.1.0           # Coverage reporting
pytest-benchmark>=4.0.0     # Performance benchmarking
pytest-html>=3.2.0          # HTML test reports
pytest-xdist>=3.3.1         # Parallel test execution
pytest-postgresql>=5.0.0    # PostgreSQL test fixtures
httpx>=0.24.0               # Modern HTTP client for API testing
locust>=2.15.0              # Load testing
factory-boy>=3.3.0          # Test data generation
freezegun>=1.2.0            # Time mocking
responses>=0.23.0           # HTTP response mocking
```

#### **1.2 pytest Configuration**
```ini
# pytest.ini
[tool:pytest]
minversion = 7.0
addopts = 
    -ra
    -q
    --strict-markers
    --strict-config
    --cov=src
    --cov-report=term-missing
    --cov-report=html:tests/reports/coverage
    --html=tests/reports/pytest_report.html
    --self-contained-html
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    unit: Unit tests for individual components
    integration: Integration tests for multiple components
    performance: Performance and benchmark tests
    e2e: End-to-end testing scenarios
    slow: Tests that take more than 10 seconds
    database: Tests requiring database connection
    network: Tests requiring network connectivity
    mining: Tests related to mining functionality
    crypto: Cryptographic functionality tests
```

#### **1.3 Test Configuration**
```python
# tests/conftest.py
import pytest
import os
import sys
import tempfile
import shutil
from typing import Generator, Dict, Any
from unittest.mock import MagicMock

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

@pytest.fixture(scope="session")
def test_database():
    """Provide isolated test database for testing"""
    # Implementation for test database setup
    pass

@pytest.fixture
def test_wallet():
    """Provide test wallet for transactions"""
    # Implementation for test wallet generation
    pass

@pytest.fixture
def mock_network_node():
    """Mock network node for isolated testing"""
    # Implementation for network node mocking
    pass

@pytest.fixture
def test_blockchain():
    """Provide clean blockchain instance"""
    # Implementation for test blockchain
    pass

@pytest.fixture(scope="function")
def temp_directory():
    """Provide temporary directory for test files"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_transaction():
    """Provide sample transaction for testing"""
    # Implementation for sample transaction
    pass

@pytest.fixture
def sample_block():
    """Provide sample block for testing"""
    # Implementation for sample block
    pass
```

### **Phase 2: Unit Test Implementation (Week 3-4)**

#### **2.1 Cryptographic Tests**
```python
# tests/unit/crypto/test_ecdsa_crypto.py
import pytest
from src.crypto.ecdsa_crypto import ECDSAKeyPair, validate_address, hash256

class TestECDSACrypto:
    def test_keypair_generation(self):
        """Test ECDSA key pair generation"""
        keypair = ECDSAKeyPair()
        
        assert keypair.private_key is not None
        assert keypair.public_key is not None
        assert len(keypair.get_private_key_hex()) == 64
        
    def test_signature_verification(self):
        """Test signature creation and verification"""
        keypair = ECDSAKeyPair()
        message = b"test message"
        
        signature = keypair.sign_message(message)
        assert keypair.verify_signature(message, signature)
        
    def test_address_generation(self):
        """Test Bitcoin-style address generation"""
        keypair = ECDSAKeyPair()
        address = keypair.get_address()
        
        assert validate_address(address)
        assert address.startswith('1')
        
    @pytest.mark.parametrize("invalid_address", [
        "invalid",
        "1234567890123456789012345678901234567890",
        "",
        "2MzQwSSnBHWHqSAqtTVQ6v47XtaisrJa1Vc"  # P2SH address
    ])
    def test_invalid_address_validation(self, invalid_address):
        """Test validation of invalid addresses"""
        assert not validate_address(invalid_address)

@pytest.mark.performance
class TestCryptoPerformance:
    def test_signature_performance(self, benchmark):
        """Benchmark signature performance"""
        keypair = ECDSAKeyPair()
        message = b"benchmark message"
        
        result = benchmark(keypair.sign_message, message)
        assert len(result) > 0
```

#### **2.2 Core Blockchain Tests**
```python
# tests/unit/core/test_block.py
import pytest
from src.core.block import Block
from src.core.bitcoin_transaction import Transaction

class TestBlock:
    def test_block_creation(self, sample_transaction):
        """Test block creation with transactions"""
        block = Block(
            index=1,
            previous_hash="0" * 64,
            transactions=[sample_transaction],
            nonce=0
        )
        
        assert block.index == 1
        assert len(block.transactions) == 1
        assert block.previous_hash == "0" * 64
        
    def test_block_hashing(self, sample_transaction):
        """Test block hash calculation"""
        block = Block(
            index=1,
            previous_hash="0" * 64,
            transactions=[sample_transaction],
            nonce=0
        )
        
        hash1 = block.calculate_hash()
        hash2 = block.calculate_hash()
        assert hash1 == hash2  # Deterministic
        assert len(hash1) == 64  # SHA-256 hex length
        
    def test_block_validation(self, sample_block):
        """Test block validation rules"""
        assert sample_block.is_valid()
        
        # Test invalid block
        sample_block.index = -1
        assert not sample_block.is_valid()
```

#### **2.3 Database Layer Tests**
```python
# tests/unit/data/test_block_dao.py
import pytest
from src.data.block_dao import BlockDAO
from src.core.block import Block

@pytest.mark.database
class TestBlockDAO:
    def test_block_insertion(self, test_database, sample_block):
        """Test block insertion into database"""
        dao = BlockDAO()
        
        result = dao.insert_block(sample_block)
        assert result is True
        
        # Verify insertion
        retrieved_block = dao.get_block_by_index(sample_block.index)
        assert retrieved_block.hash == sample_block.hash
        
    def test_block_retrieval(self, test_database):
        """Test block retrieval from database"""
        dao = BlockDAO()
        
        # Test getting latest block
        latest = dao.get_latest_block()
        assert latest is not None
        
        # Test getting by hash
        block_by_hash = dao.get_block_by_hash(latest.hash)
        assert block_by_hash.index == latest.index
        
    def test_blockchain_height(self, test_database):
        """Test blockchain height calculation"""
        dao = BlockDAO()
        
        height = dao.get_blockchain_height()
        assert height >= 0
        
    @pytest.mark.performance
    def test_bulk_block_operations(self, test_database, benchmark):
        """Benchmark bulk block operations"""
        dao = BlockDAO()
        
        def bulk_insert_blocks():
            blocks = [create_test_block(i) for i in range(100)]
            return dao.bulk_insert_blocks(blocks)
            
        result = benchmark(bulk_insert_blocks)
        assert result is True
```

### **Phase 3: Integration Testing (Week 5-6)**

#### **3.1 Mining Integration Tests**
```python
# tests/integration/mining/test_mining_flow.py
import pytest
import time
import requests
from src.clients.mining_client import MiningClient
from src.nodes.network_node import NetworkNode

@pytest.mark.integration
@pytest.mark.slow
class TestMiningFlow:
    def test_complete_mining_cycle(self, test_network_node, test_wallet):
        """Test complete mining cycle from template to block submission"""
        # Setup mining client
        mining_client = MiningClient(
            wallet_address=test_wallet.address,
            node_url="http://localhost:5000"
        )
        
        # Request mining template
        template = mining_client.get_mining_template()
        assert template is not None
        assert len(template.transactions) >= 1  # Coinbase transaction
        
        # Mine block (with low difficulty for testing)
        mined_block = mining_client.mine_block(template, timeout=10)
        assert mined_block is not None
        assert mined_block.nonce > 0
        
        # Submit block
        submission_result = mining_client.submit_block(mined_block)
        assert submission_result is True
        
        # Verify block was added to blockchain
        time.sleep(1)  # Allow for processing
        blockchain_status = requests.get("http://localhost:5000/status").json()
        assert blockchain_status["blockchain_length"] > 0
        
    def test_multi_node_mining_competition(self, test_multi_node_network):
        """Test mining competition between multiple nodes"""
        nodes = test_multi_node_network
        miners = []
        
        # Start miners on different nodes
        for i, node in enumerate(nodes):
            mining_client = MiningClient(
                wallet_address=f"test_miner_{i}",
                node_url=f"http://localhost:{5000 + i}"
            )
            miners.append(mining_client)
        
        # Run mining competition
        start_time = time.time()
        results = []
        
        while time.time() - start_time < 30:  # 30 second competition
            for miner in miners:
                template = miner.get_mining_template()
                if template:
                    # Quick mining attempt (1 second timeout)
                    block = miner.mine_block(template, timeout=1)
                    if block:
                        success = miner.submit_block(block)
                        if success:
                            results.append({
                                'miner': miner.wallet_address,
                                'block': block,
                                'timestamp': time.time()
                            })
            
            time.sleep(0.1)  # Brief pause
        
        assert len(results) > 0, "No blocks mined during competition"
        
        # Verify all nodes have same blockchain
        chain_lengths = []
        for node in nodes:
            status = requests.get(f"http://localhost:{node.port}/status").json()
            chain_lengths.append(status["blockchain_length"])
        
        assert len(set(chain_lengths)) == 1, "Blockchain sync failed"
```

#### **3.2 Transaction Flow Tests**
```python
# tests/integration/transactions/test_transaction_flow.py
import pytest
import time
from src.clients.wallet_client import WalletClient

@pytest.mark.integration
class TestTransactionFlow:
    def test_wallet_to_wallet_transfer(self, test_network_node, funded_wallet, empty_wallet):
        """Test complete wallet-to-wallet transaction"""
        sender = WalletClient(funded_wallet.filename)
        receiver = WalletClient(empty_wallet.filename)
        
        # Record initial balances
        initial_sender_balance = sender.get_balance()
        initial_receiver_balance = receiver.get_balance()
        
        assert initial_sender_balance > 10  # Ensure sufficient funds
        assert initial_receiver_balance == 0
        
        # Send transaction
        transfer_amount = 5.0
        transaction_fee = 0.1
        
        success = sender.send_transaction(
            to_address=receiver.address,
            amount=transfer_amount,
            fee=transaction_fee
        )
        assert success is True
        
        # Wait for transaction processing and mining
        time.sleep(5)
        
        # Verify balances updated
        final_sender_balance = sender.get_balance()
        final_receiver_balance = receiver.get_balance()
        
        expected_sender_balance = initial_sender_balance - transfer_amount - transaction_fee
        
        assert abs(final_sender_balance - expected_sender_balance) < 0.001
        assert abs(final_receiver_balance - transfer_amount) < 0.001
        
    def test_transaction_validation(self, test_network_node, empty_wallet):
        """Test transaction validation and rejection"""
        sender = WalletClient(empty_wallet.filename)
        
        # Attempt to send more than balance
        success = sender.send_transaction(
            to_address="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            amount=100.0,
            fee=0.1
        )
        assert success is False  # Should fail due to insufficient funds
        
    def test_batch_transactions(self, test_network_node, funded_wallet):
        """Test batch transaction processing"""
        sender = WalletClient(funded_wallet.filename)
        recipients = [
            ("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", 1.0),
            ("171SFKyrSm3n1GLXkLcCtQWTm1ZRVNvEB7", 1.5),
            ("18NDhHYAa3bx3jAZkc7HZf3vKr1JrwVXG3", 2.0)
        ]
        
        initial_balance = sender.get_balance()
        total_sent = sum(amount for _, amount in recipients)
        total_fees = len(recipients) * 0.1
        
        # Send multiple transactions
        for address, amount in recipients:
            success = sender.send_transaction(address, amount, 0.1)
            assert success is True
            time.sleep(1)  # Brief delay between transactions
        
        # Wait for all transactions to process
        time.sleep(10)
        
        final_balance = sender.get_balance()
        expected_balance = initial_balance - total_sent - total_fees
        
        assert abs(final_balance - expected_balance) < 0.01
```

### **Phase 4: Performance Testing (Week 7)**

#### **4.1 Mining Performance Tests**
```python
# tests/performance/test_mining_performance.py
import pytest
import time
import multiprocessing
from src.clients.mining_client import MiningClient

@pytest.mark.performance
class TestMiningPerformance:
    @pytest.mark.benchmark(group="hash_rates")
    def test_single_core_hash_rate(self, benchmark, test_network_node):
        """Benchmark single-core mining hash rate"""
        mining_client = MiningClient(
            wallet_address="test_miner",
            node_url="http://localhost:5000",
            workers=1
        )
        
        def mine_for_duration():
            return mining_client.mine_for_duration(seconds=5)
        
        result = benchmark(mine_for_duration)
        assert result["hashes"] > 0
        
    @pytest.mark.benchmark(group="hash_rates")
    def test_multi_core_hash_rate(self, benchmark, test_network_node):
        """Benchmark multi-core mining hash rate"""
        cpu_cores = multiprocessing.cpu_count()
        mining_client = MiningClient(
            wallet_address="test_miner",
            node_url="http://localhost:5000",
            workers=cpu_cores
        )
        
        def mine_for_duration():
            return mining_client.mine_for_duration(seconds=5)
        
        result = benchmark(mine_for_duration)
        assert result["hashes"] > 0
        
    def test_hash_rate_scaling(self, test_network_node):
        """Test hash rate scaling with worker count"""
        results = {}
        worker_counts = [1, 2, 4, multiprocessing.cpu_count()]
        
        for workers in worker_counts:
            mining_client = MiningClient(
                wallet_address="test_miner",
                node_url="http://localhost:5000",
                workers=workers
            )
            
            start_time = time.time()
            result = mining_client.mine_for_duration(seconds=10)
            duration = time.time() - start_time
            
            hash_rate = result["hashes"] / duration
            results[workers] = hash_rate
            
        # Verify scaling efficiency
        single_core_rate = results[1]
        for workers, rate in results.items():
            if workers > 1:
                efficiency = rate / (single_core_rate * workers)
                assert efficiency > 0.5, f"Poor scaling efficiency: {efficiency:.2f}"
```

#### **4.2 Database Performance Tests**
```python
# tests/performance/test_database_performance.py
import pytest
import time
from src.data.block_dao import BlockDAO
from src.data.transaction_dao import TransactionDAO

@pytest.mark.performance
@pytest.mark.database
class TestDatabasePerformance:
    @pytest.mark.benchmark(group="database_ops")
    def test_block_insertion_performance(self, benchmark, test_database):
        """Benchmark block insertion performance"""
        dao = BlockDAO()
        
        def insert_test_block():
            block = create_test_block()
            return dao.insert_block(block)
        
        result = benchmark(insert_test_block)
        assert result is True
        
    @pytest.mark.benchmark(group="database_ops")
    def test_transaction_query_performance(self, benchmark, test_database):
        """Benchmark transaction query performance"""
        dao = TransactionDAO()
        
        # Insert test transactions first
        for i in range(1000):
            tx = create_test_transaction()
            dao.insert_transaction(tx)
        
        def query_transactions():
            return dao.get_transactions_by_address("test_address")
        
        result = benchmark(query_transactions)
        assert len(result) >= 0
        
    def test_database_concurrency(self, test_database):
        """Test database performance under concurrent load"""
        import threading
        import queue
        
        dao = BlockDAO()
        results = queue.Queue()
        
        def worker():
            try:
                for _ in range(10):
                    block = create_test_block()
                    success = dao.insert_block(block)
                    results.put(success)
            except Exception as e:
                results.put(e)
        
        # Start multiple worker threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify all operations succeeded
        while not results.empty():
            result = results.get()
            assert result is True or isinstance(result, bool)
```

### **Phase 5: End-to-End Testing (Week 8)**

#### **5.1 Full Network Tests**
```python
# tests/e2e/test_full_network.py
import pytest
import time
import subprocess
import requests
from typing import List, Dict

@pytest.mark.e2e
@pytest.mark.slow
class TestFullNetwork:
    def test_complete_network_lifecycle(self):
        """Test complete network startup, operation, and shutdown"""
        network_processes = []
        
        try:
            # Start multiple nodes
            for i in range(3):
                port = 5000 + i
                p2p_port = 8000 + i
                
                cmd = [
                    "python", "src/nodes/network_node.py",
                    "--node-id", f"test_node_{i}",
                    "--api-port", str(port),
                    "--p2p-port", str(p2p_port)
                ]
                
                if i > 0:
                    cmd.extend(["--bootstrap-nodes", "http://localhost:5000"])
                
                process = subprocess.Popen(cmd)
                network_processes.append(process)
                time.sleep(2)  # Allow node to start
            
            # Wait for network to stabilize
            time.sleep(10)
            
            # Verify all nodes are responding
            for i in range(3):
                response = requests.get(f"http://localhost:{5000 + i}/status")
                assert response.status_code == 200
                
                status = response.json()
                assert status["node_id"] == f"test_node_{i}"
                assert status["active_peers"] >= 1 if i > 0 else 0
            
            # Start mining on one node
            mining_process = subprocess.Popen([
                "python", "src/clients/mining_client.py",
                "--wallet", "test_miner",
                "--node", "http://localhost:5000",
                "--timeout", "30"
            ])
            
            # Let mining run for a while
            time.sleep(30)
            
            # Verify blocks were mined and synchronized
            chain_lengths = []
            for i in range(3):
                response = requests.get(f"http://localhost:{5000 + i}/status")
                status = response.json()
                chain_lengths.append(status["blockchain_length"])
            
            assert max(chain_lengths) > 0, "No blocks were mined"
            assert len(set(chain_lengths)) == 1, "Blockchain not synchronized"
            
            mining_process.terminate()
            mining_process.wait()
            
        finally:
            # Clean shutdown
            for process in network_processes:
                process.terminate()
                process.wait()
    
    def test_network_resilience(self):
        """Test network resilience to node failures"""
        # Implementation for network resilience testing
        pass
        
    def test_transaction_propagation(self):
        """Test transaction propagation across network"""
        # Implementation for transaction propagation testing
        pass
```

### **Phase 6: Continuous Integration (Week 9-10)**

#### **6.1 GitHub Actions Configuration**
```yaml
# .github/workflows/test.yml
name: ChainCore Test Suite

on:
  push:
    branches: [ main, tier-1 ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: testpassword
          POSTGRES_DB: chaincore_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Setup test database
      run: |
        export DATABASE_URL="postgresql://postgres:testpassword@localhost:5432/chaincore_test"
        python -c "from src.data.simple_connection import init_simple_database; init_simple_database()"
    
    - name: Run unit tests
      run: |
        pytest tests/unit/ -v --cov=src --cov-report=xml
    
    - name: Run integration tests
      run: |
        pytest tests/integration/ -v -m "not slow"
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true

  performance:
    runs-on: ubuntu-latest
    needs: test
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run performance tests
      run: |
        pytest tests/performance/ -v --benchmark-json=benchmark.json
    
    - name: Store benchmark results
      uses: benchmark-action/github-action-benchmark@v1
      with:
        tool: 'pytest'
        output-file-path: benchmark.json
        github-token: ${{ secrets.GITHUB_TOKEN }}
        auto-push: true

  e2e:
    runs-on: ubuntu-latest
    needs: [test, performance]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run end-to-end tests
      run: |
        pytest tests/e2e/ -v --timeout=300
```

### **Phase 7: Test Utilities & Tools (Week 10)**

#### **7.1 Test Data Factories**
```python
# tests/fixtures/factories.py
import factory
import secrets
from src.core.block import Block
from src.core.bitcoin_transaction import Transaction, TransactionInput, TransactionOutput
from src.crypto.ecdsa_crypto import ECDSAKeyPair

class WalletFactory(factory.Factory):
    class Meta:
        model = dict
    
    private_key = factory.LazyFunction(lambda: secrets.token_hex(32))
    
    @factory.post_generation
    def create_keypair(obj, create, extracted, **kwargs):
        keypair = ECDSAKeyPair()
        obj['keypair'] = keypair
        obj['address'] = keypair.get_address()
        obj['filename'] = f"test_wallet_{secrets.token_hex(4)}.json"

class TransactionOutputFactory(factory.Factory):
    class Meta:
        model = TransactionOutput
    
    amount = factory.Faker('pydecimal', left_digits=3, right_digits=8, positive=True)
    recipient_address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"

class TransactionInputFactory(factory.Factory):
    class Meta:
        model = TransactionInput
    
    tx_id = factory.LazyFunction(lambda: secrets.token_hex(32))
    output_index = factory.Faker('random_int', min=0, max=10)

class TransactionFactory(factory.Factory):
    class Meta:
        model = Transaction
    
    @factory.post_generation
    def add_inputs_outputs(obj, create, extracted, **kwargs):
        # Add random inputs and outputs
        for _ in range(factory.Faker('random_int', min=1, max=3).generate()):
            obj.add_input(
                factory.LazyFunction(lambda: secrets.token_hex(32)).generate(),
                factory.Faker('random_int', min=0, max=10).generate()
            )
        
        for _ in range(factory.Faker('random_int', min=1, max=5).generate()):
            obj.add_output(
                factory.Faker('pydecimal', left_digits=2, right_digits=8, positive=True).generate(),
                "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
            )

class BlockFactory(factory.Factory):
    class Meta:
        model = Block
    
    index = factory.Sequence(lambda n: n)
    previous_hash = factory.LazyFunction(lambda: secrets.token_hex(32))
    nonce = factory.Faker('random_int', min=0, max=1000000)
    
    @factory.post_generation
    def add_transactions(obj, create, extracted, **kwargs):
        if extracted:
            obj.transactions = extracted
        else:
            # Add 1-5 random transactions
            obj.transactions = [
                TransactionFactory() 
                for _ in range(factory.Faker('random_int', min=1, max=5).generate())
            ]
```

#### **7.2 Testing Utilities**
```python
# tests/fixtures/utils.py
import time
import requests
import subprocess
from typing import List, Optional, Dict, Any

class NetworkTestHelper:
    @staticmethod
    def wait_for_node_ready(port: int, timeout: int = 30) -> bool:
        """Wait for a network node to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"http://localhost:{port}/status", timeout=1)
                if response.status_code == 200:
                    return True
            except:
                pass
            time.sleep(0.5)
        return False
    
    @staticmethod
    def start_test_nodes(count: int) -> List[subprocess.Popen]:
        """Start multiple test nodes"""
        processes = []
        for i in range(count):
            port = 5000 + i
            p2p_port = 8000 + i
            
            cmd = [
                "python", "src/nodes/network_node.py",
                "--node-id", f"test_node_{i}",
                "--api-port", str(port),
                "--p2p-port", str(p2p_port)
            ]
            
            if i > 0:
                cmd.extend(["--bootstrap-nodes", "http://localhost:5000"])
            
            process = subprocess.Popen(cmd)
            processes.append(process)
            
            # Wait for node to be ready
            if not NetworkTestHelper.wait_for_node_ready(port):
                raise Exception(f"Node on port {port} failed to start")
        
        return processes
    
    @staticmethod
    def stop_test_nodes(processes: List[subprocess.Popen]):
        """Stop test nodes cleanly"""
        for process in processes:
            process.terminate()
        
        for process in processes:
            process.wait(timeout=10)

class DatabaseTestHelper:
    @staticmethod
    def clean_test_database():
        """Clean test database between tests"""
        from src.data.simple_connection import get_connection
        
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("TRUNCATE blocks, transactions, utxos, nodes, mining_stats, address_balances CASCADE")
                conn.commit()
    
    @staticmethod
    def seed_test_data(blocks: int = 5, transactions_per_block: int = 3):
        """Seed database with test data"""
        from tests.fixtures.factories import BlockFactory, TransactionFactory
        from src.data.block_dao import BlockDAO
        
        dao = BlockDAO()
        
        for i in range(blocks):
            transactions = [TransactionFactory() for _ in range(transactions_per_block)]
            block = BlockFactory(index=i, transactions=transactions)
            dao.insert_block(block)

class MiningTestHelper:
    @staticmethod
    def mine_test_block(node_url: str = "http://localhost:5000", timeout: int = 10) -> Optional[Dict[Any, Any]]:
        """Mine a single test block"""
        try:
            # Get mining template
            response = requests.post(
                f"{node_url}/mine_block",
                json={"miner_address": "test_miner"},
                timeout=timeout
            )
            
            if response.status_code == 200:
                return response.json()
        except:
            pass
        
        return None
    
    @staticmethod
    def wait_for_blocks(node_url: str, target_height: int, timeout: int = 60) -> bool:
        """Wait for blockchain to reach target height"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{node_url}/status", timeout=1)
                if response.status_code == 200:
                    status = response.json()
                    if status.get("blockchain_length", 0) >= target_height:
                        return True
            except:
                pass
            
            time.sleep(1)
        
        return False
```

---

## 📊 **Testing Metrics & Reporting**

### **Coverage Targets**
- **Unit Tests**: >90% code coverage
- **Integration Tests**: >80% feature coverage
- **E2E Tests**: 100% critical path coverage

### **Performance Benchmarks**
- **Mining Hash Rate**: Track improvements over time
- **Database Operations**: <10ms for single operations
- **Network Latency**: <100ms for local network operations
- **Memory Usage**: <512MB for single node

### **Quality Gates**
- All tests must pass before merge
- Coverage must not decrease
- Performance regressions >10% require review
- Security tests must pass

---

## 🚀 **Implementation Commands**

### **Immediate Actions (Next 2 weeks)**

```bash
# 1. Install additional testing dependencies
pip install pytest-cov pytest-benchmark pytest-html pytest-xdist pytest-postgresql httpx locust factory-boy freezegun responses

# 2. Create test structure
mkdir -p tests/{unit,integration,performance,e2e,fixtures,reports}/{crypto,core,data,network,mining,blockchain}/

# 3. Create configuration files
touch pytest.ini tests/conftest.py tests/fixtures/{__init__.py,factories.py,utils.py}

# 4. Set up GitHub Actions
mkdir -p .github/workflows/
# Create test.yml workflow file

# 5. Run existing tests to baseline
python -m pytest tests/ --cov=src --cov-report=html

# 6. Create first unit test
# Start with crypto module as it's most isolated

# 7. Set up CI/CD pipeline
# Configure GitHub Actions for automated testing
```

### **Migration Plan from Current Tests**

1. **Categorize existing tests** into unit/integration/performance/e2e
2. **Refactor test scripts** to use pytest framework
3. **Create shared fixtures** for common test data
4. **Implement test utilities** for repeated patterns
5. **Add performance benchmarking** to existing tests
6. **Create comprehensive test suite** covering all components

---

## 🎯 **Success Criteria**

Your testing framework will be successful when you achieve:

✅ **Automated Test Execution**: All tests run automatically on code changes  
✅ **Comprehensive Coverage**: >90% code coverage with meaningful tests  
✅ **Performance Tracking**: Benchmark results tracked over time  
✅ **Quality Gates**: Prevent regressions through automated checks  
✅ **Developer Productivity**: Easy to write and maintain tests  
✅ **CI/CD Integration**: Seamless integration with development workflow  

This comprehensive testing setup will transform your ChainCore project from ad-hoc testing scripts into a production-ready testing ecosystem that ensures code quality, performance, and reliability at every stage of development.