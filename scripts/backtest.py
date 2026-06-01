#!/usr/bin/env python3
"""Backtesting engine for PolyTracker signals."""

import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from typing import Optional
import statistics

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from polytracker.db_pg import AsyncDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select
from polytracker.models import Trade, SignalPerformance
from loguru import logger


class BacktestEngine:
    """Backtest whale signals against market outcomes."""

    def __init__(self, db: AsyncDatabase):
        """Initialize backtest engine.

        Args:
            db: AsyncDatabase instance
        """
        self.db = db
        self.run_id = f"backtest_{uuid4().hex[:8]}"
        self.logger = logger

    async def run_backtest(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        wallet_filter: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> dict:
        """Run backtest on historical data.

        Args:
            start_date: Filter trades after this date
            end_date: Filter trades before this date
            wallet_filter: Filter to specific wallet address
            notes: Notes about this backtest run

        Returns:
            Backtest results dict
        """
        self.logger.info("=" * 70)
        self.logger.info(f"Starting Backtest Run: {self.run_id}")
        self.logger.info("=" * 70)

        try:
            # Create backtest run record
            config = {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "wallet_filter": wallet_filter,
            }
            await self.db.create_backtest_run(
                run_id=self.run_id,
                start_date=start_date or datetime(2020, 1, 1, tzinfo=timezone.utc),
                end_date=end_date or datetime.now(timezone.utc),
                config=json.dumps(config),
                notes=notes,
            )

            # Fetch and analyze trades
            results = await self._analyze_trades(start_date, end_date, wallet_filter)

            # Update backtest run with results
            await self.db.update_backtest_run(
                run_id=self.run_id,
                total_signals=results['total_signals'],
                resolved_signals=results['resolved_signals'],
                profitable_signals=results['profitable_signals'],
                win_rate=results['win_rate'],
                avg_roi=results['avg_roi'],
                total_pnl=results['total_pnl'],
            )

            self.logger.info("=" * 70)
            self.logger.info("Backtest Results:")
            self.logger.info(f"  Total Signals: {results['total_signals']}")
            self.logger.info(f"  Resolved: {results['resolved_signals']}")
            self.logger.info(f"  Profitable: {results['profitable_signals']}")
            self.logger.info(f"  Win Rate: {results['win_rate']:.1%}")
            self.logger.info(f"  Avg ROI: {results['avg_roi']:.2f}%")
            self.logger.info(f"  Total P&L: ${results['total_pnl']:.2f}")
            self.logger.info("=" * 70)

            return results

        except Exception as e:
            self.logger.error(f"Backtest failed: {e}")
            raise

    async def _analyze_trades(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        wallet_filter: Optional[str],
    ) -> dict:
        """Analyze trades for backtest."""
        async with await self.db._get_session() as session:
            # Build query
            query = select(Trade).order_by(Trade.timestamp.desc())

            if start_date:
                query = query.where(Trade.timestamp >= start_date)
            if end_date:
                query = query.where(Trade.timestamp <= end_date)
            if wallet_filter:
                query = query.where(Trade.wallet_address == wallet_filter)

            result = await session.execute(query)
            trades = result.scalars().all()

            self.logger.info(f"Found {len(trades)} signals to analyze")

            # Calculate metrics
            total_signals = len(trades)
            resolved_signals = 0
            profitable_signals = 0
            pnls = []
            rois = []

            for trade in trades:
                # Skip unresolved trades for now
                if not trade.market_resolved:
                    # Try to infer outcome if market_closes has passed
                    if trade.market_closes and trade.market_closes < datetime.now(timezone.utc):
                        # Market should have closed but outcome unknown
                        # Skip for backtest
                        continue
                    else:
                        continue

                resolved_signals += 1

                # Calculate P&L (simplified: no exit price means 0 for now)
                # In real scenario, you'd fetch actual market outcome prices
                if trade.resolved_outcome:
                    is_winning = trade.resolved_outcome == trade.direction
                    if is_winning:
                        profitable_signals += 1

                    # Simplified P&L calculation
                    # Assumes binary outcome: profit if correct, loss if wrong
                    if is_winning:
                        # Win: profit on position
                        pnl = trade.size_usd * trade.price
                    else:
                        # Loss: lose portion of position
                        pnl = -trade.size_usd * (1 - trade.price)

                    pnls.append(pnl)

                    if trade.size_usd > 0:
                        roi = (pnl / trade.size_usd) * 100
                        rois.append(roi)

            # Calculate aggregate metrics
            win_rate = profitable_signals / resolved_signals if resolved_signals > 0 else 0
            avg_roi = statistics.mean(rois) if rois else 0
            total_pnl = sum(pnls) if pnls else 0

            return {
                'total_signals': total_signals,
                'resolved_signals': resolved_signals,
                'profitable_signals': profitable_signals,
                'win_rate': win_rate,
                'avg_roi': avg_roi,
                'total_pnl': total_pnl,
                'run_id': self.run_id,
            }


async def main():
    """Main entry point."""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Parse command line arguments
    start_date = None
    end_date = None
    wallet_filter = None
    notes = None

    if len(sys.argv) > 1:
        # Simple arg parsing: --start YYYY-MM-DD --end YYYY-MM-DD --wallet ADDRESS --notes "description"
        args = sys.argv[1:]
        i = 0
        while i < len(args):
            if args[i] == '--start' and i + 1 < len(args):
                start_date = datetime.fromisoformat(args[i + 1])
                i += 2
            elif args[i] == '--end' and i + 1 < len(args):
                end_date = datetime.fromisoformat(args[i + 1])
                i += 2
            elif args[i] == '--wallet' and i + 1 < len(args):
                wallet_filter = args[i + 1]
                i += 2
            elif args[i] == '--notes' and i + 1 < len(args):
                notes = args[i + 1]
                i += 2
            else:
                i += 1

    postgres_url = os.getenv(
        'DATABASE_URL',
        'postgresql+asyncpg://polytracker:polytracker_dev@localhost:5432/polytracker'
    )

    db = AsyncDatabase(postgres_url)
    await db.connect()

    try:
        engine = BacktestEngine(db)
        results = await engine.run_backtest(
            start_date=start_date,
            end_date=end_date,
            wallet_filter=wallet_filter,
            notes=notes,
        )

        # Print JSON output for scripting
        print("\n" + "=" * 70)
        print("JSON OUTPUT (for integration):")
        print(json.dumps(results, indent=2, default=str))

    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
