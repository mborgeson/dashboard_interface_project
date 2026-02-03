"""
Report template and queued report models for the reporting suite.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import SoftDeleteMixin, TimestampMixin


class ReportCategory(StrEnum):
    """Report template categories."""

    EXECUTIVE = "executive"
    FINANCIAL = "financial"
    MARKET = "market"
    PORTFOLIO = "portfolio"
    CUSTOM = "custom"


class ReportFormat(StrEnum):
    """Report export formats."""

    PDF = "pdf"
    EXCEL = "excel"
    PPTX = "pptx"


class ReportStatus(StrEnum):
    """Queued report status."""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ScheduleFrequency(StrEnum):
    """Distribution schedule frequency."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class ReportTemplate(Base, TimestampMixin, SoftDeleteMixin):
    """Report template model for reusable report configurations."""

    __tablename__ = "report_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        Enum(ReportCategory),
        default=ReportCategory.CUSTOM,
        nullable=False,
    )
    sections: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    export_formats: Mapped[list[str]] = mapped_column(
        JSON,
        default=lambda: ["pdf"],
        nullable=False,
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[str] = mapped_column(
        String(255), default="System", nullable=False
    )

    # Configuration for custom widgets/layout
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    queued_reports: Mapped[list["QueuedReport"]] = relationship(
        "QueuedReport",
        back_populates="template",
        lazy="dynamic",
    )
    schedules: Mapped[list["DistributionSchedule"]] = relationship(
        "DistributionSchedule",
        back_populates="template",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<ReportTemplate(id={self.id}, name='{self.name}', category='{self.category}')>"


class QueuedReport(Base, TimestampMixin):
    """Queued report model for tracking report generation."""

    __tablename__ = "queued_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("report_templates.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum(ReportStatus),
        default=ReportStatus.PENDING,
        nullable=False,
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    format: Mapped[str] = mapped_column(
        Enum(ReportFormat),
        default=ReportFormat.PDF,
        nullable=False,
    )
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    file_size: Mapped[str | None] = mapped_column(String(50), nullable=True)
    download_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    template: Mapped["ReportTemplate"] = relationship(
        "ReportTemplate",
        back_populates="queued_reports",
    )

    def __repr__(self) -> str:
        return (
            f"<QueuedReport(id={self.id}, name='{self.name}', status='{self.status}')>"
        )


class DistributionSchedule(Base, TimestampMixin, SoftDeleteMixin):
    """Distribution schedule model for automated report delivery."""

    __tablename__ = "distribution_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("report_templates.id"),
        nullable=False,
    )
    recipients: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    frequency: Mapped[str] = mapped_column(
        Enum(ScheduleFrequency),
        nullable=False,
    )
    day_of_week: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # 0-6 for weekly
    day_of_month: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # 1-31 for monthly
    time: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM format
    format: Mapped[str] = mapped_column(
        Enum(ReportFormat),
        default=ReportFormat.PDF,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_sent: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_scheduled: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    template: Mapped["ReportTemplate"] = relationship(
        "ReportTemplate",
        back_populates="schedules",
    )

    def __repr__(self) -> str:
        return f"<DistributionSchedule(id={self.id}, name='{self.name}', frequency='{self.frequency}')>"
