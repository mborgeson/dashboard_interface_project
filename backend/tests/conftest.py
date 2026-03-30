"""
Pytest fixtures and configuration for the test suite.
Provides async database sessions, test client, and sample data fixtures.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# =============================================================================
# Test Database Configuration (T-DEBT-023)
# =============================================================================
# SQLite in-memory for fast unit/API tests (~3000 tests, < 60s).
# Known limitations vs PostgreSQL:
#   1. No server_default=func.now() — fixtures must set created_at/updated_at
#      explicitly via datetime.now(UTC). See test_integration/test_pg_server_defaults.py.
#   2. No reliable begin_nested() (savepoints) with StaticPool — transaction
#      rollback tests live in test_integration/test_pg_transactions.py.
#   3. Timezone info stripped on round-trip — comparisons use
#      .replace(tzinfo=None). PG preserves timezone natively.
#   4. No ILIKE, percentile_cont, array_agg — PG-only query tests live in
#      test_integration/test_pg_queries.py.
#   5. ON CONFLICT (upsert) with named constraints unsupported — PG upsert
#      validated in test_integration/test_pg_transactions.py.
# StaticPool ensures all connections share the same in-memory database.
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.permissions import CurrentUser, Role, get_current_user
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Deal, DealStage, Property, User

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocalTest = async_sessionmaker(
    engine_test,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# =============================================================================
# Core Fixtures
# =============================================================================

# NOTE: Custom event_loop fixture removed - deprecated in pytest-asyncio 0.23+
# pytest-asyncio now manages the event loop automatically with asyncio_mode = auto
# See: https://pytest-asyncio.readthedocs.io/en/latest/concepts.html


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh database session for each test.
    Tables are created before and dropped after each test.
    """
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocalTest() as session:
        yield session

    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# Ensure proper cleanup of the test engine after all tests complete
@pytest.fixture(scope="session", autouse=True)
def cleanup_engine():
    """Clean up the async engine after all tests to prevent hanging."""
    yield
    # Force synchronous cleanup using a new event loop
    loop = asyncio.new_event_loop()
    try:
        # Set timeout for cleanup to prevent indefinite hanging
        loop.run_until_complete(asyncio.wait_for(engine_test.dispose(), timeout=10.0))
    except TimeoutError:
        import logging

        logging.warning("Engine disposal timed out after 10s, forcing close")
    except Exception as e:
        import logging

        logging.warning(f"Error during engine disposal: {e}")
    finally:
        # Clean up any remaining tasks
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()


@pytest.fixture(autouse=True)
def _clear_memory_cache():
    """
    Clear the in-memory cache between tests.

    The cache module uses a module-level dict (_memory_cache) as fallback
    when Redis is unavailable (always the case in tests). Without cleanup,
    a cached dashboard response from one test leaks into the next, causing
    flaky assertions on data counts.
    """
    from app.core.cache import _memory_cache

    _memory_cache.clear()

    yield

    _memory_cache.clear()


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """
    Reset rate limiter state between tests.

    This prevents rate limiting from affecting subsequent tests
    when multiple tests hit the same endpoints.
    """
    # Reset before each test to ensure clean state
    from app.middleware.rate_limiter import RateLimiter

    limiter = RateLimiter.get_instance()
    if limiter is not None:
        limiter.reset()

    yield

    # Also reset after each test
    limiter = RateLimiter.get_instance()
    if limiter is not None:
        limiter.reset()


@pytest.fixture(autouse=True)
def _clear_token_blacklist_state():
    """
    Clear token blacklist shared state between tests (T-DEBT-013).

    The in-memory blacklist is a module-level dict that persists across tests.
    Without cleanup, a token blacklisted in one test would affect subsequent
    tests, causing flaky failures or false passes.

    This fixture clears both the memory store and resets the Redis reference
    to ensure each test starts with a clean blacklist.
    """
    from app.core.token_blacklist import _memory_blacklist, token_blacklist

    _memory_blacklist.clear()
    token_blacklist._redis = None

    yield

    _memory_blacklist.clear()
    token_blacklist._redis = None


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async test client with database dependency override.
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# =============================================================================
# Auth Override Fixture (opt-in per test module)
# =============================================================================


