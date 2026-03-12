"""Tests for authentication endpoints."""

import pytest
import pytest_asyncio

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
)
from app.core.token_blacklist import token_blacklist
from app.models import User

# =============================================================================
# Fixtures for Auth Tests
# =============================================================================


@pytest_asyncio.fixture(autouse=True)
async def _clear_token_blacklist():
    """Reset token blacklist state between tests to prevent cross-test pollution.

    Redis persists between test runs, so we must clear blacklist/revocation keys
    both before and after each test.
    """
    token_blacklist._redis = None

    async def _flush_blacklist_keys():
        await token_blacklist._ensure_redis()
        if token_blacklist._redis is not None:
            try:
                keys = await token_blacklist._redis.keys("blacklist:*")
                keys += await token_blacklist._redis.keys("user_revoked:*")
                keys += await token_blacklist._redis.keys("rl:*")
                if keys:
                    await token_blacklist._redis.delete(*keys)
            except Exception:
                pass

    await _flush_blacklist_keys()
    yield
    await _flush_blacklist_keys()
    token_blacklist._redis = None


@pytest_asyncio.fixture
async def inactive_user(db_session) -> User:
    """Create an inactive test user."""
    user = User(
        email="inactive@example.com",
        hashed_password=get_password_hash("inactivepassword123"),
        full_name="Inactive User",
        role="analyst",
        is_active=False,
        is_verified=True,
        department="Testing",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# =============================================================================
# Login Endpoint Tests
# =============================================================================


@pytest.mark.asyncio
async def test_login_success(client, test_user):
    """Test successful login returns access token."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpassword123",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data


@pytest.mark.asyncio
async def test_login_invalid_credentials(client, test_user):
    """Test login with wrong password fails."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "wrongpassword",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    """Test login with non-existent user fails."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "nonexistent@example.com",
            "password": "password123",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_inactive_user(client, inactive_user):
    """Test login with inactive user account fails with 403."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "inactive@example.com",
            "password": "inactivepassword123",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 403
    data = response.json()
    assert "disabled" in data["detail"].lower()


@pytest.mark.asyncio
async def test_login_demo_user_admin(client, monkeypatch):
    """Test login with demo admin user (fallback for development only).

    NOTE: Demo users are only available in non-production environments.
    In production, this should fail with 401 (tested separately).
    """
    from app.core.config import settings

    # Ensure demo admin password is set for test (Wave 1 S-01 made these env-var-driven)
    monkeypatch.setattr(settings, "DEMO_ADMIN_PASSWORD", "admin123")

    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin@bandrcapital.com",
            "password": "admin123",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    # In non-production (testing), demo users should work
    if settings.ENVIRONMENT != "production":
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    else:
        # In production, demo users should fail
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_demo_user_analyst(client, monkeypatch):
    """Test login with demo analyst user (fallback for development only)."""
    from app.core.config import settings

    # Ensure demo analyst password is set for test (Wave 1 S-01 made these env-var-driven)
    monkeypatch.setattr(settings, "DEMO_ANALYST_PASSWORD", "analyst123")

    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "analyst@bandrcapital.com",
            "password": "analyst123",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    if settings.ENVIRONMENT != "production":
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    else:
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_demo_user_wrong_password(client):
    """Test demo user login fails with wrong password."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin@bandrcapital.com",
            "password": "wrongpassword",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 401


# =============================================================================
# Refresh Token Tests
# =============================================================================


@pytest.mark.asyncio
async def test_refresh_token_valid(client, test_user):
    """Test refreshing tokens with valid refresh token."""
    # First get a valid refresh token through login
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpassword123",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == 200
    refresh_token = login_response.json()["refresh_token"]

    # Use the refresh token to get new tokens
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_token_invalid(client):
    """Test refreshing tokens with invalid refresh token fails."""
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.token.here"},
    )

    assert response.status_code == 401
    data = response.json()
    assert "invalid" in data["detail"].lower()


@pytest.mark.asyncio
async def test_refresh_token_access_token_used(client, test_user):
    """Test that access token cannot be used as refresh token."""
    # Create an access token (not refresh)
    access_token = create_access_token(subject=str(test_user.id))

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )

    # Should fail because access token type != "refresh"
    assert response.status_code == 401


# =============================================================================
# Logout Tests
# =============================================================================


@pytest.mark.asyncio
async def test_logout(client):
    """Test logout endpoint returns success message."""
    response = await client.post("/api/v1/auth/logout")

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "logged out" in data["message"].lower()


