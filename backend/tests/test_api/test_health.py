"""Tests for health check endpoints."""

from unittest.mock import AsyncMock, patch

import pytest


async def test_legacy_health_check(client):
    """Test the legacy health check endpoint returns 200."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "ok"]


async def test_root_redirect_or_docs(client):
    """Test root path behavior."""
    response = await client.get("/", follow_redirects=False)
    assert response.status_code in [200, 301, 302, 307, 308, 404]


# =============================================================================
# Detailed health check endpoint tests (/api/v1/health/status)
# =============================================================================


async def test_health_status_returns_200(client):
    """Test the detailed health check endpoint returns 200."""
    response = await client.get("/api/v1/health/status")
    assert response.status_code == 200


async def test_health_status_response_format(client):
    """Test the response contains all required top-level keys."""
    response = await client.get("/api/v1/health/status")
    data = response.json()

    assert "status" in data
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data
    assert "checks" in data
    assert "uptime_seconds" in data


async def test_health_status_valid_status_values(client):
    """Test that status is one of the expected values."""
    response = await client.get("/api/v1/health/status")
    data = response.json()

    assert data["status"] in ["healthy", "degraded", "unhealthy"]


async def test_health_status_version(client):
    """Test that version matches the configured app version."""
    response = await client.get("/api/v1/health/status")
    data = response.json()

    assert data["version"] == "2.0.0"


async def test_health_status_has_all_check_keys(client):
    """Test that all expected dependency checks are present."""
    response = await client.get("/api/v1/health/status")
    data = response.json()

    checks = data["checks"]
    expected_keys = {
        "database",
        "redis",
        "sharepoint",
        "fred_api",
        "census_api",
        "disk_space",
    }
    assert expected_keys == set(checks.keys())


async def test_health_status_database_check(client):
    """Test that database check reports status when DB is up."""
    response = await client.get("/api/v1/health/status")
    data = response.json()

    db_check = data["checks"]["database"]
    assert "status" in db_check
    # SQLite in-memory DB is always up (T-DEBT-023); PG health tested via conftest_pg
    assert db_check["status"] == "up"
    assert "latency_ms" in db_check
    assert isinstance(db_check["latency_ms"], (int, float))


async def test_health_status_healthy_when_db_up(client):
    """Test overall status is healthy when database is up."""
    response = await client.get("/api/v1/health/status")
    data = response.json()

    # SQLite in-memory always healthy (T-DEBT-023); may show "degraded" if Redis down
    assert data["status"] in ["healthy", "degraded"]
    assert data["checks"]["database"]["status"] == "up"


async def test_health_status_no_auth_required(client):
    """Test that the health endpoint does not require authentication."""
    # No auth headers — should still return 200
    response = await client.get("/api/v1/health/status")
    assert response.status_code == 200


async def test_health_status_disk_space_check(client):
    """Test that disk space check returns expected fields."""
    response = await client.get("/api/v1/health/status")
    data = response.json()

    disk = data["checks"]["disk_space"]
    assert "status" in disk
    assert disk["status"] in ["ok", "low", "error"]
    if disk["status"] != "error":
        assert "free_gb" in disk
        assert isinstance(disk["free_gb"], (int, float))


async def test_health_status_uptime_is_positive(client):
    """Test that uptime_seconds is a positive number."""
    response = await client.get("/api/v1/health/status")
    data = response.json()

    assert isinstance(data["uptime_seconds"], (int, float))
    assert data["uptime_seconds"] >= 0


async def test_health_status_timestamp_format(client):
    """Test that timestamp is a valid ISO 8601 string."""
    from datetime import datetime

    response = await client.get("/api/v1/health/status")
    data = response.json()

    # Should parse without error
    ts = datetime.fromisoformat(data["timestamp"])
    assert ts is not None


async def test_health_status_sharepoint_check(client):
    """Test that SharePoint check reflects auth status with last_checked timestamp."""
    response = await client.get("/api/v1/health/status")
    data = response.json()

    sp = data["checks"]["sharepoint"]
    assert sp["status"] in [
        "connected",
        "disconnected",
        "not_configured",
        "error",
        "degraded",
    ]
    assert "last_checked" in sp


async def test_health_status_api_keys_check(client):
    """Test that external API key checks are present."""
    response = await client.get("/api/v1/health/status")
    data = response.json()

    fred = data["checks"]["fred_api"]
    census = data["checks"]["census_api"]
    assert fred["status"] in ["configured", "not_configured"]
    assert census["status"] in ["configured", "not_configured"]
