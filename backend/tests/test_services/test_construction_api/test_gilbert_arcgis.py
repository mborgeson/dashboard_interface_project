"""Tests for the Gilbert ArcGIS API client."""

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
from app.services.construction_api.gilbert_arcgis import (
    fetch_gilbert_permits,
    save_gilbert_records,
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
# fetch_gilbert_permits tests (mocked HTTP)
# =============================================================================

MARCH_20_EPOCH_MS = int(datetime(2025, 3, 20, tzinfo=UTC).timestamp() * 1000)
MAY_10_EPOCH_MS = int(datetime(2025, 5, 10, tzinfo=UTC).timestamp() * 1000)

MOCK_GILBERT_RESPONSE = {
    "features": [
        {
            "attributes": {
                "PermitNum": "BP-2025-001",
                "IssueDate": MARCH_20_EPOCH_MS,
                "Address": "2500 S Val Vista Dr",
                "Description": "NEW MULTI-FAMILY RESIDENTIAL",
                "PermitType": "BUILDING",
                "Status": "ISSUED",
                "Valuation": 35000000,
            }
        },
        {
            "attributes": {
                "PermitNum": "BP-2025-002",
                "IssueDate": MAY_10_EPOCH_MS,
                "Address": "3100 E Pecos Rd",
                "Description": "MULTI-FAMILY COMPLEX",
                "PermitType": "BUILDING",
                "Status": "APPROVED",
                "Valuation": 42000000,
            }
        },
    ]
}


@pytest.mark.asyncio
async def test_fetch_gilbert_success():
    """Test successful Gilbert ArcGIS fetch."""
    mock_response = httpx.Response(
        200,
        json=MOCK_GILBERT_RESPONSE,
        request=httpx.Request("GET", "https://services1.arcgis.com/Gilbert"),
    )

    with patch("app.services.construction_api.gilbert_arcgis.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await fetch_gilbert_permits()

    assert len(result["records"]) == 2
    assert result["api_response_code"] == 200
    assert len(result["errors"]) == 0

    rec = result["records"][0]
    assert rec["source"] == "gilbert_arcgis"
    assert rec["series_id"] == "GILBERT-BP-2025-001"
    assert rec["geography"] == "Gilbert, AZ"
    assert isinstance(rec["period_date"], date)
    assert rec["address"] == "2500 S Val Vista Dr"


@pytest.mark.asyncio
async def test_fetch_gilbert_empty_features():
    """Test Gilbert ArcGIS with no features."""
    mock_response = httpx.Response(
        200,
        json={"features": []},
        request=httpx.Request("GET", "https://services1.arcgis.com/Gilbert"),
    )

    with patch("app.services.construction_api.gilbert_arcgis.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await fetch_gilbert_permits()

    assert result["records"] == []
    assert len(result["errors"]) == 0


@pytest.mark.asyncio
async def test_fetch_gilbert_arcgis_error():
    """Test Gilbert ArcGIS with error response."""
    mock_response = httpx.Response(
        200,
        json={"error": {"code": 400, "message": "Invalid query"}},
        request=httpx.Request("GET", "https://services1.arcgis.com/Gilbert"),
    )

    with patch("app.services.construction_api.gilbert_arcgis.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await fetch_gilbert_permits()

    assert result["records"] == []
    assert len(result["errors"]) > 0


@pytest.mark.asyncio
async def test_fetch_gilbert_http_error():
    """Test Gilbert ArcGIS with HTTP error."""
    mock_response = httpx.Response(
        503,
        request=httpx.Request("GET", "https://services1.arcgis.com/Gilbert"),
    )

    with patch("app.services.construction_api.gilbert_arcgis.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await fetch_gilbert_permits()

    assert result["records"] == []
    assert len(result["errors"]) > 0
    assert result["api_response_code"] == 503


@pytest.mark.asyncio
async def test_fetch_gilbert_skips_missing_date():
    """Features without IssueDate are skipped."""
    mock_response = httpx.Response(
        200,
        json={"features": [{"attributes": {"PermitNum": "X-001", "Address": "123 Main"}}]},
        request=httpx.Request("GET", "https://services1.arcgis.com/Gilbert"),
    )

    with patch("app.services.construction_api.gilbert_arcgis.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await fetch_gilbert_permits()

    assert result["records"] == []


# =============================================================================
# save_gilbert_records tests
# =============================================================================


class TestSaveGilbertRecords:
    def test_inserts_new_records(self, sync_db):
        records = [
            {
                "source": "gilbert_arcgis",
                "series_id": "GILBERT-BP-2025-001",
                "geography": "Gilbert, AZ",
                "period_date": date(2025, 3, 20),
                "period_type": "permit",
                "value": 1.0,
                "unit": "permits",
                "structure_type": "multifamily",
            },
        ]
        inserted, updated = save_gilbert_records(sync_db, records)
        assert inserted == 1
        assert updated == 0

        log = sync_db.query(ConstructionSourceLog).first()
        assert log is not None
        assert log.source_name == "gilbert_arcgis"
        assert log.records_inserted == 1
        assert log.success is True

    def test_upsert_updates_existing(self, sync_db):
        records = [
            {
                "source": "gilbert_arcgis",
                "series_id": "GILBERT-BP-2025-001",
                "geography": "Gilbert, AZ",
                "period_date": date(2025, 3, 20),
                "period_type": "permit",
                "value": 1.0,
                "unit": "permits",
                "structure_type": "multifamily",
            },
        ]
        save_gilbert_records(sync_db, records)

        records[0]["value"] = 2.0
        inserted, updated = save_gilbert_records(sync_db, records)
        assert inserted == 0
        assert updated == 1

        permit = sync_db.query(ConstructionPermitData).first()
        assert permit.value == 2.0
