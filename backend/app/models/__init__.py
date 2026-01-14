"""SQLAlchemy models for the application."""

# Activity models - imported last to avoid circular imports with db/base.py
from .activity import ActivityType, DealActivity, PropertyActivity, UserWatchlist
from .base import SoftDeleteMixin, TimestampMixin
from .deal import Deal, DealStage
from .document import Document, DocumentType

# File Monitoring Models - imported after underwriting to avoid circular imports
from .file_monitor import FileChangeLog, MonitoredFile
from .property import Property

# Reporting Models
from .report_template import (
    DistributionSchedule,
    QueuedReport,
    ReportCategory,
    ReportFormat,
    ReportStatus,
    ReportTemplate,
    ScheduleFrequency,
)

# Underwriting Models
from .underwriting import (
    AnnualCashflow,
    BudgetAssumptions,
    EquityReturns,
    ExitAssumptions,
    FinancingAssumptions,
    GeneralAssumptions,
    NOIAssumptions,
    PropertyReturns,
    RentComp,
    SalesComp,
    UnderwritingModel,
    UnitMix,
)
from .user import User

__all__ = [
    # Base Mixins
    "TimestampMixin",
    "SoftDeleteMixin",
    # Core Models
    "User",
    "Property",
    "Deal",
    "DealStage",
    "Document",
    "DocumentType",
    # Activity Models
    "ActivityType",
    "PropertyActivity",
    "DealActivity",
    "UserWatchlist",
    # File Monitoring Models
    "MonitoredFile",
    "FileChangeLog",
    # Underwriting Models
    "UnderwritingModel",
    "GeneralAssumptions",
    "ExitAssumptions",
    "NOIAssumptions",
    "FinancingAssumptions",
    "BudgetAssumptions",
    "PropertyReturns",
    "EquityReturns",
    "UnitMix",
    "RentComp",
    "SalesComp",
    "AnnualCashflow",
    # Reporting Models
    "ReportTemplate",
    "QueuedReport",
    "DistributionSchedule",
    "ReportCategory",
    "ReportFormat",
    "ReportStatus",
    "ScheduleFrequency",
]
