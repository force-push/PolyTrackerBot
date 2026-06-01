#!/usr/bin/env python3
"""Migrate data from SQLite to PostgreSQL for PolyTracker Bot."""

import asyncio
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Any
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from polytracker.db_pg import AsyncDatabase
from loguru import logger


class SQLiteMigrator:
    """Migrate data from SQLite to PostgreSQL."""

    def __init__(self, sqlite_path: str, postgres_url: str):
        """Initialize migrator.

        Args:
            sqlite_path: Path to SQLite database file
            postgres_url: PostgreSQL connection URL
        """
        self.sqlite_path = sqlite_path
        self.sqlite_conn = None
        self.pg_db = AsyncDatabase(postgres_url)

    def connect_sqlite(self) -> None:
        """Connect to SQLite database."""
        if not Path(self.sqlite_path).exists():
            raise FileNotFoundError(f"SQLite database not found: {self.sqlite_path}")

        self.sqlite_conn = sqlite3.connect(self.sqlite_path)
        self.sqlite_conn.row_factory = sqlite3.Row
        logger.info(f"Connected to SQLite: {self.sqlite_path}")

    def disconnect_sqlite(self) -> None:
        """Close SQLite connection."""
        if self.sqlite_conn:
            self.sqlite_conn.close()
            logger.info("Disconnected from SQLite")

    def _dict_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        """Convert SQLite row to dict."""
        if row is None:
            return None
        return dict(row)

    async def migrate_wallets(self) -> int:
        """Migrate wallets from SQLite to PostgreSQL."""
        cursor = self.sqlite_conn.cursor()
        cursor.execute("SELECT * FROM wallets")
        wallets = cursor.fetchall()

        count = 0
        for wallet_row in wallets:
            wallet = self._dict_from_row(wallet_row)
            await self.pg_db.upsert_wallet(
                address=wallet['address'],
                score=wallet['score'],
                win_rate=wallet['win_rate'],
                total_pnl=wallet['total_pnl'],
                roi=wallet['roi'],
                volume_30d=wallet['volume_30d'],
                avg_position=wallet['avg_position'],
                total_trades=wallet['total_trades'],
            )
            count += 1

        logger.info(f"✅ Migrated {count} wallets")
        return count

    async def migrate_trades(self) -> int:
        """Migrate trades from SQLite to PostgreSQL."""
        cursor = self.sqlite_conn.cursor()
        cursor.execute("SELECT * FROM trades")
        trades = cursor.fetchall()

        count = 0
        for trade_row in trades:
            trade = self._dict_from_row(trade_row)
            try:
                await self.pg_db.upsert_trade(
                    wallet_address=trade['wallet_address'],
                    market_id=trade['market_id'],
                    market_slug=trade['market_slug'],
                    market_title=trade['market_title'],
                    direction=trade['direction'],
                    price=trade['price'],
                    size_usd=trade['size_usd'],
                    timestamp=trade['timestamp'],
                    market_closes=trade['market_closes'],
                )
                count += 1
            except Exception as e:
                logger.warning(f"Failed to migrate trade {trade['id']}: {e}")

        logger.info(f"✅ Migrated {count} trades")
        return count

    async def migrate_alerts(self) -> int:
        """Migrate alerts from SQLite to PostgreSQL."""
        cursor = self.sqlite_conn.cursor()
        cursor.execute("SELECT * FROM alerts_sent")
        alerts = cursor.fetchall()

        count = 0
        for alert_row in alerts:
            alert = self._dict_from_row(alert_row)
            try:
                await self.pg_db.record_alert(
                    wallet_address=alert['wallet_address'],
                    market_id=alert['market_id'],
                    alert_type=alert['alert_type'],
                )
                count += 1
            except Exception as e:
                logger.warning(f"Failed to migrate alert {alert['id']}: {e}")

        logger.info(f"✅ Migrated {count} alerts")
        return count

    async def run(self) -> None:
        """Run complete migration."""
        logger.info("=" * 60)
        logger.info("PolyTracker SQLite → PostgreSQL Migration")
        logger.info("=" * 60)

        try:
            # Connect to PostgreSQL
            await self.pg_db.connect()

            # Migrate each table
            wallet_count = await self.migrate_wallets()
            trade_count = await self.migrate_trades()
            alert_count = await self.migrate_alerts()

            logger.info("=" * 60)
            logger.info("Migration Complete!")
            logger.info(f"  Wallets: {wallet_count}")
            logger.info(f"  Trades: {trade_count}")
            logger.info(f"  Alerts: {alert_count}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise

        finally:
            await self.pg_db.disconnect()


async def main():
    """Main entry point."""
    from polytracker.config import get_config

    config = get_config()

    # Get PostgreSQL URL from environment or use default
    postgres_url = os.getenv(
        'DATABASE_URL',
        'postgresql+asyncpg://polytracker:polytracker_dev@localhost:5432/polytracker'
    )

    migrator = SQLiteMigrator(
        sqlite_path=config.database_path,
        postgres_url=postgres_url,
    )

    migrator.connect_sqlite()
    try:
        await migrator.run()
    finally:
        migrator.disconnect_sqlite()


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    asyncio.run(main())
