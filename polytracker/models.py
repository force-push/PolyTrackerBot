"""SQLAlchemy models for PolyTracker Bot."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, ForeignKey, Index, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Wallet(Base):
    """Wallet model for tracking trader performance."""
    __tablename__ = "wallets"

    address = Column(String(255), primary_key=True)
    score = Column(Float, nullable=False)
    win_rate = Column(Float, nullable=False)
    total_pnl = Column(Float, nullable=False)
    roi = Column(Float, nullable=False)
    volume_30d = Column(Float, nullable=False)
    avg_position = Column(Float, nullable=False)
    total_trades = Column(Integer, nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=False)
    added_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    trades = relationship("Trade", back_populates="wallet", cascade="all, delete-orphan")
    alerts_sent = relationship("AlertSent", back_populates="wallet", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_wallets_active", "is_active"),
        Index("idx_wallets_score", "score"),
    )


class Trade(Base):
    """Trade model for tracking executed trades."""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True)
    wallet_address = Column(String(255), ForeignKey("wallets.address"), nullable=False)
    market_id = Column(String(255), nullable=False)
    market_slug = Column(String(512), nullable=False)
    market_title = Column(Text, nullable=False)
    direction = Column(String(3), nullable=False)  # YES or NO
    price = Column(Float, nullable=False)
    size_usd = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    market_closes = Column(DateTime(timezone=True), nullable=True)
    alerted = Column(Boolean, default=False, nullable=False)

    # Analytics fields
    market_resolved = Column(Boolean, default=False, nullable=False)
    resolved_outcome = Column(String(3), nullable=True)  # YES or NO
    pnl = Column(Float, nullable=True)  # Profit/loss for this trade
    roi_pct = Column(Float, nullable=True)  # Return on investment %

    wallet = relationship("Wallet", back_populates="trades")

    __table_args__ = (
        Index("idx_trades_wallet", "wallet_address"),
        Index("idx_trades_market", "market_id"),
        Index("idx_trades_alerted", "alerted"),
        Index("idx_trades_timestamp", "timestamp"),
        Index("idx_trades_resolved", "market_resolved"),
    )


class AlertSent(Base):
    """Record of alerts sent to Telegram."""
    __tablename__ = "alerts_sent"

    id = Column(Integer, primary_key=True)
    wallet_address = Column(String(255), ForeignKey("wallets.address"), nullable=False)
    market_id = Column(String(255), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=False)
    alert_type = Column(String(50), nullable=False)  # 'standard' or 'high_conviction'

    wallet = relationship("Wallet", back_populates="alerts_sent")

    __table_args__ = (
        Index("idx_alerts_wallet_market", "wallet_address", "market_id"),
        Index("idx_alerts_sent_at", "sent_at"),
    )


class BacktestRun(Base):
    """Record of backtest runs for analysis."""
    __tablename__ = "backtest_runs"

    id = Column(Integer, primary_key=True)
    run_id = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)

    total_signals = Column(Integer, default=0)
    resolved_signals = Column(Integer, default=0)
    profitable_signals = Column(Integer, default=0)

    win_rate = Column(Float, nullable=True)
    avg_roi = Column(Float, nullable=True)
    total_pnl = Column(Float, nullable=True)

    config = Column(Text, nullable=True)  # JSON config used
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_backtest_created_at", "created_at"),
        Index("idx_backtest_run_id", "run_id"),
    )


class SignalPerformance(Base):
    """Detailed signal performance tracking for backtesting."""
    __tablename__ = "signal_performance"

    id = Column(Integer, primary_key=True)
    backtest_run_id = Column(String(255), ForeignKey("backtest_runs.run_id"), nullable=True)
    wallet_address = Column(String(255), nullable=False)
    market_id = Column(String(255), nullable=False)
    market_title = Column(Text, nullable=False)

    signal_date = Column(DateTime(timezone=True), nullable=False)
    signal_direction = Column(String(3), nullable=False)  # YES or NO
    signal_strength = Column(Float, nullable=True)  # 0-1 or scoring value

    resolved_date = Column(DateTime(timezone=True), nullable=True)
    resolved_outcome = Column(String(3), nullable=True)  # YES or NO

    position_size = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)

    pnl = Column(Float, nullable=True)
    roi_pct = Column(Float, nullable=True)

    is_winning = Column(Boolean, nullable=True)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_signal_perf_backtest", "backtest_run_id"),
        Index("idx_signal_perf_wallet", "wallet_address"),
        Index("idx_signal_perf_signal_date", "signal_date"),
        Index("idx_signal_perf_resolved", "resolved_date"),
    )
