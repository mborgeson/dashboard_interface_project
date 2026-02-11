"""
Construction pipeline models — tracks Phoenix MSA multifamily development projects.

Five tables:
  1. ConstructionProject — master project registry (CoStar pipeline + municipal permits)
  2. ConstructionSourceLog — import/fetch audit trail for all data sources
  3. ConstructionPermitData — time-series permit data (Census BPS, FRED, municipal APIs)
  4. ConstructionEmploymentData — BLS construction employment time-series
  5. ConstructionBrokerageMetrics — quarterly brokerage report metrics (manual entry)

Property classifications (8 types):
  CONV_MR, CONV_CONDO, BTR, LIHTC, AGE_55, WORKFORCE, MIXED_USE, CONVERSION
"""

from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin

# ── Enums ────────────────────────────────────────────────────────────────────


class PipelineStatus(StrEnum):
    """Pipeline lifecycle stages for development projects."""

    PROPOSED = "proposed"
    FINAL_PLANNING = "final_planning"
    PERMITTED = "permitted"
    UNDER_CONSTRUCTION = "under_construction"
    DELIVERED = "delivered"


class ProjectClassification(StrEnum):
    """Multifamily property type classifications."""

    CONV_MR = "CONV_MR"
    CONV_CONDO = "CONV_CONDO"
    BTR = "BTR"
    LIHTC = "LIHTC"
    AGE_55 = "AGE_55"
    WORKFORCE = "WORKFORCE"
    MIXED_USE = "MIXED_USE"
    CONVERSION = "CONVERSION"


# ── Table 1: construction_projects ───────────────────────────────────────────


class ConstructionProject(Base, TimestampMixin):
    """Master project registry for Phoenix MSA multifamily development pipeline."""

    __tablename__ = "construction_projects"

    __table_args__ = (
        UniqueConstraint(
            "costar_property_id",
            "source_file",
            name="uq_construction_projects_costar_source",
        ),
        Index("ix_construction_projects_submarket", "submarket_cluster"),
        Index("ix_construction_projects_status", "pipeline_status"),
        Index("ix_construction_projects_classification", "primary_classification"),
        Index("ix_construction_projects_city", "city"),
    )

    # ── Primary Key ──────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── CoStar Identifiers ───────────────────────────────────────────────
    costar_property_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    property_type: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # ── Core Property Info ───────────────────────────────────────────────
    project_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    project_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(200), nullable=True)
    state: Mapped[str | None] = mapped_column(String(10), default="AZ")
    zip_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    county: Mapped[str | None] = mapped_column(String(200), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Market / Geography ───────────────────────────────────────────────
    market_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    submarket_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    submarket_cluster: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # ── Pipeline Status & Classification ─────────────────────────────────
    pipeline_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=PipelineStatus.PROPOSED
    )
    constr_status_raw: Mapped[str | None] = mapped_column(String(100), nullable=True)
    building_status_raw: Mapped[str | None] = mapped_column(String(100), nullable=True)
    primary_classification: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ProjectClassification.CONV_MR
    )
    secondary_tags: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── Building Info ────────────────────────────────────────────────────
    number_of_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    building_sf: Mapped[float | None] = mapped_column(Float, nullable=True)
    number_of_stories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_buildings: Mapped[int | None] = mapped_column(Integer, nullable=True)
    star_rating: Mapped[str | None] = mapped_column(String(50), nullable=True)
    building_class: Mapped[str | None] = mapped_column(String(10), nullable=True)
    style: Mapped[str | None] = mapped_column(String(100), nullable=True)
    secondary_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    construction_material: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    is_condo: Mapped[bool] = mapped_column(Boolean, default=False)
    number_of_elevators: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ceiling_height: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sprinklers: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── Unit Mix (percentages) ───────────────────────────────────────────
    pct_studio: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct_1bed: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct_2bed: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct_3bed: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct_4bed: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Unit Mix (counts) ────────────────────────────────────────────────
    num_studios: Mapped[int | None] = mapped_column(Integer, nullable=True)
    num_1bed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    num_2bed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    num_3bed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    num_4bed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    num_beds_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_unit_sf: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Rent Info ────────────────────────────────────────────────────────
    rent_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    affordable_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    market_segment: Mapped[str | None] = mapped_column(String(200), nullable=True)
    avg_asking_per_unit: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_asking_per_sf: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_effective_per_unit: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_effective_per_sf: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_concessions_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    vacancy_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct_leased: Mapped[float | None] = mapped_column(Float, nullable=True)
    pre_leasing: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # ── Timeline ─────────────────────────────────────────────────────────
    construction_begin: Mapped[str | None] = mapped_column(String(100), nullable=True)
    year_built: Mapped[int | None] = mapped_column(Integer, nullable=True)
    month_built: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year_renovated: Mapped[int | None] = mapped_column(Integer, nullable=True)
    month_renovated: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── Developer / Owner / Architect ────────────────────────────────────
    developer_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    owner_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    owner_contact: Mapped[str | None] = mapped_column(String(500), nullable=True)
    architect_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    property_manager_name: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    # ── Sale / For-Sale Info ─────────────────────────────────────────────
    for_sale_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    for_sale_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    for_sale_price_per_unit: Mapped[float | None] = mapped_column(Float, nullable=True)
    for_sale_price_per_sf: Mapped[float | None] = mapped_column(Float, nullable=True)
    cap_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_sale_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_sale_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    days_on_market: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Land / Parking / Zoning ──────────────────────────────────────────
    land_area_ac: Mapped[float | None] = mapped_column(Float, nullable=True)
    land_area_sf: Mapped[float | None] = mapped_column(Float, nullable=True)
    zoning: Mapped[str | None] = mapped_column(String(200), nullable=True)
    parking_spaces: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parking_spaces_per_unit: Mapped[float | None] = mapped_column(Float, nullable=True)
    parking_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Flood / FEMA ─────────────────────────────────────────────────────
    fema_flood_zone: Mapped[str | None] = mapped_column(Text, nullable=True)
    flood_risk_area: Mapped[str | None] = mapped_column(String(200), nullable=True)
    in_sfha: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ── Financing ────────────────────────────────────────────────────────
    origination_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    origination_date: Mapped[str | None] = mapped_column(String(100), nullable=True)
    originator: Mapped[str | None] = mapped_column(String(500), nullable=True)
    interest_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    interest_rate_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    loan_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    maturity_date: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── Tax ───────────────────────────────────────────────────────────────
    tax_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    taxes_per_sf: Mapped[float | None] = mapped_column(Float, nullable=True)
    taxes_total: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Amenities / Misc ─────────────────────────────────────────────────
    amenities: Mapped[str | None] = mapped_column(Text, nullable=True)
    features: Mapped[str | None] = mapped_column(Text, nullable=True)
    closest_transit_stop: Mapped[str | None] = mapped_column(String(500), nullable=True)
    closest_transit_dist_mi: Mapped[float | None] = mapped_column(Float, nullable=True)
    university: Mapped[str | None] = mapped_column(String(500), nullable=True)
    energy_star: Mapped[str | None] = mapped_column(String(50), nullable=True)
    leed_certified: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ── Source Tracking ──────────────────────────────────────────────────
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="costar"
    )
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    imported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<ConstructionProject(id={self.id}, name={self.project_name}, "
            f"units={self.number_of_units}, status={self.pipeline_status})>"
        )


