"""
Market overview and trends endpoints — MSA and national economic indicators.

Note: market_data_service is accessed via sys.modules to support test mocking.
Tests patch ``app.api.v1.endpoints.market_data.market_data_service``, so all
sub-modules must resolve the service through the package namespace.
"""

import sys

from fastapi import APIRouter, Query

from app.schemas.market_data import (
    MarketOverviewResponse,
    MarketTrendsResponse,
    SubmarketsResponse,
)

router = APIRouter()


def _svc():
    """Resolve market_data_service through the package namespace for mock support."""
    return sys.modules["app.api.v1.endpoints.market_data"].market_data_service


@router.get("/overview", response_model=MarketOverviewResponse)
async def get_market_overview():
    """
    Get market overview with MSA statistics and economic indicators.

    Returns:
        MSA overview data including population, employment, GDP,
        and key economic indicators for the Phoenix MSA.
    """
    return await _svc().get_market_overview()


@router.get("/usa/overview", response_model=MarketOverviewResponse)
async def get_usa_market_overview():
    """
    Get national (USA) market overview with economic indicators.

    Returns:
        National overview data including population, employment, GDP,
        and key economic indicators using national FRED series
        (UNRATE, PAYEMS, CPIAUCSL, GDP, MORTGAGE30US, FEDFUNDS, HOUST, PERMIT).
    """
    return await _svc().get_usa_market_overview()


@router.get("/usa/trends", response_model=MarketTrendsResponse)
async def get_usa_market_trends(
    period_months: int = Query(
        12, ge=1, le=36, description="Number of months of trend data"
    ),
):
    """
    Get national market trends over time.

    Args:
        period_months: Number of months of historical data (1-36, default 12)

    Returns:
        Monthly national trend data including unemployment rate,
        employment rate, and 30-year mortgage rate.
    """
    return await _svc().get_usa_market_trends(period_months=period_months)


@router.get("/submarkets", response_model=SubmarketsResponse)
async def get_submarkets():
    """
    Get submarket breakdown with performance metrics.

    Returns:
        List of submarkets with rent, occupancy, cap rate,
        inventory, and absorption metrics.
    """
    return await _svc().get_submarkets()


@router.get("/trends", response_model=MarketTrendsResponse)
async def get_market_trends(
    period_months: int = Query(
        12, ge=1, le=36, description="Number of months of trend data"
    ),
):
    """
    Get market trends over time.

    Args:
        period_months: Number of months of historical data (1-36, default 12)

    Returns:
        Monthly trend data including rent growth, occupancy,
        cap rates, and economic metrics.
    """
    return await _svc().get_market_trends(period_months=period_months)
