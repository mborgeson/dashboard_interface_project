"""
Property model for real estate assets.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import JSON, CheckConstraint, Date, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import SoftDeleteMixin, TimestampMixin


class Property(Base, TimestampMixin, SoftDeleteMixin):
    """Property model representing real estate assets."""

    __tablename__ = "properties"

    __table_args__ = (
        CheckConstraint(
            "purchase_price >= 0", name="ck_properties_purchase_price_non_negative"
        ),
        CheckConstraint(
            "current_value >= 0", name="ck_properties_current_value_non_negative"
        ),
        CheckConstraint("total_units > 0", name="ck_properties_total_units_positive"),
        CheckConstraint("total_sf > 0", name="ck_properties_total_sf_positive"),
        CheckConstraint("stories > 0", name="ck_properties_stories_positive"),
        CheckConstraint(
            "year_built >= 1800 AND year_built <= 2100",
            name="ck_properties_year_built_range",
        ),
        CheckConstraint(
            "year_renovated >= 1800 AND year_renovated <= 2100",
            name="ck_properties_year_renovated_range",
        ),
        CheckConstraint(
            "cap_rate >= 0 AND cap_rate <= 100",
            name="ck_properties_cap_rate_range",
        ),
        CheckConstraint(
            "occupancy_rate >= 0 AND occupancy_rate <= 100",
            name="ck_properties_occupancy_rate_range",
        ),
        CheckConstraint(
            "avg_rent_per_unit >= 0",
            name="ck_properties_avg_rent_per_unit_non_negative",
        ),
        CheckConstraint(
            "avg_rent_per_sf >= 0", name="ck_properties_avg_rent_per_sf_non_negative"
        ),
        CheckConstraint(
            "parking_spaces >= 0", name="ck_properties_parking_spaces_non_negative"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Basic Information
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    property_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # multifamily, office, retail, industrial

    # Location
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    zip_code: Mapped[str] = mapped_column(String(20), nullable=False)
    county: Mapped[str | None] = mapped_column(String(100), nullable=True)
    market: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    submarket: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )

    # Physical Characteristics
    building_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    year_built: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year_renovated: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_sf: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lot_size_acres: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    stories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parking_spaces: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Financial Metrics
    purchase_price: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )
    current_value: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )
    acquisition_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Operating Metrics
    occupancy_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    avg_rent_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    avg_rent_per_sf: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )
    noi: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )
    cap_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 3),
        nullable=True,
    )

    # Extended Financial Data (JSON blob for nested frontend fields)
    financial_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Additional Data
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    amenities: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    unit_mix: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    images: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # External IDs
    external_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
    )
    data_source: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    # deals: Mapped[List["Deal"]] = relationship("Deal", back_populates="property")

    def __repr__(self) -> str:
        return f"<Property {self.name} ({self.city}, {self.state})>"

    @property
    def price_per_unit(self) -> Decimal | None:
        """Calculate price per unit."""
        if self.purchase_price and self.total_units:
            return self.purchase_price / self.total_units
        return None

    @property
    def price_per_sf(self) -> Decimal | None:
        """Calculate price per square foot."""
        if self.purchase_price and self.total_sf:
            return self.purchase_price / self.total_sf
        return None
