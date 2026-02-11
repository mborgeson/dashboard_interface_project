"""Tests for the Census BPS API client."""

from collections.abc import Generator
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.construction import ConstructionPermitData, ConstructionSourceLog
from app.services.construction_api.census_bps import (
    CENSUS_BPS_SERIES,
    PHOENIX_MSA_CBSA,
    fetch_census_bps,
    save_census_bps_records,
)

# Sync DB for save tests
sync_engine = create_engine(
    "sqlite:///:memory:",
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
SyncTestSession = sessionmaker(bind=sync_engine, class_=Session, expire_on_commit=False)


@pytest.fixture()
def sync_db() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=sync_engine)
    session = SyncTestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=sync_engine)


# =============================================================================
# fetch_census_bps tests (mocked HTTP)
# =============================================================================


MOCK_CENSUS_RESPONSE = [
    ["BLDG5O_UNITS", "BLDG_UNITS", "BLDG5O_BLDGS", "time", "metropolitan statistical area/micropolitan statistical area"],
    ["1250", "1500", "8", "2025-01", "38060"],
    ["1100", "1400", "7", "2025-02", "38060"],
    ["", "1300", "6", "2025-03", "38060"],  # BLDG5O_UNITS is empty
]


@pytest.mark.asyncio
async def test_fetch_census_bps_success():
    """Test successful Census BPS fetch."""
    mock_response = httpx.Response(
        200,
        json=MOCK_CENSUS_RESPONSE,
        request=httpx.Request("GET", "https://api.census.gov"),
    )

    with patch("app.services.construction_api.census_bps.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await fetch_census_bps("test-api-key")

    assert len(result["records"]) > 0
    assert result["api_response_code"] == 200
    assert len(result["errors"]) == 0

    # Check record structure
    rec = result["records"][0]
    assert rec["source"] == "census_bps"
    assert rec["series_id"] in CENSUS_BPS_SERIES
    assert isinstance(rec["period_date"], date)
    assert rec["period_type"] == "monthly"


@pytest.mark.asyncio
async def test_fetch_census_bps_empty_response():
    """Test Census BPS with empty data."""
    mock_response = httpx.Response(
        200,
        json=[],
        request=httpx.Request("GET", "https://api.census.gov"),
    )

    with patch("app.services.construction_api.census_bps.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await fetch_census_bps("test-api-key")

    assert result["records"] == []
    assert len(result["errors"]) > 0


@pytest.mark.asyncio
async def test_fetch_census_bps_http_error():
    """Test Census BPS with HTTP error."""
    mock_response = httpx.Response(
        503,
        request=httpx.Request("GET", "https://api.census.gov"),
    )

    with patch("app.services.construction_api.census_bps.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await fetch_census_bps("test-api-key")

    assert result["records"] == []
    assert len(result["errors"]) > 0
    assert result["api_response_code"] == 503


# =============================================================================
# save_census_bps_records tests
# =============================================================================


class TestSaveCensusBpsRecords:
    def test_inserts_new_records(self, sync_db):
        records = [
            {
                "source": "census_bps",
                "series_id": "BLDG5O_UNITS",
                "geography": "MSA:38060",
                "period_date": date(2025, 1, 1),
                "period_type": "monthly",
                "value": 1250.0,
                "unit": "units",
                "structure_type": "5+ units",
            },
            {
                "source": "census_bps",
                "series_id": "BLDG5O_UNITS",
                "geography": "MSA:38060",
                "period_date": date(2025, 2, 1),
                "period_type": "monthly",
                "value": 1100.0,
                "unit": "units",
                "structure_type": "5+ units",
            },
        ]
        inserted, updated = save_census_bps_records(sync_db, records)
        assert inserted == 2
        assert updated == 0

        # Verify source log
        log = sync_db.query(ConstructionSourceLog).first()
        assert log is not None
        assert log.source_name == "census_bps"
        assert log.records_inserted == 2
        assert log.success is True

    def test_upsert_updates_existing(self, sync_db):
        records = [
            {
                "source": "census_bps",
                "series_id": "BLDG5O_UNITS",
                "geography": "MSA:38060",
                "period_date": date(2025, 1, 1),
                "period_type": "monthly",
                "value": 1250.0,
                "unit": "units",
                "structure_type": "5+ units",
            },
        ]
        save_census_bps_records(sync_db, records)

        # Update same record
        records[0]["value"] = 1300.0
        inserted, updated = save_census_bps_records(sync_db, records)
        assert inserted == 0
        assert updated == 1

        permit = sync_db.query(ConstructionPermitData).first()
        assert permit.value == 1300.0
