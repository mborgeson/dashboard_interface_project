"""
WebSocket service for real-time updates and collaboration.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket
from loguru import logger

from app.core.config import settings


class WebSocketManager:
    """
    WebSocket connection manager for real-time communication.

    Features:
    - Connection management per user/room
    - Broadcast to all or specific rooms
    - Heartbeat monitoring
    - Graceful disconnection handling
    """

    def __init__(self):
        # Active connections: {connection_id: WebSocket}
        self._connections: dict[str, WebSocket] = {}
        # User connections: {user_id: Set[connection_id]}
        self._user_connections: dict[int, set[str]] = {}
        # Room subscriptions: {room_id: Set[connection_id]}
        self._rooms: dict[str, set[str]] = {}
        # Connection metadata: {connection_id: metadata}
        self._metadata: dict[str, dict] = {}
        # Heartbeat tasks
        self._heartbeat_tasks: dict[str, asyncio.Task] = {}

    @property
    def connection_count(self) -> int:
        """Get total active connections."""
        return len(self._connections)

    def _generate_connection_id(self, user_id: int | None = None) -> str:
        """Generate unique connection ID."""
        import uuid

        base = str(uuid.uuid4())[:8]
        if user_id:
            return f"user_{user_id}_{base}"
        return f"anon_{base}"

    async def connect(
        self,
        websocket: WebSocket,
        user_id: int | None = None,
        rooms: list[str] | None = None,
    ) -> str:
        """
        Accept and register a WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
            user_id: Optional user ID for authenticated connections
            rooms: Optional list of rooms to subscribe to

        Returns:
            Connection ID
        """
        await websocket.accept()

        connection_id = self._generate_connection_id(user_id)
        self._connections[connection_id] = websocket
        self._metadata[connection_id] = {
            "user_id": user_id,
            "connected_at": datetime.now(UTC).isoformat(),
            "rooms": rooms or [],
        }

        # Track user connections
        if user_id:
            if user_id not in self._user_connections:
                self._user_connections[user_id] = set()
            self._user_connections[user_id].add(connection_id)

        # Subscribe to rooms
        if rooms:
            for room in rooms:
                await self.join_room(connection_id, room)

        # Start heartbeat
        self._heartbeat_tasks[connection_id] = asyncio.create_task(
            self._heartbeat_loop(connection_id)
        )

        logger.info(
            f"WebSocket connected: {connection_id} "
            f"(user: {user_id}, rooms: {rooms})"
        )

        return connection_id

    async def disconnect(self, connection_id: str) -> None:
        """
        Disconnect and clean up a WebSocket connection.
        """
        if connection_id not in self._connections:
            return

        # Cancel heartbeat
        if connection_id in self._heartbeat_tasks:
            self._heartbeat_tasks[connection_id].cancel()
            del self._heartbeat_tasks[connection_id]

        # Get metadata before cleanup
        metadata = self._metadata.get(connection_id, {})
        user_id = metadata.get("user_id")

        # Remove from user connections
        if user_id and user_id in self._user_connections:
            self._user_connections[user_id].discard(connection_id)
            if not self._user_connections[user_id]:
                del self._user_connections[user_id]

        # Remove from all rooms
        for room_id in list(self._rooms.keys()):
            self._rooms[room_id].discard(connection_id)
            if not self._rooms[room_id]:
                del self._rooms[room_id]

        # Close and remove connection
        try:
            websocket = self._connections[connection_id]
            await websocket.close()
        except Exception:
            pass

        del self._connections[connection_id]
        if connection_id in self._metadata:
            del self._metadata[connection_id]

        logger.info(f"WebSocket disconnected: {connection_id}")

    async def _heartbeat_loop(self, connection_id: str) -> None:
        """Send periodic heartbeats to keep connection alive."""
        try:
            while connection_id in self._connections:
                await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
                await self.send_to_connection(
                    connection_id,
                    {"type": "heartbeat", "timestamp": datetime.now(UTC).isoformat()},
                )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Heartbeat stopped for {connection_id}: {e}")

    # ==================== Room Management ====================

    async def join_room(self, connection_id: str, room_id: str) -> None:
        """Add connection to a room."""
        if room_id not in self._rooms:
            self._rooms[room_id] = set()
        self._rooms[room_id].add(connection_id)

        if connection_id in self._metadata:
            rooms = self._metadata[connection_id].get("rooms", [])
            if room_id not in rooms:
                rooms.append(room_id)

        logger.debug(f"Connection {connection_id} joined room {room_id}")

    async def leave_room(self, connection_id: str, room_id: str) -> None:
        """Remove connection from a room."""
        if room_id in self._rooms:
            self._rooms[room_id].discard(connection_id)
            if not self._rooms[room_id]:
                del self._rooms[room_id]

        if connection_id in self._metadata:
            rooms = self._metadata[connection_id].get("rooms", [])
            if room_id in rooms:
                rooms.remove(room_id)

        logger.debug(f"Connection {connection_id} left room {room_id}")

    # ==================== Message Sending ====================

    async def send_to_connection(self, connection_id: str, message: Any) -> bool:
        """Send message to specific connection."""
        if connection_id not in self._connections:
            return False

        try:
            websocket = self._connections[connection_id]
            if isinstance(message, dict):
                await websocket.send_json(message)
            else:
                await websocket.send_text(str(message))
            return True
        except Exception as e:
            logger.error(f"Failed to send to {connection_id}: {e}")
            await self.disconnect(connection_id)
            return False

    async def send_to_user(self, user_id: int, message: Any) -> int:
        """Send message to all connections for a user."""
        sent = 0
        connection_ids = self._user_connections.get(user_id, set()).copy()
        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                sent += 1
        return sent

    async def send_to_room(
        self, room_id: str, message: Any, exclude: str | None = None
    ) -> int:
        """Send message to all connections in a room."""
        sent = 0
        connection_ids = self._rooms.get(room_id, set()).copy()
        for connection_id in connection_ids:
            if connection_id != exclude and await self.send_to_connection(
                connection_id, message
            ):
                sent += 1
        return sent

    async def broadcast(self, message: Any, exclude: str | None = None) -> int:
        """Broadcast message to all connections."""
        sent = 0
        connection_ids = list(self._connections.keys())
        for connection_id in connection_ids:
            if connection_id != exclude and await self.send_to_connection(
                connection_id, message
            ):
                sent += 1
        return sent

    # ==================== Event Helpers ====================

    async def notify_deal_update(
        self, deal_id: int, action: str, data: dict, user_id: int | None = None
    ) -> None:
        """Notify about deal updates (for Kanban board)."""
        message = {
            "type": "deal_update",
            "action": action,  # created, updated, deleted, stage_changed
            "deal_id": deal_id,
            "data": data,
            "timestamp": datetime.now(UTC).isoformat(),
            "triggered_by": user_id,
        }
        await self.send_to_room("deals", message)

    async def notify_property_update(
        self, property_id: int, action: str, data: dict
    ) -> None:
        """Notify about property updates."""
        message = {
            "type": "property_update",
            "action": action,
            "property_id": property_id,
            "data": data,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        await self.send_to_room("properties", message)

    async def notify_analytics_ready(
        self, report_type: str, user_id: int, report_id: str
    ) -> None:
        """Notify user that analytics report is ready."""
        message = {
            "type": "analytics_ready",
            "report_type": report_type,
            "report_id": report_id,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        await self.send_to_user(user_id, message)


# Singleton instance
_ws_manager: WebSocketManager | None = None


def get_websocket_manager() -> WebSocketManager:
    """Get or create WebSocket manager singleton."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager
