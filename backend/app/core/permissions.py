"""
Role-Based Access Control (RBAC) for the B&R Capital Dashboard.

This module provides:
- Role enum defining user permission levels
- Permission checking functions
- FastAPI dependencies for route protection
- Decorator for role-based endpoint access
"""

from collections.abc import Callable
from enum import StrEnum

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.core.token_blacklist import token_blacklist
from app.crud import user as user_crud
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class Role(StrEnum):
    """
    User roles with hierarchical permissions.

    Permission hierarchy (highest to lowest):
    - ADMIN: Full system access, user management, all operations
    - MANAGER: Team management, deal approval, report generation
    - ANALYST: Data entry, analysis, limited modifications
    - VIEWER: Read-only access to dashboards and reports
    """

    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    VIEWER = "viewer"


# Role hierarchy for permission inheritance
# Higher index = more permissions
ROLE_HIERARCHY: dict[Role, int] = {
    Role.VIEWER: 0,
    Role.ANALYST: 1,
    Role.MANAGER: 2,
    Role.ADMIN: 3,
}


class CurrentUser:
    """
    Represents the current authenticated user with role information.
    """

    def __init__(
        self,
        id: int,
        email: str,
        role: Role,
        full_name: str | None = None,
        is_active: bool = True,
    ):
        self.id = id
        self.email = email
        self.role = role
        self.full_name = full_name
        self.is_active = is_active

    def has_role(self, required_role: Role) -> bool:
        """Check if user has at least the required role level."""
        return ROLE_HIERARCHY.get(self.role, 0) >= ROLE_HIERARCHY.get(required_role, 0)

    def has_exact_role(self, role: Role) -> bool:
        """Check if user has exactly the specified role."""
        return self.role == role

    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.role == Role.ADMIN

    def can_manage_users(self) -> bool:
        """Check if user can manage other users (admin only)."""
        return self.role == Role.ADMIN

    def can_approve_deals(self) -> bool:
        """Check if user can approve deals (manager or admin)."""
        return self.has_role(Role.MANAGER)

    def can_modify_data(self) -> bool:
        """Check if user can modify data (analyst or higher)."""
        return self.has_role(Role.ANALYST)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """
    Dependency to get the current authenticated user.

    Validates the JWT token and returns a CurrentUser object.

    Raises:
        HTTPException: 401 if token is invalid, expired, or revoked
        HTTPException: 403 if user account is disabled
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode and validate token
    payload = decode_token(token)
    if not payload:
        raise credentials_exception

    # Check if token has been revoked
    jti = payload.get("jti")
    if jti and await token_blacklist.is_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    # Try to fetch user from database
    db_user = await user_crud.get(db, id=int(user_id))

    if db_user:
        if not db_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled",
            )

        # Parse role from database
        try:
            role = Role(db_user.role)
        except ValueError:
            role = Role.VIEWER  # Default to lowest permission

        return CurrentUser(
            id=db_user.id,
            email=db_user.email,
            role=role,
            full_name=db_user.full_name,
            is_active=db_user.is_active,
        )

    # Fallback for demo/development users (token contains role claim)
    role_str = payload.get("role", "viewer")
    try:
        role = Role(role_str)
    except ValueError:
        role = Role.VIEWER

    return CurrentUser(
        id=int(user_id),
        email=payload.get("email", "demo@bandrcapital.com"),
        role=role,
        full_name=None,
        is_active=True,
    )


async def get_current_active_user(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """
    Dependency to ensure the current user is active.

    This is a convenience wrapper around get_current_user that
    explicitly checks the is_active flag.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    return current_user


def require_role(required_role: Role) -> Callable:
    """
    Dependency factory to require a minimum role level.

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(
            current_user: CurrentUser = Depends(require_role(Role.ADMIN))
        ):
            ...

    Args:
        required_role: Minimum role required to access the endpoint

    Returns:
        FastAPI dependency that validates user role
    """

    async def role_checker(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not current_user.has_role(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role.value} or higher",
            )
        return current_user

    return role_checker


def require_any_role(*roles: Role) -> Callable:
    """
    Dependency factory to require any of the specified roles.

    Usage:
        @router.get("/managers-or-admins")
        async def restricted_endpoint(
            current_user: CurrentUser = Depends(require_any_role(Role.MANAGER, Role.ADMIN))
        ):
            ...

    Args:
        *roles: List of acceptable roles

    Returns:
        FastAPI dependency that validates user has one of the roles
    """

    async def role_checker(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if current_user.role not in roles:
            role_names = ", ".join(r.value for r in roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {role_names}",
            )
        return current_user

    return role_checker


# Convenience dependencies for common role requirements
require_admin = require_role(Role.ADMIN)
require_manager = require_role(Role.MANAGER)
require_analyst = require_role(Role.ANALYST)
require_viewer = require_role(Role.VIEWER)


def check_resource_ownership(
    current_user: CurrentUser,
    resource_owner_id: int,
    allow_admin_override: bool = True,
) -> bool:
    """
    Check if the current user owns a resource or has admin override.

    Useful for endpoints where users can only modify their own resources
    unless they are admins.

    Args:
        current_user: The authenticated user
        resource_owner_id: ID of the resource owner
        allow_admin_override: If True, admins can access any resource

    Returns:
        True if access is allowed, False otherwise
    """
    if allow_admin_override and current_user.is_admin():
        return True
    return current_user.id == resource_owner_id


def require_ownership_or_role(resource_owner_id: int, min_role: Role = Role.ADMIN):
    """
    Dependency to require either resource ownership or minimum role.

    This is useful for endpoints like "update user profile" where users
    can update their own profile, but admins can update anyone's.

    Note: This returns a dependency function, not a dependency itself.
    You need to call it with the resource_owner_id at runtime.
    """

    async def ownership_checker(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if current_user.id == resource_owner_id:
            return current_user
        if current_user.has_role(min_role):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own resources",
        )

    return ownership_checker
