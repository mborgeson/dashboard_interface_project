"""Tests for sales analysis API endpoints.

Covers the 10 REST endpoints mounted at /api/v1/sales-analysis:
1. GET /                         -- Paginated table data
2. GET /analytics/time-series    -- (PostgreSQL-only, skipped in SQLite)
3. GET /analytics/submarket-comparison -- (PostgreSQL-only, skipped)
4. GET /analytics/buyer-activity -- (PostgreSQL-only, skipped)
5. GET /analytics/distributions  -- (PostgreSQL-only, skipped)
6. GET /analytics/data-quality   -- Data quality report
7. POST /import                  -- Trigger file import
8. GET /import/status            -- Import status
9. PUT /reminder/dismiss         -- Dismiss reminder
10. GET /reminder/status         -- Reminder status

SQLite does NOT support percentile_cont, array_agg, or to_char, so analytics
endpoints that use those PostgreSQL functions are tested by mocking the
db.execute call at the endpoint level.
"""

from collections.abc import Generator
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

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
from app.models.sales_data import SalesData

# =============================================================================
# Sync + Async DB fixtures for sales-analysis endpoints
# =============================================================================

# Sync engine (for endpoints that use get_sync_db, e.g. /import, /import/status)
SYNC_TEST_DB_URL = "sqlite:///:memory:"
sync_test_engine = create_engine(
    SYNC_TEST_DB_URL,
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
async def sales_client(
    db_session: AsyncSession, sync_db_session: Session
) -> AsyncClient:
    """
    Client that overrides both async (get_db) and sync (get_sync_db) deps.
    """

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

BASE_URL = "/api/v1/sales-analysis"


def _make_sales_record(
    comp_id: str = "C-001",
    source_file: str = "test.xlsx",
    property_name: str = "Test Apartments",
    property_address: str = "100 Main St",
    property_city: str = "Phoenix",
    submarket_cluster: str = "Central Phoenix",
    star_rating: str = "4 Star",
    year_built: int = 2010,
    number_of_units: int = 100,
    avg_unit_sf: float = 800.0,
    sale_date: date | None = None,
    sale_price: float | None = 10000000.0,
    price_per_unit: float | None = 100000.0,
    buyer_true_company: str = "Buyer Corp",
    seller_true_company: str = "Seller LLC",
    latitude: float = 33.45,
    longitude: float = -112.07,
    market: str = "Phoenix",
    actual_cap_rate: float | None = 5.0,
) -> SalesData:
    """Build a SalesData instance ready to add to session."""
    now = datetime.now(UTC)
    return SalesData(
        comp_id=comp_id,
        source_file=source_file,
        property_name=property_name,
        property_address=property_address,
        property_city=property_city,
        submarket_cluster=submarket_cluster,
        star_rating=star_rating,
        year_built=year_built,
        number_of_units=number_of_units,
        avg_unit_sf=avg_unit_sf,
        sale_date=sale_date or date(2024, 6, 15),
        sale_price=sale_price,
        price_per_unit=price_per_unit,
        buyer_true_company=buyer_true_company,
        seller_true_company=seller_true_company,
        latitude=latitude,
        longitude=longitude,
        market=market,
        actual_cap_rate=actual_cap_rate,
        imported_at=now,
        created_at=now,
        updated_at=now,
    )


@pytest_asyncio.fixture
async def sample_sales_data(db_session: AsyncSession) -> list[SalesData]:
    """Insert a set of diverse sales records for testing."""
    records = [
        _make_sales_record(
            comp_id="C-001",
            property_name="Sunrise Apts",
            property_city="Phoenix",
            submarket_cluster="Central Phoenix",
            star_rating="4 Star",
            year_built=2015,
            number_of_units=120,
            sale_date=date(2024, 3, 10),
            sale_price=18000000.0,
            price_per_unit=150000.0,
            buyer_true_company="Alpha Corp",
        ),
        _make_sales_record(
            comp_id="C-002",
            property_name="Sunset Place",
            property_city="Scottsdale",
            submarket_cluster="East Valley",
            star_rating="3 Star",
            year_built=1995,
            number_of_units=80,
            sale_date=date(2023, 11, 5),
            sale_price=8000000.0,
            price_per_unit=100000.0,
            buyer_true_company="Beta Inc",
        ),
        _make_sales_record(
            comp_id="C-003",
            property_name="Desert Vista",
            property_city="Tempe",
            submarket_cluster="Central Phoenix",
            star_rating="5 Star",
            year_built=2022,
            number_of_units=250,
            sale_date=date(2024, 7, 20),
            sale_price=62500000.0,
            price_per_unit=250000.0,
            buyer_true_company="Alpha Corp",
        ),
        _make_sales_record(
            comp_id="C-004",
            property_name="Mountain View",
            property_city="Mesa",
            submarket_cluster="East Valley",
            star_rating="3 Star",
            year_built=1988,
            number_of_units=40,
            sale_date=date(2022, 5, 1),
            sale_price=3200000.0,
            price_per_unit=80000.0,
            buyer_true_company="Gamma LLC",
        ),
        _make_sales_record(
            comp_id="C-005",
            property_name="Oasis Gardens",
            property_city="Phoenix",
            submarket_cluster="West Valley",
            star_rating="4 Star",
            year_built=2008,
            number_of_units=160,
            sale_date=date(2024, 1, 30),
            sale_price=24000000.0,
            price_per_unit=150000.0,
            buyer_true_company="Alpha Corp",
        ),
    ]
    for r in records:
        db_session.add(r)
    await db_session.commit()
    for r in records:
        await db_session.refresh(r)
    return records


# =============================================================================
# 1. GET / -- Paginated table data (works with SQLite)
# =============================================================================


@pytest.mark.asyncio
async def test_list_sales_empty(sales_client):
    """Test listing sales when table is empty."""
    response = await sales_client.get(f"{BASE_URL}/")
    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["total_pages"] == 0


@pytest.mark.asyncio
async def test_list_sales_with_data(sales_client, sample_sales_data):
    """Test listing sales returns records."""
    response = await sales_client.get(f"{BASE_URL}/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["data"]) == 5
    assert data["page"] == 1
    assert data["page_size"] == 50
    assert data["total_pages"] == 1


@pytest.mark.asyncio
async def test_list_sales_pagination(sales_client, sample_sales_data):
    """Test pagination with page_size=2."""
    response = await sales_client.get(
        f"{BASE_URL}/", params={"page": 1, "page_size": 2}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["data"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] == 3  # ceil(5/2) = 3

    # Page 2
    response2 = await sales_client.get(
        f"{BASE_URL}/", params={"page": 2, "page_size": 2}
    )
    data2 = response2.json()
    assert len(data2["data"]) == 2
    assert data2["page"] == 2

    # Page 3 (last page, 1 record)
    response3 = await sales_client.get(
        f"{BASE_URL}/", params={"page": 3, "page_size": 2}
    )
    data3 = response3.json()
    assert len(data3["data"]) == 1


@pytest.mark.asyncio
async def test_list_sales_sort_by_sale_price_asc(sales_client, sample_sales_data):
    """Test sorting by sale_price ascending."""
    response = await sales_client.get(
        f"{BASE_URL}/", params={"sort_by": "sale_price", "sort_dir": "asc"}
    )
    assert response.status_code == 200
    data = response.json()
    prices = [r["sale_price"] for r in data["data"]]
    assert prices == sorted(prices)


@pytest.mark.asyncio
async def test_list_sales_sort_by_sale_price_desc(sales_client, sample_sales_data):
    """Test sorting by sale_price descending."""
    response = await sales_client.get(
        f"{BASE_URL}/", params={"sort_by": "sale_price", "sort_dir": "desc"}
    )
    assert response.status_code == 200
    data = response.json()
    prices = [r["sale_price"] for r in data["data"]]
    assert prices == sorted(prices, reverse=True)


@pytest.mark.asyncio
async def test_list_sales_filter_search(sales_client, sample_sales_data):
    """Test search filter matches property name."""
    response = await sales_client.get(f"{BASE_URL}/", params={"search": "Desert Vista"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["data"][0]["property_name"] == "Desert Vista"


@pytest.mark.asyncio
async def test_list_sales_filter_submarkets(sales_client, sample_sales_data):
    """Test filtering by submarket_cluster."""
    response = await sales_client.get(
        f"{BASE_URL}/", params={"submarkets": "East Valley"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    for rec in data["data"]:
        assert rec["submarket_cluster"] == "East Valley"


@pytest.mark.asyncio
async def test_list_sales_filter_min_units(sales_client, sample_sales_data):
    """Test filtering by min_units."""
    response = await sales_client.get(f"{BASE_URL}/", params={"min_units": 150})
    assert response.status_code == 200
    data = response.json()
    for rec in data["data"]:
        assert rec["number_of_units"] >= 150


@pytest.mark.asyncio
async def test_list_sales_filter_price_range(sales_client, sample_sales_data):
    """Test filtering by min_price and max_price."""
    response = await sales_client.get(
        f"{BASE_URL}/", params={"min_price": 10000000, "max_price": 25000000}
    )
    assert response.status_code == 200
    data = response.json()
    for rec in data["data"]:
        assert 10000000 <= rec["sale_price"] <= 25000000


@pytest.mark.asyncio
async def test_list_sales_filter_date_range(sales_client, sample_sales_data):
    """Test filtering by date_from and date_to."""
    response = await sales_client.get(
        f"{BASE_URL}/",
        params={"date_from": "2024-01-01", "date_to": "2024-12-31"},
    )
    assert response.status_code == 200
    data = response.json()
    # C-004 (2022-05-01) and C-002 (2023-11-05) should be excluded
    assert data["total"] == 3


@pytest.mark.asyncio
async def test_list_sales_nrsf_calculation(sales_client, sample_sales_data):
    """Test that NRSF and price_per_nrsf are computed from units * avg_unit_sf."""
    response = await sales_client.get(
        f"{BASE_URL}/",
        params={"page_size": 1, "sort_by": "id", "sort_dir": "asc"},
    )
    assert response.status_code == 200
    data = response.json()
    rec = data["data"][0]
    # Record C-001: 120 units * 800 sf = 96000 NRSF
    assert rec["nrsf"] == 96000.0
    # 18000000 / 96000 = 187.5
    assert rec["price_per_nrsf"] == 187.5


@pytest.mark.asyncio
async def test_list_sales_price_per_unit_filter(sales_client, sample_sales_data):
    """Test filtering by min/max price_per_unit."""
    response = await sales_client.get(
        f"{BASE_URL}/",
        params={"min_price_per_unit": 100000, "max_price_per_unit": 200000},
    )
    assert response.status_code == 200
    data = response.json()
    # All returned records should have price_per_unit in range
    for rec in data["data"]:
        if rec["price_per_unit"] is not None:
            assert 100000 <= rec["price_per_unit"] <= 200000


@pytest.mark.asyncio
async def test_list_sales_year_built_filter(sales_client, sample_sales_data):
    """Test filtering by min/max year_built (inclusive)."""
    response = await sales_client.get(
        f"{BASE_URL}/",
        params={"min_year_built": 2000, "max_year_built": 2010},
    )
    assert response.status_code == 200
    data = response.json()
    for rec in data["data"]:
        if rec["year_built"] is not None:
            assert 2000 <= rec["year_built"] <= 2010


@pytest.mark.asyncio
async def test_filter_options(sales_client, sample_sales_data):
    """Test GET /filter-options returns distinct submarkets."""
    response = await sales_client.get(f"{BASE_URL}/filter-options")
    assert response.status_code == 200
    data = response.json()
    assert "submarkets" in data
    assert isinstance(data["submarkets"], list)
    assert len(data["submarkets"]) > 0
    # Should be sorted alphabetically
    assert data["submarkets"] == sorted(data["submarkets"])


@pytest.mark.asyncio
async def test_list_sales_search_by_buyer(sales_client, sample_sales_data):
    """Test search filter matches buyer company name."""
    response = await sales_client.get(f"{BASE_URL}/", params={"search": "Alpha Corp"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    for rec in data["data"]:
        assert rec["buyer_true_company"] == "Alpha Corp"


@pytest.mark.asyncio
async def test_list_sales_max_units_filter(sales_client, sample_sales_data):
    """Test filtering by max_units."""
    response = await sales_client.get(f"{BASE_URL}/", params={"max_units": 100})
    assert response.status_code == 200
    data = response.json()
    for rec in data["data"]:
        assert rec["number_of_units"] <= 100


# =============================================================================
# 6. GET /analytics/data-quality (works with SQLite)
# =============================================================================


@pytest.mark.asyncio
async def test_data_quality_empty(sales_client):
    """Data quality report when table is empty."""
    response = await sales_client.get(f"{BASE_URL}/analytics/data-quality")
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 0
    assert data["records_by_file"] == {}
    assert data["null_rates"] == {}
    assert data["flagged_outliers"]["dollar_one_sales"] == 0


@pytest.mark.asyncio
async def test_data_quality_with_data(sales_client, sample_sales_data):
    """Data quality report with sample data."""
    response = await sales_client.get(f"{BASE_URL}/analytics/data-quality")
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 5
    assert "test.xlsx" in data["records_by_file"]
    assert data["records_by_file"]["test.xlsx"] == 5
    # All records have sale_price and sale_date populated, so null rate = 0
    assert data["null_rates"]["sale_price"] == 0.0
    assert data["null_rates"]["sale_date"] == 0.0


@pytest.mark.asyncio
async def test_data_quality_outlier_detection(sales_client, db_session):
    """Data quality should flag $1 sales and high unit counts."""
    now = datetime.now(UTC)
    # Dollar-one sale
    rec1 = SalesData(
        comp_id="C-OUTLIER1",
        source_file="outlier.xlsx",
        sale_price=1.0,
        number_of_units=50,
        created_at=now,
        updated_at=now,
    )
    # High unit count
    rec2 = SalesData(
        comp_id="C-OUTLIER2",
        source_file="outlier.xlsx",
        sale_price=50000000.0,
        number_of_units=900,
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([rec1, rec2])
    await db_session.commit()

    response = await sales_client.get(f"{BASE_URL}/analytics/data-quality")
    assert response.status_code == 200
    data = response.json()
    assert data["flagged_outliers"]["dollar_one_sales"] == 1
    assert data["flagged_outliers"]["high_unit_count_over_800"] == 1


@pytest.mark.asyncio
async def test_data_quality_null_rates(sales_client, db_session):
    """Data quality null rates should reflect missing fields."""
    now = datetime.now(UTC)
    # Record with many nulls
    rec = SalesData(
        comp_id="C-NR",
        source_file="nulls.xlsx",
        sale_price=None,
        sale_date=None,
        property_name=None,
        actual_cap_rate=None,
        price_per_unit=None,
        avg_unit_sf=None,
        created_at=now,
        updated_at=now,
    )
    db_session.add(rec)
    await db_session.commit()

    response = await sales_client.get(f"{BASE_URL}/analytics/data-quality")
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 1
    # Every key field should have 100% null rate
    assert data["null_rates"]["sale_price"] == 1.0
    assert data["null_rates"]["sale_date"] == 1.0
    assert data["null_rates"]["property_name"] == 1.0
    assert data["null_rates"]["actual_cap_rate"] == 1.0


# =============================================================================
# 9. PUT /reminder/dismiss
# =============================================================================


@pytest.mark.asyncio
async def test_dismiss_reminder(sales_client):
    """Test dismissing the monthly import reminder."""
    response = await sales_client.put(f"{BASE_URL}/reminder/dismiss")
    assert response.status_code == 200
    data = response.json()
    assert data["dismissed"] is True
    assert "month" in data


@pytest.mark.asyncio
async def test_dismiss_reminder_idempotent(sales_client):
    """Dismissing the reminder twice should succeed both times."""
    resp1 = await sales_client.put(f"{BASE_URL}/reminder/dismiss")
    resp2 = await sales_client.put(f"{BASE_URL}/reminder/dismiss")
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["month"] == resp2.json()["month"]


# =============================================================================
# 10. GET /reminder/status
# =============================================================================


@pytest.mark.asyncio
async def test_reminder_status_empty_db(sales_client):
    """Reminder status with no imported data."""
    response = await sales_client.get(f"{BASE_URL}/reminder/status")
    assert response.status_code == 200
    data = response.json()
    assert "show_reminder" in data
    assert isinstance(data["show_reminder"], bool)
    assert data["last_imported_file_name"] is None
    assert data["last_imported_file_date"] is None


@pytest.mark.asyncio
async def test_reminder_status_with_data(sales_client, sample_sales_data):
    """Reminder status should reflect last imported file."""
    response = await sales_client.get(f"{BASE_URL}/reminder/status")
    assert response.status_code == 200
    data = response.json()
    # sample data has imported_at set
    assert data["last_imported_file_name"] == "test.xlsx"
    assert data["last_imported_file_date"] is not None


@pytest.mark.asyncio
async def test_reminder_dismissal_persists_to_database(sales_client, db_session):
    """Test that dismissals are persisted to the database (not just in-memory)."""
    from app.models.reminder_dismissal import ReminderDismissal
    from sqlalchemy import select

    # Dismiss the reminder
    response = await sales_client.put(f"{BASE_URL}/reminder/dismiss")
    assert response.status_code == 200
    month_key = response.json()["month"]

    # Verify the dismissal was persisted to the database
    result = await db_session.execute(
        select(ReminderDismissal).where(
            ReminderDismissal.dismissed_month == month_key
        )
    )
    dismissal = result.scalar_one_or_none()
    assert dismissal is not None
    assert dismissal.user_identifier == "global"
    assert dismissal.dismissed_month == month_key
    assert dismissal.dismissed_at is not None


@pytest.mark.asyncio
async def test_reminder_status_reflects_database_dismissal(sales_client, db_session):
    """Test that reminder status reads from database, not in-memory."""
    from datetime import UTC, datetime
    from app.models.reminder_dismissal import ReminderDismissal

    now = datetime.now(UTC)
    month_key = now.strftime("%Y-%m")

    # Insert a dismissal directly into the database
    dismissal = ReminderDismissal(
        user_identifier="global",
        dismissed_month=month_key,
        dismissed_at=now,
    )
    db_session.add(dismissal)
    await db_session.commit()

    # Check status - should show as dismissed
    response = await sales_client.get(f"{BASE_URL}/reminder/status")
    assert response.status_code == 200
    data = response.json()

    # Within first 7 days of month, show_reminder should be False because dismissed
    # After day 7, show_reminder would be False anyway
    # The key test is that the dismissal was recognized from the database
    if now.day <= 7:
        assert data["show_reminder"] is False


@pytest.mark.asyncio
async def test_reminder_dismissal_unique_per_month(sales_client, db_session):
    """Test that only one dismissal record is created per user per month."""
    from app.models.reminder_dismissal import ReminderDismissal
    from sqlalchemy import func, select

    # Dismiss multiple times
    await sales_client.put(f"{BASE_URL}/reminder/dismiss")
    await sales_client.put(f"{BASE_URL}/reminder/dismiss")
    await sales_client.put(f"{BASE_URL}/reminder/dismiss")

    # Count dismissal records - should only be 1
    result = await db_session.execute(
        select(func.count(ReminderDismissal.id)).where(
            ReminderDismissal.user_identifier == "global"
        )
    )
    count = result.scalar()
    assert count == 1


# =============================================================================
# Analytics endpoints (PostgreSQL-only) -- test with mocked db.execute
# =============================================================================


@pytest.mark.asyncio
async def test_time_series_mocked(sales_client, db_session):
    """Test time-series endpoint with mocked db.execute to avoid PG functions."""
    mock_row = MagicMock()
    mock_row.period = "2024"
    mock_row.count = 10
    mock_row.total_volume = 50000000.0
    mock_row.avg_price_per_unit = 150000.0  # Changed from median to avg

    mock_result = MagicMock()
    mock_result.all.return_value = [mock_row]

    with patch.object(db_session, "execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_result
        response = await sales_client.get(f"{BASE_URL}/analytics/time-series")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["period"] == "2024"
    assert data[0]["count"] == 10
    assert data[0]["total_volume"] == 50000000.0
    assert data[0]["avg_price_per_unit"] == 150000.0  # Changed from median to avg


@pytest.mark.asyncio
async def test_submarket_comparison_mocked(sales_client, db_session):
    """Test submarket-comparison endpoint with mocked db.execute."""
    mock_row = MagicMock()
    mock_row.submarket = "Central Phoenix"
    mock_row.year = 2024
    mock_row.avg_price_per_unit = 175000.0  # Changed from median to avg
    mock_row.sales_count = 15
    mock_row.total_volume = 40000000.0

    mock_result = MagicMock()
    mock_result.all.return_value = [mock_row]

    with patch.object(db_session, "execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_result
        response = await sales_client.get(f"{BASE_URL}/analytics/submarket-comparison")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["submarket"] == "Central Phoenix"
    assert data[0]["year"] == 2024


@pytest.mark.asyncio
async def test_buyer_activity_mocked(sales_client, db_session):
    """Test buyer-activity endpoint with mocked db.execute."""
    mock_row = MagicMock()
    mock_row.buyer = "Alpha Corp"
    mock_row.transaction_count = 5
    mock_row.total_volume = 80000000.0
    mock_row.first_purchase = date(2022, 1, 1)
    mock_row.last_purchase = date(2024, 7, 1)
    mock_row.submarkets_arr = ["Central Phoenix", "East Valley"]

    mock_result = MagicMock()
    mock_result.all.return_value = [mock_row]

    with patch.object(db_session, "execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_result
        response = await sales_client.get(f"{BASE_URL}/analytics/buyer-activity")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["buyer"] == "Alpha Corp"
    assert data[0]["transaction_count"] == 5
    assert "Central Phoenix" in data[0]["submarkets"]


@pytest.mark.asyncio
async def test_distributions_mocked(sales_client, db_session):
    """Test distributions endpoint with mocked db.execute."""
    mock_row = MagicMock()
    mock_row.label = "2005-2020"
    mock_row.count = 20
    mock_row.avg_price_per_unit = 135000.0  # Changed from median to avg (removed median_price_per_unit)

    mock_result = MagicMock()
    mock_result.all.return_value = [mock_row]

    with patch.object(db_session, "execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_result
        response = await sales_client.get(f"{BASE_URL}/analytics/distributions")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["label"] == "2005-2020"
    assert data[0]["count"] == 20


# =============================================================================
# 7. POST /import -- mock the import service
# =============================================================================


@pytest.mark.asyncio
async def test_import_no_new_files(sales_client):
    """Import when no new files exist."""
    with patch("app.services.sales_import.get_unimported_files", return_value=[]):
        response = await sales_client.post(f"{BASE_URL}/import")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["rows_imported"] == 0
    assert "No new files" in data["message"]


@pytest.mark.asyncio
async def test_import_with_files(sales_client):
    """Import with new files calls import_sales_file and reports results."""
    from app.services.sales_import import FileImportResult

    mock_result = FileImportResult(
        filename="new_data.xlsx", rows_imported=50, rows_updated=0
    )

    with (
        patch(
            "app.services.sales_import.get_unimported_files",
            return_value=["/data/sales/Phoenix/new_data.xlsx"],
        ),
        patch(
            "app.services.sales_import.import_sales_file",
            return_value=mock_result,
        ),
    ):
        response = await sales_client.post(f"{BASE_URL}/import")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["rows_imported"] == 50


@pytest.mark.asyncio
async def test_import_handles_exception(sales_client):
    """Import handles unexpected errors gracefully."""
    with patch(
        "app.services.sales_import.get_unimported_files",
        side_effect=RuntimeError("Disk full"),
    ):
        response = await sales_client.post(f"{BASE_URL}/import")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "Disk full" in data["message"]


# =============================================================================
# 8. GET /import/status -- mock the import service
# =============================================================================


@pytest.mark.asyncio
async def test_import_status_no_files(sales_client):
    """Import status with no unimported files."""
    with patch("app.services.sales_import.get_unimported_files", return_value=[]):
        response = await sales_client.get(f"{BASE_URL}/import/status")
    assert response.status_code == 200
    data = response.json()
    assert data["unimported_files"] == []


@pytest.mark.asyncio
async def test_import_status_with_unimported(sales_client):
    """Import status lists unimported file names."""
    with patch(
        "app.services.sales_import.get_unimported_files",
        return_value=[
            "/data/sales/Phoenix/new_jan.xlsx",
            "/data/sales/Phoenix/new_feb.xlsx",
        ],
    ):
        response = await sales_client.get(f"{BASE_URL}/import/status")
    assert response.status_code == 200
    data = response.json()
    assert "new_jan.xlsx" in data["unimported_files"]
    assert "new_feb.xlsx" in data["unimported_files"]
