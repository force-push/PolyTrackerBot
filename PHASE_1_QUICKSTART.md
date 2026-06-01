# Phase 1 Quick Start (5 minutes)

## TL;DR

Get PostgreSQL running and test analytics on your whale signals.

### 1. Install + Start Database

```bash
cd ~/code/openclaw/projects/PolyTrackerBot

# Install new dependencies
pip install sqlalchemy asyncpg alembic

# Start PostgreSQL
docker-compose -f docker-compose-pg.yml up -d postgres

# Wait ~5 seconds for health check to pass
sleep 5
docker-compose -f docker-compose-pg.yml ps
```

### 2. (Skip if no existing data) Migrate from SQLite

```bash
export DATABASE_URL="postgresql+asyncpg://polytracker:polytracker_dev@localhost:5432/polytracker"
python scripts/migrate_to_postgres.py
```

### 3. Test Analytics

```bash
# Summary view
python scripts/analyze.py

# Detailed wallet performance
python scripts/analyze.py wallets

# Signal performance (last 30 days)
python scripts/analyze.py perf

# Recent signals (last 20)
python scripts/analyze.py trades
```

### 4. Run Backtest (on all historical data)

```bash
python scripts/backtest.py
```

Output shows:
- Total signals tracked
- Resolved signals (market closed)
- Win rate
- Average ROI
- Total P&L

### 5. Run Bot with PostgreSQL

```bash
export DATABASE_URL="postgresql+asyncpg://polytracker:polytracker_dev@localhost:5432/polytracker"
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHANNEL_ID="your_channel_id"

python -m polytracker.main
```

## What's Available Now

| Tool | Purpose | Usage |
|------|---------|-------|
| `analyze.py` | Performance metrics | `python scripts/analyze.py` |
| `backtest.py` | Signal validation | `python scripts/backtest.py` |
| `migrate_to_postgres.py` | SQLite → PostgreSQL | `python scripts/migrate_to_postgres.py` |

## Database Details

- **Server:** localhost:5432
- **User:** polytracker
- **Password:** polytracker_dev
- **Database:** polytracker
- **Container:** polytracker-postgres

## Next: You Can Now...

✅ **View wallet performance** - see which traders are most reliable  
✅ **Analyze signal accuracy** - validate whale signals work  
✅ **Run backtests** - test ideas on production data  
✅ **Export JSON** - integrate with other tools  

## Docs

- Full setup: `PHASE_1_SETUP.md`
- Next phase: `Phase 2 — Trade Execution` (coming soon)

---

Need help? Check `PHASE_1_SETUP.md` for detailed setup + troubleshooting.
