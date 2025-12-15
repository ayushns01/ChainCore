#!/usr/bin/env python3
"""
Test script to verify blockchain restart integrity
Tests that previous_hash linkage is preserved across restarts
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.concurrency.blockchain_safe import ThreadSafeBlockchain
from src.data.block_dao import BlockDAO
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def test_restart_integrity():
    """Test blockchain restart integrity"""
    
    logger.info("=" * 80)
    logger.info("BLOCKCHAIN RESTART INTEGRITY TEST")
    logger.info("=" * 80)
    
    # Step 1: Create fresh blockchain
    logger.info("\n[STEP 1] Creating fresh blockchain instance...")
    blockchain1 = ThreadSafeBlockchain()
    
    initial_length = blockchain1.get_chain_length()
    logger.info(f"✅ Initial chain length: {initial_length}")
    
    if initial_length > 0:
        chain_copy = blockchain1.get_chain_copy()
        latest_block = chain_copy[-1]
        logger.info(f"✅ Latest block: #{latest_block.index}")
        logger.info(f"   Hash: {latest_block.hash[:32]}...")
        logger.info(f"   Previous: {latest_block.previous_hash[:32]}...")
    
    # Step 2: Simulate restart by creating new blockchain instance
    logger.info("\n[STEP 2] Simulating restart (creating new blockchain instance)...")
    del blockchain1
    
    blockchain2 = ThreadSafeBlockchain()
    
    restart_length = blockchain2.get_chain_length()
    logger.info(f"✅ Chain length after restart: {restart_length}")
    
    if restart_length > 0:
        chain_copy2 = blockchain2.get_chain_copy()
        latest_block2 = chain_copy2[-1]
        logger.info(f"✅ Latest block after restart: #{latest_block2.index}")
        logger.info(f"   Hash: {latest_block2.hash[:32]}...")
        logger.info(f"   Previous: {latest_block2.previous_hash[:32]}...")
    
    # Step 3: Verify chain integrity
    logger.info("\n[STEP 3] Verifying chain integrity...")
    
    if restart_length != initial_length:
        logger.error(f"❌ Chain length mismatch!")
        logger.error(f"   Before restart: {initial_length}")
        logger.error(f"   After restart:  {restart_length}")
        return False
    
    # Step 4: Verify hash linkage
    logger.info("\n[STEP 4] Verifying hash linkage across entire chain...")
    
    chain = blockchain2.get_chain_copy()
    errors = []
    
    for i in range(1, len(chain)):
        current_block = chain[i]
        previous_block = chain[i-1]
        
        if current_block.previous_hash != previous_block.hash:
            error_msg = f"Block #{i} previous_hash mismatch"
            errors.append(error_msg)
            logger.error(f"❌ {error_msg}")
            logger.error(f"   Expected: {previous_block.hash[:32]}...")
            logger.error(f"   Got:      {current_block.previous_hash[:32]}...")
        else:
            logger.info(f"✅ Block #{i} linkage valid")
    
    # Step 5: Test creating new block template
    logger.info("\n[STEP 5] Testing new block template creation after restart...")
    
    test_address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    template = blockchain2.create_block_template(test_address, "test_miner")
    
    logger.info(f"✅ Block template created successfully")
    logger.info(f"   Index: {template.index}")
    logger.info(f"   Previous hash: {template.previous_hash[:32]}...")
    
    # Verify template has correct previous_hash
    if len(chain) > 0:
        expected_prev_hash = chain[-1].hash
        if template.previous_hash != expected_prev_hash:
            logger.error(f"❌ Template previous_hash mismatch!")
            logger.error(f"   Expected: {expected_prev_hash[:32]}...")
            logger.error(f"   Got:      {template.previous_hash[:32]}...")
            errors.append("Template previous_hash mismatch")
        else:
            logger.info(f"✅ Template previous_hash matches latest block hash")
    
    # Final result
    logger.info("\n" + "=" * 80)
    if len(errors) == 0:
        logger.info("✅ ALL TESTS PASSED - Blockchain restart integrity verified!")
        logger.info("=" * 80)
        return True
    else:
        logger.error(f"❌ TEST FAILED - {len(errors)} errors found:")
        for error in errors:
            logger.error(f"   - {error}")
        logger.error("=" * 80)
        return False

if __name__ == '__main__':
    try:
        success = test_restart_integrity()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
