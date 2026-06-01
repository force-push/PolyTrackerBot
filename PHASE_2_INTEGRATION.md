# Phase 2 Integration Guide

## Overview

This guide shows how to integrate Phase 2 (Trade Execution) into the main PolyTrackerBot to convert whale signals into actual trades.

## Architecture Integration

```
┌─────────────────┐
│ Wallet Scanner  │  Discovers whale traders
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Trade Monitor   │  Monitors their trades
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Signal Filter   │  Validates trade viability
└────────┬────────┘
         │
         v
┌─────────────────────────┐
│ TradeOrchestrator ✨NEW │  Execute if signal passes risk checks
└────────┬────────────────┘
         │
         v
┌──────────────────────┐
│ TradeExecutor        │  Place actual orders (DEMO/LIVE)
│ RiskManager          │  Enforce position limits
└──────────────────────┘
         │
         v
┌──────────────────────┐
│ Telegram Alerts      │  Notify user of fills
│ Database Logging     │  Record P&L, statistics
└──────────────────────┘
```

## Step 1: Update Configuration

Add execution settings to `.env`:

```bash
# Execution Mode
EXECUTION_MODE=demo              # DRY_RUN, DEMO, or LIVE

# Position Sizing
DEFAULT_POSITION_SIZE_USD=500    # Starting position
MAX_POSITION_SIZE_USD=50000      # Hard limit per trade

# Risk Limits
MAX_DAILY_LOSS_USD=5000          # Stop loss per day
MAX_DAILY_VOLUME_USD=50000       # Max daily volume
MAX_CONCURRENT_POSITIONS=10      # Max open trades at once

# Signal Thresholds (existing)
MIN_WHALE_WIN_RATE=0.60
MIN_MARKET_LIQUIDITY=10000
```

Or update `polytracker/config.py`:

```python
# Add to AppConfig dataclass
execution_mode: str = os.getenv('EXECUTION_MODE', 'demo')
default_position_size_usd: float = float(os.getenv('DEFAULT_POSITION_SIZE_USD', '500'))
max_position_size_usd: float = float(os.getenv('MAX_POSITION_SIZE_USD', '50000'))
max_daily_loss_usd: float = float(os.getenv('MAX_DAILY_LOSS_USD', '5000'))
max_daily_volume_usd: float = float(os.getenv('MAX_DAILY_VOLUME_USD', '50000'))
max_concurrent_positions: int = int(os.getenv('MAX_CONCURRENT_POSITIONS', '10'))
```

## Step 2: Update Models

Phase 1 uses `polytracker/models.py` for wallet/trade tracking.  
Phase 2 adds `polytracker/models_execution.py` for orders/positions.

Both coexist:
- Phase 1 models: Track whale signals
- Phase 2 models: Track our execution

The database migrations will create both schemas automatically.

## Step 3: Update TradeMonitor

Modify `polytracker/polymarket/trade_monitor.py` to call executor:

```python
"""Updated trade_monitor.py with Phase 2 execution."""

from polytracker.execution.orchestrator import TradeOrchestrator
from polytracker.models_execution import ExecutionMode

class TradeMonitor:
    def __init__(self, config, db, telegram_bot, orchestrator=None):
        self.config = config
        self.db = db
        self.telegram_bot = telegram_bot
        self.orchestrator = orchestrator  # NEW: Executor for Phase 2
    
    async def monitor_wallets(self):
        """Monitor wallets and execute on viable signals."""
        # ... existing whale detection code ...
        
        for position in new_positions:
            is_viable, alert_type, reason = await is_viable_signal(...)
            
            if is_viable:
                # Phase 1: Send alert only
                await self._send_position_alert(wallet, position, ...)
                
                # Phase 2: Execute order (if orchestrator initialized)
                if self.orchestrator:
                    await self.orchestrator.process_signal(
                        whale_wallet=wallet['address'],
                        market_id=position['market_id'],
                        market_slug=position['market_slug'],
                        market_title=position['market_title'],
                        direction=position['direction'],
                        whale_entry_price=position['price'],
                        whale_position_size=position['size_usd'],
                        signal_strength=1.0,  # Could calculate from filters
                        alert_type=alert_type,
                    )
```

