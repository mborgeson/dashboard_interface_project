"""Tests for construction pipeline API endpoints.

Covers the 12 REST endpoints mounted at /api/v1/construction-pipeline:
 0. GET /filter-options               -- Distinct values for dropdowns
 1. GET /                             -- Paginated project list
 2. GET /analytics/pipeline-summary   -- Counts by status
 3. GET /analytics/pipeline-funnel    -- Funnel view
 4. GET /analytics/permit-trends      -- Census BPS + FRED time-series
 5. GET /analytics/employment-overlay -- BLS employment time-series
 6. GET /analytics/permit-velocity    -- Municipal permit rates
 7. GET /analytics/submarket-pipeline -- Pipeline by submarket
 8. GET /analytics/classification-breakdown -- Units by classification
 9. GET /analytics/data-quality       -- Source freshness, null rates
10. POST /import                      -- Trigger file import
11. GET /import/status                -- Unimported files

All queries use SQLite-compatible functions (no percentile_cont, array_agg).
"""

from collections.abc import Generator
from datetime import UTC, date, datetime
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db, get_sync_db
from app.main import app
from app.models.construction import (
    ConstructionEmploymentData,
    ConstructionPermitData,
    ConstructionProject,
    ConstructionSourceLog,
)

# =============================================================================
# Sync + Async DB fixtures
# =============================================================================

sync_test_engine = create_engine(
    "sqlite:///:memory:",
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
SyncTestSession = sessionmaker(
    bind=sync_test_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="function")
def sync_db_session() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=sync_test_engine)
    session = SyncTestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=sync_test_engine)


@pytest_asyncio.fixture(scope="function")
async def cp_client(
    db_session: AsyncSession, sync_db_session: Session
) -> AsyncClient:
    """Client that overrides both async (get_db) and sync (get_sync_db) deps."""

    async def override_get_db():
        yield db_session

    def override_get_sync_db():
        yield sync_db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_sync_db] = override_get_sync_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# =============================================================================
# Helpers
# =============================================================================

BASE_URL = "/api/v1/construction-pipeline"
NOW = datetime.now(UTC)


def _make_project(
    costar_property_id: str = "CP-001",
    project_name: str = "Test Apartments",
    project_address: str = "100 Main St",
    city: str = "Phoenix",
    submarket_cluster: str = "Central Phoenix",
    pipeline_status: str = "under_construction",
    primary_classification: str = "CONV_MR",
    number_of_units: int = 200,
    year_built: int | None = None,
    developer_name: str = "Test Developer",
    latitude: float = 33.45,
    longitude: float = -112.07,
    rent_type: str = "Market",
    source_file: str = "test.xlsx",
    source_type: str = "costar",
) -> ConstructionProject:
    return ConstructionProject(
        costar_property_id=costar_property_id,
        project_name=project_name,
        project_address=project_address,
        city=city,
        submarket_cluster=submarket_cluster,
        pipeline_status=pipeline_status,
        primary_classification=primary_classification,
        number_of_units=number_of_units,
        year_built=year_built,
        developer_name=developer_name,
        latitude=latitude,
        longitude=longitude,
        rent_type=rent_type,
        source_file=source_file,
        source_type=source_type,
        imported_at=NOW,
        created_at=NOW,
        updated_at=NOW,
    )


