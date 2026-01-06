"""
Unit tests for the Redis caching service.

Tests RedisService functionality including:
- Connection management
- Basic operations (get, set, delete, exists)
- Bulk operations (mget, delete_pattern)
- Key builders
- Pub/Sub functionality
"""
import json
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest


class TestRedisService:
    """Tests for the RedisService class."""

    @pytest.fixture
    def service(self):
        """Create RedisService instance."""
        from app.services.redis_service import RedisService
        return RedisService()

    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client."""
        client = AsyncMock()
        client.ping = AsyncMock(return_value=True)
        client.get = AsyncMock(return_value=None)
        client.set = AsyncMock(return_value=True)
        client.delete = AsyncMock(return_value=1)
        client.exists = AsyncMock(return_value=1)
        client.mget = AsyncMock(return_value=[])
        client.scan_iter = MagicMock()
        client.publish = AsyncMock(return_value=1)
        client.pubsub = MagicMock()
        client.close = AsyncMock()
        return client

    # ==================== Connection Tests ====================

    @pytest.mark.asyncio
    async def test_connect_success(self, service):
        """Test successful Redis connection."""
        with patch('app.services.redis_service.redis.ConnectionPool.from_url') as mock_pool:
            with patch('app.services.redis_service.redis.Redis') as mock_redis:
                mock_client = AsyncMock()
                mock_client.ping = AsyncMock(return_value=True)
                mock_redis.return_value = mock_client

                await service.connect()

                assert service._client is not None
                mock_client.ping.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self, service):
        """Test Redis connection failure."""
        with patch('app.services.redis_service.redis.ConnectionPool.from_url') as mock_pool:
            with patch('app.services.redis_service.redis.Redis') as mock_redis:
                mock_client = AsyncMock()
                mock_client.ping = AsyncMock(side_effect=Exception("Connection refused"))
                mock_redis.return_value = mock_client

                with pytest.raises(Exception, match="Connection refused"):
                    await service.connect()

    @pytest.mark.asyncio
    async def test_disconnect(self, service, mock_redis_client):
        """Test Redis disconnection."""
        service._client = mock_redis_client

        await service.disconnect()

        mock_redis_client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_without_connection(self, service):
        """Test disconnect when not connected."""
        service._client = None
        # Should not raise
        await service.disconnect()

    def test_client_property_raises_when_not_connected(self, service):
        """Test client property raises when not connected."""
        service._client = None

        with pytest.raises(RuntimeError, match="Redis not connected"):
            _ = service.client

    def test_client_property_returns_client(self, service, mock_redis_client):
        """Test client property returns client when connected."""
        service._client = mock_redis_client
        assert service.client is mock_redis_client

    # ==================== Basic Operations Tests ====================

    @pytest.mark.asyncio
    async def test_get_returns_value(self, service, mock_redis_client):
        """Test get returns deserialized value."""
        service._client = mock_redis_client
        mock_redis_client.get = AsyncMock(return_value='{"key": "value"}')

        result = await service.get("test_key")

        assert result == {"key": "value"}
        mock_redis_client.get.assert_awaited_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing_key(self, service, mock_redis_client):
        """Test get returns None for missing key."""
        service._client = mock_redis_client
        mock_redis_client.get = AsyncMock(return_value=None)

        result = await service.get("missing_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_raw_on_json_error(self, service, mock_redis_client):
        """Test get returns raw value on JSON decode error."""
        service._client = mock_redis_client
        mock_redis_client.get = AsyncMock(return_value="not-json")

        result = await service.get("raw_key")

        assert result == "not-json"

    @pytest.mark.asyncio
    async def test_get_handles_exception(self, service, mock_redis_client):
        """Test get handles exceptions gracefully."""
        service._client = mock_redis_client
        mock_redis_client.get = AsyncMock(side_effect=Exception("Redis error"))

        result = await service.get("error_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_success(self, service, mock_redis_client):
        """Test set stores value successfully."""
        service._client = mock_redis_client

        result = await service.set("test_key", {"data": 123})

        assert result is True
        mock_redis_client.set.assert_awaited_once()
        # Verify JSON serialization
        call_args = mock_redis_client.set.call_args
        assert call_args[0][0] == "test_key"
        assert json.loads(call_args[0][1]) == {"data": 123}

    @pytest.mark.asyncio
    async def test_set_with_custom_ttl(self, service, mock_redis_client):
        """Test set with custom TTL."""
        service._client = mock_redis_client

        await service.set("ttl_key", "value", ttl=300)

        call_kwargs = mock_redis_client.set.call_args[1]
        assert call_kwargs["ex"] == 300

    @pytest.mark.asyncio
    async def test_set_handles_exception(self, service, mock_redis_client):
        """Test set handles exceptions gracefully."""
        service._client = mock_redis_client
        mock_redis_client.set = AsyncMock(side_effect=Exception("Redis error"))

        result = await service.set("error_key", "value")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_success(self, service, mock_redis_client):
        """Test delete removes key."""
        service._client = mock_redis_client

        result = await service.delete("delete_key")

        assert result is True
        mock_redis_client.delete.assert_awaited_once_with("delete_key")

    @pytest.mark.asyncio
    async def test_delete_handles_exception(self, service, mock_redis_client):
        """Test delete handles exceptions gracefully."""
        service._client = mock_redis_client
        mock_redis_client.delete = AsyncMock(side_effect=Exception("Redis error"))

        result = await service.delete("error_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_returns_true(self, service, mock_redis_client):
        """Test exists returns True for existing key."""
        service._client = mock_redis_client
        mock_redis_client.exists = AsyncMock(return_value=1)

        result = await service.exists("existing_key")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false(self, service, mock_redis_client):
        """Test exists returns False for missing key."""
        service._client = mock_redis_client
        mock_redis_client.exists = AsyncMock(return_value=0)

        result = await service.exists("missing_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_handles_exception(self, service, mock_redis_client):
        """Test exists handles exceptions gracefully."""
        service._client = mock_redis_client
        mock_redis_client.exists = AsyncMock(side_effect=Exception("Redis error"))

        result = await service.exists("error_key")

        assert result is False

    # ==================== Bulk Operations Tests ====================

    @pytest.mark.asyncio
    async def test_mget_returns_values(self, service, mock_redis_client):
        """Test mget returns multiple values."""
        service._client = mock_redis_client
        mock_redis_client.mget = AsyncMock(return_value=[
            '{"a": 1}',
            '{"b": 2}',
            None,
        ])

        result = await service.mget(["key1", "key2", "key3"])

        assert result == {
            "key1": {"a": 1},
            "key2": {"b": 2},
        }

    @pytest.mark.asyncio
    async def test_mget_handles_exception(self, service, mock_redis_client):
        """Test mget handles exceptions gracefully."""
        service._client = mock_redis_client
        mock_redis_client.mget = AsyncMock(side_effect=Exception("Redis error"))

        result = await service.mget(["key1", "key2"])

        assert result == {}

    @pytest.mark.asyncio
    async def test_delete_pattern(self, service, mock_redis_client):
        """Test delete_pattern removes matching keys."""
        service._client = mock_redis_client

        # Mock async iterator for scan_iter
        async def async_scan_iter():
            for key in ["prefix:1", "prefix:2", "prefix:3"]:
                yield key

        mock_redis_client.scan_iter = MagicMock(return_value=async_scan_iter())
        mock_redis_client.delete = AsyncMock(return_value=3)

        result = await service.delete_pattern("prefix:*")

        assert result == 3

    @pytest.mark.asyncio
    async def test_delete_pattern_no_matches(self, service, mock_redis_client):
        """Test delete_pattern with no matches."""
        service._client = mock_redis_client

        async def empty_scan_iter():
            return
            yield  # Make it a generator

        mock_redis_client.scan_iter = MagicMock(return_value=empty_scan_iter())

        result = await service.delete_pattern("nonexistent:*")

        assert result == 0

    # ==================== Key Builder Tests ====================

    def test_build_key(self, service):
        """Test generic key builder."""
        key = service.build_key("prefix", "middle", "suffix")
        assert key == "prefix:middle:suffix"

    def test_build_key_single_part(self, service):
        """Test key builder with single part."""
        key = service.build_key("single")
        assert key == "single"

    def test_property_key(self, service):
        """Test property key builder."""
        key = service.property_key(123)
        assert key == "property:123"

    def test_deal_key(self, service):
        """Test deal key builder."""
        key = service.deal_key(456)
        assert key == "deal:456"

    def test_user_key(self, service):
        """Test user key builder."""
        key = service.user_key(789)
        assert key == "user:789"

    def test_analytics_key(self, service):
        """Test analytics key builder."""
        key = service.analytics_key("portfolio", "2024", "q1")
        assert key == "analytics:portfolio:2024:q1"

    def test_analytics_key_no_params(self, service):
        """Test analytics key builder with no params."""
        key = service.analytics_key("dashboard")
        assert key == "analytics:dashboard:"

    # ==================== Connection Pool Tests ====================

    @pytest.mark.asyncio
    async def test_connect_creates_connection_pool(self, service):
        """Test connect creates a connection pool with correct settings."""
        with patch('app.services.redis_service.redis.ConnectionPool.from_url') as mock_pool:
            with patch('app.services.redis_service.redis.Redis') as mock_redis:
                with patch('app.services.redis_service.settings') as mock_settings:
                    mock_settings.REDIS_URL = "redis://localhost:6379"
                    mock_settings.REDIS_MAX_CONNECTIONS = 20

                    mock_client = AsyncMock()
                    mock_client.ping = AsyncMock(return_value=True)
                    mock_redis.return_value = mock_client

                    await service.connect()

                    # Verify pool creation with correct parameters
                    mock_pool.assert_called_once()
                    call_kwargs = mock_pool.call_args
                    assert mock_settings.REDIS_URL in str(call_kwargs)

    @pytest.mark.asyncio
    async def test_connect_uses_pool_for_client(self, service):
        """Test connect creates Redis client with connection pool."""
        with patch('app.services.redis_service.redis.ConnectionPool.from_url') as mock_pool:
            with patch('app.services.redis_service.redis.Redis') as mock_redis:
                mock_pool_instance = MagicMock()
                mock_pool.return_value = mock_pool_instance

                mock_client = AsyncMock()
                mock_client.ping = AsyncMock(return_value=True)
                mock_redis.return_value = mock_client

                await service.connect()

                # Verify Redis client created with pool
                mock_redis.assert_called_once_with(connection_pool=mock_pool_instance)

    @pytest.mark.asyncio
    async def test_connect_timeout_handling(self, service):
        """Test connect handles connection timeout gracefully."""
        with patch('app.services.redis_service.redis.ConnectionPool.from_url') as mock_pool:
            with patch('app.services.redis_service.redis.Redis') as mock_redis:
                import asyncio

                mock_client = AsyncMock()
                mock_client.ping = AsyncMock(side_effect=TimeoutError("Connection timed out"))
                mock_redis.return_value = mock_client

                with pytest.raises(asyncio.TimeoutError):
                    await service.connect()

    @pytest.mark.asyncio
    async def test_operation_with_connection_error(self, service, mock_redis_client):
        """Test operations handle connection errors gracefully."""
        service._client = mock_redis_client

        # Simulate connection error
        import redis.exceptions
        mock_redis_client.get = AsyncMock(side_effect=Exception("Connection lost"))

        result = await service.get("test_key")

        # Should return None instead of raising
        assert result is None

    @pytest.mark.asyncio
    async def test_set_with_connection_error(self, service, mock_redis_client):
        """Test set handles connection errors gracefully."""
        service._client = mock_redis_client
        mock_redis_client.set = AsyncMock(side_effect=Exception("Connection pool exhausted"))

        result = await service.set("test_key", "test_value")

        # Should return False instead of raising
        assert result is False

    @pytest.mark.asyncio
    async def test_reconnect_after_disconnect(self, service):
        """Test service can reconnect after disconnect."""
        with patch('app.services.redis_service.redis.ConnectionPool.from_url') as mock_pool:
            with patch('app.services.redis_service.redis.Redis') as mock_redis:
                mock_client = AsyncMock()
                mock_client.ping = AsyncMock(return_value=True)
                mock_client.close = AsyncMock()
                mock_redis.return_value = mock_client

                # Connect
                await service.connect()
                assert service._client is not None

                # Disconnect
                await service.disconnect()
                mock_client.close.assert_awaited_once()

                # Reconnect
                await service.connect()
                assert service._client is not None

    # ==================== Pub/Sub Tests ====================

    @pytest.mark.asyncio
    async def test_publish_success(self, service, mock_redis_client):
        """Test publish sends message."""
        service._client = mock_redis_client
        mock_redis_client.publish = AsyncMock(return_value=2)

        result = await service.publish("channel", {"event": "update"})

        assert result == 2
        mock_redis_client.publish.assert_awaited_once()
        # Verify JSON serialization
        call_args = mock_redis_client.publish.call_args
        assert call_args[0][0] == "channel"
        assert json.loads(call_args[0][1]) == {"event": "update"}

    @pytest.mark.asyncio
    async def test_publish_handles_exception(self, service, mock_redis_client):
        """Test publish handles exceptions gracefully."""
        service._client = mock_redis_client
        mock_redis_client.publish = AsyncMock(side_effect=Exception("Pub error"))

        result = await service.publish("channel", "message")

        assert result == 0

    @pytest.mark.asyncio
    async def test_subscribe_yields_messages(self, service, mock_redis_client):
        """Test subscribe yields messages from channel."""
        service._client = mock_redis_client

        mock_pubsub = AsyncMock()
        mock_pubsub.subscribe = AsyncMock()

        # Create async iterator for listen
        async def async_listen():
            yield {"type": "subscribe", "data": 1}
            yield {"type": "message", "data": '{"event": "test"}'}
            yield {"type": "message", "data": "plain-text"}

        mock_pubsub.listen = MagicMock(return_value=async_listen())
        mock_redis_client.pubsub = MagicMock(return_value=mock_pubsub)

        messages = []
        count = 0
        async for msg in service.subscribe("test_channel"):
            messages.append(msg)
            count += 1
            if count >= 2:
                break

        assert len(messages) == 2
        assert messages[0] == {"event": "test"}
        assert messages[1] == "plain-text"


class TestRedisServiceSingleton:
    """Tests for the get_redis_service singleton."""

    @pytest.mark.asyncio
    async def test_get_redis_service_creates_and_connects(self):
        """Test get_redis_service creates and connects service."""
        with patch('app.services.redis_service.RedisService') as MockService:
            mock_instance = MagicMock()
            mock_instance.connect = AsyncMock()
            MockService.return_value = mock_instance

            # Reset singleton
            import app.services.redis_service as redis_module
            redis_module._redis_service = None

            from app.services.redis_service import get_redis_service
            service = await get_redis_service()

            mock_instance.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_redis_service_returns_existing(self):
        """Test get_redis_service returns existing instance."""
        import app.services.redis_service as redis_module
        from app.services.redis_service import RedisService

        # Set up existing instance
        existing = RedisService()
        existing._client = MagicMock()  # Pretend connected
        redis_module._redis_service = existing

        with patch.object(existing, 'connect', new=AsyncMock()) as mock_connect:
            from app.services.redis_service import get_redis_service
            service = await get_redis_service()

            # Should not call connect again
            mock_connect.assert_not_awaited()
            assert service is existing

        # Clean up
        redis_module._redis_service = None
