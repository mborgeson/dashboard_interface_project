"""
Base CRUD class with common database operations.
"""

from typing import Any, Generic, TypeVar

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


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
