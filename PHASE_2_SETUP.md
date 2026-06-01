# Phase 2: Setup & Configuration Guide

## Prerequisites

✅ Phase 1 complete (PostgreSQL, data layer, analytics)  
✅ Whale signals being detected and tracked  
✅ Latest code from `polytracker/execution/` and `polytracker/models_execution.py`

## Configuration

### Environment Variables

Add to `.env`:

```bash
# Execution Mode
EXECUTION_MODE=demo              # Options: dry_run, demo, live

# Position Sizing
DEFAULT_POSITION_SIZE_USD=500    # Starting position size
MAX_POSITION_SIZE_USD=50000      # Hard limit per order

# Risk Management
MAX_DAILY_LOSS_USD=5000          # Stop trading after this daily loss
MAX_DAILY_VOLUME_USD=50000       # Max total volume per day
MAX_CONCURRENT_POSITIONS=10      # Max open positions at once

# Signal Detection (existing)
MIN_WHALE_WIN_RATE=0.60
MIN_MARKET_LIQUIDITY_USD=10000
MIN_HOURS_REMAINING=48
```

### Safe Defaults by Mode

**Testing (Dry Run):**
```bash
EXECUTION_MODE=dry_run
DEFAULT_POSITION_SIZE_USD=0      # No positions (logging only)
```

**Validation (Demo):**
```bash
EXECUTION_MODE=demo
DEFAULT_POSITION_SIZE_USD=100    # Small position size
MAX_POSITION_SIZE_USD=5000       # Keep it small
MAX_DAILY_LOSS_USD=1000
MAX_DAILY_VOLUME_USD=10000
```

**Production (Live):**
```bash
EXECUTION_MODE=live
DEFAULT_POSITION_SIZE_USD=500    # Larger positions
MAX_POSITION_SIZE_USD=50000
MAX_DAILY_LOSS_USD=10000         # Higher tolerance
MAX_DAILY_VOLUME_USD=100000
```

## Database Setup

Phase 2 creates new tables automatically via SQLAlchemy.

### Verify Tables Exist

Connect to PostgreSQL and check:

```bash
# Using psql
psql -h localhost -U polytracker -d polytracker

# List new tables (Phase 2)
\dt orders
\dt positions
\dt risk_events
\dt execution_stats

# Should show all 4 tables
```

Or verify programmatically:

```python
import asyncio
from polytracker.db_pg import AsyncDatabase

async def verify():
    db = AsyncDatabase()
    await db.connect()
    # If no error, schema is initialized
    print("✅ Tables ready")
    await db.disconnect()

asyncio.run(verify())
```

## Integration (Main Bot)

### 1. Update main.py

Add Phase 2 imports and orchestrator:

```python
# At top of polytracker/main.py
from polytracker.execution.orchestrator import TradeOrchestrator
from polytracker.models_execution import ExecutionMode

# In main():
# Initialize orchestrator
orchestrator = None
if hasattr(config, 'execution_mode') and config.execution_mode != 'dry_run':
    exec_mode = ExecutionMode(config.execution_mode)
    orchestrator = TradeOrchestrator(config, db, exec_mode)
    logger.info(f"✅ Execution initialized: {exec_mode}")

# Pass to TradeMonitor
trade_monitor = TradeMonitor(config, db, telegram_bot, orchestrator)
```

### 2. Update trade_monitor.py

Wire orchestrator into signal processing:

```python
# In TradeMonitor.monitor_wallets():
if is_viable:
    # Existing: Send alert
    await self._send_position_alert(wallet, position, alert_type, client)
    
    # NEW: Execute order if orchestrator available
    if self.orchestrator:
        await self.orchestrator.process_signal(
            whale_wallet=wallet['address'],
            market_id=market_id,
            market_slug=market_slug,
            market_title=market_title,
            direction=direction,
            whale_entry_price=entry_price,
            whale_position_size=position_size,
            signal_strength=1.0,
            alert_type=alert_type,
        )
```

### 3. Update config.py

Add Phase 2 settings to AppConfig:

