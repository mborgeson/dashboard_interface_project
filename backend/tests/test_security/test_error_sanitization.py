"""
Error sanitization security tests.

Verifies that error responses never contain internal details such as:
- File paths (/home/user/..., /app/...)
- SQL queries (SELECT, INSERT, etc.)
- Stack traces (Traceback, File, line)
- Internal hostnames or IPs
- Database library names (sqlalchemy, psycopg, etc.)

Also directly tests the _sanitize_error_message() function.
"""

import pytest

from app.middleware.error_handler import (
    _FALLBACK_MESSAGES,
    _INTERNAL_DETAIL_PATTERNS,
    _sanitize_error_message,
)

from .conftest import INTERNAL_INFO_PATTERNS, assert_safe_response


# =============================================================================
# Direct Unit Tests for _sanitize_error_message()
# =============================================================================


class TestSanitizeErrorMessage:
    """Unit tests for the _sanitize_error_message function."""

    def test_safe_message_passes_through(self):
        """A safe error message should pass through unchanged."""
        msg = "Property not found"
        result = _sanitize_error_message(msg, "value_error")
        assert result == msg

    def test_empty_message_returns_fallback(self):
        """Empty message should return the fallback for that error type."""
        result = _sanitize_error_message("", "value_error")
        assert result == _FALLBACK_MESSAGES["value_error"]

    def test_file_path_is_sanitized(self):
        """Message containing a file path should be sanitized."""
        messages = [
            "Error in /app/models/deal.py:42",
            "File not found: /home/user/secret.txt",
            "Failed at /backend/app/crud/property.py line 100",
        ]
        for msg in messages:
            result = _sanitize_error_message(msg, "value_error")
            assert result == _FALLBACK_MESSAGES["value_error"], (
                f"File path not sanitized: {msg!r} -> {result!r}"
            )

    def test_sql_query_is_sanitized(self):
        """Message containing SQL keywords should be sanitized."""
        messages = [
            "SELECT * FROM users WHERE id = 1",
            "INSERT INTO properties VALUES (1, 'test')",
            "UPDATE deals SET stage = 'closed' WHERE id = 1",
            "DELETE FROM extracted_values WHERE property_id = 5",
        ]
        for msg in messages:
            result = _sanitize_error_message(msg, "value_error")
            assert result == _FALLBACK_MESSAGES["value_error"], (
                f"SQL not sanitized: {msg!r} -> {result!r}"
            )

    def test_traceback_is_sanitized(self):
        """Message containing traceback info should be sanitized."""
        messages = [
            "Traceback (most recent call last):",
            "File \"/app/main.py\", line 42, in handle_request",
            "Error at 0x7f1234567890",
        ]
        for msg in messages:
            result = _sanitize_error_message(msg, "value_error")
            assert result == _FALLBACK_MESSAGES["value_error"], (
                f"Traceback not sanitized: {msg!r} -> {result!r}"
            )

    def test_database_library_is_sanitized(self):
        """Message containing database library names should be sanitized."""
        messages = [
            "sqlalchemy.exc.IntegrityError: duplicate key",
            "psycopg2.OperationalError: connection refused",
            "asyncpg.exceptions.UniqueViolationError",
            "sqlite3.OperationalError: no such table",
        ]
        for msg in messages:
            result = _sanitize_error_message(msg, "value_error")
            assert result == _FALLBACK_MESSAGES["value_error"], (
                f"DB library not sanitized: {msg!r} -> {result!r}"
            )

    def test_validation_error_type(self):
        """Validation error type should use its fallback."""
        result = _sanitize_error_message("", "validation_error")
        assert result == _FALLBACK_MESSAGES["validation_error"]

    def test_permission_error_type(self):
        """Permission error type should use its fallback."""
        result = _sanitize_error_message("", "permission_error")
        assert result == _FALLBACK_MESSAGES["permission_error"]

    def test_unknown_error_type_fallback(self):
        """Unknown error type should fall back to generic message."""
        result = _sanitize_error_message("", "unknown_error")
        assert result == "An error occurred"

    def test_line_number_reference_is_sanitized(self):
        """Messages containing .py:123 or 'line 42' should be sanitized."""
        messages = [
            "error in module.py:42",
            "raised at line 156 in handler",
        ]
        for msg in messages:
            result = _sanitize_error_message(msg, "value_error")
            assert result == _FALLBACK_MESSAGES["value_error"]


# =============================================================================
# Pattern Coverage Tests
# =============================================================================


class TestInternalDetailPatterns:
    """Verify all internal detail patterns match correctly."""

    @pytest.mark.parametrize(
        "text,should_match",
        [
            ("File \"/app/main.py\", line 42", True),
            ("Traceback (most recent call last)", True),
            ("at 0x7f4a3b2c1d0e", True),
            ("/app/models/deal.py", True),
            ("SELECT id FROM users", True),
            ("INSERT INTO properties", True),
            ("UPDATE deals SET", True),
            ("DELETE FROM tokens", True),
            ("FROM properties WHERE", True),
            ("WHERE id = 1", True),
            ("sqlalchemy.exc.IntegrityError", True),
            ("psycopg2.errors.UniqueViolation", True),
            ("asyncpg.exceptions.PostgresError", True),
            ("sqlite3.OperationalError", True),
            (".py:42", True),
            ("line 156", True),
            # Safe messages that should NOT match
            ("Property not found", False),
            ("Invalid email format", False),
            ("Deal 123 does not exist", False),
            ("Incorrect email or password", False),
        ],
    )
    def test_pattern_matching(self, text, should_match):
        """Verify each internal detail pattern matches as expected."""
        matched = any(p.search(text) for p in _INTERNAL_DETAIL_PATTERNS)
        assert matched == should_match, (
            f"Text {text!r}: expected match={should_match}, got {matched}"
        )


