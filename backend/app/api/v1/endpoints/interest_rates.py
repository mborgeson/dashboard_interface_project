"""
Interest Rates API endpoints.

Provides current and historical interest rate data including:
- Key rates (Fed Funds, Treasury yields, SOFR, mortgage rates)
- Treasury yield curve
- Historical rates
- Rate spreads
- Data source information
- Real estate lending context
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Query

from app.schemas.interest_rates import (
    DataSourcesResponse,
    HistoricalRatesResponse,
    KeyRatesResponse,
    LendingContextResponse,
    RateSpreadsResponse,
    YieldCurveResponse,
)
from app.services.interest_rates import get_interest_rates_service

router = APIRouter()


@router.get("/current", response_model=KeyRatesResponse)
async def get_current_rates():
    """
    Get current key interest rates.

    Returns Federal Funds rate, Treasury yields (2Y, 5Y, 7Y, 10Y),
    SOFR rates, and mortgage rates with change from previous values.

    Rates are cached for 5 minutes and sourced from FRED API
    (falls back to mock data if unavailable).
    """
    service = get_interest_rates_service()
    data = await service.get_key_rates()

    return KeyRatesResponse(
        key_rates=data["key_rates"],
        last_updated=datetime.now(UTC),
        source=data.get("source", "mock"),
    )


@router.get("/yield-curve", response_model=YieldCurveResponse)
async def get_yield_curve():
    """
    Get current Treasury yield curve.

    Returns yield data for maturities from 1 month to 30 years,
    including current and previous yield values.

    The yield curve is a key indicator for economic outlook:
    - Normal curve (upward sloping): Economic growth expected
    - Flat curve: Uncertainty about future growth
    - Inverted curve: Potential recession indicator
    """
    service = get_interest_rates_service()
    data = await service.get_yield_curve()

    return YieldCurveResponse(
        yield_curve=data["yield_curve"],
        as_of_date=data["as_of_date"],
        last_updated=datetime.now(UTC),
        source=data.get("source", "mock"),
    )


@router.get("/historical", response_model=HistoricalRatesResponse)
async def get_historical_rates(
    months: int = Query(
        12, ge=1, le=60, description="Number of months of historical data"
    ),
):
    """
    Get historical interest rate data.

    Returns monthly historical data for key rates including:
    - Federal Funds rate
    - Treasury yields (2Y, 5Y, 10Y, 30Y)
    - SOFR
    - 30-year mortgage rate

    Args:
        months: Number of months of data to return (1-60, default 12)
    """
    service = get_interest_rates_service()
    data = await service.get_historical_rates(months)

    return HistoricalRatesResponse(
        rates=data["rates"],
        start_date=data["start_date"],
        end_date=data["end_date"],
        last_updated=datetime.now(UTC),
        source=data.get("source", "mock"),
    )


@router.get("/spreads", response_model=RateSpreadsResponse)
async def get_rate_spreads(
    months: int = Query(12, ge=1, le=60, description="Number of months of data"),
):
    """
    Get calculated rate spreads.

    Returns spread analysis including:
    - 2s10s Treasury spread (10Y - 2Y): Yield curve steepness indicator
    - Mortgage spread (30Y mortgage - 10Y Treasury): Credit premium
    - Fed Funds vs Treasury: Monetary policy stance indicator

    Args:
        months: Number of months of data to return (1-60, default 12)
    """
    service = get_interest_rates_service()
    data = await service.get_rate_spreads(months)

    return RateSpreadsResponse(
        spreads=data["spreads"],
        last_updated=datetime.now(UTC),
        source=data.get("source", "mock"),
    )


@router.get("/data-sources", response_model=DataSourcesResponse)
async def get_data_sources():
    """
    Get list of interest rate data sources.

    Returns information about authoritative sources for rate data:
    - U.S. Treasury Department
    - Federal Reserve Economic Data (FRED)
    - CME Group (for SOFR)
    - NY Fed
    - Bankrate (for mortgage rates)

    Each source includes URL, description, data types, and update frequency.
    """
    service = get_interest_rates_service()
    sources = service.get_mock_data_sources()

    return DataSourcesResponse(sources=sources)


@router.get("/lending-context", response_model=LendingContextResponse)
async def get_lending_context():
    """
    Get real estate lending context.

    Returns typical spreads and indicative rates for commercial real estate loans:
    - Multifamily Permanent (spread over 10Y Treasury)
    - Multifamily Bridge (spread over SOFR)
    - Commercial Permanent (spread over 10Y Treasury)
    - Construction (spread over Prime)

    Indicative rates are calculated from current benchmark rates plus typical spreads.
    Actual rates will vary based on property type, location, sponsor, and market conditions.
    """
    service = get_interest_rates_service()
    context = service.get_lending_context()

    return LendingContextResponse(
        context=context,
        last_updated=datetime.now(UTC),
    )
