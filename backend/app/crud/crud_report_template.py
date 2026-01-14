"""
CRUD operations for Report Template and related models.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.report_template import (
    DistributionSchedule,
    QueuedReport,
    ReportStatus,
    ReportTemplate,
)
from app.schemas.reporting import (
    DistributionScheduleCreate,
    DistributionScheduleUpdate,
    QueuedReportCreate,
    ReportTemplateCreate,
    ReportTemplateUpdate,
)


class CRUDReportTemplate(
    CRUDBase[ReportTemplate, ReportTemplateCreate, ReportTemplateUpdate]
):
    """CRUD operations for ReportTemplate model."""

    async def get_by_category(
        self,
        db: AsyncSession,
        category: str,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ReportTemplate]:
        """Get templates by category."""
        result = await db.execute(
            select(ReportTemplate)
            .where(ReportTemplate.category == category)
            .where(ReportTemplate.is_deleted.is_(False))
            .order_by(ReportTemplate.name)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_defaults(
        self,
        db: AsyncSession,
    ) -> list[ReportTemplate]:
        """Get default system templates."""
        result = await db.execute(
            select(ReportTemplate)
            .where(ReportTemplate.is_default.is_(True))
            .where(ReportTemplate.is_deleted.is_(False))
            .order_by(ReportTemplate.category, ReportTemplate.name)
        )
        return list(result.scalars().all())

    async def get_filtered(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        category: str | None = None,
        is_default: bool | None = None,
        search: str | None = None,
    ) -> list[ReportTemplate]:
        """Get templates with filters."""
        query = select(ReportTemplate).where(ReportTemplate.is_deleted.is_(False))

        if category:
            query = query.where(ReportTemplate.category == category)

        if is_default is not None:
            query = query.where(ReportTemplate.is_default.is_(is_default))

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                ReportTemplate.name.ilike(search_pattern)
                | ReportTemplate.description.ilike(search_pattern)
            )

        query = query.order_by(ReportTemplate.name).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def count_filtered(
        self,
        db: AsyncSession,
        *,
        category: str | None = None,
        is_default: bool | None = None,
        search: str | None = None,
    ) -> int:
        """Count templates with filters."""
        query = (
            select(func.count())
            .select_from(ReportTemplate)
            .where(ReportTemplate.is_deleted.is_(False))
        )

        if category:
            query = query.where(ReportTemplate.category == category)

        if is_default is not None:
            query = query.where(ReportTemplate.is_default.is_(is_default))

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                ReportTemplate.name.ilike(search_pattern)
                | ReportTemplate.description.ilike(search_pattern)
            )

        result = await db.execute(query)
        return result.scalar() or 0


class CRUDQueuedReport(CRUDBase[QueuedReport, QueuedReportCreate, QueuedReportCreate]):
    """CRUD operations for QueuedReport model."""

    async def create_with_timestamp(
        self,
        db: AsyncSession,
        *,
        obj_in: QueuedReportCreate,
    ) -> QueuedReport:
        """Create a queued report with current timestamp."""
        db_obj = QueuedReport(
            **obj_in.model_dump(),
            requested_at=datetime.now(),
            status=ReportStatus.PENDING,
            progress=0,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_by_status(
        self,
        db: AsyncSession,
        status: str,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[QueuedReport]:
        """Get queued reports by status."""
        result = await db.execute(
            select(QueuedReport)
            .where(QueuedReport.status == status)
            .order_by(QueuedReport.requested_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent(
        self,
        db: AsyncSession,
        *,
        limit: int = 10,
    ) -> list[QueuedReport]:
        """Get recent queued reports."""
        result = await db.execute(
            select(QueuedReport).order_by(QueuedReport.requested_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        db: AsyncSession,
        *,
        report_id: int,
        status: str,
        progress: int = 0,
        error: str | None = None,
        download_url: str | None = None,
        file_size: str | None = None,
    ) -> QueuedReport | None:
        """Update report generation status."""
        report = await self.get(db, report_id)
        if not report:
            return None

        report.status = status
        report.progress = progress

        if error:
            report.error = error

        if download_url:
            report.download_url = download_url

        if file_size:
            report.file_size = file_size

        if status == ReportStatus.COMPLETED.value:
            report.completed_at = datetime.now()
            report.progress = 100

        db.add(report)
        await db.commit()
        await db.refresh(report)
        return report

    async def get_filtered(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
        template_id: int | None = None,
        requested_by: str | None = None,
    ) -> list[QueuedReport]:
        """Get queued reports with filters."""
        query = select(QueuedReport)

        if status:
            query = query.where(QueuedReport.status == status)

        if template_id:
            query = query.where(QueuedReport.template_id == template_id)

        if requested_by:
            query = query.where(QueuedReport.requested_by == requested_by)

        query = (
            query.order_by(QueuedReport.requested_at.desc()).offset(skip).limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def count_filtered(
        self,
        db: AsyncSession,
        *,
        status: str | None = None,
        template_id: int | None = None,
        requested_by: str | None = None,
    ) -> int:
        """Count queued reports with filters."""
        query = select(func.count()).select_from(QueuedReport)

        if status:
            query = query.where(QueuedReport.status == status)

        if template_id:
            query = query.where(QueuedReport.template_id == template_id)

        if requested_by:
            query = query.where(QueuedReport.requested_by == requested_by)

        result = await db.execute(query)
        return result.scalar() or 0


class CRUDDistributionSchedule(
    CRUDBase[
        DistributionSchedule, DistributionScheduleCreate, DistributionScheduleUpdate
    ]
):
    """CRUD operations for DistributionSchedule model."""

    async def get_active(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[DistributionSchedule]:
        """Get active distribution schedules."""
        result = await db.execute(
            select(DistributionSchedule)
            .where(DistributionSchedule.is_active.is_(True))
            .where(DistributionSchedule.is_deleted.is_(False))
            .order_by(DistributionSchedule.next_scheduled)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_due(
        self,
        db: AsyncSession,
        as_of: datetime | None = None,
    ) -> list[DistributionSchedule]:
        """Get schedules that are due to run."""
        if as_of is None:
            as_of = datetime.now()

        result = await db.execute(
            select(DistributionSchedule)
            .where(DistributionSchedule.is_active.is_(True))
            .where(DistributionSchedule.is_deleted.is_(False))
            .where(DistributionSchedule.next_scheduled <= as_of)
            .order_by(DistributionSchedule.next_scheduled)
        )
        return list(result.scalars().all())

    async def get_by_template(
        self,
        db: AsyncSession,
        template_id: int,
    ) -> list[DistributionSchedule]:
        """Get schedules for a specific template."""
        result = await db.execute(
            select(DistributionSchedule)
            .where(DistributionSchedule.template_id == template_id)
            .where(DistributionSchedule.is_deleted.is_(False))
            .order_by(DistributionSchedule.name)
        )
        return list(result.scalars().all())

    async def update_last_sent(
        self,
        db: AsyncSession,
        *,
        schedule_id: int,
        next_scheduled: datetime,
    ) -> DistributionSchedule | None:
        """Update last sent time and next scheduled time."""
        schedule = await self.get(db, schedule_id)
        if not schedule:
            return None

        schedule.last_sent = datetime.now()
        schedule.next_scheduled = next_scheduled

        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)
        return schedule


# Singleton instances
report_template = CRUDReportTemplate(ReportTemplate)
queued_report = CRUDQueuedReport(QueuedReport)
distribution_schedule = CRUDDistributionSchedule(DistributionSchedule)
