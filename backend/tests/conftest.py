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
# Test Database Configuration
# =============================================================================
# Use SQLite for fast in-memory testing
# StaticPool ensures all connections share the same in-memory database
from sqlalchemy.pool import StaticPool

from app.core.config import settings
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
        loop.run_until_complete(
            asyncio.wait_for(engine_test.dispose(), timeout=10.0)
        )
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
        stage=DealStage.UNDERWRITING,
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
    stages = [DealStage.LEAD, DealStage.UNDERWRITING, DealStage.DUE_DILIGENCE, DealStage.CLOSED]

    for i, stage in enumerate(stages):
        deal = Deal(
            name=f"Deal #{i+1:04d}",
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
    Generate authentication headers for API requests.
    NOTE: Adjust this based on your actual auth implementation.
    """
    from app.core.security import create_access_token
    token = create_access_token(subject=str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_auth_headers(admin_user: User) -> dict:
    """Generate admin authentication headers."""
    from app.core.security import create_access_token
    token = create_access_token(subject=str(admin_user.id))
    return {"Authorization": f"Bearer {token}"}