## Step 4: Update main.py

Wire Phase 2 into the main bot:

```python
"""Updated polytracker/main.py with Phase 2 execution."""

import asyncio
import sys
import os
from loguru import logger

from polytracker.config import get_config
from polytracker.db_pg import AsyncDatabase
from polytracker.polymarket.wallet_scanner import WalletScanner
from polytracker.polymarket.trade_monitor import TradeMonitor
from polytracker.telegram.bot import TelegramBot
from polytracker.scheduler import start_scheduler

# Phase 2 imports
from polytracker.execution.orchestrator import TradeOrchestrator
from polytracker.models_execution import ExecutionMode


async def main():
    """Main bot entry point with Phase 2 execution."""
    
    config = get_config()
    
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        level=config.log_level,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    logger.add(
        "logs/polytracker.log",
        level=config.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="00:00",
        retention="7 days"
    )
    
    logger.info("🚀 PolyTracker Bot starting...")
    
    # Initialize database
    db = AsyncDatabase()
    await db.connect()
    logger.info("✅ Database connected")
    
    # Initialize components
    telegram_bot = TelegramBot(config.telegram)
    wallet_scanner = WalletScanner(config, db)
    
    # Phase 2: Initialize orchestrator (optional based on execution mode)
    orchestrator = None
    if hasattr(config, 'execution_mode') and config.execution_mode != 'none':
        exec_mode = ExecutionMode(config.execution_mode)
        orchestrator = TradeOrchestrator(config, db, exec_mode)
        logger.info(f"✅ Execution enabled: {exec_mode} mode")
    
    # Pass orchestrator to trade monitor
    trade_monitor = TradeMonitor(config, db, telegram_bot, orchestrator)
    
    # Start scheduler
    scheduler = start_scheduler(config, wallet_scanner, trade_monitor, telegram_bot)
    logger.info("✅ Scheduler started")
    
    try:
        logger.info("📡 PolyTracker Bot is running. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("⏹️ Shutting down gracefully...")
    
    finally:
        scheduler.shutdown()
        await db.disconnect()
        logger.info("✅ Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
```

## Step 5: Update Config Loading

Modify `polytracker/config.py` to load Phase 2 settings:

```python
"""Add to load_config() function."""

def load_config() -> AppConfig:
    # ... existing config loading ...
    
    # Phase 2 execution settings
    execution_mode = os.getenv('EXECUTION_MODE', 'demo')
    if execution_mode not in ['dry_run', 'demo', 'live', 'none']:
        execution_mode = 'demo'
    
    config = AppConfig(
        # ... existing fields ...
        # Phase 2
        execution_mode=execution_mode,
        default_position_size_usd=float(os.getenv('DEFAULT_POSITION_SIZE_USD', '500')),
        max_position_size_usd=float(os.getenv('MAX_POSITION_SIZE_USD', '50000')),
        max_daily_loss_usd=float(os.getenv('MAX_DAILY_LOSS_USD', '5000')),
        max_daily_volume_usd=float(os.getenv('MAX_DAILY_VOLUME_USD', '50000')),
        max_concurrent_positions=int(os.getenv('MAX_CONCURRENT_POSITIONS', '10')),
    )
    
    return config
```

## Step 6: Update Telegram Alerts

Enhance Telegram alerts to show execution status:

```python
"""Updated telegram/alerts.py"""

async def send_execution_alert(telegram_bot, order):
    """Send alert when order fills."""
    message = f"""
✅ Order Filled

Market: {order.market_title}
Direction: {order.direction}
Size: ${order.size_usd:.2f}
Entry: ${order.entry_price:.4f}
Mode: {order.execution_mode.upper()}
Timestamp: {order.filled_at}
    """.strip()
    
    await telegram_bot.send_message(message)
```

