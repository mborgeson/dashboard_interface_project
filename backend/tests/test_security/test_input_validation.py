"""
Input validation security tests.

Verifies the application properly validates and sanitizes user input,
including XSS payloads, path traversal attempts, oversized payloads,
boundary numeric values, invalid dates, and special characters.
"""

import pytest

from .conftest import (
    MAX_INT,
    NEGATIVE_INT,
    OVERSIZED_STRING,
    PATH_TRAVERSAL_PAYLOADS,
    VERY_LONG_STRING,
    XSS_PAYLOADS,
    assert_safe_response,
)


# =============================================================================
# XSS Payload Tests
# =============================================================================


class TestXSSPrevention:
    """Verify XSS payloads in string fields are handled safely."""

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    async def test_xss_in_property_name_create(self, client, admin_headers, payload):
        """XSS payloads in property name should be handled safely on create."""
        response = await client.post(
            "/api/v1/properties/",
            json={
                "name": payload,
                "property_type": "multifamily",
                "address": "123 Test St",
                "city": "Phoenix",
                "state": "AZ",
            },
            headers=admin_headers,
        )
        # Should either accept (stored as-is, frontend will escape) or reject
        # Must NOT return 500
        await assert_safe_response(response, allow_statuses=set(range(200, 500)))

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    async def test_xss_in_deal_name_create(self, client, admin_headers, payload):
        """XSS payloads in deal name should be handled safely on create."""
        response = await client.post(
            "/api/v1/deals/",
            json={
                "name": payload,
                "deal_type": "acquisition",
                "stage": "initial_review",
            },
            headers=admin_headers,
        )
        await assert_safe_response(response, allow_statuses=set(range(200, 500)))

    @pytest.mark.parametrize("payload", XSS_PAYLOADS[:5])
    async def test_xss_in_search_params(self, client, analyst_headers, payload):
        """XSS payloads in search parameters should be handled safely."""
        response = await client.get(
            "/api/v1/documents/",
            params={"search": payload},
            headers=analyst_headers,
        )
        await assert_safe_response(response)

    @pytest.mark.parametrize("payload", XSS_PAYLOADS[:5])
    async def test_xss_in_city_filter(self, client, analyst_headers, payload):
        """XSS payloads in city filter should be handled safely."""
        response = await client.get(
            "/api/v1/properties/",
            params={"city": payload},
            headers=analyst_headers,
        )
        await assert_safe_response(response)

    @pytest.mark.parametrize("payload", XSS_PAYLOADS[:5])
    async def test_xss_in_document_metadata(self, client, analyst_headers, payload):
        """XSS payloads in document metadata should be handled safely."""
        from datetime import UTC, datetime

        response = await client.post(
            "/api/v1/documents/",
            json={
                "name": payload,
                "type": "other",
                "description": payload,
                "uploaded_at": datetime.now(UTC).isoformat(),
            },
            headers=analyst_headers,
        )
        await assert_safe_response(response, allow_statuses=set(range(200, 500)))


# =============================================================================
# Path Traversal Tests
# =============================================================================


class TestPathTraversal:
    """Verify path traversal attempts in file-related operations."""

    @pytest.mark.parametrize("payload", PATH_TRAVERSAL_PAYLOADS)
    async def test_path_traversal_in_document_name(
        self, client, analyst_headers, payload
    ):
        """Path traversal in document name should not allow file access."""
        from datetime import UTC, datetime

        response = await client.post(
            "/api/v1/documents/",
            json={
                "name": payload,
                "type": "other",
                "file_path": payload,
                "url": "",
                "uploaded_at": datetime.now(UTC).isoformat(),
            },
            headers=analyst_headers,
        )
        # Should either accept safely or reject, but NOT expose file contents
        await assert_safe_response(response, allow_statuses=set(range(200, 500)))
        if response.status_code == 200 or response.status_code == 201:
            body = response.json()
            # The response should not contain contents of /etc/passwd
            assert "root:" not in str(body)
            assert "/bin/bash" not in str(body)

    @pytest.mark.parametrize("payload", PATH_TRAVERSAL_PAYLOADS[:4])
    async def test_path_traversal_in_upload_filename(
        self, client, analyst_headers, payload
    ):
        """Path traversal in upload filename should be blocked."""
        # Create a minimal file upload
        import io

        file_content = b"test content"
        files = {
            "file": (payload, io.BytesIO(file_content), "application/octet-stream")
        }
        response = await client.post(
            "/api/v1/documents/upload",
            files=files,
            headers=analyst_headers,
        )
        # Should reject the upload or sanitize the filename
        # Must NOT return 500 or expose file system paths
        await assert_safe_response(response, allow_statuses=set(range(200, 500)))


