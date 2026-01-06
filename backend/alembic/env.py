"""
Alembic migration environment configuration.
"""
import asyncio
from logging.config import fileConfig
from urllib.parse import unquote

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Import models and settings
from app.core.config import settings
from app.db.base import Base

# Underwriting models

# Import all models to ensure they're registered with Base.metadata
# Core models

# Alembic Config object
config = context.config

# Get database URL and decode any URL-encoded characters
# The .env file may have URL-encoded special characters like %21 for !
db_url = unquote(settings.database_url_async)

# Set URL in config for offline mode (escape % for ConfigParser)
config.set_main_option("sqlalchemy.url", db_url.replace("%", "%%"))

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add model's MetaData object for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in 'online' mode with async support.

    In this scenario we need to create an Engine and associate a
    connection with the context.
    """
    # Determine engine configuration based on database type
    # SQLite doesn't support pool_size, max_overflow, pool_timeout
    _is_sqlite = db_url.startswith("sqlite")

    if _is_sqlite:
        # SQLite configuration - use StaticPool for in-memory databases
        from sqlalchemy.pool import StaticPool
        connectable = create_async_engine(
            db_url,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
    else:
        # PostgreSQL/other configuration - use NullPool for migrations
        connectable = create_async_engine(
            db_url,
            poolclass=pool.NullPool,
        )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
