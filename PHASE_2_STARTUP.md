# Phase 2: Paper Trading with Dashboard

## Overview
Phase 2 involves running the bot in PAPER trading mode while displaying real-time execution in the Vue.js dashboard.

## Prerequisites
✅ Dry run completed (signals detected, logs clean)
✅ Bot process can be started/stopped
✅ Dashboard framework is ready

## Startup Instructions

### Step 1: Install Dashboard Dependencies
```bash
cd ~/code/openclaw/projects/PolyTrackerBot/dashboard
npm install
```

### Step 2: Start the Dashboard (Terminal 1)
```bash
cd ~/code/openclaw/projects/PolyTrackerBot/dashboard
npm run dev
# Dashboard will be available at http://localhost:5173
```

### Step 3: Start the Bot in Paper Mode (Terminal 2)
```bash
cd ~/code/openclaw/projects/PolyTrackerBot
cp .env.phase2 .env  # Load paper trading config
source venv/bin/activate
python -m polytracker.main
```

### Step 4: Monitor in Real-Time (Terminal 3)
```bash
cd ~/code/openclaw/projects/PolyTrackerBot
tail -f logs/polytracker.log | grep -E "Signal|Trade|Risk|Paper"
```

## What to Expect

### Dashboard (Port 5173)
- Real-time signal feed
- Execution status
- Paper trade history
- Risk monitor
- Wallet scores
- Market status

### Log Output
```
👁️ Monitoring wallets...
🐋 Signal detected: [Market] [Direction]
  ✅ Risk check passed
  📄 PAPER TRADE: [Order details]
  ✅ Trade logged: ID [order_id]
```

### Signals
- From tracked whale wallets entering new markets
- Filtered through 7-point viability check
- Paper trades execute without real orders
- Full order details logged for backtesting

## Configuration (PAPER Mode)
```
EXECUTION_MODE=PAPER
```
- ✅ Signals detected normally
- ✅ Risk checks enforced
- ✅ Paper trades executed (logged, not real)
- ✅ Dashboard updates in real-time
- ❌ No actual orders placed

## Success Criteria
- [ ] Dashboard loads at localhost:5173
- [ ] Bot starts without errors
- [ ] Wallet discovery runs (every 6h, but log shows startup scan)
- [ ] Trade monitoring active (every 5 minutes)
- [ ] Dashboard shows live signal feed
- [ ] Paper trades logged to database

## Troubleshooting

### Dashboard won't start
```bash
# Check node version
node --version  # Should be 18+

# Rebuild dependencies
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Bot won't connect to dashboard
- Ensure bot is writing to SQLite at `./data/polytracker.db`
- Dashboard queries this database for live data
- Verify database path in .env matches

### No signals detected
- Check Polymarket API status
- Verify leaderboard wallets exist
- Check logs for API errors (404 means wallet not found - expected)

## Next Steps
1. Observe 30+ minutes of paper trading
2. Verify risk constraints are enforced
3. Check dashboard data accuracy
4. Monitor for any errors or anomalies
5. Once confident, transition to Phase 3 (live trading with real orders in DEMO mode)

---
**Phase:** 2/4 — Paper Trading
**Start Time:** [Set when you run]
**Duration:** Recommended 30+ minutes minimum
**Status:** Ready to launch
