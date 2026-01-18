"""
Unit tests for Thread Safety primitives.
Tests lock ordering, atomic operations, and basic concurrency patterns.
"""
import pytest
import threading
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.concurrency.thread_safety import (
    LockOrder,
    AdvancedRWLock,
    AtomicCounter,
    TransactionQueue,
    LockStats
)


class TestLockOrder:
    """Test lock ordering hierarchy for deadlock prevention"""
    
    def test_lock_order_hierarchy_exists(self):
        """Lock orders should have distinct priorities"""
        assert LockOrder.BLOCKCHAIN.value < LockOrder.UTXO_SET.value
        assert LockOrder.UTXO_SET.value < LockOrder.MEMPOOL.value
        assert LockOrder.MEMPOOL.value < LockOrder.PEERS.value
        
    def test_all_lock_orders_unique(self):
        """All lock order values must be unique to prevent ambiguity"""
        values = [order.value for order in LockOrder]
        assert len(values) == len(set(values))
        
    def test_lock_order_is_enum(self):
        """Lock order should be proper enum for type safety"""
        assert hasattr(LockOrder, 'BLOCKCHAIN')
        assert hasattr(LockOrder, 'UTXO_SET')
        assert hasattr(LockOrder, 'MEMPOOL')
        assert hasattr(LockOrder, 'MINING')


class TestAdvancedRWLock:
    """Test Reader-Writer Lock implementation"""
    
    def test_read_lock_single_thread(self):
        """Single thread can acquire and release read lock"""
        lock = AdvancedRWLock("test_read", LockOrder.BLOCKCHAIN)
        
        with lock.read_lock():
            assert lock._readers == 1
        assert lock._readers == 0
        
    def test_write_lock_single_thread(self):
        """Single thread can acquire and release write lock"""
        lock = AdvancedRWLock("test_write", LockOrder.BLOCKCHAIN)
        
        with lock.write_lock():
            assert lock._writers == 1
        assert lock._writers == 0
        
    def test_lock_has_name(self):
        """Lock should store its name for debugging"""
        lock = AdvancedRWLock("my_named_lock", LockOrder.MEMPOOL)
        assert lock.name == "my_named_lock"
        
    def test_lock_has_order(self):
        """Lock should store its order for deadlock prevention"""
        lock = AdvancedRWLock("ordered_lock", LockOrder.UTXO_SET)
        assert lock.lock_order == LockOrder.UTXO_SET
        
    def test_stats_tracking(self):
        """Lock should track acquisition stats"""
        lock = AdvancedRWLock("stats_lock", LockOrder.BLOCKCHAIN)
        
        for _ in range(3):
            with lock.read_lock():
                pass
        for _ in range(2):
            with lock.write_lock():
                pass
                
        stats = lock.get_stats()
        assert stats.acquisitions == 5


class TestAtomicCounter:
    """Test atomic counter for thread-safe counting"""
    
    def test_initial_value_custom(self):
        """Counter starts at specified value"""
        counter = AtomicCounter(42)
        assert counter.value == 42
        
    def test_initial_value_default(self):
        """Counter defaults to 0"""
        counter = AtomicCounter()
        assert counter.value == 0
        
    def test_increment_returns_new_value(self):
        """Increment returns the new value"""
        counter = AtomicCounter(5)
        result = counter.increment()
        assert result == 6
        assert counter.value == 6
        
    def test_multiple_increments(self):
        """Multiple increments accumulate correctly"""
        counter = AtomicCounter(0)
        for i in range(10):
            counter.increment()
        assert counter.value == 10
        
    def test_cas_success(self):
        """Compare-and-swap succeeds when expected matches actual"""
        counter = AtomicCounter(100)
        success = counter.compare_and_swap(100, 200)
        assert success is True
        assert counter.value == 200
        
    def test_cas_failure(self):
        """Compare-and-swap fails when expected doesn't match"""
        counter = AtomicCounter(100)
        success = counter.compare_and_swap(50, 200)  # Expected 50, actual 100
        assert success is False
        assert counter.value == 100  # Unchanged
        
    def test_cas_atomic_semantics(self):
        """CAS should be atomic - no partial updates"""
        counter = AtomicCounter(0)
        
        # First CAS should succeed
        assert counter.compare_and_swap(0, 1) is True
        
        # Second CAS with old expected should fail
        assert counter.compare_and_swap(0, 2) is False
        
        # Value should be from first CAS
        assert counter.value == 1


