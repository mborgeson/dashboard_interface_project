"""Tests for User CRUD operations."""
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from app.crud.crud_user import CRUDUser, user as user_crud
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash


# =============================================================================
# Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def crud_user():
    """Create CRUDUser instance."""
    return CRUDUser(User)


@pytest_asyncio.fixture
async def test_user_in_db(db_session) -> User:
    """Create a test user directly in the database."""
    user = User(
        email="crudtest@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="CRUD Test User",
        role="analyst",
        is_active=True,
        is_verified=True,
        department="Testing",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# =============================================================================
# Create User Tests
# =============================================================================


class TestCRUDUserCreate:
    """Tests for user creation via CRUD."""

    @pytest.mark.asyncio
    async def test_create_user_with_dict(self, db_session, crud_user):
        """Test creating user with dictionary input."""
        user_data = {
            "email": "newuser@test.com",
            "password": "securepassword123",
            "full_name": "New User",
            "role": "analyst",
        }

        user = await crud_user.create(db_session, obj_in=user_data)

        assert user.id is not None
        assert user.email == "newuser@test.com"
        assert user.full_name == "New User"
        assert user.hashed_password is not None
        assert user.hashed_password != "securepassword123"  # Password hashed

    @pytest.mark.asyncio
    async def test_create_user_with_schema(self, db_session, crud_user):
        """Test creating user with Pydantic schema."""
        user_in = UserCreate(
            email="schemauser@test.com",
            password="schemapassword123",
            full_name="Schema User",
            role="viewer",
        )

        user = await crud_user.create(db_session, obj_in=user_in)

        assert user.id is not None
        assert user.email == "schemauser@test.com"
        assert user.role == "viewer"

    @pytest.mark.asyncio
    async def test_create_user_hashes_password(self, db_session, crud_user):
        """Test that create properly hashes password."""
        plain_password = "plaintextpassword"
        user_data = {
            "email": "hashtest@test.com",
            "password": plain_password,
            "full_name": "Hash Test",
        }

        user = await crud_user.create(db_session, obj_in=user_data)

        # Password should be hashed
        assert user.hashed_password != plain_password
        # Should be verifiable
        from app.core.security import verify_password
        assert verify_password(plain_password, user.hashed_password)


# =============================================================================
# Update User Tests
# =============================================================================


class TestCRUDUserUpdate:
    """Tests for user update via CRUD."""

    @pytest.mark.asyncio
    async def test_update_user_with_dict(self, db_session, crud_user, test_user_in_db):
        """Test updating user with dictionary input."""
        update_data = {
            "full_name": "Updated Name",
            "department": "New Department",
        }

        updated = await crud_user.update(
            db_session, db_obj=test_user_in_db, obj_in=update_data
        )

        assert updated.full_name == "Updated Name"
        assert updated.department == "New Department"

    @pytest.mark.asyncio
    async def test_update_user_with_schema(self, db_session, crud_user, test_user_in_db):
        """Test updating user with Pydantic schema."""
        update_in = UserUpdate(full_name="Schema Updated", role="admin")

        updated = await crud_user.update(
            db_session, db_obj=test_user_in_db, obj_in=update_in
        )

        assert updated.full_name == "Schema Updated"
        assert updated.role == "admin"

    @pytest.mark.asyncio
    async def test_update_user_password_hashed(self, db_session, crud_user, test_user_in_db):
        """Test that updating password hashes it."""
        new_password = "newpassword456"
        update_data = {"password": new_password}

        updated = await crud_user.update(
            db_session, db_obj=test_user_in_db, obj_in=update_data
        )

        # New password should be verifiable
        from app.core.security import verify_password
        assert verify_password(new_password, updated.hashed_password)


# =============================================================================
# Get User Tests
# =============================================================================


class TestCRUDUserGet:
    """Tests for getting users via CRUD."""

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, db_session, crud_user, test_user_in_db):
        """Test getting user by ID."""
        user = await crud_user.get(db_session, test_user_in_db.id)

        assert user is not None
        assert user.id == test_user_in_db.id
        assert user.email == test_user_in_db.email

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, db_session, crud_user):
        """Test getting non-existent user returns None."""
        user = await crud_user.get(db_session, 99999)

        assert user is None

    @pytest.mark.asyncio
    async def test_get_by_email(self, db_session, crud_user, test_user_in_db):
        """Test getting user by email."""
        user = await crud_user.get_by_email(db_session, email=test_user_in_db.email)

        assert user is not None
        assert user.id == test_user_in_db.id

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, db_session, crud_user):
        """Test getting non-existent email returns None."""
        user = await crud_user.get_by_email(db_session, email="nonexistent@test.com")

        assert user is None


# =============================================================================
# Get Multi Tests
# =============================================================================


