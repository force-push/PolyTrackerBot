"""Entry point for PolyTracker Bot."""

import asyncio
import sys
from loguru import logger

from polytracker.config import get_config
from polytracker.db import Database
from polytracker.polymarket.wallet_scanner import WalletScanner
from polytracker.polymarket.trade_monitor import TradeMonitor
from polytracker.telegram.bot import TelegramBot
from polytracker.scheduler import start_scheduler


async def main():
    """Main bot entry point."""
    
    # Load configuration
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
    db = Database(config.database_path)
    await db.connect()
    logger.info(f"✅ Database connected: {config.database_path}")
    
    # Initialize components
    telegram_bot = TelegramBot(config.telegram)
    wallet_scanner = WalletScanner(config, db)
    trade_monitor = TradeMonitor(config, db, telegram_bot)
    
    # Start scheduler
    scheduler = start_scheduler(config, wallet_scanner, trade_monitor, telegram_bot)
    logger.info("✅ Scheduler started with 5 jobs")
    
    try:
        # Run event loop
        logger.info("📡 PolyTracker Bot is running. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("⏹️ Shutting down gracefully...")
    
    finally:
        # Cleanup
        scheduler.shutdown()
        await db.disconnect()
        logger.info("✅ Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
