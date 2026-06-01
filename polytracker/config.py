"""Configuration module for PolyTracker Bot."""

import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env file
load_dotenv()


@dataclass
class TelegramConfig:
    """Telegram bot configuration."""
    bot_token: str
    channel_id: str


@dataclass
class PolymarketConfig:
    """Polymarket API configuration."""
    data_api_base: str
    gamma_api_base: str
    clob_api_base: str
    max_requests_per_second: int
    http_timeout_connect: int
    http_timeout_read: int
    max_retries: int
    retry_backoff_factor: float


@dataclass
class WalletScoringConfig:
    """Wallet scoring thresholds."""
    min_win_rate: float
    min_total_pnl: float
    min_trades: int
    min_avg_position: float
    min_volume_30d: float
    max_wallets_tracked: int


@dataclass
class SignalFilterConfig:
    """Signal filtering parameters."""
    min_signal_position: float
    min_market_liquidity: float
    min_hours_remaining: int


@dataclass
class SchedulerConfig:
    """Scheduler job intervals."""
    discover_wallets_hours: int
    rescore_wallets_hours: int
    poll_trades_minutes: int
    check_closures_hours: int
    daily_digest_hour_utc: int


@dataclass
class AppConfig:
    """Main application configuration."""
    telegram: TelegramConfig
    polymarket: PolymarketConfig
    wallet_scoring: WalletScoringConfig
    signal_filter: SignalFilterConfig
    scheduler: SchedulerConfig
    database_path: str
    log_level: str
    enable_daily_digest: bool
    enable_high_conviction_alerts: bool
    alert_on_position_changes: bool


def load_config() -> AppConfig:
    """Load and validate configuration from environment."""
    
    # Validate required env vars
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHANNEL_ID',
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    # Create data directory
    db_path = os.getenv('DATABASE_PATH', './data/polytracker.db')
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    return AppConfig(
        telegram=TelegramConfig(
            bot_token=os.getenv('TELEGRAM_BOT_TOKEN'),
            channel_id=os.getenv('TELEGRAM_CHANNEL_ID'),
        ),
        polymarket=PolymarketConfig(
            data_api_base=os.getenv('POLYMARKET_DATA_API_BASE', 'https://data-api.polymarket.com'),
            gamma_api_base=os.getenv('POLYMARKET_GAMMA_API_BASE', 'https://gamma-api.polymarket.com'),
            clob_api_base=os.getenv('POLYMARKET_CLOB_API_BASE', 'https://clob.polymarket.com'),
            max_requests_per_second=int(os.getenv('MAX_REQUESTS_PER_SECOND', '10')),
            http_timeout_connect=int(os.getenv('HTTP_TIMEOUT_CONNECT', '5')),
            http_timeout_read=int(os.getenv('HTTP_TIMEOUT_READ', '30')),
            max_retries=int(os.getenv('MAX_RETRIES', '3')),
            retry_backoff_factor=float(os.getenv('RETRY_BACKOFF_FACTOR', '1.5')),
        ),
        wallet_scoring=WalletScoringConfig(
            min_win_rate=float(os.getenv('MIN_WIN_RATE', '0.60')),
            min_total_pnl=float(os.getenv('MIN_TOTAL_PNL', '5000')),
            min_trades=int(os.getenv('MIN_TRADES', '25')),
            min_avg_position=float(os.getenv('MIN_AVG_POSITION', '200')),
            min_volume_30d=float(os.getenv('MIN_VOLUME_30D', '2000')),
            max_wallets_tracked=int(os.getenv('MAX_WALLETS_TRACKED', '50')),
        ),
        signal_filter=SignalFilterConfig(
            min_signal_position=float(os.getenv('MIN_SIGNAL_POSITION', '500')),
            min_market_liquidity=float(os.getenv('MIN_MARKET_LIQUIDITY', '10000')),
            min_hours_remaining=int(os.getenv('MIN_HOURS_REMAINING', '48')),
        ),
        scheduler=SchedulerConfig(
            discover_wallets_hours=int(os.getenv('DISCOVER_WALLETS_INTERVAL_HOURS', '6')),
            rescore_wallets_hours=int(os.getenv('RESCORE_WALLETS_INTERVAL_HOURS', '24')),
            poll_trades_minutes=int(os.getenv('POLL_TRADES_INTERVAL_MINUTES', '5')),
            check_closures_hours=int(os.getenv('CHECK_MARKET_CLOSURES_INTERVAL_HOURS', '1')),
            daily_digest_hour_utc=int(os.getenv('DAILY_DIGEST_HOUR_UTC', '8')),
        ),
        database_path=db_path,
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        enable_daily_digest=os.getenv('ENABLE_DAILY_DIGEST', 'true').lower() == 'true',
        enable_high_conviction_alerts=os.getenv('ENABLE_HIGH_CONVICTION_ALERTS', 'true').lower() == 'true',
        alert_on_position_changes=os.getenv('ALERT_ON_POSITION_SIZE_CHANGES', 'false').lower() == 'true',
    )


# Global config instance (lazy loaded)
_config: AppConfig | None = None


def get_config() -> AppConfig:
    """Get or initialize the global config."""
    global _config
    if _config is None:
        _config = load_config()
    return _config
