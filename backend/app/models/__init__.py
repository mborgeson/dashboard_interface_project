"""SQLAlchemy models for the application."""

from .base import SoftDeleteMixin, TimestampMixin
from .deal import Deal, DealStage
from .document import Document, DocumentType

# File Monitoring Models - imported after underwriting to avoid circular imports
from .file_monitor import FileChangeLog, MonitoredFile
from .property import Property

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
]
