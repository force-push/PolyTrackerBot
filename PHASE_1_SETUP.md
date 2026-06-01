# Phase 1: PostgreSQL Data Layer + Analytics Setup

## Overview

Phase 1 upgrades PolyTrackerBot from SQLite to a containerized PostgreSQL database with comprehensive analytics and backtesting capabilities. This allows you to:

- **Persist data reliably** across container restarts
- **Run backtests** on historical whale signals
- **Analyze performance** with CLI tools
- **Test on production data** yourself at each phase

## What's New

### New Files
- `docker-compose-pg.yml` — Docker compose with PostgreSQL service
- `polytracker/models.py` — SQLAlchemy ORM models
- `polytracker/db_pg.py` — Async PostgreSQL database layer
- `scripts/migrate_to_postgres.py` — SQLite → PostgreSQL migration
- `scripts/backtest.py` — Backtesting engine
- `scripts/analyze.py` — Analytics & reporting CLI
- `scripts/init_postgres.sql` — PostgreSQL initialization

### Schema Enhancements

**New tables:**
- `backtest_runs` — Backtest execution records
- `signal_performance` — Detailed signal outcome tracking

**Existing tables (enhanced):**
- `trades` — Added fields: `market_resolved`, `resolved_outcome`, `pnl`, `roi_pct`
- `wallets` — No changes (backward compatible)
- `alerts_sent` — No changes (backward compatible)

## Setup Instructions

### Step 1: Install Dependencies

```bash
cd ~/code/openclaw/projects/PolyTrackerBot
pip install -r requirements.txt
```

New dependencies added:
- `sqlalchemy>=2.0.0` — ORM for async database operations
- `asyncpg>=0.29.0` — Async PostgreSQL driver
- `alembic>=1.13.0` — Database migrations

### Step 2: Start PostgreSQL Container

```bash
docker-compose -f docker-compose-pg.yml up -d postgres
```

Verify PostgreSQL is ready:
```bash
docker-compose -f docker-compose-pg.yml ps
```

You should see `postgres` container with health check passing (green).

### Step 3: (Optional) Migrate Existing SQLite Data

If you have existing data in the old SQLite database:

```bash
# Set database URL (or use .env)
export DATABASE_URL="postgresql+asyncpg://polytracker:polytracker_dev@localhost:5432/polytracker"

# Run migration
python scripts/migrate_to_postgres.py
```

Output:
```
======================================================================
PolyTracker SQLite → PostgreSQL Migration
======================================================================
✅ Migrated X wallets
✅ Migrated Y trades
✅ Migrated Z alerts
======================================================================
Migration Complete!
  Wallets: X
  Trades: Y
  Alerts: Z
======================================================================
```

### Step 4: Test Database Connection

```bash
python -c "
import asyncio
from polytracker.db_pg import AsyncDatabase

async def test():
    db = AsyncDatabase()
    await db.connect()
    wallets = await db.get_active_wallets(limit=1)
    print(f'Connected! Found {len(wallets)} wallets')
    await db.disconnect()

asyncio.run(test())
"
```

## Using the CLI Tools

### 1. Analyze Current Performance

```bash
# Print summary + top wallets + recent signals
python scripts/analyze.py

# Print detailed wallet stats
python scripts/analyze.py wallets

# Print performance metrics
python scripts/analyze.py perf

# Print recent trades (default 20)
python scripts/analyze.py trades 50

# JSON output (for integration)
python scripts/analyze.py json
```

Example output:
```
================================================================================
POLYTRACKER ANALYTICS SUMMARY
================================================================================

Tracked Wallets: 45
Avg Wallet Score: 72.5
Top Wallet Score: 89.3

================================================================================
WALLET STATISTICS
================================================================================
Address                                            Score    Win%     PnL          Trades
────────────────────────────────────────────────────────────────────────────────
0x1234...5678                                      89.3     71.2%    $145,230     342
0x2345...6789                                      85.1     68.5%    $98,450      298
...
```

### 2. Run Backtests

Run backtest on all signals:
```bash
python scripts/backtest.py
```

Backtest with filters:
```bash
# Backtest last 30 days
python scripts/backtest.py --start 2026-05-02 --end 2026-06-01

# Backtest single wallet
python scripts/backtest.py --wallet 0x1234...5678 --notes "Testing high-conviction trader"

# With custom date range
python scripts/backtest.py --start 2026-01-01 --end 2026-06-01 --notes "Q1-Q2 2026 analysis"
```

