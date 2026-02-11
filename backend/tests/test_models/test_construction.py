"""Tests for the construction pipeline models."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.construction import (
    ConstructionBrokerageMetrics,
    ConstructionEmploymentData,
    ConstructionPermitData,
    ConstructionProject,
    ConstructionSourceLog,
    PipelineStatus,
    ProjectClassification,
)

# =============================================================================
# ConstructionProject Model Tests
# =============================================================================


@pytest.mark.asyncio
async def test_create_project_minimal(db_session):
    """Test creating a ConstructionProject with only required fields."""
    now = datetime.now(UTC)
    project = ConstructionProject(
        pipeline_status=PipelineStatus.PROPOSED,
        primary_classification=ProjectClassification.CONV_MR,
        is_condo=False,
        source_type="costar",
        created_at=now,
        updated_at=now,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    assert project.id is not None
    assert project.pipeline_status == "proposed"
    assert project.primary_classification == "CONV_MR"
    assert project.is_condo is False
    assert project.source_type == "costar"


@pytest.mark.asyncio
async def test_create_project_full(db_session):
    """Test creating a ConstructionProject with all major fields."""
    now = datetime.now(UTC)
    project = ConstructionProject(
        costar_property_id="12345678",
        property_type="Multi-Family",
        project_name="Sonoran Vista Apartments",
        project_address="1234 N Scottsdale Rd",
        city="Scottsdale",
        state="AZ",
        zip_code="85251",
        county="Maricopa",
        latitude=33.4942,
        longitude=-111.9261,
        market_name="Phoenix",
        submarket_name="Scottsdale",
        submarket_cluster="Scottsdale/Tempe",
        pipeline_status=PipelineStatus.UNDER_CONSTRUCTION,
        constr_status_raw="Under Construction",
        building_status_raw="Under Construction",
        primary_classification=ProjectClassification.CONV_MR,
        secondary_tags="luxury,garden-style",
        number_of_units=280,
        building_sf=250000.0,
        number_of_stories=4,
        total_buildings=6,
        star_rating="4 Star",
        building_class="A",
        style="Garden",
        is_condo=False,
        pct_studio=5.0,
        pct_1bed=40.0,
        pct_2bed=35.0,
        pct_3bed=20.0,
        num_studios=14,
        num_1bed=112,
        num_2bed=98,
        num_3bed=56,
        avg_unit_sf=875.0,
        rent_type="Market",
        avg_asking_per_unit=1800.0,
        avg_asking_per_sf=2.06,
        vacancy_pct=5.2,
        year_built=2025,
        developer_name="LMC Development",
        owner_name="LMC",
        architect_name="KTGY Architecture",
        for_sale_price=None,
        land_area_ac=12.5,
        zoning="PUD",
        parking_spaces=420,
        source_type="costar",
        source_file="test_export.xlsx",
        imported_at=now,
        created_at=now,
        updated_at=now,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    assert project.id is not None
    assert project.project_name == "Sonoran Vista Apartments"
    assert project.number_of_units == 280
    assert project.pipeline_status == "under_construction"
    assert project.latitude == pytest.approx(33.4942)
    assert project.developer_name == "LMC Development"


@pytest.mark.asyncio
async def test_project_unique_constraint(db_session):
    """Test unique constraint on (costar_property_id, source_file)."""
    now = datetime.now(UTC)
    base_kwargs = dict(
        costar_property_id="99999",
        source_file="export.xlsx",
        pipeline_status=PipelineStatus.PROPOSED,
        primary_classification=ProjectClassification.CONV_MR,
        is_condo=False,
        source_type="costar",
        created_at=now,
        updated_at=now,
    )
    db_session.add(ConstructionProject(**base_kwargs))
    await db_session.commit()

    # Duplicate should raise IntegrityError
    db_session.add(ConstructionProject(**base_kwargs))
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_project_same_id_different_files(db_session):
    """Same costar_property_id in different files should be allowed."""
    now = datetime.now(UTC)
    base = dict(
        costar_property_id="99999",
        pipeline_status=PipelineStatus.PROPOSED,
        primary_classification=ProjectClassification.CONV_MR,
        is_condo=False,
        source_type="costar",
        created_at=now,
        updated_at=now,
    )
    db_session.add(ConstructionProject(**base, source_file="file_a.xlsx"))
    db_session.add(ConstructionProject(**base, source_file="file_b.xlsx"))
    await db_session.commit()

    result = await db_session.execute(
        select(ConstructionProject).where(
            ConstructionProject.costar_property_id == "99999"
        )
    )
    assert len(result.scalars().all()) == 2


@pytest.mark.asyncio
async def test_pipeline_status_enum_values(db_session):
    """Test all PipelineStatus enum values can be stored."""
    now = datetime.now(UTC)
    for status in PipelineStatus:
        project = ConstructionProject(
            costar_property_id=f"status-{status.value}",
            source_file="enum_test.xlsx",
            pipeline_status=status,
            primary_classification=ProjectClassification.CONV_MR,
            is_condo=False,
            source_type="costar",
            created_at=now,
            updated_at=now,
        )
        db_session.add(project)

    await db_session.commit()
    result = await db_session.execute(select(ConstructionProject))
    projects = result.scalars().all()
    assert len(projects) == len(PipelineStatus)
    stored = {p.pipeline_status for p in projects}
    assert stored == {s.value for s in PipelineStatus}


@pytest.mark.asyncio
async def test_classification_enum_values(db_session):
    """Test all ProjectClassification enum values can be stored."""
    now = datetime.now(UTC)
    for i, cls in enumerate(ProjectClassification):
        project = ConstructionProject(
            costar_property_id=f"class-{i}",
            source_file="enum_test.xlsx",
            pipeline_status=PipelineStatus.PROPOSED,
            primary_classification=cls,
            is_condo=False,
            source_type="costar",
            created_at=now,
            updated_at=now,
        )
        db_session.add(project)

    await db_session.commit()
    result = await db_session.execute(select(ConstructionProject))
    projects = result.scalars().all()
    assert len(projects) == len(ProjectClassification)
    stored = {p.primary_classification for p in projects}
    assert stored == {c.value for c in ProjectClassification}


@pytest.mark.asyncio
async def test_project_repr(db_session):
    """Test __repr__ of ConstructionProject."""
    now = datetime.now(UTC)
    project = ConstructionProject(
        project_name="Test Project",
        number_of_units=200,
        pipeline_status=PipelineStatus.PROPOSED,
        primary_classification=ProjectClassification.CONV_MR,
        is_condo=False,
        source_type="costar",
        created_at=now,
        updated_at=now,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    assert "Test Project" in repr(project)
    assert "200" in repr(project)
    assert "proposed" in repr(project)


# =============================================================================
# ConstructionSourceLog Model Tests
# =============================================================================


@pytest.mark.asyncio
async def test_create_source_log(db_session):
    """Test creating a ConstructionSourceLog."""
    now = datetime.now(UTC)
    log = ConstructionSourceLog(
        source_name="costar_construction",
        fetch_type="excel_import",
        fetched_at=now,
        records_fetched=291,
        records_inserted=241,
        records_updated=0,
        success=True,
        created_at=now,
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)

    assert log.id is not None
    assert log.source_name == "costar_construction"
    assert log.records_fetched == 291
    assert log.success is True


@pytest.mark.asyncio
async def test_source_log_with_error(db_session):
    """Test creating a failed source log entry."""
    now = datetime.now(UTC)
    log = ConstructionSourceLog(
        source_name="census_bps",
        fetch_type="api_fetch",
        fetched_at=now,
        records_fetched=0,
        records_inserted=0,
        records_updated=0,
        success=False,
        error_message="HTTP 503: Service Unavailable",
        api_response_code=503,
        created_at=now,
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)

    assert log.success is False
    assert "503" in log.error_message
    assert log.api_response_code == 503


# =============================================================================
# ConstructionPermitData Model Tests
# =============================================================================


@pytest.mark.asyncio
async def test_create_permit_data(db_session):
    """Test creating a ConstructionPermitData record."""
    now = datetime.now(UTC)
    permit = ConstructionPermitData(
        source="census_bps",
        series_id="BLDG5O_UNITS",
        geography="MSA:38060",
        period_date=date(2025, 12, 1),
        period_type="monthly",
        value=1250.0,
        unit="units",
        structure_type="5+ units",
        created_at=now,
        updated_at=now,
    )
    db_session.add(permit)
    await db_session.commit()
    await db_session.refresh(permit)

    assert permit.id is not None
    assert permit.source == "census_bps"
    assert permit.value == 1250.0


@pytest.mark.asyncio
async def test_permit_data_unique_constraint(db_session):
    """Test unique constraint on (source, series_id, period_date)."""
    now = datetime.now(UTC)
    base = dict(
        source="fred",
        series_id="PHOE004BPPRIVSA",
        period_date=date(2025, 6, 1),
        period_type="monthly",
        value=500.0,
        created_at=now,
        updated_at=now,
    )
    db_session.add(ConstructionPermitData(**base))
    await db_session.commit()

    db_session.add(ConstructionPermitData(**base))
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_permit_data_with_source_log_fk(db_session):
    """Test permit data references a source log."""
    now = datetime.now(UTC)
    log = ConstructionSourceLog(
        source_name="fred",
        fetch_type="api_fetch",
        fetched_at=now,
        records_fetched=24,
        records_inserted=24,
        records_updated=0,
        success=True,
        created_at=now,
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)

    permit = ConstructionPermitData(
        source="fred",
        series_id="PHOE004BPPRIVSA",
        period_date=date(2025, 1, 1),
        period_type="monthly",
        value=600.0,
        source_log_id=log.id,
        created_at=now,
        updated_at=now,
    )
    db_session.add(permit)
    await db_session.commit()
    await db_session.refresh(permit)

    assert permit.source_log_id == log.id


# =============================================================================
# ConstructionEmploymentData Model Tests
# =============================================================================


@pytest.mark.asyncio
async def test_create_employment_data(db_session):
    """Test creating a ConstructionEmploymentData record."""
    now = datetime.now(UTC)
    emp = ConstructionEmploymentData(
        series_id="SMU04380602000000001",
        series_title="Construction Employment, Phoenix MSA",
        period_date=date(2025, 10, 1),
        value=125.4,
        period_type="monthly",
        created_at=now,
        updated_at=now,
    )
    db_session.add(emp)
    await db_session.commit()
    await db_session.refresh(emp)

    assert emp.id is not None
    assert emp.value == 125.4


@pytest.mark.asyncio
async def test_employment_data_unique_constraint(db_session):
    """Test unique constraint on (series_id, period_date)."""
    now = datetime.now(UTC)
    base = dict(
        series_id="SMU04380602000000001",
        period_date=date(2025, 10, 1),
        value=125.4,
        period_type="monthly",
        created_at=now,
        updated_at=now,
    )
    db_session.add(ConstructionEmploymentData(**base))
    await db_session.commit()

    db_session.add(ConstructionEmploymentData(**base))
    with pytest.raises(IntegrityError):
        await db_session.commit()


# =============================================================================
# ConstructionBrokerageMetrics Model Tests
# =============================================================================


@pytest.mark.asyncio
async def test_create_brokerage_metrics(db_session):
    """Test creating a ConstructionBrokerageMetrics record."""
    now = datetime.now(UTC)
    metric = ConstructionBrokerageMetrics(
        report_source="CBRE",
        report_quarter="Q4",
        report_year=2025,
        metric_name="pipeline_units_total",
        metric_value=15000.0,
        notes="Q4 2025 Phoenix multifamily report",
        entered_by="analyst@example.com",
        created_at=now,
        updated_at=now,
    )
    db_session.add(metric)
    await db_session.commit()
    await db_session.refresh(metric)

    assert metric.id is not None
    assert metric.metric_value == 15000.0
    assert metric.report_quarter == "Q4"


@pytest.mark.asyncio
async def test_brokerage_metrics_unique_constraint(db_session):
    """Test unique constraint on (report_source, report_quarter, metric_name)."""
    now = datetime.now(UTC)
    base = dict(
        report_source="JLL",
        report_quarter="Q1",
        report_year=2026,
        metric_name="vacancy_rate",
        metric_value=6.5,
        created_at=now,
        updated_at=now,
    )
    db_session.add(ConstructionBrokerageMetrics(**base))
    await db_session.commit()

    db_session.add(ConstructionBrokerageMetrics(**base))
    with pytest.raises(IntegrityError):
        await db_session.commit()
