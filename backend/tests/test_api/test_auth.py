"""Tests for authentication endpoints."""
import pytest
import pytest_asyncio

from app.core.security import get_password_hash, create_access_token, create_refresh_token
from app.models import User


# =============================================================================
# Fixtures for Auth Tests
# =============================================================================

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
async def test_login_demo_user_admin(client):
    """Test login with demo admin user (fallback for development)."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin@brcapital.com",
            "password": "admin123",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_demo_user_analyst(client):
    """Test login with demo analyst user (fallback for development)."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "analyst@brcapital.com",
            "password": "analyst123",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_demo_user_wrong_password(client):
    """Test demo user login fails with wrong password."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin@brcapital.com",
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
        additional_claims={"role": "viewer", "email": "demo@brcapital.com"},
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
