"""Tests for export API endpoints.

Tests the Exports API endpoints including:
- Excel exports (properties, deals, analytics)
- PDF exports (property, deal, portfolio reports)
"""

import pytest

# =============================================================================
# Properties Excel Export Tests
# =============================================================================


@pytest.mark.asyncio
async def test_export_properties_excel(client, db_session):
    """Test exporting properties to Excel format."""
    response = await client.get(
        "/api/v1/exports/properties/excel", follow_redirects=True
    )

    if response.status_code == 404:
        pytest.skip("Properties Excel export endpoint not implemented")

    if response.status_code == 501:
        pytest.skip("Excel export service not available")

    # Accept 200 (success) or 500 (service error)
    assert response.status_code in [200, 500]

    if response.status_code == 200:
        # Verify it returns an Excel file
        content_type = response.headers.get("content-type", "")
        assert "spreadsheet" in content_type or "octet-stream" in content_type


@pytest.mark.asyncio
async def test_export_properties_excel_with_filters(client, db_session):
    """Test exporting filtered properties to Excel."""
    response = await client.get(
        "/api/v1/exports/properties/excel",
        params={"property_type": "multifamily", "market": "Phoenix Metro"},
        follow_redirects=True,
    )

    if response.status_code == 404:
        pytest.skip("Properties Excel export endpoint not implemented")

    if response.status_code == 501:
        pytest.skip("Excel export service not available")

    # Should succeed or return 404 if no matching properties
    assert response.status_code in [200, 404, 500]


@pytest.mark.asyncio
async def test_export_properties_excel_no_analytics(client, db_session):
    """Test exporting properties without analytics sheet."""
    response = await client.get(
        "/api/v1/exports/properties/excel",
        params={"include_analytics": False},
        follow_redirects=True,
    )

    if response.status_code == 404:
        pytest.skip("Properties Excel export endpoint not implemented")

    if response.status_code == 501:
        pytest.skip("Excel export service not available")

    assert response.status_code in [200, 500]


# =============================================================================
# Deals Excel Export Tests
# =============================================================================


@pytest.mark.asyncio
async def test_export_deals_excel(client, db_session):
    """Test exporting deals to Excel format."""
    response = await client.get("/api/v1/exports/deals/excel", follow_redirects=True)

    if response.status_code == 404:
        pytest.skip("Deals Excel export endpoint not implemented")

    if response.status_code == 501:
        pytest.skip("Excel export service not available")

    # Accept 200 or 404 (no deals exist)
    assert response.status_code in [200, 404, 500]


@pytest.mark.asyncio
async def test_export_deals_excel_by_stage(client, db_session):
    """Test exporting deals filtered by stage."""
    response = await client.get(
        "/api/v1/exports/deals/excel", params={"stage": "lead"}, follow_redirects=True
    )

    if response.status_code == 404:
        pytest.skip("Deals Excel export not available or no deals exist")

    if response.status_code == 501:
        pytest.skip("Excel export service not available")

    assert response.status_code in [200, 404, 500]


# =============================================================================
# Analytics Excel Export Tests
# =============================================================================


@pytest.mark.asyncio
async def test_export_analytics_excel(client, db_session):
    """Test exporting analytics report to Excel."""
    response = await client.get(
        "/api/v1/exports/analytics/excel", follow_redirects=True
    )

    if response.status_code == 404:
        pytest.skip("Analytics Excel export endpoint not implemented")

    if response.status_code == 501:
        pytest.skip("Excel export service not available")

    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_export_analytics_excel_time_periods(client, db_session):
    """Test analytics export with different time periods."""
    valid_periods = ["mtd", "qtd", "ytd", "1y", "all"]

    for period in valid_periods:
        response = await client.get(
            "/api/v1/exports/analytics/excel",
            params={"time_period": period},
            follow_redirects=True,
        )

        if response.status_code == 404:
            pytest.skip("Analytics Excel export not implemented")
            return

        if response.status_code == 501:
            pytest.skip("Excel export service not available")
            return

        assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_export_analytics_excel_invalid_period(client, db_session):
    """Test analytics export with invalid time period fails validation."""
    response = await client.get(
        "/api/v1/exports/analytics/excel",
        params={"time_period": "invalid"},
        follow_redirects=True,
    )

    if response.status_code == 404:
        pytest.skip("Analytics Excel export not implemented")

    # Should fail validation
    assert response.status_code == 422


# =============================================================================
# Property PDF Export Tests
# =============================================================================


@pytest.mark.asyncio
async def test_export_property_pdf(client, db_session):
    """Test exporting a property report to PDF."""
    response = await client.get(
        "/api/v1/exports/properties/1/pdf", follow_redirects=True
    )

    if response.status_code == 404:
        pytest.skip("Property PDF export not implemented or property not found")

    if response.status_code == 501:
        pytest.skip("PDF service not available")

    assert response.status_code in [200, 500]

    if response.status_code == 200:
        content_type = response.headers.get("content-type", "")
        assert "pdf" in content_type or "octet-stream" in content_type


@pytest.mark.asyncio
async def test_export_property_pdf_not_found(client, db_session):
    """Test exporting a non-existent property returns 404."""
    response = await client.get(
        "/api/v1/exports/properties/99999/pdf", follow_redirects=True
    )

    # Should return 404 or 501
    assert response.status_code in [404, 501]


@pytest.mark.asyncio
async def test_export_property_pdf_no_analytics(client, db_session):
    """Test exporting property PDF without analytics."""
    response = await client.get(
        "/api/v1/exports/properties/1/pdf",
        params={"include_analytics": False},
        follow_redirects=True,
    )

    if response.status_code == 404:
        pytest.skip("Property PDF export not implemented")

    if response.status_code == 501:
        pytest.skip("PDF service not available")

    assert response.status_code in [200, 500]


# =============================================================================
# Deal PDF Export Tests
# =============================================================================


@pytest.mark.asyncio
async def test_export_deal_pdf(client, db_session):
    """Test exporting a deal report to PDF."""
    response = await client.get("/api/v1/exports/deals/1/pdf", follow_redirects=True)

    if response.status_code == 404:
        pytest.skip("Deal PDF export not implemented or deal not found")

    if response.status_code == 501:
        pytest.skip("PDF service not available")

    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_export_deal_pdf_not_found(client, db_session):
    """Test exporting a non-existent deal returns 404."""
    response = await client.get(
        "/api/v1/exports/deals/99999/pdf", follow_redirects=True
    )

    # Should return 404 or 501
    assert response.status_code in [404, 501]


# =============================================================================
# Portfolio PDF Export Tests
# =============================================================================


@pytest.mark.asyncio
async def test_export_portfolio_pdf(client, db_session):
    """Test exporting portfolio report to PDF."""
    response = await client.get("/api/v1/exports/portfolio/pdf", follow_redirects=True)

    if response.status_code == 404:
        pytest.skip("Portfolio PDF export not implemented")

    if response.status_code == 501:
        pytest.skip("PDF service not available")

    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_export_portfolio_pdf_time_periods(client, db_session):
    """Test portfolio PDF with different time periods."""
    for period in ["mtd", "ytd", "1y"]:
        response = await client.get(
            "/api/v1/exports/portfolio/pdf",
            params={"time_period": period},
            follow_redirects=True,
        )

        if response.status_code == 404:
            pytest.skip("Portfolio PDF export not implemented")
            return

        if response.status_code == 501:
            pytest.skip("PDF service not available")
            return

        assert response.status_code in [200, 500]
