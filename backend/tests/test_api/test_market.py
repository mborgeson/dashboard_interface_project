"""Tests for market data API endpoints.

F-037: Tests the Market Data API at /api/v1/market/ including:
- Get market overview (GET /overview)
- Get submarkets (GET /submarkets)
- Get market trends (GET /trends)
- Get comparables (GET /comparables)
- Get USA overview (GET /usa/overview)
- Get USA trends (GET /usa/trends)
- Auth guards (401 without auth)
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.market_data import (
    ComparablesResponse,
    EconomicIndicator,
    MarketOverviewResponse,
    MarketTrend,
    MarketTrendsResponse,
    MonthlyMarketData,
    MSAOverview,
    SubmarketMetrics,
    SubmarketsResponse,
)

# =============================================================================
# Mock response builders
# =============================================================================


def _mock_overview() -> MarketOverviewResponse:
    return MarketOverviewResponse(
        msa_overview=MSAOverview(
            population=4_946_000,
            employment=2_500_000,
            gdp=280_000_000_000.0,
            population_growth=1.8,
            employment_growth=2.1,
            gdp_growth=3.1,
            last_updated="2026-03-01",
        ),
        economic_indicators=[
            EconomicIndicator(
                indicator="Unemployment Rate",
                value=3.8,
                yoy_change=-0.2,
                unit="%",
            ),
        ],
        last_updated=datetime.now(UTC),
        source="mock",
    )


def _mock_submarkets() -> SubmarketsResponse:
    return SubmarketsResponse(
        submarkets=[
            SubmarketMetrics(
                name="North Scottsdale",
                avg_rent=1850.0,
                rent_growth=3.2,
                occupancy=95.2,
                cap_rate=5.5,
                inventory=12000,
                absorption=200,
            ),
        ],
        total_inventory=12000,
        total_absorption=200,
        average_occupancy=95.2,
        average_rent_growth=3.2,
        last_updated=datetime.now(UTC),
        source="mock",
    )


def _mock_trends() -> MarketTrendsResponse:
    return MarketTrendsResponse(
        trends=[
            MarketTrend(
                month="Jan",
                rent_growth=3.2,
                occupancy=94.5,
                cap_rate=5.6,
            ),
        ],
        monthly_data=[
            MonthlyMarketData(
                month="Jan",
                rent_growth=3.2,
                occupancy=94.5,
                cap_rate=5.6,
                employment=2_500_000,
                population=4_946_000,
            ),
        ],
        period="12M",
        last_updated=datetime.now(UTC),
        source="mock",
    )


def _mock_comparables() -> ComparablesResponse:
    return ComparablesResponse(
        comparables=[],
        total=0,
        radius_miles=5.0,
        last_updated=datetime.now(UTC),
        source="mock",
    )


# =============================================================================
# Auth Guard Tests
# =============================================================================


@pytest.mark.asyncio
async def test_market_overview_requires_auth(client, db_session):
    """GET /market/overview without auth returns 401."""
    response = await client.get("/api/v1/market/overview", follow_redirects=True)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_submarkets_requires_auth(client, db_session):
    """GET /market/submarkets without auth returns 401."""
    response = await client.get("/api/v1/market/submarkets", follow_redirects=True)
    assert response.status_code == 401


# =============================================================================
# GET /overview
# =============================================================================


@pytest.mark.asyncio
async def test_get_market_overview(client, db_session, auth_headers):
    """GET /market/overview returns market overview data."""
    with patch("app.api.v1.endpoints.market_data.market_data_service") as mock_svc:
        mock_svc.get_market_overview = AsyncMock(return_value=_mock_overview())

        response = await client.get(
            "/api/v1/market/overview",
            headers=auth_headers,
            follow_redirects=True,
        )
    assert response.status_code == 200
    data = response.json()
    assert "msa_overview" in data
    assert "economic_indicators" in data


# =============================================================================
# GET /usa/overview
# =============================================================================


@pytest.mark.asyncio
async def test_get_usa_overview(client, db_session, auth_headers):
    """GET /market/usa/overview returns national overview data."""
    with patch("app.api.v1.endpoints.market_data.market_data_service") as mock_svc:
        mock_svc.get_usa_market_overview = AsyncMock(return_value=_mock_overview())

        response = await client.get(
            "/api/v1/market/usa/overview",
            headers=auth_headers,
            follow_redirects=True,
        )
    assert response.status_code == 200
    data = response.json()
    assert "msa_overview" in data


# =============================================================================
# GET /submarkets
# =============================================================================


@pytest.mark.asyncio
async def test_get_submarkets(client, db_session, auth_headers):
    """GET /market/submarkets returns submarket list."""
    with patch("app.api.v1.endpoints.market_data.market_data_service") as mock_svc:
        mock_svc.get_submarkets = AsyncMock(return_value=_mock_submarkets())

        response = await client.get(
            "/api/v1/market/submarkets",
            headers=auth_headers,
            follow_redirects=True,
        )
    assert response.status_code == 200
    data = response.json()
    assert "submarkets" in data
    assert "total_inventory" in data
    assert "average_occupancy" in data


# =============================================================================
# GET /trends
# =============================================================================


@pytest.mark.asyncio
async def test_get_market_trends(client, db_session, auth_headers):
    """GET /market/trends returns trend data."""
    with patch("app.api.v1.endpoints.market_data.market_data_service") as mock_svc:
        mock_svc.get_market_trends = AsyncMock(return_value=_mock_trends())

        response = await client.get(
            "/api/v1/market/trends",
            headers=auth_headers,
            follow_redirects=True,
        )
    assert response.status_code == 200
    data = response.json()
    assert "trends" in data
    assert "monthly_data" in data
    assert "period" in data


@pytest.mark.asyncio
async def test_get_market_trends_custom_period(client, db_session, auth_headers):
    """GET /market/trends?period_months=6 respects the period parameter."""
    with patch("app.api.v1.endpoints.market_data.market_data_service") as mock_svc:
        mock_svc.get_market_trends = AsyncMock(return_value=_mock_trends())

        response = await client.get(
            "/api/v1/market/trends",
            params={"period_months": 6},
            headers=auth_headers,
            follow_redirects=True,
        )
    assert response.status_code == 200
    mock_svc.get_market_trends.assert_called_once_with(period_months=6)


# =============================================================================
# GET /usa/trends
# =============================================================================


@pytest.mark.asyncio
async def test_get_usa_trends(client, db_session, auth_headers):
    """GET /market/usa/trends returns national trend data."""
    with patch("app.api.v1.endpoints.market_data.market_data_service") as mock_svc:
        mock_svc.get_usa_market_trends = AsyncMock(return_value=_mock_trends())

        response = await client.get(
            "/api/v1/market/usa/trends",
            headers=auth_headers,
            follow_redirects=True,
        )
    assert response.status_code == 200
    data = response.json()
    assert "trends" in data


# =============================================================================
# GET /comparables
# =============================================================================


@pytest.mark.asyncio
async def test_get_comparables(client, db_session, auth_headers):
    """GET /market/comparables returns comparable properties."""
    with patch("app.api.v1.endpoints.market_data.market_data_service") as mock_svc:
        mock_svc.get_comparables = AsyncMock(return_value=_mock_comparables())

        response = await client.get(
            "/api/v1/market/comparables",
            headers=auth_headers,
            follow_redirects=True,
        )
    assert response.status_code == 200
    data = response.json()
    assert "comparables" in data
    assert "total" in data
    assert "radius_miles" in data
