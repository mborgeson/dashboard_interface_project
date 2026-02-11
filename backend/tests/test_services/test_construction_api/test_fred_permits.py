"""Tests for the FRED permits API client."""

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
from app.services.construction_api.fred_permits import (
    FRED_PERMIT_SERIES,
    fetch_fred_permits,
    save_fred_records,
)

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


MOCK_FRED_RESPONSE = {
    "observations": [
        {"date": "2025-01-01", "value": "450"},
        {"date": "2025-02-01", "value": "475"},
        {"date": "2025-03-01", "value": "."},  # Missing value
    ]
}


@pytest.mark.asyncio
async def test_fetch_fred_success():
    """Test successful FRED fetch for single series."""
    mock_response = httpx.Response(
        200,
        json=MOCK_FRED_RESPONSE,
        request=httpx.Request("GET", "https://api.stlouisfed.org"),
    )

    with patch("app.services.construction_api.fred_permits.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await fetch_fred_permits(
            "test-key", series_ids=["PHOE004BPPRIVSA"]
        )

    # 2 valid records (skips "." value)
    assert len(result["records"]) == 2
    assert result["errors"] == []
    assert result["records"][0]["source"] == "fred"
    assert result["records"][0]["series_id"] == "PHOE004BPPRIVSA"


@pytest.mark.asyncio
async def test_fetch_fred_http_error():
    """Test FRED fetch with HTTP error."""
    mock_response = httpx.Response(
        429,
        request=httpx.Request("GET", "https://api.stlouisfed.org"),
    )

    with patch("app.services.construction_api.fred_permits.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await fetch_fred_permits(
            "test-key", series_ids=["PHOE004BPPRIVSA"]
        )

    assert result["records"] == []
    assert len(result["errors"]) > 0


class TestSaveFredRecords:
    def test_inserts_records(self, sync_db):
        records = [
            {
                "source": "fred",
                "series_id": "PHOE004BPPRIVSA",
                "geography": "Phoenix MSA",
                "period_date": date(2025, 1, 1),
                "period_type": "monthly",
                "value": 450.0,
                "unit": "permits",
                "structure_type": None,
            },
        ]
        inserted, updated = save_fred_records(sync_db, records)
        assert inserted == 1
        assert updated == 0

        log = sync_db.query(ConstructionSourceLog).first()
        assert log.source_name == "fred_permits"
        assert log.success is True

    def test_upsert_updates(self, sync_db):
        records = [
            {
                "source": "fred",
                "series_id": "PHOE004BPPRIVSA",
                "geography": "Phoenix MSA",
                "period_date": date(2025, 1, 1),
                "period_type": "monthly",
                "value": 450.0,
                "unit": "permits",
                "structure_type": None,
            },
        ]
        save_fred_records(sync_db, records)
        records[0]["value"] = 500.0
        inserted, updated = save_fred_records(sync_db, records)
        assert inserted == 0
        assert updated == 1
