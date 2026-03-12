"""
Authorization security tests.

Verifies that:
- Protected endpoints return 401 without auth
- Role hierarchies are enforced (analyst, manager, admin)
- Users cannot access resources they don't own (IDOR)
- Error messages don't leak sensitive information
"""

import pytest

from app.core.security import create_access_token

from .conftest import INTERNAL_INFO_PATTERNS, assert_safe_response

# =============================================================================
# Unauthenticated Access Tests
# =============================================================================


class TestUnauthenticatedAccess:
    """Verify all protected endpoints return 401 without auth."""

    @pytest.mark.parametrize(
        "method,endpoint",
        [
            # Properties (require analyst)
            ("GET", "/api/v1/properties/"),
            ("GET", "/api/v1/properties/dashboard"),
            ("GET", "/api/v1/properties/summary"),
            ("GET", "/api/v1/properties/cursor"),
            ("GET", "/api/v1/properties/1"),
            ("POST", "/api/v1/properties/"),
            ("PUT", "/api/v1/properties/1"),
            ("DELETE", "/api/v1/properties/1"),
            # Deals (require analyst/manager)
            ("GET", "/api/v1/deals/"),
            ("GET", "/api/v1/deals/cursor"),
            ("GET", "/api/v1/deals/1"),
            ("POST", "/api/v1/deals/"),
            ("PATCH", "/api/v1/deals/1"),
            ("DELETE", "/api/v1/deals/1"),
            # Users (require admin)
            ("GET", "/api/v1/users/"),
            ("GET", "/api/v1/users/1"),
            ("POST", "/api/v1/users/"),
            ("PUT", "/api/v1/users/1"),
            ("DELETE", "/api/v1/users/1"),
            # Auth
            ("GET", "/api/v1/auth/me"),
            # Admin
            ("GET", "/api/v1/admin/audit-log"),
            ("POST", "/api/v1/admin/extract/fred"),
            ("GET", "/api/v1/admin/market-data-status"),
            # Extraction
            ("GET", "/api/v1/extraction/status"),
        ],
    )
    async def test_endpoint_requires_auth(self, client, method, endpoint):
        """Protected endpoint should return 401 without Authorization header."""
        response = await client.request(method, endpoint)
        assert response.status_code == 401, (
            f"{method} {endpoint} returned {response.status_code} without auth "
            f"(expected 401)"
        )


# =============================================================================
# Analyst Role Access Tests
# =============================================================================


class TestAnalystAccess:
    """Verify analyst role can access appropriate endpoints but not admin/manager."""

    async def test_analyst_can_read_properties(self, client, analyst_headers):
        """Analyst should be able to list properties."""
        response = await client.get(
            "/api/v1/properties/",
            headers=analyst_headers,
        )
        assert response.status_code == 200

    async def test_analyst_can_read_deals(self, client, analyst_headers):
        """Analyst should be able to list deals."""
        response = await client.get(
            "/api/v1/deals/",
            headers=analyst_headers,
        )
        assert response.status_code == 200

    async def test_analyst_cannot_create_property(self, client, analyst_headers):
        """Analyst should NOT be able to create a property (requires manager)."""
        response = await client.post(
            "/api/v1/properties/",
            json={
                "name": "Test Property",
                "property_type": "multifamily",
                "address": "123 Test St",
                "city": "Phoenix",
                "state": "AZ",
            },
            headers=analyst_headers,
        )
        assert response.status_code == 403

    async def test_analyst_cannot_update_property(self, client, analyst_headers):
        """Analyst should NOT be able to update a property (requires manager)."""
        response = await client.put(
            "/api/v1/properties/1",
            json={"name": "Hacked Name"},
            headers=analyst_headers,
        )
        assert response.status_code in {403, 404}

    async def test_analyst_cannot_delete_property(self, client, analyst_headers):
        """Analyst should NOT be able to delete a property (requires manager)."""
        response = await client.delete(
            "/api/v1/properties/1",
            headers=analyst_headers,
        )
        assert response.status_code in {403, 404}

    async def test_analyst_cannot_list_users(self, client, analyst_headers):
        """Analyst should NOT be able to list users (requires admin)."""
        response = await client.get(
            "/api/v1/users/",
            headers=analyst_headers,
        )
        assert response.status_code == 403

    async def test_analyst_cannot_create_user(self, client, analyst_headers):
        """Analyst should NOT be able to create users (requires admin)."""
        response = await client.post(
            "/api/v1/users/",
            json={
                "email": "newuser@example.com",
                "password": "Password123!",
                "full_name": "New User",
                "role": "analyst",
            },
            headers=analyst_headers,
        )
        assert response.status_code == 403

    async def test_analyst_cannot_delete_user(self, client, analyst_headers):
        """Analyst should NOT be able to delete users (requires admin)."""
        response = await client.delete(
            "/api/v1/users/1",
            headers=analyst_headers,
        )
        assert response.status_code == 403

    async def test_analyst_cannot_access_admin_panel(self, client, analyst_headers):
        """Analyst should NOT be able to access admin endpoints."""
        response = await client.get(
            "/api/v1/admin/audit-log",
            headers=analyst_headers,
        )
        assert response.status_code == 403


# =============================================================================
# Viewer Role Access Tests
# =============================================================================


