"""
Tests for SecurityHeadersMiddleware and OriginValidationMiddleware.

CSRF ASSESSMENT (2026-03-09):
    This application uses JWT Bearer tokens stored in localStorage, sent via
    Authorization header. No cookies are used for authentication anywhere in
    the codebase. CSRF attacks require the browser to auto-attach credentials
    (cookies), which does not happen with localStorage + Bearer tokens.
    Therefore, traditional CSRF protection (double-submit cookies, synchronizer
    tokens) is NOT required.

    Instead, we implement defense-in-depth via:
    - Security response headers (X-Content-Type-Options, X-Frame-Options, etc.)
    - Origin validation on state-changing requests
    - Strict Content-Security-Policy
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def _no_auth_override():
    """Clear any auth overrides so we can test middleware independently."""
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


# =============================================================================
# Security Headers Tests
# =============================================================================


async def test_security_headers_present_on_root():
    """All security headers should be present on every response."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/")

    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["X-XSS-Protection"] == "0"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "geolocation=()" in resp.headers["Permissions-Policy"]
    assert "microphone=()" in resp.headers["Permissions-Policy"]
    assert "camera=()" in resp.headers["Permissions-Policy"]


async def test_content_security_policy_present():
    """CSP header should be set with restrictive directives."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/")

    csp = resp.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "script-src 'self'" in csp


async def test_cache_control_on_api_routes():
    """API responses should have no-store cache control."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Hit a known API route (even if it returns 401/404, headers are still set)
        resp = await ac.get("/api/v1/properties")

    assert "no-store" in resp.headers.get("Cache-Control", "")


async def test_no_cache_control_on_non_api_routes():
    """Non-API routes should not get the API cache-control header."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/")

    # Root endpoint is not under /api/, so Cache-Control should not be forced
    cache_control = resp.headers.get("Cache-Control", "")
    assert "no-store" not in cache_control


async def test_hsts_not_in_development():
    """HSTS should NOT be set in development environment."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/")

    # In test/dev environment, HSTS should be absent
    assert "Strict-Transport-Security" not in resp.headers


# =============================================================================
# Origin Validation Middleware Tests
# =============================================================================


async def test_post_with_allowed_origin_passes():
    """POST with a configured CORS origin should be allowed through."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/",
            headers={"Origin": "http://localhost:5173"},
        )

    # Should not be 403 (may be 404 or 405, that's fine — not blocked by origin)
    assert resp.status_code != 403


async def test_post_with_disallowed_origin_rejected():
    """POST from an unknown origin should be rejected with 403."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/properties",
            headers={"Origin": "https://evil-site.com"},
            json={},
        )

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Origin not allowed"


async def test_put_with_disallowed_origin_rejected():
    """PUT from an unknown origin should be rejected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.put(
            "/api/v1/properties/1",
            headers={"Origin": "https://evil-site.com"},
            json={},
        )

    assert resp.status_code == 403


async def test_delete_with_disallowed_origin_rejected():
    """DELETE from an unknown origin should be rejected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.delete(
            "/api/v1/properties/1",
            headers={"Origin": "https://evil-site.com"},
        )

    assert resp.status_code == 403


async def test_get_with_disallowed_origin_allowed():
    """GET requests should NOT be blocked even from unknown origins (safe method)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/",
            headers={"Origin": "https://evil-site.com"},
        )

    # GET is not a state-changing method, should pass through
    assert resp.status_code != 403


async def test_post_without_origin_allowed():
    """POST without Origin header (server-to-server, curl) should be allowed."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/properties",
            json={},
            # No Origin header
        )

    # Should not be blocked by origin validation (may be 401/422, not 403)
    assert resp.status_code != 403


async def test_post_with_allowed_referer_passes():
    """POST with Referer from allowed origin (no Origin header) should pass."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/properties",
            headers={"Referer": "http://localhost:5173/deals/new"},
            json={},
        )

    # Referer origin matches allowed list, should not be 403
    assert resp.status_code != 403


async def test_post_with_disallowed_referer_rejected():
    """POST with Referer from disallowed origin should be rejected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/properties",
            headers={"Referer": "https://evil-site.com/attack"},
            json={},
        )

    assert resp.status_code == 403
