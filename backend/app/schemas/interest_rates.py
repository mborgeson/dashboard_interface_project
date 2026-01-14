"""
Interest rate schemas for API request/response validation.
"""

from datetime import datetime

from pydantic import Field

from .base import BaseSchema


class KeyRate(BaseSchema):
    """Schema for a key interest rate."""

    id: str = Field(..., description="Unique identifier for the rate")
    name: str = Field(..., description="Full name of the rate")
    short_name: str = Field(..., description="Short display name")
    current_value: float = Field(..., description="Current rate value as percentage")
    previous_value: float = Field(..., description="Previous rate value")
    change: float = Field(..., description="Absolute change from previous")
    change_percent: float = Field(..., description="Percentage change")
    as_of_date: str = Field(..., description="Date of the rate (YYYY-MM-DD)")
    category: str = Field(
        ...,
        pattern="^(federal|treasury|sofr|mortgage)$",
        description="Rate category",
    )
    description: str = Field(..., description="Description of the rate")


class YieldCurvePoint(BaseSchema):
    """Schema for a point on the Treasury yield curve."""

    maturity: str = Field(..., description="Maturity label (e.g., 1M, 2Y, 10Y)")
    yield_value: float = Field(..., alias="yield", description="Current yield")
    previous_yield: float = Field(..., description="Previous yield value")
    maturity_months: int = Field(..., description="Maturity in months")


class HistoricalRate(BaseSchema):
    """Schema for historical rate data at a point in time."""

    date: str = Field(..., description="Date (YYYY-MM format)")
    federal_funds: float = Field(..., description="Federal funds rate")
    treasury_2y: float = Field(..., description="2-year Treasury yield")
    treasury_5y: float = Field(..., description="5-year Treasury yield")
    treasury_10y: float = Field(..., description="10-year Treasury yield")
    treasury_30y: float = Field(..., description="30-year Treasury yield")
    sofr: float = Field(..., description="SOFR rate")
    mortgage_30y: float = Field(..., description="30-year mortgage rate")


class RateSpread(BaseSchema):
    """Schema for rate spread data."""

    date: str = Field(..., description="Date")
    spread: float = Field(..., description="Spread value")


class TreasurySpread(RateSpread):
    """Schema for Treasury spread (2s10s)."""

    pass


class MortgageSpread(RateSpread):
    """Schema for mortgage spread over Treasury."""

    pass


class FedFundsVsTreasurySpread(BaseSchema):
    """Schema for Fed Funds vs Treasury comparison."""

    date: str
    fed_funds: float
    treasury_10y: float
    spread: float


class RateSpreads(BaseSchema):
    """Schema for all rate spreads."""

    treasury_spread_2s10s: list[TreasurySpread] = Field(
        ..., description="2Y vs 10Y Treasury spread"
    )
    mortgage_spread: list[MortgageSpread] = Field(
        ..., description="30Y mortgage spread over 10Y Treasury"
    )
    fed_funds_vs_treasury: list[FedFundsVsTreasurySpread] = Field(
        ..., description="Fed Funds vs 10Y Treasury"
    )


class RateDataSource(BaseSchema):
    """Schema for rate data source information."""

    id: str = Field(..., description="Source identifier")
    name: str = Field(..., description="Source name")
    url: str = Field(..., description="Source URL")
    description: str = Field(..., description="Source description")
    data_types: list[str] = Field(..., description="Types of data provided")
    update_frequency: str = Field(..., description="How often data is updated")
    logo: str | None = Field(None, description="Logo URL")


class LendingSpread(BaseSchema):
    """Schema for real estate lending spread information."""

    name: str = Field(..., description="Loan type name")
    spread: float = Field(..., description="Spread over benchmark")
    benchmark: str = Field(..., description="Benchmark rate")


class RealEstateLendingContext(BaseSchema):
    """Schema for real estate lending context with typical spreads."""

    typical_spreads: dict[str, LendingSpread] = Field(
        ..., description="Typical spreads by loan type"
    )
    current_indicative_rates: dict[str, float] = Field(
        ..., description="Current indicative rates by loan type"
    )


# ==================== Response Schemas ====================


class KeyRatesResponse(BaseSchema):
    """Response schema for current key rates."""

    key_rates: list[KeyRate]
    last_updated: datetime
    source: str = "mock"


class YieldCurveResponse(BaseSchema):
    """Response schema for Treasury yield curve."""

    yield_curve: list[YieldCurvePoint]
    as_of_date: str
    last_updated: datetime
    source: str = "mock"


class HistoricalRatesResponse(BaseSchema):
    """Response schema for historical rates."""

    rates: list[HistoricalRate]
    start_date: str
    end_date: str
    last_updated: datetime
    source: str = "mock"


class DataSourcesResponse(BaseSchema):
    """Response schema for data sources."""

    sources: list[RateDataSource]


class RateSpreadsResponse(BaseSchema):
    """Response schema for rate spreads."""

    spreads: RateSpreads
    last_updated: datetime
    source: str = "mock"


class LendingContextResponse(BaseSchema):
    """Response schema for real estate lending context."""

    context: RealEstateLendingContext
    last_updated: datetime
