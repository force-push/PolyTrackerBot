"""Trade monitoring for tracked wallets."""

from datetime import datetime, timezone
from loguru import logger

from polytracker.polymarket.client import PolymarketClient
from polytracker.signals.filter import is_viable_signal


class TradeMonitor:
    """Monitors tracked wallets for new trading positions."""
    
    def __init__(self, config, db, telegram_bot):
        """Initialize trade monitor.
        
        Args:
            config: AppConfig object
            db: Database instance
            telegram_bot: TelegramBot instance for alerts
        """
        self.config = config
        self.db = db
        self.telegram_bot = telegram_bot
    
    async def monitor_wallets(self):
        """Monitor all active wallets for new positions.
        
        Process:
        1. Fetch all active wallets
        2. For each wallet, fetch current positions
        3. Compare against DB to find NEW trades
        4. For each new trade, check viability
        5. If viable, send alert and persist
        """
        logger.info("👁️ Monitoring wallets for new positions...")
        
        try:
            active_wallets = await self.db.get_active_wallets()
            if not active_wallets:
                logger.info("No active wallets to monitor")
                return
            
            logger.info(f"Monitoring {len(active_wallets)} wallets")
            
            async with PolymarketClient(self.config.polymarket) as client:
                alerts_sent = 0
                
                for wallet in active_wallets:
                    new_positions = await self._check_wallet_for_new_positions(
                        client, wallet
                    )
                    
                    # Process each new position
                    for position in new_positions:
                        try:
                            is_viable, alert_type, reason = await is_viable_signal(
                                position, self.config, self.db, client
                            )
                            
                            if is_viable:
                                # Send alert
                                await self._send_position_alert(
                                    wallet, position, alert_type, client
                                )
                                alerts_sent += 1
                            else:
                                logger.debug(f"Position filtered: {reason}")
                        
                        except Exception as e:
                            logger.error(f"Error processing position: {e}")
                            continue
                
                logger.info(f"✅ Monitoring complete. Alerts sent: {alerts_sent}")
        
        except Exception as e:
            logger.error(f"Wallet monitoring failed: {e}")
    
    async def _check_wallet_for_new_positions(self, client, wallet: dict) -> list[dict]:
        """Check wallet for positions not yet in database.
        
        Args:
            client: PolymarketClient instance
            wallet: Wallet dict from DB
        
        Returns:
            List of new position dicts
        """
        address = wallet['address']
        
        try:
            # Fetch current positions
            positions = await client.get_wallet_positions(address)
            if not positions:
                return []
            
            new_positions = []
            
            for position in positions:
                market_id = position.get('market_id') or position.get('condition_id')
                
                # Check if we already have this trade in DB
                existing_trades = await self.db.get_trades_for_market(market_id)
                market_traded = any(t['wallet_address'] == address for t in existing_trades)
                
                if not market_traded:
                    # New position for this wallet
                    position['wallet_address'] = address
                    position['wallet_score'] = wallet['score']
                    new_positions.append(position)
            
            if new_positions:
                logger.debug(f"Found {len(new_positions)} new position(s) for {address[:10]}...")
            
            return new_positions
        
        except Exception as e:
            logger.error(f"Error checking positions for {address}: {e}")
            return []
    
    async def _send_position_alert(
        self,
        wallet: dict,
        position: dict,
        alert_type: str,
        client: PolymarketClient,
    ) -> None:
        """Send Telegram alert for a new position.
        
        Args:
            wallet: Wallet dict
            position: Position dict
            alert_type: 'standard' or 'high_conviction'
            client: PolymarketClient for fetching market details
        """
        try:
            market_id = position.get('market_id') or position.get('condition_id')
            market_slug = position.get('market_slug')
            
            # Fetch market details
            market = None
            if market_slug:
                market = await client.get_market_by_slug(market_slug)
            elif market_id:
                market = await client.get_market_by_id(market_id)
            
            # Send via telegram bot
            await self.telegram_bot.send_alert(
                alert_type=alert_type,
                data={
                    'wallet': wallet,
                    'position': position,
                    'market': market or {},
                }
            )
            
            # Record trade in database
            now = datetime.now(timezone.utc).isoformat()
            market_closes = position.get('market_closes') or position.get('resolves_at')
            
            trade_id = await self.db.upsert_trade(
                wallet_address=wallet['address'],
                market_id=market_id,
                market_slug=market_slug or '',
                market_title=market.get('title') if market else '',
                direction=position.get('direction') or 'YES',
                price=float(position.get('price', 0)),
                size_usd=float(position.get('size_usd', 0)),
                timestamp=now,
                market_closes=market_closes,
            )
            
            # Record alert sent
            await self.db.record_alert(
                wallet_address=wallet['address'],
                market_id=market_id,
                alert_type=alert_type,
            )
            
            logger.info(
                f"✅ Alert sent: {wallet['address'][:10]}... "
                f"→ {market.get('title', 'Unknown')[:40] if market else 'Unknown'}"
            )
        
        except Exception as e:
            logger.error(f"Failed to send position alert: {e}")
