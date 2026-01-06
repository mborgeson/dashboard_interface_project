"""
Authentication endpoints for login, logout, and token management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.crud import user as user_crud
from app.db.session import get_db
from app.schemas.auth import RefreshTokenRequest, Token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Demo users fallback (for development without DB setup)
DEMO_USERS = {
    "admin@brcapital.com": {
        "password": "admin123",
        "id": 1,
        "role": "admin",
    },
    "analyst@brcapital.com": {
        "password": "analyst123",
        "id": 2,
        "role": "analyst",
    },
}


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return access tokens.

    - **username**: User email address
    - **password**: User password
    """
    # Try database authentication first
    db_user = await user_crud.authenticate(
        db, email=form_data.username, password=form_data.password
    )

    if db_user:
        # Check if user is active
        if not db_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled",
            )

        # Update last login (non-critical, handled with transaction safety)
        await user_crud.update_last_login(db, user=db_user)

        # Create tokens
        access_token = create_access_token(
            subject=str(db_user.id),
            additional_claims={"role": db_user.role},
        )
        refresh_token = create_refresh_token(subject=str(db_user.id))

        logger.info(f"User logged in: {form_data.username}")

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # Fallback to demo users for development
    demo_user = DEMO_USERS.get(form_data.username)
    if demo_user and form_data.password == demo_user["password"]:
        access_token = create_access_token(
            subject=str(demo_user["id"]),
            additional_claims={"role": demo_user["role"]},
        )
        refresh_token = create_refresh_token(subject=str(demo_user["id"]))

        logger.info(f"Demo user logged in: {form_data.username}")

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # Authentication failed
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token.

    - **refresh_token**: Valid refresh token
    """
    payload = decode_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Create new tokens
    user_id = payload.get("sub")
    access_token = create_access_token(subject=user_id)
    new_refresh_token = create_refresh_token(subject=user_id)

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
async def logout():
    """
    Logout user (invalidate tokens).

    Note: In a stateless JWT setup, this primarily signals the client
    to discard tokens. Server-side token invalidation requires a
    token blacklist (typically using Redis).
    """
    # TODO: Add token to blacklist if implementing server-side invalidation
    return {"message": "Successfully logged out"}


@router.get("/me")
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current authenticated user information.
    """
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")

    # Fetch actual user from database
    db_user = await user_crud.get(db, id=int(user_id))
    if db_user:
        return {
            "id": db_user.id,
            "email": db_user.email,
            "role": db_user.role,
            "full_name": db_user.full_name,
        }

    # Fallback for demo users (no DB record)
    return {
        "id": int(user_id),
        "email": payload.get("email", "demo@brcapital.com"),
        "role": payload.get("role", "viewer"),
    }
