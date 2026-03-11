"""Tests for deep health / readiness check endpoint (A-TD-026).

Covers:
- /health/status/ready endpoint response format
- Ready status when database is up
- 503 response when database is down
- No authentication required
"""

from unittest.mock import AsyncMock, patch

import pytest


async def test_readiness_returns_200_when_db_up(client):
    """Readiness endpoint should return 200 when database is reachable."""
    response = await client.get("/api/v1/health/status/ready")
    assert response.status_code == 200


async def test_readiness_response_format(client):
    """Readiness response should contain ready, checks, and timestamp."""
    response = await client.get("/api/v1/health/status/ready")
    data = response.json()

    assert "ready" in data
    assert "checks" in data
    assert "timestamp" in data
    assert isinstance(data["ready"], bool)


async def test_readiness_checks_database_and_redis(client):
    """Readiness checks should include database and redis."""
    response = await client.get("/api/v1/health/status/ready")
    data = response.json()

    checks = data["checks"]
    assert "database" in checks
    assert "redis" in checks


async def test_readiness_ready_when_db_up(client):
    """ready should be True when database check is up."""
    response = await client.get("/api/v1/health/status/ready")
    data = response.json()

    assert data["ready"] is True
    assert data["checks"]["database"]["status"] == "up"


async def test_readiness_no_auth_required(client):
    """Readiness endpoint should not require authentication."""
    response = await client.get("/api/v1/health/status/ready")
    assert response.status_code == 200


async def test_readiness_database_latency_included(client):
    """Database check should include latency_ms when up."""
    response = await client.get("/api/v1/health/status/ready")
    data = response.json()

    db_check = data["checks"]["database"]
    if db_check["status"] == "up":
        assert "latency_ms" in db_check
        assert isinstance(db_check["latency_ms"], (int, float))


async def test_readiness_timestamp_is_iso(client):
    """Timestamp should be a valid ISO 8601 string."""
    from datetime import datetime

    response = await client.get("/api/v1/health/status/ready")
    data = response.json()

    ts = datetime.fromisoformat(data["timestamp"])
    assert ts is not None


async def test_readiness_503_when_db_down(client):
    """Readiness should return 503 when database is unreachable."""
    with patch(
        "app.api.v1.endpoints.health._check_database",
        new_callable=AsyncMock,
        return_value={"status": "down", "error": "connection refused"},
    ):
        response = await client.get("/api/v1/health/status/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["ready"] is False
    assert data["checks"]["database"]["status"] == "down"


async def test_readiness_ok_when_redis_not_configured(client):
    """Readiness should be True even if Redis is not configured."""
    response = await client.get("/api/v1/health/status/ready")
    data = response.json()

    # Redis not_installed or not_configured should not affect readiness
    redis_status = data["checks"]["redis"]["status"]
    assert redis_status in ("up", "down", "not_installed", "not_configured")
    assert data["ready"] is True
