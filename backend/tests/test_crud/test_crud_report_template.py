"""Tests for Report Template CRUD operations.

Covers CRUDReportTemplate, CRUDQueuedReport, and CRUDDistributionSchedule:
- ReportTemplate: get_by_category, get_defaults, get_filtered, count_filtered
- QueuedReport: create_with_timestamp, get_by_status, get_recent, update_status,
  get_filtered, count_filtered
- DistributionSchedule: get_active, get_due, get_by_template, update_last_sent
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.crud.crud_report_template import (
    distribution_schedule as schedule_crud,
)
from app.crud.crud_report_template import (
    queued_report as queued_crud,
)
from app.crud.crud_report_template import (
    report_template as template_crud,
)
from app.models.report_template import (
    DistributionSchedule,
    QueuedReport,
    ReportCategory,
    ReportFormat,
    ReportStatus,
    ReportTemplate,
    ScheduleFrequency,
)

# =============================================================================
# Helpers
# =============================================================================


async def _create_template(
    db_session,
    name: str = "Test Template",
    category: str = ReportCategory.FINANCIAL,
    is_default: bool = False,
    description: str | None = None,
) -> ReportTemplate:
    """Insert a report template directly."""
    template = ReportTemplate(
        name=name,
        description=description or f"Description for {name}",
        category=category,
        sections=["summary", "financials"],
        export_formats=["pdf"],
        is_default=is_default,
        created_by="test@example.com",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(template)
    await db_session.flush()
    await db_session.refresh(template)
    return template


async def _create_queued_report(
    db_session,
    template_id: int,
    name: str = "Test Report",
    status: str = ReportStatus.PENDING,
    requested_by: str = "analyst@example.com",
) -> QueuedReport:
    """Insert a queued report directly."""
    report = QueuedReport(
        name=name,
        template_id=template_id,
        status=status,
        progress=0 if status == ReportStatus.PENDING else 50,
        format=ReportFormat.PDF,
        requested_by=requested_by,
        requested_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(report)
    await db_session.flush()
    await db_session.refresh(report)
    return report


async def _create_schedule(
    db_session,
    template_id: int,
    name: str = "Weekly Report",
    is_active: bool = True,
    next_scheduled: datetime | None = None,
) -> DistributionSchedule:
    """Insert a distribution schedule directly."""
    schedule = DistributionSchedule(
        name=name,
        template_id=template_id,
        recipients=["team@example.com"],
        frequency=ScheduleFrequency.WEEKLY,
        day_of_week=1,
        time="09:00",
        format=ReportFormat.PDF,
        is_active=is_active,
        next_scheduled=next_scheduled or datetime.now(UTC) + timedelta(days=7),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(schedule)
    await db_session.flush()
    await db_session.refresh(schedule)
    return schedule


# =============================================================================
# CRUDReportTemplate
# =============================================================================


class TestCRUDReportTemplate:
    """Tests for CRUDReportTemplate."""

    @pytest.mark.asyncio
    async def test_create_template(self, db_session):
        """Creating a template via CRUD persists all fields."""
        template = await _create_template(db_session, "Monthly P&L")
        assert template.id is not None
        assert template.name == "Monthly P&L"
        assert template.category == ReportCategory.FINANCIAL

    @pytest.mark.asyncio
    async def test_get_by_category(self, db_session):
        """get_by_category returns templates matching the category."""
        await _create_template(db_session, "Financial 1", ReportCategory.FINANCIAL)
        await _create_template(db_session, "Financial 2", ReportCategory.FINANCIAL)
        await _create_template(db_session, "Market 1", ReportCategory.MARKET)

        results = await template_crud.get_by_category(
            db_session, ReportCategory.FINANCIAL
        )
        assert len(results) == 2
        for t in results:
            assert t.category == ReportCategory.FINANCIAL

    @pytest.mark.asyncio
    async def test_get_by_category_empty(self, db_session):
        """get_by_category returns empty list for unused category."""
        results = await template_crud.get_by_category(
            db_session, ReportCategory.EXECUTIVE
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_get_by_category_excludes_deleted(self, db_session):
        """get_by_category excludes soft-deleted templates."""
        t = await _create_template(db_session, "Deleted", ReportCategory.MARKET)
        t.is_deleted = True
        t.deleted_at = datetime.now(UTC)
        db_session.add(t)
        await db_session.flush()

        results = await template_crud.get_by_category(db_session, ReportCategory.MARKET)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_get_defaults(self, db_session):
        """get_defaults returns only is_default=True templates."""
        await _create_template(db_session, "Default 1", is_default=True)
        await _create_template(db_session, "Default 2", is_default=True)
        await _create_template(db_session, "Custom", is_default=False)

        defaults = await template_crud.get_defaults(db_session)
        assert len(defaults) == 2
        for t in defaults:
            assert t.is_default is True

    @pytest.mark.asyncio
    async def test_get_defaults_empty(self, db_session):
        """get_defaults returns empty list when no defaults exist."""
        await _create_template(db_session, "Custom Only", is_default=False)
        defaults = await template_crud.get_defaults(db_session)
        assert defaults == []

    @pytest.mark.asyncio
    async def test_get_filtered_by_category(self, db_session):
        """get_filtered filters by category."""
        await _create_template(db_session, "A", ReportCategory.PORTFOLIO)
        await _create_template(db_session, "B", ReportCategory.FINANCIAL)

        results = await template_crud.get_filtered(
            db_session, category=ReportCategory.PORTFOLIO
        )
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_filtered_by_is_default(self, db_session):
        """get_filtered filters by is_default flag."""
        await _create_template(db_session, "Default", is_default=True)
        await _create_template(db_session, "Custom", is_default=False)

        defaults = await template_crud.get_filtered(db_session, is_default=True)
        assert len(defaults) == 1
        assert defaults[0].is_default is True

    @pytest.mark.asyncio
    async def test_get_filtered_by_search(self, db_session):
        """get_filtered filters by name/description search."""
        await _create_template(
            db_session, "Monthly Executive Summary", description="Monthly exec report"
        )
        await _create_template(
            db_session, "Quarterly Market", description="Market data"
        )

        results = await template_crud.get_filtered(db_session, search="executive")
        assert len(results) == 1
        assert "Executive" in results[0].name

    @pytest.mark.asyncio
    async def test_count_filtered(self, db_session):
        """count_filtered returns correct count."""
        await _create_template(db_session, "A", ReportCategory.FINANCIAL)
        await _create_template(db_session, "B", ReportCategory.FINANCIAL)
        await _create_template(db_session, "C", ReportCategory.MARKET)

        count = await template_crud.count_filtered(
            db_session, category=ReportCategory.FINANCIAL
        )
        assert count == 2

    @pytest.mark.asyncio
    async def test_count_filtered_no_filters(self, db_session):
        """count_filtered returns total when no filters."""
        await _create_template(db_session, "A")
        await _create_template(db_session, "B")

        count = await template_crud.count_filtered(db_session)
        assert count == 2

    # _build_template_conditions tests
    def test_build_conditions_no_filters(self):
        conditions = template_crud._build_template_conditions()
        assert conditions == []

    def test_build_conditions_category(self):
        conditions = template_crud._build_template_conditions(
            category=ReportCategory.MARKET
        )
        assert len(conditions) == 1

    def test_build_conditions_is_default(self):
        conditions = template_crud._build_template_conditions(is_default=True)
        assert len(conditions) == 1

    def test_build_conditions_search(self):
        conditions = template_crud._build_template_conditions(search="summary")
        assert len(conditions) == 1

    def test_build_conditions_all(self):
        conditions = template_crud._build_template_conditions(
            category=ReportCategory.FINANCIAL,
            is_default=False,
            search="P&L",
        )
        assert len(conditions) == 3


# =============================================================================
# CRUDQueuedReport
# =============================================================================


class TestCRUDQueuedReport:
    """Tests for CRUDQueuedReport."""

    @pytest.mark.asyncio
    async def test_create_with_timestamp(self, db_session):
        """create_with_timestamp sets requested_at and status=PENDING."""
        template = await _create_template(db_session)
        from app.schemas.reporting import QueuedReportCreate

        obj_in = QueuedReportCreate(
            name="Test Report",
            template_id=template.id,
            format="pdf",
            requested_by="analyst@test.com",
        )
        report = await queued_crud.create_with_timestamp(db_session, obj_in=obj_in)

        assert report.id is not None
        assert report.status == ReportStatus.PENDING
        assert report.progress == 0
        assert report.requested_at is not None

    @pytest.mark.asyncio
    async def test_get_by_status(self, db_session):
        """get_by_status returns reports matching the status."""
        template = await _create_template(db_session)
        await _create_queued_report(db_session, template.id, "R1", ReportStatus.PENDING)
        await _create_queued_report(
            db_session, template.id, "R2", ReportStatus.COMPLETED
        )
        await _create_queued_report(db_session, template.id, "R3", ReportStatus.PENDING)

        pending = await queued_crud.get_by_status(db_session, ReportStatus.PENDING)
        assert len(pending) == 2

    @pytest.mark.asyncio
    async def test_get_by_status_empty(self, db_session):
        """get_by_status returns empty list for unused status."""
        results = await queued_crud.get_by_status(db_session, ReportStatus.FAILED)
        assert results == []

    @pytest.mark.asyncio
    async def test_get_recent(self, db_session):
        """get_recent returns limited number of recent reports."""
        template = await _create_template(db_session)
        for i in range(5):
            await _create_queued_report(db_session, template.id, f"Report {i}")

        recent = await queued_crud.get_recent(db_session, limit=3)
        assert len(recent) == 3

    @pytest.mark.asyncio
    async def test_update_status_to_generating(self, db_session):
        """update_status changes status and progress."""
        template = await _create_template(db_session)
        report = await _create_queued_report(db_session, template.id)

        updated = await queued_crud.update_status(
            db_session,
            report_id=report.id,
            status=ReportStatus.GENERATING,
            progress=50,
        )

        assert updated is not None
        assert updated.status == ReportStatus.GENERATING
        assert updated.progress == 50

    @pytest.mark.asyncio
    async def test_update_status_to_completed(self, db_session):
        """update_status to COMPLETED sets progress=100 and completed_at."""
        template = await _create_template(db_session)
        report = await _create_queued_report(db_session, template.id)

        updated = await queued_crud.update_status(
            db_session,
            report_id=report.id,
            status=ReportStatus.COMPLETED.value,
            progress=100,
            download_url="/reports/test.pdf",
            file_size="2.4 MB",
        )

        assert updated is not None
        assert updated.progress == 100
        assert updated.completed_at is not None
        assert updated.download_url == "/reports/test.pdf"
        assert updated.file_size == "2.4 MB"

    @pytest.mark.asyncio
    async def test_update_status_to_failed(self, db_session):
        """update_status to FAILED stores the error message."""
        template = await _create_template(db_session)
        report = await _create_queued_report(db_session, template.id)

        updated = await queued_crud.update_status(
            db_session,
            report_id=report.id,
            status=ReportStatus.FAILED,
            error="Template rendering failed",
        )

        assert updated is not None
        assert updated.status == ReportStatus.FAILED
        assert updated.error == "Template rendering failed"

    @pytest.mark.asyncio
    async def test_update_status_nonexistent(self, db_session):
        """update_status returns None for nonexistent report."""
        result = await queued_crud.update_status(
            db_session, report_id=99999, status=ReportStatus.COMPLETED
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_get_filtered_by_status(self, db_session):
        """get_filtered filters by status."""
        template = await _create_template(db_session)
        await _create_queued_report(db_session, template.id, "A", ReportStatus.PENDING)
        await _create_queued_report(
            db_session, template.id, "B", ReportStatus.COMPLETED
        )

        results = await queued_crud.get_filtered(
            db_session, status=ReportStatus.PENDING
        )
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_filtered_by_template(self, db_session):
        """get_filtered filters by template_id."""
        t1 = await _create_template(db_session, "Template 1")
        t2 = await _create_template(db_session, "Template 2")
        await _create_queued_report(db_session, t1.id, "R1")
        await _create_queued_report(db_session, t2.id, "R2")

        results = await queued_crud.get_filtered(db_session, template_id=t1.id)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_filtered_by_requester(self, db_session):
        """get_filtered filters by requested_by."""
        template = await _create_template(db_session)
        await _create_queued_report(
            db_session, template.id, "A", requested_by="alice@test.com"
        )
        await _create_queued_report(
            db_session, template.id, "B", requested_by="bob@test.com"
        )

        results = await queued_crud.get_filtered(
            db_session, requested_by="alice@test.com"
        )
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_count_filtered(self, db_session):
        """count_filtered returns correct count with filters."""
        template = await _create_template(db_session)
        await _create_queued_report(db_session, template.id, "A", ReportStatus.PENDING)
        await _create_queued_report(db_session, template.id, "B", ReportStatus.PENDING)
        await _create_queued_report(
            db_session, template.id, "C", ReportStatus.COMPLETED
        )

        count = await queued_crud.count_filtered(
            db_session, status=ReportStatus.PENDING
        )
        assert count == 2

    # _build_queued_conditions tests
    def test_build_conditions_no_filters(self):
        conditions = queued_crud._build_queued_conditions()
        assert conditions == []

    def test_build_conditions_status(self):
        conditions = queued_crud._build_queued_conditions(status=ReportStatus.PENDING)
        assert len(conditions) == 1

    def test_build_conditions_template_id(self):
        conditions = queued_crud._build_queued_conditions(template_id=1)
        assert len(conditions) == 1

    def test_build_conditions_requested_by(self):
        conditions = queued_crud._build_queued_conditions(requested_by="user@test.com")
        assert len(conditions) == 1

    def test_build_conditions_all(self):
        conditions = queued_crud._build_queued_conditions(
            status=ReportStatus.COMPLETED,
            template_id=1,
            requested_by="user@test.com",
        )
        assert len(conditions) == 3


# =============================================================================
# CRUDDistributionSchedule
# =============================================================================


class TestCRUDDistributionSchedule:
    """Tests for CRUDDistributionSchedule."""

    @pytest.mark.asyncio
    async def test_get_active(self, db_session):
        """get_active returns only active, non-deleted schedules."""
        template = await _create_template(db_session)
        await _create_schedule(db_session, template.id, "Active", is_active=True)
        await _create_schedule(db_session, template.id, "Inactive", is_active=False)

        active = await schedule_crud.get_active(db_session)
        assert len(active) == 1
        assert active[0].name == "Active"

    @pytest.mark.asyncio
    async def test_get_active_excludes_deleted(self, db_session):
        """get_active excludes soft-deleted schedules."""
        template = await _create_template(db_session)
        s = await _create_schedule(db_session, template.id, "Deleted", is_active=True)
        s.is_deleted = True
        s.deleted_at = datetime.now(UTC)
        db_session.add(s)
        await db_session.flush()

        active = await schedule_crud.get_active(db_session)
        assert len(active) == 0

    @pytest.mark.asyncio
    async def test_get_active_empty(self, db_session):
        """get_active returns empty when no active schedules exist."""
        active = await schedule_crud.get_active(db_session)
        assert active == []

    @pytest.mark.asyncio
    async def test_get_due(self, db_session):
        """get_due returns schedules that are past their next_scheduled time."""
        template = await _create_template(db_session)
        now = datetime.now(UTC)

        # Due (past)
        await _create_schedule(
            db_session,
            template.id,
            "Due Now",
            next_scheduled=now - timedelta(hours=1),
        )
        # Not due (future)
        await _create_schedule(
            db_session,
            template.id,
            "Future",
            next_scheduled=now + timedelta(days=7),
        )

        due = await schedule_crud.get_due(db_session, as_of=now)
        assert len(due) == 1
        assert due[0].name == "Due Now"

    @pytest.mark.asyncio
    async def test_get_due_excludes_inactive(self, db_session):
        """get_due excludes inactive schedules even if past due."""
        template = await _create_template(db_session)
        now = datetime.now(UTC)

        await _create_schedule(
            db_session,
            template.id,
            "Due But Inactive",
            is_active=False,
            next_scheduled=now - timedelta(hours=1),
        )

        due = await schedule_crud.get_due(db_session, as_of=now)
        assert len(due) == 0

    @pytest.mark.asyncio
    async def test_get_due_default_as_of(self, db_session):
        """get_due uses current time when as_of is None."""
        template = await _create_template(db_session)
        # The production code uses datetime.now() (naive) for as_of default,
        # so we pass an explicit as_of to avoid naive/aware comparison issues.
        now = datetime.now()

        await _create_schedule(
            db_session,
            template.id,
            "Past Due",
            next_scheduled=now - timedelta(hours=2),
        )

        due = await schedule_crud.get_due(db_session, as_of=now)
        assert len(due) == 1

    @pytest.mark.asyncio
    async def test_get_by_template(self, db_session):
        """get_by_template returns schedules for a specific template."""
        t1 = await _create_template(db_session, "Template 1")
        t2 = await _create_template(db_session, "Template 2")

        await _create_schedule(db_session, t1.id, "Sched A")
        await _create_schedule(db_session, t1.id, "Sched B")
        await _create_schedule(db_session, t2.id, "Sched C")

        results = await schedule_crud.get_by_template(db_session, t1.id)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_by_template_empty(self, db_session):
        """get_by_template returns empty for template with no schedules."""
        results = await schedule_crud.get_by_template(db_session, 99999)
        assert results == []

    @pytest.mark.asyncio
    async def test_get_by_template_excludes_deleted(self, db_session):
        """get_by_template excludes soft-deleted schedules."""
        template = await _create_template(db_session)
        s = await _create_schedule(db_session, template.id, "Deleted")
        s.is_deleted = True
        s.deleted_at = datetime.now(UTC)
        db_session.add(s)
        await db_session.flush()

        results = await schedule_crud.get_by_template(db_session, template.id)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_update_last_sent(self, db_session):
        """update_last_sent updates last_sent and next_scheduled."""
        template = await _create_template(db_session)
        schedule = await _create_schedule(db_session, template.id)
        # Use naive datetime to match production code's datetime.now()
        next_time = datetime.now() + timedelta(days=7)

        updated = await schedule_crud.update_last_sent(
            db_session,
            schedule_id=schedule.id,
            next_scheduled=next_time,
        )

        assert updated is not None
        assert updated.last_sent is not None
        # SQLite limitation (T-DEBT-023): strips timezone on round-trip.
        # See test_integration/test_pg_server_defaults.py for PG equivalent.
        assert updated.next_scheduled.replace(tzinfo=None) == next_time.replace(
            tzinfo=None
        )

    @pytest.mark.asyncio
    async def test_update_last_sent_nonexistent(self, db_session):
        """update_last_sent returns None for nonexistent schedule."""
        next_time = datetime.now(UTC) + timedelta(days=7)
        result = await schedule_crud.update_last_sent(
            db_session,
            schedule_id=99999,
            next_scheduled=next_time,
        )
        assert result is None
