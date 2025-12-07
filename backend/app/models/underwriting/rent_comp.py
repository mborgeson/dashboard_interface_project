"""
RentComp - Market rent comparables (per-comp rows).

Maps to: 'Rent Comps' sheet data
Cell Reference Category: "Rent Comps"

This table is normalized - instead of 270 columns (10 comps × 27 fields),
each row represents one comparable property.
"""
from datetime import date
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Numeric, Date, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.underwriting.source_tracking import SourceTrackingMixin

if TYPE_CHECKING:
    from app.models.underwriting.underwriting_model import UnderwritingModel


class RentComp(Base, TimestampMixin, SourceTrackingMixin):
    """
    Rent comparable property data - one row per comparable.

    Contains: Property identification, physical characteristics,
    rent metrics, occupancy, and competitive positioning.
    """

    __tablename__ = "uw_rent_comps"

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
        back_populates="rent_comps",
    )

    # Comp ordering
    comp_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Comparable number (1, 2, 3, etc.)"
    )

    # ==========================================================================
    # PROPERTY IDENTIFICATION
    # ==========================================================================

    property_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Comparable property name"
    )
    property_address: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Full street address"
    )
    property_city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="City"
    )
    property_state: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="State"
    )
    property_zip: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="ZIP code"
    )
    distance_miles: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2),
        nullable=True,
        comment="Distance from subject property in miles"
    )

    # ==========================================================================
    # PHYSICAL CHARACTERISTICS
    # ==========================================================================

    year_built: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Year built"
    )
    year_renovated: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Year renovated"
    )
    total_units: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total number of units"
    )
    total_sf: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total square feet"
    )
    avg_unit_sf: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Average unit size in SF"
    )
    stories: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of stories"
    )
    building_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Garden, Mid-Rise, High-Rise"
    )

    # ==========================================================================
    # QUALITY & CLASSIFICATION
    # ==========================================================================

    asset_class: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="Class A, B, C, D"
    )
    condition: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Excellent, Good, Fair, Poor"
    )
    amenity_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Amenity rating 1-10"
    )

    # ==========================================================================
    # RENT METRICS
    # ==========================================================================

    avg_rent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Average rent per unit"
    )
    avg_rent_per_sf: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2),
        nullable=True,
        comment="Average rent per SF"
    )

    # By Unit Type
    studio_rent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Studio rent"
    )
    one_br_rent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="1 BR rent"
    )
    two_br_rent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="2 BR rent"
    )
    three_br_rent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="3 BR rent"
    )

    # Rent Trends
    rent_growth_yoy: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Year-over-year rent growth"
    )
    concessions: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Current concession offerings"
    )
    effective_rent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Effective rent after concessions"
    )

    # ==========================================================================
    # OCCUPANCY & LEASING
    # ==========================================================================

    occupancy_pct: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Current occupancy rate"
    )
    vacancy_pct: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Current vacancy rate"
    )
    leasing_velocity: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Leases per month"
    )
    avg_lease_term: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Average lease term in months"
    )

    # ==========================================================================
    # OWNERSHIP & MANAGEMENT
    # ==========================================================================

    owner_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Property owner"
    )
    management_company: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Management company"
    )

    # ==========================================================================
    # DATA SOURCE
    # ==========================================================================

    data_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Date rent data was collected"
    )
    data_source: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="CoStar, Yardi, etc."
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Additional notes about comparable"
    )

    def __repr__(self) -> str:
        return f"<RentComp #{self.comp_number} {self.property_name}>"
