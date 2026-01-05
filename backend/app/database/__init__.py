"""
Database seeding and data management module.

This module provides utilities for seeding the database with mock data
for development and testing environments.

Usage:
    python -m app.database.seed           # Seed database
    python -m app.database.seed --clear   # Clear seeded data
"""

# Lazy imports to avoid dependency issues before installation
__all__ = [
    "seed_database",
    "clear_database",
    "generate_property_data",
    "generate_deal_data",
]


def __getattr__(name: str):
    """Lazy import to avoid breaking when dependencies aren't installed."""
    if name in __all__:
        from app.database import seed

        return getattr(seed, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
