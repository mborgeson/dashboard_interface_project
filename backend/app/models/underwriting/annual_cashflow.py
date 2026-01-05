"""
AnnualCashflow - Time-series cashflow projections (per-year rows).

Maps to: 'Annual Cashflows' sheet data
Cell Reference Category: "Annual Cashflows"

This table is normalized - instead of 215 columns (43 line items × 5 years),
each row represents one year of cashflow data with all line items.
"""
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.underwriting.source_tracking import SourceTrackingMixin

if TYPE_CHECKING:
    from app.models.underwriting.underwriting_model import UnderwritingModel


class AnnualCashflow(Base, TimestampMixin, SourceTrackingMixin):
    """
    Annual cashflow projections - one row per year.

    Contains: Revenue, expenses, NOI, debt service, and cash flow
    projections for each year of the hold period.
    """

    __tablename__ = "uw_annual_cashflows"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Parent relationship
    underwriting_model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("underwriting_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    underwriting_model: Mapped["UnderwritingModel"] = relationship(
        "UnderwritingModel",
        back_populates="annual_cashflows",
    )

    # ==========================================================================
    # PERIOD IDENTIFICATION
    # ==========================================================================

    year_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Year number (1, 2, 3, 4, 5, etc.)"
    )
    period_label: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Period label (T-12, Year 1, Year 2, etc.)"
    )
    period_start_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Start date of period"
    )
    period_end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="End date of period"
    )
    is_partial_year: Mapped[bool | None] = mapped_column(
        nullable=True,
        comment="Whether this is a partial year"
    )

    # ==========================================================================
    # REVENUE
    # ==========================================================================

    # Gross Potential Rent
    gross_potential_rent: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Gross potential rent"
    )

    # Vacancy & Loss
    vacancy_loss: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Vacancy loss"
    )
    loss_to_lease: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Loss to lease"
    )
    concessions: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Concessions"
    )
    bad_debt: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Bad debt/collection loss"
    )
    model_unit_loss: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Model unit loss"
    )
    employee_unit_loss: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Employee unit loss"
    )

    # Net Rental Income
    net_rental_income: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Net rental income"
    )

    # Other Income
    utility_reimbursement: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Utility reimbursement income"
    )
    parking_income: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Parking income"
    )
    pet_income: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Pet income"
    )
    late_fee_income: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Late fee income"
    )
    application_fee_income: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Application fee income"
    )
    other_income: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Other miscellaneous income"
    )
    total_other_income: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Total other income"
    )

    # Effective Gross Income
    effective_gross_income: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Effective gross income (EGI)"
    )

    # ==========================================================================
    # EXPENSES
    # ==========================================================================

    # Administrative
    administrative: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Administrative expenses"
    )
    marketing: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Marketing expenses"
    )
    professional_fees: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Professional fees"
    )

    # Payroll
    payroll: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Total payroll"
    )
    management_payroll: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Management payroll"
    )
    maintenance_payroll: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Maintenance payroll"
    )
    payroll_taxes_benefits: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Payroll taxes and benefits"
    )

    # Utilities
    utilities: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Total utilities"
    )
    electricity: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Electricity"
    )
    gas: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Gas"
    )
    water_sewer: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Water/sewer"
    )
    trash: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Trash"
    )

    # Repairs & Maintenance
    repairs_maintenance: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Repairs and maintenance"
    )
    contract_services: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Contract services"
    )
    make_ready: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Make-ready/turnover costs"
    )
    landscaping: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Landscaping"
    )

    # Fixed Expenses
    insurance: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Insurance"
    )
    real_estate_taxes: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Real estate taxes"
    )

    # Management Fee
    management_fee: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Property management fee"
    )

    # Total Expenses
    total_operating_expenses: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Total operating expenses"
    )

    # ==========================================================================
    # NET OPERATING INCOME
    # ==========================================================================

    net_operating_income: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Net operating income (NOI)"
    )

    # ==========================================================================
    # CAPITAL & RESERVES
    # ==========================================================================

    replacement_reserves: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Replacement reserves"
    )
    capital_expenditures: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Capital expenditures"
    )
    renovation_costs: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Renovation costs during this period"
    )

    # ==========================================================================
    # DEBT SERVICE
    # ==========================================================================

    senior_debt_service: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Senior debt service"
    )
    senior_interest: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Senior debt interest portion"
    )
    senior_principal: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Senior debt principal portion"
    )
    mezz_debt_service: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Mezzanine debt service"
    )
    total_debt_service: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Total debt service"
    )

    # ==========================================================================
    # CASH FLOW
    # ==========================================================================

    cash_flow_before_debt: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Cash flow before debt service"
    )
    cash_flow_after_debt: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Cash flow after debt service"
    )

    # ==========================================================================
    # DISTRIBUTIONS
    # ==========================================================================

    lp_distribution: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="LP distribution for period"
    )
    gp_distribution: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="GP distribution for period"
    )
    total_distributions: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Total distributions"
    )

    # ==========================================================================
    # METRICS
    # ==========================================================================

    dscr: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Debt service coverage ratio"
    )
    cash_on_cash_return: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Cash-on-cash return"
    )
    occupancy_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Occupancy rate for period"
    )
    expense_ratio: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Expense ratio (expenses/EGI)"
    )

    def __repr__(self) -> str:
        return f"<AnnualCashflow Year {self.year_number} NOI={self.net_operating_income}>"
