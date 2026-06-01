"""SQLAlchemy models for Phase 2 trade execution."""

from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, ForeignKey, Index, Text, Numeric, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class OrderStatus(str, enum.Enum):
    """Order lifecycle status."""
    PENDING = "pending"          # Awaiting placement
    PLACED = "placed"            # On-chain, open
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"            # Complete
    CANCELLED = "cancelled"
    FAILED = "failed"            # Placement failed


class OrderType(str, enum.Enum):
    """Type of order."""
    MARKET = "market"            # Immediate execution
    LIMIT = "limit"              # Price target


class ExecutionMode(str, enum.Enum):
    """Execution mode."""
    DRY_RUN = "dry_run"          # Logging only, no actual orders
    DEMO = "demo"                # Paper trading against live prices
    LIVE = "live"                # Real money


class Order(Base):
    """Order record for trade execution."""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    order_id = Column(String(255), unique=True, nullable=True)  # Polymarket order ID

    signal_id = Column(String(255), nullable=True)  # Links to original signal
    wallet_address = Column(String(255), nullable=False)
    market_id = Column(String(255), nullable=False)
    market_slug = Column(String(512), nullable=False)
    market_title = Column(Text, nullable=False)

    direction = Column(String(3), nullable=False)  # YES or NO
    order_type = Column(String(20), nullable=False, default=OrderType.MARKET)  # market/limit
    size_usd = Column(Numeric(18, 2), nullable=False)  # Position size
    entry_price = Column(Float, nullable=True)  # Entry price achieved
    limit_price = Column(Float, nullable=True)  # Target limit price

    status = Column(String(50), nullable=False, default=OrderStatus.PENDING)
    execution_mode = Column(String(20), nullable=False, default=ExecutionMode.DEMO)

    created_at = Column(DateTime(timezone=True), nullable=False)
    filled_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Execution tracking
    amount_filled = Column(Numeric(18, 2), default=0)  # Amount executed
    avg_fill_price = Column(Float, nullable=True)  # Average price filled at

    # P&L tracking
    market_resolved = Column(Boolean, default=False)
    resolved_outcome = Column(String(3), nullable=True)  # YES or NO
    exit_price = Column(Float, nullable=True)
    pnl = Column(Numeric(18, 2), nullable=True)  # Profit/loss
    roi_pct = Column(Float, nullable=True)  # Return on investment %

    # Metadata
    notes = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_orders_wallet", "wallet_address"),
        Index("idx_orders_market", "market_id"),
        Index("idx_orders_status", "status"),
        Index("idx_orders_created_at", "created_at"),
        Index("idx_orders_execution_mode", "execution_mode"),
    )


class Position(Base):
    """Open trading position."""
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True)

    wallet_address = Column(String(255), nullable=False)
    market_id = Column(String(255), nullable=False)
    direction = Column(String(3), nullable=False)  # YES or NO

    size_usd = Column(Numeric(18, 2), nullable=False)
    entry_price = Column(Float, nullable=False)
    entry_timestamp = Column(DateTime(timezone=True), nullable=False)

    # Current state
    current_price = Column(Float, nullable=True)  # Current midpoint
    last_updated = Column(DateTime(timezone=True), nullable=True)
    unrealized_pnl = Column(Numeric(18, 2), nullable=True)
    unrealized_roi_pct = Column(Float, nullable=True)

    # Close info
    is_closed = Column(Boolean, default=False)
    close_price = Column(Float, nullable=True)
    close_timestamp = Column(DateTime(timezone=True), nullable=True)
    realized_pnl = Column(Numeric(18, 2), nullable=True)
    realized_roi_pct = Column(Float, nullable=True)

    __table_args__ = (
        Index("idx_positions_wallet", "wallet_address"),
        Index("idx_positions_market", "market_id"),
        Index("idx_positions_is_closed", "is_closed"),
    )


class RiskEvent(Base):
    """Risk management event (limit breach, stop loss trigger, etc.)."""
    __tablename__ = "risk_events"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)

    event_type = Column(String(50), nullable=False)  # e.g., "max_daily_loss", "max_position_size", "max_trades_per_hour"
    severity = Column(String(20), nullable=False)  # warning, critical

    wallet_address = Column(String(255), nullable=True)
    market_id = Column(String(255), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    description = Column(Text, nullable=False)
    current_value = Column(Float, nullable=True)
    limit_value = Column(Float, nullable=True)

    action_taken = Column(Text, nullable=True)  # e.g., "cancelled_order", "blocked_new_order"

    __table_args__ = (
        Index("idx_risk_events_timestamp", "timestamp"),
        Index("idx_risk_events_type", "event_type"),
        Index("idx_risk_events_severity", "severity"),
    )


class ExecutionStats(Base):
    """Daily execution statistics for monitoring."""
    __tablename__ = "execution_stats"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime(timezone=True), nullable=False)  # Date (UTC)

    execution_mode = Column(String(20), nullable=False)  # dry_run, demo, live

    # Order counts
    orders_placed = Column(Integer, default=0)
    orders_filled = Column(Integer, default=0)
    orders_cancelled = Column(Integer, default=0)
    orders_failed = Column(Integer, default=0)

    # P&L
    total_size_usd = Column(Numeric(18, 2), default=0)
    total_pnl = Column(Numeric(18, 2), default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, nullable=True)

    # Risk
    max_concurrent_positions = Column(Integer, default=0)
    max_daily_loss = Column(Numeric(18, 2), nullable=True)
    risk_events = Column(Integer, default=0)

    __table_args__ = (
        Index("idx_stats_date", "date"),
        Index("idx_stats_execution_mode", "execution_mode"),
    )
