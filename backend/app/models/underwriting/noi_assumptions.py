"""
NOIAssumptions - Income, expenses, and operating metrics (135 fields).

Maps to: 'Assumptions (Summary)' sheet NOI-related sections
Cell Reference Category: "NOI Assumptions"
"""
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.underwriting.source_tracking import SourceTrackingMixin

if TYPE_CHECKING:
    from app.models.underwriting.underwriting_model import UnderwritingModel


class NOIAssumptions(Base, TimestampMixin, SourceTrackingMixin):
    """
    NOI (Net Operating Income) assumptions.

    Contains: Revenue assumptions, expense ratios, vacancy factors,
    rent growth projections, expense growth, and operational metrics.
    """

    __tablename__ = "uw_noi_assumptions"

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
        back_populates="noi_assumptions",
    )

    # ==========================================================================
    # REVENUE ASSUMPTIONS
    # ==========================================================================

    # Market Rent Assumptions
    market_rent_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Market rent per unit per month"
    )
    market_rent_per_sf: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
        comment="Market rent per square foot per month"
    )
    in_place_rent_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Current in-place rent per unit"
    )
    loss_to_lease_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Loss to lease percentage"
    )

    # Rent Growth Projections (Year 1-5)
    rent_growth_year_1: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Year 1 rent growth rate"
    )
    rent_growth_year_2: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Year 2 rent growth rate"
    )
    rent_growth_year_3: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Year 3 rent growth rate"
    )
    rent_growth_year_4: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Year 4 rent growth rate"
    )
    rent_growth_year_5: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Year 5 rent growth rate"
    )

    # Vacancy & Collection Loss
    physical_vacancy_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Physical vacancy rate"
    )
    economic_vacancy_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Economic vacancy rate"
    )
    bad_debt_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Bad debt / collection loss percentage"
    )
    concessions_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Concessions percentage"
    )
    model_vacancy_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Model unit vacancy percentage"
    )
    employee_unit_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Employee unit vacancy percentage"
    )

    # Other Income
    other_income_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Other income per unit per year"
    )
    utility_reimbursement_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Utility reimbursement per unit per year"
    )
    parking_income_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Parking income per unit per year"
    )
    pet_income_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Pet income per unit per year"
    )
    late_fee_income_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Late fee income per unit per year"
    )
    application_fee_income_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Application fee income per unit per year"
    )
    other_income_growth_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Other income annual growth rate"
    )

    # ==========================================================================
    # EXPENSE ASSUMPTIONS
    # ==========================================================================

    # Administrative Expenses
    administrative_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Administrative expense per unit per year"
    )
    marketing_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Marketing expense per unit per year"
    )
    professional_fees_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Professional fees per unit per year"
    )

    # Payroll Expenses
    payroll_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Total payroll expense per unit per year"
    )
    management_salary_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Management salary per unit per year"
    )
    maintenance_salary_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Maintenance salary per unit per year"
    )
    payroll_taxes_benefits_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Payroll taxes and benefits percentage"
    )

    # Utilities
    utilities_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Total utilities per unit per year"
    )
    electricity_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Electricity per unit per year"
    )
    gas_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Gas per unit per year"
    )
    water_sewer_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Water/sewer per unit per year"
    )
    trash_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Trash per unit per year"
    )

    # Repairs & Maintenance
    repairs_maintenance_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="R&M per unit per year"
    )
    contract_services_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Contract services per unit per year"
    )
    make_ready_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Make-ready/turnover cost per unit per year"
    )
    landscaping_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Landscaping per unit per year"
    )

    # Insurance & Taxes
    insurance_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Insurance per unit per year"
    )
    real_estate_taxes_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Real estate taxes per unit per year"
    )
    tax_reassessment_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Expected tax reassessment percentage"
    )

    # Management Fee
    management_fee_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Property management fee percentage of EGI"
    )
    asset_management_fee_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Asset management fee percentage"
    )

    # Expense Growth
    expense_growth_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Annual expense growth rate"
    )
    insurance_growth_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Annual insurance growth rate"
    )
    tax_growth_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Annual property tax growth rate"
    )
    utility_growth_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Annual utility growth rate"
    )

    # ==========================================================================
    # CAPITAL RESERVES
    # ==========================================================================

    replacement_reserves_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Replacement reserves per unit per year"
    )
    capital_reserve_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Capital reserve as percentage of EGI"
    )

    # ==========================================================================
    # OPERATING METRICS (Calculated/Reference)
    # ==========================================================================

    # Per Unit Metrics
    total_revenue_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Total revenue per unit per year"
    )
    total_expenses_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Total expenses per unit per year"
    )
    noi_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="NOI per unit per year"
    )

    # Ratios
    expense_ratio: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Operating expense ratio (expenses/EGI)"
    )
    break_even_occupancy: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Break-even occupancy percentage"
    )

    # T-12 Reference Values
    t12_gpr: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="T-12 Gross Potential Rent"
    )
    t12_vacancy_loss: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="T-12 Vacancy Loss"
    )
    t12_concessions: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="T-12 Concessions"
    )
    t12_bad_debt: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="T-12 Bad Debt"
    )
    t12_other_income: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="T-12 Other Income"
    )
    t12_egi: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="T-12 Effective Gross Income"
    )
    t12_total_expenses: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="T-12 Total Operating Expenses"
    )
    t12_noi: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="T-12 Net Operating Income"
    )

    # Renovation Premium Assumptions
    renovation_rent_premium_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Expected rent premium per renovated unit"
    )
    renovation_lease_up_months: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Months to lease up renovated units"
    )
    units_to_renovate: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of units planned for renovation"
    )
    renovation_pace_per_month: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Unit renovation pace per month"
    )

    def __repr__(self) -> str:
        return f"<NOIAssumptions noi_per_unit={self.noi_per_unit}>"
