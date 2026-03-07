"""
Tests for property financial_data lazy enrichment.

Verifies that GET /properties/dashboard/{id} and the dashboard list endpoint
correctly populate financial_data from extracted_values when the JSON column
is NULL, and gracefully return empty financial fields when no extracted_values
exist.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import Property
from app.models.extraction import ExtractedValue, ExtractionRun


# ---------------------------------------------------------------------------
# Helpers — create extracted_values rows via sync session (extraction models
# use PG_UUID which works transparently on SQLite).
# ---------------------------------------------------------------------------

SYNC_TEST_URL = "sqlite:///:memory:"
_sync_engine = create_engine(
    SYNC_TEST_URL,
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
_SyncSession = sessionmaker(
    bind=_sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


def _make_extracted_value(
    run_id,
    property_name: str,
    field_name: str,
    value_numeric: float | None = None,
    value_text: str | None = None,
    property_id: int | None = None,
) -> dict:
    """Return a dict suitable for constructing an ExtractedValue."""
    return {
        "id": uuid4(),
        "extraction_run_id": run_id,
        "property_id": property_id,
        "property_name": property_name,
        "field_name": field_name,
        "value_numeric": Decimal(str(value_numeric)) if value_numeric is not None else None,
        "value_text": value_text or (str(value_numeric) if value_numeric is not None else None),
        "is_error": False,
    }


# =============================================================================
# Test: GET /properties/dashboard/{id} returns populated financial_data
# =============================================================================


@pytest.mark.asyncio
async def test_dashboard_detail_enriches_financial_data(
    client, db_session: AsyncSession, auth_headers
):
    """
    When a property has extracted_values but NULL financial_data,
    GET /properties/dashboard/{id} should lazily enrich and return
    populated financial fields.
    """
    # 1. Create a property with NO financial_data
    prop = Property(
        name="Enrichment Test Property",
        property_type="multifamily",
        address="100 Enrich Ave",
        city="Phoenix",
        state="AZ",
        zip_code="85001",
        total_units=120,
        financial_data=None,  # explicitly NULL
    )
    db_session.add(prop)
    await db_session.commit()
    await db_session.refresh(prop)

    # 2. Create an extraction run and extracted_values via the async session
    run = ExtractionRun(
        id=uuid4(),
        status="completed",
        trigger_type="manual",
        files_discovered=1,
        files_processed=1,
        files_failed=0,
    )
    db_session.add(run)
    await db_session.flush()

    # Insert key financial extracted values
    extracted_fields = [
        ("PURCHASE_PRICE", 15_000_000.0),
        ("GOING_IN_CAP_RATE", 0.055),
        ("LOAN_AMOUNT", 10_500_000.0),
        ("INTEREST_RATE", 0.065),
        ("LEVERED_RETURNS_IRR", 0.185),
        ("LEVERED_RETURNS_MOIC", 2.1),
        ("UNLEVERED_RETURNS_IRR", 0.12),
        ("UNLEVERED_RETURNS_MOIC", 1.8),
        ("NOI", 825_000.0),
        ("EFFECTIVE_GROSS_INCOME", 1_200_000.0),
        ("TOTAL_EXPENSES", 375_000.0),
        ("AVG_RENT_PER_UNIT", 1450.0),
        ("OCCUPANCY_PERCENT", 0.945),
    ]

    for field_name, value in extracted_fields:
        ev = ExtractedValue(
            **_make_extracted_value(
                run.id,
                "Enrichment Test Property",
                field_name,
                value_numeric=value,
                property_id=prop.id,
            )
        )
        db_session.add(ev)

    await db_session.commit()

    # 3. Hit the dashboard detail endpoint
    response = await client.get(
        f"/api/v1/properties/dashboard/{prop.id}",
        headers=auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200
    data = response.json()

    # 4. Verify financial fields are populated (not all zeros/nulls)
    assert data["name"] == "Enrichment Test Property"

    # Acquisition data
    acq = data.get("acquisition", {})
    assert acq.get("purchasePrice") == 15_000_000.0

    # Financing data
    fin = data.get("financing", {})
    assert fin.get("loanAmount") == 10_500_000.0
    assert fin.get("interestRate") == pytest.approx(0.065, abs=1e-4)

    # Returns / performance data
    perf = data.get("performance", {})
    assert perf.get("leveredIrr") == pytest.approx(0.185, abs=1e-4)
    assert perf.get("leveredMoic") == pytest.approx(2.1, abs=0.01)
    assert perf.get("unleveredIrr") == pytest.approx(0.12, abs=1e-4)
    assert perf.get("unleveredMoic") == pytest.approx(1.8, abs=0.01)

    # Valuation cap rate
    val = data.get("valuation", {})
    assert val.get("capRate") == pytest.approx(0.055, abs=1e-3)

    # Operations
    ops = data.get("operations", {})
    assert ops.get("averageRent") == pytest.approx(1450.0, abs=1)


# =============================================================================
# Test: GET /properties/dashboard/{id} with NO extracted_values
# =============================================================================


@pytest.mark.asyncio
async def test_dashboard_detail_no_extracted_values(
    client, db_session: AsyncSession, auth_headers
):
    """
    When a property has NULL financial_data and NO extracted_values exist,
    the endpoint should still return a valid response with zeroed/null
    financial fields — no crash.
    """
    prop = Property(
        name="Empty Financial Property",
        property_type="multifamily",
        address="200 Empty Ln",
        city="Tempe",
        state="AZ",
        zip_code="85281",
        total_units=50,
        financial_data=None,
    )
    db_session.add(prop)
    await db_session.commit()
    await db_session.refresh(prop)

    response = await client.get(
        f"/api/v1/properties/dashboard/{prop.id}",
        headers=auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "Empty Financial Property"

    # Financial fields should be zero or null — not crash
    acq = data.get("acquisition", {})
    assert acq.get("purchasePrice") == 0 or acq.get("purchasePrice") is None

    perf = data.get("performance", {})
    assert perf.get("leveredIrr") == 0 or perf.get("leveredIrr") is None


# =============================================================================
# Test: GET /properties/dashboard/{id} with EXISTING financial_data skips
# =============================================================================


@pytest.mark.asyncio
async def test_dashboard_detail_existing_financial_data_not_overwritten(
    client, db_session: AsyncSession, auth_headers
):
    """
    When a property already has financial_data populated, the endpoint
    should NOT re-enrich — it returns the cached data as-is.
    """
    existing_fd = {
        "acquisition": {"purchasePrice": 20_000_000.0},
        "financing": {"loanAmount": 14_000_000.0},
        "returns": {"leveredIrr": 0.22, "lpIrr": 0.22},
        "operations": {"noiYear1": 1_100_000.0},
    }

    prop = Property(
        name="Pre-Filled Property",
        property_type="multifamily",
        address="300 Prefilled Blvd",
        city="Mesa",
        state="AZ",
        zip_code="85201",
        total_units=200,
        purchase_price=Decimal("20000000.00"),
        financial_data=existing_fd,
    )
    db_session.add(prop)
    await db_session.commit()
    await db_session.refresh(prop)

    response = await client.get(
        f"/api/v1/properties/dashboard/{prop.id}",
        headers=auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200
    data = response.json()

    # Should use the pre-existing data, not zeros
    acq = data.get("acquisition", {})
    assert acq.get("purchasePrice") == 20_000_000.0

    perf = data.get("performance", {})
    assert perf.get("leveredIrr") == pytest.approx(0.22, abs=1e-4)


# =============================================================================
# Test: Dashboard list endpoint also enriches
# =============================================================================


@pytest.mark.asyncio
async def test_dashboard_list_enriches_missing_financial_data(
    client, db_session: AsyncSession, auth_headers
):
    """
    GET /properties/dashboard should enrich properties in the list
    that have NULL financial_data.
    """
    # Property with no financial_data
    prop = Property(
        name="List Enrich Property",
        property_type="multifamily",
        address="400 List Ave",
        city="Phoenix",
        state="AZ",
        zip_code="85001",
        total_units=80,
        financial_data=None,
    )
    db_session.add(prop)
    await db_session.commit()
    await db_session.refresh(prop)

    # Add extracted values
    run = ExtractionRun(
        id=uuid4(),
        status="completed",
        trigger_type="manual",
        files_discovered=1,
        files_processed=1,
        files_failed=0,
    )
    db_session.add(run)
    await db_session.flush()

    ev = ExtractedValue(
        **_make_extracted_value(
            run.id,
            "List Enrich Property",
            "PURCHASE_PRICE",
            value_numeric=8_000_000.0,
            property_id=prop.id,
        )
    )
    db_session.add(ev)
    await db_session.commit()

    response = await client.get(
        "/api/v1/properties/dashboard",
        headers=auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200
    data = response.json()

    # Find our property in the list
    props = data.get("properties", [])
    target = next((p for p in props if p["name"] == "List Enrich Property"), None)
    assert target is not None

    acq = target.get("acquisition", {})
    assert acq.get("purchasePrice") == 8_000_000.0


# =============================================================================
# Test: Enrichment caches — second call uses financial_data column
# =============================================================================


@pytest.mark.asyncio
async def test_enrichment_persists_to_database(
    client, db_session: AsyncSession, auth_headers
):
    """
    After lazy enrichment, the financial_data column should be persisted
    so subsequent queries don't need to re-query extracted_values.
    """
    prop = Property(
        name="Cache Test Property",
        property_type="multifamily",
        address="500 Cache Dr",
        city="Scottsdale",
        state="AZ",
        zip_code="85251",
        total_units=60,
        financial_data=None,
    )
    db_session.add(prop)
    await db_session.commit()
    await db_session.refresh(prop)

    run = ExtractionRun(
        id=uuid4(),
        status="completed",
        trigger_type="manual",
        files_discovered=1,
        files_processed=1,
        files_failed=0,
    )
    db_session.add(run)
    await db_session.flush()

    ev = ExtractedValue(
        **_make_extracted_value(
            run.id,
            "Cache Test Property",
            "LEVERED_RETURNS_IRR",
            value_numeric=0.175,
            property_id=prop.id,
        )
    )
    db_session.add(ev)
    await db_session.commit()

    # First call triggers enrichment
    resp1 = await client.get(
        f"/api/v1/properties/dashboard/{prop.id}",
        headers=auth_headers,
        follow_redirects=True,
    )
    assert resp1.status_code == 200

    # Verify the DB column was updated
    await db_session.refresh(prop)
    assert prop.financial_data is not None
    assert prop.financial_data.get("returns", {}).get("leveredIrr") == pytest.approx(
        0.175, abs=1e-4
    )


# =============================================================================
# Test: Auth guard on dashboard detail
# =============================================================================


@pytest.mark.asyncio
async def test_dashboard_detail_requires_auth(client, db_session):
    """GET /properties/dashboard/{id} without auth should return 401."""
    response = await client.get(
        "/api/v1/properties/dashboard/1",
        follow_redirects=True,
    )
    assert response.status_code == 401
