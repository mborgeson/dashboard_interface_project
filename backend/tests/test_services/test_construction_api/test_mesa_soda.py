"""Tests for the Mesa SODA API client."""

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
from app.services.construction_api.mesa_soda import (
    fetch_mesa_permits,
    save_mesa_records,
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
# fetch_mesa_permits tests (mocked HTTP)
# =============================================================================

MOCK_MESA_RESPONSE = [
    {
        "permit_number": "BLD2025-00001",
        "permit_issue_date": "2025-03-15T00:00:00.000",
        "address": "1234 E Main St",
        "description": "NEW MULTI-FAMILY 250 UNITS",
        "permit_type": "BUILDING",
        "work_class": "NEW MULTI-FAMILY",
    },
    {
        "permit_number": "BLD2025-00002",
        "permit_issue_date": "2025-04-01T00:00:00.000",
        "address": "5678 N Power Rd",
        "description": "MULTI-FAMILY ADDITION",
        "permit_type": "BUILDING",
        "work_class": "ADDITION MULTI-FAMILY",
    },
]


@pytest.mark.asyncio
async def test_fetch_mesa_success():
    """Test successful Mesa SODA fetch."""
    mock_response = httpx.Response(
        200,
        json=MOCK_MESA_RESPONSE,
        request=httpx.Request("GET", "https://data.mesaaz.gov"),
    )

    with patch("app.services.construction_api.mesa_soda.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await fetch_mesa_permits()

    assert len(result["records"]) == 2
    assert result["api_response_code"] == 200
    assert len(result["errors"]) == 0

    rec = result["records"][0]
    assert rec["source"] == "mesa_soda"
    assert rec["series_id"] == "MESA-BLD2025-00001"
    assert rec["geography"] == "Mesa, AZ"
    assert isinstance(rec["period_date"], date)
    assert rec["address"] == "1234 E Main St"


@pytest.mark.asyncio
async def test_fetch_mesa_empty_response():
    """Test Mesa SODA with empty data."""
    mock_response = httpx.Response(
        200,
        json=[],
        request=httpx.Request("GET", "https://data.mesaaz.gov"),
    )

    with patch("app.services.construction_api.mesa_soda.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await fetch_mesa_permits()

    assert result["records"] == []
    assert len(result["errors"]) == 0


@pytest.mark.asyncio
async def test_fetch_mesa_http_error():
    """Test Mesa SODA with HTTP error."""
    mock_response = httpx.Response(
        500,
        request=httpx.Request("GET", "https://data.mesaaz.gov"),
    )

    with patch("app.services.construction_api.mesa_soda.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await fetch_mesa_permits()

    assert result["records"] == []
    assert len(result["errors"]) > 0
    assert result["api_response_code"] == 500


@pytest.mark.asyncio
async def test_fetch_mesa_skips_missing_date():
    """Rows without permit_issue_date are skipped."""
    mock_response = httpx.Response(
        200,
        json=[{"permit_number": "BLD-001", "address": "123 Main"}],
        request=httpx.Request("GET", "https://data.mesaaz.gov"),
    )

    with patch("app.services.construction_api.mesa_soda.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await fetch_mesa_permits()

    assert result["records"] == []


# =============================================================================
# save_mesa_records tests
# =============================================================================


class TestSaveMesaRecords:
    def test_inserts_new_records(self, sync_db):
        records = [
            {
                "source": "mesa_soda",
                "series_id": "MESA-BLD2025-001",
                "geography": "Mesa, AZ",
                "period_date": date(2025, 3, 15),
                "period_type": "permit",
                "value": 1.0,
                "unit": "permits",
                "structure_type": "multifamily",
            },
        ]
        inserted, updated = save_mesa_records(sync_db, records)
        assert inserted == 1
        assert updated == 0

        log = sync_db.query(ConstructionSourceLog).first()
        assert log is not None
        assert log.source_name == "mesa_soda"
        assert log.records_inserted == 1
        assert log.success is True

    def test_upsert_updates_existing(self, sync_db):
        records = [
            {
                "source": "mesa_soda",
                "series_id": "MESA-BLD2025-001",
                "geography": "Mesa, AZ",
                "period_date": date(2025, 3, 15),
                "period_type": "permit",
                "value": 1.0,
                "unit": "permits",
                "structure_type": "multifamily",
            },
        ]
        save_mesa_records(sync_db, records)

        records[0]["value"] = 2.0
        inserted, updated = save_mesa_records(sync_db, records)
        assert inserted == 0
        assert updated == 1

        permit = sync_db.query(ConstructionPermitData).first()
        assert permit.value == 2.0
