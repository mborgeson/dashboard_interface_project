"""Tests for Deal CRUD operations.

Covers:
- Deal creation and retrieval
- Stage filtering and Kanban data
- Multi-filter queries
- Optimistic locking
- Stage updates
- Count operations
"""

from datetime import date
from decimal import Decimal

import pytest

from app.crud.crud_deal import deal as deal_crud
from app.models import Deal, DealStage


# =============================================================================
# Basic CRUD
# =============================================================================


@pytest.mark.asyncio
async def test_create_deal(db_session, test_user):
    """Create a deal and verify fields are persisted."""
    created = await deal_crud.create(
        db_session,
        obj_in={
            "name": "New Acquisition Deal",
            "deal_type": "acquisition",
            "stage": DealStage.INITIAL_REVIEW,
            "stage_order": 0,
            "assigned_user_id": test_user.id,
            "asking_price": Decimal("12000000.00"),
            "priority": "high",
        },
    )

    assert created.id is not None
    assert created.name == "New Acquisition Deal"
    assert created.stage == DealStage.INITIAL_REVIEW
    assert created.asking_price == Decimal("12000000.00")
    assert created.priority == "high"


@pytest.mark.asyncio
async def test_get_deal(db_session, test_deal):
    """Retrieve a deal by ID."""
    found = await deal_crud.get(db_session, test_deal.id)
    assert found is not None
    assert found.id == test_deal.id
    assert found.name == test_deal.name


@pytest.mark.asyncio
async def test_get_nonexistent_deal(db_session):
    """Getting a non-existent deal returns None."""
    found = await deal_crud.get(db_session, 99999)
    assert found is None


@pytest.mark.asyncio
async def test_get_with_relations(db_session, test_deal):
    """get_with_relations returns the deal."""
    found = await deal_crud.get_with_relations(db_session, id=test_deal.id)
    assert found is not None
    assert found.id == test_deal.id


# =============================================================================
# Stage Filtering
# =============================================================================


@pytest.mark.asyncio
async def test_get_by_stage(db_session, multiple_deals):
    """Filter deals by stage."""
    active_deals = await deal_crud.get_by_stage(
        db_session, stage=DealStage.ACTIVE_REVIEW
    )
    assert len(active_deals) == 1
    assert active_deals[0].stage == DealStage.ACTIVE_REVIEW


@pytest.mark.asyncio
async def test_get_by_stage_empty(db_session, multiple_deals):
    """Filtering by stage with no matches returns empty list."""
    realized = await deal_crud.get_by_stage(
        db_session, stage=DealStage.REALIZED
    )
    assert realized == []


# =============================================================================
# Multi-Filter Queries
# =============================================================================


@pytest.mark.asyncio
async def test_get_multi_filtered_by_stage(db_session, multiple_deals):
    """Filter deals by stage string."""
    results = await deal_crud.get_multi_filtered(
        db_session, stage="closed"
    )
    assert len(results) == 1
    assert results[0].stage == DealStage.CLOSED


@pytest.mark.asyncio
async def test_get_multi_filtered_by_priority(db_session, test_deal):
    """Filter deals by priority."""
    results = await deal_crud.get_multi_filtered(
        db_session, priority="high"
    )
    assert len(results) == 1
    assert results[0].priority == "high"


@pytest.mark.asyncio
async def test_get_multi_filtered_invalid_stage_ignored(db_session, multiple_deals):
    """Invalid stage string is silently ignored (returns all deals)."""
    results = await deal_crud.get_multi_filtered(
        db_session, stage="nonexistent_stage"
    )
    # Invalid stage is ignored, so all deals returned
    assert len(results) == len(multiple_deals)


@pytest.mark.asyncio
async def test_count_filtered(db_session, multiple_deals):
    """Count deals matching a filter."""
    count = await deal_crud.count_filtered(db_session, stage="active_review")
    assert count == 1

    total = await deal_crud.count_filtered(db_session)
    assert total == len(multiple_deals)


# =============================================================================
# Kanban Data
# =============================================================================


