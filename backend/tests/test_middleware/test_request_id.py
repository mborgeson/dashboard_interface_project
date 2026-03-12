"""
Tests for RequestIDMiddleware.

Verifies that every response includes an X-Request-ID header, that
client-provided IDs are echoed back, that auto-generated IDs are valid
UUID-4 values, and that each request gets a unique ID.
"""

import uuid

from httpx import ASGITransport, AsyncClient

from app.main import app

REQUEST_ID_HEADER = "X-Request-ID"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_valid_uuid4(value: str) -> bool:
    """Return True if *value* is a valid UUID-4 string."""
    try:
        parsed = uuid.UUID(value, version=4)
    except (ValueError, AttributeError):
        return False
    return str(parsed) == value


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_response_includes_request_id_header():
    """Every response must include an X-Request-ID header."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/")

    assert REQUEST_ID_HEADER in resp.headers


async def test_auto_generated_id_is_valid_uuid4():
    """When the client does not send X-Request-ID, the server generates a UUID-4."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/")

    rid = resp.headers[REQUEST_ID_HEADER]
    assert _is_valid_uuid4(rid), f"Expected valid UUID-4, got {rid!r}"


async def test_client_provided_id_is_echoed_back():
    """When the client sends X-Request-ID, the same value is returned."""
    client_id = "my-custom-correlation-id-12345"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/", headers={REQUEST_ID_HEADER: client_id})

    assert resp.headers[REQUEST_ID_HEADER] == client_id


async def test_each_request_gets_unique_id():
    """Two requests without a client ID should receive different IDs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp1 = await ac.get("/")
        resp2 = await ac.get("/")

    id1 = resp1.headers[REQUEST_ID_HEADER]
    id2 = resp2.headers[REQUEST_ID_HEADER]
    assert id1 != id2, f"Expected unique IDs, but both were {id1!r}"


async def test_request_id_on_api_route():
    """X-Request-ID should be present even on authenticated/API routes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # May return 401/403/404, but the header should still be set
        resp = await ac.get("/api/v1/properties")

    assert REQUEST_ID_HEADER in resp.headers
    assert len(resp.headers[REQUEST_ID_HEADER]) > 0


async def test_request_id_on_post_request():
    """X-Request-ID should work for POST requests too."""
    client_id = str(uuid.uuid4())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/",
            headers={
                REQUEST_ID_HEADER: client_id,
                "Origin": "http://localhost:5173",
            },
        )

    assert resp.headers[REQUEST_ID_HEADER] == client_id
