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
from app.core.security import get_password_hash
from app.db.session import get_db
from app.schemas.user import (
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)

router = APIRouter()

# Demo data
DEMO_USERS = [
    {
        "id": 1,
        "email": "admin@bandrcapital.com",
        "full_name": "Admin User",
        "role": "admin",
        "department": "Executive",
        "is_active": True,
        "is_verified": True,
        "email_notifications": True,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-12-01T00:00:00Z",
    },
    {
        "id": 2,
        "email": "analyst@bandrcapital.com",
        "full_name": "Investment Analyst",
        "role": "analyst",
        "department": "Acquisitions",
        "is_active": True,
        "is_verified": True,
        "email_notifications": True,
        "created_at": "2024-03-15T00:00:00Z",
        "updated_at": "2024-12-01T00:00:00Z",
    },
    {
        "id": 3,
        "email": "viewer@bandrcapital.com",
        "full_name": "Portfolio Viewer",
        "role": "viewer",
        "department": "Asset Management",
        "is_active": True,
        "is_verified": True,
        "email_notifications": False,
        "created_at": "2024-06-01T00:00:00Z",
        "updated_at": "2024-11-15T00:00:00Z",
    },
]


@router.get("/", response_model=UserListResponse)
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
    filtered = DEMO_USERS.copy()

    if role:
        filtered = [u for u in filtered if u["role"] == role]
    if department:
        filtered = [u for u in filtered if u.get("department") == department]
    if is_active is not None:
        filtered = [u for u in filtered if u["is_active"] == is_active]

    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    items = filtered[start:end]

    return UserListResponse(
        items=items,  # type: ignore[arg-type]
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", response_model=UserResponse)
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

    user = next((u for u in DEMO_USERS if u["id"] == user_id), None)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    return user


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
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
    existing = next((u for u in DEMO_USERS if u["email"] == user_data.email), None)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_id = int(max(u["id"] for u in DEMO_USERS)) + 1 if DEMO_USERS else 1  # type: ignore[type-var,call-overload]

    # Hash password
    _hashed_password = get_password_hash(user_data.password)  # noqa: F841

    new_user = {
        "id": new_id,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "role": user_data.role,
        "department": user_data.department,
        "is_active": True,
        "is_verified": False,
        "email_notifications": True,
        "created_at": "2024-12-05T00:00:00Z",
        "updated_at": "2024-12-05T00:00:00Z",
    }

    logger.info(f"Created user: {new_user['email']}")

    return new_user


@router.put("/{user_id}", response_model=UserResponse)
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

    existing = next((u for u in DEMO_USERS if u["id"] == user_id), None)

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
    if user_data.email and user_data.email != existing["email"]:
        email_exists = any(u for u in DEMO_USERS if u["email"] == user_data.email)
        if email_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use",
            )

    update_data = user_data.model_dump(exclude_unset=True)
    existing.update(update_data)

    logger.info(f"User {current_user.email} updated user: {user_id}")

    return existing


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
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

    existing = next((u for u in DEMO_USERS if u["id"] == user_id), None)

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    existing["is_active"] = False
    logger.info(f"Admin {current_user.email} deactivated user: {user_id}")

    return None


@router.post("/{user_id}/verify")
async def verify_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """
    Verify a user's email.

    Requires admin role.
    """
    existing = next((u for u in DEMO_USERS if u["id"] == user_id), None)

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    existing["is_verified"] = True
    logger.info(f"Admin {current_user.email} verified user: {user_id}")

    return {"message": f"User {user_id} verified successfully"}