# ── Table 2: construction_source_logs ────────────────────────────────────────


class ConstructionSourceLog(Base):
    """Audit trail for data source imports and API fetches."""

    __tablename__ = "construction_source_logs"

    __table_args__ = (
        Index("ix_construction_source_logs_source", "source_name"),
        Index("ix_construction_source_logs_fetched", "fetched_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    fetch_type: Mapped[str] = mapped_column(String(50), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    records_fetched: Mapped[int] = mapped_column(Integer, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<ConstructionSourceLog(id={self.id}, source={self.source_name}, "
            f"success={self.success}, fetched={self.fetched_at})>"
        )


# ── Table 3: construction_permit_data ────────────────────────────────────────


class ConstructionPermitData(Base, TimestampMixin):
    """Time-series permit data from Census BPS, FRED, and municipal APIs."""

    __tablename__ = "construction_permit_data"

    __table_args__ = (
        UniqueConstraint(
            "source",
            "series_id",
            "period_date",
            name="uq_permit_data_source_series_period",
        ),
        Index("ix_construction_permit_source_series", "source", "series_id"),
        Index("ix_construction_permit_period", "period_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    series_id: Mapped[str] = mapped_column(String(200), nullable=False)
    geography: Mapped[str | None] = mapped_column(String(200), nullable=True)
    period_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_type: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(100), nullable=True)
    structure_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_log_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("construction_source_logs.id"), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<ConstructionPermitData(source={self.source}, series={self.series_id}, "
            f"date={self.period_date}, value={self.value})>"
        )


# ── Table 4: construction_employment_data ────────────────────────────────────


class ConstructionEmploymentData(Base, TimestampMixin):
    """BLS construction employment time-series for Phoenix MSA."""

    __tablename__ = "construction_employment_data"

    __table_args__ = (
        UniqueConstraint(
            "series_id",
            "period_date",
            name="uq_employment_series_period",
        ),
        Index("ix_employment_series_date", "series_id", "period_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_id: Mapped[str] = mapped_column(String(200), nullable=False)
    series_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    period_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    period_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="monthly"
    )
    source_log_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("construction_source_logs.id"), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<ConstructionEmploymentData(series={self.series_id}, "
            f"date={self.period_date}, value={self.value})>"
        )


# ── Table 5: construction_brokerage_metrics ──────────────────────────────────


class ConstructionBrokerageMetrics(Base, TimestampMixin):
    """Quarterly brokerage report metrics (manually entered)."""

    __tablename__ = "construction_brokerage_metrics"

    __table_args__ = (
        UniqueConstraint(
            "report_source",
            "report_quarter",
            "metric_name",
            name="uq_brokerage_source_quarter_metric",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_source: Mapped[str] = mapped_column(String(200), nullable=False)
    report_quarter: Mapped[str] = mapped_column(String(10), nullable=False)
    report_year: Mapped[int] = mapped_column(Integer, nullable=False)
    metric_name: Mapped[str] = mapped_column(String(200), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    entered_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_log_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("construction_source_logs.id"), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<ConstructionBrokerageMetrics(source={self.report_source}, "
            f"quarter={self.report_quarter}, metric={self.metric_name})>"
        )
