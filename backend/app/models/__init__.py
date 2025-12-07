"""SQLAlchemy models for the application."""
from .base import TimestampMixin, SoftDeleteMixin
from .user import User
from .property import Property
from .deal import Deal, DealStage

# Underwriting Models
from .underwriting import (
    UnderwritingModel,
    GeneralAssumptions,
    ExitAssumptions,
    NOIAssumptions,
    FinancingAssumptions,
    BudgetAssumptions,
    PropertyReturns,
    EquityReturns,
    UnitMix,
    RentComp,
    SalesComp,
    AnnualCashflow,
)

__all__ = [
    # Base Mixins
    "TimestampMixin",
    "SoftDeleteMixin",
    # Core Models
    "User",
    "Property",
    "Deal",
    "DealStage",
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
