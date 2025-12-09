"""
CRUD operations for User model.

Override create/update to handle password hashing - passwords must never
be stored in plaintext. See CRUDBase for standard CRUD operations.
"""
from typing import Any, Dict, Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """
    CRUD operations for User model with authentication methods.

    Overrides create() and update() to ensure passwords are hashed.
    """

    async def create(
        self, db: AsyncSession, *, obj_in: Union[UserCreate, Dict[str, Any]]
    ) -> User:
        """Create new user with hashed password."""
        if isinstance(obj_in, dict):
            obj_in_data = obj_in.copy()
        else:
            obj_in_data = obj_in.model_dump(exclude_unset=True)

        # Hash password before storing
        if "password" in obj_in_data:
            obj_in_data["hashed_password"] = get_password_hash(
                obj_in_data.pop("password")
            )

        db_obj = User(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: User,
        obj_in: Union[UserUpdate, Dict[str, Any]],
    ) -> User:
        """Update user with password hashing support."""
        if isinstance(obj_in, dict):
            update_data = obj_in.copy()
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        # Hash password if provided
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(
                update_data.pop("password")
            )

        return await super().update(db, db_obj=db_obj, obj_in=update_data)

    async def update_last_login(
        self, db: AsyncSession, *, user: User
    ) -> User:
        """Update user's last login timestamp with transaction safety."""
        try:
            user.update_last_login()
            db.add(user)
            await db.commit()
            await db.refresh(user)
            return user
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to update last login for user {user.id}: {e}")
            # Return user without updated timestamp - non-critical failure
            return user

    async def get_by_email(
        self, db: AsyncSession, *, email: str
    ) -> Optional[User]:
        """Get user by email address."""
        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def authenticate(
        self, db: AsyncSession, *, email: str, password: str
    ) -> Optional[User]:
        """
        Authenticate user by email and password.
        Returns user if credentials are valid, None otherwise.
        """
        user = await self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def is_active(self, user: User) -> bool:
        """Check if user account is active."""
        return user.is_active

    async def is_verified(self, user: User) -> bool:
        """Check if user email is verified."""
        return user.is_verified


# Singleton instance
user = CRUDUser(User)
