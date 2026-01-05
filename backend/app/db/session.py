"""
Database session configuration with async support.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
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

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
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


# For testing - uses NullPool to avoid connection issues
def create_test_engine():
    """Create a test engine with NullPool for testing isolation."""
    return create_async_engine(
        settings.database_url_async,
        echo=True,
        poolclass=NullPool,
    )
