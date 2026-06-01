"""PostgreSQL database layer for PolyTracker Bot (async with SQLAlchemy)."""

import os
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.sql import select, func
from loguru import logger

from polytracker.models import Base, Wallet, Trade, AlertSent, BacktestRun, SignalPerformance


class AsyncDatabase:
    """PostgreSQL async database manager for PolyTracker."""

    def __init__(self, database_url: Optional[str] = None):
        """Initialize database.

        Args:
            database_url: PostgreSQL connection URL (postgresql+asyncpg://...)
                         Defaults to DATABASE_URL env var
        """
        self.database_url = database_url or os.getenv(
            'DATABASE_URL',
            'postgresql+asyncpg://polytracker:polytracker_dev@localhost:5432/polytracker'
        )
        self.engine = None
        self.async_session = None

    async def connect(self):
        """Connect to database and initialize schema."""
        self.engine = create_async_engine(
            self.database_url,
            echo=False,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,
        )
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        await self.init_schema()
        logger.info(f"PostgreSQL database connected")

    async def disconnect(self):
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()
            logger.info("PostgreSQL database disconnected")

    async def init_schema(self):
        """Create tables if they don't exist."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema initialized")

    async def _get_session(self) -> AsyncSession:
        """Get a new async session."""
        if not self.async_session:
            raise RuntimeError("Database not connected")
        return self.async_session()

    # ============================================
    # WALLET OPERATIONS
    # ============================================

    async def upsert_wallet(
        self,
        address: str,
        score: float,
        win_rate: float,
        total_pnl: float,
        roi: float,
        volume_30d: float,
        avg_position: float,
        total_trades: int,
    ) -> None:
        """Insert or update a wallet."""
        async with await self._get_session() as session:
            async with session.begin():
                now = datetime.now(timezone.utc)
                stmt = select(Wallet).where(Wallet.address == address)
                result = await session.execute(stmt)
                wallet = result.scalars().first()

                if wallet:
                    wallet.score = score
                    wallet.win_rate = win_rate
                    wallet.total_pnl = total_pnl
                    wallet.roi = roi
                    wallet.volume_30d = volume_30d
                    wallet.avg_position = avg_position
                    wallet.total_trades = total_trades
                    wallet.last_seen = now
                else:
                    wallet = Wallet(
                        address=address,
                        score=score,
                        win_rate=win_rate,
                        total_pnl=total_pnl,
                        roi=roi,
                        volume_30d=volume_30d,
                        avg_position=avg_position,
                        total_trades=total_trades,
                        last_seen=now,
                        added_at=now,
                    )
                    session.add(wallet)

                await session.commit()

    async def get_active_wallets(self, limit: Optional[int] = None) -> list[dict[str, Any]]:
        """Get all active tracked wallets."""
        async with await self._get_session() as session:
            query = select(Wallet).where(Wallet.is_active == True).order_by(Wallet.score.desc())
            if limit:
                query = query.limit(limit)

            result = await session.execute(query)
            wallets = result.scalars().all()
            return [self._wallet_to_dict(w) for w in wallets]

    async def deactivate_wallet(self, address: str) -> None:
        """Deactivate a wallet."""
        async with await self._get_session() as session:
            async with session.begin():
                stmt = select(Wallet).where(Wallet.address == address)
                result = await session.execute(stmt)
                wallet = result.scalars().first()
                if wallet:
                    wallet.is_active = False
                    await session.commit()

    async def get_wallet(self, address: str) -> Optional[dict[str, Any]]:
        """Get a single wallet by address."""
        async with await self._get_session() as session:
            stmt = select(Wallet).where(Wallet.address == address)
            result = await session.execute(stmt)
            wallet = result.scalars().first()
            return self._wallet_to_dict(wallet) if wallet else None

    @staticmethod
    def _wallet_to_dict(wallet: Wallet) -> dict[str, Any]:
        """Convert wallet model to dict."""
        if not wallet:
            return None
        return {
            'address': wallet.address,
            'score': wallet.score,
            'win_rate': wallet.win_rate,
            'total_pnl': wallet.total_pnl,
            'roi': wallet.roi,
            'volume_30d': wallet.volume_30d,
            'avg_position': wallet.avg_position,
            'total_trades': wallet.total_trades,
            'last_seen': wallet.last_seen.isoformat(),
            'added_at': wallet.added_at.isoformat(),
            'is_active': wallet.is_active,
        }

    # ============================================
    # TRADE OPERATIONS
    # ============================================

    async def upsert_trade(
        self,
        wallet_address: str,
        market_id: str,
        market_slug: str,
        market_title: str,
        direction: str,
        price: float,
        size_usd: float,
        timestamp: str,
        market_closes: Optional[str] = None,
    ) -> int:
        """Insert or update a trade record."""
        async with await self._get_session() as session:
            async with session.begin():
                # Parse timestamps
                if isinstance(timestamp, str):
                    from datetime import datetime as dt
                    ts = dt.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    ts = timestamp

                if market_closes and isinstance(market_closes, str):
                    from datetime import datetime as dt
                    mc = dt.fromisoformat(market_closes.replace('Z', '+00:00'))
                else:
                    mc = market_closes

                # Check if trade exists
                stmt = select(Trade).where(
                    (Trade.wallet_address == wallet_address) &
                    (Trade.market_id == market_id) &
                    (Trade.direction == direction) &
                    (Trade.timestamp == ts)
                )
                result = await session.execute(stmt)
                trade = result.scalars().first()

                if not trade:
                    trade = Trade(
                        wallet_address=wallet_address,
                        market_id=market_id,
                        market_slug=market_slug,
                        market_title=market_title,
                        direction=direction,
                        price=price,
                        size_usd=size_usd,
                        timestamp=ts,
                        market_closes=mc,
                    )
                    session.add(trade)

                await session.commit()
                return trade.id

    async def get_unalerted_trades(self) -> list[dict[str, Any]]:
        """Get trades that haven't been alerted on yet."""
        async with await self._get_session() as session:
            query = (
                select(Trade, Wallet.score)
                .join(Wallet, Trade.wallet_address == Wallet.address)
                .where((Trade.alerted == False) & (Wallet.is_active == True))
                .order_by(Trade.timestamp.desc())
            )
            result = await session.execute(query)
            trades = result.all()
            return [self._trade_to_dict(t[0], t[1]) for t in trades]

    async def mark_trade_alerted(self, trade_id: int) -> None:
        """Mark a trade as alerted."""
        async with await self._get_session() as session:
            async with session.begin():
                stmt = select(Trade).where(Trade.id == trade_id)
                result = await session.execute(stmt)
                trade = result.scalars().first()
                if trade:
                    trade.alerted = True
                    await session.commit()

    async def get_trades_for_market(self, market_id: str) -> list[dict[str, Any]]:
        """Get all trades for a specific market."""
        async with await self._get_session() as session:
            query = select(Trade).where(Trade.market_id == market_id)
            result = await session.execute(query)
            trades = result.scalars().all()
            return [self._trade_to_dict(t) for t in trades]

    @staticmethod
    def _trade_to_dict(trade: Trade, wallet_score: Optional[float] = None) -> dict[str, Any]:
        """Convert trade model to dict."""
        if not trade:
            return None
        d = {
            'id': trade.id,
            'wallet_address': trade.wallet_address,
            'market_id': trade.market_id,
            'market_slug': trade.market_slug,
            'market_title': trade.market_title,
            'direction': trade.direction,
            'price': trade.price,
            'size_usd': trade.size_usd,
            'timestamp': trade.timestamp.isoformat(),
            'market_closes': trade.market_closes.isoformat() if trade.market_closes else None,
            'alerted': trade.alerted,
            'market_resolved': trade.market_resolved,
            'resolved_outcome': trade.resolved_outcome,
            'pnl': trade.pnl,
            'roi_pct': trade.roi_pct,
        }
        if wallet_score is not None:
            d['score'] = wallet_score
        return d

    # ============================================
    # ALERT OPERATIONS
    # ============================================

    async def record_alert(self, wallet_address: str, market_id: str, alert_type: str) -> None:
        """Record an alert that was sent."""
        async with await self._get_session() as session:
            async with session.begin():
                now = datetime.now(timezone.utc)
                alert = AlertSent(
                    wallet_address=wallet_address,
                    market_id=market_id,
                    sent_at=now,
                    alert_type=alert_type,
                )
                session.add(alert)
                await session.commit()

    async def has_alert_for_market(self, wallet_address: str, market_id: str) -> bool:
        """Check if an alert has been sent for this wallet-market combo."""
        async with await self._get_session() as session:
            stmt = select(AlertSent).where(
                (AlertSent.wallet_address == wallet_address) &
                (AlertSent.market_id == market_id)
            ).limit(1)
            result = await session.execute(stmt)
            return result.scalars().first() is not None

    # ============================================
    # BACKTEST OPERATIONS
    # ============================================

    async def create_backtest_run(
        self,
        run_id: str,
        start_date: datetime,
        end_date: datetime,
        config: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> None:
        """Create a new backtest run record."""
        async with await self._get_session() as session:
            async with session.begin():
                backtest = BacktestRun(
                    run_id=run_id,
                    created_at=datetime.now(timezone.utc),
                    start_date=start_date,
                    end_date=end_date,
                    config=config,
                    notes=notes,
                )
                session.add(backtest)
                await session.commit()

    async def update_backtest_run(
        self,
        run_id: str,
        total_signals: int,
        resolved_signals: int,
        profitable_signals: int,
        win_rate: float,
        avg_roi: float,
        total_pnl: float,
    ) -> None:
        """Update backtest run with results."""
        async with await self._get_session() as session:
            async with session.begin():
                stmt = select(BacktestRun).where(BacktestRun.run_id == run_id)
                result = await session.execute(stmt)
                backtest = result.scalars().first()
                if backtest:
                    backtest.total_signals = total_signals
                    backtest.resolved_signals = resolved_signals
                    backtest.profitable_signals = profitable_signals
                    backtest.win_rate = win_rate
                    backtest.avg_roi = avg_roi
                    backtest.total_pnl = total_pnl
                    await session.commit()

    async def get_backtest_run(self, run_id: str) -> Optional[dict[str, Any]]:
        """Get backtest run details."""
        async with await self._get_session() as session:
            stmt = select(BacktestRun).where(BacktestRun.run_id == run_id)
            result = await session.execute(stmt)
            backtest = result.scalars().first()
            if backtest:
                return {
                    'run_id': backtest.run_id,
                    'created_at': backtest.created_at.isoformat(),
                    'start_date': backtest.start_date.isoformat(),
                    'end_date': backtest.end_date.isoformat(),
                    'total_signals': backtest.total_signals,
                    'resolved_signals': backtest.resolved_signals,
                    'profitable_signals': backtest.profitable_signals,
                    'win_rate': backtest.win_rate,
                    'avg_roi': backtest.avg_roi,
                    'total_pnl': backtest.total_pnl,
                    'notes': backtest.notes,
                }
            return None

    async def get_trades_for_backtest(self, run_id: str) -> list[dict[str, Any]]:
        """Get all trades associated with a backtest run."""
        async with await self._get_session() as session:
            query = (
                select(SignalPerformance)
                .where(SignalPerformance.backtest_run_id == run_id)
                .order_by(SignalPerformance.signal_date.desc())
            )
            result = await session.execute(query)
            trades = result.scalars().all()
            return [self._signal_perf_to_dict(t) for t in trades]

    @staticmethod
    def _signal_perf_to_dict(signal: SignalPerformance) -> dict[str, Any]:
        """Convert signal performance model to dict."""
        if not signal:
            return None
        return {
            'id': signal.id,
            'wallet_address': signal.wallet_address,
            'market_id': signal.market_id,
            'market_title': signal.market_title,
            'signal_date': signal.signal_date.isoformat(),
            'signal_direction': signal.signal_direction,
            'signal_strength': signal.signal_strength,
            'resolved_date': signal.resolved_date.isoformat() if signal.resolved_date else None,
            'resolved_outcome': signal.resolved_outcome,
            'position_size': signal.position_size,
            'entry_price': signal.entry_price,
            'exit_price': signal.exit_price,
            'pnl': signal.pnl,
            'roi_pct': signal.roi_pct,
            'is_winning': signal.is_winning,
        }
