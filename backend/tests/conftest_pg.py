"""
PostgreSQL-specific test fixtures (T-DEBT-015 / T-DEBT-023).

Provides an async engine and session factory that connect to a real PostgreSQL
instance.  All fixtures here are scoped to ``function`` so each test gets a
clean schema and a fresh engine (avoiding event-loop mismatch).

Configuration
-------------
Set the ``TEST_DATABASE_URL`` environment variable to a *synchronous*
PostgreSQL URL (e.g. ``postgresql://test_user:test_password@localhost:5432/test_db``).
The URL is automatically converted to an asyncpg URL.

When ``TEST_DATABASE_URL`` is unset every ``@pytest.mark.pg`` test is skipped
gracefully.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base

# Import all models so Base.metadata.create_all() creates every table.
import app.models  # noqa: F401

# ---------------------------------------------------------------------------
# URL resolution
# ---------------------------------------------------------------------------

_SYNC_URL: str | None = os.environ.get("TEST_DATABASE_URL")

# Convert ``postgresql://`` to ``postgresql+asyncpg://`` for the async engine.
_ASYNC_URL: str | None = (
    _SYNC_URL.replace("postgresql://", "postgresql+asyncpg://") if _SYNC_URL else None
)

# Guard: skip all PG tests when no database is configured.
pg_available = pytest.mark.skipif(
    _ASYNC_URL is None,
    reason="TEST_DATABASE_URL not set — PostgreSQL not available",
)


# ---------------------------------------------------------------------------
# Fixtures — fresh engine per test to avoid event-loop mismatch
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def pg_engine():
    """Create a fresh async PG engine per test (skip when unavailable)."""
    if _ASYNC_URL is None:
        pytest.skip("TEST_DATABASE_URL not set")

    engine = create_async_engine(
        _ASYNC_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=2,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def pg_session(pg_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create all tables, yield a session, then drop everything.

    Each test gets a fully clean schema — no leftover data.
    """
    # Create tables
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Yield session
    factory = async_sessionmaker(
        bind=pg_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with factory() as session:
        yield session

    # Tear down tables
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def pg_user(pg_session: AsyncSession):
    """Create a test user in the PG database."""
    from app.core.security import get_password_hash
    from app.models import User

    user = User(
        email="pg_test@example.com",
        hashed_password=get_password_hash("pgpassword123"),
        full_name="PG Test User",
        role="analyst",
        is_active=True,
        is_verified=True,
        department="Testing",
    )
    pg_session.add(user)
    await pg_session.commit()
    await pg_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def pg_property(pg_session: AsyncSession):
    """Create a test property in the PG database."""
    from app.models import Property

    prop = Property(
        name="PG Test Property",
        property_type="multifamily",
        address="456 Integration Ave",
        city="Phoenix",
        state="AZ",
        zip_code="85001",
        market="Phoenix Metro",
        year_built=2015,
        total_sf=75000,
        total_units=100,
        purchase_price=Decimal("15000000.00"),
        cap_rate=Decimal("6.250"),
        occupancy_rate=Decimal("93.50"),
    )
    pg_session.add(prop)
    await pg_session.commit()
    await pg_session.refresh(prop)
    return prop


@pytest_asyncio.fixture(scope="function")
async def pg_deal(pg_session: AsyncSession, pg_user):
    """Create a test deal in the PG database."""
    from app.models import Deal, DealStage

    deal = Deal(
        name="PG Test Deal #0001",
        deal_type="acquisition",
        stage=DealStage.ACTIVE_REVIEW,
        stage_order=0,
        assigned_user_id=pg_user.id,
        asking_price=Decimal("20000000.00"),
        offer_price=Decimal("18500000.00"),
        projected_irr=Decimal("17.500"),
        projected_coc=Decimal("7.500"),
        projected_equity_multiple=Decimal("2.05"),
        hold_period_years=5,
        initial_contact_date=date.today(),
        target_close_date=date(2026, 12, 31),
        source="Marcus & Millichap",
        priority="high",
        competition_level="medium",
    )
    pg_session.add(deal)
    await pg_session.commit()
    await pg_session.refresh(deal)
    return deal
