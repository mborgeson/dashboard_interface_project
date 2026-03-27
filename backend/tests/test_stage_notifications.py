"""
Tests for stage change notifications and deletion policy.

Epic 3.4: Stage Change Notifications [UR-018, UR-019]

Covers:
- Individual WebSocket notification emission on stage change
- Batch notification when more than STAGE_SYNC_BATCH_THRESHOLD deals change
- Deletion policy: all files removed → DEAD
- CLOSED deals protected from deletion policy
- "ignore" deletion policy skips marking deals dead
- Notification fire-and-forget (never blocks sync on failure)
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deal import Deal, DealStage
from app.models.stage_change_log import StageChangeLog, StageChangeSource
from app.services.extraction.file_monitor import SharePointFileMonitor

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_deal(
    name: str,
    stage: DealStage = DealStage.ACTIVE_REVIEW,
    **kwargs: Any,
) -> Deal:
    """Create a Deal instance with sensible defaults."""
    return Deal(
        name=name,
        deal_type="acquisition",
        stage=stage,
        stage_order=0,
        asking_price=Decimal("10000000"),
        hold_period_years=5,
        initial_contact_date=date.today(),
        source="Test",
        priority="medium",
        competition_level="low",
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def deal_active(db_session: AsyncSession) -> Deal:
    """An ACTIVE_REVIEW deal called 'The Clubhouse'."""
    deal = _make_deal("The Clubhouse", DealStage.ACTIVE_REVIEW)
    db_session.add(deal)
    await db_session.commit()
    await db_session.refresh(deal)
    return deal


@pytest_asyncio.fixture
async def deal_closed(db_session: AsyncSession) -> Deal:
    """A CLOSED deal called 'Villas at Scottsdale'."""
    deal = _make_deal("Villas at Scottsdale", DealStage.CLOSED)
    db_session.add(deal)
    await db_session.commit()
    await db_session.refresh(deal)
    return deal


@pytest_asyncio.fixture
async def deal_dead(db_session: AsyncSession) -> Deal:
    """A DEAD deal called 'Dead Creek Apartments'."""
    deal = _make_deal("Dead Creek Apartments", DealStage.DEAD)
    db_session.add(deal)
    await db_session.commit()
    await db_session.refresh(deal)
    return deal


@pytest_asyncio.fixture
async def many_deals(db_session: AsyncSession) -> list[Deal]:
    """Create 7 deals in INITIAL_REVIEW stage for batch tests."""
    deals = []
    for i in range(7):
        d = _make_deal(f"Batch Deal {i}", DealStage.INITIAL_REVIEW)
        db_session.add(d)
        deals.append(d)
    await db_session.commit()
    for d in deals:
        await db_session.refresh(d)
    return deals


@pytest_asyncio.fixture
def monitor(db_session: AsyncSession) -> SharePointFileMonitor:
    """SharePointFileMonitor bound to the test session."""
    mock_client = MagicMock()
    return SharePointFileMonitor(db=db_session, sharepoint_client=mock_client)


# ===========================================================================
# Task 1: Individual notifications on stage change
# ===========================================================================


class TestIndividualStageNotification:
    """Emit notify_deal_update() for each stage change when <= threshold."""

    @pytest.mark.asyncio
    async def test_single_stage_change_emits_notification(
        self,
        db_session: AsyncSession,
        monitor: SharePointFileMonitor,
        deal_active: Deal,
    ) -> None:
        """A single stage change should fire one notify_deal_update call."""
        mock_manager = AsyncMock()
        with patch(
            "app.services.websocket_manager.get_connection_manager",
            return_value=mock_manager,
        ):
            await monitor._sync_deal_stages([
                ("The Clubhouse", "under_contract"),
            ])

        mock_manager.notify_deal_update.assert_called_once()
        call_kwargs = mock_manager.notify_deal_update.call_args
        assert call_kwargs.kwargs["deal_id"] == deal_active.id
        assert call_kwargs.kwargs["action"] == "stage_changed"
        assert call_kwargs.kwargs["data"]["old_stage"] == "active_review"
        assert call_kwargs.kwargs["data"]["new_stage"] == "under_contract"
        assert call_kwargs.kwargs["data"]["source"] == "sharepoint_sync"

    @pytest.mark.asyncio
    async def test_multiple_below_threshold_emits_individual(
        self,
        db_session: AsyncSession,
        monitor: SharePointFileMonitor,
    ) -> None:
        """3 stage changes (below default threshold of 5) emit 3 individual notifications."""
        deals = []
        for i in range(3):
            d = _make_deal(f"Small Batch {i}", DealStage.INITIAL_REVIEW)
            db_session.add(d)
            deals.append(d)
        await db_session.commit()

        mock_manager = AsyncMock()
        with patch(
            "app.services.websocket_manager.get_connection_manager",
            return_value=mock_manager,
        ):
            count = await monitor._sync_deal_stages([
                (f"Small Batch {i}", "active_review") for i in range(3)
            ])

        assert count == 3
        assert mock_manager.notify_deal_update.call_count == 3
        # No batch notification should have been sent
        mock_manager.send_to_channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_notification_includes_deal_name(
        self,
        db_session: AsyncSession,
        monitor: SharePointFileMonitor,
        deal_active: Deal,
    ) -> None:
        """Notification data includes the deal_name field."""
        mock_manager = AsyncMock()
        with patch(
            "app.services.websocket_manager.get_connection_manager",
            return_value=mock_manager,
        ):
            await monitor._sync_deal_stages([
                ("The Clubhouse", "dead"),
            ])

        data = mock_manager.notify_deal_update.call_args.kwargs["data"]
        assert data["deal_name"] == "The Clubhouse"

    @pytest.mark.asyncio
    async def test_no_notification_when_no_stage_change(
        self,
        db_session: AsyncSession,
        monitor: SharePointFileMonitor,
        deal_active: Deal,
    ) -> None:
        """If the deal is already at the target stage, no notification fires."""
        mock_manager = AsyncMock()
        with patch(
            "app.services.websocket_manager.get_connection_manager",
            return_value=mock_manager,
        ):
            count = await monitor._sync_deal_stages([
                ("The Clubhouse", "active_review"),  # Already ACTIVE_REVIEW
            ])

        assert count == 0
        mock_manager.notify_deal_update.assert_not_called()
        mock_manager.send_to_channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_notification_skipped_for_invalid_stage(
        self,
        db_session: AsyncSession,
        monitor: SharePointFileMonitor,
        deal_active: Deal,
    ) -> None:
        """Invalid stage strings are skipped gracefully."""
        mock_manager = AsyncMock()
        with patch(
            "app.services.websocket_manager.get_connection_manager",
            return_value=mock_manager,
        ):
            count = await monitor._sync_deal_stages([
                ("The Clubhouse", "nonexistent_stage"),
            ])

        assert count == 0
        mock_manager.notify_deal_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_notification_failure_does_not_block_sync(
        self,
        db_session: AsyncSession,
        monitor: SharePointFileMonitor,
        deal_active: Deal,
    ) -> None:
        """If WebSocket notification fails, the sync still succeeds."""
        mock_manager = AsyncMock()
        mock_manager.notify_deal_update.side_effect = RuntimeError("WS down")
        with patch(
            "app.services.websocket_manager.get_connection_manager",
            return_value=mock_manager,
        ):
            count = await monitor._sync_deal_stages([
                ("The Clubhouse", "under_contract"),
            ])

        # Stage change still happened
        assert count == 1
        assert deal_active.stage == DealStage.UNDER_CONTRACT


# ===========================================================================
# Task 2: Batch notification for bulk moves (>5 deals)
# ===========================================================================


class TestBatchStageNotification:
    """Emit batch event when more than STAGE_SYNC_BATCH_THRESHOLD deals change."""

    @pytest.mark.asyncio
    async def test_batch_notification_above_threshold(
        self,
        db_session: AsyncSession,
        monitor: SharePointFileMonitor,
        many_deals: list[Deal],
    ) -> None:
        """7 stage changes (above default threshold of 5) emit a single batch event."""
        mock_manager = AsyncMock()
        with patch(
            "app.services.websocket_manager.get_connection_manager",
            return_value=mock_manager,
        ):
            count = await monitor._sync_deal_stages([
                (f"Batch Deal {i}", "active_review") for i in range(7)
            ])

        assert count == 7
        # Individual notifications should NOT have been sent
        mock_manager.notify_deal_update.assert_not_called()
        # Batch notification should have been sent
        mock_manager.send_to_channel.assert_called_once()
        call_args = mock_manager.send_to_channel.call_args
        assert call_args.args[0] == "deals"  # channel
        payload = call_args.args[1]
        assert payload["type"] == "batch_stage_changed"
        assert payload["count"] == 7
        assert payload["source"] == "sharepoint_sync"
        assert len(payload["deals"]) == 7

    @pytest.mark.asyncio
    async def test_batch_payload_contains_deal_summaries(
        self,
        db_session: AsyncSession,
        monitor: SharePointFileMonitor,
        many_deals: list[Deal],
    ) -> None:
        """Batch payload includes deal_id, deal_name, old_stage, new_stage for each deal."""
        mock_manager = AsyncMock()
        with patch(
            "app.services.websocket_manager.get_connection_manager",
            return_value=mock_manager,
        ):
            await monitor._sync_deal_stages([
                (f"Batch Deal {i}", "dead") for i in range(7)
            ])

        payload = mock_manager.send_to_channel.call_args.args[1]
        for deal_summary in payload["deals"]:
            assert "deal_id" in deal_summary
            assert "deal_name" in deal_summary
            assert deal_summary["old_stage"] == "initial_review"
            assert deal_summary["new_stage"] == "dead"

    @pytest.mark.asyncio
    async def test_exactly_at_threshold_sends_individual(
        self,
        db_session: AsyncSession,
        monitor: SharePointFileMonitor,
    ) -> None:
        """Exactly 5 changes (= threshold) sends individual, not batch."""
        deals = []
        for i in range(5):
            d = _make_deal(f"Threshold Deal {i}", DealStage.INITIAL_REVIEW)
            db_session.add(d)
            deals.append(d)
        await db_session.commit()

        mock_manager = AsyncMock()
        with patch(
            "app.services.websocket_manager.get_connection_manager",
            return_value=mock_manager,
        ):
            count = await monitor._sync_deal_stages([
                (f"Threshold Deal {i}", "active_review") for i in range(5)
            ])

        assert count == 5
        assert mock_manager.notify_deal_update.call_count == 5
        mock_manager.send_to_channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_threshold_configurable(
        self,
        db_session: AsyncSession,
        monitor: SharePointFileMonitor,
    ) -> None:
        """Custom STAGE_SYNC_BATCH_THRESHOLD is respected."""
        deals = []
        for i in range(3):
            d = _make_deal(f"CustomThresh Deal {i}", DealStage.INITIAL_REVIEW)
            db_session.add(d)
            deals.append(d)
        await db_session.commit()

        mock_manager = AsyncMock()
        with patch(
            "app.services.websocket_manager.get_connection_manager",
            return_value=mock_manager,
        ), patch(
            "app.services.extraction.file_monitor.settings"
        ) as mock_settings:
            mock_settings.STAGE_SYNC_BATCH_THRESHOLD = 2  # Lower threshold
            await monitor._sync_deal_stages([
                (f"CustomThresh Deal {i}", "dead") for i in range(3)
            ])

        # 3 > 2, so batch notification should fire
        mock_manager.send_to_channel.assert_called_once()
        mock_manager.notify_deal_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_notification_includes_timestamp(
        self,
        db_session: AsyncSession,
        monitor: SharePointFileMonitor,
        many_deals: list[Deal],
    ) -> None:
        """Batch payload includes a timestamp."""
        mock_manager = AsyncMock()
        with patch(
            "app.services.websocket_manager.get_connection_manager",
            return_value=mock_manager,
        ):
            await monitor._sync_deal_stages([
                (f"Batch Deal {i}", "active_review") for i in range(7)
            ])

        payload = mock_manager.send_to_channel.call_args.args[1]
        assert "timestamp" in payload


# ===========================================================================
# Task 3: Deletion policy — mark DEAD when all files removed
# ===========================================================================


class TestDeletionPolicy:
    """When all files for a deal are removed, mark it DEAD."""

    @pytest.mark.asyncio
    async def test_all_files_removed_marks_dead(
        self,
        db_session: AsyncSession,
        monitor: SharePointFileMonitor,
        deal_active: Deal,
    ) -> None:
        """Deal is marked DEAD when all its files disappear from SharePoint."""
        # Simulate: deal_active ("The Clubhouse") had files, now none remain
        deleted_deal_names = {"The Clubhouse"}
        current_paths: set[str] = set()  # No files remain

        class FakeFile:
            deal_name = "Other Deal"

        with patch(
            "app.services.extraction.file_monitor.settings"
        ) as mock_settings:
            mock_settings.STAGE_SYNC_DELETE_POLICY = "mark_dead"
            mock_settings.STAGE_SYNC_PROTECT_CLOSED = True
            await monitor._apply_deletion_policy(
                deleted_deal_names, current_paths, []
            )

        assert deal_active.stage == DealStage.DEAD

    @pytest.mark.asyncio
    async def test_partial_file_removal_no_mark_dead(
        self,
        db_session: AsyncSession,
        monitor: SharePointFileMonitor,
        deal_active: Deal,
    ) -> None:
        """Deal is NOT marked dead if it still has some files remaining."""
        deleted_deal_names = {"The Clubhouse"}
        current_paths: set[str] = set()

        # One file still exists for this deal
        class FakeFile:
            deal_name = "The Clubhouse"

        with patch(
            "app.services.extraction.file_monitor.settings"
        ) as mock_settings:
            mock_settings.STAGE_SYNC_DELETE_POLICY = "mark_dead"
            mock_settings.STAGE_SYNC_PROTECT_CLOSED = True
            await monitor._apply_deletion_policy(
                deleted_deal_names, current_paths, [FakeFile()]  # type: ignore[arg-type]
            )

        # Should remain ACTIVE_REVIEW
        assert deal_active.stage == DealStage.ACTIVE_REVIEW

    @pytest.mark.asyncio
    async def test_closed_deal_protected(
        self,
        db_session: AsyncSession,
        monitor: SharePointFileMonitor,
        deal_closed: Deal,
    ) -> None:
        """CLOSED deals are NOT changed to DEAD when STAGE_SYNC_PROTECT_CLOSED is True."""
        deleted_deal_names = {"Villas at Scottsdale"}

        with patch(
            "app.services.extraction.file_monitor.settings"
        ) as mock_settings:
            mock_settings.STAGE_SYNC_DELETE_POLICY = "mark_dead"
            mock_settings.STAGE_SYNC_PROTECT_CLOSED = True
            await monitor._apply_deletion_policy(
                deleted_deal_names, set(), []
            )

        assert deal_closed.stage == DealStage.CLOSED

    @pytest.mark.asyncio
    async def test_closed_deal_not_protected_when_setting_disabled(
        self,
        db_session: AsyncSession,
        monitor: SharePointFileMonitor,
        deal_closed: Deal,
    ) -> None:
        """CLOSED deals ARE changed to DEAD when STAGE_SYNC_PROTECT_CLOSED is False."""
        deleted_deal_names = {"Villas at Scottsdale"}

        with patch(
            "app.services.extraction.file_monitor.settings"
        ) as mock_settings:
            mock_settings.STAGE_SYNC_DELETE_POLICY = "mark_dead"
            mock_settings.STAGE_SYNC_PROTECT_CLOSED = False
            await monitor._apply_deletion_policy(
                deleted_deal_names, set(), []
            )

        assert deal_closed.stage == DealStage.DEAD

    @pytest.mark.asyncio
    async def test_ignore_policy_skips_marking_dead(
        self,
        db_session: AsyncSession,
        monitor: SharePointFileMonitor,
        deal_active: Deal,
    ) -> None:
        """'ignore' deletion policy does not change deal stage."""
        deleted_deal_names = {"The Clubhouse"}

        with patch(
            "app.services.extraction.file_monitor.settings"
        ) as mock_settings:
            mock_settings.STAGE_SYNC_DELETE_POLICY = "ignore"
            await monitor._apply_deletion_policy(
                deleted_deal_names, set(), []
            )

        assert deal_active.stage == DealStage.ACTIVE_REVIEW

    @pytest.mark.asyncio
    async def test_already_dead_deal_not_changed(
        self,
        db_session: AsyncSession,
        monitor: SharePointFileMonitor,
        deal_dead: Deal,
    ) -> None:
        """Deals already in DEAD stage are not changed again."""
        deleted_deal_names = {"Dead Creek Apartments"}

        with patch(
            "app.services.extraction.file_monitor.settings"
        ) as mock_settings:
            mock_settings.STAGE_SYNC_DELETE_POLICY = "mark_dead"
            mock_settings.STAGE_SYNC_PROTECT_CLOSED = True
            await monitor._apply_deletion_policy(
                deleted_deal_names, set(), []
            )

        # Still DEAD, and no StageChangeLog should be created
        assert deal_dead.stage == DealStage.DEAD
        result = await db_session.execute(
            select(StageChangeLog).where(StageChangeLog.deal_id == deal_dead.id)
        )
        logs = list(result.scalars().all())
        assert len(logs) == 0

    @pytest.mark.asyncio
    async def test_deletion_policy_creates_audit_log(
        self,
        db_session: AsyncSession,
        monitor: SharePointFileMonitor,
        deal_active: Deal,
    ) -> None:
        """Marking a deal DEAD via deletion policy creates a StageChangeLog."""
        deleted_deal_names = {"The Clubhouse"}

        with patch(
            "app.services.extraction.file_monitor.settings"
        ) as mock_settings:
            mock_settings.STAGE_SYNC_DELETE_POLICY = "mark_dead"
            mock_settings.STAGE_SYNC_PROTECT_CLOSED = True
            await monitor._apply_deletion_policy(
                deleted_deal_names, set(), []
            )

        result = await db_session.execute(
            select(StageChangeLog).where(
                StageChangeLog.deal_id == deal_active.id
            )
        )
        logs = list(result.scalars().all())
        assert len(logs) == 1
        assert logs[0].old_stage == "active_review"
        assert logs[0].new_stage == "dead"
        assert logs[0].source == StageChangeSource.SHAREPOINT_SYNC
        assert "All files removed" in (logs[0].reason or "")

    @pytest.mark.asyncio
    async def test_deletion_policy_multiple_deals(
        self,
        db_session: AsyncSession,
        monitor: SharePointFileMonitor,
    ) -> None:
        """Multiple deals with all files removed are all marked DEAD."""
        d1 = _make_deal("Property A", DealStage.INITIAL_REVIEW)
        d2 = _make_deal("Property B", DealStage.ACTIVE_REVIEW)
        db_session.add_all([d1, d2])
        await db_session.commit()
        await db_session.refresh(d1)
        await db_session.refresh(d2)

        with patch(
            "app.services.extraction.file_monitor.settings"
        ) as mock_settings:
            mock_settings.STAGE_SYNC_DELETE_POLICY = "mark_dead"
            mock_settings.STAGE_SYNC_PROTECT_CLOSED = True
            await monitor._apply_deletion_policy(
                {"Property A", "Property B"}, set(), []
            )

        assert d1.stage == DealStage.DEAD
        assert d2.stage == DealStage.DEAD


# ===========================================================================
# Task 5: Config settings
# ===========================================================================


class TestConfigSettings:
    """Verify the stage sync config fields exist with correct defaults."""

    def test_stage_sync_delete_policy_default(self) -> None:
        from app.core.config import Settings

        s = Settings()
        assert s.STAGE_SYNC_DELETE_POLICY == "mark_dead"

    def test_stage_sync_protect_closed_default(self) -> None:
        from app.core.config import Settings

        s = Settings()
        assert s.STAGE_SYNC_PROTECT_CLOSED is True

    def test_stage_sync_batch_threshold_default(self) -> None:
        from app.core.config import Settings

        s = Settings()
        assert s.STAGE_SYNC_BATCH_THRESHOLD == 5


# ===========================================================================
# Integration: _sync_deal_stages creates audit logs + notifications
# ===========================================================================


class TestSyncDealStagesIntegration:
    """End-to-end tests combining stage change, audit log, and notification."""

    @pytest.mark.asyncio
    async def test_sync_creates_audit_and_notification(
        self,
        db_session: AsyncSession,
        monitor: SharePointFileMonitor,
        deal_active: Deal,
    ) -> None:
        """_sync_deal_stages creates StageChangeLog AND fires notification."""
        mock_manager = AsyncMock()
        with patch(
            "app.services.websocket_manager.get_connection_manager",
            return_value=mock_manager,
        ):
            count = await monitor._sync_deal_stages([
                ("The Clubhouse", "under_contract"),
            ])

        assert count == 1

        # Audit log created
        result = await db_session.execute(
            select(StageChangeLog).where(
                StageChangeLog.deal_id == deal_active.id
            )
        )
        logs = list(result.scalars().all())
        assert len(logs) == 1
        assert logs[0].new_stage == "under_contract"

        # Notification fired
        mock_manager.notify_deal_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_with_unmatched_deal_name(
        self,
        db_session: AsyncSession,
        monitor: SharePointFileMonitor,
    ) -> None:
        """Stage change for a deal name not in DB is silently skipped."""
        mock_manager = AsyncMock()
        with patch(
            "app.services.websocket_manager.get_connection_manager",
            return_value=mock_manager,
        ):
            count = await monitor._sync_deal_stages([
                ("Nonexistent Property", "dead"),
            ])

        assert count == 0
        mock_manager.notify_deal_update.assert_not_called()
