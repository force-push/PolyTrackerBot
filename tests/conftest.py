"""Pytest fixtures for PolyTracker tests."""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from polytracker.config import AppConfig, TelegramConfig, PolymarketConfig
from polytracker.config import WalletScoringConfig, SignalFilterConfig, SchedulerConfig
from polytracker.db import Database


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_config():
    """Mock configuration."""
    return AppConfig(
        telegram=TelegramConfig(
            bot_token='TEST_TOKEN',
            channel_id='-100123456789',
        ),
        polymarket=PolymarketConfig(
            data_api_base='https://data-api.polymarket.com',
            gamma_api_base='https://gamma-api.polymarket.com',
            clob_api_base='https://clob.polymarket.com',
            max_requests_per_second=10,
            http_timeout_connect=5,
            http_timeout_read=30,
            max_retries=3,
            retry_backoff_factor=1.5,
        ),
        wallet_scoring=WalletScoringConfig(
            min_win_rate=0.60,
            min_total_pnl=5000,
            min_trades=25,
            min_avg_position=200,
            min_volume_30d=2000,
            max_wallets_tracked=50,
        ),
        signal_filter=SignalFilterConfig(
            min_signal_position=500,
            min_market_liquidity=10000,
            min_hours_remaining=48,
        ),
        scheduler=SchedulerConfig(
            discover_wallets_hours=6,
            rescore_wallets_hours=24,
            poll_trades_minutes=5,
            check_closures_hours=1,
            daily_digest_hour_utc=8,
        ),
        database_path=':memory:',  # In-memory SQLite for tests
        log_level='DEBUG',
        enable_daily_digest=True,
        enable_high_conviction_alerts=True,
        alert_on_position_changes=False,
    )


@pytest.fixture
async def mock_db(mock_config):
    """Mock database with in-memory SQLite."""
    db = Database(mock_config.database_path)
    await db.connect()
    yield db
    await db.disconnect()


@pytest.fixture
def mock_wallet_stats():
    """Mock wallet stats."""
    return {
        'address': '0x1234567890abcdef1234567890abcdef12345678',
        'win_rate': 0.73,
        'total_pnl': 24300,
        'roi': 142.0,
        'volume_30d': 15000,
        'avg_position': 750,
        'total_trades': 20,
        'last_trade_date': datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def mock_leaderboard():
    """Mock leaderboard response."""
    return [
        {
            'rank': '1',
            'proxyWallet': '0x1111111111111111111111111111111111111111',
            'userName': 'whale1',
            'pnl': 50000,
            'vol': 200000,
            'win_rate': 0.75,
            'total_trades': 50,
        },
        {
            'rank': '2',
            'proxyWallet': '0x2222222222222222222222222222222222222222',
            'userName': 'whale2',
            'pnl': 35000,
            'vol': 150000,
            'win_rate': 0.68,
            'total_trades': 45,
        },
    ]


@pytest.fixture
def mock_position():
    """Mock wallet position."""
    future = datetime.now(timezone.utc) + timedelta(days=60)
    return {
        'market_id': 'market_123',
        'condition_id': 'cond_123',
        'market_slug': 'will-x-happen',
        'direction': 'YES',
        'price': 0.34,
        'size_usd': 1200,
        'market_closes': future.isoformat(),
        'wallet_address': '0x1234567890abcdef1234567890abcdef12345678',
    }


@pytest.fixture
def mock_market():
    """Mock market details."""
    future = datetime.now(timezone.utc) + timedelta(days=60)
    return {
        'id': 'market_123',
        'condition_id': 'cond_123',
        'slug': 'will-x-happen',
        'title': 'Will X happen by Dec 31?',
        'description': 'Market description',
        'liquidity': 85400,
        'volume': 200000,
        'resolved': False,
        'status': 'active',
        'closes_at': future.isoformat(),
        'resolves_at': future.isoformat(),
    }


@pytest.fixture
def mock_polymarket_client(mock_leaderboard, mock_position, mock_market):
    """Mock PolymarketClient."""
    client = AsyncMock()
    
    client.get_trader_leaderboard = AsyncMock(return_value=mock_leaderboard)
    client.get_wallet_stats = AsyncMock(return_value={
        'win_rate': 0.73,
        'pnl': 24300,
        'roi': 142.0,
        'volume_30d': 15000,
    })
    client.get_wallet_trades = AsyncMock(return_value=[
        {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'market_id': 'market_123',
        }
    ])
    client.get_wallet_positions = AsyncMock(return_value=[mock_position])
    client.get_market_by_slug = AsyncMock(return_value=mock_market)
    client.get_market_by_id = AsyncMock(return_value=mock_market)
    client.get_market_liquidity = AsyncMock(return_value=85400)
    
    return client


@pytest.fixture
def mock_telegram_bot():
    """Mock TelegramBot."""
    bot = AsyncMock()
    bot.send_message = AsyncMock(return_value=True)
    bot.send_alert = AsyncMock(return_value=True)
    return bot