```python
# In AppConfig dataclass
execution_mode: str
default_position_size_usd: float
max_position_size_usd: float
max_daily_loss_usd: float
max_daily_volume_usd: float
max_concurrent_positions: int

# In load_config():
config = AppConfig(
    # ... existing ...
    # Phase 2
    execution_mode=os.getenv('EXECUTION_MODE', 'demo'),
    default_position_size_usd=float(os.getenv('DEFAULT_POSITION_SIZE_USD', '500')),
    max_position_size_usd=float(os.getenv('MAX_POSITION_SIZE_USD', '50000')),
    max_daily_loss_usd=float(os.getenv('MAX_DAILY_LOSS_USD', '5000')),
    max_daily_volume_usd=float(os.getenv('MAX_DAILY_VOLUME_USD', '50000')),
    max_concurrent_positions=int(os.getenv('MAX_CONCURRENT_POSITIONS', '10')),
)
```

## Testing

### Step 1: Dry Run

Test signal detection without placing orders:

```bash
export EXECUTION_MODE=dry_run
export TELEGRAM_BOT_TOKEN="token"
export TELEGRAM_CHANNEL_ID="channel"

python -m polytracker.main
```

**What to expect:**
- Bot detects whale signals
- Logs "🔧 DRY RUN: Would execute..." for each signal
- Zero orders created in database
- No Telegram alerts (execution-related)

**Duration:** 1-2 hours

### Step 2: Demo Mode (Paper Trading)

Test with paper orders at live prices:

```bash
export EXECUTION_MODE=demo
export DEFAULT_POSITION_SIZE_USD=100
export TELEGRAM_BOT_TOKEN="token"
export TELEGRAM_CHANNEL_ID="channel"

python -m polytracker.main
```

**What to expect:**
- Whale signals detected
- Logs "📋 Demo execution: fetching current price..."
- Demo orders created in database
- P&L tracked (even though not real money)

**Check results:**
```sql
SELECT id, market_title, direction, size_usd, entry_price, status 
FROM orders 
WHERE execution_mode = 'demo'
ORDER BY created_at DESC LIMIT 10;
```

**Duration:** 3-7 days (enough signals to validate)

### Step 3: Analysis

After demo, review performance:

```sql
-- Demo P&L
SELECT 
  COUNT(*) as total_orders,
  COUNT(*) FILTER (WHERE pnl > 0) as winning_trades,
  COUNT(*) FILTER (WHERE pnl < 0) as losing_trades,
  SUM(pnl) as total_pnl,
  SUM(pnl) * 100.0 / COUNT(*) FILTER (WHERE pnl IS NOT NULL) as avg_pnl,
  COUNT(*) FILTER (WHERE pnl > 0) * 100.0 / COUNT(*) as win_rate
FROM orders
WHERE execution_mode = 'demo' AND market_resolved = TRUE;
```

**Success criteria:**
- Win rate ≥ 60%
- Average ROI positive
- No daily loss limit breaches (or very few)

If successful, proceed to live.

### Step 4: Live Mode (Real Money)

After demo validation:

```bash
export EXECUTION_MODE=live
export DEFAULT_POSITION_SIZE_USD=500    # Start with reasonable size
export MAX_POSITION_SIZE_USD=2000       # Keep tight limits
export MAX_DAILY_LOSS_USD=2000          # Conservative stops
export TELEGRAM_BOT_TOKEN="token"
export TELEGRAM_CHANNEL_ID="channel"

python -m polytracker.main
```

**Before going live:**
- [ ] Demo mode run for minimum 3-7 days
- [ ] Win rate ≥ 60% on demo
- [ ] Average ROI positive on demo
- [ ] No major risk limit breaches
- [ ] Telegram alerts tested and working
- [ ] Team/stakeholders notified
- [ ] Small position sizes configured
- [ ] Close monitoring plan ready

**First 24 hours:**
- Monitor closely
- Check orders every hour
- Verify P&L calculations
- Watch for unexpected behavior
- Be ready to stop if issues arise

## Monitoring Commands

### View Recent Orders
```bash
# SQL to show last 20 orders
psql -h localhost -U polytracker -d polytracker -c "
SELECT id, market_title, direction, size_usd, status, entry_price, 
       execution_mode, created_at 
FROM orders 
ORDER BY created_at DESC LIMIT 20;
"
```

