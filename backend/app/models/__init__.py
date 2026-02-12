"""SQLAlchemy models for the application."""

# Activity models - imported last to avoid circular imports with db/base.py
from .activity import ActivityType, DealActivity, PropertyActivity, UserWatchlist
from .activity_log import ActivityAction, ActivityLog
from .base import SoftDeleteMixin, TimestampMixin

# Construction Pipeline Models
from .construction import (
    ConstructionBrokerageMetrics,
    ConstructionEmploymentData,
    ConstructionPermitData,
    ConstructionProject,
    ConstructionSourceLog,
    PipelineStatus,
    ProjectClassification,
)
from .deal import Deal, DealStage
from .document import Document, DocumentType

# File Monitoring Models - imported after underwriting to avoid circular imports
from .file_monitor import FileChangeLog, MonitoredFile
from .property import Property

# Sales Analysis Models
from .reminder_dismissal import ReminderDismissal

# Reporting Models
from .report_settings import ReportSettings
from .report_template import (
    DistributionSchedule,
    QueuedReport,
    ReportCategory,
    ReportFormat,
    ReportStatus,
    ReportTemplate,
    ScheduleFrequency,
)
from .sales_data import SalesData

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
    # Activity Log Models (UUID-based)
    "ActivityAction",
    "ActivityLog",
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
    "ReportSettings",
    "ReportTemplate",
    "QueuedReport",
    "DistributionSchedule",
    "ReportCategory",
    "ReportFormat",
    "ReportStatus",
    "ScheduleFrequency",
    # Sales Analysis Models
    "ReminderDismissal",
    "SalesData",
    # Construction Pipeline Models
    "ConstructionProject",
    "ConstructionSourceLog",
    "ConstructionPermitData",
    "ConstructionEmploymentData",
    "ConstructionBrokerageMetrics",
    "PipelineStatus",
    "ProjectClassification",
]
