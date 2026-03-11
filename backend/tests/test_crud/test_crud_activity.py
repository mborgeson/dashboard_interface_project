"""Tests for Activity CRUD operations.

Covers CRUDPropertyActivity, CRUDDealActivity, and CRUDWatchlist:
- PropertyActivity: get_by_property, count_by_property, log_view, log_edit
- DealActivity: get_by_deal, count_by_deal
- Watchlist: get_by_user, get_by_user_and_deal, is_watching,
  add_to_watchlist, remove_from_watchlist, toggle_watchlist, count_by_user
"""

from datetime import UTC, datetime

import pytest

from app.crud.crud_activity import deal_activity, property_activity, watchlist
from app.models.activity import ActivityType, DealActivity, PropertyActivity


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def _seed_property_activities(db_session, test_property, test_user):
    """Return an async callable that creates N property activities."""

    async def _create(n: int = 3, activity_type: ActivityType = ActivityType.VIEW):
        activities = []
        for i in range(n):
            act = PropertyActivity(
                property_id=test_property.id,
                user_id=test_user.id,
                activity_type=activity_type,
                description=f"Activity {i}",
                created_at=datetime.now(UTC),
            )
            db_session.add(act)
            activities.append(act)
        await db_session.flush()
        for act in activities:
            await db_session.refresh(act)
        return activities

    return _create


@pytest.fixture
def _seed_deal_activities(db_session, test_deal, test_user):
    """Return an async callable that creates N deal activities."""

    async def _create(n: int = 3, activity_type: ActivityType = ActivityType.VIEW):
        activities = []
        for i in range(n):
            act = DealActivity(
                deal_id=test_deal.id,
                user_id=test_user.id,
                activity_type=activity_type,
                description=f"Deal activity {i}",
                created_at=datetime.now(UTC),
            )
            db_session.add(act)
            activities.append(act)
        await db_session.flush()
        for act in activities:
            await db_session.refresh(act)
        return activities

    return _create


# =============================================================================
# CRUDPropertyActivity Tests
# =============================================================================


