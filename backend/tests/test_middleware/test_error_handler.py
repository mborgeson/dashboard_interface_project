"""
Tests for ErrorHandlerMiddleware.

Verifies that the middleware catches common exception types and returns
structured JSON error responses with request_id correlation.
"""

from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.request_id import RequestIDMiddleware

REQUEST_ID_HEADER = "X-Request-ID"


def _create_test_app() -> FastAPI:
    """Create a minimal FastAPI app with error handler + request ID middleware."""
    test_app = FastAPI()

    # Register middleware (order matters: last added = outermost on request path)
    test_app.add_middleware(ErrorHandlerMiddleware)
    test_app.add_middleware(RequestIDMiddleware)

    @test_app.get("/ok")
    async def ok_endpoint():
        return {"status": "ok"}

    @test_app.get("/http-exception")
    async def http_exception_endpoint():
        raise HTTPException(status_code=404, detail="Not found")

    @test_app.get("/sqlalchemy-error")
    async def sqlalchemy_error_endpoint():
        raise SQLAlchemyError("connection refused")

    @test_app.get("/validation-error")
    async def validation_error_endpoint():
        # Trigger a real Pydantic ValidationError
        class StrictModel(BaseModel):
            value: int

        StrictModel.model_validate({"value": "not-an-int"})

    @test_app.get("/permission-error")
    async def permission_error_endpoint():
        raise PermissionError("Insufficient privileges")

    @test_app.get("/value-error")
    async def value_error_endpoint():
        raise ValueError("Invalid input value")

    @test_app.get("/generic-error")
    async def generic_error_endpoint():
        raise RuntimeError("Something broke unexpectedly")

    return test_app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_successful_request_passes_through():
    """Normal responses should pass through the middleware unchanged."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/ok")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_http_exception_passes_through():
    """HTTPExceptions should be handled by FastAPI, not the middleware."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/http-exception")

    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"] == "Not found"


async def test_sqlalchemy_error_returns_500():
    """SQLAlchemy errors should return 500 with database_error type."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/sqlalchemy-error")

    assert resp.status_code == 500
    body = resp.json()
    assert body["type"] == "database_error"
    assert "database error" in body["detail"].lower()
    assert "request_id" in body
    assert len(body["request_id"]) > 0


async def test_sqlalchemy_error_includes_request_id():
    """SQLAlchemy error responses should include the request_id from the request."""
    app = _create_test_app()
    custom_rid = "test-correlation-id-123"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/sqlalchemy-error",
            headers={REQUEST_ID_HEADER: custom_rid},
        )

    assert resp.status_code == 500
    body = resp.json()
    assert body["request_id"] == custom_rid


async def test_validation_error_returns_422():
    """Pydantic ValidationErrors should return 422 with validation_error type."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/validation-error")

    assert resp.status_code == 422
    body = resp.json()
    assert body["type"] == "validation_error"
    assert "request_id" in body


async def test_permission_error_returns_403():
    """PermissionError should return 403 with permission_error type."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/permission-error")

    assert resp.status_code == 403
    body = resp.json()
    assert body["type"] == "permission_error"
    assert "Insufficient privileges" in body["detail"]
    assert "request_id" in body


async def test_value_error_returns_400():
    """ValueError should return 400 with value_error type."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/value-error")

    assert resp.status_code == 400
    body = resp.json()
    assert body["type"] == "value_error"
    assert "Invalid input value" in body["detail"]
    assert "request_id" in body


async def test_generic_exception_returns_500():
    """Unhandled exceptions should return 500 with internal_error type."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/generic-error")

    assert resp.status_code == 500
    body = resp.json()
    assert body["type"] == "internal_error"
    assert body["detail"] == "An unexpected error occurred"
    assert "request_id" in body


async def test_error_response_includes_request_id_from_header():
    """All error responses should include the client-provided request_id."""
    app = _create_test_app()
    custom_rid = "my-custom-rid-456"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/generic-error",
            headers={REQUEST_ID_HEADER: custom_rid},
        )

    body = resp.json()
    assert body["request_id"] == custom_rid


async def test_error_response_has_auto_generated_request_id():
    """When no X-Request-ID header is sent, the response should still have a request_id."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/value-error")

    body = resp.json()
    assert "request_id" in body
    # Should be a UUID or at least non-empty
    assert len(body["request_id"]) > 0


async def test_error_response_json_structure():
    """All error responses should have the standard structure: detail, request_id, type."""
    app = _create_test_app()
    transport = ASGITransport(app=app)

    error_endpoints = [
        ("/sqlalchemy-error", 500, "database_error"),
        ("/permission-error", 403, "permission_error"),
        ("/value-error", 400, "value_error"),
        ("/generic-error", 500, "internal_error"),
    ]

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        for path, expected_status, expected_type in error_endpoints:
            resp = await ac.get(path)
            assert resp.status_code == expected_status, f"Wrong status for {path}"
            body = resp.json()
            assert "detail" in body, f"Missing 'detail' for {path}"
            assert "request_id" in body, f"Missing 'request_id' for {path}"
            assert "type" in body, f"Missing 'type' for {path}"
            assert body["type"] == expected_type, f"Wrong type for {path}"