class TestViewerAccess:
    """Verify viewer role has very restricted access."""

    async def test_viewer_cannot_list_properties(self, client, viewer_headers):
        """Viewer should NOT be able to list properties (requires analyst)."""
        response = await client.get(
            "/api/v1/properties/",
            headers=viewer_headers,
        )
        assert response.status_code == 403

    async def test_viewer_cannot_list_deals(self, client, viewer_headers):
        """Viewer should NOT be able to list deals (requires analyst)."""
        response = await client.get(
            "/api/v1/deals/",
            headers=viewer_headers,
        )
        assert response.status_code == 403

    async def test_viewer_cannot_create_anything(self, client, viewer_headers):
        """Viewer should NOT be able to create resources."""
        # Try creating a property
        response = await client.post(
            "/api/v1/properties/",
            json={
                "name": "Viewer Property",
                "property_type": "multifamily",
                "address": "123 Test St",
                "city": "Phoenix",
                "state": "AZ",
            },
            headers=viewer_headers,
        )
        assert response.status_code == 403

    async def test_viewer_cannot_list_users(self, client, viewer_headers):
        """Viewer should NOT be able to list users."""
        response = await client.get(
            "/api/v1/users/",
            headers=viewer_headers,
        )
        assert response.status_code == 403


# =============================================================================
# IDOR (Insecure Direct Object Reference) Tests
# =============================================================================


class TestIDOR:
    """Verify users cannot access resources they should not."""

    async def test_user_cannot_view_other_user_profile(
        self, client, analyst_user, viewer_user_sec
    ):
        """Non-admin user should not be able to view another user's profile."""
        analyst_token = create_access_token(subject=str(analyst_user.id))
        headers = {"Authorization": f"Bearer {analyst_token}"}

        # Analyst trying to view viewer's profile
        response = await client.get(
            f"/api/v1/users/{viewer_user_sec.id}",
            headers=headers,
        )
        assert response.status_code == 403

    async def test_user_cannot_update_other_user_profile(
        self, client, analyst_user, viewer_user_sec
    ):
        """Non-admin user should not be able to update another user's profile."""
        analyst_token = create_access_token(subject=str(analyst_user.id))
        headers = {"Authorization": f"Bearer {analyst_token}"}

        response = await client.put(
            f"/api/v1/users/{viewer_user_sec.id}",
            json={"full_name": "Hacked Name"},
            headers=headers,
        )
        assert response.status_code == 403

    async def test_user_can_view_own_profile(self, client, analyst_user):
        """Users should be able to view their own profile."""
        analyst_token = create_access_token(subject=str(analyst_user.id))
        headers = {"Authorization": f"Bearer {analyst_token}"}

        response = await client.get(
            f"/api/v1/users/{analyst_user.id}",
            headers=headers,
        )
        assert response.status_code == 200

    async def test_admin_can_view_any_profile(
        self, client, admin_headers, analyst_user
    ):
        """Admin should be able to view any user's profile."""
        response = await client.get(
            f"/api/v1/users/{analyst_user.id}",
            headers=admin_headers,
        )
        assert response.status_code == 200

    async def test_user_cannot_escalate_own_role(self, client, analyst_user):
        """Non-admin user should not be able to change their own role."""
        analyst_token = create_access_token(subject=str(analyst_user.id))
        headers = {"Authorization": f"Bearer {analyst_token}"}

        response = await client.put(
            f"/api/v1/users/{analyst_user.id}",
            json={"role": "admin"},
            headers=headers,
        )
        assert response.status_code == 403

    async def test_user_cannot_activate_own_account(self, client, inactive_user_sec):
        """Inactive user should not be able to re-activate themselves."""
        # Inactive user's token should be rejected at the auth layer
        token = create_access_token(subject=str(inactive_user_sec.id))
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.put(
            f"/api/v1/users/{inactive_user_sec.id}",
            json={"is_active": True},
            headers=headers,
        )
        # Should be rejected: either 401/403 (inactive) or 403 (restricted field)
        assert response.status_code in {401, 403}


# =============================================================================
# Error Message Sanitization in Auth Context
# =============================================================================


class TestAuthErrorSanitization:
    """Verify auth-related error messages don't leak sensitive info."""

    async def test_401_does_not_leak_info(self, client):
        """401 responses should not reveal internal details."""
        response = await client.get(
            "/api/v1/properties/",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401
        body = response.text
        for pattern in INTERNAL_INFO_PATTERNS:
            if pattern.isupper():
                assert pattern not in body
            else:
                assert pattern not in body.lower()

    async def test_403_does_not_leak_info(self, client, analyst_headers):
        """403 responses should not reveal internal details."""
        response = await client.get(
            "/api/v1/users/",
            headers=analyst_headers,
        )
        assert response.status_code == 403
        body = response.text
        # Should not contain stack traces or file paths
        assert "Traceback" not in body
        assert ".py:" not in body

    async def test_404_does_not_leak_info(self, client, analyst_headers):
        """404 responses should not reveal table names or SQL."""
        response = await client.get(
            "/api/v1/properties/99999",
            headers=analyst_headers,
        )
        assert response.status_code == 404
        body = response.text
        assert "SELECT" not in body
        assert "FROM" not in body
        assert "sqlalchemy" not in body.lower()

    async def test_nonexistent_route_returns_clean_404(self, client, analyst_headers):
        """Requesting a nonexistent route should return clean 404/405."""
        response = await client.get(
            "/api/v1/this/does/not/exist",
            headers=analyst_headers,
        )
        assert response.status_code in {404, 405}
        await assert_safe_response(response, allow_statuses={404, 405})

    async def test_wrong_method_returns_clean_405(self, client, analyst_headers):
        """Using wrong HTTP method should return clean 405."""
        response = await client.patch(
            "/api/v1/properties/",
            json={},
            headers=analyst_headers,
        )
        assert response.status_code == 405
        await assert_safe_response(response, allow_statuses={405})
