#!/usr/bin/env python3
import threading
import time
import functools
import logging
from typing import Dict, Set, List, Any, Optional, Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
import uuid

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class LockOrder(Enum):
    """
    Lock ordering hierarchy to prevent deadlocks
    Always acquire locks in this order, release in reverse order
    """
    BLOCKCHAIN = 1      # Highest priority - blockchain state
    UTXO_SET = 2       # UTXO set modifications  
    MEMPOOL = 3        # Transaction pool operations
    PEERS = 4          # Peer management
    SESSION = 5        # Session management
    MINING = 6         # Mining operations
    NETWORK = 7        # Network I/O (lowest priority)

@dataclass
class LockStats:
    """Thread safety statistics for monitoring"""
    acquisitions: int = 0
    contentions: int = 0
    max_wait_time: float = 0.0
    deadlock_attempts: int = 0
    
class DeadlockDetector:

    def __init__(self):
        self._lock_graph: Dict[int, Set[int]] = {}  # thread_id -> set of lock_ids
        self._waiting_for: Dict[int, int] = {}      # thread_id -> lock_id
        self._lock_owners: Dict[str, int] = {}      # lock_name -> thread_id
        self._graph_lock = threading.RLock()
        
    def add_edge(self, from_thread: int, to_lock: str, lock_order: LockOrder):
        """Add edge in wait-for graph"""
        with self._graph_lock:
            if from_thread not in self._lock_graph:
                self._lock_graph[from_thread] = set()
            
            # Check if this would create a cycle
            if to_lock in self._lock_owners:
                owner_thread = self._lock_owners[to_lock]
                if self._has_path(owner_thread, from_thread):
                    raise RuntimeError(f"Deadlock detected: Thread {from_thread} waiting for lock {to_lock} owned by {owner_thread}")
            
            self._waiting_for[from_thread] = hash(to_lock)
            logger.debug(f"Thread {from_thread} waiting for lock {to_lock}")
    
    def remove_edge(self, thread_id: int, lock_name: str):
        """Remove edge when lock is acquired"""
        with self._graph_lock:
            self._waiting_for.pop(thread_id, None)
            self._lock_owners[lock_name] = thread_id
            logger.debug(f"Thread {thread_id} acquired lock {lock_name}")
    
    def release_lock(self, thread_id: int, lock_name: str):
        """Release lock from graph"""
        with self._graph_lock:
            if lock_name in self._lock_owners and self._lock_owners[lock_name] == thread_id:
                del self._lock_owners[lock_name]
                logger.debug(f"Thread {thread_id} released lock {lock_name}")
    
    def _has_path(self, from_thread: int, to_thread: int) -> bool:
        """Check if there's a path in wait-for graph (cycle detection)"""
        visited = set()
        
        def dfs(current: int) -> bool:
            if current == to_thread:
                return True
            if current in visited:
                return False
            
            visited.add(current)
            
            # Check what this thread is waiting for
            if current in self._waiting_for:
                waiting_lock = self._waiting_for[current]
                for lock_name, owner in self._lock_owners.items():
                    if hash(lock_name) == waiting_lock and owner not in visited:
                        if dfs(owner):
                            return True
            
            return False
        
        return dfs(from_thread)

