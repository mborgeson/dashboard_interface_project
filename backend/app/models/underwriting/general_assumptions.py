"""
GeneralAssumptions - Property basics, location, ownership (32 fields).

Maps to: 'Assumptions (Summary)'!$D$6 through $J$15 range
Cell Reference Category: "General Assumptions"
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


class GeneralAssumptions(Base, TimestampMixin, SourceTrackingMixin):
    """
    General property assumptions extracted from underwriting model.

    Contains: Property identification, location, physical characteristics,
    ownership history, quality ratings, and analysis dates.
    """

    __tablename__ = "uw_general_assumptions"

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
        back_populates="general_assumptions",
    )

    # Property Identification (D6-D11)
    property_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="PROPERTY_NAME - 'Assumptions (Summary)'!$D$6"
    )
    property_city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="PROPERTY_CITY - 'Assumptions (Summary)'!$D$8"
    )
    property_state: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="PROPERTY_STATE - 'Assumptions (Summary)'!$D$9"
    )
    year_built: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="YEAR_BUILT - 'Assumptions (Summary)'!$D$10"
    )
    year_renovated: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="YEAR_RENOVATED - 'Assumptions (Summary)'!$D$11"
    )

    # Quality Ratings (D13-D14)
    location_quality: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="LOCATION_QUALITY - 'Assumptions (Summary)'!$D$13"
    )
    building_quality: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="BUILDING_QUALITY - 'Assumptions (Summary)'!$D$14"
    )

    # Physical Characteristics (G6-G13)
    units: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="UNITS - 'Assumptions (Summary)'!$G$6"
    )
    avg_square_feet: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="AVG_SQUARE_FEET - 'Assumptions (Summary)'!$G$7"
    )
    parking_spaces_covered: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="NUMBER_OF_PARKING_SPACES_COVERED - 'Assumptions (Summary)'!$G$9"
    )
    parking_spaces_uncovered: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="NUMBER_OF_PARKING_SPACES_UNCOVERED - 'Assumptions (Summary)'!$G$10"
    )
    individually_metered: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="INDIVIDUALLY_METERED - 'Assumptions (Summary)'!$G$13"
    )

    # Ownership Information (I6-I15)
    current_owner: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="CURRENT_OWNER - 'Assumptions (Summary)'!$I$6"
    )
    last_sale_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="LAST_SALE_DATE - 'Assumptions (Summary)'!$I$7"
    )
    last_sale_price: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="LAST_SALE_PRICE - 'Assumptions (Summary)'!$I$8"
    )

    # Address Details (additional fields from General Assumptions)
    property_street_address: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Full street address"
    )
    property_zip_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="ZIP code"
    )
    property_county: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="County name"
    )
    property_latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
        comment="GPS latitude"
    )
    property_longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
        comment="GPS longitude"
    )

    # Additional Physical Details
    total_sf: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Total rentable square feet"
    )
    stories: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of stories"
    )
    buildings: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of buildings"
    )
    lot_size_acres: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4),
        nullable=True,
        comment="Lot size in acres"
    )
    building_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Garden, Mid-Rise, High-Rise, etc."
    )

    # Analysis Dates
    analysis_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Date of underwriting analysis"
    )
    t12_end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Trailing 12 month end date"
    )
    acquisition_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Projected/actual acquisition date"
    )

    # Property Classification
    asset_class: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Class A, B, C, D rating"
    )
    submarket: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Submarket name"
    )
    msa: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Metropolitan Statistical Area"
    )

    def __repr__(self) -> str:
        return f"<GeneralAssumptions {self.property_name} ({self.property_city}, {self.property_state})>"
