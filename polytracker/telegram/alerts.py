"""Alert formatting for Telegram."""

from datetime import datetime, timezone
from typing import Any
from loguru import logger


def format_standard_alert(data: dict[str, Any]) -> str:
    """Format a standard trade signal alert.
    
    Args:
        data: Dict with keys:
            - wallet: Wallet dict (address, score, win_rate, total_pnl, roi)
            - position: Position dict (direction, size_usd, price)
            - market: Market dict (title, liquidity, closes_at)
    
    Returns:
        HTML-formatted message string
    """
    try:
        wallet = data.get('wallet', {})
        position = data.get('position', {})
        market = data.get('market', {})
        
        address = wallet.get('address', '0x????')
        score = wallet.get('score', 0)
        win_rate = wallet.get('win_rate', 0)
        total_pnl = wallet.get('total_pnl', 0)
        roi = wallet.get('roi', 0)
        
        direction = position.get('direction', 'YES')
        size_usd = position.get('size_usd', 0)
        price = position.get('price', 0)
        
        title = market.get('title', 'Unknown Market')
        liquidity = market.get('liquidity', 0)
        closes_at = market.get('closes_at') or market.get('resolves_at')
        
        # Format address
        addr_short = f"{address[:6]}...{address[-4:]}" if len(address) > 10 else address
        
        # Calculate time remaining
        time_remaining = _format_time_remaining(closes_at)
        
        # Estimate risk/confidence
        risk_level = _estimate_risk(win_rate, score, size_usd)
        confidence = _estimate_confidence(score, win_rate)
        
        message = f"""📡 <b>POLYTRACKER SIGNAL</b>

<b>Wallet:</b> <code>{addr_short}</code> [Score: {score:.0f}/100]
<b>Win Rate:</b> {win_rate*100:.0f}% | <b>PnL:</b> ${total_pnl:,.0f} | <b>ROI:</b> {roi:+.0f}%

📌 <b>Market:</b> {title[:60]}
<b>Position:</b> {direction} @ ${price:.2f}
<b>Size:</b> ${size_usd:,.0f}
<b>Liquidity:</b> ${liquidity:,.0f}
<b>Closes:</b> {time_remaining}

🔗 <b>Market:</b> <a href="https://polymarket.com/profile/{address}">View</a>
🔗 <b>Wallet:</b> <a href="https://polymarket.com/profile/{address}">View</a>

<b>Risk:</b> {risk_level} | <b>Confidence:</b> {confidence}
"""
        return message
    
    except Exception as e:
        logger.error(f"Error formatting standard alert: {e}")
        return ""


def format_high_conviction_alert(data: dict[str, Any]) -> str:
    """Format a high conviction alert (2+ wallets same market).
    
    Args:
        data: Dict with keys:
            - wallets: List of wallet dicts
            - positions: List of position dicts
            - market: Market dict
    
    Returns:
        HTML-formatted message string
    """
    try:
        wallets = data.get('wallets', [])
        market = data.get('market', {})
        
        if not wallets or not market:
            return ""
        
        title = market.get('title', 'Unknown Market')
        liquidity = market.get('liquidity', 0)
        closes_at = market.get('closes_at') or market.get('resolves_at')
        
        # Format time remaining
        time_remaining = _format_time_remaining(closes_at)
        
        # Build wallet list
        wallet_lines = []
        total_size = 0
        for wallet in wallets:
            addr = wallet.get('address', '0x????')
            addr_short = f"{addr[:6]}...{addr[-4:]}" if len(addr) > 10 else addr
            score = wallet.get('score', 0)
            position = wallet.get('position', {})
            direction = position.get('direction', 'YES')
            price = position.get('price', 0)
            size = position.get('size_usd', 0)
            total_size += size
            
            wallet_lines.append(
                f"  • <code>{addr_short}</code> (Score: {score:.0f}) → {direction} @ ${price:.2f} (${size:,.0f})"
            )
        
        wallets_text = "\n".join(wallet_lines)
        
        message = f"""🔥 <b>HIGH CONVICTION — POLYTRACKER</b>

<b>{len(wallets)} tracked whales entered the same market!</b>

<b>Wallets:</b>
{wallets_text}

📌 <b>Market:</b> {title[:60]}
<b>Combined Position:</b> ${total_size:,.0f}
<b>Liquidity:</b> ${liquidity:,.0f}
<b>Closes:</b> {time_remaining}

🔗 <a href="https://polymarket.com/event/{market.get('slug', '')}">View Market</a>
"""
        return message
    
    except Exception as e:
        logger.error(f"Error formatting high conviction alert: {e}")
        return ""


def _format_time_remaining(closes_at: str | None) -> str:
    """Format time remaining until market close.
    
    Args:
        closes_at: ISO timestamp string
    
    Returns:
        Formatted time string (e.g., "14d 6h")
    """
    if not closes_at:
        return "Unknown"
    
    try:
        if isinstance(closes_at, str):
            closes_at = closes_at.rstrip('Z')
            if '.' in closes_at:
                close_dt = datetime.fromisoformat(closes_at.split('.')[0])
            else:
                close_dt = datetime.fromisoformat(closes_at)
        else:
            close_dt = closes_at
        
        if close_dt.tzinfo is None:
            close_dt = close_dt.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        delta = close_dt - now
        
        if delta.total_seconds() < 0:
            return "Expired"
        
        days = delta.days
        hours = delta.seconds // 3600
        
        if days > 0:
            return f"{days}d {hours}h"
        else:
            return f"{hours}h"
    
    except Exception as e:
        logger.debug(f"Could not parse close time: {e}")
        return "Unknown"


def _estimate_risk(win_rate: float, score: float, size_usd: float) -> str:
    """Estimate risk level.
    
    Args:
        win_rate: Win rate (0-1)
        score: Wallet score (0-100)
        size_usd: Position size
    
    Returns:
        Risk label (LOW, MEDIUM, HIGH)
    """
    if win_rate >= 0.70 and score >= 80:
        return "LOW"
    elif win_rate >= 0.60 and score >= 60:
        return "MEDIUM"
    else:
        return "HIGH"


def _estimate_confidence(score: float, win_rate: float) -> str:
    """Estimate confidence level.
    
    Args:
        score: Wallet score (0-100)
        win_rate: Win rate (0-1)
    
    Returns:
        Confidence label (LOW, MEDIUM, HIGH)
    """
    if score >= 85 and win_rate >= 0.70:
        return "HIGH"
    elif score >= 65 and win_rate >= 0.60:
        return "MEDIUM"
    else:
        return "LOW"