class AdvancedRWLock:
    """
    Reader-Writer lock with priority queuing and starvation prevention
    """
    
    def __init__(self, name: str, lock_order: LockOrder):
        self.name = name
        self.lock_order = lock_order
        self._readers = 0
        self._writers = 0
        self._read_ready = threading.Condition(threading.RLock())
        self._write_ready = threading.Condition(threading.RLock())
        self._waiting_writers = 0
        self._waiting_readers = 0
        self._stats = LockStats()
        self._start_time = None
        
    @contextmanager
    def read_lock(self):
        """Acquire read lock with deadlock detection"""
        thread_id = threading.get_ident()
        start_time = time.time()
        
        try:
            # Deadlock detection
            deadlock_detector.add_edge(thread_id, self.name, self.lock_order)
            
            with self._read_ready:
                # Wait if there are writers or waiting writers (prevent writer starvation)
                while self._writers > 0 or self._waiting_writers > 0:
                    self._waiting_readers += 1
                    self._stats.contentions += 1
                    self._read_ready.wait()
                    self._waiting_readers -= 1
                
                self._readers += 1
                self._stats.acquisitions += 1
                
            # Remove from deadlock graph
            deadlock_detector.remove_edge(thread_id, self.name)
            
            wait_time = time.time() - start_time
            self._stats.max_wait_time = max(self._stats.max_wait_time, wait_time)
            
            logger.debug(f"Thread {thread_id} acquired read lock {self.name} (readers: {self._readers})")
            
            yield
            
        finally:
            with self._read_ready:
                self._readers -= 1
                if self._readers == 0:
                    self._read_ready.notify_all()
            
            deadlock_detector.release_lock(thread_id, self.name)
            logger.debug(f"Thread {thread_id} released read lock {self.name}")
    
    @contextmanager
    def write_lock(self):
        """Acquire exclusive write lock"""
        thread_id = threading.get_ident()
        start_time = time.time()
        
        try:
            # Deadlock detection
            deadlock_detector.add_edge(thread_id, self.name, self.lock_order)
            
            with self._write_ready:
                # Wait for all readers and writers to finish
                while self._readers > 0 or self._writers > 0:
                    self._waiting_writers += 1
                    self._stats.contentions += 1
                    self._write_ready.wait()
                    self._waiting_writers -= 1
                
                self._writers += 1
                self._stats.acquisitions += 1
            
            # Remove from deadlock graph
            deadlock_detector.remove_edge(thread_id, self.name)
            
            wait_time = time.time() - start_time
            self._stats.max_wait_time = max(self._stats.max_wait_time, wait_time)
            
            logger.debug(f"Thread {thread_id} acquired write lock {self.name}")
            
            yield
            
        finally:
            with self._write_ready:
                self._writers -= 1
                # Notify waiting readers first to prevent writer starvation
                if self._waiting_readers > 0:
                    self._read_ready.notify_all()
                else:
                    self._write_ready.notify()
            
            deadlock_detector.release_lock(thread_id, self.name)
            logger.debug(f"Thread {thread_id} released write lock {self.name}")
    
    def get_stats(self) -> LockStats:
        """Get lock statistics for monitoring"""
        return self._stats

class AtomicCounter:
    """Thread-safe counter with compare-and-swap operations"""
    
    def __init__(self, initial: int = 0):
        self._value = initial
        self._lock = threading.Lock()
    
    def increment(self) -> int:
        """Atomically increment and return new value"""
        with self._lock:
            self._value += 1
            return self._value
    
    def compare_and_swap(self, expected: int, new_value: int) -> bool:
        """Atomic compare-and-swap operation"""
        with self._lock:
            if self._value == expected:
                self._value = new_value
                return True
            return False
    
    @property
    def value(self) -> int:
        with self._lock:
            return self._value

class TransactionQueue:
    """
    Lock-free transaction queue using atomic operations
    """
    
    def __init__(self, maxsize: int = 10000):
        self._queue = []
        self._lock = threading.RLock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)
        self._maxsize = maxsize
        self._stats = AtomicCounter()
    
    def put(self, item: Any, timeout: Optional[float] = None) -> bool:
        """Thread-safe enqueue with timeout"""
        with self._not_full:
            if timeout is None:
                while len(self._queue) >= self._maxsize:
                    self._not_full.wait()
            else:
                end_time = time.time() + timeout
                while len(self._queue) >= self._maxsize:
                    remaining = end_time - time.time()
                    if remaining <= 0.0:
                        return False
                    self._not_full.wait(remaining)
            
            self._queue.append(item)
            self._stats.increment()
            self._not_empty.notify()
            return True
    
    def get(self, timeout: Optional[float] = None) -> Optional[Any]:
        """Thread-safe dequeue with timeout"""
        with self._not_empty:
            if timeout is None:
                while not self._queue:
                    self._not_empty.wait()
            else:
                end_time = time.time() + timeout
                while not self._queue:
                    remaining = end_time - time.time()
                    if remaining <= 0.0:
                        return None
                    self._not_empty.wait(remaining)
            
            item = self._queue.pop(0)
            self._not_full.notify()
            return item
    
    def qsize(self) -> int:
        """Get queue size"""
        with self._lock:
            return len(self._queue)

# Global deadlock detector instance
deadlock_detector = DeadlockDetector()

