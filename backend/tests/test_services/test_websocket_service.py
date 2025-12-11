"""
Unit tests for the WebSocket service.

Tests WebSocketManager functionality including:
- Connection management
- Room subscriptions
- Message sending (individual, user, room, broadcast)
- Event notifications
- Heartbeat management
"""
import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from typing import Dict, Set


class TestWebSocketManager:
    """Tests for the WebSocketManager class."""

    @pytest.fixture
    def manager(self):
        """Create WebSocketManager instance."""
        from app.services.websocket_service import WebSocketManager
        return WebSocketManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()
        return ws

    # ==================== Initialization Tests ====================

    def test_manager_initialization(self, manager):
        """Test WebSocketManager initializes with empty collections."""
        assert manager._connections == {}
        assert manager._user_connections == {}
        assert manager._rooms == {}
        assert manager._metadata == {}
        assert manager._heartbeat_tasks == {}

    def test_connection_count_empty(self, manager):
        """Test connection_count returns 0 when no connections."""
        assert manager.connection_count == 0

    def test_connection_count_with_connections(self, manager, mock_websocket):
        """Test connection_count returns correct count."""
        manager._connections = {"conn1": mock_websocket, "conn2": mock_websocket}
        assert manager.connection_count == 2

    # ==================== Connection Tests ====================

    @pytest.mark.asyncio
    async def test_connect_accepts_websocket(self, manager, mock_websocket):
        """Test connect accepts the WebSocket."""
        with patch.object(manager, '_heartbeat_loop', new=AsyncMock()):
            conn_id = await manager.connect(mock_websocket)
            mock_websocket.accept.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_connect_returns_connection_id(self, manager, mock_websocket):
        """Test connect returns a connection ID."""
        with patch.object(manager, '_heartbeat_loop', new=AsyncMock()):
            conn_id = await manager.connect(mock_websocket)
            assert conn_id is not None
            assert isinstance(conn_id, str)

    @pytest.mark.asyncio
    async def test_connect_with_user_id(self, manager, mock_websocket):
        """Test connect with user_id includes user in ID."""
        with patch.object(manager, '_heartbeat_loop', new=AsyncMock()):
            conn_id = await manager.connect(mock_websocket, user_id=123)
            assert "user_123" in conn_id

    @pytest.mark.asyncio
    async def test_connect_without_user_id(self, manager, mock_websocket):
        """Test connect without user_id creates anon ID."""
        with patch.object(manager, '_heartbeat_loop', new=AsyncMock()):
            conn_id = await manager.connect(mock_websocket)
            assert "anon_" in conn_id

    @pytest.mark.asyncio
    async def test_connect_registers_connection(self, manager, mock_websocket):
        """Test connect registers the connection."""
        with patch.object(manager, '_heartbeat_loop', new=AsyncMock()):
            conn_id = await manager.connect(mock_websocket)
            assert conn_id in manager._connections
            assert manager._connections[conn_id] is mock_websocket

    @pytest.mark.asyncio
    async def test_connect_stores_metadata(self, manager, mock_websocket):
        """Test connect stores connection metadata."""
        with patch.object(manager, '_heartbeat_loop', new=AsyncMock()):
            conn_id = await manager.connect(mock_websocket, user_id=456, rooms=["deals"])

            assert conn_id in manager._metadata
            metadata = manager._metadata[conn_id]
            assert metadata["user_id"] == 456
            assert "deals" in metadata["rooms"]
            assert "connected_at" in metadata

    @pytest.mark.asyncio
    async def test_connect_tracks_user_connections(self, manager, mock_websocket):
        """Test connect tracks user connections."""
        with patch.object(manager, '_heartbeat_loop', new=AsyncMock()):
            conn_id = await manager.connect(mock_websocket, user_id=789)

            assert 789 in manager._user_connections
            assert conn_id in manager._user_connections[789]

    @pytest.mark.asyncio
    async def test_connect_subscribes_to_rooms(self, manager, mock_websocket):
        """Test connect subscribes to specified rooms."""
        with patch.object(manager, '_heartbeat_loop', new=AsyncMock()):
            conn_id = await manager.connect(mock_websocket, rooms=["room1", "room2"])

            assert "room1" in manager._rooms
            assert "room2" in manager._rooms
            assert conn_id in manager._rooms["room1"]
            assert conn_id in manager._rooms["room2"]

    # ==================== Disconnect Tests ====================

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self, manager, mock_websocket):
        """Test disconnect removes the connection."""
        conn_id = "test_conn"
        manager._connections[conn_id] = mock_websocket
        manager._metadata[conn_id] = {"user_id": None, "rooms": []}

        await manager.disconnect(conn_id)

        assert conn_id not in manager._connections

    @pytest.mark.asyncio
    async def test_disconnect_removes_metadata(self, manager, mock_websocket):
        """Test disconnect removes metadata."""
        conn_id = "test_conn"
        manager._connections[conn_id] = mock_websocket
        manager._metadata[conn_id] = {"user_id": None, "rooms": []}

        await manager.disconnect(conn_id)

        assert conn_id not in manager._metadata

    @pytest.mark.asyncio
    async def test_disconnect_removes_from_user_connections(self, manager, mock_websocket):
        """Test disconnect removes from user connections."""
        conn_id = "test_conn"
        user_id = 123
        manager._connections[conn_id] = mock_websocket
        manager._metadata[conn_id] = {"user_id": user_id, "rooms": []}
        manager._user_connections[user_id] = {conn_id}

        await manager.disconnect(conn_id)

        assert user_id not in manager._user_connections

    @pytest.mark.asyncio
    async def test_disconnect_removes_from_rooms(self, manager, mock_websocket):
        """Test disconnect removes from rooms."""
        conn_id = "test_conn"
        manager._connections[conn_id] = mock_websocket
        manager._metadata[conn_id] = {"user_id": None, "rooms": ["room1"]}
        manager._rooms["room1"] = {conn_id}

        await manager.disconnect(conn_id)

        assert "room1" not in manager._rooms

    @pytest.mark.asyncio
    async def test_disconnect_cancels_heartbeat(self, manager, mock_websocket):
        """Test disconnect cancels heartbeat task."""
        conn_id = "test_conn"
        manager._connections[conn_id] = mock_websocket
        manager._metadata[conn_id] = {"user_id": None, "rooms": []}

        mock_task = MagicMock()
        mock_task.cancel = MagicMock()
        manager._heartbeat_tasks[conn_id] = mock_task

        await manager.disconnect(conn_id)

        mock_task.cancel.assert_called_once()
        assert conn_id not in manager._heartbeat_tasks

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_connection(self, manager):
        """Test disconnect handles nonexistent connection."""
        # Should not raise
        await manager.disconnect("nonexistent")

    @pytest.mark.asyncio
    async def test_disconnect_closes_websocket(self, manager, mock_websocket):
        """Test disconnect closes the WebSocket."""
        conn_id = "test_conn"
        manager._connections[conn_id] = mock_websocket
        manager._metadata[conn_id] = {"user_id": None, "rooms": []}

        await manager.disconnect(conn_id)

        mock_websocket.close.assert_awaited_once()

    # ==================== Room Management Tests ====================

    @pytest.mark.asyncio
    async def test_join_room_creates_room(self, manager):
        """Test join_room creates room if not exists."""
        conn_id = "test_conn"
        manager._metadata[conn_id] = {"rooms": []}

        await manager.join_room(conn_id, "new_room")

        assert "new_room" in manager._rooms
        assert conn_id in manager._rooms["new_room"]

    @pytest.mark.asyncio
    async def test_join_room_adds_to_existing(self, manager):
        """Test join_room adds to existing room."""
        conn_id = "test_conn"
        manager._metadata[conn_id] = {"rooms": []}
        manager._rooms["existing_room"] = {"other_conn"}

        await manager.join_room(conn_id, "existing_room")

        assert conn_id in manager._rooms["existing_room"]
        assert "other_conn" in manager._rooms["existing_room"]

    @pytest.mark.asyncio
    async def test_join_room_updates_metadata(self, manager):
        """Test join_room updates connection metadata."""
        conn_id = "test_conn"
        manager._metadata[conn_id] = {"rooms": []}

        await manager.join_room(conn_id, "room1")

        assert "room1" in manager._metadata[conn_id]["rooms"]

    @pytest.mark.asyncio
    async def test_leave_room_removes_from_room(self, manager):
        """Test leave_room removes connection from room."""
        conn_id = "test_conn"
        manager._metadata[conn_id] = {"rooms": ["room1"]}
        manager._rooms["room1"] = {conn_id, "other_conn"}

        await manager.leave_room(conn_id, "room1")

        assert conn_id not in manager._rooms["room1"]
        assert "other_conn" in manager._rooms["room1"]

    @pytest.mark.asyncio
    async def test_leave_room_deletes_empty_room(self, manager):
        """Test leave_room deletes empty room."""
        conn_id = "test_conn"
        manager._metadata[conn_id] = {"rooms": ["room1"]}
        manager._rooms["room1"] = {conn_id}

        await manager.leave_room(conn_id, "room1")

        assert "room1" not in manager._rooms

    @pytest.mark.asyncio
    async def test_leave_room_updates_metadata(self, manager):
        """Test leave_room updates metadata."""
        conn_id = "test_conn"
        manager._metadata[conn_id] = {"rooms": ["room1", "room2"]}
        manager._rooms["room1"] = {conn_id}

        await manager.leave_room(conn_id, "room1")

        assert "room1" not in manager._metadata[conn_id]["rooms"]
        assert "room2" in manager._metadata[conn_id]["rooms"]

    # ==================== Message Sending Tests ====================

    @pytest.mark.asyncio
    async def test_send_to_connection_json(self, manager, mock_websocket):
        """Test send_to_connection sends JSON."""
        conn_id = "test_conn"
        manager._connections[conn_id] = mock_websocket

        result = await manager.send_to_connection(conn_id, {"key": "value"})

        assert result is True
        mock_websocket.send_json.assert_awaited_once_with({"key": "value"})

    @pytest.mark.asyncio
    async def test_send_to_connection_text(self, manager, mock_websocket):
        """Test send_to_connection sends text."""
        conn_id = "test_conn"
        manager._connections[conn_id] = mock_websocket

        result = await manager.send_to_connection(conn_id, "plain text")

        assert result is True
        mock_websocket.send_text.assert_awaited_once_with("plain text")

    @pytest.mark.asyncio
    async def test_send_to_connection_nonexistent(self, manager):
        """Test send_to_connection returns False for missing connection."""
        result = await manager.send_to_connection("nonexistent", "message")
        assert result is False

    @pytest.mark.asyncio
    async def test_send_to_connection_handles_error(self, manager, mock_websocket):
        """Test send_to_connection handles errors and disconnects."""
        conn_id = "test_conn"
        manager._connections[conn_id] = mock_websocket
        manager._metadata[conn_id] = {"user_id": None, "rooms": []}
        mock_websocket.send_json.side_effect = Exception("Send failed")

        result = await manager.send_to_connection(conn_id, {"msg": "test"})

        assert result is False
        assert conn_id not in manager._connections

    @pytest.mark.asyncio
    async def test_send_to_user(self, manager, mock_websocket):
        """Test send_to_user sends to all user connections."""
        user_id = 123
        conn_ids = ["conn1", "conn2"]
        manager._user_connections[user_id] = set(conn_ids)
        manager._connections = {cid: mock_websocket for cid in conn_ids}

        result = await manager.send_to_user(user_id, {"event": "test"})

        assert result == 2
        assert mock_websocket.send_json.await_count == 2

    @pytest.mark.asyncio
    async def test_send_to_user_no_connections(self, manager):
        """Test send_to_user with no user connections."""
        result = await manager.send_to_user(999, {"event": "test"})
        assert result == 0

    @pytest.mark.asyncio
    async def test_send_to_room(self, manager, mock_websocket):
        """Test send_to_room sends to all room members."""
        room_id = "test_room"
        conn_ids = ["conn1", "conn2", "conn3"]
        manager._rooms[room_id] = set(conn_ids)
        manager._connections = {cid: mock_websocket for cid in conn_ids}

        result = await manager.send_to_room(room_id, {"event": "test"})

        assert result == 3

    @pytest.mark.asyncio
    async def test_send_to_room_with_exclude(self, manager, mock_websocket):
        """Test send_to_room excludes specified connection."""
        room_id = "test_room"
        conn_ids = ["conn1", "conn2", "conn3"]
        manager._rooms[room_id] = set(conn_ids)
        manager._connections = {cid: mock_websocket for cid in conn_ids}

        result = await manager.send_to_room(room_id, {"event": "test"}, exclude="conn1")

        assert result == 2

    @pytest.mark.asyncio
    async def test_send_to_room_empty(self, manager):
        """Test send_to_room with empty room."""
        result = await manager.send_to_room("empty_room", {"event": "test"})
        assert result == 0

    @pytest.mark.asyncio
    async def test_broadcast(self, manager, mock_websocket):
        """Test broadcast sends to all connections."""
        conn_ids = ["conn1", "conn2", "conn3", "conn4"]
        manager._connections = {cid: mock_websocket for cid in conn_ids}

        result = await manager.broadcast({"event": "global"})

        assert result == 4

    @pytest.mark.asyncio
    async def test_broadcast_with_exclude(self, manager, mock_websocket):
        """Test broadcast excludes specified connection."""
        conn_ids = ["conn1", "conn2", "conn3"]
        manager._connections = {cid: mock_websocket for cid in conn_ids}

        result = await manager.broadcast({"event": "global"}, exclude="conn2")

        assert result == 2

    # ==================== Heartbeat Loop Tests ====================

    @pytest.mark.asyncio
    async def test_heartbeat_loop_sends_heartbeat(self, manager, mock_websocket):
        """Test heartbeat loop sends heartbeat messages."""
        conn_id = "test_conn"
        manager._connections[conn_id] = mock_websocket

        with patch('app.services.websocket_service.settings') as mock_settings:
            mock_settings.WS_HEARTBEAT_INTERVAL = 0.01  # Very short for testing

            # Run heartbeat for a brief period
            task = asyncio.create_task(manager._heartbeat_loop(conn_id))
            await asyncio.sleep(0.05)  # Let a few heartbeats run
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Should have sent at least one heartbeat
        assert mock_websocket.send_json.await_count >= 1
        # Verify heartbeat format
        call_args = mock_websocket.send_json.call_args_list[0][0][0]
        assert call_args["type"] == "heartbeat"
        assert "timestamp" in call_args

    @pytest.mark.asyncio
    async def test_heartbeat_loop_stops_on_disconnect(self, manager, mock_websocket):
        """Test heartbeat loop stops when connection removed."""
        conn_id = "test_conn"
        manager._connections[conn_id] = mock_websocket

        with patch('app.services.websocket_service.settings') as mock_settings:
            mock_settings.WS_HEARTBEAT_INTERVAL = 0.01

            # Start heartbeat
            task = asyncio.create_task(manager._heartbeat_loop(conn_id))
            await asyncio.sleep(0.02)  # Let it start

            # Remove connection
            del manager._connections[conn_id]
            await asyncio.sleep(0.02)  # Let loop exit

            # Task should complete without cancellation
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_heartbeat_loop_handles_cancelled_error(self, manager, mock_websocket):
        """Test heartbeat loop handles cancellation gracefully."""
        conn_id = "test_conn"
        manager._connections[conn_id] = mock_websocket

        with patch('app.services.websocket_service.settings') as mock_settings:
            mock_settings.WS_HEARTBEAT_INTERVAL = 0.01

            task = asyncio.create_task(manager._heartbeat_loop(conn_id))
            await asyncio.sleep(0.02)
            task.cancel()

            # Should not raise, just exit gracefully
            try:
                await task
            except asyncio.CancelledError:
                pass  # Expected behavior

    @pytest.mark.asyncio
    async def test_heartbeat_loop_handles_send_failure(self, manager, mock_websocket):
        """Test heartbeat loop handles send errors gracefully."""
        conn_id = "test_conn"
        manager._connections[conn_id] = mock_websocket
        manager._metadata[conn_id] = {"user_id": None, "rooms": []}

        # Make send fail
        mock_websocket.send_json.side_effect = Exception("Connection lost")

        with patch('app.services.websocket_service.settings') as mock_settings:
            mock_settings.WS_HEARTBEAT_INTERVAL = 0.01

            # Run heartbeat - should handle error and disconnect
            task = asyncio.create_task(manager._heartbeat_loop(conn_id))
            await asyncio.sleep(0.05)

            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    # ==================== Event Notification Tests ====================

    @pytest.mark.asyncio
    async def test_notify_deal_update(self, manager, mock_websocket):
        """Test notify_deal_update sends to deals room."""
        manager._rooms["deals"] = {"conn1"}
        manager._connections["conn1"] = mock_websocket

        await manager.notify_deal_update(
            deal_id=123,
            action="updated",
            data={"name": "New Deal"},
            user_id=456,
        )

        mock_websocket.send_json.assert_awaited_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "deal_update"
        assert call_args["action"] == "updated"
        assert call_args["deal_id"] == 123
        assert call_args["triggered_by"] == 456

    @pytest.mark.asyncio
    async def test_notify_property_update(self, manager, mock_websocket):
        """Test notify_property_update sends to properties room."""
        manager._rooms["properties"] = {"conn1"}
        manager._connections["conn1"] = mock_websocket

        await manager.notify_property_update(
            property_id=789,
            action="created",
            data={"name": "New Property"},
        )

        mock_websocket.send_json.assert_awaited_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "property_update"
        assert call_args["property_id"] == 789

    @pytest.mark.asyncio
    async def test_notify_analytics_ready(self, manager, mock_websocket):
        """Test notify_analytics_ready sends to specific user."""
        user_id = 123
        manager._user_connections[user_id] = {"conn1"}
        manager._connections["conn1"] = mock_websocket

        await manager.notify_analytics_ready(
            report_type="portfolio",
            user_id=user_id,
            report_id="report-abc123",
        )

        mock_websocket.send_json.assert_awaited_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "analytics_ready"
        assert call_args["report_type"] == "portfolio"
        assert call_args["report_id"] == "report-abc123"


class TestWebSocketManagerSingleton:
    """Tests for the get_websocket_manager singleton."""

    def test_get_websocket_manager_returns_instance(self):
        """Test get_websocket_manager returns WebSocketManager instance."""
        from app.services.websocket_service import get_websocket_manager, WebSocketManager

        manager = get_websocket_manager()
        assert isinstance(manager, WebSocketManager)

    def test_get_websocket_manager_returns_same_instance(self):
        """Test get_websocket_manager returns singleton."""
        from app.services.websocket_service import get_websocket_manager

        manager1 = get_websocket_manager()
        manager2 = get_websocket_manager()
        assert manager1 is manager2
