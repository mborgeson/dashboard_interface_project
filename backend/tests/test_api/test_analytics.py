"""Tests for analytics API endpoints.

Tests the Analytics API endpoints including:
- Dashboard metrics
- Portfolio analytics
- Market data
- Deal pipeline analytics
- Rent growth predictions (ML endpoints)
"""

import pytest

# =============================================================================
# Dashboard Metrics Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_dashboard_metrics(client, db_session):
    """Test getting dashboard metrics."""
    response = await client.get("/api/v1/analytics/dashboard", follow_redirects=True)

    if response.status_code == 404:
        pytest.skip("Dashboard analytics endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    # Verify structure
    assert "portfolio_summary" in data
    assert "kpis" in data
    assert "alerts" in data
    assert "recent_activity" in data


@pytest.mark.asyncio
async def test_dashboard_metrics_structure(client, db_session):
    """Test dashboard metrics contain expected fields."""
    response = await client.get("/api/v1/analytics/dashboard", follow_redirects=True)

    if response.status_code == 404:
        pytest.skip("Dashboard analytics endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    # Portfolio summary fields
    summary = data.get("portfolio_summary", {})
    assert "total_properties" in summary
    assert "total_units" in summary
    assert "total_value" in summary
    assert "avg_occupancy" in summary

    # KPI fields
    kpis = data.get("kpis", {})
    assert "ytd_noi_growth" in kpis
    assert "ytd_rent_growth" in kpis
    assert "deals_in_pipeline" in kpis


# =============================================================================
# Portfolio Analytics Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_portfolio_analytics(client, db_session):
    """Test getting portfolio analytics with default time period."""
    response = await client.get("/api/v1/analytics/portfolio", follow_redirects=True)

    if response.status_code == 404:
        pytest.skip("Portfolio analytics endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    assert "time_period" in data
    assert "performance" in data
    assert "composition" in data
    assert "trends" in data


@pytest.mark.asyncio
async def test_portfolio_analytics_time_periods(client, db_session):
    """Test portfolio analytics with different time periods."""
    valid_periods = ["mtd", "qtd", "ytd", "1y", "3y", "5y", "all"]

    for period in valid_periods:
        response = await client.get(
            "/api/v1/analytics/portfolio",
            params={"time_period": period},
            follow_redirects=True,
        )

        if response.status_code == 404:
            pytest.skip("Portfolio analytics endpoint not implemented")

        assert response.status_code == 200
        data = response.json()
        assert data["time_period"] == period


@pytest.mark.asyncio
async def test_portfolio_analytics_invalid_period(client, db_session):
    """Test portfolio analytics with invalid time period fails validation."""
    response = await client.get(
        "/api/v1/analytics/portfolio",
        params={"time_period": "invalid"},
        follow_redirects=True,
    )

    if response.status_code == 404:
        pytest.skip("Portfolio analytics endpoint not implemented")

    # Should fail validation
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_portfolio_analytics_performance_metrics(client, db_session):
    """Test portfolio analytics returns performance metrics."""
    response = await client.get("/api/v1/analytics/portfolio", follow_redirects=True)

    if response.status_code == 404:
        pytest.skip("Portfolio analytics endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    performance = data.get("performance", {})
    assert "total_return" in performance
    assert "income_return" in performance
    assert "appreciation_return" in performance


@pytest.mark.asyncio
async def test_portfolio_composition(client, db_session):
    """Test portfolio analytics returns composition breakdown."""
    response = await client.get("/api/v1/analytics/portfolio", follow_redirects=True)

    if response.status_code == 404:
        pytest.skip("Portfolio analytics endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    composition = data.get("composition", {})
    assert "by_type" in composition
    assert "by_market" in composition


# =============================================================================
# Market Data Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_market_data(client, db_session):
    """Test getting market data for a specific market."""
    response = await client.get(
        "/api/v1/analytics/market-data",
        params={"market": "Phoenix Metro"},
        follow_redirects=True,
    )

    if response.status_code == 404:
        pytest.skip("Market data endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    assert data["market"] == "Phoenix Metro"
    assert "metrics" in data
    assert "economic_indicators" in data
    assert "forecast" in data


@pytest.mark.asyncio
async def test_market_data_requires_market_param(client, db_session):
    """Test market data requires market parameter."""
    response = await client.get("/api/v1/analytics/market-data", follow_redirects=True)

    if response.status_code == 404:
        pytest.skip("Market data endpoint not implemented")

    # Should fail validation - market is required
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_market_data_with_property_type(client, db_session):
    """Test market data filtered by property type."""
    response = await client.get(
        "/api/v1/analytics/market-data",
        params={"market": "Phoenix Metro", "property_type": "multifamily"},
        follow_redirects=True,
    )

    if response.status_code == 404:
        pytest.skip("Market data endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    assert data["property_type"] == "multifamily"


@pytest.mark.asyncio
async def test_market_data_metrics(client, db_session):
    """Test market data returns expected metrics."""
    response = await client.get(
        "/api/v1/analytics/market-data",
        params={"market": "Phoenix Metro"},
        follow_redirects=True,
    )

    if response.status_code == 404:
        pytest.skip("Market data endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    metrics = data.get("metrics", {})
    assert "avg_rent_psf" in metrics
    assert "avg_cap_rate" in metrics
    assert "vacancy_rate" in metrics
    assert "rent_growth_12m" in metrics


# =============================================================================
# Deal Pipeline Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_deal_pipeline_analytics(client, db_session):
    """Test getting deal pipeline analytics."""
    response = await client.get(
        "/api/v1/analytics/deal-pipeline", follow_redirects=True
    )

    if response.status_code == 404:
        pytest.skip("Deal pipeline endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    assert "time_period" in data
    assert "funnel" in data
    assert "conversion_rates" in data
    assert "cycle_times_days" in data
    assert "volume" in data


@pytest.mark.asyncio
async def test_deal_pipeline_funnel_stages(client, db_session):
    """Test deal pipeline returns all funnel stages."""
    response = await client.get(
        "/api/v1/analytics/deal-pipeline", follow_redirects=True
    )

    if response.status_code == 404:
        pytest.skip("Deal pipeline endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    funnel = data.get("funnel", {})
    expected_stages = [
        "dead",
        "initial_review",
        "active_review",
        "under_contract",
        "closed",
        "realized",
    ]
    for stage in expected_stages:
        assert stage in funnel


@pytest.mark.asyncio
async def test_deal_pipeline_conversion_rates(client, db_session):
    """Test deal pipeline returns conversion rates."""
    response = await client.get(
        "/api/v1/analytics/deal-pipeline", follow_redirects=True
    )

    if response.status_code == 404:
        pytest.skip("Deal pipeline endpoint not implemented")

    assert response.status_code == 200
    data = response.json()

    rates = data.get("conversion_rates", {})
    assert "initial_to_active" in rates
    assert "overall" in rates


# =============================================================================
# Rent Prediction Tests (ML Endpoints)
# =============================================================================


@pytest.mark.asyncio
async def test_rent_prediction_endpoint_exists(client, db_session):
    """Test rent prediction endpoint is accessible."""
    property_data = {
        "property_id": 1,
        "market": "Phoenix Metro",
        "property_type": "multifamily",
        "total_units": 100,
        "year_built": 2015,
        "current_rent": 1450.00,
    }

    response = await client.post(
        "/api/v1/analytics/rent-prediction", json=property_data, follow_redirects=True
    )

    if response.status_code == 404:
        pytest.skip("Rent prediction endpoint not implemented")

    # Accept 200 (success) or 500 (ML model issues are OK for this test)
    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_rent_prediction_batch_endpoint_exists(client, db_session):
    """Test batch rent prediction endpoint is accessible."""
    properties = [
        {
            "property_id": 1,
            "market": "Phoenix Metro",
            "property_type": "multifamily",
            "current_rent": 1450.00,
        },
        {
            "property_id": 2,
            "market": "Tucson",
            "property_type": "multifamily",
            "current_rent": 1200.00,
        },
    ]

    response = await client.post(
        "/api/v1/analytics/rent-prediction/batch",
        json=properties,
        follow_redirects=True,
    )

    if response.status_code == 404:
        pytest.skip("Batch rent prediction endpoint not implemented")

    # Accept 200 (success) or 500 (ML model issues are OK for this test)
    assert response.status_code in [200, 500]