class TestCRUDUserGetMulti:
    """Tests for getting multiple users."""

    @pytest.mark.asyncio
    async def test_get_multi_empty(self, db_session, crud_user):
        """Test getting users when empty returns empty list."""
        users = await crud_user.get_multi(db_session, skip=0, limit=10)

        assert isinstance(users, list)

    @pytest.mark.asyncio
    async def test_get_multi_with_pagination(self, db_session, crud_user, test_user_in_db):
        """Test pagination works correctly."""
        # Create multiple users
        for i in range(5):
            await crud_user.create(
                db_session,
                obj_in={
                    "email": f"multiuser{i}@test.com",
                    "password": "password123",
                    "full_name": f"Multi User {i}",
                }
            )

        # Get first 3
        users = await crud_user.get_multi(db_session, skip=0, limit=3)
        assert len(users) == 3

        # Get next batch
        users = await crud_user.get_multi(db_session, skip=3, limit=10)
        assert len(users) >= 2  # At least remaining users


# =============================================================================
# Authentication Tests
# =============================================================================


class TestCRUDUserAuthenticate:
    """Tests for user authentication via CRUD."""

    @pytest.mark.asyncio
    async def test_authenticate_success(self, db_session, crud_user):
        """Test successful authentication."""
        # Create user with known password
        await crud_user.create(
            db_session,
            obj_in={
                "email": "authtest@test.com",
                "password": "correctpassword",
                "full_name": "Auth Test",
            }
        )

        user = await crud_user.authenticate(
            db_session, email="authtest@test.com", password="correctpassword"
        )

        assert user is not None
        assert user.email == "authtest@test.com"

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self, db_session, crud_user, test_user_in_db):
        """Test authentication with wrong password."""
        user = await crud_user.authenticate(
            db_session, email=test_user_in_db.email, password="wrongpassword"
        )

        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_nonexistent_user(self, db_session, crud_user):
        """Test authentication with non-existent user."""
        user = await crud_user.authenticate(
            db_session, email="nobody@test.com", password="password"
        )

        assert user is None


# =============================================================================
# Status Check Tests
# =============================================================================


class TestCRUDUserStatus:
    """Tests for user status checks."""

    @pytest.mark.asyncio
    async def test_is_active_true(self, crud_user, test_user_in_db):
        """Test is_active returns True for active user."""
        result = await crud_user.is_active(test_user_in_db)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_active_false(self, crud_user):
        """Test is_active returns False for inactive user."""
        inactive_user = User(
            email="inactive@test.com",
            hashed_password="hash",
            is_active=False,
        )
        result = await crud_user.is_active(inactive_user)
        assert result is False

    @pytest.mark.asyncio
    async def test_is_verified_true(self, crud_user, test_user_in_db):
        """Test is_verified returns True for verified user."""
        result = await crud_user.is_verified(test_user_in_db)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_verified_false(self, crud_user):
        """Test is_verified returns False for unverified user."""
        unverified = User(
            email="unverified@test.com",
            hashed_password="hash",
            is_verified=False,
        )
        result = await crud_user.is_verified(unverified)
        assert result is False


# =============================================================================
# Last Login Tests
# =============================================================================


class TestCRUDUserLastLogin:
    """Tests for updating last login."""

    @pytest.mark.asyncio
    async def test_update_last_login(self, db_session, crud_user, test_user_in_db):
        """Test updating last login timestamp."""
        original_login = test_user_in_db.last_login

        updated = await crud_user.update_last_login(db_session, user=test_user_in_db)

        assert updated.last_login is not None
        if original_login:
            assert updated.last_login >= original_login


# =============================================================================
# Remove Tests
# =============================================================================


class TestCRUDUserRemove:
    """Tests for removing users."""

    @pytest.mark.asyncio
    async def test_remove_user(self, db_session, crud_user):
        """Test removing user."""
        # Create user to remove
        user = await crud_user.create(
            db_session,
            obj_in={
                "email": "removetest@test.com",
                "password": "password123",
                "full_name": "Remove Test",
            }
        )
        user_id = user.id

        # Remove user
        removed = await crud_user.remove(db_session, id=user_id)

        assert removed is not None
        assert removed.id == user_id

        # Verify user is gone
        result = await crud_user.get(db_session, user_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_remove_nonexistent_user(self, db_session, crud_user):
        """Test removing non-existent user returns None."""
        result = await crud_user.remove(db_session, id=99999)
        assert result is None


# =============================================================================
# Count Tests
# =============================================================================


class TestCRUDUserCount:
    """Tests for counting users."""

    @pytest.mark.asyncio
    async def test_count_users(self, db_session, crud_user, test_user_in_db):
        """Test counting all users."""
        count = await crud_user.count(db_session)

        assert count >= 1

    @pytest.mark.asyncio
    async def test_count_with_filters(self, db_session, crud_user, test_user_in_db):
        """Test counting users with filters."""
        count = await crud_user.count(
            db_session,
            filters={"email": test_user_in_db.email}
        )

        assert count == 1


# =============================================================================
# Singleton Tests
# =============================================================================


class TestCRUDUserSingleton:
    """Tests for CRUD singleton instance."""

    def test_singleton_exists(self):
        """Test that singleton instance exists."""
        assert user_crud is not None
        assert isinstance(user_crud, CRUDUser)

    def test_singleton_model_is_user(self):
        """Test singleton is configured with User model."""
        assert user_crud.model == User
