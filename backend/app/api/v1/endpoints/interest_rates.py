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
async def get_current_rates(
    force_refresh: bool = Query(
        False, description="When true, fetch live rates from FRED API first"
    ),
):
    """
    Get current key interest rates.

    Returns Federal Funds rate, Treasury yields (2Y, 5Y, 7Y, 10Y),
    SOFR rates, and mortgage rates with change from previous values.

    Rates are cached for 5 minutes and sourced from database or FRED API.
    When force_refresh=true, the FRED API is queried first and results
    are written back to the database.
    """
    service = get_interest_rates_service()
    data = await service.get_key_rates(force_refresh=force_refresh)

    last_updated_str = data.get("last_updated", datetime.now(UTC).isoformat())
    if isinstance(last_updated_str, str):
        try:
            last_updated = datetime.fromisoformat(last_updated_str)
        except ValueError:
            last_updated = datetime.now(UTC)
    else:
        last_updated = last_updated_str

    return KeyRatesResponse(
        key_rates=data["key_rates"],
        last_updated=last_updated,
        source=data.get("source", "unavailable"),
    )


@router.get("/yield-curve", response_model=YieldCurveResponse)
async def get_yield_curve(
    force_refresh: bool = Query(
        False, description="When true, fetch live data from FRED API first"
    ),
):
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
    data = await service.get_yield_curve(force_refresh=force_refresh)

    last_updated_str = data.get("last_updated", datetime.now(UTC).isoformat())
    if isinstance(last_updated_str, str):
        try:
            last_updated = datetime.fromisoformat(last_updated_str)
        except ValueError:
            last_updated = datetime.now(UTC)
    else:
        last_updated = last_updated_str

    return YieldCurveResponse(
        yield_curve=data["yield_curve"],
        as_of_date=data["as_of_date"],
        last_updated=last_updated,
        source=data.get("source", "unavailable"),
    )


@router.get("/historical", response_model=HistoricalRatesResponse)
async def get_historical_rates(
    months: int = Query(
        12, ge=1, le=60, description="Number of months of historical data"
    ),
    force_refresh: bool = Query(
        False, description="When true, fetch live data from FRED API first"
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
        force_refresh: When true, fetch from FRED API first
    """
    service = get_interest_rates_service()
    data = await service.get_historical_rates(months, force_refresh=force_refresh)

    last_updated_str = data.get("last_updated", datetime.now(UTC).isoformat())
    if isinstance(last_updated_str, str):
        try:
            last_updated = datetime.fromisoformat(last_updated_str)
        except ValueError:
            last_updated = datetime.now(UTC)
    else:
        last_updated = last_updated_str

    return HistoricalRatesResponse(
        rates=data["rates"],
        start_date=data["start_date"],
        end_date=data["end_date"],
        last_updated=last_updated,
        source=data.get("source", "unavailable"),
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

    last_updated_str = data.get("last_updated", datetime.now(UTC).isoformat())
    if isinstance(last_updated_str, str):
        try:
            last_updated = datetime.fromisoformat(last_updated_str)
        except ValueError:
            last_updated = datetime.now(UTC)
    else:
        last_updated = last_updated_str

    return RateSpreadsResponse(
        spreads=data["spreads"],
        last_updated=last_updated,
        source=data.get("source", "unavailable"),
    )


@router.get("/data-sources", response_model=DataSourcesResponse)
async def get_data_sources():
    """
    Get list of interest rate data sources.

    Returns information about authoritative sources for rate data:
    - Federal Reserve Economic Data (FRED)
    - U.S. Treasury Department
    - CME Group (for SOFR)
    - NY Fed

    Each source includes URL, description, data types, and update frequency.
    """
    sources = [
        {
            "id": "fred",
            "name": "Federal Reserve Economic Data (FRED)",
            "url": "https://fred.stlouisfed.org/",
            "description": "Comprehensive economic database by Federal Reserve Bank of St. Louis.",
            "data_types": [
                "Federal Funds Rate",
                "Treasury Yields",
                "SOFR",
                "Economic Indicators",
            ],
            "update_frequency": "Daily",
        },
        {
            "id": "treasury-gov",
            "name": "U.S. Treasury Department",
            "url": "https://home.treasury.gov/",
            "description": "Official source for Treasury yield curve data.",
            "data_types": ["Treasury Yields", "Yield Curve", "Auction Results"],
            "update_frequency": "Daily",
        },
        {
            "id": "cme-sofr",
            "name": "CME Group - SOFR",
            "url": "https://www.cmegroup.com/markets/interest-rates/stirs/sofr.html",
            "description": "Official source for Term SOFR rates.",
            "data_types": ["Term SOFR", "SOFR Futures"],
            "update_frequency": "Real-time",
        },
        {
            "id": "ny-fed",
            "name": "Federal Reserve Bank of New York",
            "url": "https://www.newyorkfed.org/markets/reference-rates/sofr",
            "description": "Official administrator of SOFR.",
            "data_types": ["SOFR", "EFFR", "OBFR"],
            "update_frequency": "Daily",
        },
    ]

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
    context = await service.get_lending_context()

    return LendingContextResponse(
        context=context,
        last_updated=datetime.now(UTC),
    )
