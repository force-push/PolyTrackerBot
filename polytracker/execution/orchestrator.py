"""Trade orchestration: converts signals to execution."""

from datetime import datetime, timezone
from typing import Optional
from loguru import logger

from polytracker.execution.executor import TradeExecutor
from polytracker.execution.risk_manager import RiskManager
from polytracker.models_execution import ExecutionMode


class TradeOrchestrator:
    """Orchestrates signal detection → execution decision → order placement."""

    def __init__(self, config, db, execution_mode: ExecutionMode = ExecutionMode.DEMO):
        """Initialize orchestrator.

        Args:
            config: AppConfig
            db: AsyncDatabase
            execution_mode: DRY_RUN, DEMO, or LIVE
        """
        self.config = config
        self.db = db
        self.execution_mode = execution_mode
        self.executor = TradeExecutor(config, db, execution_mode)
        self.risk_manager = RiskManager(config, db)
        self.logger = logger

    async def process_signal(
        self,
        whale_wallet: str,
        market_id: str,
        market_slug: str,
        market_title: str,
        direction: str,  # YES or NO
        whale_entry_price: float,
        whale_position_size: float,
        signal_strength: float = 1.0,
        alert_type: str = "standard",
    ) -> bool:
        """Process a whale signal and execute if appropriate.

        Args:
            whale_wallet: Wallet that made the signal
            market_id: Market ID
            market_slug: Market slug
            market_title: Market title
            direction: YES or NO
            whale_entry_price: Entry price observed
            whale_position_size: Position size observed
            signal_strength: Signal strength (0-1)
            alert_type: standard or high_conviction

        Returns:
            True if order placed, False otherwise
        """
        self.logger.info(
            f"🐋 Processing signal: {market_title} | {direction} | {alert_type} | Strength: {signal_strength:.2f}"
        )

        try:
            # Step 1: Risk checks
            can_execute, reason = await self.risk_manager.can_execute_trade(
                size_usd=whale_position_size,
                wallet_address=whale_wallet,
            )

            if not can_execute:
                self.logger.warning(f"  ❌ Risk check blocked: {reason}")
                await self.risk_manager.record_risk_event(
                    event_type="execution_blocked",
                    severity="warning",
                    description=f"Trade blocked: {reason}",
                    wallet_address=whale_wallet,
                    market_id=market_id,
                )
                return False

            # Step 2: Size calculation
            # Scale position size based on signal strength and mode
            execution_size = await self._calculate_position_size(
                base_size=whale_position_size,
                signal_strength=signal_strength,
                alert_type=alert_type,
            )

            self.logger.info(
                f"  📊 Execution size: ${execution_size:.2f} "
                f"(whale: ${whale_position_size:.2f}, scaling: {execution_size/whale_position_size:.2%})"
            )

            # Step 3: Execute order
            order = await self.executor.execute_signal(
                wallet_address=whale_wallet,
                market_id=market_id,
                market_slug=market_slug,
                market_title=market_title,
                direction=direction,
                size_usd=execution_size,
                signal_strength=signal_strength,
                signal_id=None,  # Would link to signal DB record
            )

            if not order:
                self.logger.error("  ❌ Order execution failed")
                return False

            self.logger.info(
                f"  ✅ Order {order.status}: {order.order_id or 'pending'} "
                f"@ ${order.entry_price or '?'}"
            )

            return True

        except Exception as e:
            self.logger.error(f"Signal processing failed: {e}")
            return False

    async def _calculate_position_size(
        self,
        base_size: float,
        signal_strength: float,
        alert_type: str,
    ) -> float:
        """Calculate execution position size.

        Args:
            base_size: Whale position size
            signal_strength: Signal strength (0-1)
            alert_type: standard or high_conviction

        Returns:
            Execution size in USD
        """
        # Base sizing strategy
        if self.execution_mode == ExecutionMode.DRY_RUN:
            # Dry run: no actual sizing
            return base_size * 0.0

        if self.execution_mode == ExecutionMode.DEMO:
            # Demo: smaller position (10-50% of whale)
            scaling = 0.1 if alert_type == "standard" else 0.25
            return base_size * scaling * signal_strength

        if self.execution_mode == ExecutionMode.LIVE:
            # Live: full position but with risk limits
            scaling = 0.25 if alert_type == "standard" else 0.50
            size = base_size * scaling * signal_strength

            # Apply max position limit
            max_size = getattr(self.config, 'max_position_size_usd', 50000.0)
            return min(size, max_size)

        return base_size

    async def get_execution_stats(self, hours: int = 24) -> dict:
        """Get execution statistics for monitoring.

        Args:
            hours: Hours of history to include

        Returns:
            Stats dict
        """
        try:
            from datetime import timedelta
            from sqlalchemy.sql import select, func
            from polytracker.models_execution import Order, OrderStatus

            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

            async with await self.db._get_session() as session:
                # Get all orders in period
                query = select(Order).where(Order.created_at >= cutoff)
                result = await session.execute(query)
                orders = result.scalars().all()

                if not orders:
                    return {
                        'period_hours': hours,
                        'orders_placed': 0,
                        'total_pnl': 0,
                        'win_rate': 0,
                    }

                filled = [o for o in orders if o.status == OrderStatus.FILLED]
                closed = [o for o in orders if o.closed_at and o.pnl is not None]
                winning = [o for o in closed if o.pnl > 0]

                total_pnl = sum(float(o.pnl or 0) for o in closed)
                win_rate = len(winning) / len(closed) if closed else 0

                return {
                    'period_hours': hours,
                    'orders_placed': len(orders),
                    'orders_filled': len(filled),
                    'orders_closed': len(closed),
                    'total_pnl': total_pnl,
                    'winning_trades': len(winning),
                    'losing_trades': len(closed) - len(winning),
                    'win_rate': win_rate,
                    'avg_pnl': total_pnl / len(closed) if closed else 0,
                }

        except Exception as e:
            self.logger.error(f"Failed to get execution stats: {e}")
            return {}
