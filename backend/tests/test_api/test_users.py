"""Tests for user API endpoints.

Tests the Users API endpoints including:
- List users with filtering and pagination
- Get user by ID
- Create, update, and delete users
- User verification

All endpoints require authentication (RBAC implemented).
Users are persisted in the database via CRUDUser.
"""

import pytest

# =============================================================================
# List Users Tests (Admin only)
# =============================================================================


@pytest.mark.asyncio
async def test_list_users(client, db_session, admin_auth_headers, admin_user):
    """Test listing all users with default pagination (admin only)."""
    response = await client.get(
        "/api/v1/users/", headers=admin_auth_headers, follow_redirects=True
    )

    assert response.status_code == 200
    data = response.json()

    # Should return paginated response
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert isinstance(data["items"], list)
    assert data["total"] >= 1  # At least the admin user


@pytest.mark.asyncio
async def test_list_users_pagination(client, db_session, admin_auth_headers, test_user):
    """Test listing users with custom pagination."""
    response = await client.get(
        "/api/v1/users/",
        params={"page": 1, "page_size": 2},
        headers=admin_auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) <= 2


@pytest.mark.asyncio
async def test_list_users_filter_by_role(client, db_session, admin_auth_headers, admin_user):
    """Test filtering users by role."""
    response = await client.get(
        "/api/v1/users/",
        params={"role": "admin"},
        headers=admin_auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) >= 1
    for user in data["items"]:
        assert user["role"] == "admin"


@pytest.mark.asyncio
async def test_list_users_filter_by_department(
    client, db_session, admin_auth_headers, test_user
):
    """Test filtering users by department."""
    response = await client.get(
        "/api/v1/users/",
        params={"department": "Testing"},
        headers=admin_auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) >= 1
    for user in data["items"]:
        assert user["department"] == "Testing"


