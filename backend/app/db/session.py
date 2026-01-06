"""
Database session configuration with async and sync support.

Provides both async and sync session factories for different use cases:
- AsyncSession: For async API endpoints (file monitor, etc.)
- Session: For sync CRUD operations and background tasks
"""

from collections.abc import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from app.core.config import settings

# Determine engine configuration based on database type
# SQLite doesn't support pool_size, max_overflow, pool_timeout
_is_sqlite = settings.database_url_async.startswith("sqlite")

if _is_sqlite:
    # SQLite configuration - use StaticPool for in-memory databases
    engine = create_async_engine(
        settings.database_url_async,
        echo=settings.DEBUG,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL/other configuration - use connection pooling
    engine = create_async_engine(
        settings.database_url_async,
        echo=settings.DEBUG,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        pool_pre_ping=True,  # Enable connection health checks
    )

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# ============================================================================
# Sync engine and session for CRUD operations and background tasks
# ============================================================================

if _is_sqlite:
    # SQLite sync configuration
    sync_engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL/other sync configuration
    sync_engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        pool_pre_ping=True,
    )

# Sync session factory
SessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.

    Usage:
        @app.get("/items")
        async def read_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db() -> Generator[Session, None, None]:
    """
    Dependency for getting sync database sessions.

    Use this for endpoints that call synchronous CRUD operations.

    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_sync_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# For testing - uses NullPool to avoid connection issues
def create_test_engine():
    """Create a test engine with NullPool for testing isolation."""
    return create_async_engine(
        settings.database_url_async,
        echo=True,
        poolclass=NullPool,
    )
