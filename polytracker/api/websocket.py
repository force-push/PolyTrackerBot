"""WebSocket server for dashboard real-time updates."""

import asyncio
import json
from datetime import datetime, timezone
from typing import Set
from loguru import logger

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
except ImportError:
    logger.warning("websockets not installed. Run: pip install websockets")
    websockets = None


class DashboardWebSocketServer:
    """WebSocket server for broadcasting trading updates to dashboard."""

    def __init__(self, host: str = "localhost", port: int = 8000):
        """Initialize WebSocket server.

        Args:
            host: Server host
            port: Server port
        """
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.logger = logger

    async def start(self):
        """Start WebSocket server."""
        if not websockets:
            self.logger.error("websockets package required. Install with: pip install websockets")
            return

        async with websockets.serve(self.handle_client, self.host, self.port):
            self.logger.info(f"✅ WebSocket server running on ws://{self.host}:{self.port}")
            await asyncio.Future()  # run forever

    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket client connection.

        Args:
            websocket: Client connection
            path: Connection path
        """
        self.clients.add(websocket)
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self.logger.info(f"✅ Client connected: {client_id}")

        try:
            # Send initial connection confirmation
            await websocket.send(
                json.dumps({
                    "type": "connected",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message": "Connected to PolyTracker dashboard",
                })
            )

            # Listen for client messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(websocket, data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({"error": "Invalid JSON"}))

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            self.logger.info(f"❌ Client disconnected: {client_id}")

    async def handle_message(self, websocket: WebSocketServerProtocol, message: dict):
        """Handle message from client.

        Args:
            websocket: Client connection
            message: Message data
        """
        msg_type = message.get("type")

        if msg_type == "ping":
            await websocket.send(json.dumps({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()}))

        elif msg_type == "subscribe":
            channels = message.get("channels", [])
            self.logger.info(f"Client subscribed to: {channels}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients.

        Args:
            message: Message data (will be JSON serialized)
        """
        if not self.clients:
            return

        message["timestamp"] = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(message)

        # Send to all clients concurrently
        await asyncio.gather(
            *[client.send(payload) for client in self.clients],
            return_exceptions=True,
        )

    async def broadcast_signal(self, signal: dict):
        """Broadcast new whale signal.

        Args:
            signal: Signal data
        """
        await self.broadcast({"type": "signal", "data": signal})

    async def broadcast_order(self, order: dict):
        """Broadcast order update.

        Args:
            order: Order data
        """
        await self.broadcast({"type": "order", "data": order})

    async def broadcast_position(self, position: dict):
        """Broadcast position update.

        Args:
            position: Position data
        """
        await self.broadcast({"type": "position", "data": position})

    async def broadcast_risk_event(self, event: dict):
        """Broadcast risk event.

        Args:
            event: Risk event data
        """
        await self.broadcast({"type": "risk_event", "data": event})

    async def broadcast_stats(self, stats: dict):
        """Broadcast execution stats update.

        Args:
            stats: Stats data
        """
        await self.broadcast({"type": "stats", "data": stats})

    async def broadcast_config(self, config: dict):
        """Broadcast configuration update.

        Args:
            config: Config data
        """
        await self.broadcast({"type": "config", "data": config})


# Global WebSocket server instance
_ws_server: DashboardWebSocketServer | None = None


def get_websocket_server(host: str = "localhost", port: int = 8000) -> DashboardWebSocketServer:
    """Get or create WebSocket server instance.

    Args:
        host: Server host
        port: Server port

    Returns:
        WebSocket server instance
    """
    global _ws_server
    if _ws_server is None:
        _ws_server = DashboardWebSocketServer(host, port)
    return _ws_server


async def broadcast_signal(signal: dict):
    """Broadcast signal to all dashboard clients."""
    server = get_websocket_server()
    await server.broadcast_signal(signal)


async def broadcast_order(order: dict):
    """Broadcast order to all dashboard clients."""
    server = get_websocket_server()
    await server.broadcast_order(order)


async def broadcast_position(position: dict):
    """Broadcast position to all dashboard clients."""
    server = get_websocket_server()
    await server.broadcast_position(position)


async def broadcast_risk_event(event: dict):
    """Broadcast risk event to all dashboard clients."""
    server = get_websocket_server()
    await server.broadcast_risk_event(event)


async def broadcast_stats(stats: dict):
    """Broadcast stats to all dashboard clients."""
    server = get_websocket_server()
    await server.broadcast_stats(stats)


async def broadcast_config(config: dict):
    """Broadcast config to all dashboard clients."""
    server = get_websocket_server()
    await server.broadcast_config(config)
