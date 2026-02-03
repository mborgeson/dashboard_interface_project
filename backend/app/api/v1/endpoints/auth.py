"""
Authentication endpoints for login, logout, and token management.
"""

import time

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.token_blacklist import token_blacklist
from app.crud import user as user_crud
from app.db.session import get_db
from app.schemas.auth import RefreshTokenRequest, Token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def _get_demo_users() -> dict:
    """
    Get demo users dictionary - only available in non-production environments.

    SECURITY: Demo users are disabled in production to prevent unauthorized access.
    In production, all authentication must go through the database.
    """
    if settings.ENVIRONMENT == "production":
        return {}

    # Demo users for development/testing only
    return {
        "admin@bandrcapital.com": {
            "password": "admin123",
            "id": 1,
            "role": "admin",
        },
        "analyst@bandrcapital.com": {
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

    # Fallback to demo users for development (disabled in production)
    demo_users = _get_demo_users()
    demo_user = demo_users.get(form_data.username)
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

    # Check if refresh token has been revoked
    jti = payload.get("jti")
    if jti and await token_blacklist.is_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
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
async def logout(
    authorization: str | None = Header(None, alias="Authorization"),
):
    """
    Logout user (invalidate tokens).

    Adds the token to a blacklist to prevent further use.
    The token will remain blacklisted until its natural expiration.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        try:
            payload = decode_token(token)
            if payload:
                jti = payload.get("jti")
                exp = payload.get("exp", 0)
                if jti:
                    # Calculate remaining token lifetime
                    ttl = max(0, int(exp) - int(time.time()))
                    if ttl > 0:
                        await token_blacklist.add(jti, ttl)
                        logger.info(f"Token blacklisted: {jti[:8]}... (TTL: {ttl}s)")
        except Exception as e:
            # Token may be invalid or expired, no need to blacklist
            logger.debug(f"Logout token processing skipped: {e}")

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

    # Check if token has been revoked (logout)
    jti = payload.get("jti")
    if jti and await token_blacklist.is_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
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
        "email": payload.get("email", "demo@bandrcapital.com"),
        "role": payload.get("role", "viewer"),
    }
