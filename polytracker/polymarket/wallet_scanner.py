"""Wallet discovery and scoring for PolyTracker."""

from datetime import datetime, timezone
from loguru import logger

from polytracker.polymarket.client import PolymarketClient
from polytracker.signals.scorer import calculate_wallet_score, validate_wallet_for_tracking


class WalletScanner:
    """Discovers and scores high-performing Polymarket wallets."""
    
    def __init__(self, config, db):
        """Initialize scanner.
        
        Args:
            config: AppConfig object
            db: Database instance
        """
        self.config = config
        self.db = db
    
    async def discover_wallets(self):
        """Discover top traders and add/update in database.
        
        Process:
        1. Fetch top 100-200 traders from leaderboard
        2. Score each wallet
        3. Filter by MIN_* thresholds
        4. Persist top MAX_WALLETS_TRACKED
        5. Log results
        """
        logger.info("🔍 Starting wallet discovery...")
        
        try:
            async with PolymarketClient(self.config.polymarket) as client:
                # Fetch leaderboard
                leaderboard = await client.get_trader_leaderboard(
                    category="OVERALL",
                    time_period="ALL",
                    order_by="PNL",
                    limit=100,
                    offset=0,
                )
                
                if not leaderboard:
                    logger.warning("No leaderboard data received")
                    return
                
                logger.info(f"Retrieved {len(leaderboard)} traders from leaderboard")
                
                # Score and filter wallets
                candidates = []
                for trader in leaderboard:
                    address = trader.get('proxyWallet') or trader.get('address')
                    if not address:
                        continue

                    # Extract stats from leaderboard (no separate profile call needed)
                    stats = self._extract_stats_from_leaderboard(trader, address)
                    if not stats:
                        continue
                    
                    # Validate against thresholds
                    is_valid, reason = validate_wallet_for_tracking(
                        stats,
                        min_win_rate=self.config.wallet_scoring.min_win_rate,
                        min_pnl=self.config.wallet_scoring.min_total_pnl,
                        min_trades=self.config.wallet_scoring.min_trades,
                        min_avg_position=self.config.wallet_scoring.min_avg_position,
                        min_volume_30d=self.config.wallet_scoring.min_volume_30d,
                    )
                    
                    if not is_valid:
                        continue
                    
                    # Calculate score
                    score = calculate_wallet_score(stats)
                    
                    candidates.append({
                        'address': address,
                        'score': score,
                        'stats': stats,
                    })
                
                # Sort by score
                candidates.sort(key=lambda x: x['score'], reverse=True)
                
                # Keep only top N
                top_wallets = candidates[:self.config.wallet_scoring.max_wallets_tracked]
                logger.info(f"Found {len(top_wallets)} qualifying wallets")
                
                # Persist to database
                tracked_addresses = set()
                for wallet in top_wallets:
                    await self.db.upsert_wallet(
                        address=wallet['address'],
                        score=wallet['score'],
                        win_rate=wallet['stats'].get('win_rate', 0),
                        total_pnl=wallet['stats'].get('total_pnl', 0),
                        roi=wallet['stats'].get('roi', 0),
                        volume_30d=wallet['stats'].get('volume_30d', 0),
                        avg_position=wallet['stats'].get('avg_position', 0),
                        total_trades=wallet['stats'].get('total_trades', 0),
                    )
                    tracked_addresses.add(wallet['address'])
                    logger.debug(f"✅ {wallet['address'][:10]}... Score: {wallet['score']:.1f}")
                
                # Deactivate wallets that dropped off top list
                existing = await self.db.get_active_wallets()
                for wallet in existing:
                    if wallet['address'] not in tracked_addresses:
                        await self.db.deactivate_wallet(wallet['address'])
                        logger.debug(f"⭕ Deactivated {wallet['address'][:10]}...")
                
                logger.info(f"✅ Wallet discovery complete. Tracking {len(top_wallets)} wallets")
        
        except Exception as e:
            logger.error(f"Wallet discovery failed: {e}")
    
    async def rescore_wallets(self):
        """Re-evaluate all active wallets and update scores.
        
        Deactivates wallets that no longer meet thresholds.
        """
        logger.info("📊 Starting wallet rescoring...")
        
        try:
            existing_wallets = await self.db.get_active_wallets()
            if not existing_wallets:
                logger.info("No active wallets to rescore")
                return
            
            async with PolymarketClient(self.config.polymarket) as client:
                updated_count = 0
                deactivated_count = 0
                
                for wallet in existing_wallets:
                    address = wallet['address']
                    
                    # Fetch fresh stats
                    stats = await self._fetch_wallet_stats(client, address)
                    if not stats:
                        logger.warning(f"Could not fetch stats for {address}")
                        continue
                    
                    # Check if still meets thresholds
                    is_valid, reason = validate_wallet_for_tracking(
                        stats,
                        min_win_rate=self.config.wallet_scoring.min_win_rate,
                        min_pnl=self.config.wallet_scoring.min_total_pnl,
                        min_trades=self.config.wallet_scoring.min_trades,
                        min_avg_position=self.config.wallet_scoring.min_avg_position,
                        min_volume_30d=self.config.wallet_scoring.min_volume_30d,
                    )
                    
                    if not is_valid:
                        await self.db.deactivate_wallet(address)
                        logger.debug(f"⭕ Deactivated {address[:10]}... ({reason})")
                        deactivated_count += 1
                        continue
                    
                    # Recalculate score and update
                    new_score = calculate_wallet_score(stats)
                    await self.db.upsert_wallet(
                        address=address,
                        score=new_score,
                        win_rate=stats.get('win_rate', 0),
                        total_pnl=stats.get('total_pnl', 0),
                        roi=stats.get('roi', 0),
                        volume_30d=stats.get('volume_30d', 0),
                        avg_position=stats.get('avg_position', 0),
                        total_trades=stats.get('total_trades', 0),
                    )
                    updated_count += 1
                    logger.debug(f"✅ {address[:10]}... New score: {new_score:.1f}")
                
                logger.info(f"✅ Rescoring complete. Updated: {updated_count}, Deactivated: {deactivated_count}")
        
        except Exception as e:
            logger.error(f"Wallet rescoring failed: {e}")
    
    def _extract_stats_from_leaderboard(self, trader: dict, address: str) -> dict | None:
        """Extract wallet stats from leaderboard response.

        Args:
            trader: Trader dict from leaderboard response
            address: Wallet address

        Returns:
            Stats dict or None if insufficient data
        """
        try:
            # Extract from leaderboard response
            vol = float(trader.get('vol', 0))
            pnl = float(trader.get('pnl', 0))

            # Estimate win_rate from rank and PnL (rough heuristic)
            # Real win_rate would come from detailed trade history
            win_rate = 0.65 if pnl > 0 else 0.45

            # ROI estimate
            roi = 15.0 if pnl > 10000 else (10.0 if pnl > 5000 else 5.0)

            # Average position size estimate
            avg_position = vol / 150 if vol > 0 else 100

            # Estimate total trades from volume
            total_trades = int(vol / avg_position) if avg_position > 0 else 0

            return {
                'address': address,
                'win_rate': win_rate,
                'total_pnl': pnl,
                'roi': roi,
                'volume_30d': vol,
                'avg_position': avg_position,
                'total_trades': total_trades,
                'last_trade_date': None,
            }

        except Exception as e:
            logger.warning(f"Failed to extract stats for {address}: {e}")
            return None
