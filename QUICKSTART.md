# PolyTracker Bot — Quick Start (5 Minutes)

## Prerequisites

- Python 3.11+
- Telegram account
- 5 minutes

## Step 1: Get Telegram Bot Token

1. Open Telegram, search for `@BotFather`
2. Type `/start` then `/newbot`
3. Follow prompts to name your bot
4. **Save the token** (e.g., `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

## Step 2: Create/Get Channel ID

1. Create a Telegram channel (e.g., `@polytracker`)
2. Add your bot as admin
3. Forward any message to `@userinfobot`
4. **Save the CHANNEL_ID** (format: `-100123456789`)

## Step 3: Setup PolyTracker

```bash
cd ~/code/openclaw/projects/PolyTrackerBot

# Copy and edit config
cp .env.example .env

# Edit .env with your values:
#   TELEGRAM_BOT_TOKEN=your_token_here
#   TELEGRAM_CHANNEL_ID=-100...
```

## Step 4: Install & Run

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the bot
python -m polytracker.main
```

You should see:
```
INFO     | 🚀 PolyTracker Bot starting...
INFO     | ✅ Database connected: ./data/polytracker.db
INFO     | ✅ Scheduler started with 5 jobs
INFO     | 📡 PolyTracker Bot is running. Press Ctrl+C to stop.
```

## Step 5: Test

Press `Ctrl+C` to stop. Bot will:
- Discover wallets every 6 hours
- Poll for new positions every 5 minutes
- Send Telegram alerts when signals match

## Running with Docker

```bash
docker-compose up --build
```

## Configuration

All settings in `.env`:

| Setting | Default | Description |
|---------|---------|-------------|
| `MIN_WIN_RATE` | 0.60 | Wallet must have 60%+ win rate |
| `MIN_TOTAL_PNL` | 5000 | Wallet must have $5k+ lifetime profit |
| `MIN_SIGNAL_POSITION` | 500 | Only alert on $500+ positions |
| `MIN_MARKET_LIQUIDITY` | 10000 | Market must have $10k+ liquidity |
| `MIN_HOURS_REMAINING` | 48 | Market must have 48+ hours to close |

---

**Next:** Read [README.md](README.md) for full documentation.

**Issues?** Check logs in `logs/polytracker.log`
