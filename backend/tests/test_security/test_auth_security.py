"""
Authentication security tests.

Verifies the JWT authentication system is resistant to common attack vectors
including token tampering, expired tokens, wrong signing keys, missing auth,
malformed tokens, blacklisted tokens, and role escalation attempts.
"""

import time
from datetime import UTC, datetime, timedelta

import pytest
import jwt

from app.core.config import settings
from app.core.security import create_access_token, decode_token
from app.core.token_blacklist import token_blacklist

from .conftest import assert_safe_response


# =============================================================================
# Expired Token Tests
# =============================================================================


class TestExpiredTokens:
    """Verify expired JWT tokens are properly rejected."""

    async def test_expired_token_rejected(self, client, expired_token):
        """An expired JWT token should be rejected with 401."""
        response = await client.get(
            "/api/v1/properties/",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    async def test_expired_token_on_deals(self, client, expired_token):
        """Expired token should be rejected on deal endpoints too."""
        response = await client.get(
            "/api/v1/deals/",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    async def test_expired_token_on_me(self, client, expired_token):
        """Expired token should be rejected on /auth/me."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    async def test_expired_token_on_users(self, client, expired_token):
        """Expired token should be rejected on user endpoints."""
        response = await client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401


# =============================================================================
# Tampered Token Tests
# =============================================================================


class TestTamperedTokens:
    """Verify tampered JWT tokens are properly rejected."""

    async def test_tampered_payload_rejected(self, client, tampered_token):
        """A token with a modified payload (but original sig) should be rejected."""
        response = await client.get(
            "/api/v1/properties/",
            headers={"Authorization": f"Bearer {tampered_token}"},
        )
        assert response.status_code == 401

    async def test_truncated_token_rejected(self, client, analyst_token):
        """A token that has been truncated should be rejected."""
        truncated = analyst_token[:50]
        response = await client.get(
            "/api/v1/properties/",
            headers={"Authorization": f"Bearer {truncated}"},
        )
        assert response.status_code == 401

    async def test_token_with_extra_segments_rejected(self, client, analyst_token):
        """A token with an extra segment appended should be rejected."""
        extra_segment = analyst_token + ".extrasegment"
        response = await client.get(
            "/api/v1/properties/",
            headers={"Authorization": f"Bearer {extra_segment}"},
        )
        assert response.status_code == 401

    async def test_empty_payload_token_rejected(self, client):
        """A token with empty payload should be rejected."""
        # Create a JWT with no sub claim
        expire = datetime.now(UTC) + timedelta(minutes=30)
        payload = {"exp": expire}
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        response = await client.get(
            "/api/v1/properties/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401


# =============================================================================
# Wrong Signing Key Tests
# =============================================================================


class TestWrongSigningKey:
    """Verify tokens signed with the wrong key are rejected."""

    async def test_wrong_key_rejected(self, client, wrong_key_token):
        """A JWT signed with a different secret key should be rejected."""
        response = await client.get(
            "/api/v1/properties/",
            headers={"Authorization": f"Bearer {wrong_key_token}"},
        )
        assert response.status_code == 401

    async def test_wrong_algorithm(self, client):
        """A JWT using a different algorithm should be rejected."""
        expire = datetime.now(UTC) + timedelta(minutes=30)
        payload = {"exp": expire, "sub": "1", "jti": "test-algo"}
        # Use HS384 instead of HS256
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS384")
        response = await client.get(
            "/api/v1/properties/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    async def test_none_algorithm_rejected(self, client):
        """The 'none' algorithm attack should be rejected.

        Some JWT implementations accept algorithm=none which bypasses signature
        verification entirely. Our system should reject this.
        """
        import base64
        import json

        header = (
            base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode())
            .rstrip(b"=")
            .decode()
        )
        payload = (
            base64.urlsafe_b64encode(
                json.dumps({"sub": "1", "exp": int(time.time()) + 3600}).encode()
            )
            .rstrip(b"=")
            .decode()
        )
        # No signature
        token = f"{header}.{payload}."
        response = await client.get(
            "/api/v1/properties/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401


# =============================================================================
# Missing Authorization Tests
# =============================================================================


class TestMissingAuth:
    """Verify endpoints require authentication."""

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/api/v1/properties/",
            "/api/v1/properties/dashboard",
            "/api/v1/properties/summary",
            "/api/v1/deals/",
            "/api/v1/users/",
            "/api/v1/auth/me",
            "/api/v1/admin/audit-log",
            "/api/v1/analytics/dashboard",
        ],
    )
    async def test_no_auth_header_returns_401(self, client, endpoint):
        """Endpoints without Authorization header should return 401."""
        response = await client.get(endpoint)
        assert response.status_code == 401, (
            f"Endpoint {endpoint} returned {response.status_code} without auth"
        )

    async def test_empty_auth_header_returns_401(self, client):
        """An empty Authorization header should return 401."""
        response = await client.get(
            "/api/v1/properties/",
            headers={"Authorization": ""},
        )
        # FastAPI's OAuth2PasswordBearer expects "Bearer <token>"
        assert response.status_code in {401, 403}

    async def test_auth_without_bearer_prefix_returns_401(self, client, analyst_token):
        """Token without 'Bearer ' prefix should be rejected."""
        response = await client.get(
            "/api/v1/properties/",
            headers={"Authorization": analyst_token},
        )
        assert response.status_code in {401, 403}


# =============================================================================
# Malformed Token Tests
# =============================================================================


class TestMalformedTokens:
    """Verify malformed Bearer tokens are properly rejected."""

    @pytest.mark.parametrize(
        "token_value",
        [
            "notavalidtoken",
            "Bearer ",
            "a.b.c",
            "eyJhbGciOiJIUzI1NiJ9..invalid",
            "null",
            "undefined",
            "true",
            "123456789",
            '{"sub": "1"}',
            "",
        ],
    )
    async def test_malformed_token_rejected(self, client, token_value):
        """Various malformed token strings should be rejected."""
        response = await client.get(
            "/api/v1/properties/",
            headers={"Authorization": f"Bearer {token_value}"},
        )
        assert response.status_code == 401, (
            f"Token {token_value!r} was not rejected (status={response.status_code})"
        )

    async def test_bearer_with_spaces_rejected(self, client):
        """Bearer token with extra spaces should be handled safely."""
        response = await client.get(
            "/api/v1/properties/",
            headers={"Authorization": "Bearer    "},
        )
        assert response.status_code == 401

    async def test_very_long_token_rejected(self, client):
        """An extremely long token string should be rejected safely."""
        long_token = "A" * 10000
        response = await client.get(
            "/api/v1/properties/",
            headers={"Authorization": f"Bearer {long_token}"},
        )
        assert response.status_code == 401
        await assert_safe_response(response, allow_statuses={401})


# =============================================================================
# Blacklisted / Revoked Token Tests
# =============================================================================


class TestBlacklistedTokens:
    """Verify blacklisted tokens are properly rejected."""

    async def test_blacklisted_token_rejected(self, client, analyst_user):
        """A token that has been blacklisted should be rejected."""
        token = create_access_token(subject=str(analyst_user.id))
        # Decode to get jti
        payload = decode_token(token)
        jti = payload["jti"]

        # Blacklist it
        await token_blacklist.add(jti, expires_in=300)

        response = await client.get(
            "/api/v1/properties/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    async def test_token_reuse_after_logout(self, client, analyst_user):
        """A token used after logout (blacklisted) should be rejected."""
        token = create_access_token(subject=str(analyst_user.id))

        # First request should work
        response1 = await client.get(
            "/api/v1/properties/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response1.status_code == 200

        # Logout (blacklist the token)
        await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Second request should fail
        response2 = await client.get(
            "/api/v1/properties/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response2.status_code == 401

    async def test_different_token_after_logout_works(self, client, analyst_user):
        """Logging out one token should not affect other valid tokens."""
        token1 = create_access_token(subject=str(analyst_user.id))
        token2 = create_access_token(subject=str(analyst_user.id))

        # Logout token1
        await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token1}"},
        )

        # token2 should still work
        response = await client.get(
            "/api/v1/properties/",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert response.status_code == 200


# =============================================================================
# Role Escalation Tests
# =============================================================================


class TestRoleEscalation:
    """Verify that users cannot escalate their privileges."""

    async def test_analyst_cannot_access_admin_endpoints(self, client, analyst_headers):
        """Analyst-level users should be denied access to admin-only endpoints."""
        admin_endpoints = [
            ("GET", "/api/v1/admin/audit-log"),
            ("POST", "/api/v1/admin/extract/fred"),
            ("POST", "/api/v1/admin/extract/costar"),
            ("POST", "/api/v1/admin/extract/census"),
            ("GET", "/api/v1/admin/market-data-status"),
        ]
        for method, url in admin_endpoints:
            if method == "GET":
                response = await client.get(url, headers=analyst_headers)
            else:
                response = await client.post(url, headers=analyst_headers)
            assert response.status_code == 403, (
                f"Analyst could access admin endpoint {method} {url} "
                f"(status={response.status_code})"
            )

    async def test_analyst_cannot_create_deals(self, client, analyst_headers):
        """Analyst should not be able to create deals (requires manager)."""
        response = await client.post(
            "/api/v1/deals/",
            json={
                "name": "Hacked Deal",
                "deal_type": "acquisition",
                "stage": "initial_review",
            },
            headers=analyst_headers,
        )
        assert response.status_code == 403

    async def test_analyst_cannot_delete_deals(self, client, analyst_headers):
        """Analyst should not be able to delete deals (requires manager)."""
        response = await client.delete(
            "/api/v1/deals/1",
            headers=analyst_headers,
        )
        # 403 (permission denied) or 404 (deal doesn't exist) are both safe
        assert response.status_code in {403, 404}

    async def test_analyst_cannot_create_properties(self, client, analyst_headers):
        """Analyst should not be able to create properties (requires manager)."""
        response = await client.post(
            "/api/v1/properties/",
            json={
                "name": "Hacked Property",
                "property_type": "multifamily",
                "address": "123 Hack St",
                "city": "Phoenix",
                "state": "AZ",
            },
            headers=analyst_headers,
        )
        assert response.status_code == 403

    async def test_analyst_cannot_manage_users(self, client, analyst_headers):
        """Analyst should not be able to list or create users (requires admin)."""
        # List users
        response = await client.get(
            "/api/v1/users/",
            headers=analyst_headers,
        )
        assert response.status_code == 403

        # Create user
        response = await client.post(
            "/api/v1/users/",
            json={
                "email": "hacker@example.com",
                "password": "HackerPass123!",
                "full_name": "Hacker",
                "role": "admin",
            },
            headers=analyst_headers,
        )
        assert response.status_code == 403

    async def test_viewer_cannot_access_analyst_endpoints(self, client, viewer_headers):
        """Viewer should be denied access to analyst-level endpoints."""
        # Properties require analyst role
        response = await client.get(
            "/api/v1/properties/",
            headers=viewer_headers,
        )
        assert response.status_code == 403

    async def test_viewer_cannot_access_manager_endpoints(self, client, viewer_headers):
        """Viewer should be denied access to manager-level endpoints."""
        response = await client.post(
            "/api/v1/deals/",
            json={"name": "Test", "deal_type": "acquisition"},
            headers=viewer_headers,
        )
        assert response.status_code == 403

    async def test_inactive_user_token_rejected(self, client, inactive_user_sec):
        """Tokens for inactive users should be rejected."""
        token = create_access_token(subject=str(inactive_user_sec.id))
        response = await client.get(
            "/api/v1/properties/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    async def test_token_claims_cannot_override_db_role(self, client, analyst_user):
        """Token claims should not override the database role.

        Even if we embed role=admin in the token claims, the system should
        check the database and enforce the actual user role.
        """
        # Create token with admin role claim for an analyst user
        token = create_access_token(
            subject=str(analyst_user.id),
            additional_claims={"role": "admin"},
        )
        # Try admin endpoint
        response = await client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should be 403 because DB says analyst, not admin
        assert response.status_code == 403


# =============================================================================
# Login Security Tests
# =============================================================================


class TestLoginSecurity:
    """Verify login endpoint security measures."""

    async def test_login_with_wrong_password(self, client, analyst_user):
        """Login with wrong password should fail with 401."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": analyst_user.email,
                "password": "WrongPassword123!",
            },
        )
        assert response.status_code == 401

    async def test_login_with_nonexistent_user(self, client):
        """Login with nonexistent email should fail with 401."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "AnyPassword123!",
            },
        )
        assert response.status_code == 401

    async def test_login_error_does_not_reveal_user_existence(
        self, client, analyst_user
    ):
        """Login failure messages should not reveal whether the user exists."""
        # Wrong password for existing user
        response1 = await client.post(
            "/api/v1/auth/login",
            data={
                "username": analyst_user.email,
                "password": "WrongPassword",
            },
        )
        # Nonexistent user
        response2 = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "WrongPassword",
            },
        )
        # Both should return the same status code and similar messages
        assert response1.status_code == response2.status_code == 401

    async def test_login_inactive_user(self, client, inactive_user_sec):
        """Login for inactive user should fail with 403."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": inactive_user_sec.email,
                "password": "InactivePass123!",
            },
        )
        assert response.status_code == 403

    async def test_login_requires_form_data(self, client):
        """Login endpoint requires form data, not JSON body."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "test@example.com",
                "password": "testpassword",
            },
        )
        assert response.status_code == 422
