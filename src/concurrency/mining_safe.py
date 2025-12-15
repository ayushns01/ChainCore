#!/usr/bin/env python3
"""
Thread-Safe Mining System with Work Coordination
Enterprise-grade mining with duplicate prevention and work coordination
"""

import threading
import time
import hashlib
import logging
import queue
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from contextlib import contextmanager
import concurrent.futures

from .thread_safety import (
    LockManager, LockOrder, synchronized, AtomicCounter, 
    MemoryBarrier, lock_manager
)

logger = logging.getLogger(__name__)

@dataclass
class MiningWork:
    """Represents a unit of mining work"""
    block_template: dict
    target_difficulty: int
    start_nonce: int
    end_nonce: int
    miner_id: str
    timestamp: float = field(default_factory=time.time)

@dataclass
class MiningResult:
    """Result of mining operation"""
    success: bool
    block_hash: Optional[str] = None
    nonce: Optional[int] = None
    mining_time: float = 0.0
    hash_rate: float = 0.0
    miner_id: str = ""
    error_message: Optional[str] = None

class WorkCoordinator:
    """
    Coordinates mining work across multiple threads/processes
    Prevents duplicate work and manages nonce ranges
    """
    
    def __init__(self):
        self._current_work: Optional[dict] = None
        self._work_assignments: Dict[str, MiningWork] = {}
        self._completed_ranges: Set[Tuple[int, int]] = set()
        self._next_nonce = AtomicCounter()
        
        self._work_lock = lock_manager.get_lock("mining_work", LockOrder.MINING)
        self._assignment_lock = lock_manager.get_lock("work_assignment", LockOrder.MINING)
        
        # Statistics
        self._stats = {
            'work_units_assigned': AtomicCounter(),
            'work_units_completed': AtomicCounter(),
            'duplicate_work_prevented': AtomicCounter(),
            'work_conflicts': AtomicCounter()
        }
        
        logger.info("Work coordinator initialized")
    
    def _get_default_difficulty(self) -> int:
        """Get default difficulty from centralized configuration"""
        try:
            from ..config import BLOCKCHAIN_DIFFICULTY
            return BLOCKCHAIN_DIFFICULTY
        except ImportError:
            return 5  # Ultimate fallback
    
    @synchronized("mining_work", LockOrder.MINING, mode='write')
    def set_current_work(self, block_template: dict) -> bool:
        """Set new block template for mining"""
        # Check if this is actually new work
        if (self._current_work and 
            self._current_work.get('previous_hash') == block_template.get('previous_hash') and
            self._current_work.get('index') == block_template.get('index')):
            return False  # Same work already in progress
        
        # Reset for new work
        self._current_work = block_template.copy()
        self._work_assignments.clear()
        self._completed_ranges.clear()
        self._next_nonce = AtomicCounter()
        
        logger.info(f"New mining work set: block {block_template.get('index')}")
        return True
    
    @synchronized("work_assignment", LockOrder.MINING, mode='write') 
    def assign_work(self, miner_id: str, nonce_range: int = 100000) -> Optional[MiningWork]:
        """Assign work range to a miner"""
        if not self._current_work:
            return None
        
        start_nonce = self._next_nonce.value
        end_nonce = start_nonce + nonce_range
        
        # Check for overlap with completed ranges
        work_range = (start_nonce, end_nonce)
        if any(self._ranges_overlap(work_range, completed) for completed in self._completed_ranges):
            self._stats['duplicate_work_prevented'].increment()
            # Find next available range
            max_completed = max((r[1] for r in self._completed_ranges), default=0)
            start_nonce = max(max_completed + 1, self._next_nonce.value)
            end_nonce = start_nonce + nonce_range
        
        # Advance counter
        self._next_nonce = AtomicCounter(end_nonce)
        
        work = MiningWork(
            block_template=self._current_work.copy(),
            target_difficulty=self._current_work.get('target_difficulty', self._get_default_difficulty()),  # Dynamic default from network_node
            start_nonce=start_nonce,
            end_nonce=end_nonce,
            miner_id=miner_id
        )
        
        self._work_assignments[miner_id] = work
        self._stats['work_units_assigned'].increment()
        
        logger.debug(f"Work assigned to {miner_id}: nonces {start_nonce}-{end_nonce}")
        return work
    
    def _ranges_overlap(self, range1: Tuple[int, int], range2: Tuple[int, int]) -> bool:
        """Check if two nonce ranges overlap"""
        return range1[0] <= range2[1] and range2[0] <= range1[1]
    
    @synchronized("work_assignment", LockOrder.MINING, mode='write')
    def report_work_completed(self, miner_id: str, nonce_range: Tuple[int, int], found_solution: bool = False) -> bool:
        """Report completed work range"""
        if miner_id not in self._work_assignments:
            logger.warning(f"Unknown miner reporting work: {miner_id}")
            return False
        
        self._completed_ranges.add(nonce_range)
        self._stats['work_units_completed'].increment()
        
        # Clean up assignment
        del self._work_assignments[miner_id]
        
        if found_solution:
            logger.info(f"Mining solution found by {miner_id} in range {nonce_range}")
            # Mark all work as obsolete
            self._current_work = None
            self._work_assignments.clear()
        
        return True
    
    @synchronized("mining_work", LockOrder.MINING, mode='read')
    def is_work_valid(self, work: MiningWork) -> bool:
        """Check if work is still valid (not superseded)"""
        if not self._current_work:
            return False
        
        return (work.block_template.get('previous_hash') == self._current_work.get('previous_hash') and
                work.block_template.get('index') == self._current_work.get('index'))
    
    def get_stats(self) -> Dict[str, int]:
        """Get work coordination statistics"""
        return {
            'work_units_assigned': self._stats['work_units_assigned'].value,
            'work_units_completed': self._stats['work_units_completed'].value,
            'duplicate_work_prevented': self._stats['duplicate_work_prevented'].value,
            'active_miners': len(self._work_assignments)
        }

