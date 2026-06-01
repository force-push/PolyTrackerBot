"""APScheduler job definitions for PolyTracker."""

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger


def start_scheduler(config, wallet_scanner, trade_monitor, telegram_bot):
    """Create and start APScheduler with PolyTracker jobs.
    
    Args:
        config: AppConfig object
        wallet_scanner: WalletScanner instance
        trade_monitor: TradeMonitor instance
        telegram_bot: TelegramBot instance
    
    Returns:
        AsyncIOScheduler instance (already started)
    """
    
    scheduler = AsyncIOScheduler()
    
    # Job 1: Discover wallets (every 6 hours)
    scheduler.add_job(
        _job_discover_wallets,
        'interval',
        hours=config.scheduler.discover_wallets_hours,
        args=[wallet_scanner],
        id='discover_wallets',
        name='Discover Wallets',
    )
    logger.info(f"📅 Scheduled wallet discovery every {config.scheduler.discover_wallets_hours}h")
    
    # Job 2: Rescore wallets (every 24 hours)
    scheduler.add_job(
        _job_rescore_wallets,
        'interval',
        hours=config.scheduler.rescore_wallets_hours,
        args=[wallet_scanner],
        id='rescore_wallets',
        name='Rescore Wallets',
    )
    logger.info(f"📅 Scheduled wallet rescoring every {config.scheduler.rescore_wallets_hours}h")
    
    # Job 3: Poll trades (every 5 minutes) - CRITICAL PATH
    scheduler.add_job(
        _job_poll_trades,
        'interval',
        minutes=config.scheduler.poll_trades_minutes,
        args=[trade_monitor],
        id='poll_trades',
        name='Poll Trades',
    )
    logger.info(f"📅 Scheduled trade polling every {config.scheduler.poll_trades_minutes}m")
    
    # Job 4: Check market closures (every 1 hour)
    scheduler.add_job(
        _job_check_closures,
        'interval',
        hours=config.scheduler.check_closures_hours,
        id='check_closures',
        name='Check Market Closures',
    )
    logger.info(f"📅 Scheduled market closure check every {config.scheduler.check_closures_hours}h")
    
    # Job 5: Daily digest (at 08:00 UTC)
    scheduler.add_job(
        _job_daily_digest,
        'cron',
        hour=config.scheduler.daily_digest_hour_utc,
        minute=0,
        args=[telegram_bot],
        id='daily_digest',
        name='Daily Digest',
    )
    logger.info(f"📅 Scheduled daily digest at {config.scheduler.daily_digest_hour_utc:02d}:00 UTC")
    
    # Start scheduler
    scheduler.start()
    logger.info("✅ Scheduler started with 5 jobs")
    
    return scheduler


async def _job_discover_wallets(wallet_scanner):
    """Job: Discover new high-performing wallets."""
    try:
        await wallet_scanner.discover_wallets()
    except Exception as e:
        logger.error(f"❌ Wallet discovery job failed: {e}")


async def _job_rescore_wallets(wallet_scanner):
    """Job: Re-evaluate existing wallets."""
    try:
        await wallet_scanner.rescore_wallets()
    except Exception as e:
        logger.error(f"❌ Wallet rescoring job failed: {e}")


async def _job_poll_trades(trade_monitor):
    """Job: Check tracked wallets for new positions (critical path)."""
    try:
        await trade_monitor.monitor_wallets()
    except Exception as e:
        logger.error(f"❌ Trade monitoring job failed: {e}")


async def _job_check_closures():
    """Job: Cleanup resolved/closed markets."""
    try:
        logger.info("🧹 Checking for closed markets...")
        # TODO: Implement market closure cleanup
        logger.info("✅ Market closure check complete")
    except Exception as e:
        logger.error(f"❌ Market closure check failed: {e}")


async def _job_daily_digest(telegram_bot):
    """Job: Send daily summary of signals."""
    try:
        logger.info("📊 Generating daily digest...")
        # TODO: Fetch today's signals, format summary, send
        logger.info("✅ Daily digest sent")
    except Exception as e:
        logger.error(f"❌ Daily digest job failed: {e}")