Output:
```
======================================================================
Starting Backtest Run: backtest_a1b2c3d4
======================================================================
Found 342 signals to analyze

======================================================================
Backtest Results:
  Total Signals: 342
  Resolved: 187
  Profitable: 134
  Win Rate: 71.7%
  Avg ROI: 12.45%
  Total P&L: $18,945.32
======================================================================

JSON OUTPUT (for integration):
{
  "total_signals": 342,
  "resolved_signals": 187,
  "profitable_signals": 134,
  "win_rate": 0.717,
  "avg_roi": 12.45,
  "total_pnl": 18945.32,
  "run_id": "backtest_a1b2c3d4"
}
```

## Running the Main Bot with PostgreSQL

Option A: Use docker-compose (recommended for production)
```bash
docker-compose -f docker-compose-pg.yml up
```

Option B: Run locally against PostgreSQL container
```bash
export DATABASE_URL="postgresql+asyncpg://polytracker:polytracker_dev@localhost:5432/polytracker"
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHANNEL_ID="your_channel_id"
python -m polytracker.main
```

## Database Connection

### Local Development
```
Host: localhost
Port: 5432
User: polytracker
Password: polytracker_dev
Database: polytracker
URL: postgresql+asyncpg://polytracker:polytracker_dev@localhost:5432/polytracker
```

### Docker Container
```
Host: postgres (internal DNS)
Port: 5432
URL: postgresql+asyncpg://polytracker:polytracker_dev@postgres:5432/polytracker
```

## Schema Overview

### Wallets Table
Tracks high-performing traders.
- `address` (primary key)
- `score`, `win_rate`, `total_pnl`, `roi`
- `is_active` — track only active wallets

### Trades Table
Records of trades executed by tracked wallets.
- `id` (primary key)
- `wallet_address` (foreign key)
- `market_id`, `market_slug`, `market_title`
- `direction`, `price`, `size_usd`, `timestamp`
- **NEW:** `market_resolved`, `resolved_outcome`, `pnl`, `roi_pct`

### Alerts Sent Table
History of Telegram alerts sent.
- Tracks which wallet-market pairs have been alerted

### Backtest Runs Table
Records of backtest executions (Phase 1).
- `run_id`, `created_at`, `start_date`, `end_date`
- `total_signals`, `resolved_signals`, `profitable_signals`
- `win_rate`, `avg_roi`, `total_pnl`

### Signal Performance Table
Detailed outcome tracking for backtesting (Phase 1).
- Tracks each signal: outcome, P&L, ROI
- Links to `backtest_runs` for run grouping

## Next Steps (Phase 2)

After validating Phase 1 analytics:

1. **Trade Execution Layer** — Connect to Polymarket CLOB API
2. **Order Management** — Place orders, track positions
3. **Risk Controls** — Position limits, loss thresholds
4. **Demo Mode** — Test execution safely before live trading

## Troubleshooting

### PostgreSQL connection fails
```bash
# Check container is running
docker-compose -f docker-compose-pg.yml ps

# Check logs
docker-compose -f docker-compose-pg.yml logs postgres

# Restart
docker-compose -f docker-compose-pg.yml restart postgres
```

### Migration fails
```bash
# Verify SQLite database exists
ls -la ./data/polytracker.db

# Check PostgreSQL is accepting connections
psql -h localhost -U polytracker -d polytracker -c "SELECT 1"
```

### Performance queries slow
PostgreSQL already has indexes on common queries. If needed, create additional indexes:
```bash
# Create index on resolved_outcome
docker-compose -f docker-compose-pg.yml exec postgres psql -U polytracker -d polytracker -c "
CREATE INDEX idx_trades_resolved_outcome ON trades(resolved_outcome) WHERE market_resolved = TRUE;
"
```

## Testing on Production Data

You can now run analytics and backtests on your real whale signals:

1. **Collect data** — Let the bot run for a few days, collecting trades
2. **Analyze** — `python scripts/analyze.py` to see performance
3. **Backtest** — `python scripts/backtest.py` to validate signals retroactively
4. **Iterate** — Adjust filters/config based on insights
5. **Proceed to Phase 2** — When confident in signal quality

---

**Status:** Phase 1 ✅ Complete and ready for testing  
**Next Phase:** Phase 2 — Trade Execution Layer  
**Last Updated:** 2026-06-01
