# How to Run PolyTrackerBot

## Quick Start

### Dry Run Mode (Signals Only, No Orders)

```bash
cd /Users/kym/code/openclaw/projects/PolyTrackerBot
./run_dryrun.sh
```

**Logs to:** `logs/dryrun_YYYYMMDD_HHMMSS.log`

What happens:
- ✅ Detects whale signals
- ✅ Logs everything
- ❌ **ZERO orders placed** (testing only)

### Demo Mode (Paper Trading)

```bash
cd /Users/kym/code/openclaw/projects/PolyTrackerBot
./run_demo.sh
```

**Logs to:** `logs/demo_YYYYMMDD_HHMMSS.log`

What happens:
- ✅ Detects whale signals
- ✅ Places paper orders at live prices
- ✅ Tracks P&L (no real money)
- ✅ Enforces risk limits

## Monitoring Logs

### Real-time tail

```bash
tail -f logs/dryrun_*.log
```

### Filter for signals

```bash
tail -f logs/dryrun_*.log | grep "Processing signal\|DRY RUN\|Risk check"
```

### Filter for execution (demo mode)

```bash
tail -f logs/demo_*.log | grep "Processing signal\|Demo execution\|Order"
```

## Dashboard

### Start Dashboard (in another terminal)

```bash
cd /Users/kym/code/openclaw/projects/PolyTrackerBot/dashboard
npm install  # first time only
npm run dev
```

Opens at `http://localhost:3000`

**Dashboard shows:**
- Live signals (real-time feed)
- Order status (dry run / demo / live)
- Positions and P&L
- Risk events and alerts
- Mode indicator and stats

## Directory Structure

```
PolyTrackerBot/
├── run_dryrun.sh          ← Start dry run (signals only)
├── run_demo.sh            ← Start demo (paper trading)
├── logs/                  ← Log files appear here
│   ├── dryrun_*.log
│   └── demo_*.log
├── dashboard/             ← Web UI
│   └── src/
└── polytracker/           ← Bot code
```

## Full Timeline

| Time | Command | What Happens | Logs |
|------|---------|--------------|------|
| 4pm-5pm | `./run_dryrun.sh` | Detect signals, no orders | `logs/dryrun_*.log` |
| 5pm | Stop dry run, start dashboard | Launch web UI | N/A |
| 5pm onward | `./run_demo.sh` | Paper trade at live prices | `logs/demo_*.log` |

## Database Requirements

**PostgreSQL must be running:**

```bash
docker-compose -f docker-compose-pg.yml up -d postgres
```

Verify connection:

```bash
psql -h localhost -U polytracker -d polytracker -c "SELECT NOW();"
```

## Troubleshooting

### "ModuleNotFoundError: No module named..."

Venv not activated. The scripts activate it automatically, but if running manually:

```bash
source venv/bin/activate
python -m polytracker.main
```

### "Connection refused" (PostgreSQL)

PostgreSQL not running:

```bash
docker-compose -f docker-compose-pg.yml up -d postgres
docker-compose -f docker-compose-pg.yml ps  # verify it's running
```

### Logs not appearing

Check log directory exists:

```bash
ls -la logs/
```

If missing:

```bash
mkdir -p logs
```

### Dashboard not connecting

WebSocket not yet wired (coming in Phase 3). Dashboard shows mock data for now.

To connect real data: Update `dashboard/src/hooks/useWebSocket.ts` with backend URL.

## Log File Locations

**Dry Run:**
```
/Users/kym/code/openclaw/projects/PolyTrackerBot/logs/dryrun_20260601_160000.log
```

**Demo:**
```
/Users/kym/code/openclaw/projects/PolyTrackerBot/logs/demo_20260601_170000.log
```

**Tail in real-time:**
```bash
tail -f /Users/kym/code/openclaw/projects/PolyTrackerBot/logs/*.log
```

---

## Summary

**Dry Run:** `./run_dryrun.sh` → Logs to `logs/dryrun_*.log`  
**Demo:** `./run_demo.sh` → Logs to `logs/demo_*.log`  
**Dashboard:** `cd dashboard && npm run dev` → Opens localhost:3000

Ready? Start the scripts and watch the logs!
