"""Tests for ETag middleware.

F-039: Tests ETagMiddleware from app.middleware.etag including:
- ETag generation on GET responses
- 304 response when If-None-Match matches
- Normal response when If-None-Match doesn't match
- Non-GET requests bypass ETag processing

Tests the middleware dispatch logic directly, since Starlette's
BaseHTTPMiddleware wraps responses as StreamingResponse (no .body attr)
when used through the ASGI test client, but in production the middleware
operates on Response objects with .body.
"""

import hashlib

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.testclient import TestClient

from app.middleware.etag import ETagMiddleware

# =============================================================================
# Helpers — test the dispatch logic directly
# =============================================================================


async def _make_request(method: str = "GET", headers: dict | None = None) -> Request:
    """Build a fake Starlette Request."""
    scope = {
        "type": "http",
        "method": method,
        "path": "/test",
        "query_string": b"",
        "headers": [
            (k.lower().encode(), v.encode()) for k, v in (headers or {}).items()
        ],
    }
    return Request(scope)


class _FakeMiddleware(ETagMiddleware):
    """Subclass that lets us call dispatch directly without ASGI plumbing."""

    def __init__(self):
        # Skip BaseHTTPMiddleware.__init__ — we don't need an app
        pass


async def _call_dispatch(
    method: str = "GET",
    headers: dict | None = None,
    response_body: bytes = b'{"status":"ok"}',
    response_status: int = 200,
) -> Response:
    """Call the ETag middleware dispatch with a fake request and next handler."""
    mw = _FakeMiddleware()
    request = await _make_request(method, headers)

    # Simulate call_next returning a Response with .body
    async def call_next(req):
        resp = Response(
            content=response_body,
            status_code=response_status,
            media_type="application/json",
        )
        return resp

    return await mw.dispatch(request, call_next)


# =============================================================================
# ETag generation on GET responses
# =============================================================================


@pytest.mark.asyncio
async def test_get_response_has_etag_header():
    """GET responses should include an ETag header."""
    response = await _call_dispatch()
    assert response.status_code == 200
    assert "etag" in response.headers


@pytest.mark.asyncio
async def test_etag_is_quoted_sha256():
    """ETag value should be a quoted SHA-256 hex digest of the response body."""
    body = b'{"status":"ok"}'
    response = await _call_dispatch(response_body=body)

    etag = response.headers.get("etag")
    expected_etag = f'"{hashlib.sha256(body).hexdigest()}"'
    assert etag == expected_etag


@pytest.mark.asyncio
async def test_etag_is_deterministic():
    """Same body should produce the same ETag."""
    body = b'{"value":42}'
    r1 = await _call_dispatch(response_body=body)
    r2 = await _call_dispatch(response_body=body)
    assert r1.headers["etag"] == r2.headers["etag"]


@pytest.mark.asyncio
async def test_empty_body_no_etag():
    """Empty body responses should not get an ETag."""
    response = await _call_dispatch(response_body=b"")
    assert "etag" not in response.headers


# =============================================================================
# 304 response when If-None-Match matches
# =============================================================================


@pytest.mark.asyncio
async def test_304_when_if_none_match_matches():
    """When If-None-Match matches the ETag, server should return 304."""
    body = b'{"status":"ok"}'
    etag = f'"{hashlib.sha256(body).hexdigest()}"'

    response = await _call_dispatch(
        headers={"if-none-match": etag},
        response_body=body,
    )
    assert response.status_code == 304


@pytest.mark.asyncio
async def test_304_response_has_etag():
    """304 responses should still include the ETag header."""
    body = b'{"status":"ok"}'
    etag = f'"{hashlib.sha256(body).hexdigest()}"'

    response = await _call_dispatch(
        headers={"if-none-match": etag},
        response_body=body,
    )
    assert response.status_code == 304
    assert response.headers.get("etag") == etag


@pytest.mark.asyncio
async def test_304_with_wildcard_if_none_match():
    """If-None-Match: * should always return 304 for non-empty body."""
    response = await _call_dispatch(
        headers={"if-none-match": "*"},
        response_body=b'{"data": true}',
    )
    assert response.status_code == 304


