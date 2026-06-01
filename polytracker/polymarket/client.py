"""Async HTTP client for Polymarket API."""

import asyncio
import httpx
from typing import Any, Optional
from loguru import logger


class PolymarketClient:
    """Async Polymarket API client with rate limiting and retry logic."""
    
    def __init__(self, config):
        """Initialize the client.
        
        Args:
            config: PolymarketConfig object with API settings
        """
        self.config = config
        self.data_api_base = config.data_api_base
        self.gamma_api_base = config.gamma_api_base
        self.clob_api_base = config.clob_api_base
        
        # Rate limiting semaphore
        self.rate_limiter = asyncio.Semaphore(config.max_requests_per_second)
        
        # HTTP client (will be initialized in async context)
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                timeout=30,
                connect=self.config.http_timeout_connect,
                read=self.config.http_timeout_read,
                write=10,
                pool=10,
            ),
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
            ),
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    async def _request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> dict[str, Any]:
        """Make an HTTP request with rate limiting and retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL to request
            **kwargs: Additional arguments to pass to httpx
        
        Returns:
            Response JSON as dict
        
        Raises:
            httpx.HTTPError: On HTTP errors after retries exhausted
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        for attempt in range(self.config.max_retries):
            try:
                async with self.rate_limiter:
                    response = await self.client.request(method, url, **kwargs)
                    response.raise_for_status()
                    return response.json()
            
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limited
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Rate limited. Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    continue
                elif e.response.status_code >= 500:  # Server error
                    if attempt < self.config.max_retries - 1:
                        wait_time = (self.config.retry_backoff_factor ** attempt)
                        logger.warning(f"Server error {e.response.status_code}. Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                raise
            
            except httpx.RequestError as e:
                if attempt < self.config.max_retries - 1:
                    wait_time = (self.config.retry_backoff_factor ** attempt)
                    logger.warning(f"Request error: {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                raise
        
        raise RuntimeError(f"Failed after {self.config.max_retries} retries: {url}")
    
    # ============================================
    # DATA API ENDPOINTS (Leaderboard, Trades, Positions)
    # ============================================
    
    async def get_trader_leaderboard(
        self,
        category: str = "OVERALL",
        time_period: str = "MONTH",
        order_by: str = "PNL",
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get trader leaderboard.
        
        Args:
            category: Market category (OVERALL, POLITICS, SPORTS, CRYPTO, etc.)
            time_period: Time period (DAY, WEEK, MONTH, ALL)
            order_by: Sort by (PNL or VOL)
            limit: Max results (1-50, default 25)
            offset: Pagination offset
        
        Returns:
            List of trader entries with rank, address, pnl, vol, etc.
        """
        url = f"{self.data_api_base}/v1/leaderboard"
        params = {
            "category": category,
            "timePeriod": time_period,
            "orderBy": order_by,
            "limit": min(limit, 50),  # API max is 50
            "offset": offset,
        }
        result = await self._request("GET", url, params=params)
        return result if isinstance(result, list) else []
    
    async def get_wallet_stats(self, wallet_address: str) -> dict[str, Any]:
        """Get wallet public profile stats.
        
        Args:
            wallet_address: User's wallet address (0x...)
        
        Returns:
            Dict with pnl, win_rate, vol, trades, etc.
        """
        url = f"{self.data_api_base}/v1/profiles/{wallet_address}/public-profile"
        try:
            return await self._request("GET", url)
        except Exception as e:
            logger.error(f"Failed to fetch stats for {wallet_address}: {e}")
            return {}
    
    async def get_wallet_positions(self, wallet_address: str) -> list[dict[str, Any]]:
        """Get wallet's current open positions.
        
        Args:
            wallet_address: User's wallet address (0x...)
        
        Returns:
            List of open position records
        """
        url = f"{self.data_api_base}/v1/user/{wallet_address}/positions"
        try:
            result = await self._request("GET", url)
            return result if isinstance(result, list) else result.get("positions", [])
        except Exception as e:
            logger.error(f"Failed to fetch positions for {wallet_address}: {e}")
            return []
    
    async def get_wallet_trades(
        self,
        wallet_address: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get wallet's recent trades.
        
        Args:
            wallet_address: User's wallet address (0x...)
            limit: Max results to return
            offset: Pagination offset
        
        Returns:
            List of trade records
        """
        url = f"{self.data_api_base}/v1/user/{wallet_address}/trades"
        params = {"limit": limit, "offset": offset}
        try:
            result = await self._request("GET", url, params=params)
            return result if isinstance(result, list) else result.get("trades", [])
        except Exception as e:
            logger.error(f"Failed to fetch trades for {wallet_address}: {e}")
            return []
    
    async def get_wallet_activity(self, wallet_address: str) -> list[dict[str, Any]]:
        """Get wallet's recent activity.
        
        Args:
            wallet_address: User's wallet address (0x...)
        
        Returns:
            List of activity records
        """
        url = f"{self.data_api_base}/v1/user/{wallet_address}/activity"
        try:
            result = await self._request("GET", url)
            return result if isinstance(result, list) else result.get("activity", [])
        except Exception as e:
            logger.error(f"Failed to fetch activity for {wallet_address}: {e}")
            return []
    
    # ============================================
    # GAMMA API ENDPOINTS (Markets, Profiles)
    # ============================================
    
    async def get_market_by_slug(self, slug: str) -> dict[str, Any]:
        """Get market details by slug.
        
        Args:
            slug: Market slug (URL-friendly identifier)
        
        Returns:
            Market object with title, liquidity, closes_at, etc.
        """
        url = f"{self.gamma_api_base}/v1/markets/{slug}"
        try:
            return await self._request("GET", url)
        except Exception as e:
            logger.error(f"Failed to fetch market {slug}: {e}")
            return {}
    
    async def get_market_by_id(self, market_id: str) -> dict[str, Any]:
        """Get market details by ID.
        
        Args:
            market_id: Market condition ID
        
        Returns:
            Market object with title, liquidity, closes_at, etc.
        """
        url = f"{self.gamma_api_base}/v1/conditions/{market_id}"
        try:
            return await self._request("GET", url)
        except Exception as e:
            logger.error(f"Failed to fetch market {market_id}: {e}")
            return {}
    
    # ============================================
    # CLOB API ENDPOINTS (Prices, Orderbook)
    # ============================================
    
    async def get_midpoint_price(self, token_id: str) -> Optional[float]:
        """Get current midpoint price for a token.
        
        Args:
            token_id: Token ID
        
        Returns:
            Midpoint price as float, or None if unavailable
        """
        url = f"{self.clob_api_base}/v1/prices/midpoint"
        params = {"token_id": token_id}
        try:
            result = await self._request("GET", url, params=params)
            return result.get("midpoint")
        except Exception as e:
            logger.error(f"Failed to fetch midpoint for {token_id}: {e}")
            return None
    
    async def get_market_liquidity(self, token_id: str) -> Optional[float]:
        """Get total liquidity for a market token.
        
        Args:
            token_id: Token ID
        
        Returns:
            Liquidity in USD, or None if unavailable
        """
        url = f"{self.clob_api_base}/v1/orderbook"
        params = {"token_id": token_id}
        try:
            result = await self._request("GET", url, params=params)
            # Parse bid/ask total to get liquidity estimate
            bids = result.get("bids", [])
            asks = result.get("asks", [])
            bid_liquidity = sum(float(b.get("size", 0)) for b in bids)
            ask_liquidity = sum(float(a.get("size", 0)) for a in asks)
            return bid_liquidity + ask_liquidity
        except Exception as e:
            logger.error(f"Failed to fetch liquidity for {token_id}: {e}")
            return None

    # ============================================
    # CLOB TRADE EXECUTION (Phase 2)
    # ============================================

    async def place_market_order(
        self,
        token_id: str,
        size_usd: float,
        side: str = "BUY",  # BUY or SELL
    ) -> Optional[dict[str, Any]]:
        """Place a market order on Polymarket CLOB.

        Args:
            token_id: Token ID to trade
            size_usd: Size in USD
            side: BUY or SELL

        Returns:
            Order result dict with order_id, avg_price, amount_filled, etc.
                or None if failed
        """
        url = f"{self.clob_api_base}/v1/orders"
        payload = {
            "token_id": token_id,
            "order_type": "MARKET",
            "side": side,
            "size": size_usd,
        }

        try:
            result = await self._request("POST", url, json=payload)
            logger.info(f"Order placed: {result.get('order_id')} | {side} {size_usd} {token_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to place market order: {e}")
            return None

    async def place_limit_order(
        self,
        token_id: str,
        size_usd: float,
        price: float,
        side: str = "BUY",
    ) -> Optional[dict[str, Any]]:
        """Place a limit order on Polymarket CLOB.

        Args:
            token_id: Token ID to trade
            size_usd: Size in USD
            price: Limit price (0-1)
            side: BUY or SELL

        Returns:
            Order result dict or None
        """
        url = f"{self.clob_api_base}/v1/orders"
        payload = {
            "token_id": token_id,
            "order_type": "LIMIT",
            "side": side,
            "size": size_usd,
            "price": price,
        }

        try:
            result = await self._request("POST", url, json=payload)
            logger.info(f"Limit order placed: {result.get('order_id')}")
            return result
        except Exception as e:
            logger.error(f"Failed to place limit order: {e}")
            return None

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if successful, False otherwise
        """
        url = f"{self.clob_api_base}/v1/orders/{order_id}"

        try:
            result = await self._request("DELETE", url)
            logger.info(f"Order cancelled: {order_id}")
            return result.get("success", False)
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    async def get_order_status(self, order_id: str) -> Optional[dict[str, Any]]:
        """Get status of an order.

        Args:
            order_id: Order ID

        Returns:
            Order status dict with status, filled_amount, avg_price, etc.
        """
        url = f"{self.clob_api_base}/v1/orders/{order_id}"

        try:
            return await self._request("GET", url)
        except Exception as e:
            logger.error(f"Failed to get order status {order_id}: {e}")
            return None

    async def get_open_orders(self, wallet_address: str) -> list[dict[str, Any]]:
        """Get all open orders for a wallet.

        Args:
            wallet_address: Wallet address

        Returns:
            List of open order dicts
        """
        url = f"{self.clob_api_base}/v1/orders"
        params = {"wallet": wallet_address, "status": "open"}

        try:
            result = await self._request("GET", url, params=params)
            return result if isinstance(result, list) else result.get("orders", [])
        except Exception as e:
            logger.error(f"Failed to fetch open orders for {wallet_address}: {e}")
            return []
