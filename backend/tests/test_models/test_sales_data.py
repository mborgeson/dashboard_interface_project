"""Tests for the SalesData model."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.sales_data import SalesData

# =============================================================================
# Basic Model Tests
# =============================================================================


@pytest.mark.asyncio
async def test_create_sales_data_minimal(db_session):
    """Test creating a SalesData record with only required fields."""
    now = datetime.now(UTC)
    record = SalesData(
        comp_id="C-001",
        source_file="test_export.xlsx",
        created_at=now,
        updated_at=now,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    assert record.id is not None
    assert record.comp_id == "C-001"
    assert record.source_file == "test_export.xlsx"
    assert record.created_at is not None
    assert record.updated_at is not None


@pytest.mark.asyncio
async def test_create_sales_data_all_fields(db_session):
    """Test creating a SalesData record with all fields populated."""
    now = datetime.now(UTC)
    record = SalesData(
        source_file="full_export.xlsx",
        imported_at=now,
        market="Phoenix",
        property_name="Sunset Apartments",
        property_id="P-12345",
        comp_id="C-999",
        property_address="100 Main St",
        property_city="Phoenix",
        property_state="AZ",
        property_zip_code="85001",
        latitude=33.4484,
        longitude=-112.0740,
        property_county="Maricopa",
        submarket_cluster="Central Phoenix",
        submarket_name="Downtown",
        parcel_number_1_min="123-45-001",
        parcel_number_2_max="123-45-009",
        land_area_ac=5.0,
        land_area_sf=217800.0,
        location_type="Urban",
        star_rating="4 Star",
        market_column="Phoenix",
        submarket_code="PHX-DT",
        building_class="A",
        affordable_type="Market Rate",
        buyer_true_company="Acme Corp",
        buyer_true_contact="John Smith",
        acquisition_fund_name="Fund VII",
        buyer_contact="Jane Doe",
        seller_true_company="Seller LLC",
        disposition_fund_name="Disposition I",
        listing_broker_company="CBRE",
        listing_broker_agent_first_name="Bob",
        listing_broker_agent_last_name="Jones",
        buyers_broker_company="JLL",
        buyers_broker_agent_first_name="Alice",
        buyers_broker_agent_last_name="Williams",
        construction_begin="2018-01",
        year_built=2019,
        year_renovated=2023,
        age=5,
        property_type="Multifamily",
        building_sf=120000.0,
        building_materials="Steel Frame",
        building_condition="Excellent",
        construction_material="Steel",
        roof_type="Flat",
        ceiling_height="10ft",
        secondary_type="Garden",
        number_of_floors=3,
        number_of_units=200,
        number_of_parking_spaces=300,
        number_of_tenants=195,
        land_sf_gross=220000.0,
        land_sf_net=210000.0,
        flood_risk="Low",
        flood_zone="X",
        avg_unit_sf=800.0,
        sale_date=date(2024, 6, 15),
        sale_price=50000000.0,
        price_per_unit=250000.0,
        price_per_sf_net=240.0,
        price_per_sf=416.67,
        hold_period="5 Years",
        document_number="DOC-2024-001",
        down_payment=15000000.0,
        sale_type="Investment",
        sale_condition="Arm's Length",
        sale_price_comment="Full price",
        sale_status="Confirmed",
        sale_category="Investment Sale",
        actual_cap_rate=5.25,
        units_per_acre=40.0,
        zoning="R-5",
        number_of_beds=350,
        gross_income=12000000.0,
        grm=4.17,
        gim=4.0,
        building_operating_expenses="$3,500,000",
        total_expense_amount=3500000.0,
        vacancy=2.5,
        assessed_improved=35000000.0,
        assessed_land=8000000.0,
        assessed_value=43000000.0,
        assessed_year=2024,
        number_of_studios_units=20,
        number_of_1_bedrooms_units=80,
        number_of_2_bedrooms_units=70,
        number_of_3_bedrooms_units=25,
        number_of_other_bedrooms_units=5,
        first_trust_deed_terms="30yr Fixed",
        first_trust_deed_balance=35000000.0,
        first_trust_deed_lender="Wells Fargo",
        first_trust_deed_payment=200000.0,
        second_trust_deed_balance=5000000.0,
        second_trust_deed_lender="Mezzanine Co",
        second_trust_deed_payment=50000.0,
        second_trust_deed_terms="10yr IO",
        title_company="First American",
        amenities="Pool, Gym, Clubhouse",
        sewer="Municipal",
        transaction_notes="Portfolio deal",
        description_text="Class A garden-style community",
        research_status="Verified",
        created_at=now,
        updated_at=now,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    assert record.id is not None
    assert record.property_name == "Sunset Apartments"
    assert record.sale_price == 50000000.0
    assert record.number_of_units == 200
    assert record.year_built == 2019
    assert record.sale_date == date(2024, 6, 15)
    assert record.latitude == 33.4484
    assert record.actual_cap_rate == 5.25


@pytest.mark.asyncio
async def test_nullable_fields_accept_none(db_session):
    """Test that nullable fields properly accept None values."""
    now = datetime.now(UTC)
    record = SalesData(
        comp_id="C-002",
        source_file="partial.xlsx",
        property_name=None,
        sale_price=None,
        sale_date=None,
        year_built=None,
        number_of_units=None,
        latitude=None,
        longitude=None,
        actual_cap_rate=None,
        created_at=now,
        updated_at=now,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    assert record.id is not None
    assert record.property_name is None
    assert record.sale_price is None
    assert record.sale_date is None
    assert record.year_built is None
    assert record.number_of_units is None
    assert record.latitude is None
    assert record.actual_cap_rate is None


# =============================================================================
# Unique Constraint Tests
# =============================================================================


@pytest.mark.asyncio
async def test_unique_constraint_comp_id_source_file(db_session):
    """Test that the unique constraint on (comp_id, source_file) is enforced."""
    now = datetime.now(UTC)
    record1 = SalesData(
        comp_id="C-DUP",
        source_file="export_a.xlsx",
        created_at=now,
        updated_at=now,
    )
    db_session.add(record1)
    await db_session.commit()

    record2 = SalesData(
        comp_id="C-DUP",
        source_file="export_a.xlsx",
        created_at=now,
        updated_at=now,
    )
    db_session.add(record2)

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_same_comp_id_different_source_file(db_session):
    """Test that the same comp_id can exist in different source files."""
    now = datetime.now(UTC)
    record1 = SalesData(
        comp_id="C-SHARED",
        source_file="export_jan.xlsx",
        created_at=now,
        updated_at=now,
    )
    record2 = SalesData(
        comp_id="C-SHARED",
        source_file="export_feb.xlsx",
        created_at=now,
        updated_at=now,
    )
    db_session.add(record1)
    db_session.add(record2)
    await db_session.commit()

    result = await db_session.execute(
        select(SalesData).where(SalesData.comp_id == "C-SHARED")
    )
    records = result.scalars().all()
    assert len(records) == 2


# =============================================================================
# Timestamp Tests
# =============================================================================


@pytest.mark.asyncio
async def test_created_at_updated_at_set(db_session):
    """Test that created_at and updated_at are properly set."""
    now = datetime.now(UTC)
    record = SalesData(
        comp_id="C-TS",
        source_file="ts_test.xlsx",
        created_at=now,
        updated_at=now,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    assert record.created_at is not None
    assert record.updated_at is not None
    # Both should be close to 'now'
    assert (
        abs(
            (
                record.created_at.replace(tzinfo=None) - now.replace(tzinfo=None)
            ).total_seconds()
        )
        < 2
    )
    assert (
        abs(
            (
                record.updated_at.replace(tzinfo=None) - now.replace(tzinfo=None)
            ).total_seconds()
        )
        < 2
    )


# =============================================================================
# Repr Test
# =============================================================================


@pytest.mark.asyncio
async def test_sales_data_repr(db_session):
    """Test the SalesData __repr__ method."""
    now = datetime.now(UTC)
    record = SalesData(
        comp_id="C-REPR",
        source_file="repr.xlsx",
        property_address="456 Oak Ave",
        sale_date=date(2024, 1, 15),
        created_at=now,
        updated_at=now,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    r = repr(record)
    assert "SalesData" in r
    assert "C-REPR" in r
    assert "456 Oak Ave" in r