class TestTransactionQueue:
    """Test thread-safe transaction queue"""
    
    def test_put_increases_size(self):
        """Put should increase queue size"""
        queue = TransactionQueue()
        assert queue.qsize() == 0
        
        queue.put("tx1")
        assert queue.qsize() == 1
        
        queue.put("tx2")
        assert queue.qsize() == 2
        
    def test_get_decreases_size(self):
        """Get should decrease queue size"""
        queue = TransactionQueue()
        queue.put("tx1")
        queue.put("tx2")
        
        queue.get(timeout=0.1)
        assert queue.qsize() == 1
        
    def test_fifo_ordering(self):
        """Queue should maintain FIFO order"""
        queue = TransactionQueue()
        queue.put("first")
        queue.put("second")
        queue.put("third")
        
        assert queue.get(timeout=0.1) == "first"
        assert queue.get(timeout=0.1) == "second"
        assert queue.get(timeout=0.1) == "third"
        
    def test_get_timeout_on_empty(self):
        """Get on empty queue with timeout returns None"""
        queue = TransactionQueue()
        result = queue.get(timeout=0.01)
        assert result is None
        
    def test_queue_with_dict_items(self):
        """Queue should handle transaction-like dict objects"""
        queue = TransactionQueue()
        tx = {"tx_id": "abc123", "amount": 50.0, "to": "alice"}
        
        queue.put(tx)
        retrieved = queue.get(timeout=0.1)
        
        assert retrieved == tx
        assert retrieved["tx_id"] == "abc123"


class TestLockStats:
    """Test lock statistics tracking"""
    
    def test_stats_default_values(self):
        """Stats should initialize to zero"""
        stats = LockStats()
        assert stats.acquisitions == 0
        assert stats.contentions == 0
        assert stats.max_wait_time == 0.0
        assert stats.deadlock_attempts == 0
        
    def test_stats_is_dataclass(self):
        """Stats should be a proper dataclass"""
        stats = LockStats(acquisitions=5, contentions=2)
        assert stats.acquisitions == 5
        assert stats.contentions == 2


class TestConcurrentIncrements:
    """Test actual concurrent behavior"""
    
    def test_atomic_counter_thread_safety(self):
        """AtomicCounter should handle concurrent increments"""
        counter = AtomicCounter(0)
        num_threads = 5
        increments_per_thread = 100
        
        def increment_many():
            for _ in range(increments_per_thread):
                counter.increment()
                
        threads = [threading.Thread(target=increment_many) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        expected = num_threads * increments_per_thread
        assert counter.value == expected
        
    def test_queue_concurrent_put(self):
        """Queue should handle concurrent puts"""
        queue = TransactionQueue()
        num_threads = 5
        items_per_thread = 20
        
        def put_many(thread_id):
            for i in range(items_per_thread):
                queue.put(f"t{thread_id}_item{i}")
                
        threads = [threading.Thread(target=put_many, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        expected = num_threads * items_per_thread
        assert queue.qsize() == expected


class TestRWLockSemantics:
    """Test reader-writer lock semantics"""
    
    def test_multiple_sequential_reads(self):
        """Multiple sequential read acquisitions should work"""
        lock = AdvancedRWLock("seq_read", LockOrder.BLOCKCHAIN)
        
        for i in range(5):
            with lock.read_lock():
                assert lock._readers == 1
            assert lock._readers == 0
            
    def test_multiple_sequential_writes(self):
        """Multiple sequential write acquisitions should work"""
        lock = AdvancedRWLock("seq_write", LockOrder.BLOCKCHAIN)
        
        for i in range(5):
            with lock.write_lock():
                assert lock._writers == 1
            assert lock._writers == 0
            
    def test_read_then_write_sequential(self):
        """Read followed by write should work sequentially"""
        lock = AdvancedRWLock("rw_seq", LockOrder.BLOCKCHAIN)
        
        with lock.read_lock():
            assert lock._readers == 1
            
        with lock.write_lock():
            assert lock._writers == 1