## Testing the Integration

### 1. Dry Run Mode (No Orders)

```bash
export EXECUTION_MODE=dry_run
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHANNEL_ID="your_channel"

python -m polytracker.main
```

Bot logs all signals but places zero orders. Perfect for testing.

### 2. Demo Mode (Paper Trading)

```bash
export EXECUTION_MODE=demo
export DEFAULT_POSITION_SIZE_USD=100
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHANNEL_ID="your_channel"

python -m polytracker.main
```

Bot places demo orders at live prices. Track P&L in database.

**Check demo orders:**
```sql
SELECT * FROM orders WHERE execution_mode = 'demo' ORDER BY created_at DESC;
```

### 3. Live Mode (Real Money)

```bash
export EXECUTION_MODE=live
export DEFAULT_POSITION_SIZE_USD=500
export MAX_POSITION_SIZE_USD=2000
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHANNEL_ID="your_channel"

python -m polytracker.main
```

### Validation Script

```python
"""Test integration"""
import asyncio
from polytracker.config import get_config
from polytracker.db_pg import AsyncDatabase
from polytracker.execution.orchestrator import TradeOrchestrator
from polytracker.models_execution import ExecutionMode

async def test_integration():
    config = get_config()
    db = AsyncDatabase()
    await db.connect()
    
    # Create demo orchestrator
    orchestrator = TradeOrchestrator(config, db, ExecutionMode.DEMO)
    
    # Simulate a whale signal
    success = await orchestrator.process_signal(
        whale_wallet="0x1234567890abcdef",
        market_id="123abc",
        market_slug="bitcoin-100k",
        market_title="Will Bitcoin hit $100k?",
        direction="YES",
        whale_entry_price=0.65,
        whale_position_size=5000.0,
        signal_strength=0.9,
        alert_type="high_conviction",
    )
    
    print(f"Signal processed: {success}")
    
    # Check stats
    stats = await orchestrator.get_execution_stats(hours=1)
    print(f"Stats: {stats}")
    
    await db.disconnect()

asyncio.run(test_integration())
```

## Backward Compatibility

Phase 2 is **100% backward compatible**:

- If `EXECUTION_MODE` not set → Defaults to `demo` (no real orders)
- If `orchestrator` is None → Bot works as Phase 1 (signal detection only)
- All Phase 1 tables/functionality unchanged
- Can disable execution by setting `EXECUTION_MODE=none`

So you can:
1. Deploy Phase 2 code without enabling execution
2. Test in dry_run or demo first
3. Graduate to live once confident

## Monitoring & Debugging

### View Order History

```sql
SELECT id, market_title, direction, size_usd, status, 
       entry_price, pnl, created_at 
FROM orders 
ORDER BY created_at DESC LIMIT 20;
```

### View Risk Events

```sql
SELECT timestamp, event_type, severity, description, action_taken
FROM risk_events
ORDER BY timestamp DESC LIMIT 10;
```

### View Daily Stats

```sql
SELECT date, execution_mode, orders_placed, total_pnl, win_rate
FROM execution_stats
ORDER BY date DESC LIMIT 7;
```

### Check Current Positions

```sql
SELECT p.*, o.market_title, o.direction
FROM positions p
JOIN orders o ON p.order_id = o.id
WHERE p.is_closed = FALSE;
```

## Next: Phase 3 (Hardening)

After Phase 2 is validated:
- Integration tests (signal → order flow)
- Structured logging for trading
- Telegram notifier refinement
- Order status polling (currently one-time)
- Stop-loss automation
- Performance optimization

---

**Phase 2 Integration:** Complete  
**Status:** Ready for demo testing  
**Next:** Monitor Phase 1 signals while Phase 2 is in demo mode
