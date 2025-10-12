-- ChainCore Database Setup Script (Fixed)
-- Creates all missing tables and functions for the blockchain system

-- ================================
-- 1. TRANSACTIONS TABLE
-- ================================
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(255) UNIQUE NOT NULL,
    block_id INTEGER NOT NULL,
    block_index INTEGER NOT NULL,
    transaction_type VARCHAR(50) NOT NULL CHECK (transaction_type IN ('coinbase', 'transfer')),
    inputs_json JSONB,
    outputs_json JSONB,
    total_amount DECIMAL(20,8) NOT NULL DEFAULT 0,
    is_coinbase BOOLEAN NOT NULL DEFAULT FALSE,
    timestamp DECIMAL(20,6) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for transactions table
CREATE INDEX IF NOT EXISTS idx_transactions_tx_id ON transactions (transaction_id);
CREATE INDEX IF NOT EXISTS idx_transactions_block_id ON transactions (block_id);
CREATE INDEX IF NOT EXISTS idx_transactions_block_index ON transactions (block_index);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions (transaction_type);
CREATE INDEX IF NOT EXISTS idx_transactions_coinbase ON transactions (is_coinbase);

-- ================================
-- 2. UTXOS TABLE  
-- ================================
CREATE TABLE IF NOT EXISTS utxos (
    id SERIAL PRIMARY KEY,
    utxo_key VARCHAR(255) UNIQUE NOT NULL,
    transaction_id VARCHAR(255) NOT NULL,
    output_index INTEGER NOT NULL,
    recipient_address VARCHAR(255) NOT NULL,
    amount DECIMAL(20,8) NOT NULL,
    block_index INTEGER NOT NULL,
    is_spent BOOLEAN NOT NULL DEFAULT FALSE,
    spent_in_transaction VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for UTXOs table
CREATE INDEX IF NOT EXISTS idx_utxos_key ON utxos (utxo_key);
CREATE INDEX IF NOT EXISTS idx_utxos_address ON utxos (recipient_address);
CREATE INDEX IF NOT EXISTS idx_utxos_spent ON utxos (is_spent);
CREATE INDEX IF NOT EXISTS idx_utxos_block ON utxos (block_index);
CREATE INDEX IF NOT EXISTS idx_utxos_address_unspent ON utxos (recipient_address, is_spent);

-- ================================
-- 3. MINING_STATS TABLE
-- ================================
CREATE TABLE IF NOT EXISTS mining_stats (
    id SERIAL PRIMARY KEY,
    node_id VARCHAR(255) NOT NULL,
    block_id INTEGER NOT NULL,
    mining_duration_seconds DECIMAL(10,3) NOT NULL,
    hash_attempts BIGINT NOT NULL,
    hash_rate DECIMAL(15,2) NOT NULL,
    mining_started_at TIMESTAMP NOT NULL,
    mining_completed_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for mining_stats table
CREATE INDEX IF NOT EXISTS idx_mining_stats_node ON mining_stats (node_id);
CREATE INDEX IF NOT EXISTS idx_mining_stats_block ON mining_stats (block_id);
CREATE INDEX IF NOT EXISTS idx_mining_stats_duration ON mining_stats (mining_duration_seconds);
CREATE INDEX IF NOT EXISTS idx_mining_stats_hash_rate ON mining_stats (hash_rate);

-- ================================
-- 4. ADDRESS_BALANCES TABLE
-- Persistent table to store balances for all seen addresses
-- ================================
CREATE TABLE IF NOT EXISTS address_balances (
    address VARCHAR(255) PRIMARY KEY,
    balance DECIMAL(20,8) NOT NULL DEFAULT 0,
    utxo_count INTEGER NOT NULL DEFAULT 0,
    last_activity_block INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast lookups and rich-list queries
CREATE INDEX IF NOT EXISTS idx_address_balances_balance ON address_balances (balance DESC);
CREATE INDEX IF NOT EXISTS idx_address_balances_updated ON address_balances (updated_at);

-- ================================
-- 5. UPDATE BLOCKS TABLE (add missing columns if needed)
-- ================================
-- Add columns that might be missing from blocks table
DO $$ 
BEGIN
    -- Add columns if they don't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'blocks' AND column_name = 'miner_node') THEN
        ALTER TABLE blocks ADD COLUMN miner_node VARCHAR(255) DEFAULT 'unknown';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'blocks' AND column_name = 'miner_address') THEN
        ALTER TABLE blocks ADD COLUMN miner_address VARCHAR(255) DEFAULT 'unknown';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'blocks' AND column_name = 'transaction_count') THEN
        ALTER TABLE blocks ADD COLUMN transaction_count INTEGER DEFAULT 0;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'blocks' AND column_name = 'raw_data') THEN
        ALTER TABLE blocks ADD COLUMN raw_data JSONB;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'blocks' AND column_name = 'created_at') THEN
        ALTER TABLE blocks ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;
END $$;

