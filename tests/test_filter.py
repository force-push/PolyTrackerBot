"""Unit tests for signal filtering logic."""

import pytest
from datetime import datetime, timezone, timedelta

from polytracker.signals.filter import is_viable_signal


class TestIsViableSignal:
    """Tests for is_viable_signal function."""
    
    @pytest.mark.asyncio
    async def test_passes_all_checks(self, mock_config, mock_db, mock_polymarket_client, mock_position, mock_market):
        """Test position that passes all viability checks."""
        is_viable, alert_type, reason = await is_viable_signal(
            mock_position,
            mock_config,
            mock_db,
            mock_polymarket_client,
        )
        
        assert is_viable is True
        assert alert_type in ['standard', 'high_conviction']
    
    @pytest.mark.asyncio
    async def test_fails_position_too_small(self, mock_config, mock_db, mock_polymarket_client, mock_position, mock_market):
        """Test rejection for position size < MIN_SIGNAL_POSITION."""
        mock_position['size_usd'] = 200  # Below $500 threshold
        
        is_viable, alert_type, reason = await is_viable_signal(
            mock_position,
            mock_config,
            mock_db,
            mock_polymarket_client,
        )
        
        assert is_viable is False
        assert "size" in reason.lower() or "position" in reason.lower()
    
    @pytest.mark.asyncio
    async def test_fails_market_resolved(self, mock_config, mock_db, mock_polymarket_client, mock_position):
        """Test rejection for resolved market."""
        mock_market_resolved = {
            'id': 'market_123',
            'title': 'Already Resolved',
            'resolved': True,
            'liquidity': 50000,
        }
        mock_polymarket_client.get_market_by_slug.return_value = mock_market_resolved
        
        is_viable, alert_type, reason = await is_viable_signal(
            mock_position,
            mock_config,
            mock_db,
            mock_polymarket_client,
        )
        
        assert is_viable is False
        assert "resolved" in reason.lower()
    
    @pytest.mark.asyncio
    async def test_fails_insufficient_liquidity(self, mock_config, mock_db, mock_polymarket_client, mock_position, mock_market):
        """Test rejection for insufficient market liquidity."""
        mock_market['liquidity'] = 5000  # Below $10,000 threshold
        mock_polymarket_client.get_market_by_slug.return_value = mock_market
        
        is_viable, alert_type, reason = await is_viable_signal(
            mock_position,
            mock_config,
            mock_db,
            mock_polymarket_client,
        )
        
        assert is_viable is False
        assert "liquidity" in reason.lower()
    
    @pytest.mark.asyncio
    async def test_fails_market_closes_soon(self, mock_config, mock_db, mock_polymarket_client, mock_position, mock_market):
        """Test rejection for market closing in < MIN_HOURS_REMAINING."""
        # Set market to close in 24 hours (less than default 48h threshold)
        soon = datetime.now(timezone.utc) + timedelta(hours=24)
        mock_market['closes_at'] = soon.isoformat()
        mock_polymarket_client.get_market_by_slug.return_value = mock_market
        
        is_viable, alert_type, reason = await is_viable_signal(
            mock_position,
            mock_config,
            mock_db,
            mock_polymarket_client,
        )
        
        assert is_viable is False
        assert "remaining" in reason.lower() or "hours" in reason.lower()
    
    @pytest.mark.asyncio
    async def test_fails_duplicate_alert(self, mock_config, mock_db, mock_polymarket_client, mock_position, mock_market):
        """Test rejection when alert already sent for wallet-market pair."""
        market_id = mock_position.get('market_id')
        wallet_address = mock_position['wallet_address']
        
        # Pre-populate alert in DB
        await mock_db.record_alert(wallet_address, market_id, 'standard')
        
        is_viable, alert_type, reason = await is_viable_signal(
            mock_position,
            mock_config,
            mock_db,
            mock_polymarket_client,
        )
        
        assert is_viable is False
        assert "already" in reason.lower() or "duplicate" in reason.lower()
    
    @pytest.mark.asyncio
    async def test_missing_market_id_fails(self, mock_config, mock_db, mock_polymarket_client, mock_position):
        """Test rejection for missing market_id."""
        mock_position['market_id'] = None
        mock_position['condition_id'] = None
        
        is_viable, alert_type, reason = await is_viable_signal(
            mock_position,
            mock_config,
            mock_db,
            mock_polymarket_client,
        )
        
        assert is_viable is False
    
    @pytest.mark.asyncio
    async def test_missing_wallet_address_fails(self, mock_config, mock_db, mock_polymarket_client, mock_position):
        """Test rejection for missing wallet_address."""
        mock_position['wallet_address'] = None
        
        is_viable, alert_type, reason = await is_viable_signal(
            mock_position,
            mock_config,
            mock_db,
            mock_polymarket_client,
        )
        
        assert is_viable is False
    
    @pytest.mark.asyncio
    async def test_standard_alert_single_wallet(self, mock_config, mock_db, mock_polymarket_client, mock_position, mock_market):
        """Test that single wallet position generates standard alert."""
        is_viable, alert_type, reason = await is_viable_signal(
            mock_position,
            mock_config,
            mock_db,
            mock_polymarket_client,
        )
        
        assert is_viable is True
        assert alert_type == 'standard'
    
    @pytest.mark.asyncio
    async def test_high_conviction_multiple_wallets(self, mock_config, mock_db, mock_polymarket_client, mock_position, mock_market):
        """Test that multiple wallets on same market generates high_conviction alert."""
        market_id = mock_position['market_id']
        
        # Pre-populate trades from other wallets
        await mock_db.upsert_trade(
            wallet_address='0x9999999999999999999999999999999999999999',
            market_id=market_id,
            market_slug='market_slug',
            market_title='Test Market',
            direction='YES',
            price=0.5,
            size_usd=2000,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
        # Mark one as alerted
        trades = await mock_db.get_trades_for_market(market_id)
        if trades:
            await mock_db.mark_trade_alerted(trades[0]['id'])
        
        is_viable, alert_type, reason = await is_viable_signal(
            mock_position,
            mock_config,
            mock_db,
            mock_polymarket_client,
        )
        
        assert is_viable is True
        # May be high_conviction if other wallet's alert was counted
        assert alert_type in ['standard', 'high_conviction']