@pytest.fixture
def auto_auth():
    """
    Override get_current_user to auto-authenticate as admin.
    Use in test modules for endpoints that now require auth.

    Usage: add `auto_auth` as a parameter to test functions, or use
    `pytestmark = pytest.mark.usefixtures("auto_auth")` at module level.
    """

    async def _override():
        return CurrentUser(
            id=1,
            email="test@example.com",
            role=Role.ADMIN,
            full_name="Test Admin",
            is_active=True,
        )

    app.dependency_overrides[get_current_user] = _override
    yield
    app.dependency_overrides.pop(get_current_user, None)


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        role="analyst",
        is_active=True,
        is_verified=True,
        department="Testing",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin test user."""
    user = User(
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword123"),
        full_name="Admin User",
        role="admin",
        is_active=True,
        is_verified=True,
        department="Executive",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_property(db_session: AsyncSession) -> Property:
    """Create a test property."""
    prop = Property(
        name="Test Property",
        property_type="multifamily",
        address="123 Test St",
        city="Phoenix",
        state="AZ",
        zip_code="85001",
        market="Phoenix Metro",
        year_built=2020,
        total_sf=50000,
        total_units=50,
        purchase_price=Decimal("10000000.00"),
        cap_rate=Decimal("6.500"),
        occupancy_rate=Decimal("95.00"),
    )
    db_session.add(prop)
    await db_session.commit()
    await db_session.refresh(prop)
    return prop


@pytest_asyncio.fixture
async def test_deal(db_session: AsyncSession, test_user: User) -> Deal:
    """Create a test deal."""
    deal = Deal(
        name="Test Deal #0001",
        deal_type="acquisition",
        stage=DealStage.ACTIVE_REVIEW,
        stage_order=0,
        assigned_user_id=test_user.id,
        asking_price=Decimal("15000000.00"),
        offer_price=Decimal("14000000.00"),
        projected_irr=Decimal("18.500"),
        projected_coc=Decimal("8.000"),
        projected_equity_multiple=Decimal("2.10"),
        hold_period_years=5,
        initial_contact_date=date.today(),
        target_close_date=date(2025, 6, 30),
        source="CBRE",
        priority="high",
        competition_level="medium",
    )
    db_session.add(deal)
    await db_session.commit()
    await db_session.refresh(deal)
    return deal


@pytest_asyncio.fixture
async def multiple_deals(db_session: AsyncSession, test_user: User) -> list[Deal]:
    """Create multiple test deals across different stages."""
    deals = []
    stages = [
        DealStage.INITIAL_REVIEW,
        DealStage.ACTIVE_REVIEW,
        DealStage.UNDER_CONTRACT,
        DealStage.CLOSED,
    ]

    for i, stage in enumerate(stages):
        deal = Deal(
            name=f"Deal #{i + 1:04d}",
            deal_type="acquisition",
            stage=stage,
            stage_order=i,
            assigned_user_id=test_user.id,
            asking_price=Decimal(str(10_000_000 + i * 5_000_000)),
            priority="medium",
        )
        db_session.add(deal)
        deals.append(deal)

    await db_session.commit()
    for deal in deals:
        await db_session.refresh(deal)
    return deals


# =============================================================================
# Authentication Helpers
# =============================================================================


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict:
    """
    Generate analyst authentication headers for API requests.

    Use for: GET endpoints, analyst-level POST/PUT (e.g., deal activity).
    For admin-level mutations (create/update/delete resources), use admin_auth_headers.
    """
    from app.core.security import create_access_token

    token = create_access_token(subject=str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_auth_headers(admin_user: User) -> dict:
    """
    Generate admin authentication headers for API requests.

    Use for: POST/PUT/DELETE on admin-only endpoints (user management,
    resource creation/deletion that requires require_manager).
    """
    from app.core.security import create_access_token

    token = create_access_token(subject=str(admin_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def viewer_user(db_session: AsyncSession) -> User:
    """Create a viewer (read-only) test user."""
    user = User(
        email="viewer@example.com",
        hashed_password=get_password_hash("viewerpassword123"),
        full_name="Viewer User",
        role="viewer",
        is_active=True,
        is_verified=True,
        department="Reporting",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def viewer_auth_headers(viewer_user: User) -> dict:
    """
    Generate viewer (read-only) authentication headers for API requests.

    Use for: Testing that viewer-level users are denied access to
    analyst/manager/admin endpoints (expect 403).
    """
    from app.core.security import create_access_token

    token = create_access_token(subject=str(viewer_user.id))
    return {"Authorization": f"Bearer {token}"}
