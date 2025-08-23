-- ChainCore PostgreSQL Database Schema
-- Run this file to create all necessary tables

-- Enable UUID extension for better performance
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table for storing blockchain blocks
CREATE TABLE blocks (
    id SERIAL PRIMARY KEY,
    block_index INTEGER UNIQUE NOT NULL,
    hash VARCHAR(64) UNIQUE NOT NULL,
    previous_hash VARCHAR(64) NOT NULL,
    merkle_root VARCHAR(64) NOT NULL,
    timestamp DECIMAL(20,6) NOT NULL,
    nonce BIGINT NOT NULL,
    difficulty INTEGER NOT NULL,
    miner_node VARCHAR(50),
    miner_address VARCHAR(64),
    transaction_count INTEGER DEFAULT 0,
    block_size INTEGER DEFAULT 0,
    block_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for storing transactions
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(64) UNIQUE NOT NULL,
    block_id INTEGER REFERENCES blocks(id) ON DELETE CASCADE,
    block_index INTEGER NOT NULL,
    transaction_type VARCHAR(20) DEFAULT 'transfer',
    inputs_json JSONB,
    outputs_json JSONB,
    total_amount DECIMAL(20,8) DEFAULT 0,
    fee DECIMAL(20,8) DEFAULT 0,
    is_coinbase BOOLEAN DEFAULT FALSE,
    timestamp DECIMAL(20,6) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for tracking network nodes
CREATE TABLE nodes (
    id SERIAL PRIMARY KEY,
    node_id VARCHAR(50) UNIQUE NOT NULL,
    node_url VARCHAR(200),
    api_port INTEGER,
    status VARCHAR(20) DEFAULT 'active',
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    blocks_mined INTEGER DEFAULT 0,
    total_rewards DECIMAL(20,8) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for mining statistics
CREATE TABLE mining_stats (
    id SERIAL PRIMARY KEY,
    node_id VARCHAR(50) REFERENCES nodes(node_id),
    block_id INTEGER REFERENCES blocks(id),
    mining_duration_seconds DECIMAL(10,3),
    hash_attempts BIGINT,
    hash_rate DECIMAL(15,2),
    mining_started_at TIMESTAMP WITH TIME ZONE,
    mining_completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for UTXO (Unspent Transaction Outputs) - for fast balance lookups
CREATE TABLE utxos (
    id SERIAL PRIMARY KEY,
    utxo_key VARCHAR(128) UNIQUE NOT NULL, -- tx_id:output_index
    transaction_id VARCHAR(64) NOT NULL,
    output_index INTEGER NOT NULL,
    recipient_address VARCHAR(64) NOT NULL,
    amount DECIMAL(20,8) NOT NULL,
    block_index INTEGER NOT NULL,
    is_spent BOOLEAN DEFAULT FALSE,
    spent_in_transaction VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance indexes for fast queries
CREATE INDEX idx_blocks_hash ON blocks(hash);
CREATE INDEX idx_blocks_index ON blocks(block_index);
CREATE INDEX idx_blocks_miner ON blocks(miner_node);
CREATE INDEX idx_blocks_timestamp ON blocks(timestamp);

CREATE INDEX idx_transactions_id ON transactions(transaction_id);
CREATE INDEX idx_transactions_block ON transactions(block_index);
CREATE INDEX idx_transactions_type ON transactions(transaction_type);

CREATE INDEX idx_utxos_address ON utxos(recipient_address);
CREATE INDEX idx_utxos_spent ON utxos(is_spent);
CREATE INDEX idx_utxos_key ON utxos(utxo_key);

CREATE INDEX idx_mining_stats_node ON mining_stats(node_id);
CREATE INDEX idx_mining_stats_block ON mining_stats(block_id);

-- Materialized view for fast balance lookups
CREATE MATERIALIZED VIEW address_balances AS
SELECT 
    recipient_address as address,
    SUM(amount) as balance,
    COUNT(*) as utxo_count,
    MAX(created_at) as last_transaction
FROM utxos 
WHERE is_spent = FALSE 
GROUP BY recipient_address;

CREATE UNIQUE INDEX idx_address_balances_address ON address_balances(address);

-- Materialized view for mining statistics
CREATE MATERIALIZED VIEW mining_summary AS
SELECT 
    n.node_id,
    n.node_url,
    COUNT(b.id) as blocks_mined,
    SUM(COALESCE(ms.hash_attempts, 0)) as total_hash_attempts,
    AVG(COALESCE(ms.hash_rate, 0)) as avg_hash_rate,
    SUM(b.transaction_count) as total_transactions_processed,
    MIN(b.timestamp) as first_block_time,
    MAX(b.timestamp) as last_block_time
FROM nodes n
LEFT JOIN blocks b ON n.node_id = b.miner_node
LEFT JOIN mining_stats ms ON b.id = ms.block_id
GROUP BY n.node_id, n.node_url;

-- Function to refresh materialized views
CREATE OR REPLACE FUNCTION refresh_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW address_balances;
    REFRESH MATERIALIZED VIEW mining_summary;
END;
$$ LANGUAGE plpgsql;

-- Function to add a new block (ensures data consistency)
CREATE OR REPLACE FUNCTION add_block(
    p_block_index INTEGER,
    p_hash VARCHAR(64),
    p_previous_hash VARCHAR(64),
    p_merkle_root VARCHAR(64),
    p_timestamp DECIMAL(20,6),
    p_nonce BIGINT,
    p_difficulty INTEGER,
    p_miner_node VARCHAR(50),
    p_miner_address VARCHAR(64),
    p_block_data JSONB
)
RETURNS INTEGER AS $$
DECLARE
    new_block_id INTEGER;
BEGIN
    -- Insert the block
    INSERT INTO blocks (
        block_index, hash, previous_hash, merkle_root, timestamp,
        nonce, difficulty, miner_node, miner_address, block_data,
        transaction_count, block_size
    ) VALUES (
        p_block_index, p_hash, p_previous_hash, p_merkle_root, p_timestamp,
        p_nonce, p_difficulty, p_miner_node, p_miner_address, p_block_data,
        (p_block_data->>'transaction_count')::INTEGER,
        (p_block_data->>'block_size')::INTEGER
    ) RETURNING id INTO new_block_id;
    
    -- Update node statistics
    INSERT INTO nodes (node_id, blocks_mined, total_rewards)
    VALUES (p_miner_node, 1, 50.0)
    ON CONFLICT (node_id) DO UPDATE SET
        blocks_mined = nodes.blocks_mined + 1,
        total_rewards = nodes.total_rewards + 50.0,
        last_seen = NOW();
    
    RETURN new_block_id;
END;
$$ LANGUAGE plpgsql;

-- Insert initial node data
INSERT INTO nodes (node_id, node_url, api_port, status) VALUES
('Node-5000', 'http://localhost:5000', 5000, 'active'),
('Node-5001', 'http://localhost:5001', 5001, 'active'),
('Node-5002', 'http://localhost:5002', 5002, 'active')
ON CONFLICT (node_id) DO NOTHING;

COMMENT ON TABLE blocks IS 'Stores all blockchain blocks with complete metadata';
COMMENT ON TABLE transactions IS 'Stores all transactions with input/output details';
COMMENT ON TABLE nodes IS 'Tracks all network nodes and their statistics';
COMMENT ON TABLE mining_stats IS 'Detailed mining performance statistics';
COMMENT ON TABLE utxos IS 'Unspent transaction outputs for fast balance calculations';