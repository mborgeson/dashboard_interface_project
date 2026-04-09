"""Tests for monitoring API endpoints.

Tests the Monitoring API endpoints including:
- Prometheus metrics export
- Health check probes (liveness, readiness)
- Detailed health information
- Performance statistics
- Application info
"""

import pytest

# All monitoring endpoints now require admin authentication
pytestmark = pytest.mark.usefixtures("auto_auth")

# =============================================================================
# Liveness Probe Tests
# =============================================================================


@pytest.mark.asyncio
async def test_liveness_probe(client, db_session):
    """Test liveness probe returns alive status."""
    response = await client.get("/api/v1/monitoring/health/live", follow_redirects=True)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    data = response.json()

    assert data["status"] == "alive"
    assert "timestamp" in data


# =============================================================================
# Readiness Probe Tests
# =============================================================================


@pytest.mark.asyncio
async def test_readiness_probe(client, db_session):
    """Test readiness probe checks database connectivity."""
    response = await client.get(
        "/api/v1/monitoring/health/ready", follow_redirects=True
    )

    # Accept 200 (ready) or 503 (not ready)
    assert response.status_code in [200, 503]

    if response.status_code == 200:
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "timestamp" in data


# =============================================================================
# Detailed Health Check Tests
# =============================================================================


@pytest.mark.asyncio
async def test_detailed_health_check(client, db_session):
    """Test detailed health check returns comprehensive info."""
    response = await client.get(
        "/api/v1/monitoring/health/detailed", follow_redirects=True
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    data = response.json()

    assert "status" in data
    assert "timestamp" in data
    assert "application" in data
    assert "checks" in data


@pytest.mark.asyncio
async def test_detailed_health_application_info(client, db_session):
    """Test detailed health includes application info."""
    response = await client.get(
        "/api/v1/monitoring/health/detailed", follow_redirects=True
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    data = response.json()

    app_info = data.get("application", {})
    assert "name" in app_info
    assert "version" in app_info
    assert "environment" in app_info


# =============================================================================
# Prometheus Metrics Tests
# =============================================================================


@pytest.mark.asyncio
async def test_prometheus_metrics(client, db_session):
    """Test Prometheus metrics endpoint returns metrics."""
    response = await client.get("/api/v1/monitoring/metrics", follow_redirects=True)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )

    # Should return text/plain or Prometheus format
    content_type = response.headers.get("content-type", "")
    assert "text" in content_type or "application" in content_type


@pytest.mark.asyncio
async def test_prometheus_metrics_content(client, db_session):
    """Test Prometheus metrics contain expected format."""
    response = await client.get("/api/v1/monitoring/metrics", follow_redirects=True)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )

    # Content should not be empty
    content = response.text
    assert len(content) > 0


# =============================================================================
# Connection Pool Stats Tests
# =============================================================================


@pytest.mark.asyncio
async def test_pool_stats(client, db_session):
    """Test connection pool stats endpoint returns pool metrics."""
    response = await client.get("/api/v1/monitoring/pool-stats", follow_redirects=True)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    data = response.json()

    assert "timestamp" in data
    assert "database" in data
    assert "redis" in data
    assert "summary" in data


@pytest.mark.asyncio
async def test_pool_stats_summary_structure(client, db_session):
    """Test pool stats summary contains expected fields."""
    response = await client.get("/api/v1/monitoring/pool-stats", follow_redirects=True)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    data = response.json()

    summary = data.get("summary", {})
    assert "db_pool_total_size" in summary
    assert "db_pool_total_checked_out" in summary
    assert "db_pool_utilization_pct" in summary
    assert "redis_pools_configured" in summary
    assert "redis_pools_connected" in summary


# =============================================================================
# Performance Stats Tests
# =============================================================================


@pytest.mark.asyncio
async def test_performance_stats(client, db_session):
    """Test performance statistics endpoint."""
    response = await client.get("/api/v1/monitoring/stats", follow_redirects=True)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    data = response.json()

    assert "timestamp" in data


@pytest.mark.asyncio
async def test_performance_stats_system_metrics(client, db_session):
    """Test performance stats include system metrics."""
    response = await client.get("/api/v1/monitoring/stats", follow_redirects=True)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    data = response.json()

    # Should have system metrics
    assert "system" in data or "note" in data


# =============================================================================
# Application Info Tests
# =============================================================================


@pytest.mark.asyncio
async def test_application_info(client, db_session):
    """Test application info endpoint."""
    response = await client.get("/api/v1/monitoring/info", follow_redirects=True)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    data = response.json()

    assert "name" in data
    assert "version" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_application_info_structure(client, db_session):
    """Test application info contains expected structure."""
    response = await client.get("/api/v1/monitoring/info", follow_redirects=True)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    data = response.json()

    # Should have server and features info
    assert "server" in data or "features" in data or "api" in data


@pytest.mark.asyncio
async def test_application_info_no_secrets(client, db_session):
    """Test application info does not expose secrets."""
    response = await client.get("/api/v1/monitoring/info", follow_redirects=True)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    data = response.json()

    # Convert to string to check for sensitive patterns
    data_str = str(data).lower()

    # Should not contain sensitive info patterns
    assert "password" not in data_str
    assert "secret_key" not in data_str
    assert "api_key" not in data_str
