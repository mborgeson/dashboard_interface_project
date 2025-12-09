"""Tests for health check endpoints."""
import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """Test the health check endpoint returns 200."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "ok"]


@pytest.mark.asyncio
async def test_root_redirect_or_docs(client):
    """Test root path behavior."""
    response = await client.get("/", follow_redirects=False)
    # Either redirect to docs or return some response
    assert response.status_code in [200, 301, 302, 307, 308, 404]