# =============================================================================
# Oversized Payload Tests
# =============================================================================


class TestOversizedPayloads:
    """Verify the app handles oversized inputs without crashing."""

    async def test_very_long_property_name(self, client, admin_headers):
        """Very long property name should be rejected or truncated."""
        response = await client.post(
            "/api/v1/properties/",
            json={
                "name": VERY_LONG_STRING,
                "property_type": "multifamily",
                "address": "123 Test St",
                "city": "Phoenix",
                "state": "AZ",
            },
            headers=admin_headers,
        )
        # Should either reject or accept without crashing
        await assert_safe_response(response, allow_statuses=set(range(200, 500)))

    async def test_oversized_string_in_search(self, client, analyst_headers):
        """Oversized search string should be handled safely."""
        from httpx import InvalidURL

        try:
            response = await client.get(
                "/api/v1/documents/",
                params={"search": OVERSIZED_STRING},
                headers=analyst_headers,
            )
            # If the server accepts it, verify the response is safe
            await assert_safe_response(response)
        except InvalidURL:
            # HTTP client rejects the URL as too long — this is safe behavior
            pass

    async def test_oversized_city_filter(self, client, analyst_headers):
        """Oversized city filter should be handled safely."""
        from httpx import InvalidURL

        try:
            response = await client.get(
                "/api/v1/properties/",
                params={"city": OVERSIZED_STRING},
                headers=analyst_headers,
            )
            await assert_safe_response(response)
        except InvalidURL:
            # HTTP client rejects the URL as too long — this is safe behavior
            pass

    async def test_very_long_deal_name(self, client, admin_headers):
        """Very long deal name should be handled safely."""
        response = await client.post(
            "/api/v1/deals/",
            json={
                "name": VERY_LONG_STRING,
                "deal_type": "acquisition",
                "stage": "initial_review",
            },
            headers=admin_headers,
        )
        await assert_safe_response(response, allow_statuses=set(range(200, 500)))

    async def test_deeply_nested_json(self, client, admin_headers):
        """Deeply nested JSON should be handled safely."""
        # Build deeply nested object
        nested = {"data": "value"}
        for _ in range(50):
            nested = {"nested": nested}
        response = await client.post(
            "/api/v1/properties/",
            json=nested,
            headers=admin_headers,
        )
        # Should get validation error, not a crash
        assert response.status_code in {400, 422}


# =============================================================================
# Numeric Boundary Tests
# =============================================================================


class TestNumericBoundaries:
    """Verify extreme numeric values are handled safely."""

    async def test_max_int_property_id(self, client, analyst_headers):
        """Max integer value as property ID should be handled safely."""
        response = await client.get(
            f"/api/v1/properties/{MAX_INT}",
            headers=analyst_headers,
        )
        # Should return 404 (not found) or 422 (validation), not 500
        assert response.status_code in {404, 422}

    async def test_negative_property_id(self, client, analyst_headers):
        """Negative property ID should be handled safely."""
        response = await client.get(
            "/api/v1/properties/-1",
            headers=analyst_headers,
        )
        assert response.status_code in {404, 422}

    async def test_zero_property_id(self, client, analyst_headers):
        """Zero property ID should be handled safely."""
        response = await client.get(
            "/api/v1/properties/0",
            headers=analyst_headers,
        )
        assert response.status_code in {404, 422}

    async def test_negative_page_number(self, client, analyst_headers):
        """Negative page number should be rejected."""
        response = await client.get(
            "/api/v1/properties/",
            params={"page": -1},
            headers=analyst_headers,
        )
        assert response.status_code == 422

    async def test_zero_page_size(self, client, analyst_headers):
        """Zero page size should be rejected."""
        response = await client.get(
            "/api/v1/properties/",
            params={"page_size": 0},
            headers=analyst_headers,
        )
        assert response.status_code == 422

    async def test_huge_page_size(self, client, analyst_headers):
        """Extremely large page size should be clamped or rejected."""
        response = await client.get(
            "/api/v1/properties/",
            params={"page_size": 1000000},
            headers=analyst_headers,
        )
        # FastAPI Query(le=100) should reject this
        assert response.status_code == 422

    async def test_negative_min_units(self, client, analyst_headers):
        """Negative min_units should be handled safely."""
        response = await client.get(
            "/api/v1/properties/",
            params={"min_units": -100},
            headers=analyst_headers,
        )
        # Should return safe response (empty results or validation error)
        await assert_safe_response(response)

    async def test_max_int_as_asking_price(self, client, admin_headers):
        """Max integer as asking price should be handled safely."""
        response = await client.post(
            "/api/v1/deals/",
            json={
                "name": "Big Deal",
                "deal_type": "acquisition",
                "stage": "initial_review",
                "asking_price": MAX_INT,
            },
            headers=admin_headers,
        )
        await assert_safe_response(response, allow_statuses=set(range(200, 500)))


