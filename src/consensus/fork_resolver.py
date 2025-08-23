#!/usr/bin/env python3
"""
Local Network Fork Resolution
Implements proper fork resolution for multi-terminal testing
"""

import logging
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ForkCandidate:
    """Represents a potential fork in the blockchain"""
    chain: List  # List of blocks
    cumulative_difficulty: int
    source_peer: str
    timestamp: float
    
class LocalForkResolver:
    """Resolves forks in local multi-terminal environment"""
    
    def __init__(self, max_fork_depth: int = 6):
        self.max_fork_depth = max_fork_depth
        self._active_forks: Dict[int, List[ForkCandidate]] = {}  # height -> candidates
        self._fork_timeout = 30.0  # 30 seconds to resolve
        
    def add_fork_candidate(self, blocks: List, source_peer: str, common_ancestor: int) -> bool:
        """Add a potential fork for evaluation"""
        if not blocks:
            return False
            
        # Calculate cumulative difficulty
        cumulative_difficulty = sum(self._calculate_block_difficulty(block) for block in blocks)
        
        candidate = ForkCandidate(
            chain=blocks,
            cumulative_difficulty=cumulative_difficulty,
            source_peer=source_peer,
            timestamp=time.time()
        )
        
        fork_height = common_ancestor
        if fork_height not in self._active_forks:
            self._active_forks[fork_height] = []
            
        self._active_forks[fork_height].append(candidate)
        
        logger.info(f"Fork candidate added: height {fork_height}, difficulty {cumulative_difficulty}")
        return True
    
    def resolve_fork(self, current_chain: List, fork_height: int) -> Optional[List]:
        """Resolve fork using longest/heaviest chain rule"""
        if fork_height not in self._active_forks:
            return None
            
        candidates = self._active_forks[fork_height]
        current_time = time.time()
        
        # Remove expired candidates
        candidates = [c for c in candidates if current_time - c.timestamp < self._fork_timeout]
        
        if not candidates:
            del self._active_forks[fork_height]
            return None
            
        # Find heaviest chain
        current_difficulty = sum(self._calculate_block_difficulty(block) 
                               for block in current_chain[fork_height:])
        
        best_candidate = None
        best_difficulty = current_difficulty
        
        for candidate in candidates:
            if candidate.cumulative_difficulty > best_difficulty:
                best_candidate = candidate
                best_difficulty = candidate.cumulative_difficulty
                
        if best_candidate:
            logger.info(f"Fork resolved: Switching to heavier chain "
                       f"(difficulty {best_difficulty} vs {current_difficulty})")
            
            # Build new chain: common ancestor + winning fork
            new_chain = current_chain[:fork_height] + best_candidate.chain
            
            # Clean up resolved fork
            del self._active_forks[fork_height]
            
            return new_chain
            
        return None
    
    def _calculate_block_difficulty(self, block) -> int:
        """Calculate work/difficulty for a block"""
        # Count leading zeros in hash (simple PoW difficulty)
        if hasattr(block, 'hash'):
            return len(block.hash) - len(block.hash.lstrip('0'))
        return 1  # Default difficulty
    
    def cleanup_old_forks(self):
        """Remove expired fork candidates"""
        current_time = time.time()
        expired_heights = []
        
        for height, candidates in self._active_forks.items():
            valid_candidates = [c for c in candidates 
                              if current_time - c.timestamp < self._fork_timeout]
            
            if valid_candidates:
                self._active_forks[height] = valid_candidates
            else:
                expired_heights.append(height)
                
        for height in expired_heights:
            del self._active_forks[height]
            
        if expired_heights:
            logger.debug(f"Cleaned up expired forks at heights: {expired_heights}")
    
    def get_fork_status(self) -> Dict:
        """Get current fork resolution status"""
        return {
            'active_forks': len(self._active_forks),
            'fork_heights': list(self._active_forks.keys()),
            'total_candidates': sum(len(candidates) for candidates in self._active_forks.values())
        }

# Global fork resolver instance
fork_resolver = LocalForkResolver()

def get_fork_resolver() -> LocalForkResolver:
    """Get the global fork resolver instance"""
    return fork_resolver