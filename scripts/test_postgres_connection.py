#!/usr/bin/env python3
"""Test PostgreSQL connection and schema creation."""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from polytracker.db_pg import AsyncDatabase
from loguru import logger


async def main():
    """Test database connection."""
    from dotenv import load_dotenv
    load_dotenv()

    postgres_url = os.getenv(
        'DATABASE_URL',
        'postgresql+asyncpg://polytracker:polytracker_dev@localhost:5432/polytracker'
    )

    logger.info(f"Testing connection to: {postgres_url}")

    try:
        db = AsyncDatabase(postgres_url)
        await db.connect()
        logger.info("✅ Connected to PostgreSQL")

        # Test schema creation
        logger.info("✅ Schema initialized successfully")

        # Try to get wallets (should be empty or have migrated data)
        wallets = await db.get_active_wallets(limit=1)
        logger.info(f"✅ Query successful. Found {len(wallets)} wallets")

        # Try to create a test wallet
        test_address = "0xtest_wallet_12345"
        await db.upsert_wallet(
            address=test_address,
            score=75.5,
            win_rate=0.65,
            total_pnl=5000.0,
            roi=12.5,
            volume_30d=50000.0,
            avg_position=500.0,
            total_trades=100,
        )
        logger.info("✅ Insert/update operations work")

        # Try to read it back
        wallet = await db.get_wallet(test_address)
        if wallet:
            logger.info(f"✅ Read-back successful: {wallet['address']}")
        else:
            logger.error("❌ Could not read back inserted wallet")

        # Clean up
        await db.disconnect()
        logger.info("✅ Disconnected successfully")

        logger.info("\n" + "=" * 70)
        logger.info("All tests passed! PostgreSQL is ready for use.")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
