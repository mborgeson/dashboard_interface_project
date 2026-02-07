"""Tests for reporting settings GET/PUT endpoints."""

import pytest
from sqlalchemy import text


@pytest.fixture
async def seed_report_settings(db_session):
    """Seed the report_settings singleton row."""
    await db_session.execute(
        text(
            "INSERT INTO report_settings (id, company_name, primary_color, "
            "secondary_color, default_font, default_page_size, default_orientation, "
            "include_page_numbers, include_table_of_contents, include_timestamp, "
            "footer_text, header_text, created_at, updated_at) "
            "VALUES (1, 'B&R Capital', '#1e40af', '#059669', 'Inter', 'letter', "
            "'portrait', 1, 1, 1, 'Confidential - For Internal Use Only', "
            "'B&R Capital Real Estate Analytics', "
            "datetime('now'), datetime('now'))"
        )
    )
    await db_session.commit()


# =============================================================================
# GET /api/v1/reporting/settings
# =============================================================================


@pytest.mark.asyncio
async def test_get_report_settings_defaults(client, db_session, seed_report_settings):
    """GET /settings returns the seeded defaults."""
    response = await client.get("/api/v1/reporting/settings")
    assert response.status_code == 200

    data = response.json()
    assert data["company_name"] == "B&R Capital"
    assert data["primary_color"] == "#1e40af"
    assert data["secondary_color"] == "#059669"
    assert data["default_font"] == "Inter"
    assert data["default_page_size"] == "letter"
    assert data["default_orientation"] == "portrait"
    assert data["include_page_numbers"] is True
    assert data["include_table_of_contents"] is True
    assert data["include_timestamp"] is True
    assert data["footer_text"] == "Confidential - For Internal Use Only"
    assert data["header_text"] == "B&R Capital Real Estate Analytics"
    assert data["watermark_text"] is None


@pytest.mark.asyncio
async def test_get_report_settings_404_when_missing(client, db_session):
    """GET /settings returns 404 when no row exists."""
    response = await client.get("/api/v1/reporting/settings")
    assert response.status_code == 404


# =============================================================================
# PUT /api/v1/reporting/settings
# =============================================================================


@pytest.mark.asyncio
async def test_put_report_settings_partial_update(client, db_session, seed_report_settings):
    """PUT /settings with partial data updates only provided fields."""
    response = await client.put(
        "/api/v1/reporting/settings",
        json={
            "company_name": "Acme Corp",
            "primary_color": "#ff0000",
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["company_name"] == "Acme Corp"
    assert data["primary_color"] == "#ff0000"
    # Unchanged fields remain at defaults
    assert data["secondary_color"] == "#059669"
    assert data["default_font"] == "Inter"


@pytest.mark.asyncio
async def test_put_report_settings_invalid_page_size(client, db_session, seed_report_settings):
    """PUT /settings with invalid page_size returns 422."""
    response = await client.put(
        "/api/v1/reporting/settings",
        json={"default_page_size": "tabloid"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_put_report_settings_invalid_orientation(client, db_session, seed_report_settings):
    """PUT /settings with invalid orientation returns 422."""
    response = await client.put(
        "/api/v1/reporting/settings",
        json={"default_orientation": "diagonal"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_put_report_settings_watermark(client, db_session, seed_report_settings):
    """PUT /settings can set and clear watermark_text."""
    # Set watermark
    response = await client.put(
        "/api/v1/reporting/settings",
        json={"watermark_text": "DRAFT"},
    )
    assert response.status_code == 200
    assert response.json()["watermark_text"] == "DRAFT"

    # Clear watermark
    response = await client.put(
        "/api/v1/reporting/settings",
        json={"watermark_text": None},
    )
    assert response.status_code == 200
    assert response.json()["watermark_text"] is None
