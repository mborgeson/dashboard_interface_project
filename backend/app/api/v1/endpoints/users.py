"""
User management endpoints.

Access Control:
- List users: Admin only
- Get user: Admin or self
- Create user: Admin only
- Update user: Admin or self (with restrictions)
- Delete user: Admin only
- Verify user: Admin only
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    CurrentUser,
    get_current_user,
    require_admin,
)
from app.crud.crud_user import user as user_crud
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)

router = APIRouter()


@router.get(
    "/",
    response_model=UserListResponse,
    summary="List users",
    description="List all users with optional filtering by role, department, and "
    "active status. Requires admin role. Supports pagination.",
    responses={
        200: {"description": "Paginated list of users"},
    },
)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: str | None = None,
    department: str | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """
    List all users with filtering and pagination.

    Requires admin role.
    """
    logger.info(f"User {current_user.email} listing users")

    # Build filter conditions
    conditions: list = []
    if role:
        conditions.append(User.role == role)
    if department:
        conditions.append(User.department == department)
    if is_active is not None:
        conditions.append(User.is_active == is_active)

    result = await user_crud.get_paginated(
        db,
        page=page,
        per_page=page_size,
        order_by="id",
        order_desc=False,
        conditions=conditions,
    )

    return UserListResponse(
        items=[
            UserResponse.model_validate(u, from_attributes=True) for u in result.items
        ],
        total=result.total,
        page=result.page,
        page_size=result.per_page,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    description="Retrieve a single user by their ID. Users can view their own "
    "profile; admins can view any user.",
    responses={
        200: {"description": "User details"},
        403: {"description": "Not authorized to view this user"},
        404: {"description": "User not found"},
    },
)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get a specific user by ID.

    Users can view their own profile. Admins can view any user.
    """
    # Check authorization: user can view self, admin can view anyone
    if current_user.id != user_id and not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own profile",
        )

    user = await user_crud.get(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    return user


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user",
    description="Create a new user account. Requires admin role. "
    "Returns 400 if the email is already registered.",
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Email already registered"},
    },
)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """
    Create a new user.

    Requires admin role.
    """
    logger.info(f"Admin {current_user.email} creating user: {user_data.email}")

    # Check for existing email
    existing = await user_crud.get_by_email(db, email=user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = await user_crud.create(db, obj_in=user_data)
    logger.info(f"Created user: {new_user.email}")

    return new_user


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update a user",
    description="Update an existing user's profile. Users can update their own "
    "profile (limited fields). Admins can update any user with all fields.",
    responses={
        200: {"description": "User updated successfully"},
        400: {"description": "Email already in use"},
        403: {"description": "Not authorized or restricted fields attempted"},
        404: {"description": "User not found"},
    },
)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Update an existing user.

    Users can update their own profile (limited fields).
    Admins can update any user with all fields.
    """
    # Check authorization
    is_self = current_user.id == user_id
    is_admin = current_user.is_admin()

    if not is_self and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile",
        )

    existing = await user_crud.get(db, user_id)

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    # Non-admins cannot change certain fields
    if is_self and not is_admin:
        restricted_fields = {"role", "is_active", "is_verified"}
        update_dict = user_data.model_dump(exclude_unset=True)
        attempted_restricted = set(update_dict.keys()) & restricted_fields
        if attempted_restricted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You cannot modify: {', '.join(attempted_restricted)}",
            )

    # Check email uniqueness if changing
    if user_data.email and user_data.email != existing.email:
        email_exists = await user_crud.get_by_email(db, email=user_data.email)
        if email_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use",
            )

    updated_user = await user_crud.update(db, db_obj=existing, obj_in=user_data)
    logger.info(f"User {current_user.email} updated user: {user_id}")

    return updated_user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a user",
    description="Soft-delete a user by setting is_active to False. "
    "Requires admin role. Admins cannot deactivate themselves.",
    responses={
        204: {"description": "User deactivated successfully"},
        400: {"description": "Cannot deactivate your own account"},
        404: {"description": "User not found"},
    },
)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """
    Deactivate a user (soft delete).

    Requires admin role.
    """
    # Prevent admin from deleting themselves
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )

    existing = await user_crud.get(db, user_id)

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    # Soft-delete: set is_active = False
    await user_crud.update(db, db_obj=existing, obj_in={"is_active": False})
    logger.info(f"Admin {current_user.email} deactivated user: {user_id}")

    return None


@router.post(
    "/{user_id}/verify",
    summary="Verify a user",
    description="Mark a user's email as verified. Requires admin role.",
    responses={
        200: {"description": "User verified successfully"},
        404: {"description": "User not found"},
    },
)
async def verify_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """
    Verify a user's email.

    Requires admin role.
    """
    existing = await user_crud.get(db, user_id)

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    await user_crud.update(db, db_obj=existing, obj_in={"is_verified": True})
    logger.info(f"Admin {current_user.email} verified user: {user_id}")

    return {"message": f"User {user_id} verified successfully"}