class ThreadSafeMiner:
    """
    Thread-safe mining implementation with work coordination
    """
    
    def __init__(self, miner_id: str, worker_threads: int = 4):
        self.miner_id = miner_id
        self.worker_threads = worker_threads
        
        # Mining state
        self._is_mining = False
        self._mining_lock = threading.Lock()
        self._stop_event = threading.Event()
        
        # Work coordination
        self._work_coordinator = WorkCoordinator()
        self._work_queue = queue.Queue(maxsize=worker_threads * 2)
        self._result_queue = queue.Queue()
        
        # Worker thread pool
        self._workers: List[threading.Thread] = []
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=worker_threads)
        
        # Statistics
        self._stats = {
            'blocks_mined': AtomicCounter(),
            'total_hashes': AtomicCounter(),
            'mining_time': 0.0,
            'start_time': 0.0,
            'last_block_time': 0.0
        }
        
        logger.info(f"Thread-safe miner initialized: {miner_id} with {worker_threads} workers")
    
    def start_mining(self, block_template: dict) -> bool:
        """Start mining with thread safety"""
        with self._mining_lock:
            if self._is_mining:
                logger.warning(f"Miner {self.miner_id} already mining")
                return False
            
            # Set new work
            if not self._work_coordinator.set_current_work(block_template):
                logger.info(f"Work unchanged, continuing mining")
                return True
            
            self._is_mining = True
            self._stop_event.clear()
            self._stats['start_time'] = time.time()
            
            # Start worker threads
            self._start_workers()
            
            logger.info(f"Mining started: block {block_template.get('index')}")
            return True
    
    def stop_mining(self) -> bool:
        """Stop mining with cleanup"""
        with self._mining_lock:
            if not self._is_mining:
                return False
            
            self._is_mining = False
            self._stop_event.set()
            
            # Stop workers
            self._stop_workers()
            
            # Update statistics
            if self._stats['start_time'] > 0:
                self._stats['mining_time'] += time.time() - self._stats['start_time']
            
            logger.info(f"Mining stopped: {self.miner_id}")
            return True
    
    def _start_workers(self):
        """Start mining worker threads"""
        self._workers.clear()
        
        for i in range(self.worker_threads):
            worker = threading.Thread(
                target=self._mining_worker,
                name=f"{self.miner_id}_worker_{i}",
                daemon=True
            )
            worker.start()
            self._workers.append(worker)
        
        logger.debug(f"Started {len(self._workers)} mining workers")
    
    def _stop_workers(self):
        """Stop all mining workers"""
        # Signal stop
        self._stop_event.set()
        
        # Wait for workers to finish (with timeout)
        for worker in self._workers:
            worker.join(timeout=5.0)
            if worker.is_alive():
                logger.warning(f"Worker {worker.name} did not stop gracefully")
        
        self._workers.clear()
    
    def _mining_worker(self):
        """Individual mining worker thread"""
        worker_name = threading.current_thread().name
        logger.debug(f"Mining worker started: {worker_name}")
        
        while not self._stop_event.is_set():
            try:
                # Get work assignment
                work = self._work_coordinator.assign_work(f"{self.miner_id}_{worker_name}")
                if not work:
                    time.sleep(0.1)
                    continue
                
                # Mine the work range
                result = self._mine_work_range(work)
                
                # Report results
                self._handle_mining_result(work, result)
                
                if result.success:
                    logger.info(f"Block mined by {worker_name}!")
                    break  # Stop mining on success
                
            except Exception as e:
                logger.error(f"Mining worker error in {worker_name}: {e}")
                time.sleep(1.0)
        
        logger.debug(f"Mining worker stopped: {worker_name}")
    
    def _mine_work_range(self, work: MiningWork) -> MiningResult:
        """Mine a specific nonce range"""
        start_time = time.time()
        block_template = work.block_template
        target = "0" * work.target_difficulty
        
        try:
            for nonce in range(work.start_nonce, work.end_nonce):
                # Check if we should stop
                if self._stop_event.is_set():
                    break
                
                # Check if work is still valid
                if not self._work_coordinator.is_work_valid(work):
                    logger.debug(f"Work became invalid, stopping range {work.start_nonce}-{work.end_nonce}")
                    break
                
                # Calculate hash
                block_data = {
                    'index': block_template['index'],
                    'previous_hash': block_template['previous_hash'],
                    'merkle_root': block_template.get('merkle_root', ''),
                    'timestamp': block_template['timestamp'],
                    'nonce': nonce,
                    'target_difficulty': work.target_difficulty
                }
                
                # Double SHA-256 like Bitcoin
                block_string = self._serialize_block_data(block_data)
                hash1 = hashlib.sha256(block_string.encode()).digest()
                hash2 = hashlib.sha256(hash1).hexdigest()
                
                self._stats['total_hashes'].increment()
                
                # Check if we found a solution
                if hash2.startswith(target):
                    mining_time = time.time() - start_time
                    hash_rate = (nonce - work.start_nonce + 1) / max(mining_time, 0.001)
                    
                    return MiningResult(
                        success=True,
                        block_hash=hash2,
                        nonce=nonce,
                        mining_time=mining_time,
                        hash_rate=hash_rate,
                        miner_id=work.miner_id
                    )
                
                # Periodic checks (every 10000 hashes)
                if nonce % 10000 == 0:
                    # Check for stop signal
                    if self._stop_event.is_set():
                        break
                    
                    # Yield to other threads occasionally
                    if nonce % 100000 == 0:
                        time.sleep(0.001)
            
            # Range completed without solution
            mining_time = time.time() - start_time
            hash_rate = (work.end_nonce - work.start_nonce) / max(mining_time, 0.001)
            
            return MiningResult(
                success=False,
                mining_time=mining_time,
                hash_rate=hash_rate,
                miner_id=work.miner_id
            )
            
        except Exception as e:
            return MiningResult(
                success=False,
                error_message=str(e),
                miner_id=work.miner_id
            )
    
    def _serialize_block_data(self, block_data: dict) -> str:
        """Serialize block data for hashing"""
        import json
        return json.dumps(block_data, sort_keys=True)
    
    def _handle_mining_result(self, work: MiningWork, result: MiningResult):
        """Handle mining result and update statistics"""
        work_range = (work.start_nonce, work.end_nonce)
        
        # Report work completion
        self._work_coordinator.report_work_completed(
            work.miner_id, 
            work_range, 
            result.success
        )
        
        if result.success:
            # Update mining statistics
            self._stats['blocks_mined'].increment()
            self._stats['last_block_time'] = time.time()
            
            # Update block template with solution
            work.block_template['nonce'] = result.nonce
            work.block_template['hash'] = result.block_hash
            
            # Put result in queue for main thread
            self._result_queue.put(result)
            
            # Stop all mining
            self._stop_event.set()
    
    def get_mining_result(self, timeout: float = 0.1) -> Optional[MiningResult]:
        """Get mining result if available"""
        try:
            return self._result_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_stats(self) -> Dict:
        """Get mining statistics"""
        current_time = time.time()
        total_time = self._stats['mining_time']
        
        if self._is_mining and self._stats['start_time'] > 0:
            total_time += current_time - self._stats['start_time']
        
        return {
            'miner_id': self.miner_id,
            'is_mining': self._is_mining,
            'blocks_mined': self._stats['blocks_mined'].value,
            'total_hashes': self._stats['total_hashes'].value,
            'total_mining_time': total_time,
            'average_hash_rate': self._stats['total_hashes'].value / max(total_time, 1),
            'worker_threads': self.worker_threads,
            'work_coordinator_stats': self._work_coordinator.get_stats()
        }
    
    @property
    def is_mining(self) -> bool:
        """Thread-safe mining status check"""
        with self._mining_lock:
            return self._is_mining
    
    def cleanup(self):
        """Cleanup mining resources"""
        self.stop_mining()
        
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=True)
        
        logger.info(f"Mining cleanup complete: {self.miner_id}")

