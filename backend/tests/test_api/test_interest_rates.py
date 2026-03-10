"""Tests for interest rate API endpoints.

F-036: Tests the Interest Rates API at /api/v1/interest-rates/ including:
- Get current rates (GET /current)
- Get yield curve (GET /yield-curve)
- Get historical rates (GET /historical)
- Get rate spreads (GET /spreads)
- Get data sources (GET /data-sources)
- Get lending context (GET /lending-context)
- Auth guards (401 without auth)
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

# =============================================================================
# Mock data matching the Pydantic response schemas exactly
# =============================================================================

_NOW = datetime.now(UTC).isoformat()

MOCK_KEY_RATES = {
    "key_rates": [
        {
            "id": "fed_funds",
            "name": "Federal Funds Rate",
            "short_name": "Fed Funds",
            "current_value": 5.33,
            "previous_value": 5.33,
            "change": 0.0,
            "change_percent": 0.0,
            "as_of_date": "2026-03-01",
            "category": "federal",
            "description": "Federal Funds target rate",
        },
    ],
    "last_updated": _NOW,
    "source": "mock",
}

MOCK_YIELD_CURVE = {
    "yield_curve": [
        {
            "maturity": "1M",
            "yield": 5.3,
            "previous_yield": 5.25,
            "maturity_months": 1,
        },
        {
            "maturity": "10Y",
            "yield": 4.25,
            "previous_yield": 4.30,
            "maturity_months": 120,
        },
    ],
    "as_of_date": "2026-03-01",
    "last_updated": _NOW,
    "source": "mock",
}

MOCK_HISTORICAL = {
    "rates": [
        {
            "date": "2026-01",
            "federal_funds": 5.33,
            "treasury_2y": 4.10,
            "treasury_5y": 4.00,
            "treasury_10y": 4.25,
            "treasury_30y": 4.50,
            "sofr": 5.30,
            "mortgage_30y": 6.65,
        },
    ],
    "start_date": "2025-03",
    "end_date": "2026-03",
    "last_updated": _NOW,
    "source": "mock",
}

MOCK_SPREADS = {
    "spreads": {
        "treasury_spread_2s10s": [
            {"date": "2026-03-01", "spread": -0.15},
        ],
        "mortgage_spread": [
            {"date": "2026-03-01", "spread": 2.40},
        ],
        "fed_funds_vs_treasury": [
            {"date": "2026-03-01", "fed_funds": 5.33, "treasury_10y": 4.25, "spread": 1.08},
        ],
    },
    "last_updated": _NOW,
    "source": "mock",
}

MOCK_LENDING_CONTEXT = {
    "typical_spreads": {
        "multifamily_permanent": {
            "name": "Multifamily Permanent",
            "spread": 1.75,
            "benchmark": "10Y Treasury",
        },
    },
    "current_indicative_rates": {
        "multifamily_permanent": 6.00,
    },
}


# =============================================================================
# Auth Guard Tests
# =============================================================================


@pytest.mark.asyncio
async def test_current_rates_requires_auth(client, db_session):
    """GET /interest-rates/current without auth returns 401."""
    response = await client.get(
        "/api/v1/interest-rates/current", follow_redirects=True
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_historical_rates_requires_auth(client, db_session):
    """GET /interest-rates/historical without auth returns 401."""
    response = await client.get(
        "/api/v1/interest-rates/historical", follow_redirects=True
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_yield_curve_requires_auth(client, db_session):
    """GET /interest-rates/yield-curve without auth returns 401."""
    response = await client.get(
        "/api/v1/interest-rates/yield-curve", follow_redirects=True
    )
    assert response.status_code == 401


# =============================================================================
# GET /current
# =============================================================================


@pytest.mark.asyncio
async def test_get_current_rates(client, db_session, auth_headers):
    """GET /interest-rates/current returns key rates."""
    with patch(
        "app.api.v1.endpoints.interest_rates.get_interest_rates_service"
    ) as mock_svc:
        mock_instance = AsyncMock()
        mock_instance.get_key_rates.return_value = MOCK_KEY_RATES
        mock_svc.return_value = mock_instance

        response = await client.get(
            "/api/v1/interest-rates/current",
            headers=auth_headers,
            follow_redirects=True,
        )
    assert response.status_code == 200
    data = response.json()
    assert "key_rates" in data
    assert "last_updated" in data
    assert "source" in data
    assert len(data["key_rates"]) >= 1


# =============================================================================
# GET /yield-curve
# =============================================================================


@pytest.mark.asyncio
async def test_get_yield_curve(client, db_session, auth_headers):
    """GET /interest-rates/yield-curve returns yield curve data."""
    with patch(
        "app.api.v1.endpoints.interest_rates.get_interest_rates_service"
    ) as mock_svc:
        mock_instance = AsyncMock()
        mock_instance.get_yield_curve.return_value = MOCK_YIELD_CURVE
        mock_svc.return_value = mock_instance

        response = await client.get(
            "/api/v1/interest-rates/yield-curve",
            headers=auth_headers,
            follow_redirects=True,
        )
    assert response.status_code == 200
    data = response.json()
    assert "yield_curve" in data
    assert "as_of_date" in data


# =============================================================================
# GET /historical
# =============================================================================


@pytest.mark.asyncio
async def test_get_historical_rates(client, db_session, auth_headers):
    """GET /interest-rates/historical returns historical data."""
    with patch(
        "app.api.v1.endpoints.interest_rates.get_interest_rates_service"
    ) as mock_svc:
        mock_instance = AsyncMock()
        mock_instance.get_historical_rates.return_value = MOCK_HISTORICAL
        mock_svc.return_value = mock_instance

        response = await client.get(
            "/api/v1/interest-rates/historical",
            headers=auth_headers,
            follow_redirects=True,
        )
    assert response.status_code == 200
    data = response.json()
    assert "rates" in data
    assert "start_date" in data
    assert "end_date" in data


@pytest.mark.asyncio
async def test_get_historical_rates_custom_months(client, db_session, auth_headers):
    """GET /interest-rates/historical?months=6 passes month param."""
    with patch(
        "app.api.v1.endpoints.interest_rates.get_interest_rates_service"
    ) as mock_svc:
        mock_instance = AsyncMock()
        mock_instance.get_historical_rates.return_value = MOCK_HISTORICAL
        mock_svc.return_value = mock_instance

        response = await client.get(
            "/api/v1/interest-rates/historical",
            params={"months": 6},
            headers=auth_headers,
            follow_redirects=True,
        )
    assert response.status_code == 200
    mock_instance.get_historical_rates.assert_called_once_with(6, force_refresh=False)


# =============================================================================
# GET /spreads
# =============================================================================


@pytest.mark.asyncio
async def test_get_rate_spreads(client, db_session, auth_headers):
    """GET /interest-rates/spreads returns spread data."""
    with patch(
        "app.api.v1.endpoints.interest_rates.get_interest_rates_service"
    ) as mock_svc:
        mock_instance = AsyncMock()
        mock_instance.get_rate_spreads.return_value = MOCK_SPREADS
        mock_svc.return_value = mock_instance

        response = await client.get(
            "/api/v1/interest-rates/spreads",
            headers=auth_headers,
            follow_redirects=True,
        )
    assert response.status_code == 200
    data = response.json()
    assert "spreads" in data


# =============================================================================
# GET /data-sources
# =============================================================================


@pytest.mark.asyncio
async def test_get_data_sources(client, db_session, auth_headers):
    """GET /interest-rates/data-sources returns list of sources."""
    response = await client.get(
        "/api/v1/interest-rates/data-sources",
        headers=auth_headers,
        follow_redirects=True,
    )
    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    assert len(data["sources"]) >= 1
    # Each source should have expected fields
    source = data["sources"][0]
    assert "id" in source
    assert "name" in source
    assert "url" in source


# =============================================================================
# GET /lending-context
# =============================================================================


@pytest.mark.asyncio
async def test_get_lending_context(client, db_session, auth_headers):
    """GET /interest-rates/lending-context returns lending context data."""
    with patch(
        "app.api.v1.endpoints.interest_rates.get_interest_rates_service"
    ) as mock_svc:
        mock_instance = AsyncMock()
        mock_instance.get_lending_context.return_value = MOCK_LENDING_CONTEXT
        mock_svc.return_value = mock_instance

        response = await client.get(
            "/api/v1/interest-rates/lending-context",
            headers=auth_headers,
            follow_redirects=True,
        )
    assert response.status_code == 200
    data = response.json()
    assert "context" in data
    assert "last_updated" in data
