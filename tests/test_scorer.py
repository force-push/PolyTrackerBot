"""Unit tests for wallet scoring logic."""

import pytest
import math
from datetime import datetime, timezone, timedelta

from polytracker.signals.scorer import (
    calculate_wallet_score,
    validate_wallet_for_tracking,
    _calculate_recency_bonus,
)


class TestCalculateWalletScore:
    """Tests for calculate_wallet_score function."""
    
    def test_perfect_wallet(self):
        """Test scoring for a perfect wallet."""
        stats = {
            'win_rate': 1.0,
            'total_pnl': 100000,
            'roi': 500.0,
            'last_trade_date': datetime.now(timezone.utc).isoformat(),
        }
        score = calculate_wallet_score(stats)
        assert 95 <= score <= 100  # Should be very high
    
    def test_minimum_qualifying_wallet(self):
        """Test scoring for wallet at minimum thresholds."""
        stats = {
            'win_rate': 0.60,
            'total_pnl': 5000,
            'roi': 50.0,
            'last_trade_date': datetime.now(timezone.utc).isoformat(),
        }
        score = calculate_wallet_score(stats)
        assert 40 <= score <= 70  # Should be moderate
    
    def test_poor_wallet(self):
        """Test scoring for poor-performing wallet."""
        stats = {
            'win_rate': 0.45,
            'total_pnl': 1000,
            'roi': 10.0,
            'last_trade_date': None,
        }
        score = calculate_wallet_score(stats)
        assert 0 <= score <= 40  # Should be low
    
    def test_handles_missing_fields(self):
        """Test scoring with missing fields."""
        stats = {}
        score = calculate_wallet_score(stats)
        assert score == 0.0  # Should not crash
    
    def test_handles_none_pnl(self):
        """Test scoring with None total_pnl."""
        stats = {
            'win_rate': 0.70,
            'total_pnl': None,
            'roi': 100.0,
        }
        score = calculate_wallet_score(stats)
        assert 20 <= score <= 50  # Should handle gracefully with no recent bonus
    
    def test_handles_zero_pnl(self):
        """Test scoring with zero PnL (log(0) edge case)."""
        stats = {
            'win_rate': 0.70,
            'total_pnl': 0,
            'roi': 100.0,
        }
        score = calculate_wallet_score(stats)
        assert score >= 0  # Should not crash
    
    def test_clamps_to_100(self):
        """Test that score never exceeds 100."""
        stats = {
            'win_rate': 2.0,  # Invalid, should be clamped
            'total_pnl': 1000000000,
            'roi': 10000.0,
        }
        score = calculate_wallet_score(stats)
        assert score <= 100
    
    def test_recency_bonus_active(self):
        """Test scoring with recent trade (recent bonus)."""
        now = datetime.now(timezone.utc)
        stats = {
            'win_rate': 0.70,
            'total_pnl': 10000,
            'roi': 100.0,
            'last_trade_date': now.isoformat(),
        }
        score_recent = calculate_wallet_score(stats)
        
        # Repeat with old trade (no bonus)
        old_date = (now - timedelta(days=60)).isoformat()
        stats['last_trade_date'] = old_date
        score_old = calculate_wallet_score(stats)
        
        # Recency bonus is 20 points max
        assert (score_recent - score_old) >= 10  # Significant difference
    
    def test_win_rate_component(self):
        """Test that win_rate is weighted correctly (40 points max)."""
        stats_base = {
            'total_pnl': 10000,
            'roi': 100.0,
            'last_trade_date': None,
        }
        
        stats_high_wr = {**stats_base, 'win_rate': 0.95}
        stats_low_wr = {**stats_base, 'win_rate': 0.50}
        
        score_high = calculate_wallet_score(stats_high_wr)
        score_low = calculate_wallet_score(stats_low_wr)
        
        # High win rate should score higher
        assert score_high > score_low
        # Difference should be roughly 40 * (0.95 - 0.50) = 18
        assert 10 <= (score_high - score_low) <= 30
    
    def test_pnl_logarithmic_scaling(self):
        """Test that PnL uses logarithmic scaling."""
        stats_base = {
            'win_rate': 0.70,
            'roi': 100.0,
            'last_trade_date': None,
        }
        
        # Score with $1k PnL
        stats_1k = {**stats_base, 'total_pnl': 1000}
        score_1k = calculate_wallet_score(stats_1k)
        
        # Score with $100k PnL (100x more)
        stats_100k = {**stats_base, 'total_pnl': 100000}
        score_100k = calculate_wallet_score(stats_100k)
        
        # With log scaling, higher PnL should give higher score
        assert score_100k > score_1k
        assert 2.5 <= (score_100k - score_1k) <= 10