### Check Daily P&L
```bash
psql -h localhost -U polytracker -d polytracker -c "
SELECT DATE(created_at) as date, 
       execution_mode,
       COUNT(*) as trades,
       ROUND(CAST(SUM(pnl) AS numeric), 2) as daily_pnl,
       ROUND(CAST(AVG(roi_pct) AS numeric), 2) as avg_roi
FROM orders
WHERE market_resolved = TRUE
GROUP BY DATE(created_at), execution_mode
ORDER BY date DESC;
"
```

### View Risk Events
```bash
psql -h localhost -U polytracker -d polytracker -c "
SELECT timestamp, event_type, severity, description, action_taken
FROM risk_events
ORDER BY timestamp DESC LIMIT 10;
"
```

### Monitor Positions
```bash
psql -h localhost -U polytracker -d polytracker -c "
SELECT p.id, o.market_title, o.direction, 
       p.size_usd, p.entry_price, p.current_price,
       ROUND(CAST(p.unrealized_pnl AS numeric), 2) as unrealized_pnl,
       p.last_updated
FROM positions p
JOIN orders o ON p.order_id = o.id
WHERE p.is_closed = FALSE
ORDER BY p.entry_timestamp DESC;
"
```

## Troubleshooting

### Orders not being placed

**Check:**
```bash
# 1. Verify execution mode is set
echo $EXECUTION_MODE    # Should output: dry_run, demo, or live

# 2. Check logs for risk blocks
tail -f logs/polytracker.log | grep "Risk check"

# 3. Verify database connection
python -c "
import asyncio
from polytracker.db_pg import AsyncDatabase
async def test():
    db = AsyncDatabase()
    await db.connect()
    print('✅ Database connected')
    await db.disconnect()
asyncio.run(test())
"

# 4. Check for CLOB API errors
tail -f logs/polytracker.log | grep "CLOB\|order"
```

### Risk events triggered constantly

**Likely causes:**
- Position size too aggressive for limits
- Daily loss limit too tight
- Running multiple instances

**Fix:**
- Increase `MAX_DAILY_LOSS_USD`
- Decrease `DEFAULT_POSITION_SIZE_USD`
- Stop other bot instances

### P&L calculations wrong

**Note:** Phase 2 MVP uses simplified P&L:
- Assumes binary outcomes (WIN = price ≥ 0.5, LOSE = price < 0.5)
- Doesn't track partial fills
- P&L updated only when market resolves

This is acceptable for Phase 2; Phase 3 will refine.

## Performance Tuning

### For high-volume trading:

```bash
# Increase connection pool
export DATABASE_POOL_SIZE=30

# Increase rate limits (if API allows)
export MAX_REQUESTS_PER_SECOND=20

# Batch risk checks (in code)
# check_risk_batch_size=10
```

### For conservative trading:

```bash
# Smaller positions
export DEFAULT_POSITION_SIZE_USD=100

# Tight limits
export MAX_POSITION_SIZE_USD=500
export MAX_DAILY_LOSS_USD=500

# Fewer concurrent positions
export MAX_CONCURRENT_POSITIONS=3
```

## Alerts Integration

Phase 2 creates orders but alert sending isn't yet wired.

To enable Telegram alerts for fills:

```python
# In trade_monitor.py or main.py
async def on_order_filled(order):
    message = f"""
    ✅ Order Filled!
    {order.market_title}
    {order.direction} @ ${order.entry_price:.4f}
    Size: ${order.size_usd:.2f}
    """
    await telegram_bot.send_message(message)
```

This will be fully integrated in Phase 3.

## Next Steps

1. **Configure .env** — Add EXECUTION_MODE and risk limits
2. **Update code** — Wire Phase 2 into main.py
3. **Test dry_run** — 1-2 hours, confirm signals logged
4. **Test demo** — 3-7 days, validate P&L
5. **Review results** — Check win rate, risk events
6. **Go live** — When confident (if win rate > 60%)

## Support

If you hit issues:

1. Check logs: `tail -f logs/polytracker.log | grep ERROR`
2. Check database: `psql -h localhost -U polytracker -d polytracker`
3. Check risk events: Query `risk_events` table
4. Check orders: Query `orders` table

---

**Phase 2 Setup:** Complete  
**Status:** Ready to integrate and test  
**Recommended Path:** dry_run → demo (3-7 days) → live (if validated)

Start with dry_run today, demo for a week, then go live!
