"""Risk management framework for trade execution."""

from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
from decimal import Decimal
from loguru import logger

from polytracker.models_execution import RiskEvent


class RiskManager:
    """Manage risk constraints during trade execution."""

    def __init__(self, config, db):
        """Initialize risk manager.

        Args:
            config: AppConfig
            db: AsyncDatabase
        """
        self.config = config
        self.db = db
        self.logger = logger

    async def can_execute_trade(
        self,
        size_usd: float,
        wallet_address: str,
    ) -> Tuple[bool, Optional[str]]:
        """Check if trade can be executed based on risk constraints.

        Args:
            size_usd: Proposed trade size
            wallet_address: Wallet placing trade

        Returns:
            (can_execute, reason_if_blocked)
        """
        checks = [
            await self._check_max_position_size(size_usd),
            await self._check_daily_loss_limit(wallet_address),
            await self._check_max_daily_volume(wallet_address),
            await self._check_max_concurrent_positions(wallet_address),
            await self._check_position_overlap(wallet_address),
        ]

        for passed, reason in checks:
            if not passed:
                self.logger.warning(f"⚠️ Risk check failed: {reason}")
                return False, reason

        return True, None

    async def _check_max_position_size(self, size_usd: float) -> Tuple[bool, Optional[str]]:
        """Check position doesn't exceed max size."""
        # Get from config or use default
        max_size = getattr(self.config, 'max_position_size_usd', 50000.0)

        if size_usd > max_size:
            return False, f"Position size ${size_usd} exceeds max ${max_size}"

        return True, None

    async def _check_daily_loss_limit(self, wallet_address: str) -> Tuple[bool, Optional[str]]:
        """Check daily loss doesn't exceed limit."""
        max_daily_loss = getattr(self.config, 'max_daily_loss_usd', 10000.0)

        # Get today's closed positions
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        try:
            async with await self.db._get_session() as session:
                from sqlalchemy.sql import select, func
                from polytracker.models_execution import Order, OrderStatus

                query = (
                    select(func.sum(Order.pnl))
                    .where(
                        (Order.wallet_address == wallet_address) &
                        (Order.status == OrderStatus.FILLED.value) &
                        (Order.closed_at >= today_start) &
                        (Order.pnl < 0)  # Losing trades only
                    )
                )
                result = await session.execute(query)
                daily_loss = result.scalar() or Decimal(0)

                if abs(daily_loss) > max_daily_loss:
                    return False, f"Daily loss ${abs(daily_loss):.2f} exceeds limit ${max_daily_loss}"

                return True, None

        except Exception as e:
            self.logger.warning(f"Could not check daily loss limit: {e}")
            return True, None  # Fail open to avoid blocking

    async def _check_max_daily_volume(self, wallet_address: str) -> Tuple[bool, Optional[str]]:
        """Check daily volume doesn't exceed limit."""
        max_daily_volume = getattr(self.config, 'max_daily_volume_usd', 100000.0)

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        try:
            async with await self.db._get_session() as session:
                from sqlalchemy.sql import select, func
                from polytracker.models_execution import Order

                query = (
                    select(func.sum(Order.size_usd))
                    .where(
                        (Order.wallet_address == wallet_address) &
                        (Order.created_at >= today_start)
                    )
                )
                result = await session.execute(query)
                daily_volume = result.scalar() or Decimal(0)

                if daily_volume > max_daily_volume:
                    return False, f"Daily volume ${float(daily_volume):.2f} exceeds limit ${max_daily_volume}"

                return True, None

        except Exception as e:
            self.logger.warning(f"Could not check daily volume limit: {e}")
            return True, None

    async def _check_max_concurrent_positions(self, wallet_address: str) -> Tuple[bool, Optional[str]]:
        """Check doesn't exceed max open positions."""
        max_positions = getattr(self.config, 'max_concurrent_positions', 10)

        try:
            async with await self.db._get_session() as session:
                from sqlalchemy.sql import select, func
                from polytracker.models_execution import Position

                query = (
                    select(func.count(Position.id))
                    .where(
                        (Position.wallet_address == wallet_address) &
                        (Position.is_closed == False)
                    )
                )
                result = await session.execute(query)
                open_count = result.scalar() or 0

                if open_count >= max_positions:
                    return False, f"Already have {open_count} open positions (max {max_positions})"

                return True, None

        except Exception as e:
            self.logger.warning(f"Could not check concurrent positions: {e}")
            return True, None

    async def _check_position_overlap(self, wallet_address: str) -> Tuple[bool, Optional[str]]:
        """Check doesn't trade same market twice simultaneously."""
        # This would check market_id against open positions
        # Simplified for Phase 2
        return True, None

    async def record_risk_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        current_value: Optional[float] = None,
        limit_value: Optional[float] = None,
        wallet_address: Optional[str] = None,
        market_id: Optional[str] = None,
        order_id: Optional[int] = None,
        action_taken: Optional[str] = None,
    ) -> None:
        """Record a risk management event."""
        try:
            event = RiskEvent(
                timestamp=datetime.now(timezone.utc),
                event_type=event_type,
                severity=severity,
                wallet_address=wallet_address,
                market_id=market_id,
                order_id=order_id,
                description=description,
                current_value=current_value,
                limit_value=limit_value,
                action_taken=action_taken,
            )

            # Would save to database in real implementation
            self.logger.warning(
                f"Risk Event [{severity}] {event_type}: {description} "
                f"(current: {current_value}, limit: {limit_value})"
            )

        except Exception as e:
            self.logger.error(f"Failed to record risk event: {e}")
