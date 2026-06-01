#!/usr/bin/env python3
"""Validate Phase 1 setup and readiness for Phase 2."""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from polytracker.db_pg import AsyncDatabase
from loguru import logger


class Phase1Validator:
    """Validate Phase 1 setup completeness."""

    def __init__(self):
        """Initialize validator."""
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = []

    async def check_database_connection(self) -> bool:
        """Check PostgreSQL connection."""
        logger.info("[1/8] Checking PostgreSQL connection...")
        try:
            db = AsyncDatabase()
            await db.connect()
            await db.disconnect()
            logger.info("  ✅ PostgreSQL connected")
            self.checks_passed += 1
            return True
        except Exception as e:
            logger.error(f"  ❌ Connection failed: {e}")
            self.checks_failed += 1
            return False

    async def check_schema_creation(self) -> bool:
        """Check database schema creation."""
        logger.info("[2/8] Checking schema creation...")
        try:
            db = AsyncDatabase()
            await db.connect()

            # Try to get wallets (triggers schema check)
            wallets = await db.get_active_wallets(limit=1)
            logger.info(f"  ✅ Schema initialized (found {len(wallets)} wallets)")

            await db.disconnect()
            self.checks_passed += 1
            return True
        except Exception as e:
            logger.error(f"  ❌ Schema check failed: {e}")
            self.checks_failed += 1
            return False

    async def check_wallet_operations(self) -> bool:
        """Check wallet CRUD operations."""
        logger.info("[3/8] Checking wallet operations...")
        try:
            db = AsyncDatabase()
            await db.connect()

            test_addr = f"0xvalidator_{datetime.now(timezone.utc).timestamp()}"

            # Insert
            await db.upsert_wallet(
                address=test_addr,
                score=75.0,
                win_rate=0.65,
                total_pnl=1000.0,
                roi=10.0,
                volume_30d=10000.0,
                avg_position=100.0,
                total_trades=50,
            )

            # Read
            wallet = await db.get_wallet(test_addr)
            if wallet and wallet['address'] == test_addr:
                logger.info("  ✅ Wallet operations working")
                self.checks_passed += 1
                await db.disconnect()
                return True
            else:
                logger.error("  ❌ Wallet read-back failed")
                self.checks_failed += 1
                await db.disconnect()
                return False

        except Exception as e:
            logger.error(f"  ❌ Wallet operations failed: {e}")
            self.checks_failed += 1
            return False

    async def check_trade_operations(self) -> bool:
        """Check trade CRUD operations."""
        logger.info("[4/8] Checking trade operations...")
        try:
            db = AsyncDatabase()
            await db.connect()

            # Get or create a test wallet
            test_wallet = f"0xtest_trades_{datetime.now(timezone.utc).timestamp()}"
            await db.upsert_wallet(
                address=test_wallet,
                score=70.0,
                win_rate=0.60,
                total_pnl=500.0,
                roi=5.0,
                volume_30d=5000.0,
                avg_position=50.0,
                total_trades=25,
            )

            # Insert trade
            trade_id = await db.upsert_trade(
                wallet_address=test_wallet,
                market_id="test_market_123",
                market_slug="test-market",
                market_title="Test Market",
                direction="YES",
                price=0.65,
                size_usd=100.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            if trade_id:
                logger.info("  ✅ Trade operations working")
                self.checks_passed += 1
                await db.disconnect()
                return True
            else:
                logger.error("  ❌ Trade insert failed")
                self.checks_failed += 1
                await db.disconnect()
                return False

        except Exception as e:
            logger.error(f"  ❌ Trade operations failed: {e}")
            self.checks_failed += 1
            return False

    async def check_alert_operations(self) -> bool:
        """Check alert recording operations."""
        logger.info("[5/8] Checking alert operations...")
        try:
            db = AsyncDatabase()
            await db.connect()

            test_wallet = f"0xtest_alerts_{datetime.now(timezone.utc).timestamp()}"
            await db.upsert_wallet(
                address=test_wallet,
                score=70.0,
                win_rate=0.60,
                total_pnl=500.0,
                roi=5.0,
                volume_30d=5000.0,
                avg_position=50.0,
                total_trades=25,
            )

            # Record alert
            await db.record_alert(
                wallet_address=test_wallet,
                market_id="test_market_alert",
                alert_type="standard",
            )

            # Check if alert exists
            has_alert = await db.has_alert_for_market(test_wallet, "test_market_alert")

            if has_alert:
                logger.info("  ✅ Alert operations working")
                self.checks_passed += 1
                await db.disconnect()
                return True
            else:
                logger.error("  ❌ Alert verification failed")
                self.checks_failed += 1
                await db.disconnect()
                return False

        except Exception as e:
            logger.error(f"  ❌ Alert operations failed: {e}")
            self.checks_failed += 1
            return False

    async def check_backtest_operations(self) -> bool:
        """Check backtest recording operations."""
        logger.info("[6/8] Checking backtest operations...")
        try:
            db = AsyncDatabase()
            await db.connect()

            run_id = f"validation_{datetime.now(timezone.utc).timestamp()}"
            start = datetime(2026, 1, 1, tzinfo=timezone.utc)
            end = datetime(2026, 6, 1, tzinfo=timezone.utc)

            # Create backtest
            await db.create_backtest_run(
                run_id=run_id,
                start_date=start,
                end_date=end,
                config='{"test": true}',
                notes="Phase 1 validation",
            )

            # Update backtest
            await db.update_backtest_run(
                run_id=run_id,
                total_signals=100,
                resolved_signals=50,
                profitable_signals=35,
                win_rate=0.70,
                avg_roi=12.5,
                total_pnl=5000.0,
            )

            # Retrieve
            backtest = await db.get_backtest_run(run_id)
            if backtest and backtest['total_signals'] == 100:
                logger.info("  ✅ Backtest operations working")
                self.checks_passed += 1
                await db.disconnect()
                return True
            else:
                logger.error("  ❌ Backtest retrieval failed")
                self.checks_failed += 1
                await db.disconnect()
                return False

        except Exception as e:
            logger.error(f"  ❌ Backtest operations failed: {e}")
            self.checks_failed += 1
            return False

    def check_dependencies(self) -> bool:
        """Check required dependencies installed."""
        logger.info("[7/8] Checking dependencies...")
        required_packages = [
            'sqlalchemy',
            'asyncpg',
            'loguru',
            'pydantic',
            'python_dotenv',
        ]

        try:
            for package in required_packages:
                __import__(package.replace('_', '-').replace('-', '_'))
            logger.info("  ✅ All dependencies installed")
            self.checks_passed += 1
            return True
        except ImportError as e:
            logger.error(f"  ❌ Missing dependency: {e}")
            logger.error("     Run: pip install sqlalchemy asyncpg alembic")
            self.checks_failed += 1
            return False

    def check_files(self) -> bool:
        """Check Phase 1 files exist."""
        logger.info("[8/8] Checking Phase 1 files...")
        required_files = [
            'docker-compose-pg.yml',
            'polytracker/models.py',
            'polytracker/db_pg.py',
            'scripts/migrate_to_postgres.py',
            'scripts/backtest.py',
            'scripts/analyze.py',
            'scripts/test_postgres_connection.py',
            'scripts/init_postgres.sql',
            'PHASE_1_QUICKSTART.md',
            'PHASE_1_SETUP.md',
        ]

        project_root = Path(__file__).parent.parent
        missing_files = []

        for file in required_files:
            file_path = project_root / file
            if not file_path.exists():
                missing_files.append(file)

        if not missing_files:
            logger.info(f"  ✅ All {len(required_files)} Phase 1 files present")
            self.checks_passed += 1
            return True
        else:
            logger.error(f"  ❌ Missing {len(missing_files)} files:")
            for f in missing_files:
                logger.error(f"     - {f}")
            self.checks_failed += 1
            return False

    async def run_all_checks(self) -> bool:
        """Run all validation checks."""
        logger.info("=" * 80)
        logger.info("PHASE 1 VALIDATION")
        logger.info("=" * 80)

        await self.check_database_connection()
        await self.check_schema_creation()
        await self.check_wallet_operations()
        await self.check_trade_operations()
        await self.check_alert_operations()
        await self.check_backtest_operations()
        self.check_dependencies()
        self.check_files()

        logger.info("=" * 80)
        logger.info(f"RESULTS: {self.checks_passed} passed, {self.checks_failed} failed")
        logger.info("=" * 80)

        if self.checks_failed == 0:
            logger.info("\n✅ Phase 1 validation PASSED")
            logger.info("You're ready to move to Phase 2: Trade Execution Layer")
            return True
        else:
            logger.error(f"\n❌ Phase 1 validation FAILED ({self.checks_failed} issues)")
            logger.error("Please fix the above issues before proceeding to Phase 2")
            return False


async def main():
    """Main entry point."""
    from dotenv import load_dotenv
    load_dotenv()

    validator = Phase1Validator()
    success = await validator.run_all_checks()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
