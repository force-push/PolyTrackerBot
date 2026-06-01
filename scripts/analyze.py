#!/usr/bin/env python3
"""Analytics and reporting CLI for PolyTracker data."""

import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
import statistics

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from polytracker.db_pg import AsyncDatabase
from sqlalchemy.sql import select, func
from polytracker.models import Trade, Wallet, AlertSent
from loguru import logger


class AnalyticsEngine:
    """Analyze PolyTracker signals and performance."""

    def __init__(self, db: AsyncDatabase):
        """Initialize analytics engine.

        Args:
            db: AsyncDatabase instance
        """
        self.db = db
        self.logger = logger

    async def get_wallet_stats(self) -> list[dict]:
        """Get statistics for all tracked wallets."""
        wallets = await self.db.get_active_wallets()
        stats = []

        for wallet in wallets:
            # Get trades for this wallet
            async with await self.db._get_session() as session:
                stmt = select(Trade).where(Trade.wallet_address == wallet['address'])
                result = await session.execute(stmt)
                trades = result.scalars().all()

                total_trades = len(trades)
                alerted_trades = sum(1 for t in trades if t.alerted)
                resolved_trades = sum(1 for t in trades if t.market_resolved)

                stats.append({
                    'address': wallet['address'],
                    'score': wallet['score'],
                    'win_rate': wallet['win_rate'],
                    'total_pnl': wallet['total_pnl'],
                    'roi': wallet['roi'],
                    'volume_30d': wallet['volume_30d'],
                    'total_trades': total_trades,
                    'alerted': alerted_trades,
                    'resolved': resolved_trades,
                    'added_at': wallet['added_at'],
                    'last_seen': wallet['last_seen'],
                })

        return sorted(stats, key=lambda x: x['score'], reverse=True)

    async def get_signal_performance(
        self,
        days: int = 30,
        wallet_filter: Optional[str] = None,
    ) -> dict:
        """Get signal performance over time period.

        Args:
            days: Number of days to analyze
            wallet_filter: Optional wallet address filter

        Returns:
            Performance metrics dict
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        async with await self.db._get_session() as session:
            query = select(Trade).where(Trade.timestamp >= cutoff)
            if wallet_filter:
                query = query.where(Trade.wallet_address == wallet_filter)

            result = await session.execute(query)
            trades = result.scalars().all()

            total_signals = len(trades)
            resolved_signals = sum(1 for t in trades if t.market_resolved)
            profitable_signals = sum(1 for t in trades if t.market_resolved and t.pnl and t.pnl > 0)

            pnls = [t.pnl for t in trades if t.market_resolved and t.pnl is not None]
            rois = [t.roi_pct for t in trades if t.market_resolved and t.roi_pct is not None]

            return {
                'period_days': days,
                'filter': wallet_filter or 'all_wallets',
                'total_signals': total_signals,
                'resolved_signals': resolved_signals,
                'profitable_signals': profitable_signals,
                'win_rate': profitable_signals / resolved_signals if resolved_signals > 0 else 0,
                'avg_roi': statistics.mean(rois) if rois else 0,
                'median_roi': statistics.median(rois) if rois else 0,
                'total_pnl': sum(pnls) if pnls else 0,
                'avg_pnl': statistics.mean(pnls) if pnls else 0,
            }

    async def get_recent_trades(self, limit: int = 50) -> list[dict]:
        """Get recent trades sorted by timestamp.

        Args:
            limit: Maximum trades to return

        Returns:
            List of trade dicts
        """
        async with await self.db._get_session() as session:
            query = select(Trade).order_by(Trade.timestamp.desc()).limit(limit)
            result = await session.execute(query)
            trades = result.scalars().all()
            return [self.db._trade_to_dict(t) for t in trades]

    async def get_top_wallets(self, limit: int = 10) -> list[dict]:
        """Get top wallets by score.

        Args:
            limit: Maximum wallets to return

        Returns:
            List of wallet dicts
        """
        return await self.db.get_active_wallets(limit=limit)

    async def get_summary(self) -> dict:
        """Get overall summary stats.

        Returns:
            Summary dict
        """
        wallets = await self.db.get_active_wallets()
        perf_30d = await self.get_signal_performance(days=30)
        perf_7d = await self.get_signal_performance(days=7)

        return {
            'summary': {
                'tracked_wallets': len(wallets),
                'avg_wallet_score': statistics.mean([w['score'] for w in wallets]) if wallets else 0,
                'top_wallet_score': wallets[0]['score'] if wallets else 0,
            },
            'last_30_days': perf_30d,
            'last_7_days': perf_7d,
        }


async def print_wallet_stats(engine: AnalyticsEngine) -> None:
    """Print wallet statistics."""
    print("\n" + "=" * 80)
    print("WALLET STATISTICS")
    print("=" * 80)

    stats = await engine.get_wallet_stats()

    print(f"{'Address':<50} {'Score':<8} {'Win%':<8} {'PnL':<12} {'Trades':<8}")
    print("-" * 80)

    for stat in stats[:20]:  # Top 20
        address = stat['address'][:50] if stat['address'] else 'unknown'
        win_rate = f"{stat['win_rate']*100:.1f}%"
        pnl = f"${stat['total_pnl']:,.0f}"
        print(f"{address:<50} {stat['score']:<8.1f} {win_rate:<8} {pnl:<12} {stat['total_trades']:<8}")


async def print_performance(engine: AnalyticsEngine) -> None:
    """Print performance metrics."""
    print("\n" + "=" * 80)
    print("SIGNAL PERFORMANCE")
    print("=" * 80)

    perf_7d = await engine.get_signal_performance(days=7)
    perf_30d = await engine.get_signal_performance(days=30)

    print("\nLast 7 Days:")
    print(f"  Total Signals: {perf_7d['total_signals']}")
    print(f"  Resolved: {perf_7d['resolved_signals']}")
    print(f"  Win Rate: {perf_7d['win_rate']*100:.1f}%")
    print(f"  Avg ROI: {perf_7d['avg_roi']:.2f}%")
    print(f"  Total P&L: ${perf_7d['total_pnl']:,.2f}")

    print("\nLast 30 Days:")
    print(f"  Total Signals: {perf_30d['total_signals']}")
    print(f"  Resolved: {perf_30d['resolved_signals']}")
    print(f"  Win Rate: {perf_30d['win_rate']*100:.1f}%")
    print(f"  Avg ROI: {perf_30d['avg_roi']:.2f}%")
    print(f"  Total P&L: ${perf_30d['total_pnl']:,.2f}")


async def print_recent_trades(engine: AnalyticsEngine, limit: int = 20) -> None:
    """Print recent trades."""
    print("\n" + "=" * 120)
    print("RECENT SIGNALS")
    print("=" * 120)

    trades = await engine.get_recent_trades(limit=limit)

    if not trades:
        print("No trades found.")
        return

    print(f"{'Wallet':<45} {'Market':<30} {'Dir':<3} {'Size':<10} {'Alerted':<8} {'Resolved':<10}")
    print("-" * 120)

    for trade in trades:
        wallet = trade['wallet_address'][:45] if trade['wallet_address'] else 'unknown'
        market = trade['market_title'][:30] if trade['market_title'] else 'unknown'
        direction = trade['direction']
        size = f"${trade['size_usd']:.0f}"
        alerted = "✓" if trade['alerted'] else "✗"
        resolved = "✓" if trade['market_resolved'] else "✗"
        print(f"{wallet:<45} {market:<30} {direction:<3} {size:<10} {alerted:<8} {resolved:<10}")


async def main():
    """Main entry point."""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    postgres_url = os.getenv(
        'DATABASE_URL',
        'postgresql+asyncpg://polytracker:polytracker_dev@localhost:5432/polytracker'
    )

    db = AsyncDatabase(postgres_url)
    await db.connect()

    try:
        engine = AnalyticsEngine(db)

        # Print summary
        summary = await engine.get_summary()
        print("\n" + "=" * 80)
        print("POLYTRACKER ANALYTICS SUMMARY")
        print("=" * 80)
        print(f"\nTracked Wallets: {summary['summary']['tracked_wallets']}")
        print(f"Avg Wallet Score: {summary['summary']['avg_wallet_score']:.1f}")
        print(f"Top Wallet Score: {summary['summary']['top_wallet_score']:.1f}")

        # Print detailed reports
        if len(sys.argv) > 1:
            if sys.argv[1] == 'wallets':
                await print_wallet_stats(engine)
            elif sys.argv[1] == 'perf':
                await print_performance(engine)
            elif sys.argv[1] == 'trades':
                limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
                await print_recent_trades(engine, limit=limit)
            elif sys.argv[1] == 'json':
                print("\n" + json.dumps(summary, indent=2, default=str))
        else:
            # Default: print all
            await print_wallet_stats(engine)
            await print_performance(engine)
            await print_recent_trades(engine, limit=10)

    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