# =============================================================================
# Endpoint Error Response Tests
# =============================================================================


class TestEndpointErrorResponses:
    """Verify API error responses don't leak internal details."""

    async def test_invalid_property_id_error_is_clean(self, client, analyst_headers):
        """Property not-found error should be clean."""
        response = await client.get(
            "/api/v1/properties/99999",
            headers=analyst_headers,
        )
        assert response.status_code == 404
        body = response.json()
        detail = body.get("detail", "")
        # Should be a clean message like "Property 99999 not found"
        assert "SELECT" not in detail
        assert "sqlalchemy" not in detail.lower()
        assert ".py" not in detail

    async def test_invalid_deal_id_error_is_clean(self, client, analyst_headers):
        """Deal not-found error should be clean."""
        response = await client.get(
            "/api/v1/deals/99999",
            headers=analyst_headers,
        )
        assert response.status_code == 404
        body = response.json()
        detail = body.get("detail", "")
        assert "SELECT" not in detail
        assert "sqlalchemy" not in detail.lower()

    async def test_validation_error_is_clean(self, client, admin_headers):
        """Validation errors should not contain internal paths."""
        response = await client.post(
            "/api/v1/properties/",
            json={},  # Missing required fields
            headers=admin_headers,
        )
        assert response.status_code == 422
        body_str = str(response.json())
        assert "/home/" not in body_str
        assert "Traceback" not in body_str

    async def test_type_error_in_path_param_is_clean(self, client, analyst_headers):
        """Non-integer path parameter should return clean error."""
        response = await client.get(
            "/api/v1/properties/abc",
            headers=analyst_headers,
        )
        assert response.status_code == 422
        body_str = str(response.json())
        assert "Traceback" not in body_str
        assert "File " not in body_str

    async def test_method_not_allowed_is_clean(self, client, analyst_headers):
        """405 Method Not Allowed should be a clean response."""
        response = await client.patch(
            "/api/v1/properties/",
            json={},
            headers=analyst_headers,
        )
        assert response.status_code == 405
        await assert_safe_response(response, allow_statuses={405})

    async def test_missing_request_body_error_is_clean(self, client, admin_headers):
        """POST without body should return clean validation error."""
        response = await client.post(
            "/api/v1/deals/",
            headers=admin_headers,
        )
        assert response.status_code == 422
        body_str = str(response.json())
        assert "/app/" not in body_str
        assert "Traceback" not in body_str

    async def test_wrong_content_type_is_clean(self, client, admin_headers):
        """Sending wrong Content-Type should return clean error."""
        response = await client.post(
            "/api/v1/deals/",
            content="not json",
            headers={**admin_headers, "Content-Type": "text/plain"},
        )
        assert response.status_code in {400, 415, 422}
        await assert_safe_response(response, allow_statuses={400, 415, 422})


# =============================================================================
# No Internal IP/Hostname Leaks
# =============================================================================


class TestNoInternalInfoLeaks:
    """Verify responses don't contain internal infrastructure details."""

    async def test_error_response_no_internal_ips(self, client, analyst_headers):
        """Error responses should not contain internal IPs."""
        # Trigger a 404
        response = await client.get(
            "/api/v1/properties/99999",
            headers=analyst_headers,
        )
        body = response.text
        # Check for common internal IP patterns
        import re

        internal_ip_pattern = re.compile(
            r"(10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
            r"|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
            r"|192\.168\.\d{1,3}\.\d{1,3})"
        )
        match = internal_ip_pattern.search(body)
        assert match is None, f"Internal IP found in response: {match.group()}"

    async def test_error_response_no_hostname(self, client, analyst_headers):
        """Error responses should not contain server hostname."""
        import socket

        hostname = socket.gethostname()

        response = await client.get(
            "/api/v1/properties/99999",
            headers=analyst_headers,
        )
        body = response.text
        assert hostname not in body, (
            f"Server hostname '{hostname}' found in error response"
        )

    async def test_error_response_no_db_connection_string(self, client, analyst_headers):
        """Error responses should not contain database connection strings."""
        response = await client.get(
            "/api/v1/properties/99999",
            headers=analyst_headers,
        )
        body = response.text.lower()
        assert "postgresql://" not in body
        assert "sqlite:///" not in body
        assert "mysql://" not in body
        assert "redis://" not in body

    async def test_error_response_no_environment_variables(self, client, analyst_headers):
        """Error responses should not contain environment variable values."""
        response = await client.get(
            "/api/v1/properties/99999",
            headers=analyst_headers,
        )
        body = response.text
        # Check that the secret key is not exposed
        from app.core.config import settings

        if settings.SECRET_KEY and len(settings.SECRET_KEY) > 8:
            assert settings.SECRET_KEY not in body


# =============================================================================
# Comprehensive Error Code Coverage
# =============================================================================


class TestErrorCodeCoverage:
    """Verify common error status codes all return clean responses."""

    async def test_all_common_errors_are_clean(self, client, analyst_headers):
        """Test a range of error-inducing requests and verify all are clean."""
        test_cases = [
            # (description, method, url, expected_status)
            ("nonexistent property", "GET", "/api/v1/properties/99999", 404),
            ("nonexistent deal", "GET", "/api/v1/deals/99999", 404),
            ("invalid path param type", "GET", "/api/v1/properties/abc", 422),
        ]
        for desc, method, url, expected in test_cases:
            response = await client.request(method, url, headers=analyst_headers)
            assert response.status_code == expected, (
                f"Case '{desc}': expected {expected}, got {response.status_code}"
            )
            await assert_safe_response(
                response, allow_statuses={expected}
            )