class TestCalculateRecencyBonus:
    """Tests for _calculate_recency_bonus function."""
    
    def test_recent_trade_full_bonus(self):
        """Test full bonus for trade < 7 days old."""
        now = datetime.now(timezone.utc)
        recent = (now - timedelta(days=3)).isoformat()
        bonus = _calculate_recency_bonus(recent)
        assert bonus == 1.0
    
    def test_medium_trade_half_bonus(self):
        """Test half bonus for trade 7-30 days old."""
        now = datetime.now(timezone.utc)
        medium = (now - timedelta(days=15)).isoformat()
        bonus = _calculate_recency_bonus(medium)
        assert bonus == 0.5
    
    def test_old_trade_no_bonus(self):
        """Test no bonus for trade > 30 days old."""
        now = datetime.now(timezone.utc)
        old = (now - timedelta(days=60)).isoformat()
        bonus = _calculate_recency_bonus(old)
        assert bonus == 0.0
    
    def test_none_date_returns_zero(self):
        """Test that None date returns 0 bonus."""
        bonus = _calculate_recency_bonus(None)
        assert bonus == 0.0
    
    def test_invalid_date_returns_zero(self):
        """Test that invalid date returns 0 bonus."""
        bonus = _calculate_recency_bonus("invalid-date")
        assert bonus == 0.0
    
    def test_handles_z_suffix(self):
        """Test parsing ISO timestamps with Z suffix."""
        now = datetime.now(timezone.utc)
        recent = (now - timedelta(days=1)).isoformat() + 'Z'
        bonus = _calculate_recency_bonus(recent)
        assert bonus == 1.0


class TestValidateWalletForTracking:
    """Tests for validate_wallet_for_tracking function."""
    
    def test_qualifies_wallet(self):
        """Test wallet that meets all thresholds."""
        stats = {
            'win_rate': 0.75,
            'total_pnl': 25000,
            'total_trades': 50,
            'avg_position': 500,
            'volume_30d': 5000,
        }
        is_valid, reason = validate_wallet_for_tracking(stats)
        assert is_valid is True
        assert "passed" in reason.lower()
    
    def test_fails_low_win_rate(self):
        """Test rejection for low win rate."""
        stats = {
            'win_rate': 0.45,  # Below 0.60 threshold
            'total_pnl': 25000,
            'total_trades': 50,
            'avg_position': 500,
            'volume_30d': 5000,
        }
        is_valid, reason = validate_wallet_for_tracking(stats)
        assert is_valid is False
        assert "win rate" in reason.lower()
    
    def test_fails_low_pnl(self):
        """Test rejection for low total PnL."""
        stats = {
            'win_rate': 0.75,
            'total_pnl': 1000,  # Below $5000 threshold
            'total_trades': 50,
            'avg_position': 500,
            'volume_30d': 5000,
        }
        is_valid, reason = validate_wallet_for_tracking(stats)
        assert is_valid is False
        assert "pnl" in reason.lower()
    
    def test_fails_low_trade_count(self):
        """Test rejection for low trade count."""
        stats = {
            'win_rate': 0.75,
            'total_pnl': 25000,
            'total_trades': 10,  # Below 25 threshold
            'avg_position': 500,
            'volume_30d': 5000,
        }
        is_valid, reason = validate_wallet_for_tracking(stats)
        assert is_valid is False
        assert "trades" in reason.lower()
    
    def test_custom_thresholds(self):
        """Test with custom threshold values."""
        stats = {
            'win_rate': 0.65,
            'total_pnl': 10000,
            'total_trades': 30,
            'avg_position': 300,
            'volume_30d': 3000,
        }
        is_valid, reason = validate_wallet_for_tracking(
            stats,
            min_win_rate=0.60,
            min_pnl=8000,
            min_trades=25,
            min_avg_position=250,
            min_volume_30d=2000,
        )
        assert is_valid is True
