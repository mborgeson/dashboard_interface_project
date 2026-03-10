"""
WebSocket connection manager/pool for real-time updates.

Provides channel-based connection pooling for:
- Deal stage changes ("deals")
- Extraction progress ("extraction")
- Notifications ("notifications")

Features:
- Named channels (rooms) for topic-based subscriptions
- Per-client connection limits to prevent resource exhaustion
- Broadcast to all connections in a channel
- Send to specific connection or user
- Connection lifecycle management with heartbeat/ping-pong
- Graceful cleanup on disconnect
"""

import asyncio
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from fastapi import WebSocket
from loguru import logger

from app.core.config import settings


class Channel(StrEnum):
    """Well-known WebSocket channels."""

    DEALS = "deals"
    EXTRACTION = "extraction"
    NOTIFICATIONS = "notifications"
    PROPERTIES = "properties"
    ANALYTICS = "analytics"


class ConnectionManager:
    """
    WebSocket connection manager that tracks active connections
    and supports named channels/rooms for topic-based messaging.

    Thread-safe for use with asyncio (single event loop).
    """

    # Default max connections per client (user_id)
    DEFAULT_MAX_CONNECTIONS_PER_CLIENT: int = 5

    def __init__(
        self,
        max_connections_per_client: int | None = None,
    ) -> None:
        # Active connections: {connection_id: WebSocket}
        self._connections: dict[str, WebSocket] = {}
        # User connections: {user_id: set[connection_id]}
        self._user_connections: dict[int, set[str]] = {}
        # Channel subscriptions: {channel: set[connection_id]}
        self._channels: dict[str, set[str]] = {}
        # Connection metadata: {connection_id: metadata}
        self._metadata: dict[str, dict[str, Any]] = {}
        # Heartbeat tasks: {connection_id: Task}
        self._heartbeat_tasks: dict[str, asyncio.Task[None]] = {}
        # Per-client limit
        self._max_connections_per_client = (
            max_connections_per_client or self.DEFAULT_MAX_CONNECTIONS_PER_CLIENT
        )

    @property
    def connection_count(self) -> int:
        """Get total number of active connections."""
        return len(self._connections)

    @property
    def channel_counts(self) -> dict[str, int]:
        """Get connection count per channel."""
        return {ch: len(conns) for ch, conns in self._channels.items()}

    def get_user_connection_count(self, user_id: int) -> int:
        """Get the number of active connections for a user."""
        return len(self._user_connections.get(user_id, set()))

    def _generate_connection_id(self, user_id: int | None = None) -> str:
        """Generate a unique connection ID."""
        short_id = uuid.uuid4().hex[:8]
        if user_id is not None:
            return f"user_{user_id}_{short_id}"
        return f"anon_{short_id}"

    # ==================== Connection Lifecycle ====================

    async def connect(
        self,
        websocket: WebSocket,
        user_id: int | None = None,
        channels: list[str] | None = None,
    ) -> str:
        """
        Accept and register a WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance.
            user_id: Optional authenticated user ID.
            channels: Optional list of channels to subscribe to on connect.

        Returns:
            Connection ID assigned to this connection.

        Raises:
            ValueError: If global connection limit or per-client limit is exceeded.
        """
        # Enforce global limit
        if self.connection_count >= settings.WS_MAX_CONNECTIONS:
            raise ValueError(
                f"Global connection limit reached ({settings.WS_MAX_CONNECTIONS})"
            )

        # Enforce per-client limit
        if user_id is not None:
            current = self.get_user_connection_count(user_id)
            if current >= self._max_connections_per_client:
                raise ValueError(
                    f"Per-client connection limit reached "
                    f"({self._max_connections_per_client}) for user {user_id}"
                )

        await websocket.accept()

        connection_id = self._generate_connection_id(user_id)
        self._connections[connection_id] = websocket
        self._metadata[connection_id] = {
            "user_id": user_id,
            "connected_at": datetime.now(UTC).isoformat(),
            "channels": list(channels or []),
            "last_heartbeat": datetime.now(UTC).isoformat(),
        }

        # Track user connections
        if user_id is not None:
            if user_id not in self._user_connections:
                self._user_connections[user_id] = set()
            self._user_connections[user_id].add(connection_id)

        # Subscribe to channels
        if channels:
            for channel in channels:
                self._add_to_channel(connection_id, channel)

        # Start heartbeat
        self._heartbeat_tasks[connection_id] = asyncio.create_task(
            self._heartbeat_loop(connection_id)
        )

        logger.info(
            f"WebSocket connected: {connection_id} "
            f"(user={user_id}, channels={channels})"
        )

        # Send welcome message with connection info
        await self._send_json(
            connection_id,
            {
                "type": "connected",
                "connection_id": connection_id,
                "channels": list(channels or []),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

        return connection_id

    async def disconnect(self, connection_id: str) -> None:
        """
        Disconnect and clean up a WebSocket connection.

        Idempotent: safe to call multiple times or with unknown connection IDs.
        """
        if connection_id not in self._connections:
            return

        # Cancel heartbeat
        task = self._heartbeat_tasks.pop(connection_id, None)
        if task is not None:
            task.cancel()

        # Get metadata before cleanup
        metadata = self._metadata.get(connection_id, {})
        user_id = metadata.get("user_id")

        # Remove from user connections
        if user_id is not None and user_id in self._user_connections:
            self._user_connections[user_id].discard(connection_id)
            if not self._user_connections[user_id]:
                del self._user_connections[user_id]

        # Remove from all channels
        for channel in list(self._channels.keys()):
            self._channels[channel].discard(connection_id)
            if not self._channels[channel]:
                del self._channels[channel]

        # Close WebSocket
        try:
            ws = self._connections[connection_id]
            await ws.close()
        except Exception:
            pass  # Connection may already be closed

        # Clean up maps
        self._connections.pop(connection_id, None)
        self._metadata.pop(connection_id, None)

        logger.info(f"WebSocket disconnected: {connection_id}")

    # ==================== Channel Management ====================

    def _add_to_channel(self, connection_id: str, channel: str) -> None:
        """Add a connection to a channel (internal, no message sent)."""
        if channel not in self._channels:
            self._channels[channel] = set()
        self._channels[channel].add(connection_id)

    async def subscribe(self, connection_id: str, channel: str) -> None:
        """Subscribe a connection to a channel."""
        self._add_to_channel(connection_id, channel)

        # Update metadata
        if connection_id in self._metadata:
            channels = self._metadata[connection_id].get("channels", [])
            if channel not in channels:
                channels.append(channel)

        logger.debug(f"Connection {connection_id} subscribed to {channel}")

    async def unsubscribe(self, connection_id: str, channel: str) -> None:
        """Unsubscribe a connection from a channel."""
        if channel in self._channels:
            self._channels[channel].discard(connection_id)
            if not self._channels[channel]:
                del self._channels[channel]

        if connection_id in self._metadata:
            channels = self._metadata[connection_id].get("channels", [])
            if channel in channels:
                channels.remove(channel)

        logger.debug(f"Connection {connection_id} unsubscribed from {channel}")

    # ==================== Message Sending ====================

    async def _send_json(self, connection_id: str, message: dict) -> bool:
        """Send a JSON message to a specific connection. Returns True on success."""
        ws = self._connections.get(connection_id)
        if ws is None:
            return False
        try:
            await ws.send_json(message)
            return True
        except Exception as e:
            logger.warning(f"Send failed for {connection_id}: {e}")
            await self.disconnect(connection_id)
            return False

    async def send_to_connection(self, connection_id: str, message: dict) -> bool:
        """Send a message to a specific connection by ID."""
        return await self._send_json(connection_id, message)

    async def send_to_user(self, user_id: int, message: dict) -> int:
        """Send a message to all connections belonging to a user. Returns send count."""
        sent = 0
        conn_ids = self._user_connections.get(user_id, set()).copy()
        for cid in conn_ids:
            if await self._send_json(cid, message):
                sent += 1
        return sent

    async def send_to_channel(
        self,
        channel: str,
        message: dict,
        exclude: str | None = None,
    ) -> int:
        """Broadcast a message to all connections in a channel. Returns send count."""
        sent = 0
        conn_ids = self._channels.get(channel, set()).copy()
        for cid in conn_ids:
            if cid != exclude and await self._send_json(cid, message):
                sent += 1
        return sent

    async def broadcast(self, message: dict, exclude: str | None = None) -> int:
        """Broadcast a message to every active connection. Returns send count."""
        sent = 0
        for cid in list(self._connections.keys()):
            if cid != exclude and await self._send_json(cid, message):
                sent += 1
        return sent

    # ==================== Heartbeat ====================

    async def _heartbeat_loop(self, connection_id: str) -> None:
        """Periodically send ping/heartbeat to keep the connection alive."""
        try:
            while connection_id in self._connections:
                await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
                if connection_id not in self._connections:
                    break
                success = await self._send_json(
                    connection_id,
                    {
                        "type": "ping",
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )
                if not success:
                    break
                # Record heartbeat time
                if connection_id in self._metadata:
                    self._metadata[connection_id]["last_heartbeat"] = datetime.now(
                        UTC
                    ).isoformat()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Heartbeat ended for {connection_id}: {e}")

    async def handle_pong(self, connection_id: str) -> None:
        """Record that a pong was received from the client."""
        if connection_id in self._metadata:
            self._metadata[connection_id]["last_pong"] = datetime.now(UTC).isoformat()

    # ==================== Event Helpers ====================

    async def notify_deal_update(
        self,
        deal_id: int,
        action: str,
        data: dict,
        user_id: int | None = None,
    ) -> None:
        """Notify deal channel about a deal change."""
        await self.send_to_channel(
            Channel.DEALS,
            {
                "type": "deal_update",
                "action": action,
                "deal_id": deal_id,
                "data": data,
                "triggered_by": user_id,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    async def notify_extraction_progress(
        self,
        extraction_id: str,
        status: str,
        progress: float,
        detail: str | None = None,
    ) -> None:
        """Notify extraction channel about progress updates."""
        await self.send_to_channel(
            Channel.EXTRACTION,
            {
                "type": "extraction_progress",
                "extraction_id": extraction_id,
                "status": status,
                "progress": progress,
                "detail": detail,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    async def notify_user(
        self,
        user_id: int,
        title: str,
        body: str,
        level: str = "info",
        data: dict | None = None,
    ) -> None:
        """Send a notification to a specific user."""
        await self.send_to_user(
            user_id,
            {
                "type": "notification",
                "title": title,
                "body": body,
                "level": level,
                "data": data or {},
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    async def notify_property_update(
        self,
        property_id: int,
        action: str,
        data: dict,
    ) -> None:
        """Notify properties channel about a property change."""
        await self.send_to_channel(
            Channel.PROPERTIES,
            {
                "type": "property_update",
                "action": action,
                "property_id": property_id,
                "data": data,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )


# ==================== Singleton ====================

_manager: ConnectionManager | None = None


def get_connection_manager() -> ConnectionManager:
    """Get or create the global ConnectionManager singleton."""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager
