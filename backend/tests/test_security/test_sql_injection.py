"""
SQL Injection security tests.

Verifies that all endpoints accepting user input properly use parameterized
queries and do not pass raw user input into SQL statements. Each test sends
common SQL injection payloads and verifies the app returns a safe response
(200 with filtered/empty results, or 400/422 validation error) rather than
a 500 error that could indicate SQL injection vulnerability.
"""

import pytest

from .conftest import (
    SQL_INJECTION_PAYLOADS,
    assert_safe_response,
    check_payloads_against_endpoint,
)


# =============================================================================
# Property Endpoint SQL Injection Tests
# =============================================================================


class TestPropertySQLInjection:
    """SQL injection tests against /api/v1/properties endpoints."""

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS[:7])
    async def test_city_filter_injection(self, client, analyst_headers, payload):
        """City filter parameter should not be injectable."""
        response = await client.get(
            "/api/v1/properties/",
            params={"city": payload},
            headers=analyst_headers,
        )
        await assert_safe_response(response)

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS[:7])
    async def test_state_filter_injection(self, client, analyst_headers, payload):
        """State filter parameter should not be injectable."""
        response = await client.get(
            "/api/v1/properties/",
            params={"state": payload},
            headers=analyst_headers,
        )
        await assert_safe_response(response)

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS[:7])
    async def test_property_type_filter_injection(self, client, analyst_headers, payload):
        """Property type filter should not be injectable."""
        response = await client.get(
            "/api/v1/properties/",
            params={"property_type": payload},
            headers=analyst_headers,
        )
        await assert_safe_response(response)

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS[:7])
    async def test_market_filter_injection(self, client, analyst_headers, payload):
        """Market filter parameter should not be injectable."""
        response = await client.get(
            "/api/v1/properties/",
            params={"market": payload},
            headers=analyst_headers,
        )
        await assert_safe_response(response)

    @pytest.mark.parametrize(
        "payload",
        [
            "name; DROP TABLE properties--",
            "name UNION SELECT 1--",
            "name' OR '1'='1",
            "created_at; DELETE FROM users--",
            "1 OR 1=1",
        ],
    )
    async def test_sort_by_injection(self, client, analyst_headers, payload):
        """sort_by parameter should not be injectable."""
        response = await client.get(
            "/api/v1/properties/",
            params={"sort_by": payload},
            headers=analyst_headers,
        )
        # Either returns safe results or a 400/422 validation error
        await assert_safe_response(response)

    @pytest.mark.parametrize(
        "payload",
        [
            "asc; DROP TABLE properties--",
            "desc' OR '1'='1",
            "asc UNION SELECT 1--",
        ],
    )
    async def test_sort_order_injection(self, client, analyst_headers, payload):
        """sort_order parameter should not be injectable."""
        response = await client.get(
            "/api/v1/properties/",
            params={"sort_order": payload},
            headers=analyst_headers,
        )
        await assert_safe_response(response)

    async def test_property_id_injection(self, client, analyst_headers):
        """Property ID path parameter should not be injectable."""
        # Path params are typed as int in FastAPI, so injection strings
        # should be rejected with 422
        response = await client.get(
            "/api/v1/properties/1%20OR%201%3D1",
            headers=analyst_headers,
        )
        # FastAPI will return 422 for non-integer path params
        assert response.status_code in {404, 422}

    async def test_cursor_pagination_injection(self, client, analyst_headers):
        """Cursor parameter should not be injectable."""
        payloads = [
            "'; DROP TABLE properties; --",
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9' UNION SELECT 1--",
            "../../etc/passwd",
        ]
        for payload in payloads:
            response = await client.get(
                "/api/v1/properties/cursor",
                params={"cursor": payload},
                headers=analyst_headers,
            )
            await assert_safe_response(response)


# =============================================================================
# Deal Endpoint SQL Injection Tests
# =============================================================================


class TestDealSQLInjection:
    """SQL injection tests against /api/v1/deals endpoints."""

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS[:7])
    async def test_stage_filter_injection(self, client, analyst_headers, payload):
        """Deal stage filter should not be injectable."""
        response = await client.get(
            "/api/v1/deals/",
            params={"stage": payload},
            headers=analyst_headers,
        )
        await assert_safe_response(response)

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS[:7])
    async def test_deal_type_filter_injection(self, client, analyst_headers, payload):
        """Deal type filter should not be injectable."""
        response = await client.get(
            "/api/v1/deals/",
            params={"deal_type": payload},
            headers=analyst_headers,
        )
        await assert_safe_response(response)

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS[:7])
    async def test_priority_filter_injection(self, client, analyst_headers, payload):
        """Priority filter should not be injectable."""
        response = await client.get(
            "/api/v1/deals/",
            params={"priority": payload},
            headers=analyst_headers,
        )
        await assert_safe_response(response)

    @pytest.mark.parametrize(
        "payload",
        [
            "created_at; DROP TABLE deals--",
            "name' OR '1'='1",
            "1 UNION SELECT * FROM users--",
        ],
    )
    async def test_deal_sort_by_injection(self, client, analyst_headers, payload):
        """Deal sort_by parameter should not be injectable."""
        response = await client.get(
            "/api/v1/deals/",
            params={"sort_by": payload},
            headers=analyst_headers,
        )
        await assert_safe_response(response)


# =============================================================================
# Document Endpoint SQL Injection Tests
# =============================================================================


class TestDocumentSQLInjection:
    """SQL injection tests against /api/v1/documents endpoints."""

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS[:7])
    async def test_search_injection(self, client, analyst_headers, payload):
        """Document search parameter should not be injectable."""
        response = await client.get(
            "/api/v1/documents/",
            params={"search": payload},
            headers=analyst_headers,
        )
        await assert_safe_response(response)

    @pytest.mark.parametrize(
        "payload",
        [
            "uploaded_at; DROP TABLE documents--",
            "name' UNION SELECT 1,2,3--",
        ],
    )
    async def test_document_sort_injection(self, client, analyst_headers, payload):
        """Document sort_by parameter should not be injectable."""
        response = await client.get(
            "/api/v1/documents/",
            params={"sort_by": payload},
            headers=analyst_headers,
        )
        await assert_safe_response(response)


# =============================================================================
# User Endpoint SQL Injection Tests
# =============================================================================


class TestUserSQLInjection:
    """SQL injection tests against /api/v1/users endpoints."""

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS[:5])
    async def test_role_filter_injection(self, client, admin_headers, payload):
        """User role filter should not be injectable."""
        response = await client.get(
            "/api/v1/users/",
            params={"role": payload},
            headers=admin_headers,
        )
        await assert_safe_response(response)

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS[:5])
    async def test_department_filter_injection(self, client, admin_headers, payload):
        """User department filter should not be injectable."""
        response = await client.get(
            "/api/v1/users/",
            params={"department": payload},
            headers=admin_headers,
        )
        await assert_safe_response(response)


# =============================================================================
# Auth Endpoint SQL Injection Tests
# =============================================================================


class TestAuthSQLInjection:
    """SQL injection tests against /api/v1/auth endpoints."""

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS[:7])
    async def test_login_username_injection(self, client, payload):
        """Login username field should not be injectable."""
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": payload, "password": "anything"},
        )
        # Should get 401 (invalid credentials), NOT 500
        assert response.status_code in {401, 422}
        await assert_safe_response(response, allow_statuses={401, 422})

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS[:7])
    async def test_login_password_injection(self, client, payload):
        """Login password field should not be injectable."""
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": payload},
        )
        # Should get 401 (invalid credentials), NOT 500
        assert response.status_code in {401, 422}
        await assert_safe_response(response, allow_statuses={401, 422})


# =============================================================================
# Analytics/Admin SQL Injection Tests
# =============================================================================


class TestAnalyticsSQLInjection:
    """SQL injection tests for analytics and admin endpoints."""

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS[:5])
    async def test_audit_log_action_filter_injection(self, client, admin_headers, payload):
        """Audit log action filter should not be injectable."""
        response = await client.get(
            "/api/v1/admin/audit-log",
            params={"action": payload},
            headers=admin_headers,
        )
        await assert_safe_response(response)

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS[:5])
    async def test_audit_log_resource_type_injection(self, client, admin_headers, payload):
        """Audit log resource_type filter should not be injectable."""
        response = await client.get(
            "/api/v1/admin/audit-log",
            params={"resource_type": payload},
            headers=admin_headers,
        )
        await assert_safe_response(response)


# =============================================================================
# Batch injection test using helper
# =============================================================================


class TestBatchSQLInjection:
    """Batch test: run all payloads against key endpoints."""

    async def test_all_payloads_properties_city(self, client, analyst_headers):
        """All SQL injection payloads against properties city filter."""
        await check_payloads_against_endpoint(
            client,
            "get",
            "/api/v1/properties/",
            SQL_INJECTION_PAYLOADS,
            param_name="city",
            headers=analyst_headers,
        )

    async def test_all_payloads_deals_stage(self, client, analyst_headers):
        """All SQL injection payloads against deals stage filter."""
        await check_payloads_against_endpoint(
            client,
            "get",
            "/api/v1/deals/",
            SQL_INJECTION_PAYLOADS,
            param_name="stage",
            headers=analyst_headers,
        )

    async def test_all_payloads_documents_search(self, client, analyst_headers):
        """All SQL injection payloads against documents search."""
        await check_payloads_against_endpoint(
            client,
            "get",
            "/api/v1/documents/",
            SQL_INJECTION_PAYLOADS,
            param_name="search",
            headers=analyst_headers,
        )
