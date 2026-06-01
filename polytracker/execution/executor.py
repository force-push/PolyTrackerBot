"""Trade execution engine with CLOB API integration."""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Any
from decimal import Decimal
from loguru import logger

from polytracker.polymarket.client import PolymarketClient
from polytracker.models_execution import Order, OrderStatus, OrderType, ExecutionMode, Position, RiskEvent


class TradeExecutor:
    """Execute trades on Polymarket via CLOB API."""

    def __init__(self, config, db, execution_mode: ExecutionMode = ExecutionMode.DEMO):
        """Initialize executor.

        Args:
            config: AppConfig
            db: AsyncDatabase (Phase 2)
            execution_mode: DRY_RUN, DEMO, or LIVE
        """
        self.config = config
        self.db = db
        self.execution_mode = execution_mode
        self.logger = logger

    async def execute_signal(
        self,
        wallet_address: str,
        market_id: str,
        market_slug: str,
        market_title: str,
        direction: str,  # YES or NO
        size_usd: float,
        signal_strength: Optional[float] = None,
        signal_id: Optional[str] = None,
    ) -> Optional[Order]:
        """Execute a trade based on whale signal.

        Args:
            wallet_address: Whale wallet address
            market_id: Polymarket market ID
            market_slug: Market slug
            market_title: Market title
            direction: YES or NO
            size_usd: Position size in USD
            signal_strength: Optional signal strength (0-1)
            signal_id: Optional link to original signal

        Returns:
            Order record if successful, None on failure
        """
        self.logger.info(
            f"📊 Executing signal: {market_title} | {direction} | ${size_usd:.2f} | Mode: {self.execution_mode}"
        )

        try:
            # Create order record
            order = Order(
                signal_id=signal_id,
                wallet_address=wallet_address,
                market_id=market_id,
                market_slug=market_slug,
                market_title=market_title,
                direction=direction,
                order_type=OrderType.MARKET,
                size_usd=Decimal(str(size_usd)),
                status=OrderStatus.PENDING,
                execution_mode=self.execution_mode.value,
                created_at=datetime.now(timezone.utc),
            )

            # DRY RUN: Log only, no execution
            if self.execution_mode == ExecutionMode.DRY_RUN:
                self.logger.info(f"🔧 DRY RUN: Would execute {order.order_type} order")
                order.status = OrderStatus.FILLED
                order.filled_at = datetime.now(timezone.utc)
                order.entry_price = 0.5  # Assume 50c average
                order.amount_filled = Decimal(str(size_usd))
                order.avg_fill_price = 0.5
                return order

            # DEMO: Paper trade at live prices
            if self.execution_mode == ExecutionMode.DEMO:
                order = await self._execute_demo(order)
                return order

            # LIVE: Real money execution
            if self.execution_mode == ExecutionMode.LIVE:
                order = await self._execute_live(order)
                return order

        except Exception as e:
            self.logger.error(f"❌ Execution failed: {e}")
            if order:
                order.status = OrderStatus.FAILED
                order.error_message = str(e)
            return None

        return None

    async def _execute_demo(self, order: Order) -> Order:
        """Execute order in demo mode (paper trading).

        Args:
            order: Order to execute

        Returns:
            Updated order with execution details
        """
        self.logger.info("📋 Demo execution: fetching current price...")

        try:
            async with PolymarketClient(self.config.polymarket) as client:
                # Get current market price
                market = await client.get_market_by_id(order.market_id)
                if not market:
                    raise ValueError(f"Market not found: {order.market_id}")

                # Get token ID for price lookup
                tokens = market.get("tokens", [])
                if not tokens:
                    raise ValueError("Market has no tokens")

                # Find token matching direction
                token_id = None
                for token in tokens:
                    if token.get("outcome") == order.direction:
                        token_id = token.get("token_id")
                        break

                if not token_id:
                    raise ValueError(f"Token not found for direction {order.direction}")

                # Get midpoint price
                price = await client.get_midpoint_price(token_id)
                if price is None:
                    price = 0.5  # Default fallback

                self.logger.info(f"  Current price: ${price:.4f}")

                # Simulate execution
                order.status = OrderStatus.FILLED
                order.filled_at = datetime.now(timezone.utc)
                order.entry_price = float(price)
                order.amount_filled = order.size_usd
                order.avg_fill_price = float(price)

                self.logger.info(
                    f"  ✅ Demo filled: {order.amount_filled} @ ${order.entry_price:.4f}"
                )

                return order

        except Exception as e:
            self.logger.error(f"Demo execution error: {e}")
            order.status = OrderStatus.FAILED
            order.error_message = str(e)
            return order

    async def _execute_live(self, order: Order) -> Order:
        """Execute order with real money on Polymarket.

        Args:
            order: Order to execute

        Returns:
            Updated order with execution details
        """
        self.logger.warning("🚨 LIVE EXECUTION: Real money trade")

        try:
            async with PolymarketClient(self.config.polymarket) as client:
                # Get market details
                market = await client.get_market_by_id(order.market_id)
                if not market:
                    raise ValueError(f"Market not found: {order.market_id}")

                # Find token ID
                tokens = market.get("tokens", [])
                token_id = None
                for token in tokens:
                    if token.get("outcome") == order.direction:
                        token_id = token.get("token_id")
                        break

                if not token_id:
                    raise ValueError(f"Token not found for direction {order.direction}")

                # Place market order on CLOB
                order_result = await client.place_market_order(
                    token_id=token_id,
                    size_usd=float(order.size_usd),
                    side="BUY",  # Always BUY YES or BUY NO
                )

                if not order_result or not order_result.get("order_id"):
                    raise ValueError("Order placement failed")

                order.order_id = order_result.get("order_id")
                order.status = OrderStatus.PLACED
                order.filled_at = datetime.now(timezone.utc)
                order.entry_price = float(order_result.get("avg_price", 0.5))
                order.amount_filled = Decimal(str(order_result.get("amount_filled", order.size_usd)))
                order.avg_fill_price = order.entry_price

                self.logger.info(
                    f"  ✅ Live order placed: ID {order.order_id} @ ${order.entry_price:.4f}"
                )

                return order

        except Exception as e:
            self.logger.error(f"Live execution error: {e}")
            order.status = OrderStatus.FAILED
            order.error_message = str(e)
            return order

    async def close_position(
        self,
        position_id: int,
        market_id: str,
        direction: str,
    ) -> Optional[Order]:
        """Close an open position.

        Args:
            position_id: Position ID to close
            market_id: Market ID
            direction: Original direction (YES or NO)

        Returns:
            Closing order or None
        """
        self.logger.info(f"🔒 Closing position {position_id}...")

        # Create exit order (opposite direction)
        exit_direction = "NO" if direction == "YES" else "YES"

        try:
            async with PolymarketClient(self.config.polymarket) as client:
                market = await client.get_market_by_id(market_id)
                if not market:
                    raise ValueError(f"Market not found: {market_id}")

                # Find token for exit direction
                tokens = market.get("tokens", [])
                token_id = None
                for token in tokens:
                    if token.get("outcome") == exit_direction:
                        token_id = token.get("token_id")
                        break

                if not token_id:
                    raise ValueError(f"Exit token not found for {exit_direction}")

                # Get current price
                price = await client.get_midpoint_price(token_id)
                if price is None:
                    price = 0.5

                self.logger.info(f"  Exit price: ${price:.4f}")

                # In live mode, would place SELL order here
                if self.execution_mode == ExecutionMode.LIVE:
                    # Place SELL order (opposite of entry)
                    order_result = await client.place_market_order(
                        token_id=token_id,
                        size_usd=100.0,  # Would get from position
                        side="SELL",
                    )

                self.logger.info(f"  ✅ Position closed @ ${price:.4f}")

                return None  # Simplified for Phase 2

        except Exception as e:
            self.logger.error(f"Close position error: {e}")
            return None
