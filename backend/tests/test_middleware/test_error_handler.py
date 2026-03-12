"""
Tests for ErrorHandlerMiddleware.

Verifies that the middleware catches common exception types and returns
structured JSON error responses with request_id correlation.

T-DEBT-006: Edge cases for sanitization, empty messages, and concurrent errors.
"""

from unittest.mock import patch

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.middleware.error_handler import (
    ErrorHandlerMiddleware,
    _sanitize_error_message,
)
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

    @test_app.get("/value-error-with-path")
    async def value_error_with_path_endpoint():
        raise ValueError("Error in /app/models/deal.py:42")

    @test_app.get("/value-error-with-sql")
    async def value_error_with_sql_endpoint():
        raise ValueError("SELECT * FROM users WHERE id = 1")

    @test_app.get("/value-error-empty")
    async def value_error_empty_endpoint():
        raise ValueError("")

    @test_app.get("/permission-error-with-traceback")
    async def permission_error_with_traceback_endpoint():
        raise PermissionError("Traceback (most recent call last): File app.py line 10")

    @test_app.post("/post-error")
    async def post_error_endpoint():
        raise ValueError("POST also handled")

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


# =============================================================================
# T-DEBT-006: Edge case tests — sanitization, empty messages, POST errors
# =============================================================================


async def test_value_error_with_file_path_sanitized():
    """ValueError containing file paths should be sanitized."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/value-error-with-path")

    assert resp.status_code == 400
    body = resp.json()
    assert body["type"] == "value_error"
    # Internal file path should NOT appear in the response
    assert "/app/models/deal.py" not in body["detail"]
    assert (
        "line" not in body["detail"].lower()
        or "check your input" in body["detail"].lower()
    )


async def test_value_error_with_sql_sanitized():
    """ValueError containing SQL fragments should be sanitized."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/value-error-with-sql")

    assert resp.status_code == 400
    body = resp.json()
    # SQL should NOT be exposed to the client
    assert "SELECT" not in body["detail"]
    assert "check your input" in body["detail"].lower()


async def test_value_error_empty_message():
    """ValueError with empty string should use fallback message."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/value-error-empty")

    assert resp.status_code == 400
    body = resp.json()
    assert body["type"] == "value_error"
    # Empty message should be replaced with fallback
    assert len(body["detail"]) > 0
    assert "check your input" in body["detail"].lower()


async def test_permission_error_with_traceback_sanitized():
    """PermissionError containing traceback info should be sanitized."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/permission-error-with-traceback")

    assert resp.status_code == 403
    body = resp.json()
    # Traceback should NOT be exposed
    assert "Traceback" not in body["detail"]
    assert "most recent call" not in body["detail"].lower()


async def test_post_request_error_handled():
    """Errors on POST requests should also be caught by middleware."""
    app = _create_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/post-error")

    assert resp.status_code == 400
    body = resp.json()
    assert body["type"] == "value_error"
    assert "request_id" in body


# =============================================================================
# T-DEBT-006: Unit tests for _sanitize_error_message
# =============================================================================


def test_sanitize_safe_message():
    """Safe messages should pass through unchanged."""
    assert (
        _sanitize_error_message("Invalid email format", "value_error")
        == "Invalid email format"
    )


def test_sanitize_empty_message():
    """Empty message should return fallback."""
    result = _sanitize_error_message("", "value_error")
    assert "check your input" in result.lower()


def test_sanitize_file_path_message():
    """Messages with file paths should be replaced with fallback."""
    result = _sanitize_error_message(
        "Error in /app/models/deal.py at line 42", "value_error"
    )
    assert "/app/" not in result
    assert "check your input" in result.lower()


def test_sanitize_sql_message():
    """Messages with SQL fragments should be replaced with fallback."""
    result = _sanitize_error_message(
        "SELECT id FROM properties WHERE name = 'test'", "value_error"
    )
    assert "SELECT" not in result


def test_sanitize_traceback_message():
    """Messages with traceback indicators should be replaced with fallback."""
    result = _sanitize_error_message(
        "Traceback (most recent call last):\n  File app.py", "value_error"
    )
    assert "Traceback" not in result


def test_sanitize_unknown_error_type():
    """Unknown error type should use generic fallback."""
    result = _sanitize_error_message("", "unknown_type")
    assert result == "An error occurred"


@pytest.mark.parametrize(
    "message",
    [
        "psycopg2.OperationalError: connection refused",
        "sqlalchemy.exc.IntegrityError: duplicate key",
        "asyncpg.exceptions.ConnectionDoesNotExistError",
        "sqlite3.OperationalError: table not found",
    ],
)
def test_sanitize_db_library_messages(message):
    """Messages mentioning database libraries should be sanitized."""
    result = _sanitize_error_message(message, "value_error")
    # None of the db library names should appear in the sanitized output
    assert "psycopg" not in result
    assert "sqlalchemy" not in result.lower()
    assert "asyncpg" not in result
    assert "sqlite3" not in result
