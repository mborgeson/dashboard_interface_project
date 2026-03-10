"""Tests for monitoring collectors."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.monitoring.collectors import (
    ApplicationMetricsCollector,
    CollectorRegistry,
    ConnectionPoolCollector,
    DatabaseMetricsCollector,
    SystemMetricsCollector,
    get_collector_registry,
)

# =============================================================================
# SystemMetricsCollector Tests
# =============================================================================


class TestSystemMetricsCollector:
    """Tests for SystemMetricsCollector."""

    def test_initialization(self):
        """Test collector initialization."""
        collector = SystemMetricsCollector()

        assert collector._last_collection is None
        assert collector._cache_duration == timedelta(seconds=5)
        assert collector._cached_metrics == {}

    @pytest.mark.asyncio
    async def test_collect_returns_metrics(self):
        """Test that collect returns metrics dict."""
        collector = SystemMetricsCollector()

        metrics = await collector.collect()

        assert "timestamp" in metrics
        assert "platform" in metrics
        assert "process" in metrics
        assert metrics["platform"]["system"] is not None
        assert metrics["process"]["pid"] is not None

    @pytest.mark.asyncio
    async def test_collect_uses_cache(self):
        """Test that collect uses cached metrics."""
        collector = SystemMetricsCollector()

        # First collection
        metrics1 = await collector.collect()

        # Second collection should return cached
        metrics2 = await collector.collect()

        assert metrics1["timestamp"] == metrics2["timestamp"]

    @pytest.mark.asyncio
    async def test_collect_with_psutil(self):
        """Test collect when psutil is available."""
        collector = SystemMetricsCollector()

        # Clear cache to force fresh collection
        collector._last_collection = None

        metrics = await collector.collect()

        # Check if psutil metrics are included
        if metrics.get("cpu", {}).get("available", True) is not False:
            assert "percent" in metrics.get("cpu", {})
            assert "memory" in metrics
            assert "disk" in metrics

    @pytest.mark.asyncio
    async def test_collect_without_psutil(self):
        """Test collect when psutil is not available."""
        collector = SystemMetricsCollector()
        collector._last_collection = None

        # Mock ImportError for psutil
        with patch.dict("sys.modules", {"psutil": None}):
            # Force reimport attempt by clearing cache
            collector._cached_metrics = {}

            # The collector gracefully handles missing psutil
            metrics = await collector.collect()
            assert "platform" in metrics


# =============================================================================
# DatabaseMetricsCollector Tests
# =============================================================================


class TestDatabaseMetricsCollector:
    """Tests for DatabaseMetricsCollector."""

    def test_initialization(self):
        """Test collector initialization."""
        collector = DatabaseMetricsCollector()

        assert collector._engine is None
        assert collector._sync_engine is None

    def test_set_engine(self):
        """Test setting the database engine."""
        collector = DatabaseMetricsCollector()
        mock_engine = MagicMock()

        collector.set_engine(mock_engine)

        assert collector._engine is mock_engine

    def test_set_sync_engine(self):
        """Test setting the sync database engine."""
        collector = DatabaseMetricsCollector()
        mock_engine = MagicMock()

        collector.set_sync_engine(mock_engine)

        assert collector._sync_engine is mock_engine

    @pytest.mark.asyncio
    async def test_collect_without_engine(self):
        """Test collect returns minimal metrics without engine."""
        collector = DatabaseMetricsCollector()

        metrics = await collector.collect()

        assert metrics["connected"] is False
        assert metrics["pool"] == {}

    @pytest.mark.asyncio
    async def test_collect_with_engine(self):
        """Test collect with mock engine."""
        collector = DatabaseMetricsCollector()

        # Create mock engine with pool
        mock_pool = MagicMock()
        mock_pool.size.return_value = 10
        mock_pool.checkedout.return_value = 2
        mock_pool.overflow.return_value = 0
        mock_pool.checkedin.return_value = 8

        mock_engine = MagicMock()
        mock_engine.pool = mock_pool

        collector.set_engine(mock_engine)

        metrics = await collector.collect()

        assert metrics["connected"] is True
        assert metrics["pool"]["size"] == 10
        assert metrics["pool"]["checked_out"] == 2
        assert metrics["pool"]["overflow"] == 0
        assert metrics["pool"]["checked_in"] == 8
        # Verify per-engine breakdown
        assert metrics["pool"]["async"]["size"] == 10

    @pytest.mark.asyncio
    async def test_collect_with_both_engines(self):
        """Test collect with both async and sync engines."""
        collector = DatabaseMetricsCollector()

        # Async engine
        mock_async_pool = MagicMock()
        mock_async_pool.size.return_value = 10
        mock_async_pool.checkedout.return_value = 2
        mock_async_pool.overflow.return_value = 0
        mock_async_pool.checkedin.return_value = 8
        mock_async_engine = MagicMock()
        mock_async_engine.pool = mock_async_pool

        # Sync engine
        mock_sync_pool = MagicMock()
        mock_sync_pool.size.return_value = 5
        mock_sync_pool.checkedout.return_value = 1
        mock_sync_pool.overflow.return_value = 0
        mock_sync_pool.checkedin.return_value = 4
        mock_sync_engine = MagicMock()
        mock_sync_engine.pool = mock_sync_pool

        collector.set_engine(mock_async_engine)
        collector.set_sync_engine(mock_sync_engine)

        metrics = await collector.collect()

        assert metrics["connected"] is True
        assert metrics["pool"]["async"]["size"] == 10
        assert metrics["pool"]["sync"]["size"] == 5

    @pytest.mark.asyncio
    async def test_collect_engine_error(self):
        """Test collect handles engine errors."""
        collector = DatabaseMetricsCollector()

        mock_engine = MagicMock()
        mock_engine.pool.size.side_effect = Exception("Pool error")

        collector.set_engine(mock_engine)

        metrics = await collector.collect()

        assert "async_error" in metrics["pool"]


# =============================================================================
# ApplicationMetricsCollector Tests
# =============================================================================


class TestApplicationMetricsCollector:
    """Tests for ApplicationMetricsCollector."""

    def test_initialization(self):
        """Test collector initialization."""
        collector = ApplicationMetricsCollector()

        assert collector._db_session_factory is None
        assert collector._last_collection is None
        assert collector._cache_duration == timedelta(seconds=30)

    def test_set_session_factory(self):
        """Test setting session factory."""
        collector = ApplicationMetricsCollector()
        mock_factory = MagicMock()

        collector.set_session_factory(mock_factory)

        assert collector._db_session_factory is mock_factory

    @pytest.mark.asyncio
    async def test_collect_without_session_factory(self):
        """Test collect returns minimal metrics without session factory."""
        collector = ApplicationMetricsCollector()

        metrics = await collector.collect()

        assert "users" in metrics
        assert "deals" in metrics
        assert "properties" in metrics
        assert metrics["users"] == {}

    @pytest.mark.asyncio
    async def test_collect_uses_cache(self):
        """Test that collect uses cached metrics."""
        collector = ApplicationMetricsCollector()
        collector._cached_metrics = {"cached": True, "timestamp": "test"}
        collector._last_collection = datetime.now(UTC)

        metrics = await collector.collect()

        assert metrics.get("cached") is True


# =============================================================================
# CollectorRegistry Tests
# =============================================================================


# =============================================================================
# ConnectionPoolCollector Tests
# =============================================================================


class TestConnectionPoolCollector:
    """Tests for ConnectionPoolCollector."""

    def test_initialization(self):
        """Test collector initialization."""
        collector = ConnectionPoolCollector()

        assert collector._engine is None
        assert collector._sync_engine is None
        assert collector._last_collection is None
        assert collector._cached_metrics == {}

    def test_set_engine(self):
        """Test setting the async engine."""
        collector = ConnectionPoolCollector()
        mock_engine = MagicMock()

        collector.set_engine(mock_engine)

        assert collector._engine is mock_engine

    def test_set_sync_engine(self):
        """Test setting the sync engine."""
        collector = ConnectionPoolCollector()
        mock_engine = MagicMock()

        collector.set_sync_engine(mock_engine)

        assert collector._sync_engine is mock_engine

    @pytest.mark.asyncio
    async def test_collect_without_engines(self):
        """Test collect returns minimal metrics without engines."""
        collector = ConnectionPoolCollector()

        metrics = await collector.collect()

        assert "timestamp" in metrics
        assert "database" in metrics
        assert "redis" in metrics
        assert "summary" in metrics
        assert metrics["summary"]["db_pool_total_size"] == 0

    @pytest.mark.asyncio
    async def test_collect_with_async_engine(self):
        """Test collect with async engine set."""
        collector = ConnectionPoolCollector()

        mock_pool = MagicMock()
        mock_pool.size.return_value = 10
        mock_pool.checkedout.return_value = 3
        mock_pool.overflow.return_value = 1
        mock_pool.checkedin.return_value = 7
        mock_pool._max_overflow = 5

        mock_engine = MagicMock()
        mock_engine.pool = mock_pool

        collector.set_engine(mock_engine)

        metrics = await collector.collect()

        assert metrics["database"]["async"]["size"] == 10
        assert metrics["database"]["async"]["checked_out"] == 3
        assert metrics["database"]["async"]["overflow"] == 1
        assert metrics["database"]["async"]["checked_in"] == 7
        assert metrics["database"]["async"]["max_overflow"] == 5
        assert metrics["database"]["async"]["label"] == "async"
        assert metrics["summary"]["db_pool_total_size"] == 10
        assert metrics["summary"]["db_pool_total_checked_out"] == 3
        assert metrics["summary"]["db_pool_utilization_pct"] == 30.0

    @pytest.mark.asyncio
    async def test_collect_with_both_engines(self):
        """Test collect aggregates stats from both engines."""
        collector = ConnectionPoolCollector()

        # Async engine
        mock_async_pool = MagicMock()
        mock_async_pool.size.return_value = 10
        mock_async_pool.checkedout.return_value = 2
        mock_async_pool.overflow.return_value = 0
        mock_async_pool.checkedin.return_value = 8
        mock_async_engine = MagicMock()
        mock_async_engine.pool = mock_async_pool

        # Sync engine
        mock_sync_pool = MagicMock()
        mock_sync_pool.size.return_value = 5
        mock_sync_pool.checkedout.return_value = 1
        mock_sync_pool.overflow.return_value = 0
        mock_sync_pool.checkedin.return_value = 4
        mock_sync_engine = MagicMock()
        mock_sync_engine.pool = mock_sync_pool

        collector.set_engine(mock_async_engine)
        collector.set_sync_engine(mock_sync_engine)

        metrics = await collector.collect()

        assert metrics["summary"]["db_pool_total_size"] == 15
        assert metrics["summary"]["db_pool_total_checked_out"] == 3
        assert metrics["summary"]["db_pool_utilization_pct"] == 20.0

    @pytest.mark.asyncio
    async def test_collect_uses_cache(self):
        """Test that collect uses cached metrics within cache duration."""
        collector = ConnectionPoolCollector()

        metrics1 = await collector.collect()
        metrics2 = await collector.collect()

        assert metrics1["timestamp"] == metrics2["timestamp"]

    @pytest.mark.asyncio
    async def test_collect_handles_engine_error(self):
        """Test collect handles engine pool errors gracefully."""
        collector = ConnectionPoolCollector()

        mock_engine = MagicMock()
        mock_engine.pool.size.side_effect = Exception("Pool error")

        collector.set_engine(mock_engine)

        metrics = await collector.collect()

        assert "async_error" in metrics["database"]
        # Should still have summary
        assert "summary" in metrics

    @pytest.mark.asyncio
    async def test_collect_redis_pool_stats(self):
        """Test Redis pool stats collection with mock client."""
        collector = ConnectionPoolCollector()

        # Create a mock Redis client with connection pool
        mock_pool = MagicMock()
        mock_pool.max_connections = 20
        mock_pool._created_connections = 5
        mock_pool._available_connections = [MagicMock(), MagicMock(), MagicMock()]
        mock_pool._in_use_connections = {MagicMock(), MagicMock()}

        mock_redis = MagicMock()
        mock_redis.connection_pool = mock_pool

        stats = await collector._collect_redis_pool("test_pool", mock_redis)

        assert stats["available"] is True
        assert stats["max_connections"] == 20
        assert stats["created_connections"] == 5
        assert stats["available_connections"] == 3
        assert stats["in_use_connections"] == 2

    @pytest.mark.asyncio
    async def test_collect_redis_pool_none_client(self):
        """Test Redis pool stats when client is None."""
        collector = ConnectionPoolCollector()

        stats = await collector._collect_redis_pool("test_pool", None)

        assert stats["backend"] == "memory"
        assert stats["available"] is False

    @pytest.mark.asyncio
    async def test_collect_redis_pool_no_pool_attribute(self):
        """Test Redis pool stats when client has no connection_pool."""
        collector = ConnectionPoolCollector()

        mock_redis = MagicMock(spec=[])  # No attributes

        stats = await collector._collect_redis_pool("test_pool", mock_redis)

        assert stats["available"] is False
        assert "note" in stats


class TestCollectorRegistry:
    """Tests for CollectorRegistry."""

    def test_initialization(self):
        """Test registry initialization creates collectors."""
        registry = CollectorRegistry()

        assert isinstance(registry.system, SystemMetricsCollector)
        assert isinstance(registry.database, DatabaseMetricsCollector)
        assert isinstance(registry.application, ApplicationMetricsCollector)
        assert isinstance(registry.connection_pool, ConnectionPoolCollector)

    @pytest.mark.asyncio
    async def test_collect_all(self):
        """Test collecting metrics from all collectors."""
        registry = CollectorRegistry()

        metrics = await registry.collect_all()

        assert "system" in metrics
        assert "database" in metrics
        assert "application" in metrics
        assert "connection_pools" in metrics

    @pytest.mark.asyncio
    async def test_collect_all_handles_exceptions(self):
        """Test collect_all handles individual collector exceptions."""
        registry = CollectorRegistry()

        # Mock one collector to raise exception
        registry.system.collect = AsyncMock(side_effect=Exception("System error"))

        metrics = await registry.collect_all()

        assert "error" in metrics["system"]
        assert "System error" in metrics["system"]["error"]


# =============================================================================
# Singleton Tests
# =============================================================================


class TestCollectorRegistrySingleton:
    """Tests for collector registry singleton pattern."""

    def test_get_collector_registry_returns_instance(self):
        """Test get_collector_registry returns an instance."""
        import app.services.monitoring.collectors as module

        module._collector_registry = None

        registry = get_collector_registry()
        assert isinstance(registry, CollectorRegistry)

    def test_get_collector_registry_returns_same_instance(self):
        """Test get_collector_registry returns cached singleton."""
        import app.services.monitoring.collectors as module

        module._collector_registry = None

        registry1 = get_collector_registry()
        registry2 = get_collector_registry()
        assert registry1 is registry2
