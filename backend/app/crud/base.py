"""
Base CRUD class with common database operations.
"""

from __future__ import annotations

import math
from datetime import datetime
from decimal import Decimal
from typing import Any, Generic, TypeVar

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.schemas.pagination import (
    CursorPaginationParams,
    decode_cursor,
    encode_cursor,
)

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class PaginatedResult(Generic[ModelType]):
    """Container for paginated query results.

    Attributes:
        items: List of model instances for the current page.
        total: Total number of matching records.
        page: Current page number (1-indexed).
        per_page: Number of items per page.
        pages: Total number of pages.
        has_next: Whether there is a next page.
        has_prev: Whether there is a previous page.
    """

    __slots__ = ("items", "total", "page", "per_page", "pages", "has_next", "has_prev")

    def __init__(
        self,
        items: list[ModelType],
        total: int,
        page: int,
        per_page: int,
    ) -> None:
        self.items = items
        self.total = total
        self.page = page
        self.per_page = per_page
        self.pages = math.ceil(total / per_page) if per_page > 0 else 0
        self.has_next = page < self.pages
        self.has_prev = page > 1

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (useful for API responses)."""
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "per_page": self.per_page,
            "pages": self.pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
        }


class CursorPaginatedResult(Generic[ModelType]):
    """Container for cursor-paginated query results.

    Attributes:
        items: List of model instances for the current page.
        next_cursor: Opaque cursor for the next page (None at end).
        prev_cursor: Opaque cursor for the previous page (None on first page).
        has_more: Whether more items exist beyond the current page.
        total: Total count of matching records (None if not requested).
    """

    __slots__ = ("items", "next_cursor", "prev_cursor", "has_more", "total")

    def __init__(
        self,
        items: list[ModelType],
        next_cursor: str | None = None,
        prev_cursor: str | None = None,
        has_more: bool = False,
        total: int | None = None,
    ) -> None:
        self.items = items
        self.next_cursor = next_cursor
        self.prev_cursor = prev_cursor
        self.has_more = has_more
        self.total = total

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (useful for API responses)."""
        return {
            "items": self.items,
            "next_cursor": self.next_cursor,
            "prev_cursor": self.prev_cursor,
            "has_more": self.has_more,
            "total": self.total,
        }


