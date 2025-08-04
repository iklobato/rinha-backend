-- Optimized database initialization for high-performance backend
-- Includes proper indexes and optimized table structures

-- Create clients table with optimized structure
CREATE TABLE IF NOT EXISTS clientes (
    id SERIAL PRIMARY KEY,
    limite INTEGER NOT NULL,
    saldo INTEGER NOT NULL DEFAULT 0
);

-- Create transactions table with optimized structure
CREATE TABLE IF NOT EXISTS transacoes (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL,
    valor INTEGER NOT NULL,
    tipo CHAR(1) NOT NULL CHECK (tipo IN ('c', 'd')),
    descricao VARCHAR(10) NOT NULL,
    realizada_em TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create optimized indexes for performance
-- Index for client lookups (most frequent query)
CREATE INDEX IF NOT EXISTS idx_clientes_id ON clientes(id);

-- Composite index for transaction queries (ordered by most selective columns)
CREATE INDEX IF NOT EXISTS idx_transacoes_cliente_data ON transacoes(cliente_id, realizada_em DESC);

-- Index for transaction type filtering if needed
CREATE INDEX IF NOT EXISTS idx_transacoes_tipo ON transacoes(tipo);

-- Insert initial clients with optimized limits
INSERT INTO clientes (id, limite, saldo) VALUES
    (1, 100000, 0),
    (2, 80000, 0),
    (3, 1000000, 0),
    (4, 10000000, 0),
    (5, 500000, 0)
ON CONFLICT (id) DO NOTHING;

-- Optimize table statistics
ANALYZE clientes;
ANALYZE transacoes;

-- Set optimized PostgreSQL settings for performance
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
ALTER SYSTEM SET work_mem = '4MB';
ALTER SYSTEM SET min_wal_size = '1GB';
ALTER SYSTEM SET max_wal_size = '4GB';

-- Reload configuration
SELECT pg_reload_conf(); 