-- PostgreSQL initialization script for PolyTracker Bot
-- This file is automatically run by docker-compose on first startup

-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Additional indexes for performance
CREATE INDEX IF NOT EXISTS idx_trades_wallet_timestamp ON trades(wallet_address, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_market_resolved ON trades(market_id, market_resolved);
CREATE INDEX IF NOT EXISTS idx_wallets_score_active ON wallets(score DESC, is_active);

-- Set up basic settings
ALTER DATABASE polytracker SET log_statement = 'mod';
ALTER DATABASE polytracker SET log_duration = off;

-- Done
SELECT 'PostgreSQL PolyTracker database initialized successfully' as status;
