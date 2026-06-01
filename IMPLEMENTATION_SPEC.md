# PolyTracker Bot — Implementation Specification

**Status:** Phase 0 ✅ Complete  
**Next:** Phases 1-3 (core engine → signals → hardening)

---

## What's Already Done

✅ **Verified Polymarket API endpoints** (Data, Gamma, CLOB)  
✅ **Project structure** created  
✅ **Config system** (env-based, typed dataclasses)  
✅ **Database schema** (SQLite with aiosqlite)  
✅ **HTTP client stub** (async, rate-limiting, retry logic)  
✅ **README** with full API reference + setup guide  
✅ **requirements.txt** (all deps)  
✅ **main.py template** (entry point)  

---

## Your Mission: Phases 1-3

### Phase 1: Core Engine (2-3 hours)

**Files to implement:**

#### `polymarket/wallet_scanner.py`
- Class: `WalletScanner(config, db)`
- Methods:
  - `async discover_wallets()` — Fetch top 100-200 traders from leaderboard, score, filter, persist
  - `async rescore_wallets()` — Re-evaluate all active wallets monthly
  - Score formula: `(win_rate*40) + (log(pnl)*20) + (roi*20) + (recency*20)`
- Uses: `polymarket/client.py`, `signals/scorer.py`

#### `signals/scorer.py`
- Function: `calculate_wallet_score(wallet_stats: dict) -> float`
- Inputs: win_rate, total_pnl, roi, last_trade_date
- Output: Score 0-100
- Edge cases: Handle missing fields, invalid dates, log(0)

#### `polymarket/trade_monitor.py`
- Class: `TradeMonitor(config, db, telegram_bot)`
- Methods:
  - `async monitor_wallets()` — For each active wallet:
    1. Fetch recent positions from `/v1/user/{address}/positions`
    2. Compare against `trades` table to find NEW trades only
    3. For each new trade, call `signals/filter.py` to check viability
    4. If viable, call `telegram/alerts.py` to send alert
    5. Persist trade + mark alert as sent
- Uses: `polymarket/client.py`, `signals/filter.py`, `telegram/alerts.py`

---

### Phase 2: Signals & Alerts (1-2 hours)

**Files to implement:**

#### `signals/filter.py`
- Function: `async is_viable_signal(trade: dict, market: dict, wallet: dict) -> tuple[bool, str, str]`
- Returns: `(is_viable: bool, alert_type: str, reason: str)`
  - `alert_type`: 'standard' or 'high_conviction'
  - `reason`: Why signal passed/failed
- Checks (ALL must pass):
  1. Market still open (not resolved)
  2. Position size ≥ `MIN_SIGNAL_POSITION` (default $500)
  3. Liquidity ≥ `MIN_MARKET_LIQUIDITY` (default $10k)
  4. Hours remaining ≥ `MIN_HOURS_REMAINING` (default 48)
  5. No previous alert for this wallet-market pair
  6. Direction matches wallet's historical edge in category (optional; skip if data unavailable)
  7. New position (not update to existing)
- High conviction detection: If 2+ active wallets have alerts on same market → upgrade to `high_conviction`
- Uses: `db.py`, `polymarket/client.py`

#### `telegram/bot.py`
- Class: `TelegramBot(telegram_config)`
- Methods:
  - `async send_message(channel_id: str, message: str, parse_mode: str = "HTML")`
  - `async send_alert(alert_type: str, data: dict)` — Dispatch to alerts.py

#### `telegram/alerts.py`
- Function: `format_standard_alert(wallet: dict, trade: dict, market: dict) -> str`
- Function: `format_high_conviction_alert(wallets: list, market: dict) -> str`
- Uses templates from README (HTML format for Telegram)
- Returns HTML-formatted message string
- Uses: `telegram/bot.py` to send

---

### Phase 3: Hardening & Deployment (1 hour)

**Files to implement:**

#### `scheduler.py`
- Function: `start_scheduler(config, wallet_scanner, trade_monitor, telegram_bot) -> APScheduler.Scheduler`
- Jobs:
  1. **discover_wallets** — Every 6h — `wallet_scanner.discover_wallets()`
  2. **rescore_wallets** — Every 24h — `wallet_scanner.rescore_wallets()`
  3. **poll_trades** — Every 5min — `trade_monitor.monitor_wallets()`
  4. **check_closures** — Every 1h — Delete resolved trades from DB
  5. **daily_digest** — 08:00 UTC daily — Summarize day's signals