async def _seed_projects(db: AsyncSession) -> list[ConstructionProject]:
    """Seed 5 projects across different statuses/submarkets/classifications."""
    projects = [
        _make_project(
            costar_property_id="CP-001",
            project_name="Downtown Tower",
            city="Phoenix",
            submarket_cluster="Central Phoenix",
            pipeline_status="under_construction",
            primary_classification="CONV_MR",
            number_of_units=300,
            developer_name="Urban Dev Co",
        ),
        _make_project(
            costar_property_id="CP-002",
            project_name="Mesa Gardens",
            city="Mesa",
            submarket_cluster="East Valley",
            pipeline_status="proposed",
            primary_classification="LIHTC",
            number_of_units=150,
            developer_name="Affordable Housing Inc",
            rent_type="Affordable",
        ),
        _make_project(
            costar_property_id="CP-003",
            project_name="Scottsdale Heights",
            city="Scottsdale",
            submarket_cluster="North Scottsdale",
            pipeline_status="delivered",
            primary_classification="CONV_CONDO",
            number_of_units=80,
            developer_name="Luxury Builders",
        ),
        _make_project(
            costar_property_id="CP-004",
            project_name="Tempe Student Lofts",
            city="Tempe",
            submarket_cluster="Tempe/ASU",
            pipeline_status="final_planning",
            primary_classification="CONV_MR",
            number_of_units=250,
            developer_name="Student Housing LLC",
        ),
        _make_project(
            costar_property_id="CP-005",
            project_name="Gilbert BTR Community",
            city="Gilbert",
            submarket_cluster="Southeast Valley",
            pipeline_status="permitted",
            primary_classification="BTR",
            number_of_units=120,
            developer_name="BTR Builders",
        ),
    ]
    for p in projects:
        db.add(p)
    await db.commit()
    for p in projects:
        await db.refresh(p)
    return projects


async def _seed_permit_data(db: AsyncSession) -> None:
    """Seed permit time-series data."""
    records = [
        ConstructionPermitData(
            source="census_bps",
            series_id="BLDG5O_UNITS",
            geography="MSA:38060",
            period_date=date(2025, 1, 1),
            period_type="monthly",
            value=450.0,
            unit="units",
            created_at=NOW,
            updated_at=NOW,
        ),
        ConstructionPermitData(
            source="census_bps",
            series_id="BLDG5O_UNITS",
            geography="MSA:38060",
            period_date=date(2025, 2, 1),
            period_type="monthly",
            value=475.0,
            unit="units",
            created_at=NOW,
            updated_at=NOW,
        ),
        ConstructionPermitData(
            source="fred",
            series_id="PHOE004BPPRIVSA",
            geography="Phoenix MSA",
            period_date=date(2025, 1, 1),
            period_type="monthly",
            value=1200.0,
            unit="permits",
            created_at=NOW,
            updated_at=NOW,
        ),
    ]
    for r in records:
        db.add(r)
    await db.commit()


async def _seed_employment_data(db: AsyncSession) -> None:
    """Seed employment time-series data."""
    records = [
        ConstructionEmploymentData(
            series_id="SMU04380602000000001",
            series_title="Construction Employment, Phoenix MSA",
            period_date=date(2025, 9, 1),
            value=124.1,
            period_type="monthly",
            created_at=NOW,
            updated_at=NOW,
        ),
        ConstructionEmploymentData(
            series_id="SMU04380602000000001",
            series_title="Construction Employment, Phoenix MSA",
            period_date=date(2025, 10, 1),
            value=125.4,
            period_type="monthly",
            created_at=NOW,
            updated_at=NOW,
        ),
    ]
    for r in records:
        db.add(r)
    await db.commit()


async def _seed_source_log(db: AsyncSession) -> None:
    """Seed a source log entry."""
    log = ConstructionSourceLog(
        source_name="costar_import",
        fetch_type="file_import",
        fetched_at=NOW,
        records_fetched=5,
        records_inserted=5,
        records_updated=0,
        success=True,
        created_at=NOW,
    )
    db.add(log)
    await db.commit()


# =============================================================================
# Tests: GET /filter-options
# =============================================================================


