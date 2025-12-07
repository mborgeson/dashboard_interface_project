"""
Property model for real estate assets.
"""
from datetime import date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import String, Integer, Numeric, Date, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, SoftDeleteMixin


class Property(Base, TimestampMixin, SoftDeleteMixin):
    """Property model representing real estate assets."""

    __tablename__ = "properties"

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
    county: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    market: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    submarket: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Physical Characteristics
    year_built: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    year_renovated: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_units: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_sf: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    lot_size_acres: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    stories: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parking_spaces: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Financial Metrics
    purchase_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )
    current_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )
    acquisition_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Operating Metrics
    occupancy_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    avg_rent_per_unit: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    avg_rent_per_sf: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )
    noi: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )
    cap_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 3),
        nullable=True,
    )

    # Additional Data
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    amenities: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    unit_mix: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    images: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # External IDs
    external_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
    )
    data_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    # deals: Mapped[List["Deal"]] = relationship("Deal", back_populates="property")

    def __repr__(self) -> str:
        return f"<Property {self.name} ({self.city}, {self.state})>"

    @property
    def price_per_unit(self) -> Optional[Decimal]:
        """Calculate price per unit."""
        if self.purchase_price and self.total_units:
            return self.purchase_price / self.total_units
        return None

    @property
    def price_per_sf(self) -> Optional[Decimal]:
        """Calculate price per square foot."""
        if self.purchase_price and self.total_sf:
            return self.purchase_price / self.total_sf
        return None