class TestCRUDPropertyActivity:
    """Tests for CRUDPropertyActivity."""

    @pytest.mark.asyncio
    async def test_get_by_property_returns_activities(
        self, db_session, test_property, _seed_property_activities
    ):
        """get_by_property returns activities for the given property."""
        created = await _seed_property_activities(3)
        results = await property_activity.get_by_property(
            db_session, property_id=test_property.id
        )
        assert len(results) == 3
        for act in results:
            assert act.property_id == test_property.id

    @pytest.mark.asyncio
    async def test_get_by_property_empty(self, db_session):
        """get_by_property returns empty list for unknown property."""
        results = await property_activity.get_by_property(
            db_session, property_id=99999
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_get_by_property_with_type_filter(
        self, db_session, test_property, _seed_property_activities
    ):
        """get_by_property filters by activity_type string."""
        await _seed_property_activities(2, ActivityType.VIEW)
        await _seed_property_activities(1, ActivityType.EDIT)

        views = await property_activity.get_by_property(
            db_session, property_id=test_property.id, activity_type="view"
        )
        assert len(views) == 2

        edits = await property_activity.get_by_property(
            db_session, property_id=test_property.id, activity_type="edit"
        )
        assert len(edits) == 1

    @pytest.mark.asyncio
    async def test_get_by_property_invalid_type_ignored(
        self, db_session, test_property, _seed_property_activities
    ):
        """Invalid activity_type string is silently ignored (returns all)."""
        await _seed_property_activities(3)
        results = await property_activity.get_by_property(
            db_session,
            property_id=test_property.id,
            activity_type="nonexistent_type",
        )
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_get_by_property_pagination(
        self, db_session, test_property, _seed_property_activities
    ):
        """get_by_property supports skip and limit."""
        await _seed_property_activities(5)

        page1 = await property_activity.get_by_property(
            db_session, property_id=test_property.id, skip=0, limit=2
        )
        assert len(page1) == 2

        page2 = await property_activity.get_by_property(
            db_session, property_id=test_property.id, skip=2, limit=2
        )
        assert len(page2) == 2

        # IDs should not overlap
        page1_ids = {a.id for a in page1}
        page2_ids = {a.id for a in page2}
        assert page1_ids.isdisjoint(page2_ids)

    @pytest.mark.asyncio
    async def test_count_by_property(
        self, db_session, test_property, _seed_property_activities
    ):
        """count_by_property returns correct count."""
        await _seed_property_activities(4)
        count = await property_activity.count_by_property(
            db_session, property_id=test_property.id
        )
        assert count == 4

    @pytest.mark.asyncio
    async def test_count_by_property_with_type(
        self, db_session, test_property, _seed_property_activities
    ):
        """count_by_property filters by activity_type."""
        await _seed_property_activities(3, ActivityType.VIEW)
        await _seed_property_activities(2, ActivityType.COMMENT)

        view_count = await property_activity.count_by_property(
            db_session, property_id=test_property.id, activity_type="view"
        )
        assert view_count == 3

        comment_count = await property_activity.count_by_property(
            db_session, property_id=test_property.id, activity_type="comment"
        )
        assert comment_count == 2

    @pytest.mark.asyncio
    async def test_count_by_property_zero(self, db_session):
        """count_by_property returns 0 for unknown property."""
        count = await property_activity.count_by_property(
            db_session, property_id=99999
        )
        assert count == 0

    @pytest.mark.asyncio
    async def test_log_view(self, db_session, test_property, test_user):
        """log_view creates a VIEW activity with correct fields."""
        act = await property_activity.log_view(
            db_session,
            property_id=test_property.id,
            user_id=test_user.id,
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0",
        )

        assert act.id is not None
        assert act.property_id == test_property.id
        assert act.user_id == test_user.id
        assert act.activity_type == ActivityType.VIEW
        assert act.description == "Viewed property details"
        assert act.ip_address == "192.168.1.1"
        assert act.user_agent == "TestAgent/1.0"

    @pytest.mark.asyncio
    async def test_log_view_optional_metadata(self, db_session, test_property, test_user):
        """log_view works without optional ip_address and user_agent."""
        act = await property_activity.log_view(
            db_session,
            property_id=test_property.id,
            user_id=test_user.id,
        )
        assert act.ip_address is None
        assert act.user_agent is None

    @pytest.mark.asyncio
    async def test_log_edit(self, db_session, test_property, test_user):
        """log_edit creates an EDIT activity with field change metadata."""
        act = await property_activity.log_edit(
            db_session,
            property_id=test_property.id,
            user_id=test_user.id,
            field_changed="occupancy_rate",
            old_value="95.0",
            new_value="97.5",
        )

        assert act.id is not None
        assert act.activity_type == ActivityType.EDIT
        assert act.field_changed == "occupancy_rate"
        assert act.old_value == "95.0"
        assert act.new_value == "97.5"
        assert "occupancy_rate" in act.description

    @pytest.mark.asyncio
    async def test_log_edit_null_values(self, db_session, test_property, test_user):
        """log_edit handles None old_value and new_value."""
        act = await property_activity.log_edit(
            db_session,
            property_id=test_property.id,
            user_id=test_user.id,
            field_changed="notes",
            old_value=None,
            new_value="New note text",
        )

        assert act.old_value is None
        assert act.new_value == "New note text"


# =============================================================================
# CRUDDealActivity Tests
# =============================================================================


class TestCRUDDealActivity:
    """Tests for CRUDDealActivity."""

    @pytest.mark.asyncio
    async def test_get_by_deal_returns_activities(
        self, db_session, test_deal, _seed_deal_activities
    ):
        """get_by_deal returns activities for the given deal."""
        await _seed_deal_activities(3)
        results = await deal_activity.get_by_deal(
            db_session, deal_id=test_deal.id
        )
        assert len(results) == 3
        for act in results:
            assert act.deal_id == test_deal.id

    @pytest.mark.asyncio
    async def test_get_by_deal_empty(self, db_session):
        """get_by_deal returns empty list for unknown deal."""
        results = await deal_activity.get_by_deal(db_session, deal_id=99999)
        assert results == []

    @pytest.mark.asyncio
    async def test_get_by_deal_type_filter(
        self, db_session, test_deal, _seed_deal_activities
    ):
        """get_by_deal filters by activity_type."""
        await _seed_deal_activities(2, ActivityType.VIEW)
        await _seed_deal_activities(1, ActivityType.EDIT)

        views = await deal_activity.get_by_deal(
            db_session, deal_id=test_deal.id, activity_type="view"
        )
        assert len(views) == 2

    @pytest.mark.asyncio
    async def test_get_by_deal_invalid_type_ignored(
        self, db_session, test_deal, _seed_deal_activities
    ):
        """Invalid activity_type string is silently ignored."""
        await _seed_deal_activities(3)
        results = await deal_activity.get_by_deal(
            db_session, deal_id=test_deal.id, activity_type="fake_type"
        )
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_get_by_deal_pagination(
        self, db_session, test_deal, _seed_deal_activities
    ):
        """get_by_deal supports skip and limit."""
        await _seed_deal_activities(5)

        page1 = await deal_activity.get_by_deal(
            db_session, deal_id=test_deal.id, skip=0, limit=2
        )
        assert len(page1) == 2

        all_results = await deal_activity.get_by_deal(
            db_session, deal_id=test_deal.id, skip=0, limit=50
        )
        assert len(all_results) == 5

    @pytest.mark.asyncio
    async def test_count_by_deal(self, db_session, test_deal, _seed_deal_activities):
        """count_by_deal returns correct count."""
        await _seed_deal_activities(4)
        count = await deal_activity.count_by_deal(
            db_session, deal_id=test_deal.id
        )
        assert count == 4

    @pytest.mark.asyncio
    async def test_count_by_deal_with_type(
        self, db_session, test_deal, _seed_deal_activities
    ):
        """count_by_deal filters by activity_type."""
        await _seed_deal_activities(3, ActivityType.EDIT)
        await _seed_deal_activities(1, ActivityType.STATUS_CHANGE)

        edit_count = await deal_activity.count_by_deal(
            db_session, deal_id=test_deal.id, activity_type="edit"
        )
        assert edit_count == 3

    @pytest.mark.asyncio
    async def test_count_by_deal_zero(self, db_session):
        """count_by_deal returns 0 for unknown deal."""
        count = await deal_activity.count_by_deal(db_session, deal_id=99999)
        assert count == 0


# =============================================================================
# CRUDWatchlist Tests
# =============================================================================


class TestCRUDWatchlist:
    """Tests for CRUDWatchlist."""

    @pytest.mark.asyncio
    async def test_add_to_watchlist(self, db_session, test_user, test_deal):
        """add_to_watchlist creates a new entry."""
        entry = await watchlist.add_to_watchlist(
            db_session, user_id=test_user.id, deal_id=test_deal.id
        )
        assert entry.id is not None
        assert entry.user_id == test_user.id
        assert entry.deal_id == test_deal.id
        assert entry.notes is None

    @pytest.mark.asyncio
    async def test_add_to_watchlist_with_notes(self, db_session, test_user, test_deal):
        """add_to_watchlist stores optional notes."""
        entry = await watchlist.add_to_watchlist(
            db_session,
            user_id=test_user.id,
            deal_id=test_deal.id,
            notes="Monitoring closely",
        )
        assert entry.notes == "Monitoring closely"

    @pytest.mark.asyncio
    async def test_add_to_watchlist_idempotent(self, db_session, test_user, test_deal):
        """Adding the same deal twice returns the existing entry (no duplicate)."""
        entry1 = await watchlist.add_to_watchlist(
            db_session, user_id=test_user.id, deal_id=test_deal.id
        )
        entry2 = await watchlist.add_to_watchlist(
            db_session, user_id=test_user.id, deal_id=test_deal.id
        )
        assert entry1.id == entry2.id

    @pytest.mark.asyncio
    async def test_get_by_user(self, db_session, test_user, multiple_deals):
        """get_by_user returns all watched deals."""
        for deal in multiple_deals[:3]:
            await watchlist.add_to_watchlist(
                db_session, user_id=test_user.id, deal_id=deal.id
            )

        results = await watchlist.get_by_user(
            db_session, user_id=test_user.id
        )
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_get_by_user_empty(self, db_session, test_user):
        """get_by_user returns empty list when no deals are watched."""
        results = await watchlist.get_by_user(
            db_session, user_id=test_user.id
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_get_by_user_pagination(
        self, db_session, test_user, multiple_deals
    ):
        """get_by_user supports skip and limit."""
        for deal in multiple_deals:
            await watchlist.add_to_watchlist(
                db_session, user_id=test_user.id, deal_id=deal.id
            )

        page = await watchlist.get_by_user(
            db_session, user_id=test_user.id, skip=0, limit=2
        )
        assert len(page) == 2

    @pytest.mark.asyncio
    async def test_get_by_user_and_deal_found(self, db_session, test_user, test_deal):
        """get_by_user_and_deal returns the entry when it exists."""
        await watchlist.add_to_watchlist(
            db_session, user_id=test_user.id, deal_id=test_deal.id
        )
        result = await watchlist.get_by_user_and_deal(
            db_session, user_id=test_user.id, deal_id=test_deal.id
        )
        assert result is not None
        assert result.deal_id == test_deal.id

    @pytest.mark.asyncio
    async def test_get_by_user_and_deal_not_found(self, db_session, test_user):
        """get_by_user_and_deal returns None when not on watchlist."""
        result = await watchlist.get_by_user_and_deal(
            db_session, user_id=test_user.id, deal_id=99999
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_is_watching_true(self, db_session, test_user, test_deal):
        """is_watching returns True when deal is on watchlist."""
        await watchlist.add_to_watchlist(
            db_session, user_id=test_user.id, deal_id=test_deal.id
        )
        result = await watchlist.is_watching(
            db_session, user_id=test_user.id, deal_id=test_deal.id
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_is_watching_false(self, db_session, test_user, test_deal):
        """is_watching returns False when deal is not on watchlist."""
        result = await watchlist.is_watching(
            db_session, user_id=test_user.id, deal_id=test_deal.id
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_from_watchlist_success(
        self, db_session, test_user, test_deal
    ):
        """remove_from_watchlist returns True and removes the entry."""
        await watchlist.add_to_watchlist(
            db_session, user_id=test_user.id, deal_id=test_deal.id
        )
        removed = await watchlist.remove_from_watchlist(
            db_session, user_id=test_user.id, deal_id=test_deal.id
        )
        assert removed is True

        # Confirm it is gone
        still_watching = await watchlist.is_watching(
            db_session, user_id=test_user.id, deal_id=test_deal.id
        )
        assert still_watching is False

    @pytest.mark.asyncio
    async def test_remove_from_watchlist_not_found(self, db_session, test_user):
        """remove_from_watchlist returns False when entry does not exist."""
        removed = await watchlist.remove_from_watchlist(
            db_session, user_id=test_user.id, deal_id=99999
        )
        assert removed is False

    @pytest.mark.asyncio
    async def test_toggle_watchlist_add(self, db_session, test_user, test_deal):
        """toggle_watchlist adds to watchlist when not present."""
        is_watched, entry = await watchlist.toggle_watchlist(
            db_session, user_id=test_user.id, deal_id=test_deal.id
        )
        assert is_watched is True
        assert entry is not None
        assert entry.deal_id == test_deal.id

    @pytest.mark.asyncio
    async def test_toggle_watchlist_remove(self, db_session, test_user, test_deal):
        """toggle_watchlist removes from watchlist when already present."""
        await watchlist.add_to_watchlist(
            db_session, user_id=test_user.id, deal_id=test_deal.id
        )
        is_watched, entry = await watchlist.toggle_watchlist(
            db_session, user_id=test_user.id, deal_id=test_deal.id
        )
        assert is_watched is False
        assert entry is None

    @pytest.mark.asyncio
    async def test_toggle_watchlist_round_trip(self, db_session, test_user, test_deal):
        """toggle twice returns to original state."""
        # Toggle on
        is_watched_1, _ = await watchlist.toggle_watchlist(
            db_session, user_id=test_user.id, deal_id=test_deal.id
        )
        assert is_watched_1 is True

        # Toggle off
        is_watched_2, _ = await watchlist.toggle_watchlist(
            db_session, user_id=test_user.id, deal_id=test_deal.id
        )
        assert is_watched_2 is False

        # Confirm gone
        assert await watchlist.is_watching(
            db_session, user_id=test_user.id, deal_id=test_deal.id
        ) is False

    @pytest.mark.asyncio
    async def test_toggle_watchlist_with_notes(self, db_session, test_user, test_deal):
        """toggle_watchlist passes notes when adding."""
        is_watched, entry = await watchlist.toggle_watchlist(
            db_session,
            user_id=test_user.id,
            deal_id=test_deal.id,
            notes="Flagged for review",
        )
        assert is_watched is True
        assert entry.notes == "Flagged for review"

    @pytest.mark.asyncio
    async def test_count_by_user(self, db_session, test_user, multiple_deals):
        """count_by_user returns the correct count."""
        for deal in multiple_deals[:3]:
            await watchlist.add_to_watchlist(
                db_session, user_id=test_user.id, deal_id=deal.id
            )

        count = await watchlist.count_by_user(
            db_session, user_id=test_user.id
        )
        assert count == 3

    @pytest.mark.asyncio
    async def test_count_by_user_zero(self, db_session, test_user):
        """count_by_user returns 0 when no deals are watched."""
        count = await watchlist.count_by_user(
            db_session, user_id=test_user.id
        )
        assert count == 0

    @pytest.mark.asyncio
    async def test_watchlist_user_isolation(
        self, db_session, test_user, admin_user, test_deal
    ):
        """Watchlist entries are isolated per user."""
        await watchlist.add_to_watchlist(
            db_session, user_id=test_user.id, deal_id=test_deal.id
        )

        # Admin user should not see it
        assert await watchlist.is_watching(
            db_session, user_id=admin_user.id, deal_id=test_deal.id
        ) is False

        admin_count = await watchlist.count_by_user(
            db_session, user_id=admin_user.id
        )
        assert admin_count == 0
