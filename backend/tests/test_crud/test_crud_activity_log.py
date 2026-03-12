"""Tests for ActivityLog CRUD operations.

Covers CRUDActivityLog:
- create_for_deal: generic creation with action, description, metadata
- log_stage_change: stage transition logging
- log_creation: deal creation logging
- log_update: field change logging
- get_by_deal: retrieval with filtering and pagination
- count_by_deal: counting with filters
- get_recent_for_deals: batch-fetch recent activities for multiple deals
- Soft-delete awareness (is_deleted filter)
"""

from datetime import UTC, datetime

import pytest

from app.crud.crud_activity_log import activity_log
from app.models.activity_log import ActivityAction, ActivityLog

# =============================================================================
# Helpers
# =============================================================================


async def _create_log_entries(
    db_session,
    deal_id: int,
    n: int = 3,
    action: ActivityAction = ActivityAction.VIEWED,
) -> list[ActivityLog]:
    """Create N activity log entries for a deal."""
    entries = []
    for i in range(n):
        entry = await activity_log.create_for_deal(
            db_session,
            deal_id=deal_id,
            action=action,
            description=f"Test entry {i}",
            user_id=f"user_{i}",
        )
        entries.append(entry)
    return entries


# =============================================================================
# create_for_deal
# =============================================================================


class TestCreateForDeal:
    """Tests for create_for_deal."""

    @pytest.mark.asyncio
    async def test_creates_with_required_fields(self, db_session, test_deal):
        """create_for_deal persists with correct action and description."""
        entry = await activity_log.create_for_deal(
            db_session,
            deal_id=test_deal.id,
            action=ActivityAction.CREATED,
            description="Deal created",
        )

        assert entry.id is not None
        assert entry.deal_id == test_deal.id
        assert entry.action == ActivityAction.CREATED
        assert entry.description == "Deal created"
        assert entry.user_id is None
        assert entry.meta is None

    @pytest.mark.asyncio
    async def test_creates_with_user_and_metadata(self, db_session, test_deal):
        """create_for_deal stores user_id and JSON metadata."""
        meta = {"old_stage": "initial_review", "new_stage": "active_review"}
        entry = await activity_log.create_for_deal(
            db_session,
            deal_id=test_deal.id,
            action=ActivityAction.STAGE_CHANGED,
            description="Stage changed",
            user_id="user_123",
            meta=meta,
        )

        assert entry.user_id == "user_123"
        assert entry.meta == meta

    @pytest.mark.asyncio
    async def test_uuid_primary_key(self, db_session, test_deal):
        """Each entry gets a unique UUID primary key."""
        entry1 = await activity_log.create_for_deal(
            db_session,
            deal_id=test_deal.id,
            action=ActivityAction.VIEWED,
            description="View 1",
        )
        entry2 = await activity_log.create_for_deal(
            db_session,
            deal_id=test_deal.id,
            action=ActivityAction.VIEWED,
            description="View 2",
        )

        assert entry1.id != entry2.id
        assert entry1.id is not None
        assert entry2.id is not None

    @pytest.mark.asyncio
    async def test_created_at_populated(self, db_session, test_deal):
        """created_at is populated automatically."""
        entry = await activity_log.create_for_deal(
            db_session,
            deal_id=test_deal.id,
            action=ActivityAction.VIEWED,
            description="Test",
        )
        assert entry.created_at is not None

    @pytest.mark.asyncio
    async def test_is_deleted_defaults_false(self, db_session, test_deal):
        """New entries have is_deleted=False by default."""
        entry = await activity_log.create_for_deal(
            db_session,
            deal_id=test_deal.id,
            action=ActivityAction.VIEWED,
            description="Test",
        )
        assert entry.is_deleted is False


# =============================================================================
# log_stage_change
# =============================================================================


class TestLogStageChange:
    """Tests for log_stage_change."""

    @pytest.mark.asyncio
    async def test_logs_stage_transition(self, db_session, test_deal):
        """log_stage_change creates STAGE_CHANGED entry with metadata."""
        entry = await activity_log.log_stage_change(
            db_session,
            deal_id=test_deal.id,
            old_stage="initial_review",
            new_stage="active_review",
            user_id="admin_1",
        )

        assert entry.action == ActivityAction.STAGE_CHANGED
        assert "initial_review" in entry.description
        assert "active_review" in entry.description
        assert entry.meta["old_stage"] == "initial_review"
        assert entry.meta["new_stage"] == "active_review"
        assert entry.user_id == "admin_1"

    @pytest.mark.asyncio
    async def test_logs_stage_change_without_user(self, db_session, test_deal):
        """log_stage_change works without user_id."""
        entry = await activity_log.log_stage_change(
            db_session,
            deal_id=test_deal.id,
            old_stage="active_review",
            new_stage="under_contract",
        )
        assert entry.user_id is None
        assert entry.action == ActivityAction.STAGE_CHANGED


