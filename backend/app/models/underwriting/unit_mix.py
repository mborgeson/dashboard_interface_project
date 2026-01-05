"""
UnitMix - Normalized unit type data (per-unit-type rows).

Maps to: 'Unit Mix' sheet data
Cell Reference Category: "Unit Mix Assumptions"

This table is normalized - instead of 91 columns for fixed unit types,
each row represents one unit type, allowing flexible property configurations.
"""
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.underwriting.source_tracking import SourceTrackingMixin

if TYPE_CHECKING:
    from app.models.underwriting.underwriting_model import UnderwritingModel


class UnitMix(Base, TimestampMixin, SourceTrackingMixin):
    """
    Unit mix data - one row per unit type.

    Contains: Unit type characteristics, counts, rents,
    and renovation assumptions per unit type.
    """

    __tablename__ = "uw_unit_mix"

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
        back_populates="unit_mixes",
    )

    # ==========================================================================
    # UNIT TYPE IDENTIFICATION
    # ==========================================================================

    unit_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Unit type identifier (e.g., 1BR/1BA, 2BR/2BA)"
    )
    unit_type_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Short code for unit type (e.g., A1, B2)"
    )
    bedrooms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of bedrooms"
    )
    bathrooms: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 1),
        nullable=True,
        comment="Number of bathrooms"
    )

    # ==========================================================================
    # UNIT COUNTS
    # ==========================================================================

    unit_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of units of this type"
    )
    unit_count_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Percentage of total units"
    )

    # ==========================================================================
    # PHYSICAL CHARACTERISTICS
    # ==========================================================================

    avg_sf: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Average square feet per unit"
    )
    total_sf: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Total square feet for this unit type"
    )

    # ==========================================================================
    # RENT INFORMATION
    # ==========================================================================

    # In-Place Rent
    in_place_rent: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Current in-place rent per unit"
    )
    in_place_rent_per_sf: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
        comment="Current in-place rent per SF"
    )

    # Market Rent
    market_rent: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Market rent per unit"
    )
    market_rent_per_sf: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
        comment="Market rent per SF"
    )

    # Loss to Lease
    loss_to_lease: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Loss to lease amount per unit"
    )
    loss_to_lease_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Loss to lease percentage"
    )

    # Pro Forma Rent
    proforma_rent: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Pro forma rent per unit (post-renovation)"
    )
    proforma_rent_per_sf: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
        comment="Pro forma rent per SF"
    )

    # Rent Growth
    rent_premium_post_renovation: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Expected rent premium after renovation"
    )

    # ==========================================================================
    # RENOVATION ASSUMPTIONS
    # ==========================================================================

    units_to_renovate: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of units to renovate"
    )
    renovation_cost_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Renovation cost per unit"
    )
    total_renovation_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Total renovation cost for this unit type"
    )
    renovation_scope: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Light, Medium, Heavy renovation scope"
    )

    # ==========================================================================
    # REVENUE CALCULATIONS
    # ==========================================================================

    monthly_gpr: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Monthly gross potential rent for this unit type"
    )
    annual_gpr: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Annual gross potential rent for this unit type"
    )

    def __repr__(self) -> str:
        return f"<UnitMix {self.unit_type} x{self.unit_count} @ ${self.market_rent}>"