def _has_soft_delete(model: type) -> bool:
    """Check if a model has soft-delete columns."""
    return hasattr(model, "is_deleted") and hasattr(model, "deleted_at")


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base class for CRUD operations.

    Provides:
        - get: Get single record by ID (excludes soft-deleted by default)
        - get_multi: Get multiple records with pagination (excludes soft-deleted)
        - create: Create new record
        - update: Update existing record
        - remove: Soft-delete record (if model supports it), otherwise hard delete
        - restore: Restore a soft-deleted record
        - count: Count records with optional filters (excludes soft-deleted)
    """

    def __init__(self, model: type[ModelType]):
        """
        Initialize CRUD with SQLAlchemy model.

        Args:
            model: SQLAlchemy model class
        """
        self.model = model

    def _apply_soft_delete_filter(
        self, query: Any, *, include_deleted: bool = False
    ) -> Any:
        """Apply soft-delete filter if the model supports it."""
        if not include_deleted and _has_soft_delete(self.model):
            query = query.where(self.model.is_deleted.is_(False))  # type: ignore[attr-defined]
        return query

    async def get(
        self,
        db: AsyncSession,
        id: Any,
        *,
        include_deleted: bool = False,
    ) -> ModelType | None:
        """Get a single record by ID, excluding soft-deleted by default."""
        query = select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = None,
        order_desc: bool = True,
        include_deleted: bool = False,
    ) -> list[ModelType]:
        """Get multiple records with pagination, excluding soft-deleted by default."""
        query = select(self.model)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)

        if order_by and hasattr(self.model, order_by):
            col = getattr(self.model, order_by)
            query = query.order_by(col.desc() if order_desc else col.asc())

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def create(
        self, db: AsyncSession, *, obj_in: CreateSchemaType | dict[str, Any]
    ) -> ModelType:
        """Create a new record."""
        if isinstance(obj_in, dict):
            obj_in_data = obj_in
        else:
            obj_in_data = obj_in.model_dump(exclude_unset=True)

        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        """Update an existing record."""
        obj_data = jsonable_encoder(db_obj)

        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, *, id: Any) -> ModelType | None:
        """
        Soft-delete a record by ID if the model supports soft-delete.

        Falls back to hard delete for models without SoftDeleteMixin.
        """
        obj = await self.get(db, id, include_deleted=False)
        if not obj:
            return None

        if _has_soft_delete(self.model):
            obj.soft_delete()  # type: ignore[attr-defined]
            db.add(obj)
            await db.commit()
            await db.refresh(obj)
        else:
            await db.delete(obj)
            await db.commit()
        return obj

    async def restore(self, db: AsyncSession, *, id: Any) -> ModelType | None:
        """
        Restore a soft-deleted record by ID.

        Returns the restored record, or None if not found or not deleted.
        Raises ValueError if the model does not support soft-delete.
        """
        if not _has_soft_delete(self.model):
            raise ValueError(f"{self.model.__name__} does not support soft-delete")

        # Fetch including deleted records
        obj = await self.get(db, id, include_deleted=True)
        if not obj:
            return None

        if not obj.is_deleted:  # type: ignore[attr-defined]
            return obj  # Already active, nothing to restore

        obj.restore()  # type: ignore[attr-defined]
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj

    async def count(
        self,
        db: AsyncSession,
        *,
        filters: dict[str, Any] | None = None,
        include_deleted: bool = False,
    ) -> int:
        """Count records with optional filters, excluding soft-deleted by default."""
        query = select(func.count()).select_from(self.model)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.where(getattr(self.model, field) == value)

        result = await db.execute(query)
        return result.scalar() or 0

    # ------------------------------------------------------------------
    # Reusable pagination, ordering, and filtered-query helpers
    # ------------------------------------------------------------------

    def _apply_ordering(
        self,
        query: Any,
        order_by: str | None = None,
        order_desc: bool = True,
    ) -> Any:
        """Apply column-based ordering to a query.

        Only applies the order clause when *order_by* names a valid column
        on the model, preventing AttributeError on invalid column names.
        """
        if order_by and hasattr(self.model, order_by):
            col = getattr(self.model, order_by)
            query = query.order_by(col.desc() if order_desc else col.asc())
        return query

    async def count_where(
        self,
        db: AsyncSession,
        *,
        conditions: list[Any] | None = None,
        include_deleted: bool = False,
    ) -> int:
        """Count records matching arbitrary SQLAlchemy filter conditions.

        This avoids the need for each subclass to repeat the
        ``select(func.count()).select_from(Model)`` boilerplate.

        Args:
            db: Async database session.
            conditions: List of SQLAlchemy ``where`` clause expressions
                (e.g. ``[Deal.stage == DealStage.ACTIVE_REVIEW]``).
            include_deleted: Include soft-deleted records.
        """
        query = select(func.count()).select_from(self.model)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)

        for cond in conditions or []:
            query = query.where(cond)

        result = await db.execute(query)
        return result.scalar() or 0

    async def get_multi_ordered(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = None,
        order_desc: bool = True,
        conditions: list[Any] | None = None,
        include_deleted: bool = False,
    ) -> list[ModelType]:
        """Fetch multiple records with optional filters and ordering.

        A more flexible version of ``get_multi`` that accepts arbitrary
        SQLAlchemy filter conditions rather than only ``skip``/``limit``.

        Args:
            db: Async database session.
            skip: Number of records to skip (offset).
            limit: Maximum number of records to return.
            order_by: Model column name to order by.
            order_desc: If True, order descending; ascending otherwise.
            conditions: List of SQLAlchemy ``where`` clause expressions.
            include_deleted: Include soft-deleted records.
        """
        query = select(self.model)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)

        for cond in conditions or []:
            query = query.where(cond)

        query = self._apply_ordering(query, order_by=order_by, order_desc=order_desc)
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_paginated(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        per_page: int = 20,
        order_by: str | None = None,
        order_desc: bool = True,
        conditions: list[Any] | None = None,
        include_deleted: bool = False,
    ) -> PaginatedResult[ModelType]:
        """Fetch a page of records with total count and pagination metadata.

        Combines ``get_multi_ordered`` and ``count_where`` into a single
        call that returns a ``PaginatedResult`` containing ``items``,
        ``total``, ``page``, ``per_page``, ``pages``, ``has_next``, and
        ``has_prev``.

        Args:
            db: Async database session.
            page: 1-indexed page number.
            per_page: Number of items per page (clamped to >= 1).
            order_by: Model column name to order by.
            order_desc: If True, order descending; ascending otherwise.
            conditions: List of SQLAlchemy ``where`` clause expressions.
            include_deleted: Include soft-deleted records.
        """
        per_page = max(per_page, 1)
        page = max(page, 1)
        skip = (page - 1) * per_page

        items = await self.get_multi_ordered(
            db,
            skip=skip,
            limit=per_page,
            order_by=order_by,
            order_desc=order_desc,
            conditions=conditions,
            include_deleted=include_deleted,
        )

        total = await self.count_where(
            db,
            conditions=conditions,
            include_deleted=include_deleted,
        )

        return PaginatedResult(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
        )

    # ------------------------------------------------------------------
    # Cursor-based pagination
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_sort_value(raw: Any, col: Any) -> Any:
        """Coerce a decoded cursor sort-value to match the column type.

        JSON round-tripping converts datetimes to ISO strings and Decimals
        to strings.  This restores the original Python type so SQLAlchemy
        comparisons work correctly.
        """
        if raw is None:
            return None

        col_type = getattr(col, "type", None)
        if col_type is None:
            return raw

        type_name = type(col_type).__name__

        if type_name in ("DateTime", "TIMESTAMP"):
            if isinstance(raw, str):
                # Handle ISO format with or without timezone
                return datetime.fromisoformat(raw)
            return raw

        if type_name in ("Numeric", "DECIMAL", "Float"):
            if isinstance(raw, str):
                return Decimal(raw)
            return raw

        if type_name in ("Integer", "BigInteger", "SmallInteger"):
            return int(raw)

        return raw

    async def get_cursor_paginated(
        self,
        db: AsyncSession,
        *,
        params: CursorPaginationParams,
        order_by: str = "id",
        order_desc: bool = True,
        conditions: list[Any] | None = None,
        include_deleted: bool = False,
        include_total: bool = True,
    ) -> CursorPaginatedResult[ModelType]:
        """Fetch a page of records using cursor-based pagination.

        The cursor encodes the value of the sort column and the row ID for
        deterministic keyset pagination.  This method:

        1. Decodes the incoming cursor (if any).
        2. Builds a keyset ``WHERE`` clause that skips to the correct
           position without an ``OFFSET``.
        3. Fetches ``limit + 1`` rows to detect whether more data exists.
        4. Encodes next/prev cursors for the caller.

        Args:
            db: Async database session.
            params: Cursor pagination parameters (cursor, limit, direction).
            order_by: Model column name to sort by (default ``"id"``).
            order_desc: Whether to sort descending (default ``True``).
            conditions: Additional SQLAlchemy ``where`` clause expressions.
            include_deleted: Include soft-deleted records.
            include_total: Whether to run a ``COUNT`` query.  Set to
                ``False`` for large tables where the total is expensive.

        Returns:
            ``CursorPaginatedResult`` with items, cursors, and metadata.

        Raises:
            ValueError: If the cursor string is malformed.
        """
        # Resolve the sort column (fall back to ``id`` if invalid)
        sort_col_name = order_by if hasattr(self.model, order_by) else "id"
        sort_col = getattr(self.model, sort_col_name)
        id_col = self.model.id  # type: ignore[attr-defined]

        # Base query
        query = select(self.model)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)

        for cond in conditions or []:
            query = query.where(cond)

        # Decode cursor and apply keyset filter
        if params.cursor:
            cursor_sort_val, cursor_id = decode_cursor(params.cursor)
            cursor_sort_val = self._coerce_sort_value(cursor_sort_val, sort_col)

            if params.direction == "next":
                if order_desc:
                    # Descending: next page = smaller values
                    query = query.where(
                        (sort_col < cursor_sort_val)
                        | ((sort_col == cursor_sort_val) & (id_col < cursor_id))
                    )
                else:
                    # Ascending: next page = larger values
                    query = query.where(
                        (sort_col > cursor_sort_val)
                        | ((sort_col == cursor_sort_val) & (id_col > cursor_id))
                    )
            else:  # direction == "prev"
                if order_desc:
                    # Descending: prev page = larger values (reverse)
                    query = query.where(
                        (sort_col > cursor_sort_val)
                        | ((sort_col == cursor_sort_val) & (id_col > cursor_id))
                    )
                else:
                    # Ascending: prev page = smaller values (reverse)
                    query = query.where(
                        (sort_col < cursor_sort_val)
                        | ((sort_col == cursor_sort_val) & (id_col < cursor_id))
                    )

        # Ordering — for "prev" requests we invert the sort so we can
        # fetch the *nearest* rows, then reverse the result list.
        if params.direction == "prev":
            # Invert ordering
            if order_desc:
                query = query.order_by(sort_col.asc(), id_col.asc())
            else:
                query = query.order_by(sort_col.desc(), id_col.desc())
        else:
            if order_desc:
                query = query.order_by(sort_col.desc(), id_col.desc())
            else:
                query = query.order_by(sort_col.asc(), id_col.asc())

        # Fetch limit + 1 to detect has_more
        query = query.limit(params.limit + 1)

        result = await db.execute(query)
        rows = list(result.scalars().all())

        has_more = len(rows) > params.limit
        if has_more:
            rows = rows[: params.limit]

        # For "prev" direction we fetched in reverse order — restore original
        if params.direction == "prev":
            rows.reverse()

        # Build cursors
        next_cursor: str | None = None
        prev_cursor: str | None = None

        if rows:
            # Next cursor is always based on the *last* item in the page
            last = rows[-1]
            last_sort_val = getattr(last, sort_col_name)
            last_id = last.id  # type: ignore[attr-defined]

            if has_more or params.direction == "prev":
                # There are more rows ahead, or we came from a "prev"
                # direction so forward is always valid.
                next_cursor = encode_cursor(last_sort_val, last_id)

            # Prev cursor is based on the *first* item
            first = rows[0]
            first_sort_val = getattr(first, sort_col_name)
            first_id = first.id  # type: ignore[attr-defined]

            if params.cursor is not None:
                # We're not on the very first page
                prev_cursor = encode_cursor(first_sort_val, first_id)

        # If we went "prev" and there *are* items, has_more refers to
        # whether there are older items (the "prev" direction).  But we
        # report has_more relative to the *next* direction by convention.
        if params.direction == "prev":
            # When going backwards, "has_more" means there are earlier
            # items.  But the caller typically cares about forward
            # has_more.  We approximate: if we have a next cursor, more
            # exist ahead.  The caller can still use next_cursor != None.
            has_more = next_cursor is not None

        # Optional total count
        total: int | None = None
        if include_total:
            total = await self.count_where(
                db, conditions=conditions, include_deleted=include_deleted
            )

        return CursorPaginatedResult(
            items=rows,
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            has_more=has_more,
            total=total,
        )
