#!/usr/bin/env python3
import json
import sys
import os

# Add src and parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.crypto.ecdsa_crypto import double_sha256

# Load fresh template
with open('fresh_template.json', 'r') as f:
    response = json.load(f)

block_template = response['block_template']
target_difficulty = response['target_difficulty']

print(f'Mining block {block_template["index"]} with target difficulty {target_difficulty}')

# Mine a block
target = '0' * target_difficulty
nonce = 0
while True:
    block_template['nonce'] = nonce
    block_data = {
        'index': block_template['index'],
        'previous_hash': block_template['previous_hash'],
        'merkle_root': block_template['merkle_root'],
        'timestamp': block_template['timestamp'],
        'nonce': nonce,
        'target_difficulty': target_difficulty
    }
    
    block_hash = double_sha256(json.dumps(block_data, sort_keys=True))
    if block_hash.startswith(target):
        print(f'✅ Block mined! Hash: {block_hash}, Nonce: {nonce}')
        block_template['hash'] = block_hash
        
        # Save mined block
        with open('mined_block.json', 'w') as f:
            json.dump(block_template, f, indent=2)
        print('Mined block saved to mined_block.json')
        break
    nonce += 1
    if nonce > 100000:
        print('Mining failed - took too long')
        break