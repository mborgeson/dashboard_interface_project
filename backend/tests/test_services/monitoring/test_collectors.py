"""Tests for monitoring collectors."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.monitoring.collectors import (
    ApplicationMetricsCollector,
    CollectorRegistry,
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

    def test_set_engine(self):
        """Test setting the database engine."""
        collector = DatabaseMetricsCollector()
        mock_engine = MagicMock()

        collector.set_engine(mock_engine)

        assert collector._engine is mock_engine

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

    @pytest.mark.asyncio
    async def test_collect_engine_error(self):
        """Test collect handles engine errors."""
        collector = DatabaseMetricsCollector()

        mock_engine = MagicMock()
        mock_engine.pool.size.side_effect = Exception("Pool error")

        collector.set_engine(mock_engine)

        metrics = await collector.collect()

        assert "error" in metrics


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
        collector._last_collection = datetime.utcnow()

        metrics = await collector.collect()

        assert metrics.get("cached") is True


# =============================================================================
# CollectorRegistry Tests
# =============================================================================


class TestCollectorRegistry:
    """Tests for CollectorRegistry."""

    def test_initialization(self):
        """Test registry initialization creates collectors."""
        registry = CollectorRegistry()

        assert isinstance(registry.system, SystemMetricsCollector)
        assert isinstance(registry.database, DatabaseMetricsCollector)
        assert isinstance(registry.application, ApplicationMetricsCollector)

    @pytest.mark.asyncio
    async def test_collect_all(self):
        """Test collecting metrics from all collectors."""
        registry = CollectorRegistry()

        metrics = await registry.collect_all()

        assert "system" in metrics
        assert "database" in metrics
        assert "application" in metrics

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
