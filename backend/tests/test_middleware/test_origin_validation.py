"""
Tests for OriginValidationMiddleware (backend/app/main.py).

F-040: Covers allowed origin passes, disallowed origin rejected (403),
no origin header (non-browser) passes through, and only state-changing
methods (POST/PUT/PATCH/DELETE) are checked.
"""

from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import OriginValidationMiddleware

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://dashboard.bandrcapital.com",
]


def _create_test_app() -> FastAPI:
    """Create a minimal FastAPI app with OriginValidationMiddleware."""
    test_app = FastAPI()
    test_app.add_middleware(OriginValidationMiddleware)

    @test_app.get("/data")
    async def get_data():
        return {"ok": True}

    @test_app.post("/create")
    async def create_item():
        return {"created": True}

    @test_app.put("/update")
    async def update_item():
        return {"updated": True}

    @test_app.patch("/patch")
    async def patch_item():
        return {"patched": True}

    @test_app.delete("/remove")
    async def remove_item():
        return {"deleted": True}

    return test_app


# ---------------------------------------------------------------------------
# Allowed origin passes
# ---------------------------------------------------------------------------


@patch("app.core.config.settings.CORS_ORIGINS", ALLOWED_ORIGINS)
async def test_post_with_allowed_origin_passes():
    """POST with an allowed origin should succeed."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/create", headers={"Origin": "http://localhost:5173"}
        )
    assert resp.status_code == 200
    assert resp.json()["created"] is True


@patch("app.core.config.settings.CORS_ORIGINS", ALLOWED_ORIGINS)
async def test_put_with_allowed_origin_passes():
    """PUT with an allowed origin should succeed."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.put(
            "/update", headers={"Origin": "https://dashboard.bandrcapital.com"}
        )
    assert resp.status_code == 200


@patch("app.core.config.settings.CORS_ORIGINS", ALLOWED_ORIGINS)
async def test_patch_with_allowed_origin_passes():
    """PATCH with an allowed origin should succeed."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.patch(
            "/patch", headers={"Origin": "http://localhost:3000"}
        )
    assert resp.status_code == 200


@patch("app.core.config.settings.CORS_ORIGINS", ALLOWED_ORIGINS)
async def test_delete_with_allowed_origin_passes():
    """DELETE with an allowed origin should succeed."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.delete(
            "/remove", headers={"Origin": "http://localhost:5173"}
        )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Disallowed origin rejected (403)
# ---------------------------------------------------------------------------


@patch("app.core.config.settings.CORS_ORIGINS", ALLOWED_ORIGINS)
async def test_post_with_disallowed_origin_rejected():
    """POST from a disallowed origin returns 403."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/create", headers={"Origin": "https://evil.example.com"}
        )
    assert resp.status_code == 403
    assert "Origin not allowed" in resp.json()["detail"]


@patch("app.core.config.settings.CORS_ORIGINS", ALLOWED_ORIGINS)
async def test_put_with_disallowed_origin_rejected():
    """PUT from a disallowed origin returns 403."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.put(
            "/update", headers={"Origin": "https://evil.example.com"}
        )
    assert resp.status_code == 403


@patch("app.core.config.settings.CORS_ORIGINS", ALLOWED_ORIGINS)
async def test_delete_with_disallowed_origin_rejected():
    """DELETE from a disallowed origin returns 403."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.delete(
            "/remove", headers={"Origin": "https://evil.example.com"}
        )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# No origin header (non-browser request) passes through
# ---------------------------------------------------------------------------


@patch("app.core.config.settings.CORS_ORIGINS", ALLOWED_ORIGINS)
async def test_post_without_origin_passes():
    """POST without Origin header (e.g., curl, server-to-server) passes."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/create")
    assert resp.status_code == 200


@patch("app.core.config.settings.CORS_ORIGINS", ALLOWED_ORIGINS)
async def test_delete_without_origin_passes():
    """DELETE without Origin header passes through."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.delete("/remove")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Only state-changing methods (POST/PUT/PATCH/DELETE) are checked
# ---------------------------------------------------------------------------


@patch("app.core.config.settings.CORS_ORIGINS", ALLOWED_ORIGINS)
async def test_get_with_disallowed_origin_passes():
    """GET requests are not origin-checked, even from disallowed origins."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/data", headers={"Origin": "https://evil.example.com"}
        )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@patch("app.core.config.settings.CORS_ORIGINS", ALLOWED_ORIGINS)
async def test_get_without_origin_passes():
    """GET without Origin header passes normally."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/data")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Referer fallback
# ---------------------------------------------------------------------------


@patch("app.core.config.settings.CORS_ORIGINS", ALLOWED_ORIGINS)
async def test_referer_fallback_allowed():
    """When Origin is absent, Referer header is used as fallback."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/create",
            headers={"Referer": "http://localhost:5173/some/page"},
        )
    assert resp.status_code == 200


@patch("app.core.config.settings.CORS_ORIGINS", ALLOWED_ORIGINS)
async def test_referer_fallback_rejected():
    """When Origin is absent, a disallowed Referer is rejected."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/create",
            headers={"Referer": "https://evil.example.com/hack"},
        )
    assert resp.status_code == 403
