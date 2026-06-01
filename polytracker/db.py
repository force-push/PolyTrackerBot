"""Database models and operations for PolyTracker Bot."""

import aiosqlite
from datetime import datetime, timezone
from typing import Optional, Any
from loguru import logger


class Database:
    """SQLite database manager for PolyTracker."""
    
    def __init__(self, db_path: str):
        """Initialize database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None
    
    async def connect(self):
        """Connect to database."""
        self.conn = await aiosqlite.connect(self.db_path)
        await self.init_schema()
    
    async def disconnect(self):
        """Close database connection."""
        if self.conn:
            await self.conn.close()
    
    async def init_schema(self):
        """Create tables if they don't exist."""
        if not self.conn:
            raise RuntimeError("Not connected to database")
        
        await self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS wallets (
                address TEXT PRIMARY KEY,
                score REAL,
                win_rate REAL,
                total_pnl REAL,
                roi REAL,
                volume_30d REAL,
                avg_position REAL,
                total_trades INTEGER,
                last_seen TIMESTAMP,
                added_at TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            );
            
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_address TEXT,
                market_id TEXT,
                market_slug TEXT,
                market_title TEXT,
                direction TEXT,
                price REAL,
                size_usd REAL,
                timestamp TIMESTAMP,
                market_closes TIMESTAMP,
                alerted BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (wallet_address) REFERENCES wallets(address)
            );
            
            CREATE TABLE IF NOT EXISTS alerts_sent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_address TEXT,
                market_id TEXT,
                sent_at TIMESTAMP,
                alert_type TEXT,
                FOREIGN KEY (wallet_address) REFERENCES wallets(address)
            );
            
            CREATE INDEX IF NOT EXISTS idx_trades_wallet ON trades(wallet_address);
            CREATE INDEX IF NOT EXISTS idx_trades_market ON trades(market_id);
            CREATE INDEX IF NOT EXISTS idx_trades_alerted ON trades(alerted);
            CREATE INDEX IF NOT EXISTS idx_alerts_wallet_market ON alerts_sent(wallet_address, market_id);
            CREATE INDEX IF NOT EXISTS idx_wallets_active ON wallets(is_active);
        """)
        await self.conn.commit()
        logger.info(f"Database schema initialized: {self.db_path}")
    
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
        """Insert or update a wallet.
        
        Args:
            address: Wallet address
            score: Calculated score (0-100)
            win_rate: Win rate (0-1)
            total_pnl: Total PnL in USD
            roi: Return on investment %
            volume_30d: 30-day volume in USD
            avg_position: Average position size
            total_trades: Total trades executed
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")
        
        now = datetime.now(timezone.utc).isoformat()
        
        await self.conn.execute("""
            INSERT INTO wallets (address, score, win_rate, total_pnl, roi, volume_30d, avg_position, total_trades, last_seen, added_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(address) DO UPDATE SET
                score = excluded.score,
                win_rate = excluded.win_rate,
                total_pnl = excluded.total_pnl,
                roi = excluded.roi,
                volume_30d = excluded.volume_30d,
                avg_position = excluded.avg_position,
                total_trades = excluded.total_trades,
                last_seen = excluded.last_seen
        """, (address, score, win_rate, total_pnl, roi, volume_30d, avg_position, total_trades, now, now))
        
        await self.conn.commit()
    
    async def get_active_wallets(self, limit: Optional[int] = None) -> list[dict[str, Any]]:
        """Get all active tracked wallets.
        
        Args:
            limit: Max wallets to return
        
        Returns:
            List of wallet dicts
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")
        
        query = "SELECT * FROM wallets WHERE is_active = TRUE ORDER BY score DESC"
        if limit:
            query += f" LIMIT {limit}"
        
        cursor = await self.conn.execute(query)
        rows = await cursor.fetchall()
        
        if not rows:
            return []
        
        # Convert to dicts
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    async def deactivate_wallet(self, address: str) -> None:
        """Deactivate a wallet.
        
        Args:
            address: Wallet address
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")
        
        await self.conn.execute(
            "UPDATE wallets SET is_active = FALSE WHERE address = ?",
            (address,)
        )
        await self.conn.commit()
    
    async def get_wallet(self, address: str) -> Optional[dict[str, Any]]:
        """Get a single wallet by address.
        
        Args:
            address: Wallet address
        
        Returns:
            Wallet dict or None
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")
        
        cursor = await self.conn.execute(
            "SELECT * FROM wallets WHERE address = ?",
            (address,)
        )
        row = await cursor.fetchone()
        
        if not row:
            return None
        
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
    
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
        """Insert or update a trade record.
        
        Args:
            wallet_address: Wallet address
            market_id: Polymarket market ID
            market_slug: Market slug
            market_title: Market title
            direction: YES or NO
            price: Entry price
            size_usd: Position size in USD
            timestamp: Trade timestamp (ISO format)
            market_closes: Market close timestamp
        
        Returns:
            Trade ID
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")
        
        cursor = await self.conn.execute("""
            INSERT INTO trades (wallet_address, market_id, market_slug, market_title, direction, price, size_usd, timestamp, market_closes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (wallet_address, market_id, market_slug, market_title, direction, price, size_usd, timestamp, market_closes))
        
        await self.conn.commit()
        return cursor.lastrowid
    
    async def get_unalerted_trades(self) -> list[dict[str, Any]]:
        """Get trades that haven't been alerted on yet.
        
        Returns:
            List of trade dicts
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")
        
        cursor = await self.conn.execute("""
            SELECT t.*, w.score FROM trades t
            JOIN wallets w ON t.wallet_address = w.address
            WHERE t.alerted = FALSE AND w.is_active = TRUE
            ORDER BY t.timestamp DESC
        """)
        rows = await cursor.fetchall()
        
        if not rows:
            return []
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    async def mark_trade_alerted(self, trade_id: int) -> None:
        """Mark a trade as alerted.
        
        Args:
            trade_id: Trade ID
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")
        
        await self.conn.execute(
            "UPDATE trades SET alerted = TRUE WHERE id = ?",
            (trade_id,)
        )
        await self.conn.commit()
    
    async def get_trades_for_market(self, market_id: str) -> list[dict[str, Any]]:
        """Get all trades for a specific market.
        
        Args:
            market_id: Market ID
        
        Returns:
            List of trade dicts
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")
        
        cursor = await self.conn.execute(
            "SELECT * FROM trades WHERE market_id = ?",
            (market_id,)
        )
        rows = await cursor.fetchall()
        
        if not rows:
            return []
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    # ============================================
    # ALERT OPERATIONS
    # ============================================
    
    async def record_alert(self, wallet_address: str, market_id: str, alert_type: str) -> None:
        """Record an alert that was sent.
        
        Args:
            wallet_address: Wallet address
            market_id: Market ID
            alert_type: 'standard' or 'high_conviction'
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")
        
        now = datetime.now(timezone.utc).isoformat()
        
        await self.conn.execute("""
            INSERT INTO alerts_sent (wallet_address, market_id, sent_at, alert_type)
            VALUES (?, ?, ?, ?)
        """, (wallet_address, market_id, now, alert_type))
        
        await self.conn.commit()
    
    async def has_alert_for_market(self, wallet_address: str, market_id: str) -> bool:
        """Check if an alert has been sent for this wallet-market combo.
        
        Args:
            wallet_address: Wallet address
            market_id: Market ID
        
        Returns:
            True if alert already sent, False otherwise
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")
        
        cursor = await self.conn.execute(
            "SELECT 1 FROM alerts_sent WHERE wallet_address = ? AND market_id = ? LIMIT 1",
            (wallet_address, market_id)
        )
        return await cursor.fetchone() is not None
