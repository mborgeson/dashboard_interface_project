"""
BudgetAssumptions - Acquisition and renovation costs (32 fields).

Maps to: 'Assumptions (Summary)' Budget sections
Cell Reference Category: "Budget Assumptions"
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


class BudgetAssumptions(Base, TimestampMixin, SourceTrackingMixin):
    """
    Budget assumptions for acquisition and renovation.

    Contains: Purchase price, closing costs, renovation budget,
    capital expenditures, and total project costs.
    """

    __tablename__ = "uw_budget_assumptions"

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
        back_populates="budget_assumptions",
    )

    # ==========================================================================
    # PURCHASE PRICE
    # ==========================================================================

    purchase_price: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Total purchase price"
    )
    price_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, comment="Purchase price per unit"
    )
    price_per_sf: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="Purchase price per square foot"
    )
    going_in_cap_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), nullable=True, comment="Going-in cap rate at purchase"
    )

    # ==========================================================================
    # CLOSING COSTS
    # ==========================================================================

    title_insurance: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, comment="Title insurance costs"
    )
    survey_costs: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, comment="Survey costs"
    )
    environmental_costs: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, comment="Environmental assessment costs"
    )
    appraisal_costs: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, comment="Appraisal costs"
    )
    legal_costs: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, comment="Legal and documentation costs"
    )
    transfer_taxes: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, comment="Transfer taxes and recording fees"
    )
    other_closing_costs: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, comment="Other closing costs"
    )
    total_closing_costs: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, comment="Total acquisition closing costs"
    )
    closing_costs_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Closing costs as percentage of purchase price",
    )

    # ==========================================================================
    # RENOVATION BUDGET
    # ==========================================================================

    # Unit Renovations
    interior_renovation_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="Interior renovation cost per unit"
    )
    appliance_package_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="Appliance package cost per unit"
    )
    flooring_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="Flooring cost per unit"
    )
    countertops_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="Countertop cost per unit"
    )
    fixtures_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="Fixtures cost per unit"
    )
    total_unit_renovation_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="Total unit renovation cost per unit"
    )
    total_unit_renovation_budget: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Total unit renovation budget"
    )

    # Exterior/Common Area
    exterior_renovation: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Exterior renovation budget"
    )
    common_area_renovation: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Common area renovation budget"
    )
    amenity_improvements: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Amenity improvements budget"
    )
    landscaping_improvements: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Landscaping improvements budget"
    )
    parking_improvements: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Parking lot/structure improvements"
    )

    # Building Systems
    hvac_replacement: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="HVAC replacement budget"
    )
    roof_replacement: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Roof replacement budget"
    )
    plumbing_updates: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Plumbing updates budget"
    )
    electrical_updates: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Electrical updates budget"
    )

    # Renovation Totals
    total_renovation_budget: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Total renovation budget"
    )
    renovation_contingency_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), nullable=True, comment="Renovation contingency percentage"
    )
    renovation_contingency_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Renovation contingency amount"
    )

    # ==========================================================================
    # TOTAL PROJECT COSTS
    # ==========================================================================

    total_project_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Total all-in project cost"
    )
    total_cost_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, comment="Total cost per unit"
    )
    total_cost_per_sf: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="Total cost per square foot"
    )

    def __repr__(self) -> str:
        return f"<BudgetAssumptions purchase={self.purchase_price} renovation={self.total_renovation_budget}>"