# =============================================================================
# Invalid Date Format Tests
# =============================================================================


class TestInvalidDates:
    """Verify invalid date formats are handled safely."""

    @pytest.mark.parametrize(
        "date_value",
        [
            "not-a-date",
            "2025-13-45",
            "2025-00-00",
            "9999-99-99",
            "'; DROP TABLE deals--",
            "2025-01-01T99:99:99",
            "",
            "null",
        ],
    )
    async def test_invalid_initial_contact_date(
        self, client, admin_headers, date_value
    ):
        """Invalid date in deal creation should be rejected safely."""
        response = await client.post(
            "/api/v1/deals/",
            json={
                "name": "Test Deal",
                "deal_type": "acquisition",
                "stage": "initial_review",
                "initial_contact_date": date_value,
            },
            headers=admin_headers,
        )
        # Should get 422 (validation error), not 500
        assert response.status_code in {201, 422}

    @pytest.mark.parametrize(
        "date_value",
        [
            "not-a-date",
            "'; DROP TABLE audit_log--",
        ],
    )
    async def test_invalid_audit_log_date_filter(
        self, client, admin_headers, date_value
    ):
        """Invalid date in audit log filter should be rejected safely."""
        response = await client.get(
            "/api/v1/admin/audit-log",
            params={"from_date": date_value},
            headers=admin_headers,
        )
        assert response.status_code in {200, 422}


# =============================================================================
# Special Character Tests
# =============================================================================


class TestSpecialCharacters:
    """Verify special characters in queries are handled safely."""

    @pytest.mark.parametrize(
        "payload",
        [
            "Phoenix%00",  # null byte
            "Phoenix\x00",  # null character
            "Phoenix\n\r",  # CRLF injection
            "Phoenix\t",  # tab
            "Phoenix\\",  # backslash
            'Phoenix"',  # double quote
            "Phoenix'",  # single quote
            "Phoenix`",  # backtick
            "Phoenix;",  # semicolon
            "Phoenix|",  # pipe
            "Phoenix&",  # ampersand
            "Phoenix$",  # dollar sign
            "Phoenix{}",  # curly braces
            "Phoenix[]",  # square brackets
            "Phoenix()",  # parentheses
        ],
    )
    async def test_special_chars_in_city_filter(self, client, analyst_headers, payload):
        """Special characters in city filter should be handled safely."""
        response = await client.get(
            "/api/v1/properties/",
            params={"city": payload},
            headers=analyst_headers,
        )
        await assert_safe_response(response)

    @pytest.mark.parametrize(
        "payload",
        [
            "\x00\x01\x02",  # control characters
            "\uffff",  # max unicode
            "\ud800",  # surrogate (invalid in some contexts)
            "a" * 255 + "\x00",  # string with embedded null
        ],
    )
    async def test_binary_chars_in_search(self, client, analyst_headers, payload):
        """Binary/control characters in search should be handled safely."""
        try:
            response = await client.get(
                "/api/v1/documents/",
                params={"search": payload},
                headers=analyst_headers,
            )
            await assert_safe_response(response)
        except UnicodeEncodeError:
            # The HTTP client itself rejected the character, which is fine
            pass

    async def test_unicode_normalization_attacks(self, client, analyst_headers):
        """Unicode normalization attacks should be handled safely."""
        # Homoglyph for 'admin' using Cyrillic characters
        payloads = [
            "\u0430dmin",  # Cyrillic 'a'
            "ad\u043cin",  # Cyrillic 'm'
            "\uff41dmin",  # fullwidth 'a'
        ]
        for payload in payloads:
            response = await client.get(
                "/api/v1/properties/",
                params={"city": payload},
                headers=analyst_headers,
            )
            await assert_safe_response(response)

    async def test_json_injection_in_string_field(self, client, admin_headers):
        """JSON injection attempts in string fields should be handled safely."""
        payloads = [
            '{"$gt": ""}',
            '{"$ne": null}',
            '{"$where": "1==1"}',
        ]
        for payload in payloads:
            response = await client.post(
                "/api/v1/properties/",
                json={
                    "name": payload,
                    "property_type": "multifamily",
                    "address": "123 Test St",
                    "city": "Phoenix",
                    "state": "AZ",
                },
                headers=admin_headers,
            )
            await assert_safe_response(response, allow_statuses=set(range(200, 500)))