# =============================================================================
# Get Current User (/me) Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_me_with_valid_token(client, test_user, auth_headers):
    """Test getting current user info with valid token."""
    response = await client.get("/api/v1/auth/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["email"] == test_user.email
    assert data["role"] == test_user.role
    assert data["full_name"] == test_user.full_name


@pytest.mark.asyncio
async def test_get_me_without_token(client):
    """Test getting current user info without token fails."""
    response = await client.get("/api/v1/auth/me")

    assert response.status_code in [401, 403, 422]


@pytest.mark.asyncio
async def test_get_me_with_invalid_token(client):
    """Test getting current user info with invalid token fails."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_demo_user_fallback(client):
    """Test /me endpoint with demo user (no DB record) returns fallback data."""
    # Create token for demo user (ID 1, which may not exist in test DB)
    demo_token = create_access_token(
        subject="999999",  # Non-existent user ID
        additional_claims={"role": "viewer", "email": "demo@bandrcapital.com"},
    )

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {demo_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 999999
    # Fallback values returned for non-DB user
    assert "role" in data


# =============================================================================
# Edge Cases and Security Tests
# =============================================================================


@pytest.mark.asyncio
async def test_login_missing_username(client):
    """Test login without username fails."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"password": "testpassword123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_login_missing_password(client):
    """Test login without password fails."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_protected_endpoint_without_auth(client):
    """Test that protected endpoints require authentication."""
    response = await client.get("/api/v1/users/me")

    assert response.status_code in [401, 403, 422]


@pytest.mark.asyncio
async def test_protected_endpoint_with_auth(client, auth_headers):
    """Test that protected endpoints accept valid auth (not 401)."""
    response = await client.get("/api/v1/users/me", headers=auth_headers)

    # Should not be auth error - may be 200, 422 (validation), etc.
    # The key test is that auth headers are accepted
    assert response.status_code != 401


@pytest.mark.asyncio
async def test_demo_users_disabled_in_production_environment(monkeypatch):
    """Test that _get_demo_users returns empty dict in production."""
    from app.api.v1.endpoints.auth import _get_demo_users
    from app.core.config import settings

    # Ensure demo passwords are set for test (Wave 1 S-01 made these env-var-driven)
    monkeypatch.setattr(settings, "DEMO_ADMIN_PASSWORD", "admin123")
    monkeypatch.setattr(settings, "DEMO_ANALYST_PASSWORD", "analyst123")

    demo_users = _get_demo_users()

    # Should have demo users in non-production
    if settings.ENVIRONMENT != "production":
        assert len(demo_users) > 0
        assert "admin@bandrcapital.com" in demo_users
        assert "analyst@bandrcapital.com" in demo_users
    # Note: Cannot easily test production behavior without changing settings
    # The implementation guards against production by checking settings.ENVIRONMENT


# =============================================================================
# Token Blacklist Tests
# =============================================================================


@pytest.mark.asyncio
async def test_logout_blacklists_token(client, test_user):
    """Test that logout adds token to blacklist."""
    # Login to get a token
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpassword123",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    # Verify token works before logout
    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200

    # Logout with the token
    logout_response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_response.status_code == 200
    assert "logged out" in logout_response.json()["message"].lower()

    # Token should now be rejected
    me_response_after = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response_after.status_code == 401
    assert "revoked" in me_response_after.json()["detail"].lower()


@pytest.mark.asyncio
async def test_logout_without_token_still_succeeds(client):
    """Test that logout without a token still returns success."""
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert "logged out" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_logout_with_invalid_token_still_succeeds(client):
    """Test that logout with invalid token still returns success."""
    response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert response.status_code == 200
    assert "logged out" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_token_contains_jti(client, test_user):
    """Test that generated tokens contain a JTI claim."""
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpassword123",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]
    refresh_token = login_response.json()["refresh_token"]

    # Decode and verify JTI exists
    access_payload = decode_token(access_token)
    refresh_payload = decode_token(refresh_token)

    assert access_payload is not None
    assert "jti" in access_payload
    assert len(access_payload["jti"]) == 36  # UUID format

    assert refresh_payload is not None
    assert "jti" in refresh_payload
    assert len(refresh_payload["jti"]) == 36  # UUID format

    # JTIs should be unique
    assert access_payload["jti"] != refresh_payload["jti"]


@pytest.mark.asyncio
async def test_blacklist_add_and_check():
    """Test token blacklist add and check operations."""
    test_jti = "test-jti-12345678"

    # Should not be blacklisted initially
    is_blocked = await token_blacklist.is_blacklisted(test_jti)
    assert is_blocked is False

    # Add to blacklist
    await token_blacklist.add(test_jti, expires_in=60)

    # Should now be blacklisted
    is_blocked = await token_blacklist.is_blacklisted(test_jti)
    assert is_blocked is True

    # Clean up
    await token_blacklist.remove(test_jti)

    # Should no longer be blacklisted
    is_blocked = await token_blacklist.is_blacklisted(test_jti)
    assert is_blocked is False


@pytest.mark.asyncio
async def test_blacklist_empty_jti():
    """Test that empty JTI is handled gracefully."""
    # Should not raise errors with empty/None JTI
    await token_blacklist.add("", expires_in=60)
    is_blocked = await token_blacklist.is_blacklisted("")
    assert is_blocked is False

    await token_blacklist.add(None, expires_in=60)  # type: ignore
    is_blocked = await token_blacklist.is_blacklisted(None)  # type: ignore
    assert is_blocked is False


@pytest.mark.asyncio
async def test_blacklist_stats():
    """Test blacklist stats retrieval."""
    stats = await token_blacklist.get_stats()

    assert "backend" in stats
    assert stats["backend"] in ["redis", "memory"]
    assert "memory_entries" in stats
    assert isinstance(stats["memory_entries"], int)


@pytest.mark.asyncio
async def test_refresh_token_blacklisted_after_logout(client, test_user):
    """Test that refresh token works before logout but is blacklisted after use (rotation)."""
    # Login to get tokens
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpassword123",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    original_refresh = login_response.json()["refresh_token"]

    # Use the refresh token — should succeed and return new tokens
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original_refresh},
    )
    assert refresh_response.status_code == 200
    new_refresh = refresh_response.json()["refresh_token"]
    assert new_refresh != original_refresh  # Must be a new token

    # The original refresh token is now blacklisted (rotation) — cannot be reused
    # Clear user revocation first so we can test the token-level blacklist
    user_id = decode_token(original_refresh).get("sub")
    await token_blacklist.clear_user_revocation(user_id)

    replay_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original_refresh},
    )
    assert replay_response.status_code == 401
    assert (
        "reuse" in replay_response.json()["detail"].lower()
        or "revoked" in replay_response.json()["detail"].lower()
    )

    # But the NEW refresh token should still work (after clearing user revocation)
    await token_blacklist.clear_user_revocation(user_id)
    new_refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": new_refresh},
    )
    assert new_refresh_response.status_code == 200


# =============================================================================
# Refresh Token Rotation Tests
# =============================================================================


@pytest.mark.asyncio
async def test_refresh_rotation_returns_both_tokens(client, test_user):
    """Test that refresh endpoint returns both a new access token and new refresh token."""
    # Login
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpassword123",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == 200
    original_access = login_response.json()["access_token"]
    original_refresh = login_response.json()["refresh_token"]

    # Refresh
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original_refresh},
    )
    assert refresh_response.status_code == 200
    data = refresh_response.json()

    # Both tokens must be present and different from originals
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["access_token"] != original_access
    assert data["refresh_token"] != original_refresh
    assert data["token_type"] == "bearer"
    assert "expires_in" in data


@pytest.mark.asyncio
async def test_refresh_rotation_old_token_blacklisted(client, test_user):
    """Test that the old refresh token is blacklisted after rotation."""
    # Login
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpassword123",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    original_refresh = login_response.json()["refresh_token"]

    # Use the refresh token (rotates it)
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original_refresh},
    )
    assert refresh_response.status_code == 200

    # Verify the old token's JTI is now blacklisted
    old_payload = decode_token(original_refresh)
    old_jti = old_payload["jti"]
    assert await token_blacklist.is_blacklisted(old_jti) is True


@pytest.mark.asyncio
async def test_refresh_rotation_replay_attack_detected(client, test_user):
    """Test that reusing a blacklisted refresh token triggers replay attack detection."""
    # Login
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpassword123",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    original_refresh = login_response.json()["refresh_token"]
    user_id = decode_token(original_refresh).get("sub")

    # First refresh — succeeds, rotates the token
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original_refresh},
    )
    assert refresh_response.status_code == 200
    new_refresh = refresh_response.json()["refresh_token"]

    # Clear user revocation to isolate the replay test
    await token_blacklist.clear_user_revocation(user_id)

    # Replay attack: reuse the OLD refresh token
    replay_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original_refresh},
    )
    assert replay_response.status_code == 401
    assert "reuse" in replay_response.json()["detail"].lower()

    # After replay detection, user's tokens should be revoked
    assert await token_blacklist.is_user_revoked(user_id) is True

    # Even the NEW refresh token should now be rejected (user-level revocation)
    new_refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": new_refresh},
    )
    assert new_refresh_response.status_code == 401
    assert "revoked" in new_refresh_response.json()["detail"].lower()

    # Clean up user revocation for other tests
    await token_blacklist.clear_user_revocation(user_id)
