"""Tests for the User model."""
import pytest
from sqlalchemy import select

from app.core.security import get_password_hash, verify_password
from app.models import User


@pytest.mark.asyncio
async def test_create_user(db_session):
    """Test creating a new user."""
    user = User(
        email="newuser@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="New User",
        role="viewer",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.email == "newuser@example.com"
    assert user.full_name == "New User"
    assert user.role == "viewer"
    assert user.is_active is True


@pytest.mark.asyncio
async def test_user_password_hashing(db_session):
    """Test that passwords are properly hashed."""
    password = "securepassword123"
    user = User(
        email="hashtest@example.com",
        hashed_password=get_password_hash(password),
        full_name="Hash Test",
        role="analyst",
    )
    db_session.add(user)
    await db_session.commit()

    # Password should be hashed, not plain text
    assert user.hashed_password != password
    # But should verify correctly
    assert verify_password(password, user.hashed_password)
    # Wrong password should fail
    assert not verify_password("wrongpassword", user.hashed_password)


@pytest.mark.asyncio
async def test_user_unique_email(db_session):
    """Test that duplicate emails raise an error."""
    user1 = User(
        email="duplicate@example.com",
        hashed_password=get_password_hash("password"),
        full_name="User 1",
        role="viewer",
    )
    db_session.add(user1)
    await db_session.commit()

    user2 = User(
        email="duplicate@example.com",
        hashed_password=get_password_hash("password"),
        full_name="User 2",
        role="viewer",
    )
    db_session.add(user2)

    with pytest.raises(Exception):  # IntegrityError
        await db_session.commit()


@pytest.mark.asyncio
async def test_user_fixture(test_user):
    """Test that the test_user fixture works."""
    assert test_user.id is not None
    assert test_user.email == "test@example.com"
    assert test_user.role == "analyst"


@pytest.mark.asyncio
async def test_admin_user_fixture(admin_user):
    """Test that the admin_user fixture works."""
    assert admin_user.id is not None
    assert admin_user.email == "admin@example.com"
    assert admin_user.role == "admin"


@pytest.mark.asyncio
async def test_user_repr(test_user):
    """Test the User __repr__ method."""
    assert "<User" in repr(test_user)
    assert test_user.email in repr(test_user)
