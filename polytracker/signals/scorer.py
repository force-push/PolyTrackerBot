"""Wallet scoring logic for PolyTracker."""

import math
from datetime import datetime, timezone
from typing import Any
from loguru import logger


def calculate_wallet_score(stats: dict[str, Any]) -> float:
    """Calculate wallet score based on profitability metrics.
    
    Formula:
        score = (win_rate*40) + (log(pnl)*20) + (roi*20) + (recency*20)
    
    Args:
        stats: Dict with keys:
            - win_rate (0-1): Win rate percentage
            - total_pnl (float): Total profit/loss in USD
            - roi (float): Return on investment percentage
            - last_trade_date (str, optional): ISO timestamp of last trade
    
    Returns:
        Score 0-100 (clamped)
    
    Raises:
        No exceptions; returns 0 on invalid input
    """
    try:
        win_rate = float(stats.get('win_rate') or 0)
        total_pnl = float(stats.get('total_pnl') or 1)
        roi = float(stats.get('roi') or 0)
        last_trade_date = stats.get('last_trade_date')
        
        # Clamp win_rate to 0-1
        win_rate = max(0, min(1, win_rate))
        
        # Calculate recency bonus
        recency = _calculate_recency_bonus(last_trade_date)
        
        # Calculate component scores
        # ROI is typically 50-200%, we scale it to 0-20 points
        roi_scaled = (roi / 500.0) * 20  # Normalize: 500% ROI = 20 points
        roi_score = max(0, min(20, roi_scaled))
        
        # Log PnL: log(1) = 0, log(100k) = 11.5
        # We want 0-20 points from this
        pnl_score = max(0, min(20, math.log(max(1, total_pnl)) * 2.5))
        
        win_score = win_rate * 40
        recency_score = recency * 20
        
        # Total score (0-100)
        total_score = win_score + pnl_score + roi_score + recency_score
        final_score = max(0, min(100, total_score))
        
        return final_score
    
    except (TypeError, ValueError) as e:
        logger.warning(f"Error calculating wallet score: {e}")
        return 0.0


def _calculate_recency_bonus(last_trade_date: str | None) -> float:
    """Calculate recency bonus based on last trade date.
    
    Args:
        last_trade_date: ISO timestamp string of last trade, or None
    
    Returns:
        Bonus factor (0.0-1.0):
            1.0 if < 7 days ago
            0.5 if 7-30 days ago
            0.0 if > 30 days or unknown
    """
    if not last_trade_date:
        return 0.0
    
    try:
        # Parse ISO timestamp
        if isinstance(last_trade_date, str):
            # Handle both with/without Z suffix
            last_trade_date = last_trade_date.rstrip('Z')
            if '.' in last_trade_date:
                last_trade_dt = datetime.fromisoformat(last_trade_date.split('.')[0])
            else:
                last_trade_dt = datetime.fromisoformat(last_trade_date)
        else:
            last_trade_dt = last_trade_date
        
        # Ensure timezone awareness
        if last_trade_dt.tzinfo is None:
            last_trade_dt = last_trade_dt.replace(tzinfo=timezone.utc)
        
        # Calculate days since last trade
        now = datetime.now(timezone.utc)
        days_ago = (now - last_trade_dt).days
        
        if days_ago < 7:
            return 1.0
        elif days_ago < 30:
            return 0.5
        else:
            return 0.0
    
    except Exception as e:
        logger.debug(f"Error parsing last_trade_date: {e}")
        return 0.0


def validate_wallet_for_tracking(
    stats: dict[str, Any],
    min_win_rate: float = 0.60,
    min_pnl: float = 5000,
    min_trades: int = 25,
    min_avg_position: float = 200,
    min_volume_30d: float = 2000,
) -> tuple[bool, str]:
    """Validate wallet against minimum thresholds.
    
    Args:
        stats: Wallet stats dict
        min_win_rate: Minimum win rate (0-1)
        min_pnl: Minimum total PnL in USD
        min_trades: Minimum trade count
        min_avg_position: Minimum average position size USD
        min_volume_30d: Minimum 30-day volume USD
    
    Returns:
        (is_valid, reason) tuple
    """
    win_rate = float(stats.get('win_rate', 0))
    if win_rate < min_win_rate:
        return False, f"Win rate {win_rate:.1%} < {min_win_rate:.1%}"
    
    total_pnl = float(stats.get('total_pnl', 0))
    if total_pnl < min_pnl:
        return False, f"Total PnL ${total_pnl:,.0f} < ${min_pnl:,.0f}"
    
    total_trades = int(stats.get('total_trades', 0))
    if total_trades < min_trades:
        return False, f"Trades {total_trades} < {min_trades}"
    
    avg_position = float(stats.get('avg_position', 0))
    if avg_position < min_avg_position:
        return False, f"Avg position ${avg_position:,.0f} < ${min_avg_position:,.0f}"
    
    volume_30d = float(stats.get('volume_30d', 0))
    if volume_30d < min_volume_30d:
        return False, f"30d volume ${volume_30d:,.0f} < ${min_volume_30d:,.0f}"
    
    return True, "All thresholds passed"