- Error handling: Catch + log each job exception individually (don't crash scheduler)
- Use: `apscheduler.schedulers.asyncio.AsyncIOScheduler`

#### `tests/`
- `test_scorer.py` — Unit tests for scoring formula
- `test_filter.py` — Unit tests for signal filter
- `conftest.py` — Fixtures (mock DB, mock API responses)
- Run: `pytest tests/ -v`

#### Docker setup
- `Dockerfile` — Python 3.11 base, install deps, run `python -m polytracker.main`
- `docker-compose.yml` — For local dev (mounts .env, data volume)

#### Documentation
- `QUICKSTART.md` — 5-minute setup guide
- `API_ENDPOINTS.md` — Full Polymarket endpoint reference (already in README)

---

## Key Implementation Notes

### Database Access
- Always use `async` methods: `db.get_active_wallets()`, `db.upsert_trade()`, etc.
- Never block the event loop with sync DB calls
- Use `db.has_alert_for_market()` to prevent duplicate alerts

### API Client Usage
```python
async with PolymarketClient(config.polymarket) as client:
    leaderboard = await client.get_trader_leaderboard(limit=100)
    positions = await client.get_wallet_positions(address)
    market = await client.get_market_by_slug(slug)
```

### Logging
- Use `loguru` consistently: `logger.info()`, `logger.error()`, etc.
- Log all alerts sent with wallet, market, size, score
- Log API errors without crashing (already handled in client.py)

### Error Handling
- Wrap all Telegram sends in try/except (log, don't raise)
- All DB operations must be wrapped (transaction safety)
- API failures should be logged but not stop the scheduler

### Testing
- Use `pytest-asyncio` for async tests
- Mock Polymarket API responses (fixture in conftest.py)
- Mock Telegram sends (don't actually send during tests)
- Test scoring formula with edge cases (log of zero, missing fields)

---

## Scoring Formula Reference

```python
import math

def calculate_wallet_score(stats: dict) -> float:
    """
    score = (win_rate * 40) + (log(total_pnl) * 20) + (roi * 20) + (recency_bonus * 20)
    """
    win_rate = stats.get('win_rate', 0)
    total_pnl = stats.get('total_pnl', 1)  # Avoid log(0)
    roi = stats.get('roi', 0)
    last_trade_days_ago = stats.get('last_trade_days_ago', 999)
    
    # Recency bonus
    if last_trade_days_ago < 7:
        recency = 1.0
    elif last_trade_days_ago < 30:
        recency = 0.5
    else:
        recency = 0.0
    
    # Calculate components
    win_score = win_rate * 40
    pnl_score = max(0, math.log(max(1, total_pnl)) * 20)
    roi_score = roi * 20
    recency_score = recency * 20
    
    total = win_score + pnl_score + roi_score + recency_score
    return min(100, max(0, total))  # Clamp 0-100
```

---

## Alert Format Examples

### Standard
```
📡 POLYTRACKER SIGNAL

Wallet: 0x1234...abcd [Score: 87/100]
Win Rate: 73% | PnL: $24,300 | ROI: +142%

📌 Market: "Will X happen by Dec 31?"
Position: YES @ 34¢
Size: $1,200
Liquidity: $85,400
Closes: 14d 6h

🔗 Market: https://polymarket.com/event/will-x-happen
🔗 Wallet: https://polymarket.com/profile/0x1234...abcd

Risk: MEDIUM | Confidence: HIGH
```

### High Conviction
```
🔥 HIGH CONVICTION — POLYTRACKER

2 tracked whales entered the same market!

Wallets:
 • 0x1234...abcd (Score: 87) → YES @ 34¢ ($1,200)
 • 0x5678...efgh (Score: 91) → YES @ 36¢ ($3,400)

📌 "Will X happen by Dec 31?"
Combined Position: $4,600
Liquidity: $85,400
Closes: 14d 6h

🔗 https://polymarket.com/event/will-x-happen
```

---

## Testing Checklist

- [ ] Scorer handles edge cases (log(0), missing fields)
- [ ] Filter rejects positions < $500 size
- [ ] Filter detects market closures correctly
- [ ] Dedup logic prevents duplicate alerts
- [ ] Scheduler runs all 5 jobs without crashing
- [ ] Telegram sends format correctly (no HTML injection)
- [ ] Database transactions don't deadlock
- [ ] Rate limiter doesn't exceed 10 req/sec
- [ ] Logging captures all alerts to file

---

## Deliverables

1. ✅ All source files in `polytracker/` (8 new files)
2. ✅ Test suite with 70%+ coverage
3. ✅ `.env.example` → `.env` setup guide
4. ✅ Docker + docker-compose
5. ✅ Run with: `python -m polytracker.main`

---

## Questions to Ask Yourself

1. **Is the wallet filtering correct?** Review MIN_* thresholds against leaderboard data
2. **Can alerts be duplicated?** Check `has_alert_for_market()` is called before sending
3. **Will the bot survive an API outage?** All HTTP errors are caught, logged, not fatal
4. **Is the database thread-safe?** Using aiosqlite (async), not multi-threaded
5. **Can Telegram failures crash the bot?** All bot sends wrapped in try/except

---

*Good luck! You've got this. 🚀*