# =============================================================================
# log_creation
# =============================================================================


class TestLogCreation:
    """Tests for log_creation."""

    @pytest.mark.asyncio
    async def test_logs_deal_creation(self, db_session, test_deal):
        """log_creation creates a CREATED entry with deal name in metadata."""
        entry = await activity_log.log_creation(
            db_session,
            deal_id=test_deal.id,
            deal_name="Test Acquisition",
            user_id="creator_1",
        )

        assert entry.action == ActivityAction.CREATED
        assert "Test Acquisition" in entry.description
        assert entry.meta["deal_name"] == "Test Acquisition"
        assert entry.user_id == "creator_1"

    @pytest.mark.asyncio
    async def test_logs_creation_without_user(self, db_session, test_deal):
        """log_creation works without user_id."""
        entry = await activity_log.log_creation(
            db_session,
            deal_id=test_deal.id,
            deal_name="Auto-Created Deal",
        )
        assert entry.user_id is None


# =============================================================================
# log_update
# =============================================================================


class TestLogUpdate:
    """Tests for log_update."""

    @pytest.mark.asyncio
    async def test_logs_field_changes(self, db_session, test_deal):
        """log_update records changed fields and values."""
        entry = await activity_log.log_update(
            db_session,
            deal_id=test_deal.id,
            changed_fields=["name", "priority"],
            user_id="editor_1",
            old_values={"name": "Old Name", "priority": "medium"},
            new_values={"name": "New Name", "priority": "high"},
        )

        assert entry.action == ActivityAction.UPDATED
        assert "name" in entry.description
        assert "priority" in entry.description
        assert entry.meta["changed_fields"] == ["name", "priority"]
        assert entry.meta["old_values"]["name"] == "Old Name"
        assert entry.meta["new_values"]["priority"] == "high"

    @pytest.mark.asyncio
    async def test_logs_update_without_values(self, db_session, test_deal):
        """log_update works without old_values and new_values."""
        entry = await activity_log.log_update(
            db_session,
            deal_id=test_deal.id,
            changed_fields=["asking_price"],
        )

        assert entry.meta["changed_fields"] == ["asking_price"]
        assert "old_values" not in entry.meta
        assert "new_values" not in entry.meta

    @pytest.mark.asyncio
    async def test_logs_update_single_field(self, db_session, test_deal):
        """log_update works with a single field change."""
        entry = await activity_log.log_update(
            db_session,
            deal_id=test_deal.id,
            changed_fields=["stage"],
        )
        assert "stage" in entry.description


# =============================================================================
# get_by_deal
# =============================================================================


class TestGetByDeal:
    """Tests for get_by_deal."""

    @pytest.mark.asyncio
    async def test_returns_entries_for_deal(self, db_session, test_deal):
        """get_by_deal returns all non-deleted entries for a deal."""
        await _create_log_entries(db_session, test_deal.id, n=3)
        results = await activity_log.get_by_deal(db_session, deal_id=test_deal.id)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_empty_for_unknown_deal(self, db_session):
        """get_by_deal returns empty list for unknown deal."""
        results = await activity_log.get_by_deal(db_session, deal_id=99999)
        assert results == []

    @pytest.mark.asyncio
    async def test_filters_by_action(self, db_session, test_deal):
        """get_by_deal filters by action string."""
        await _create_log_entries(db_session, test_deal.id, 2, ActivityAction.VIEWED)
        await _create_log_entries(db_session, test_deal.id, 1, ActivityAction.CREATED)

        viewed = await activity_log.get_by_deal(
            db_session, deal_id=test_deal.id, action="viewed"
        )
        assert len(viewed) == 2

        created = await activity_log.get_by_deal(
            db_session, deal_id=test_deal.id, action="created"
        )
        assert len(created) == 1

    @pytest.mark.asyncio
    async def test_invalid_action_ignored(self, db_session, test_deal):
        """Invalid action string is silently ignored (returns all)."""
        await _create_log_entries(db_session, test_deal.id, 3)
        results = await activity_log.get_by_deal(
            db_session, deal_id=test_deal.id, action="nonexistent_action"
        )
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_pagination(self, db_session, test_deal):
        """get_by_deal supports skip and limit."""
        await _create_log_entries(db_session, test_deal.id, 5)

        page1 = await activity_log.get_by_deal(
            db_session, deal_id=test_deal.id, skip=0, limit=2
        )
        assert len(page1) == 2

        page2 = await activity_log.get_by_deal(
            db_session, deal_id=test_deal.id, skip=2, limit=2
        )
        assert len(page2) == 2

    @pytest.mark.asyncio
    async def test_excludes_soft_deleted(self, db_session, test_deal):
        """get_by_deal excludes soft-deleted entries."""
        entries = await _create_log_entries(db_session, test_deal.id, 3)

        # Soft-delete one
        entries[0].is_deleted = True
        entries[0].deleted_at = datetime.now(UTC)
        db_session.add(entries[0])
        await db_session.flush()

        results = await activity_log.get_by_deal(db_session, deal_id=test_deal.id)
        assert len(results) == 2