@pytest.mark.asyncio
async def test_list_users_filter_active(client, db_session, admin_auth_headers, admin_user):
    """Test filtering users by active status."""
    response = await client.get(
        "/api/v1/users/",
        params={"is_active": True},
        headers=admin_auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200
    data = response.json()

    for user in data["items"]:
        assert user["is_active"] is True


@pytest.mark.asyncio
async def test_list_users_unauthenticated(client, db_session):
    """Test that listing users without auth returns 401."""
    response = await client.get("/api/v1/users/", follow_redirects=True)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_users_non_admin(client, db_session, auth_headers):
    """Test that non-admin users cannot list users."""
    response = await client.get(
        "/api/v1/users/", headers=auth_headers, follow_redirects=True
    )
    # Non-admin should get 403 Forbidden
    assert response.status_code == 403


# =============================================================================
# Get User Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_user_by_id(client, db_session, admin_auth_headers, admin_user):
    """Test getting a specific user by ID (admin can view any user)."""
    response = await client.get(
        f"/api/v1/users/{admin_user.id}",
        headers=admin_auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == admin_user.id
    assert "email" in data
    assert "full_name" in data
    assert "role" in data


@pytest.mark.asyncio
async def test_get_user_self(client, db_session, auth_headers, test_user):
    """Test that a user can view their own profile."""
    response = await client.get(
        f"/api/v1/users/{test_user.id}",
        headers=auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["email"] == test_user.email


@pytest.mark.asyncio
async def test_get_user_not_found(client, db_session, admin_auth_headers):
    """Test getting a non-existent user returns 404."""
    response = await client.get(
        "/api/v1/users/99999", headers=admin_auth_headers, follow_redirects=True
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_user_unauthenticated(client, db_session):
    """Test that getting user without auth returns 401."""
    response = await client.get("/api/v1/users/1", follow_redirects=True)
    assert response.status_code == 401


# =============================================================================
# Create User Tests (Admin only)
# =============================================================================


@pytest.mark.asyncio
async def test_create_user(client, db_session, admin_auth_headers):
    """Test creating a new user (admin only)."""
    new_user = {
        "email": "newuser@bandrcapital.com",
        "password": "SecurePassword123!",
        "full_name": "New Test User",
        "role": "analyst",
        "department": "Research",
    }

    response = await client.post(
        "/api/v1/users/",
        json=new_user,
        headers=admin_auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 201
    data = response.json()

    assert "id" in data
    assert data["email"] == "newuser@bandrcapital.com"
    assert data["full_name"] == "New Test User"
    assert data["role"] == "analyst"
    assert data["is_active"] is True
    assert data["is_verified"] is False
    # Password should not be in response
    assert "password" not in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_create_user_persists(client, db_session, admin_auth_headers):
    """Test that created user is persisted and retrievable."""
    new_user = {
        "email": "persist@bandrcapital.com",
        "password": "SecurePassword123!",
        "full_name": "Persist User",
        "role": "viewer",
    }

    create_resp = await client.post(
        "/api/v1/users/",
        json=new_user,
        headers=admin_auth_headers,
        follow_redirects=True,
    )
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    # Retrieve the user and verify it exists in DB
    get_resp = await client.get(
        f"/api/v1/users/{user_id}",
        headers=admin_auth_headers,
        follow_redirects=True,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["email"] == "persist@bandrcapital.com"


@pytest.mark.asyncio
async def test_create_user_duplicate_email(
    client, db_session, admin_auth_headers, admin_user
):
    """Test creating a user with duplicate email fails."""
    duplicate_user = {
        "email": admin_user.email,  # Already exists in DB
        "password": "SecurePassword123!",
        "full_name": "Duplicate User",
        "role": "analyst",
    }

    response = await client.post(
        "/api/v1/users/",
        json=duplicate_user,
        headers=admin_auth_headers,
        follow_redirects=True,
    )

    # Should fail with 400 Bad Request (email already registered)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_user_missing_required_fields(
    client, db_session, admin_auth_headers
):
    """Test creating a user with missing required fields fails validation."""
    incomplete_user = {
        "email": "incomplete@bandrcapital.com",
        # Missing password, full_name, role
    }

    response = await client.post(
        "/api/v1/users/",
        json=incomplete_user,
        headers=admin_auth_headers,
        follow_redirects=True,
    )

    # Should fail validation
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_user_non_admin(client, db_session, auth_headers):
    """Test that non-admin users cannot create users."""
    new_user = {
        "email": "newuser2@bandrcapital.com",
        "password": "SecurePassword123!",
        "full_name": "New Test User",
        "role": "analyst",
    }

    response = await client.post(
        "/api/v1/users/", json=new_user, headers=auth_headers, follow_redirects=True
    )

    # Non-admin should get 403 Forbidden
    assert response.status_code == 403


# =============================================================================
# Update User Tests
# =============================================================================


@pytest.mark.asyncio
async def test_update_user(client, db_session, admin_auth_headers, test_user):
    """Test updating an existing user (admin can update any user)."""
    update_data = {
        "full_name": "Updated Name",
        "department": "New Department",
    }

    response = await client.put(
        f"/api/v1/users/{test_user.id}",
        json=update_data,
        headers=admin_auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["full_name"] == "Updated Name"
    assert data["department"] == "New Department"


@pytest.mark.asyncio
async def test_update_user_not_found(client, db_session, admin_auth_headers):
    """Test updating a non-existent user returns 404."""
    update_data = {"full_name": "Updated Name"}

    response = await client.put(
        "/api/v1/users/99999",
        json=update_data,
        headers=admin_auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_user_unauthenticated(client, db_session):
    """Test that updating user without auth returns 401."""
    update_data = {"full_name": "Updated Name"}
    response = await client.put(
        "/api/v1/users/1", json=update_data, follow_redirects=True
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_user_email_uniqueness(
    client, db_session, admin_auth_headers, test_user, admin_user
):
    """Test that updating email to an already-used email fails."""
    update_data = {"email": admin_user.email}

    response = await client.put(
        f"/api/v1/users/{test_user.id}",
        json=update_data,
        headers=admin_auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 400
    assert "already in use" in response.json()["detail"]


# =============================================================================
# Delete User Tests (Admin only)
# =============================================================================


@pytest.mark.asyncio
async def test_delete_user(client, db_session, admin_auth_headers, test_user):
    """Test deleting (deactivating) a user (admin only)."""
    response = await client.delete(
        f"/api/v1/users/{test_user.id}",
        headers=admin_auth_headers,
        follow_redirects=True,
    )

    # Successful delete returns 204 No Content
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_user_self_prevention(
    client, db_session, admin_auth_headers, admin_user
):
    """Test that an admin cannot deactivate their own account."""
    response = await client.delete(
        f"/api/v1/users/{admin_user.id}",
        headers=admin_auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 400
    assert "your own account" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_user_not_found(client, db_session, admin_auth_headers):
    """Test deleting a non-existent user returns 404."""
    response = await client.delete(
        "/api/v1/users/99999", headers=admin_auth_headers, follow_redirects=True
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_non_admin(client, db_session, auth_headers):
    """Test that non-admin users cannot delete users."""
    response = await client.delete(
        "/api/v1/users/1", headers=auth_headers, follow_redirects=True
    )

    # Non-admin should get 403 Forbidden
    assert response.status_code == 403


# =============================================================================
# User Verification Tests (Admin only)
# =============================================================================


@pytest.mark.asyncio
async def test_verify_user(client, db_session, admin_auth_headers, test_user):
    """Test verifying a user's email (admin only)."""
    response = await client.post(
        f"/api/v1/users/{test_user.id}/verify",
        headers=admin_auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200
    data = response.json()

    assert "message" in data
    assert "verified" in data["message"].lower()


@pytest.mark.asyncio
async def test_verify_user_not_found(client, db_session, admin_auth_headers):
    """Test verifying a non-existent user returns 404."""
    response = await client.post(
        "/api/v1/users/99999/verify", headers=admin_auth_headers, follow_redirects=True
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_verify_user_non_admin(client, db_session, auth_headers):
    """Test that non-admin users cannot verify users."""
    response = await client.post(
        "/api/v1/users/1/verify", headers=auth_headers, follow_redirects=True
    )

    # Non-admin should get 403 Forbidden
    assert response.status_code == 403