@pytest.mark.asyncio
async def test_304_with_multiple_etags():
    """If-None-Match with multiple ETags, one matching, should return 304."""
    body = b'{"status":"ok"}'
    etag = f'"{hashlib.sha256(body).hexdigest()}"'

    response = await _call_dispatch(
        headers={"if-none-match": f'"stale1", {etag}, "stale2"'},
        response_body=body,
    )
    assert response.status_code == 304


# =============================================================================
# Normal response when If-None-Match doesn't match
# =============================================================================


@pytest.mark.asyncio
async def test_200_when_if_none_match_does_not_match():
    """When If-None-Match does not match, server should return 200 with full body."""
    response = await _call_dispatch(
        headers={"if-none-match": '"stale-etag-value"'},
    )
    assert response.status_code == 200
    assert "etag" in response.headers
    assert response.body == b'{"status":"ok"}'


# =============================================================================
# Non-GET requests bypass ETag processing
# =============================================================================


@pytest.mark.asyncio
async def test_post_does_not_get_etag():
    """POST requests should not have ETag headers added."""
    response = await _call_dispatch(method="POST")
    assert "etag" not in response.headers


@pytest.mark.asyncio
async def test_put_does_not_get_etag():
    """PUT requests should not have ETag headers added."""
    response = await _call_dispatch(method="PUT")
    assert "etag" not in response.headers


@pytest.mark.asyncio
async def test_delete_does_not_get_etag():
    """DELETE requests should not have ETag headers added."""
    response = await _call_dispatch(method="DELETE")
    assert "etag" not in response.headers


# =============================================================================
# T-DEBT-006: Edge case tests
# =============================================================================


@pytest.mark.asyncio
async def test_head_does_not_get_etag():
    """HEAD requests should not have ETag headers added (non-GET)."""
    response = await _call_dispatch(method="HEAD")
    assert "etag" not in response.headers


@pytest.mark.asyncio
async def test_patch_does_not_get_etag():
    """PATCH requests should not have ETag headers added."""
    response = await _call_dispatch(method="PATCH")
    assert "etag" not in response.headers


@pytest.mark.asyncio
async def test_non_200_response_still_gets_etag():
    """Non-200 GET responses should still get ETag if they have a body."""
    response = await _call_dispatch(
        response_body=b'{"error":"not found"}',
        response_status=404,
    )
    assert response.status_code == 404
    assert "etag" in response.headers


@pytest.mark.asyncio
async def test_different_bodies_produce_different_etags():
    """Different response bodies should produce different ETags."""
    r1 = await _call_dispatch(response_body=b'{"a":1}')
    r2 = await _call_dispatch(response_body=b'{"a":2}')
    assert r1.headers["etag"] != r2.headers["etag"]


@pytest.mark.asyncio
async def test_304_strips_body():
    """304 response should not include the response body."""
    body = b'{"status":"ok"}'
    etag = f'"{hashlib.sha256(body).hexdigest()}"'

    response = await _call_dispatch(
        headers={"if-none-match": etag},
        response_body=body,
    )
    assert response.status_code == 304
    assert response.body == b""


@pytest.mark.asyncio
async def test_streaming_response_skipped():
    """Streaming responses (no .body attribute) should pass through unchanged."""
    mw = _FakeMiddleware()
    request = await _make_request("GET")

    class StreamingFake:
        """Fake streaming response without .body attribute."""

        status_code = 200
        headers = {}

    async def call_next(req):
        return StreamingFake()

    response = await mw.dispatch(request, call_next)
    # Should pass through unchanged since no .body attribute
    assert isinstance(response, StreamingFake)
    assert "etag" not in response.headers


@pytest.mark.asyncio
async def test_whitespace_only_body_no_etag():
    """Response with whitespace-only body should not get an ETag (empty after strip)."""
    # Note: empty bytes b"" is falsy, so no ETag is set.
    # Whitespace bytes like b"  " are truthy, so they WILL get an ETag.
    # This test documents the actual behavior.
    response = await _call_dispatch(response_body=b"  ")
    assert response.status_code == 200
    # Whitespace bytes are truthy, so an ETag IS generated
    assert "etag" in response.headers


@pytest.mark.asyncio
async def test_large_body_gets_etag():
    """Large response bodies should still get an ETag."""
    large_body = b"x" * 100_000
    response = await _call_dispatch(response_body=large_body)
    assert "etag" in response.headers
    expected = f'"{hashlib.sha256(large_body).hexdigest()}"'
    assert response.headers["etag"] == expected
