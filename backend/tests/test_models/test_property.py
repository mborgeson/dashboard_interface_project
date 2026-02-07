"""Tests for the Property model."""

from decimal import Decimal

import pytest

from app.models import Property


@pytest.mark.asyncio
async def test_create_property(db_session):
    """Test creating a new property."""
    prop = Property(
        name="Downtown Office Tower",
        property_type="office",
        address="456 Main Street",
        city="Los Angeles",
        state="CA",
        zip_code="90001",
        market="LA Metro",
        year_built=2015,
        total_sf=100000,
        purchase_price=Decimal("50000000.00"),
        cap_rate=Decimal("5.750"),
    )
    db_session.add(prop)
    await db_session.commit()
    await db_session.refresh(prop)

    assert prop.id is not None
    assert prop.name == "Downtown Office Tower"
    assert prop.property_type == "office"
    assert prop.city == "Los Angeles"


@pytest.mark.asyncio
async def test_property_types(db_session):
    """Test various property types."""
    types = ["multifamily", "office", "retail", "industrial", "mixed-use", "hotel"]

    for ptype in types:
        prop = Property(
            name=f"Test {ptype.title()}",
            property_type=ptype,
            address="123 Test St",
            city="Phoenix",
            state="AZ",
            zip_code="85001",
        )
        db_session.add(prop)

    await db_session.commit()


@pytest.mark.asyncio
async def test_property_price_per_unit(db_session):
    """Test the price_per_unit computed property."""
    prop = Property(
        name="Multifamily Test",
        property_type="multifamily",
        address="789 Unit Ave",
        city="Dallas",
        state="TX",
        zip_code="75201",
        total_units=100,
        purchase_price=Decimal("20000000.00"),
    )
    db_session.add(prop)
    await db_session.commit()
    await db_session.refresh(prop)

    # 20M / 100 units = 200K per unit
    assert prop.price_per_unit == Decimal("200000.00")


@pytest.mark.asyncio
async def test_property_price_per_sf(db_session):
    """Test the price_per_sf computed property."""
    prop = Property(
        name="Office Test",
        property_type="office",
        address="101 Corporate Dr",
        city="Chicago",
        state="IL",
        zip_code="60601",
        total_sf=50000,
        purchase_price=Decimal("15000000.00"),
    )
    db_session.add(prop)
    await db_session.commit()
    await db_session.refresh(prop)

    # 15M / 50K sf = 300 per sf
    assert prop.price_per_sf == Decimal("300.00")


@pytest.mark.asyncio
async def test_property_without_price_calculations(db_session):
    """Test that price calculations return None when data is missing."""
    prop = Property(
        name="Incomplete Property",
        property_type="industrial",
        address="555 Warehouse Rd",
        city="Denver",
        state="CO",
        zip_code="80201",
    )
    db_session.add(prop)
    await db_session.commit()
    await db_session.refresh(prop)

    assert prop.price_per_unit is None
    assert prop.price_per_sf is None


@pytest.mark.asyncio
async def test_property_fixture(test_property):
    """Test that the test_property fixture works."""
    assert test_property.id is not None
    assert test_property.name == "Test Property"
    assert test_property.city == "Phoenix"
    assert test_property.property_type == "multifamily"


@pytest.mark.asyncio
async def test_property_repr(test_property):
    """Test the Property __repr__ method."""
    assert "<Property" in repr(test_property)
    assert test_property.city in repr(test_property)
    assert test_property.state in repr(test_property)
