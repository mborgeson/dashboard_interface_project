"""
Underwriting Models Package

Comprehensive SQLAlchemy models for multifamily real estate underwriting,
designed to support SharePoint/Excel extraction and real-time data synchronization.

Categories (based on B&R Capital underwriting model):
- UnderwritingModel: Parent entity linking property/deal to underwriting data
- GeneralAssumptions: Property basics, location, ownership (32 fields)
- ExitAssumptions: Exit timing and disposition (3 fields)
- NOIAssumptions: Income, expenses, operating metrics (135 fields)
- FinancingAssumptions: Debt and equity structure (53 fields)
- BudgetAssumptions: Acquisition and renovation costs (32 fields)
- PropertyReturns: Property-level return metrics (44 fields)
- EquityReturns: Equity-level return metrics (21 fields)
- UnitMix: Normalized unit type data (per-unit-type rows)
- RentComp: Market rent comparables (per-comp rows)
- SalesComp: Transaction comparables (per-comp rows)
- AnnualCashflow: Time-series cashflow projections (per-year rows)
"""

from app.models.underwriting.annual_cashflow import AnnualCashflow
from app.models.underwriting.budget_assumptions import BudgetAssumptions
from app.models.underwriting.equity_returns import EquityReturns
from app.models.underwriting.exit_assumptions import ExitAssumptions
from app.models.underwriting.financing_assumptions import FinancingAssumptions
from app.models.underwriting.general_assumptions import GeneralAssumptions
from app.models.underwriting.noi_assumptions import NOIAssumptions
from app.models.underwriting.property_returns import PropertyReturns
from app.models.underwriting.rent_comp import RentComp
from app.models.underwriting.sales_comp import SalesComp
from app.models.underwriting.underwriting_model import (
    UnderwritingModel,
    UnderwritingStatus,
)
from app.models.underwriting.unit_mix import UnitMix

__all__ = [
    "UnderwritingModel",
    "UnderwritingStatus",
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
