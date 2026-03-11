"""
PostgreSQL-specific test fixtures (T-DEBT-015 / T-DEBT-023).

Provides an async engine and session factory that connect to a real PostgreSQL
instance.  All fixtures here are scoped to ``function`` so each test gets a
clean schema.

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

# ---------------------------------------------------------------------------
# URL resolution
# ---------------------------------------------------------------------------

_SYNC_URL: str | None = os.environ.get("TEST_DATABASE_URL")

# Convert ``postgresql://`` to ``postgresql+asyncpg://`` for the async engine.
_ASYNC_URL: str | None = (
    _SYNC_URL.replace("postgresql://", "postgresql+asyncpg://")
    if _SYNC_URL
    else None
)

# Guard: skip all PG tests when no database is configured.
pg_available = pytest.mark.skipif(
    _ASYNC_URL is None,
    reason="TEST_DATABASE_URL not set — PostgreSQL not available",
)

# ---------------------------------------------------------------------------
# Engine & session factory (module-level singletons, created lazily)
# ---------------------------------------------------------------------------

_pg_engine = None
_PGSessionLocal = None


def _get_pg_engine():
    """Return (and cache) the async PG engine."""
    global _pg_engine  # noqa: PLW0603
    if _pg_engine is None and _ASYNC_URL is not None:
        _pg_engine = create_async_engine(
            _ASYNC_URL,
            echo=False,
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=2,
        )
    return _pg_engine


def _get_pg_session_factory():
    """Return (and cache) the async session factory for PG."""
    global _PGSessionLocal  # noqa: PLW0603
    if _PGSessionLocal is None:
        engine = _get_pg_engine()
        if engine is not None:
            _PGSessionLocal = async_sessionmaker(
                bind=engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )
    return _PGSessionLocal


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def pg_engine():
    """Yield the async PG engine (skip when unavailable)."""
    engine = _get_pg_engine()
    if engine is None:
        pytest.skip("TEST_DATABASE_URL not set")
    yield engine


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
    factory = _get_pg_session_factory()
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


# ---------------------------------------------------------------------------
# Session-scoped cleanup
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def cleanup_pg_engine():
    """Dispose the PG engine after the entire test session."""
    yield
    import asyncio

    engine = _get_pg_engine()
    if engine is not None:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(asyncio.wait_for(engine.dispose(), timeout=10.0))
        except (TimeoutError, Exception):
            pass
        finally:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            loop.close()
