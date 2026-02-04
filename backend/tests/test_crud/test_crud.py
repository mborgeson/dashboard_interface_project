"""Unit tests for CRUD layer operations.

Tests the CRUD base class and model-specific CRUD classes:
- CRUDBase: Generic CRUD operations
- CRUDUser: User-specific operations with password hashing
- CRUDDeal: Deal-specific operations with stage management
"""

from datetime import date
from decimal import Decimal

import pytest

from app.core.security import verify_password
from app.crud.base import CRUDBase
from app.crud.crud_deal import CRUDDeal
from app.crud.crud_deal import deal as deal_crud
from app.crud.crud_user import CRUDUser
from app.crud.crud_user import user as user_crud
from app.models import Deal, DealStage, User

# =============================================================================
# CRUDUser Tests
# =============================================================================


@pytest.mark.asyncio
async def test_crud_user_create_hashes_password(db_session):
    """Test that user creation properly hashes the password."""
    user_data = {
        "email": "hashtest@example.com",
        "password": "plaintext123",
        "full_name": "Hash Test User",
        "role": "analyst",
        "is_active": True,
    }

    created_user = await user_crud.create(db_session, obj_in=user_data)

    # Password should be hashed, not plaintext
    assert created_user.hashed_password is not None
    assert created_user.hashed_password != "plaintext123"
    assert verify_password("plaintext123", created_user.hashed_password)


@pytest.mark.asyncio
async def test_crud_user_get_by_email(db_session, test_user):
    """Test getting user by email address."""
    found_user = await user_crud.get_by_email(db_session, email=test_user.email)

    assert found_user is not None
    assert found_user.id == test_user.id
    assert found_user.email == test_user.email


@pytest.mark.asyncio
async def test_crud_user_get_by_email_not_found(db_session):
    """Test getting non-existent user by email returns None."""
    found_user = await user_crud.get_by_email(
        db_session, email="nonexistent@example.com"
    )

    assert found_user is None


@pytest.mark.asyncio
async def test_crud_user_authenticate_success(db_session):
    """Test successful user authentication."""
    # Create user with known password
    user_data = {
        "email": "authtest@example.com",
        "password": "correctpassword",
        "full_name": "Auth Test",
        "role": "analyst",
        "is_active": True,
    }
    await user_crud.create(db_session, obj_in=user_data)

    # Authenticate with correct credentials
    authenticated = await user_crud.authenticate(
        db_session, email="authtest@example.com", password="correctpassword"
    )

    assert authenticated is not None
    assert authenticated.email == "authtest@example.com"


@pytest.mark.asyncio
async def test_crud_user_authenticate_wrong_password(db_session):
    """Test authentication fails with wrong password."""
    user_data = {
        "email": "wrongpw@example.com",
        "password": "correctpassword",
        "full_name": "Wrong PW Test",
        "role": "analyst",
        "is_active": True,
    }
    await user_crud.create(db_session, obj_in=user_data)

    authenticated = await user_crud.authenticate(
        db_session, email="wrongpw@example.com", password="wrongpassword"
    )

    assert authenticated is None


@pytest.mark.asyncio
async def test_crud_user_authenticate_nonexistent_user(db_session):
    """Test authentication fails for non-existent user."""
    authenticated = await user_crud.authenticate(
        db_session, email="nouser@example.com", password="anypassword"
    )

    assert authenticated is None


@pytest.mark.asyncio
async def test_crud_user_is_active(test_user):
    """Test is_active check."""
    is_active = await user_crud.is_active(test_user)
    assert is_active is True


@pytest.mark.asyncio
async def test_crud_user_is_verified(test_user):
    """Test is_verified check."""
    is_verified = await user_crud.is_verified(test_user)
    assert is_verified is True


# =============================================================================
# CRUDDeal Tests
# =============================================================================


@pytest.mark.asyncio
async def test_crud_deal_get_by_stage(db_session, multiple_deals):
    """Test getting deals filtered by stage."""
    leads = await deal_crud.get_by_stage(db_session, stage=DealStage.INITIAL_REVIEW)

    assert len(leads) >= 1
    for deal in leads:
        assert deal.stage == DealStage.INITIAL_REVIEW


@pytest.mark.asyncio
async def test_crud_deal_get_multi_filtered(db_session, multiple_deals):
    """Test getting deals with multiple filters."""
    deals = await deal_crud.get_multi_filtered(db_session, stage="initial_review", limit=10)

    for deal in deals:
        assert deal.stage == DealStage.INITIAL_REVIEW


