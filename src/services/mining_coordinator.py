#!/usr/bin/env python3
"""
Local Network Mining Coordination
Prevents constant forking in multi-terminal testing
"""

import time
import random
import logging
import threading
from typing import Dict, Set, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MiningRound:
    """Represents a mining round with designated miner"""
    round_number: int
    designated_miner: str
    start_time: float
    duration: float
    block_height: int

class LocalMiningCoordinator:
    """Coordinates mining in local multi-terminal environment"""
    
    def __init__(self, round_duration: float = 15.0):
        self.round_duration = round_duration  # 15 seconds per mining round
        self._active_miners: Set[str] = set()
        self._current_round: Optional[MiningRound] = None
        self._round_number = 0
        self._lock = threading.RLock()
        self._last_block_time = time.time()
        
    def register_miner(self, miner_id: str) -> bool:
        """Register a miner in the coordination system"""
        with self._lock:
            if miner_id not in self._active_miners:
                self._active_miners.add(miner_id)
                logger.info(f"Miner registered: {miner_id} "
                           f"(total miners: {len(self._active_miners)})")
                return True
            return False
    
    def unregister_miner(self, miner_id: str) -> bool:
        """Unregister a miner from coordination"""
        with self._lock:
            if miner_id in self._active_miners:
                self._active_miners.discard(miner_id)
                logger.info(f"Miner unregistered: {miner_id}")
                return True
            return False
    
    def should_mine_now(self, miner_id: str, current_block_height: int) -> Dict:
        """Check if this miner should mine in current round"""
        with self._lock:
            current_time = time.time()
            
            # Start new round if needed
            if (self._current_round is None or 
                current_time - self._current_round.start_time > self.round_duration or
                current_block_height > self._current_round.block_height):
                
                self._start_new_round(current_block_height)
            
            # Check if this miner is designated for current round
            is_designated = (self._current_round and 
                           self._current_round.designated_miner == miner_id)
            
            # Allow backup mining if designated miner is inactive
            backup_time = self.round_duration * 0.7  # 70% through round
            is_backup = (current_time - self._current_round.start_time > backup_time)
            
            return {
                'should_mine': is_designated or is_backup,
                'is_designated': is_designated,
                'is_backup': is_backup,
                'round_number': self._round_number,
                'designated_miner': self._current_round.designated_miner if self._current_round else None,
                'time_remaining': max(0, self.round_duration - (current_time - self._current_round.start_time)) if self._current_round else 0,
                'total_miners': len(self._active_miners)
            }
    
    def _start_new_round(self, block_height: int):
        """Start a new mining round with designated miner"""
        if not self._active_miners:
            logger.warning("No active miners for coordination")
            return
            
        # Select designated miner (round-robin with randomness)
        miners_list = sorted(list(self._active_miners))  # Consistent ordering
        
        if len(miners_list) == 1:
            designated = miners_list[0]
        else:
            # Use block height for deterministic but distributed selection
            index = (block_height + self._round_number) % len(miners_list)
            designated = miners_list[index]
        
        self._round_number += 1
        self._current_round = MiningRound(
            round_number=self._round_number,
            designated_miner=designated,
            start_time=time.time(),
            duration=self.round_duration,
            block_height=block_height
        )
        
        logger.info(f"New mining round #{self._round_number}: "
                   f"Designated miner: {designated} for block #{block_height}")
    
    def report_block_mined(self, miner_id: str, block_height: int):
        """Report that a block was successfully mined"""
        with self._lock:
            self._last_block_time = time.time()
            
            if self._current_round and self._current_round.designated_miner == miner_id:
                logger.info(f"✅ Block #{block_height} mined by designated miner: {miner_id}")
            else:
                logger.info(f"⚡ Block #{block_height} mined by backup miner: {miner_id}")
            
            # End current round since block was found
            self._current_round = None
    
    def get_mining_status(self) -> Dict:
        """Get current mining coordination status"""
        with self._lock:
            current_time = time.time()
            
            status = {
                'active_miners': len(self._active_miners),
                'miners_list': sorted(list(self._active_miners)),
                'round_duration': self.round_duration,
                'current_round': self._round_number
            }
            
            if self._current_round:
                time_elapsed = current_time - self._current_round.start_time
                status.update({
                    'designated_miner': self._current_round.designated_miner,
                    'round_start_time': self._current_round.start_time,
                    'time_elapsed': time_elapsed,
                    'time_remaining': max(0, self.round_duration - time_elapsed),
                    'block_height': self._current_round.block_height
                })
            
            return status
    
    def adjust_round_duration(self, target_block_time: float = 10.0):
        """Dynamically adjust round duration based on network performance"""
        with self._lock:
            current_time = time.time()
            time_since_last_block = current_time - self._last_block_time
            
            # If blocks are coming too fast, increase round duration
            if time_since_last_block < target_block_time * 0.5:
                self.round_duration = min(30.0, self.round_duration * 1.1)
                logger.debug(f"Mining rounds slowed: {self.round_duration:.1f}s")
            
            # If blocks are too slow, decrease round duration  
            elif time_since_last_block > target_block_time * 2.0:
                self.round_duration = max(5.0, self.round_duration * 0.9)
                logger.debug(f"Mining rounds accelerated: {self.round_duration:.1f}s")

# Global mining coordinator instance
mining_coordinator = LocalMiningCoordinator()

def get_mining_coordinator() -> LocalMiningCoordinator:
    """Get the global mining coordinator instance"""
    return mining_coordinator