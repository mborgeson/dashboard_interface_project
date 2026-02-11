"""Tests for the Tempe BLDS ArcGIS API client."""

from collections.abc import Generator
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.construction import ConstructionPermitData, ConstructionSourceLog
from app.services.construction_api.tempe_blds import (
    fetch_tempe_permits,
    save_tempe_records,
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
# fetch_tempe_permits tests (mocked HTTP)
# =============================================================================

# Epoch ms for 2025-03-15
MARCH_15_EPOCH_MS = int(datetime(2025, 3, 15, tzinfo=UTC).timestamp() * 1000)
APRIL_01_EPOCH_MS = int(datetime(2025, 4, 1, tzinfo=UTC).timestamp() * 1000)

MOCK_TEMPE_RESPONSE = {
    "features": [
        {
            "attributes": {
                "PermitNumber": "BLD-2025-001",
                "IssuedDate": MARCH_15_EPOCH_MS,
                "Address": "900 S Mill Ave",
                "Description": "NEW MULTI-FAMILY COMPLEX",
                "PermitType": "BUILDING",
                "StatusCurrent": "ISSUED",
                "Valuation": 50000000,
            }
        },
        {
            "attributes": {
                "PermitNumber": "BLD-2025-002",
                "IssuedDate": APRIL_01_EPOCH_MS,
                "Address": "1100 E University Dr",
                "Description": "MULTI-FAMILY ADDITION",
                "PermitType": "BUILDING",
                "StatusCurrent": "APPROVED",
                "Valuation": 25000000,
            }
        },
    ]
}


@pytest.mark.asyncio
async def test_fetch_tempe_success():
    """Test successful Tempe ArcGIS fetch."""
    mock_response = httpx.Response(
        200,
        json=MOCK_TEMPE_RESPONSE,
        request=httpx.Request("GET", "https://services1.arcgis.com/Tempe"),
    )

    with patch("app.services.construction_api.tempe_blds.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await fetch_tempe_permits()

    assert len(result["records"]) == 2
    assert result["api_response_code"] == 200
    assert len(result["errors"]) == 0

    rec = result["records"][0]
    assert rec["source"] == "tempe_blds"
    assert rec["series_id"] == "TEMPE-BLD-2025-001"
    assert rec["geography"] == "Tempe, AZ"
    assert isinstance(rec["period_date"], date)
    assert rec["address"] == "900 S Mill Ave"


@pytest.mark.asyncio
async def test_fetch_tempe_empty_features():
    """Test Tempe ArcGIS with no features."""
    mock_response = httpx.Response(
        200,
        json={"features": []},
        request=httpx.Request("GET", "https://services1.arcgis.com/Tempe"),
    )

    with patch("app.services.construction_api.tempe_blds.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await fetch_tempe_permits()

    assert result["records"] == []
    assert len(result["errors"]) == 0


@pytest.mark.asyncio
async def test_fetch_tempe_arcgis_error():
    """Test Tempe ArcGIS with error response."""
    mock_response = httpx.Response(
        200,
        json={"error": {"code": 400, "message": "Invalid query"}},
        request=httpx.Request("GET", "https://services1.arcgis.com/Tempe"),
    )

    with patch("app.services.construction_api.tempe_blds.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await fetch_tempe_permits()

    assert result["records"] == []
    assert len(result["errors"]) > 0


@pytest.mark.asyncio
async def test_fetch_tempe_http_error():
    """Test Tempe ArcGIS with HTTP error."""
    mock_response = httpx.Response(
        503,
        request=httpx.Request("GET", "https://services1.arcgis.com/Tempe"),
    )

    with patch("app.services.construction_api.tempe_blds.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await fetch_tempe_permits()

    assert result["records"] == []
    assert len(result["errors"]) > 0
    assert result["api_response_code"] == 503


@pytest.mark.asyncio
async def test_fetch_tempe_skips_missing_date():
    """Features without IssuedDate are skipped."""
    mock_response = httpx.Response(
        200,
        json={"features": [{"attributes": {"PermitNumber": "X-001", "Address": "123 Main"}}]},
        request=httpx.Request("GET", "https://services1.arcgis.com/Tempe"),
    )

    with patch("app.services.construction_api.tempe_blds.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await fetch_tempe_permits()

    assert result["records"] == []


# =============================================================================
# save_tempe_records tests
# =============================================================================


class TestSaveTempeRecords:
    def test_inserts_new_records(self, sync_db):
        records = [
            {
                "source": "tempe_blds",
                "series_id": "TEMPE-BLD-2025-001",
                "geography": "Tempe, AZ",
                "period_date": date(2025, 3, 15),
                "period_type": "permit",
                "value": 1.0,
                "unit": "permits",
                "structure_type": "multifamily",
            },
        ]
        inserted, updated = save_tempe_records(sync_db, records)
        assert inserted == 1
        assert updated == 0

        log = sync_db.query(ConstructionSourceLog).first()
        assert log is not None
        assert log.source_name == "tempe_blds"
        assert log.records_inserted == 1
        assert log.success is True

    def test_upsert_updates_existing(self, sync_db):
        records = [
            {
                "source": "tempe_blds",
                "series_id": "TEMPE-BLD-2025-001",
                "geography": "Tempe, AZ",
                "period_date": date(2025, 3, 15),
                "period_type": "permit",
                "value": 1.0,
                "unit": "permits",
                "structure_type": "multifamily",
            },
        ]
        save_tempe_records(sync_db, records)

        records[0]["value"] = 2.0
        inserted, updated = save_tempe_records(sync_db, records)
        assert inserted == 0
        assert updated == 1

        permit = sync_db.query(ConstructionPermitData).first()
        assert permit.value == 2.0
