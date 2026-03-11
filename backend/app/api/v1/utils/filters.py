"""
Shared filter utilities for API endpoints.

Provides reusable helpers for common query filter patterns found across
sales_analysis, construction_pipeline, and other list endpoints:

- ``parse_csv_list``: Parse a comma-separated query string into a list.
- ``apply_numeric_range_filter``: Apply min/max integer or float filters.
- ``apply_date_range_filter``: Apply date_from/date_to filters.
- ``apply_search_filter``: Apply ILIKE search across multiple columns.
"""

from datetime import date
from typing import Any


def parse_csv_list(csv_string: str | None) -> list[str]:
    """Parse a comma-separated query parameter into a cleaned list of strings.

    Returns an empty list if the input is ``None`` or contains only whitespace.

    Example::

        parse_csv_list("Phoenix, Tempe, Mesa")
        # => ["Phoenix", "Tempe", "Mesa"]

        parse_csv_list(None)
        # => []
    """
    if not csv_string:
        return []
    return [s.strip() for s in csv_string.split(",") if s.strip()]


def apply_numeric_range_filter(
    stmt: Any,
    column: Any,
    *,
    min_val: int | float | None = None,
    max_val: int | float | None = None,
) -> Any:
    """Apply a min/max numeric range filter to a SQLAlchemy statement.

    Only adds WHERE clauses for non-None boundaries, so callers can pass
    through optional query params directly.

    Args:
        stmt: A SQLAlchemy select statement.
        column: The model column to filter on.
        min_val: Minimum value (inclusive), or None to skip.
        max_val: Maximum value (inclusive), or None to skip.

    Returns:
        The statement with additional WHERE clauses applied.
    """
    if min_val is not None:
        stmt = stmt.where(column >= min_val)
    if max_val is not None:
        stmt = stmt.where(column <= max_val)
    return stmt


def apply_date_range_filter(
    stmt: Any,
    column: Any,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
) -> Any:
    """Apply a date range filter to a SQLAlchemy statement.

    Args:
        stmt: A SQLAlchemy select statement.
        column: The model column to filter on (must be a Date or DateTime type).
        date_from: Start date (inclusive), or None to skip.
        date_to: End date (inclusive), or None to skip.

    Returns:
        The statement with additional WHERE clauses applied.
    """
    if date_from is not None:
        stmt = stmt.where(column >= date_from)
    if date_to is not None:
        stmt = stmt.where(column <= date_to)
    return stmt


def apply_search_filter(
    stmt: Any,
    search: str | None,
    columns: list[Any],
) -> Any:
    """Apply an ILIKE search across multiple columns using OR logic.

    Args:
        stmt: A SQLAlchemy select statement.
        search: The search string, or None to skip.
        columns: List of model columns to search across.

    Returns:
        The statement with a WHERE ... OR ... clause if search is provided.
    """
    if not search or not columns:
        return stmt

    from sqlalchemy import or_

    pattern = f"%{search}%"
    conditions = [col.ilike(pattern) for col in columns]
    return stmt.where(or_(*conditions))