class MiningPool:
    """
    Manages multiple miners with work distribution
    """
    
    def __init__(self):
        self._miners: Dict[str, ThreadSafeMiner] = {}
        self._pool_lock = lock_manager.get_lock("mining_pool", LockOrder.MINING)
        self._global_work_coordinator = WorkCoordinator()
        
        # Pool statistics
        self._pool_stats = {
            'total_blocks_mined': AtomicCounter(),
            'total_hash_rate': 0.0,
            'active_miners': 0
        }
        
        logger.info("Mining pool initialized")
    
    @synchronized("mining_pool", LockOrder.MINING, mode='write')
    def add_miner(self, miner_id: str, worker_threads: int = 4) -> bool:
        """Add miner to pool"""
        if miner_id in self._miners:
            logger.warning(f"Miner {miner_id} already in pool")
            return False
        
        miner = ThreadSafeMiner(miner_id, worker_threads)
        self._miners[miner_id] = miner
        
        logger.info(f"Miner added to pool: {miner_id}")
        return True
    
    @synchronized("mining_pool", LockOrder.MINING, mode='write')
    def remove_miner(self, miner_id: str) -> bool:
        """Remove miner from pool"""
        if miner_id not in self._miners:
            return False
        
        miner = self._miners[miner_id]
        miner.cleanup()
        del self._miners[miner_id]
        
        logger.info(f"Miner removed from pool: {miner_id}")
        return True
    
    def start_pool_mining(self, block_template: dict) -> int:
        """Start mining across all miners in pool"""
        started_count = 0
        
        with self._pool_lock.read_lock():
            for miner in self._miners.values():
                if miner.start_mining(block_template):
                    started_count += 1
        
        logger.info(f"Pool mining started: {started_count} miners active")
        return started_count
    
    def stop_pool_mining(self) -> int:
        """Stop mining across all miners in pool"""
        stopped_count = 0
        
        with self._pool_lock.read_lock():
            for miner in self._miners.values():
                if miner.stop_mining():
                    stopped_count += 1
        
        logger.info(f"Pool mining stopped: {stopped_count} miners stopped")
        return stopped_count
    
    def get_pool_stats(self) -> Dict:
        """Get comprehensive pool statistics"""
        with self._pool_lock.read_lock():
            miner_stats = {miner_id: miner.get_stats() for miner_id, miner in self._miners.items()}
            
            total_hash_rate = sum(stats['average_hash_rate'] for stats in miner_stats.values())
            active_miners = sum(1 for stats in miner_stats.values() if stats['is_mining'])
            total_blocks = sum(stats['blocks_mined'] for stats in miner_stats.values())
            
            return {
                'pool_summary': {
                    'total_miners': len(self._miners),
                    'active_miners': active_miners,
                    'total_blocks_mined': total_blocks,
                    'combined_hash_rate': total_hash_rate
                },
                'individual_miners': miner_stats
            }
    
    def cleanup(self):
        """Cleanup all miners in pool"""
        with self._pool_lock.write_lock():
            for miner in self._miners.values():
                miner.cleanup()
            self._miners.clear()
        
        logger.info("Mining pool cleanup complete")

# Global mining pool instance
mining_pool = MiningPool()