@pytest.mark.asyncio
async def test_get_kanban_data(db_session, multiple_deals):
    """Kanban data groups deals by stage with counts."""
    kanban = await deal_crud.get_kanban_data(db_session)

    assert kanban["total_deals"] == len(multiple_deals)
    assert "stages" in kanban
    assert "stage_counts" in kanban
    # Check that we have all stage keys
    for stage in DealStage:
        assert stage.value in kanban["stages"]
        assert stage.value in kanban["stage_counts"]

    # Check specific counts
    assert kanban["stage_counts"]["active_review"] == 1
    assert kanban["stage_counts"]["closed"] == 1


@pytest.mark.asyncio
async def test_get_kanban_data_with_filter(db_session, multiple_deals, test_user):
    """Kanban data can be filtered by assigned user."""
    kanban = await deal_crud.get_kanban_data(
        db_session, assigned_user_id=test_user.id
    )
    assert kanban["total_deals"] == len(multiple_deals)


# =============================================================================
# Optimistic Locking
# =============================================================================


@pytest.mark.asyncio
async def test_update_optimistic_success(db_session, test_deal):
    """Optimistic update succeeds when version matches."""
    original_version = test_deal.version
    updated = await deal_crud.update_optimistic(
        db_session,
        deal_id=test_deal.id,
        expected_version=original_version,
        update_data={"name": "Updated Deal Name"},
    )

    assert updated is not None
    assert updated.name == "Updated Deal Name"
    assert updated.version == original_version + 1


@pytest.mark.asyncio
async def test_update_optimistic_stale_version(db_session, test_deal):
    """Optimistic update fails when version is stale."""
    result = await deal_crud.update_optimistic(
        db_session,
        deal_id=test_deal.id,
        expected_version=test_deal.version + 100,  # Wrong version
        update_data={"name": "Should Not Apply"},
    )

    assert result is None


@pytest.mark.asyncio
async def test_update_optimistic_nonexistent_deal(db_session):
    """Optimistic update on non-existent deal returns None."""
    result = await deal_crud.update_optimistic(
        db_session,
        deal_id=99999,
        expected_version=1,
        update_data={"name": "Ghost"},
    )

    assert result is None


# =============================================================================
# Stage Update
# =============================================================================


@pytest.mark.asyncio
async def test_update_stage(db_session, test_deal):
    """Update a deal's stage."""
    updated = await deal_crud.update_stage(
        db_session,
        deal_id=test_deal.id,
        new_stage=DealStage.UNDER_CONTRACT,
    )

    assert updated is not None
    assert updated.stage == DealStage.UNDER_CONTRACT


@pytest.mark.asyncio
async def test_update_stage_with_order(db_session, test_deal):
    """Update stage and ordering position."""
    updated = await deal_crud.update_stage(
        db_session,
        deal_id=test_deal.id,
        new_stage=DealStage.CLOSED,
        stage_order=5,
    )

    assert updated is not None
    assert updated.stage == DealStage.CLOSED
    assert updated.stage_order == 5


@pytest.mark.asyncio
async def test_update_stage_nonexistent(db_session):
    """Updating stage of non-existent deal returns None."""
    result = await deal_crud.update_stage(
        db_session, deal_id=99999, new_stage=DealStage.DEAD
    )
    assert result is None


# =============================================================================
# Build Conditions
# =============================================================================


class TestBuildDealConditions:
    """Test the internal _build_deal_conditions method."""

    def test_no_filters(self):
        conditions = deal_crud._build_deal_conditions()
        assert conditions == []

    def test_valid_stage_filter(self):
        conditions = deal_crud._build_deal_conditions(stage="active_review")
        assert len(conditions) == 1

    def test_invalid_stage_filter_ignored(self):
        conditions = deal_crud._build_deal_conditions(stage="invalid")
        assert conditions == []

    def test_multiple_filters(self):
        conditions = deal_crud._build_deal_conditions(
            stage="closed",
            deal_type="acquisition",
            priority="high",
            assigned_user_id=1,
        )
        assert len(conditions) == 4