class TestFilterOptions:
    @pytest.mark.asyncio
    async def test_returns_distinct_values(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_projects(db_session)
        resp = await cp_client.get(f"{BASE_URL}/filter-options")
        assert resp.status_code == 200
        data = resp.json()
        assert "Central Phoenix" in data["submarkets"]
        assert "Phoenix" in data["cities"]
        assert "under_construction" in data["statuses"]
        assert "CONV_MR" in data["classifications"]
        assert "Market" in data["rent_types"]

    @pytest.mark.asyncio
    async def test_empty_db(self, cp_client: AsyncClient):
        resp = await cp_client.get(f"{BASE_URL}/filter-options")
        assert resp.status_code == 200
        data = resp.json()
        assert data["submarkets"] == []
        assert data["cities"] == []


# =============================================================================
# Tests: GET / (paginated list)
# =============================================================================


class TestListProjects:
    @pytest.mark.asyncio
    async def test_returns_paginated_data(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_projects(db_session)
        resp = await cp_client.get(f"{BASE_URL}/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert data["page"] == 1
        assert len(data["data"]) == 5

    @pytest.mark.asyncio
    async def test_pagination(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_projects(db_session)
        resp = await cp_client.get(f"{BASE_URL}/?page=1&page_size=2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["data"]) == 2
        assert data["total_pages"] == 3

    @pytest.mark.asyncio
    async def test_filter_by_status(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_projects(db_session)
        resp = await cp_client.get(
            f"{BASE_URL}/?statuses=under_construction"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["data"][0]["pipeline_status"] == "under_construction"

    @pytest.mark.asyncio
    async def test_filter_by_classification(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_projects(db_session)
        resp = await cp_client.get(f"{BASE_URL}/?classifications=LIHTC")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["data"][0]["primary_classification"] == "LIHTC"

    @pytest.mark.asyncio
    async def test_filter_by_city(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_projects(db_session)
        resp = await cp_client.get(f"{BASE_URL}/?cities=Mesa")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["data"][0]["city"] == "Mesa"

    @pytest.mark.asyncio
    async def test_filter_by_min_units(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_projects(db_session)
        resp = await cp_client.get(f"{BASE_URL}/?min_units=200")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2  # 300 + 250

    @pytest.mark.asyncio
    async def test_search(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_projects(db_session)
        resp = await cp_client.get(f"{BASE_URL}/?search=Downtown")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["data"][0]["project_name"] == "Downtown Tower"

    @pytest.mark.asyncio
    async def test_sort_asc(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_projects(db_session)
        resp = await cp_client.get(
            f"{BASE_URL}/?sort_by=number_of_units&sort_dir=asc"
        )
        assert resp.status_code == 200
        data = resp.json()
        units = [r["number_of_units"] for r in data["data"]]
        assert units == sorted(units)

    @pytest.mark.asyncio
    async def test_empty_db(self, cp_client: AsyncClient):
        resp = await cp_client.get(f"{BASE_URL}/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["data"] == []


# =============================================================================
# Tests: GET /analytics/pipeline-summary
# =============================================================================


class TestPipelineSummary:
    @pytest.mark.asyncio
    async def test_returns_status_counts(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_projects(db_session)
        resp = await cp_client.get(f"{BASE_URL}/analytics/pipeline-summary")
        assert resp.status_code == 200
        data = resp.json()
        status_map = {r["status"]: r for r in data}
        assert status_map["under_construction"]["project_count"] == 1
        assert status_map["under_construction"]["total_units"] == 300
        assert status_map["proposed"]["project_count"] == 1

    @pytest.mark.asyncio
    async def test_with_classification_filter(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_projects(db_session)
        resp = await cp_client.get(
            f"{BASE_URL}/analytics/pipeline-summary?classifications=CONV_MR"
        )
        assert resp.status_code == 200
        data = resp.json()
        total_projects = sum(r["project_count"] for r in data)
        assert total_projects == 2  # CP-001 + CP-004


# =============================================================================
# Tests: GET /analytics/pipeline-funnel
# =============================================================================


class TestPipelineFunnel:
    @pytest.mark.asyncio
    async def test_returns_ordered_funnel(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_projects(db_session)
        resp = await cp_client.get(f"{BASE_URL}/analytics/pipeline-funnel")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5
        assert data[0]["status"] == "proposed"
        assert data[-1]["status"] == "delivered"
        # Cumulative should be non-decreasing
        for i in range(1, len(data)):
            assert data[i]["cumulative_units"] >= data[i - 1]["cumulative_units"]

    @pytest.mark.asyncio
    async def test_cumulative_units(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_projects(db_session)
        resp = await cp_client.get(f"{BASE_URL}/analytics/pipeline-funnel")
        data = resp.json()
        # Total cumulative = sum of all units = 300 + 150 + 80 + 250 + 120 = 900
        assert data[-1]["cumulative_units"] == 900


# =============================================================================
# Tests: GET /analytics/permit-trends
# =============================================================================


class TestPermitTrends:
    @pytest.mark.asyncio
    async def test_returns_permit_data(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_permit_data(db_session)
        resp = await cp_client.get(f"{BASE_URL}/analytics/permit-trends")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_filter_by_source(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_permit_data(db_session)
        resp = await cp_client.get(
            f"{BASE_URL}/analytics/permit-trends?source=fred"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["source"] == "fred"

    @pytest.mark.asyncio
    async def test_empty(self, cp_client: AsyncClient):
        resp = await cp_client.get(f"{BASE_URL}/analytics/permit-trends")
        assert resp.status_code == 200
        assert resp.json() == []


# =============================================================================
# Tests: GET /analytics/employment-overlay
# =============================================================================


class TestEmploymentOverlay:
    @pytest.mark.asyncio
    async def test_returns_employment_data(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_employment_data(db_session)
        resp = await cp_client.get(
            f"{BASE_URL}/analytics/employment-overlay"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_empty(self, cp_client: AsyncClient):
        resp = await cp_client.get(
            f"{BASE_URL}/analytics/employment-overlay"
        )
        assert resp.status_code == 200
        assert resp.json() == []


# =============================================================================
# Tests: GET /analytics/permit-velocity
# =============================================================================


class TestPermitVelocity:
    @pytest.mark.asyncio
    async def test_empty_no_municipal(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        """No municipal data → empty result (census_bps/fred are excluded)."""
        await _seed_permit_data(db_session)
        resp = await cp_client.get(
            f"{BASE_URL}/analytics/permit-velocity"
        )
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_with_municipal_data(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        """Seed mesa_soda permit data → returned in velocity."""
        permit = ConstructionPermitData(
            source="mesa_soda",
            series_id="building_permit",
            geography="Mesa, AZ",
            period_date=date(2025, 6, 1),
            period_type="monthly",
            value=15.0,
            created_at=NOW,
            updated_at=NOW,
        )
        db_session.add(permit)
        await db_session.commit()

        resp = await cp_client.get(
            f"{BASE_URL}/analytics/permit-velocity"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["source"] == "mesa_soda"


# =============================================================================
# Tests: GET /analytics/submarket-pipeline
# =============================================================================


class TestSubmarketPipeline:
    @pytest.mark.asyncio
    async def test_returns_submarket_breakdown(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_projects(db_session)
        resp = await cp_client.get(
            f"{BASE_URL}/analytics/submarket-pipeline"
        )
        assert resp.status_code == 200
        data = resp.json()
        submarket_map = {r["submarket"]: r for r in data}
        assert "Central Phoenix" in submarket_map
        assert submarket_map["Central Phoenix"]["total_units"] == 300
        assert submarket_map["Central Phoenix"]["under_construction"] == 1

    @pytest.mark.asyncio
    async def test_proposed_count(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_projects(db_session)
        resp = await cp_client.get(
            f"{BASE_URL}/analytics/submarket-pipeline"
        )
        data = resp.json()
        submarket_map = {r["submarket"]: r for r in data}
        assert submarket_map["East Valley"]["proposed"] == 1


# =============================================================================
# Tests: GET /analytics/classification-breakdown
# =============================================================================


class TestClassificationBreakdown:
    @pytest.mark.asyncio
    async def test_returns_classification_counts(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_projects(db_session)
        resp = await cp_client.get(
            f"{BASE_URL}/analytics/classification-breakdown"
        )
        assert resp.status_code == 200
        data = resp.json()
        cls_map = {r["classification"]: r for r in data}
        assert "CONV_MR" in cls_map
        assert cls_map["CONV_MR"]["project_count"] == 2
        assert cls_map["CONV_MR"]["total_units"] == 550  # 300 + 250

    @pytest.mark.asyncio
    async def test_with_status_filter(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_projects(db_session)
        resp = await cp_client.get(
            f"{BASE_URL}/analytics/classification-breakdown?statuses=delivered"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["classification"] == "CONV_CONDO"


# =============================================================================
# Tests: GET /analytics/data-quality
# =============================================================================


class TestDataQuality:
    @pytest.mark.asyncio
    async def test_returns_quality_report(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_projects(db_session)
        await _seed_permit_data(db_session)
        await _seed_employment_data(db_session)
        await _seed_source_log(db_session)

        resp = await cp_client.get(f"{BASE_URL}/analytics/data-quality")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_projects"] == 5
        assert data["projects_by_source"]["costar"] == 5
        assert data["permit_data_count"] == 3
        assert data["employment_data_count"] == 2
        assert len(data["source_logs"]) == 1
        assert "project_name" in data["null_rates"]

    @pytest.mark.asyncio
    async def test_empty_db(self, cp_client: AsyncClient):
        resp = await cp_client.get(f"{BASE_URL}/analytics/data-quality")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_projects"] == 0
        assert data["null_rates"] == {}


# =============================================================================
# Tests: POST /import
# =============================================================================


class TestImport:
    @pytest.mark.asyncio
    async def test_no_files_to_import(self, cp_client: AsyncClient):
        with patch(
            "app.api.v1.endpoints.construction_pipeline.CONSTRUCTION_DATA_DIR",
            "/nonexistent/path",
        ):
            resp = await cp_client.post(f"{BASE_URL}/import")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["message"] == "No new files to import."

    @pytest.mark.asyncio
    async def test_import_error_handled(self, cp_client: AsyncClient):
        with patch(
            "app.services.construction_import.get_unimported_files",
            side_effect=RuntimeError("disk full"),
        ):
            resp = await cp_client.post(f"{BASE_URL}/import")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "disk full" in data["message"]


# =============================================================================
# Tests: GET /import/status
# =============================================================================


class TestImportStatus:
    @pytest.mark.asyncio
    async def test_returns_status(self, cp_client: AsyncClient):
        with patch(
            "app.api.v1.endpoints.construction_pipeline.CONSTRUCTION_DATA_DIR",
            "/nonexistent/path",
        ):
            resp = await cp_client.get(f"{BASE_URL}/import/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["unimported_files"] == []
        assert data["total_projects"] == 0

    @pytest.mark.asyncio
    async def test_with_existing_projects(
        self, cp_client: AsyncClient, db_session: AsyncSession, sync_db_session: Session
    ):
        """Seed a project in sync DB to verify last import info."""
        # Use sync session since import/status uses get_sync_db
        Base.metadata.create_all(bind=sync_test_engine)
        proj = ConstructionProject(
            costar_property_id="CP-SYNC",
            project_name="Sync Test",
            pipeline_status="proposed",
            primary_classification="CONV_MR",
            source_type="costar",
            source_file="test_sync.xlsx",
            imported_at=NOW,
            created_at=NOW,
            updated_at=NOW,
        )
        sync_db_session.add(proj)
        sync_db_session.commit()

        with patch(
            "app.api.v1.endpoints.construction_pipeline.CONSTRUCTION_DATA_DIR",
            "/nonexistent/path",
        ):
            resp = await cp_client.get(f"{BASE_URL}/import/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_projects"] == 1
        assert data["last_imported_file"] == "test_sync.xlsx"


# =============================================================================
# Tests: Multiple filter combinations
# =============================================================================


class TestCombinedFilters:
    @pytest.mark.asyncio
    async def test_status_and_city(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_projects(db_session)
        resp = await cp_client.get(
            f"{BASE_URL}/?statuses=under_construction&cities=Phoenix"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_multiple_statuses(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_projects(db_session)
        resp = await cp_client.get(
            f"{BASE_URL}/?statuses=proposed,delivered"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    @pytest.mark.asyncio
    async def test_rent_type_filter(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_projects(db_session)
        resp = await cp_client.get(f"{BASE_URL}/?rent_type=Affordable")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["data"][0]["project_name"] == "Mesa Gardens"

    @pytest.mark.asyncio
    async def test_unit_range_filter(
        self, cp_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_projects(db_session)
        resp = await cp_client.get(
            f"{BASE_URL}/?min_units=100&max_units=200"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2  # 150 + 120