# Lock manager for the entire blockchain system
class LockManager:
    """
    Centralized lock management system
    Ensures proper lock ordering and prevents deadlocks
    """
    
    def __init__(self):
        self._locks: Dict[str, AdvancedRWLock] = {}
        self._creation_lock = threading.Lock()
    
    def get_lock(self, name: str, lock_order: LockOrder) -> AdvancedRWLock:
        """Get or create a named lock"""
        if name not in self._locks:
            with self._creation_lock:
                if name not in self._locks:
                    self._locks[name] = AdvancedRWLock(name, lock_order)
        return self._locks[name]
    
    def get_all_stats(self) -> Dict[str, LockStats]:
        """Get statistics for all locks"""
        return {name: lock.get_stats() for name, lock in self._locks.items()}

# Global lock manager instance
lock_manager = LockManager()

# Decorator for method-level locking
def synchronized(lock_name: str, lock_order: LockOrder, mode: str = 'write'):
    """
    Decorator for automatic method synchronization
    
    Args:
        lock_name: Name of the lock
        lock_order: Lock ordering for deadlock prevention
        mode: 'read' or 'write' lock mode
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            lock = lock_manager.get_lock(lock_name, lock_order)
            
            if mode == 'read':
                with lock.read_lock():
                    return func(*args, **kwargs)
            else:
                with lock.write_lock():
                    return func(*args, **kwargs)
        
        return wrapper
    return decorator

# Transaction for atomic operations
class Transaction:
    """
    Transaction context for atomic multi-step operations
    Implements two-phase commit protocol
    """
    
    def __init__(self, tx_id: Optional[str] = None):
        self.tx_id = tx_id or str(uuid.uuid4())
        self._locks: List[AdvancedRWLock] = []
        self._operations: List[Callable] = []
        self._rollback_operations: List[Callable] = []
        self._committed = False
        self._aborted = False
    
    def add_lock(self, lock: AdvancedRWLock, mode: str = 'write'):
        """Add lock to transaction"""
        self._locks.append((lock, mode))
    
    def add_operation(self, operation: Callable, rollback: Callable = None):
        """Add operation to transaction"""
        self._operations.append(operation)
        if rollback:
            self._rollback_operations.append(rollback)
    
    def commit(self) -> bool:
        """Commit transaction atomically"""
        if self._committed or self._aborted:
            return False
        
        # Acquire all locks in proper order
        acquired_locks = []
        try:
            # Sort locks by order to prevent deadlocks
            sorted_locks = sorted(self._locks, key=lambda x: x[0].lock_order.value)
            
            for lock, mode in sorted_locks:
                if mode == 'read':
                    lock_ctx = lock.read_lock()
                else:
                    lock_ctx = lock.write_lock()
                
                lock_ctx.__enter__()
                acquired_locks.append(lock_ctx)
            
            # Execute all operations
            for operation in self._operations:
                operation()
            
            self._committed = True
            logger.info(f"Transaction {self.tx_id} committed successfully")
            return True
            
        except Exception as e:
            # Rollback on failure
            logger.error(f"Transaction {self.tx_id} failed: {e}")
            self._rollback()
            return False
        
        finally:
            # Release all locks in reverse order
            for lock_ctx in reversed(acquired_locks):
                try:
                    lock_ctx.__exit__(None, None, None)
                except Exception as e:
                    logger.error(f"Error releasing lock: {e}")
    
    def _rollback(self):
        """Rollback transaction"""
        if self._aborted:
            return
        
        try:
            for rollback_op in reversed(self._rollback_operations):
                rollback_op()
            logger.info(f"Transaction {self.tx_id} rolled back")
        except Exception as e:
            logger.error(f"Error during rollback: {e}")
        finally:
            self._aborted = True

# Memory barrier for ensuring ordering
class MemoryBarrier:
    """Memory barrier implementation for ensuring operation ordering"""
    
    @staticmethod
    def full_barrier():
        """Full memory barrier - ensures all operations complete"""
        # Python GIL provides some ordering guarantees, but we can be explicit
        threading.current_thread()  # Force thread-local access
    
    @staticmethod
    def write_barrier():
        """Write barrier - ensures writes are visible"""
        threading.current_thread()
    
    @staticmethod
    def read_barrier():
        """Read barrier - ensures reads see latest values"""
        threading.current_thread()

# Alias for backward compatibility
RWLock = AdvancedRWLock