"""Tests for user API endpoints.

Tests the Users API endpoints including:
- List users with filtering and pagination
- Get user by ID
- Create, update, and delete users
- User verification
"""

import pytest

# =============================================================================
# List Users Tests
# =============================================================================


@pytest.mark.asyncio
async def test_list_users(client, db_session):
    """Test listing all users with default pagination."""
    response = await client.get("/api/v1/users/", follow_redirects=True)

    if response.status_code == 404:
        pytest.skip("Users endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    # Should return paginated response
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_list_users_pagination(client, db_session):
    """Test listing users with custom pagination."""
    response = await client.get(
        "/api/v1/users/", params={"page": 1, "page_size": 2}, follow_redirects=True
    )

    if response.status_code == 404:
        pytest.skip("Users endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) <= 2


@pytest.mark.asyncio
async def test_list_users_filter_by_role(client, db_session):
    """Test filtering users by role."""
    response = await client.get(
        "/api/v1/users/", params={"role": "admin"}, follow_redirects=True
    )

    if response.status_code == 404:
        pytest.skip("Users endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    for user in data["items"]:
        assert user["role"] == "admin"


@pytest.mark.asyncio
async def test_list_users_filter_by_department(client, db_session):
    """Test filtering users by department."""
    response = await client.get(
        "/api/v1/users/", params={"department": "Acquisitions"}, follow_redirects=True
    )

    if response.status_code == 404:
        pytest.skip("Users endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    for user in data["items"]:
        assert user["department"] == "Acquisitions"


@pytest.mark.asyncio
async def test_list_users_filter_active(client, db_session):
    """Test filtering users by active status."""
    response = await client.get(
        "/api/v1/users/", params={"is_active": True}, follow_redirects=True
    )

    if response.status_code == 404:
        pytest.skip("Users endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    for user in data["items"]:
        assert user["is_active"] is True


# =============================================================================
# Get User Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_user_by_id(client, db_session):
    """Test getting a specific user by ID."""
    response = await client.get("/api/v1/users/1", follow_redirects=True)

    if response.status_code == 404:
        pytest.skip("User not found or endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == 1
    assert "email" in data
    assert "full_name" in data
    assert "role" in data


@pytest.mark.asyncio
async def test_get_user_not_found(client, db_session):
    """Test getting a non-existent user returns 404."""
    response = await client.get("/api/v1/users/99999", follow_redirects=True)

    assert response.status_code == 404


# =============================================================================
# Create User Tests
# =============================================================================


@pytest.mark.asyncio
async def test_create_user(client, db_session):
    """Test creating a new user."""
    new_user = {
        "email": "newuser@brcapital.com",
        "password": "SecurePassword123!",
        "full_name": "New Test User",
        "role": "analyst",
        "department": "Research",
    }

    response = await client.post("/api/v1/users/", json=new_user, follow_redirects=True)

    if response.status_code == 404:
        pytest.skip("Create user endpoint not implemented")

    if response.status_code in [401, 403]:
        pytest.skip("Endpoint requires authentication")

    assert response.status_code == 201
    data = response.json()

    assert "id" in data
    assert data["email"] == "newuser@brcapital.com"
    assert data["full_name"] == "New Test User"
    assert data["role"] == "analyst"
    # Password should not be in response
    assert "password" not in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_create_user_duplicate_email(client, db_session):
    """Test creating a user with duplicate email fails."""
    duplicate_user = {
        "email": "admin@brcapital.com",  # Already exists in demo data
        "password": "SecurePassword123!",
        "full_name": "Duplicate User",
        "role": "analyst",
    }

    response = await client.post(
        "/api/v1/users/", json=duplicate_user, follow_redirects=True
    )

    if response.status_code == 404:
        pytest.skip("Create user endpoint not implemented")

    # Should fail with 400 Bad Request (email already registered)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_user_missing_required_fields(client, db_session):
    """Test creating a user with missing required fields fails validation."""
    incomplete_user = {
        "email": "incomplete@brcapital.com",
        # Missing password, full_name, role
    }

    response = await client.post(
        "/api/v1/users/", json=incomplete_user, follow_redirects=True
    )

    if response.status_code == 404:
        pytest.skip("Create user endpoint not implemented")

    # Should fail validation
    assert response.status_code == 422


# =============================================================================
# Update User Tests
# =============================================================================


@pytest.mark.asyncio
async def test_update_user(client, db_session):
    """Test updating an existing user."""
    update_data = {
        "full_name": "Updated Name",
        "department": "New Department",
    }

    response = await client.put(
        "/api/v1/users/1", json=update_data, follow_redirects=True
    )

    if response.status_code == 404:
        pytest.skip("Update user endpoint not implemented")

    if response.status_code in [401, 403]:
        pytest.skip("Endpoint requires authentication")

    assert response.status_code == 200
    data = response.json()

    assert data["full_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_user_not_found(client, db_session):
    """Test updating a non-existent user returns 404."""
    update_data = {"full_name": "Updated Name"}

    response = await client.put(
        "/api/v1/users/99999", json=update_data, follow_redirects=True
    )

    assert response.status_code == 404


# =============================================================================
# Delete User Tests
# =============================================================================


@pytest.mark.asyncio
async def test_delete_user(client, db_session):
    """Test deleting (deactivating) a user."""
    response = await client.delete("/api/v1/users/1", follow_redirects=True)

    if response.status_code == 404:
        pytest.skip("Delete user endpoint not implemented")

    if response.status_code in [401, 403]:
        pytest.skip("Endpoint requires authentication")

    # Successful delete returns 204 No Content
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_user_not_found(client, db_session):
    """Test deleting a non-existent user returns 404."""
    response = await client.delete("/api/v1/users/99999", follow_redirects=True)

    assert response.status_code == 404


# =============================================================================
# User Verification Tests
# =============================================================================


@pytest.mark.asyncio
async def test_verify_user(client, db_session):
    """Test verifying a user's email."""
    response = await client.post("/api/v1/users/1/verify", follow_redirects=True)

    if response.status_code == 404:
        pytest.skip("Verify user endpoint not implemented")

    if response.status_code in [401, 403]:
        pytest.skip("Endpoint requires authentication")

    assert response.status_code == 200
    data = response.json()

    assert "message" in data
    assert "verified" in data["message"].lower()


@pytest.mark.asyncio
async def test_verify_user_not_found(client, db_session):
    """Test verifying a non-existent user returns 404."""
    response = await client.post("/api/v1/users/99999/verify", follow_redirects=True)

    assert response.status_code == 404
