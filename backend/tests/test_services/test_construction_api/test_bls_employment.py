"""Tests for the BLS employment API client."""

from collections.abc import Generator
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.construction import ConstructionEmploymentData, ConstructionSourceLog
from app.services.construction_api.bls_employment import (
    BLS_EMPLOYMENT_SERIES,
    fetch_bls_employment,
    save_bls_records,
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


MOCK_BLS_RESPONSE = {
    "status": "REQUEST_SUCCEEDED",
    "Results": {
        "series": [
            {
                "seriesID": "SMU04380602000000001",
                "data": [
                    {"year": "2025", "period": "M10", "value": "125.4"},
                    {"year": "2025", "period": "M09", "value": "124.1"},
                    {"year": "2025", "period": "M13", "value": "124.8"},  # Annual avg — should skip
                ],
            }
        ]
    },
}


@pytest.mark.asyncio
async def test_fetch_bls_success():
    """Test successful BLS fetch."""
    mock_response = httpx.Response(
        200,
        json=MOCK_BLS_RESPONSE,
        request=httpx.Request("POST", "https://api.bls.gov"),
    )

    with patch("app.services.construction_api.bls_employment.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await fetch_bls_employment(
            series_ids=["SMU04380602000000001"],
            start_year=2025,
            end_year=2025,
        )

    # 2 valid records (M13 annual avg skipped)
    assert len(result["records"]) == 2
    assert result["errors"] == []
    assert result["records"][0]["series_id"] == "SMU04380602000000001"
    assert result["records"][0]["period_type"] == "monthly"


@pytest.mark.asyncio
async def test_fetch_bls_api_error():
    """Test BLS fetch with API error status."""
    mock_response = httpx.Response(
        200,
        json={
            "status": "REQUEST_FAILED",
            "message": ["Invalid Series ID"],
        },
        request=httpx.Request("POST", "https://api.bls.gov"),
    )

    with patch("app.services.construction_api.bls_employment.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await fetch_bls_employment(
            series_ids=["INVALID"],
            start_year=2025,
            end_year=2025,
        )

    assert result["records"] == []
    assert len(result["errors"]) > 0


@pytest.mark.asyncio
async def test_fetch_bls_http_error():
    """Test BLS fetch with HTTP error."""
    mock_response = httpx.Response(
        500,
        request=httpx.Request("POST", "https://api.bls.gov"),
    )

    with patch("app.services.construction_api.bls_employment.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await fetch_bls_employment(series_ids=["TEST"])

    assert result["records"] == []
    assert result["api_response_code"] == 500


class TestSaveBlsRecords:
    def test_inserts_records(self, sync_db):
        records = [
            {
                "series_id": "SMU04380602000000001",
                "series_title": "Construction Employment, Phoenix MSA",
                "period_date": date(2025, 10, 1),
                "value": 125.4,
                "period_type": "monthly",
            },
        ]
        inserted, updated = save_bls_records(sync_db, records)
        assert inserted == 1
        assert updated == 0

        log = sync_db.query(ConstructionSourceLog).first()
        assert log.source_name == "bls_employment"
        assert log.success is True

    def test_upsert_updates(self, sync_db):
        records = [
            {
                "series_id": "SMU04380602000000001",
                "series_title": "Construction Employment, Phoenix MSA",
                "period_date": date(2025, 10, 1),
                "value": 125.4,
                "period_type": "monthly",
            },
        ]
        save_bls_records(sync_db, records)
        records[0]["value"] = 126.0
        inserted, updated = save_bls_records(sync_db, records)
        assert inserted == 0
        assert updated == 1

        emp = sync_db.query(ConstructionEmploymentData).first()
        assert emp.value == 126.0
