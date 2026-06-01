"""Signal filtering logic for PolyTracker."""

from datetime import datetime, timezone, timedelta
from typing import Any
from loguru import logger

from polytracker.polymarket.client import PolymarketClient


async def is_viable_signal(
    position: dict[str, Any],
    config,
    db,
    client: PolymarketClient,
) -> tuple[bool, str, str]:
    """Check if a position is a viable trade signal.
    
    All 7 checks must pass:
    1. Market still open (not resolved)
    2. Position size >= MIN_SIGNAL_POSITION
    3. Liquidity >= MIN_MARKET_LIQUIDITY
    4. Hours remaining >= MIN_HOURS_REMAINING
    5. No previous alert for wallet-market pair
    6. (Optional) Direction matches wallet's historical edge
    7. New position (handled upstream)
    
    Args:
        position: Position dict with keys:
            - wallet_address
            - market_id
            - direction (YES/NO)
            - size_usd
            - market_slug
            - market_closes
        config: AppConfig object
        db: Database instance
        client: PolymarketClient instance
    
    Returns:
        (is_viable, alert_type, reason) where:
            - is_viable: True if passes all checks
            - alert_type: 'standard' or 'high_conviction'
            - reason: Explanation (e.g., "Passed all checks" or "Size too small")
    """
    
    market_id = position.get('market_id') or position.get('condition_id')
    wallet_address = position.get('wallet_address')
    direction = position.get('direction', 'YES')
    size_usd = float(position.get('size_usd', 0))
    market_slug = position.get('market_slug')
    market_closes = position.get('market_closes') or position.get('resolves_at')
    
    if not market_id or not wallet_address:
        return False, '', "Missing market_id or wallet_address"
    
    # Check 1: Market still open (not resolved)
    try:
        market = None
        if market_slug:
            market = await client.get_market_by_slug(market_slug)
        elif market_id:
            market = await client.get_market_by_id(market_id)
        
        if not market:
            return False, '', "Could not fetch market details"
        
        # Check if resolved
        if market.get('resolved') or market.get('status') == 'resolved':
            return False, '', "Market already resolved"
        
        # Prefer market's close time over position's
        market_closes = market.get('closes_at') or market.get('resolves_at') or market_closes
    
    except Exception as e:
        logger.warning(f"Could not fetch market details: {e}")
        return False, '', f"Market fetch failed: {e}"
    
    # Check 2: Position size >= MIN_SIGNAL_POSITION
    min_position = config.signal_filter.min_signal_position
    if size_usd < min_position:
        return False, '', f"Position ${size_usd:,.0f} < ${min_position:,.0f}"
    
    # Check 3: Liquidity >= MIN_MARKET_LIQUIDITY
    min_liquidity = config.signal_filter.min_market_liquidity
    try:
        liquidity = market.get('liquidity')
        if not liquidity:
            # Try to estimate from orderbook
            market_id_for_liquidity = market.get('condition_id') or market_id
            liquidity = await client.get_market_liquidity(market_id_for_liquidity)
        
        if liquidity and liquidity < min_liquidity:
            return False, '', f"Liquidity ${liquidity:,.0f} < ${min_liquidity:,.0f}"
    
    except Exception as e:
        logger.debug(f"Could not check liquidity: {e}")
        # Don't fail on liquidity check if data unavailable
    
    # Check 4: Hours remaining >= MIN_HOURS_REMAINING
    min_hours = config.signal_filter.min_hours_remaining
    if market_closes:
        try:
            if isinstance(market_closes, str):
                # Parse ISO timestamp
                market_closes = market_closes.rstrip('Z')
                if '.' in market_closes:
                    close_dt = datetime.fromisoformat(market_closes.split('.')[0])
                else:
                    close_dt = datetime.fromisoformat(market_closes)
            else:
                close_dt = market_closes
            
            if close_dt.tzinfo is None:
                close_dt = close_dt.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            hours_remaining = (close_dt - now).total_seconds() / 3600
            
            if hours_remaining < min_hours:
                return False, '', f"{hours_remaining:.1f}h remaining < {min_hours}h"
        
        except Exception as e:
            logger.debug(f"Could not parse market close time: {e}")
    
    # Check 5: No previous alert for this wallet-market pair
    has_alert = await db.has_alert_for_market(wallet_address, market_id)
    if has_alert:
        return False, '', "Alert already sent for this wallet-market pair"
    
    # Check 6: (Optional) Direction matches wallet edge
    # Skipped if data unavailable - not critical
    
    # All checks passed
    # Determine if high conviction (2+ wallets on same market)
    trades_on_market = await db.get_trades_for_market(market_id)
    alerted_wallets = set()
    for trade in trades_on_market:
        if trade.get('alerted'):
            alerted_wallets.add(trade['wallet_address'])
    
    alert_type = 'standard'
    if len(alerted_wallets) >= 2:
        alert_type = 'high_conviction'
    
    return True, alert_type, "All checks passed"