-- Add indexes to blocks table
CREATE INDEX IF NOT EXISTS idx_blocks_index ON blocks (block_index);
CREATE INDEX IF NOT EXISTS idx_blocks_hash ON blocks (hash);
CREATE INDEX IF NOT EXISTS idx_blocks_previous_hash ON blocks (previous_hash);
CREATE INDEX IF NOT EXISTS idx_blocks_miner_node ON blocks (miner_node);
CREATE INDEX IF NOT EXISTS idx_blocks_timestamp ON blocks (timestamp);

-- ================================
-- 6. ADD_BLOCK STORED FUNCTION
-- ================================
CREATE OR REPLACE FUNCTION add_block(
    p_block_index INTEGER,
    p_hash VARCHAR(255),
    p_previous_hash VARCHAR(255),
    p_merkle_root VARCHAR(255),
    p_timestamp DECIMAL(20,6),
    p_nonce BIGINT,
    p_difficulty DECIMAL(20,8),
    p_miner_node VARCHAR(255),
    p_miner_address VARCHAR(255),
    p_block_data JSONB
) RETURNS INTEGER AS $$
DECLARE
    block_id INTEGER;
BEGIN
    -- Insert block and return the ID
    INSERT INTO blocks (
        block_index, hash, previous_hash, merkle_root,
        timestamp, nonce, difficulty, miner_node, miner_address,
        transaction_count, raw_data, created_at
    ) VALUES (
        p_block_index, p_hash, p_previous_hash, p_merkle_root,
        p_timestamp, p_nonce, p_difficulty, p_miner_node, p_miner_address,
        COALESCE((p_block_data->>'transaction_count')::INTEGER, 0),
        p_block_data, CURRENT_TIMESTAMP
    ) RETURNING id INTO block_id;
    
    RETURN block_id;
END;
$$ LANGUAGE plpgsql;

-- ================================
-- 7. REFRESH MATERIALIZED VIEW FUNCTION
-- ================================
CREATE OR REPLACE FUNCTION refresh_address_balances() 
RETURNS VOID AS $$
BEGIN
    -- Rebuild the address_balances persistent table from utxos
    -- This will replace contents with aggregated current unspent UTXOs
    TRUNCATE TABLE address_balances;

    -- Build a set of all addresses that have ever appeared in transactions or utxos
    WITH seen_addresses AS (
        -- Addresses from UTXO recipients (both spent and unspent)
        SELECT DISTINCT recipient_address AS address FROM utxos
        UNION
        -- Addresses from transaction outputs (recipients)
        SELECT DISTINCT (elem->>'recipient_address') AS address
        FROM transactions, jsonb_array_elements(outputs_json) AS elem
        WHERE outputs_json IS NOT NULL AND elem->>'recipient_address' IS NOT NULL
        UNION
        -- Addresses from transaction inputs (senders) - extract from input addresses
        SELECT DISTINCT (elem->>'address') AS address
        FROM transactions, jsonb_array_elements(inputs_json) AS elem
        WHERE inputs_json IS NOT NULL AND elem->>'address' IS NOT NULL
    ),
    balances AS (
        SELECT recipient_address,
               SUM(amount) AS balance,
               COUNT(*) AS utxo_count,
               MAX(block_index) AS last_activity_block
        FROM utxos
        WHERE is_spent = FALSE
        GROUP BY recipient_address
    ),
    all_activity AS (
        -- Get last activity block for each address from all sources
        SELECT address,
               MAX(activity_block) AS last_activity_block
        FROM (
            -- Activity from UTXOs (both spent and unspent)
            SELECT recipient_address AS address, block_index AS activity_block FROM utxos
            UNION ALL
            -- Activity from transactions
            SELECT (elem->>'recipient_address') AS address, t.block_index AS activity_block
            FROM transactions t, jsonb_array_elements(t.outputs_json) AS elem
            WHERE t.outputs_json IS NOT NULL AND elem->>'recipient_address' IS NOT NULL
        ) activities
        GROUP BY address
    )
    INSERT INTO address_balances (address, balance, utxo_count, last_activity_block, updated_at)
    SELECT
        s.address,
        COALESCE(b.balance, 0) AS balance,
        COALESCE(b.utxo_count, 0) AS utxo_count,
        COALESCE(a.last_activity_block, b.last_activity_block) AS last_activity_block,
        CURRENT_TIMESTAMP
    FROM seen_addresses s
    LEFT JOIN balances b ON s.address = b.recipient_address
    LEFT JOIN all_activity a ON s.address = a.address;
END;
$$ LANGUAGE plpgsql;

-- ================================
-- INITIAL DATA SETUP
-- ================================
-- Refresh the materialized view initially (will be empty)
-- Populate address_balances table initially
SELECT refresh_address_balances();

-- ================================
-- SETUP COMPLETE - VERIFICATION
-- ================================
SELECT 'ChainCore Database Setup Complete!' AS status;
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name AND table_schema = 'public') AS column_count
FROM information_schema.tables t 
WHERE table_schema = 'public' 
ORDER BY table_name;