@pytest.mark.asyncio
async def test_crud_deal_get_multi_filtered_by_priority(db_session, test_deal):
    """Test filtering deals by priority."""
    deals = await deal_crud.get_multi_filtered(db_session, priority="high")

    for deal in deals:
        assert deal.priority == "high"


@pytest.mark.asyncio
async def test_crud_deal_count_filtered(db_session, multiple_deals):
    """Test counting deals with filters."""
    count = await deal_crud.count_filtered(db_session)
    assert count >= 4  # multiple_deals creates 4


@pytest.mark.asyncio
async def test_crud_deal_count_by_stage(db_session, multiple_deals):
    """Test counting deals by stage."""
    count = await deal_crud.count_filtered(db_session, stage="initial_review")
    assert count >= 1


@pytest.mark.asyncio
async def test_crud_deal_get_kanban_data(db_session, multiple_deals):
    """Test getting Kanban board data."""
    kanban = await deal_crud.get_kanban_data(db_session)

    assert "stages" in kanban
    assert "total_deals" in kanban
    assert "stage_counts" in kanban
    assert kanban["total_deals"] >= 4


@pytest.mark.asyncio
async def test_crud_deal_update_stage(db_session, test_deal):
    """Test updating deal stage."""
    updated = await deal_crud.update_stage(
        db_session,
        deal_id=test_deal.id,
        new_stage=DealStage.UNDER_CONTRACT,
    )

    assert updated is not None
    assert updated.stage == DealStage.UNDER_CONTRACT


@pytest.mark.asyncio
async def test_crud_deal_update_stage_not_found(db_session):
    """Test updating stage of non-existent deal returns None."""
    updated = await deal_crud.update_stage(
        db_session,
        deal_id=99999,
        new_stage=DealStage.CLOSED,
    )

    assert updated is None


# =============================================================================
# CRUDBase Tests (via Deal model)
# =============================================================================


@pytest.mark.asyncio
async def test_crud_base_get(db_session, test_deal):
    """Test getting record by ID."""
    found = await deal_crud.get(db_session, test_deal.id)

    assert found is not None
    assert found.id == test_deal.id


@pytest.mark.asyncio
async def test_crud_base_get_not_found(db_session):
    """Test getting non-existent record returns None."""
    found = await deal_crud.get(db_session, 99999)

    assert found is None


@pytest.mark.asyncio
async def test_crud_base_get_multi(db_session, multiple_deals):
    """Test getting multiple records with pagination."""
    deals = await deal_crud.get_multi(db_session, skip=0, limit=2)

    assert len(deals) == 2


@pytest.mark.asyncio
async def test_crud_base_create(db_session, test_user):
    """Test creating a new record."""
    deal_data = {
        "name": "CRUD Test Deal",
        "deal_type": "acquisition",
        "stage": DealStage.INITIAL_REVIEW,
        "assigned_user_id": test_user.id,
        "priority": "low",
    }

    created = await deal_crud.create(db_session, obj_in=deal_data)

    assert created.id is not None
    assert created.name == "CRUD Test Deal"


@pytest.mark.asyncio
async def test_crud_base_update(db_session, test_deal):
    """Test updating a record."""
    update_data = {"name": "Updated Deal Name", "priority": "low"}

    updated = await deal_crud.update(db_session, db_obj=test_deal, obj_in=update_data)

    assert updated.name == "Updated Deal Name"
    assert updated.priority == "low"


@pytest.mark.asyncio
async def test_crud_base_remove(db_session, test_user):
    """Test removing a record."""
    # Create a deal to delete
    deal_data = {
        "name": "Delete Me",
        "deal_type": "disposition",
        "stage": DealStage.DEAD,
        "assigned_user_id": test_user.id,
        "priority": "low",
    }
    created = await deal_crud.create(db_session, obj_in=deal_data)
    deal_id = created.id

    # Remove it
    removed = await deal_crud.remove(db_session, id=deal_id)

    assert removed is not None

    # Verify it's gone
    found = await deal_crud.get(db_session, deal_id)
    assert found is None


@pytest.mark.asyncio
async def test_crud_base_count(db_session, multiple_deals):
    """Test counting records."""
    count = await deal_crud.count(db_session)

    assert count >= 4