# =============================================================================
# count_by_deal
# =============================================================================


class TestCountByDeal:
    """Tests for count_by_deal."""

    @pytest.mark.asyncio
    async def test_correct_count(self, db_session, test_deal):
        """count_by_deal returns accurate count."""
        await _create_log_entries(db_session, test_deal.id, 4)
        count = await activity_log.count_by_deal(db_session, deal_id=test_deal.id)
        assert count == 4

    @pytest.mark.asyncio
    async def test_zero_for_unknown_deal(self, db_session):
        """count_by_deal returns 0 for unknown deal."""
        count = await activity_log.count_by_deal(db_session, deal_id=99999)
        assert count == 0

    @pytest.mark.asyncio
    async def test_filters_by_action(self, db_session, test_deal):
        """count_by_deal filters by action."""
        await _create_log_entries(db_session, test_deal.id, 3, ActivityAction.VIEWED)
        await _create_log_entries(db_session, test_deal.id, 1, ActivityAction.CREATED)

        viewed_count = await activity_log.count_by_deal(
            db_session, deal_id=test_deal.id, action="viewed"
        )
        assert viewed_count == 3


# =============================================================================
# get_recent_for_deals
# =============================================================================


class TestGetRecentForDeals:
    """Tests for get_recent_for_deals (batch fetch)."""

    @pytest.mark.asyncio
    async def test_returns_grouped_by_deal(self, db_session, multiple_deals):
        """get_recent_for_deals returns dict keyed by deal_id."""
        for deal in multiple_deals[:2]:
            await _create_log_entries(db_session, deal.id, 2)

        deal_ids = [d.id for d in multiple_deals[:2]]
        result = await activity_log.get_recent_for_deals(db_session, deal_ids=deal_ids)

        assert isinstance(result, dict)
        for deal_id in deal_ids:
            assert deal_id in result
            assert len(result[deal_id]) == 2

    @pytest.mark.asyncio
    async def test_empty_list_returns_empty_dict(self, db_session):
        """get_recent_for_deals returns {} for empty deal_ids list."""
        result = await activity_log.get_recent_for_deals(db_session, deal_ids=[])
        assert result == {}

    @pytest.mark.asyncio
    async def test_respects_limit_per_deal(self, db_session, test_deal):
        """get_recent_for_deals limits activities per deal."""
        await _create_log_entries(db_session, test_deal.id, 5)

        result = await activity_log.get_recent_for_deals(
            db_session, deal_ids=[test_deal.id], limit_per_deal=2
        )

        assert len(result[test_deal.id]) == 2

    @pytest.mark.asyncio
    async def test_excludes_soft_deleted(self, db_session, test_deal):
        """get_recent_for_deals excludes soft-deleted entries."""
        entries = await _create_log_entries(db_session, test_deal.id, 3)

        # Soft-delete one
        entries[0].is_deleted = True
        entries[0].deleted_at = datetime.now(UTC)
        db_session.add(entries[0])
        await db_session.flush()

        result = await activity_log.get_recent_for_deals(
            db_session, deal_ids=[test_deal.id], limit_per_deal=10
        )

        assert len(result[test_deal.id]) == 2

    @pytest.mark.asyncio
    async def test_deals_with_no_activities_excluded(self, db_session, multiple_deals):
        """Deals with no activity logs are not present in result dict."""
        # Only create activities for the first deal
        await _create_log_entries(db_session, multiple_deals[0].id, 2)

        deal_ids = [d.id for d in multiple_deals[:3]]
        result = await activity_log.get_recent_for_deals(db_session, deal_ids=deal_ids)

        assert multiple_deals[0].id in result
        assert multiple_deals[1].id not in result
        assert multiple_deals[2].id not in result
