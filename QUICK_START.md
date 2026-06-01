# Quick Start - Phase 3 Demo Trading

## One-Command Startup

```bash
cd ~/code/openclaw/projects/PolyTrackerBot
./START_EVERYTHING.sh
```

This starts:
- ✅ Bot (DEMO mode, real orders on demo account)
- ✅ API Server (port 8000, mode control)
- ✅ Dashboard (port 3000, UI monitoring)

## What Gets Started

### 1. Bot Process
- Location: `polytracker/main.py`
- Mode: DEMO (can be changed via API)
- Monitoring: Every 5 minutes for whale signals
- Logging: `logs/bot.log` + `logs/polytracker.log`

### 2. API Server
- Location: `polytracker/api/server.py`
- Port: 8000
- Purpose: Mode control, configuration
- Logging: `logs/api.log`

### 3. Dashboard
- Location: `dashboard/` (Vite dev server)
- Port: 3000
- Purpose: Real-time monitoring & mode switching
- Logging: `logs/dashboard.log`

## Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| Dashboard | http://localhost:3000 | Monitor signals, switch modes |
| API Info | http://localhost:8000/api/mode/info | Get mode info |
| API Current | http://localhost:8000/api/mode/current | Check current mode |

## Dashboard Mode Switching

1. Open http://localhost:3000
2. Find "Execution Mode" panel (right side)
3. Click button for desired mode:
   - **Dry Run** — Logging only, no orders
   - **Demo** — Real orders on demo account
   - **Live** — Real money (requires confirmation)
4. See success/error message
5. Restart bot to apply new mode
6. Bot will use new mode immediately after restart

## Example: Switch to DEMO

```bash
# Get current mode
curl http://localhost:8000/api/mode/current

# Switch to DEMO
curl -X POST http://localhost:8000/api/mode/set \
  -H "Content-Type: application/json" \
  -d '{"mode": "DEMO"}'

# Verify change
curl http://localhost:8000/api/mode/current
```

## Monitoring

### Watch all activity
```bash
tail -f logs/polytracker.log
```

### Watch bot only
```bash
tail -f logs/bot.log
```

### Watch API only
```bash
tail -f logs/api.log
```

### Watch for signals
```bash
tail -f logs/polytracker.log | grep -i signal
```

### Watch for mode changes
```bash
tail -f logs/polytracker.log | grep -i mode
```

## Troubleshooting

### "Failed to connect to API"
API server hasn't started. Check:
```bash
lsof -Pi :8000
# Should show Python process listening on 8000

# If not running, start it:
source venv/bin/activate
python -m polytracker.api.server
```

### "Failed to fetch" error
Port 3000 and 8000 must both be running. Start with:
```bash
./START_EVERYTHING.sh
```

### Dashboard won't load
```bash
# Check if Vite server is running
lsof -Pi :3000

# Check logs
tail logs/dashboard.log

# Reinstall deps if needed
cd dashboard && npm install && cd ..
npm run dev
```

### Bot not running
```bash
# Check if process exists
pgrep -f "python -m polytracker"

# Check logs
tail logs/bot.log

# Restart
source venv/bin/activate
python -m polytracker.main
```

## Log Files

All logs stored in `logs/`:
- `polytracker.log` — Main bot activity
- `bot.log` — Bot output
- `api.log` — API server output
- `dashboard.log` — Dashboard build output

## Stopping Services

From the `START_EVERYTHING.sh` output, get the PIDs and kill them:

```bash
kill $BOT_PID $API_PID $DASHBOARD_PID
```

Or just Ctrl+C the running script.

## Advanced: Manual Startup

If you prefer to start services individually:

### Terminal 1 - Bot
```bash
source venv/bin/activate
python -m polytracker.main
```

### Terminal 2 - API
```bash
source venv/bin/activate
python -m polytracker.api.server
```

### Terminal 3 - Dashboard
```bash
cd dashboard
npm run dev
```

---

**Status:** Ready to go!  
**Next:** Watch for whale signals in logs and test mode switching from dashboard.
