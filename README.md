# PolyTracker Bot — Polymarket Whale Tracker

A production-grade Python bot that monitors high-performing wallets on [Polymarket](https://polymarket.com) and sends Telegram alerts when they make profitable trade signals.

## Overview

**What it does:**
1. Discovers and scores the top-performing wallets on Polymarket
2. Tracks only wallets that meet profitability thresholds (60%+ win rate, $5k+ lifetime profit, etc.)
3. Polls tracked wallets every 5 minutes for new positions
4. Sends **Telegram alerts** with direct market links when high-conviction signals are detected
5. Supports "high conviction" alerts when 2+ whales enter the same market

**Why it matters:**
Following consistent winners on prediction markets can improve decision-making and reduce research overhead.

---

## Tech Stack

- **Language:** Python 3.11+
- **Async HTTP:** `httpx` with retry logic & rate limiting
- **Scheduler:** APScheduler (5-minute polling + daily digest)
- **Database:** SQLite (with aiosqlite)
- **Telegram:** `python-telegram-bot` v20+
- **Logging:** `loguru`
- **Config:** `python-dotenv`

---

## Project Structure

```
PolyTrackerBot/
├── polytracker/
│   ├── __init__.py
│   ├── config.py              # Load config from .env
│   ├── db.py                  # SQLite database + queries
│   ├── main.py                # Entry point
│   ├── scheduler.py           # APScheduler job definitions
│   │
│   ├── polymarket/
│   │   ├── __init__.py
│   │   ├── client.py          # Async Polymarket API client
│   │   ├── wallet_scanner.py  # Discover & score wallets
│   │   └── trade_monitor.py   # Poll tracked wallets for new positions
│   │
│   ├── signals/
│   │   ├── __init__.py
│   │   ├── filter.py          # Apply 7 viability filters
│   │   └── scorer.py          # Wallet scoring formula
│   │
│   └── telegram/
│       ├── __init__.py
│       ├── bot.py             # Telegram bot setup
│       └── alerts.py          # Format & send alerts
│
├── tests/
│   ├── test_scorer.py
│   ├── test_filter.py
│   └── conftest.py
│
├── .env.example               # Template (copy to .env)
├── requirements.txt           # Dependencies
├── Dockerfile                 # Container setup
├── docker-compose.yml         # Local dev
└── README.md                  # This file
```

---

## Verified Polymarket API Endpoints

### Data API (`https://data-api.polymarket.com`)
All endpoints are **public** — no authentication required.

| Endpoint | Purpose |
|---|---|
| `GET /v1/leaderboard` | Top traders by PnL or volume |
| `GET /v1/user/{address}/positions` | Current open positions |
| `GET /v1/user/{address}/trades` | Recent trade history |
| `GET /v1/user/{address}/activity` | Recent activity stream |
| `GET /v1/profiles/{address}/public-profile` | Public wallet stats (PnL, win rate, vol) |

**Parameters for leaderboard:**
- `category`: OVERALL, POLITICS, SPORTS, CRYPTO, CULTURE, etc. (default: OVERALL)
- `timePeriod`: DAY, WEEK, MONTH, ALL (default: DAY)
- `orderBy`: PNL or VOL (default: PNL)
- `limit`: 1-50 (default: 25)
- `offset`: Pagination (default: 0)

### Gamma API (`https://gamma-api.polymarket.com`)
Market & event metadata (no auth).

| Endpoint | Purpose |
|---|---|
| `GET /v1/markets/{slug}` | Market details by slug |
| `GET /v1/conditions/{id}` | Market details by condition ID |

### CLOB API (`https://clob.polymarket.com`)
Orderbook & pricing (public endpoints only).

| Endpoint | Purpose |
|---|---|
| `GET /v1/prices/midpoint` | Current midpoint price |
| `GET /v1/orderbook?token_id=...` | Liquidity estimate |

---

## Setup Instructions

### 1. Create Telegram Bot

1. Message `@BotFather` on Telegram
2. Type `/start` then `/newbot`
3. Follow prompts to name your bot
4. Save the **bot token** (e.g., `123456789:ABCdefGHIjkLmNoPQRstUVWxYzAbcD...`)

### 2. Create/Get Channel ID

1. Create a channel (e.g., `@polytracker`) or use existing one
2. Add your bot as admin
3. Forward any message to `@userinfobot` to get the `CHANNEL_ID`
   - Look for `-100...` format (e.g., `-1001234567890`)

### 3. Clone & Setup

```bash
cd ~/code/openclaw/projects
git clone <repo-url> PolyTrackerBot
cd PolyTrackerBot

# Copy and fill config
cp .env.example .env
# Edit .env:
#   TELEGRAM_BOT_TOKEN=your_token
#   TELEGRAM_CHANNEL_ID=-100...
```

### 4. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Run Locally

```bash
python -m polytracker.main
```

You should see:
```
INFO     | PolyTracker Bot started
INFO     | Scheduler running with 5 jobs
INFO     | Wallet discovery job scheduled for every 6 hours
...
```

---

## Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | (required) | Bot token from @BotFather |
| `TELEGRAM_CHANNEL_ID` | (required) | Channel ID (with `-100` prefix) |
| `MIN_WIN_RATE` | 0.60 | Minimum win rate (0-1) |
| `MIN_TOTAL_PNL` | 5000 | Minimum lifetime PnL in USD |
| `MIN_TRADES` | 25 | Minimum trade count for validity |
| `MIN_AVG_POSITION` | 200 | Minimum average position size USD |
| `MIN_VOLUME_30D` | 2000 | Minimum 30-day volume USD |
| `MAX_WALLETS_TRACKED` | 50 | Max tracked wallets at once |
| `MIN_SIGNAL_POSITION` | 500 | Minimum position size to alert USD |
| `MIN_MARKET_LIQUIDITY` | 10000 | Minimum market liquidity USD |
| `MIN_HOURS_REMAINING` | 48 | Minimum hours until market close |
| `POLL_TRADES_INTERVAL_MINUTES` | 5 | How often to check for new positions |
| `DATABASE_PATH` | `./data/polytracker.db` | SQLite database path |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

---

## Scheduler Jobs

| Job | Frequency | Purpose |
|---|---|---|
| **discover_wallets** | Every 6 hours | Find new high-performing wallets |
| **rescore_wallets** | Every 24 hours | Re-evaluate existing wallets |
| **poll_trades** | Every 5 minutes | Check tracked wallets for new positions |
| **check_closures** | Every 1 hour | Cleanup resolved/closed markets |
| **daily_digest** | 08:00 UTC daily | Send summary of day's signals |

---

## Alert Format

### Standard Alert (1 whale)

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

### High Conviction Alert (2+ whales same market)

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

## Database Schema

### wallets
```sql
- address (PRIMARY KEY)
- score (0-100)
- win_rate (0-1)
- total_pnl (USD)
- roi (%)
- volume_30d (USD)
- avg_position (USD)
- total_trades (int)
- last_seen (timestamp)
- added_at (timestamp)
- is_active (bool)
```

### trades
```sql
- id (PRIMARY KEY)
- wallet_address (FK)
- market_id
- market_slug
- market_title
- direction (YES/NO)
- price (0-1)
- size_usd
- timestamp
- market_closes (timestamp)
- alerted (bool)
```

### alerts_sent
```sql
- id (PRIMARY KEY)
- wallet_address (FK)
- market_id
- sent_at (timestamp)
- alert_type ('standard' or 'high_conviction')
```

---

## Wallet Scoring Formula

```
score = (win_rate * 40) + (log(total_pnl) * 20) + (roi * 20) + (recency_bonus * 20)

recency_bonus:
  1.0 if last_trade < 7 days
  0.5 if 7-30 days
  0.0 if > 30 days
```

---

## Signal Viability Filter (All 7 Must Pass)

1. ✅ Tracked wallet opens **new position**
2. ✅ Market is **still open** (not resolved)
3. ✅ Position size **≥ $500** (configurable)
4. ✅ Market liquidity **≥ $10,000** (configurable)
5. ✅ **≥ 48 hours** remaining (configurable)
6. ✅ **No previous alert** for this wallet-market pair
7. ✅ Position direction matches wallet's **historical edge** in category

---

## Docker Deployment

### Build & Run Locally

```bash
docker-compose up --build
```

### Production Deployment

```bash
docker build -t polytracker:latest .
docker run -d \
  --name polytracker \
  -e TELEGRAM_BOT_TOKEN=... \
  -e TELEGRAM_CHANNEL_ID=... \
  --restart=always \
  -v $(pwd)/data:/app/data \
  polytracker:latest
```

### Systemd Service (Linux)

Create `/etc/systemd/system/polytracker.service`:

```ini
[Unit]
Description=PolyTracker Bot
After=network.target

[Service]
Type=simple
User=bot
WorkingDirectory=/home/bot/PolyTrackerBot
Environment="PATH=/home/bot/PolyTrackerBot/venv/bin"
EnvironmentFile=/home/bot/PolyTrackerBot/.env
ExecStart=/home/bot/PolyTrackerBot/venv/bin/python -m polytracker.main
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable & start:
```bash
sudo systemctl enable polytracker
sudo systemctl start polytracker
sudo journalctl -u polytracker -f  # Watch logs
```

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_scorer.py -v

# With coverage
pytest tests/ --cov=polytracker --cov-report=html
```

---

## Monitoring & Troubleshooting

### Check Logs

```bash
# Local
tail -f logs/polytracker.log

# Docker
docker logs -f polytracker

# Systemd
journalctl -u polytracker -f
```

### Common Issues

| Issue | Solution |
|---|---|
| Bot not sending alerts | Check `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHANNEL_ID` in `.env` |
| "Rate limited" errors | Reduce `MAX_REQUESTS_PER_SECOND` or increase polling interval |
| Missing wallets | Run wallet discovery job manually: `python -m polytracker.main --discover-now` |
| Database locked | Ensure only one instance is running; check `data/polytracker.db` permissions |

---

## Future Enhancements (V2)

- [ ] Web dashboard (React UI)
- [ ] Webhook support (replace polling with real-time events)
- [ ] Wallet clustering by trading style
- [ ] Backtesting framework
- [ ] Position sizing advice (Kelly Criterion)
- [ ] Multi-platform alerts (Discord, SMS)
- [ ] GraphQL API for custom queries

---

## License

TBD

---

## Support

- **Issues:** Open a GitHub issue
- **Questions:** See `/docs` folder or check `AGENTS.md`

---

*Built with Python, APScheduler, and caffeine. ⚡*
