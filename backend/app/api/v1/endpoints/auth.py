"""
Authentication endpoints for login, logout, and token management.
"""

import time

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    decode_token,
)
from app.core.token_blacklist import token_blacklist
from app.crud import user as user_crud
from app.db.session import get_db
from app.schemas.auth import RefreshTokenRequest, Token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
slog = structlog.get_logger("app.api.auth")


def _get_demo_users() -> dict:
    """
    Get demo users dictionary - only available in non-production environments.

    SECURITY: Demo users are disabled in production to prevent unauthorized access.
    In production, all authentication must go through the database.
    """
    if settings.ENVIRONMENT == "production":
        return {}

    # Demo users for development/testing only
    # Passwords loaded from environment variables — never hardcoded
    users = {}
    if settings.DEMO_USER_PASSWORD:
        users["matt@bandrcapital.com"] = {
            "password": settings.DEMO_USER_PASSWORD,
            "id": 1,
            "role": "admin",
            "full_name": "Matt Borgeson",
        }
    if settings.DEMO_ADMIN_PASSWORD:
        users["admin@bandrcapital.com"] = {
            "password": settings.DEMO_ADMIN_PASSWORD,
            "id": 2,
            "role": "admin",
            "full_name": "Admin User",
        }
    if settings.DEMO_ANALYST_PASSWORD:
        users["analyst@bandrcapital.com"] = {
            "password": settings.DEMO_ANALYST_PASSWORD,
            "id": 3,
            "role": "analyst",
            "full_name": "Analyst User",
        }
    return users


@router.post(
    "/login",
    response_model=Token,
    summary="Login",
    description="Authenticate a user with email and password. Returns JWT access and refresh "
    "tokens. Tries database authentication first, then falls back to demo users in "
    "non-production environments.",
    responses={
        200: {"description": "Authentication successful, tokens returned"},
        401: {"description": "Invalid email or password"},
        403: {"description": "User account is disabled"},
    },
)
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

        slog.info(
            "user_login_success",
            user_id=db_user.id,
            email=form_data.username,
            auth_method="database",
        )

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
            additional_claims={
                "role": demo_user["role"],
                "email": form_data.username,
                "full_name": demo_user.get("full_name"),
            },
        )
        refresh_token = create_refresh_token(subject=str(demo_user["id"]))

        slog.info(
            "user_login_success",
            user_id=demo_user["id"],
            email=form_data.username,
            auth_method="demo",
        )

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # Authentication failed
    slog.warning(
        "user_login_failed",
        email=form_data.username,
        reason="invalid_credentials",
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh token",
    description="Exchange a refresh token for new access and refresh tokens. Implements "
    "refresh token rotation — the old refresh token is blacklisted after use. Detects "
    "replay attacks and revokes all user sessions if a used token is resubmitted.",
    responses={
        200: {"description": "New access and refresh tokens issued"},
        401: {"description": "Invalid, expired, or reused refresh token"},
    },
)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token (with rotation).

    Implements refresh token rotation:
    - Issues a NEW access token AND a NEW refresh token
    - Blacklists the OLD refresh token after use
    - Detects replay attacks: if a previously-used (blacklisted) refresh token
      is presented, revokes ALL tokens for that user

    - **refresh_token**: Valid refresh token
    """
    payload = decode_refresh_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    jti = payload.get("jti")
    user_id = payload.get("sub")

    # Check if user's tokens have been globally revoked (replay attack response)
    if user_id and await token_blacklist.is_user_revoked(user_id):
        slog.warning(
            "token_refresh_revoked_user",
            user_id=user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="All sessions have been revoked. Please log in again.",
        )

    # Check if this refresh token has already been used (replay attack detection)
    if jti and await token_blacklist.is_blacklisted(jti):
        # Replay attack detected — a previously-used refresh token is being reused.
        # Revoke ALL tokens for this user as a security measure.
        if user_id:
            await token_blacklist.revoke_user_tokens(
                user_id,
                expires_in=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
            )
        slog.warning(
            "token_replay_attack_detected",
            user_id=user_id,
            jti_prefix=jti[:8] if jti else None,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token reuse detected. All sessions have been revoked for security.",
        )

    # Blacklist the old refresh token (rotation: one-time use only)
    if jti:
        exp = payload.get("exp", 0)
        ttl = max(0, int(exp) - int(time.time()))
        if ttl > 0:
            await token_blacklist.add(jti, ttl)
            slog.debug(
                "token_refresh_rotated",
                user_id=user_id,
                jti_prefix=jti[:8],
                ttl_seconds=ttl,
            )

    # Create new tokens (rotation: both access and refresh are new)
    access_token = create_access_token(subject=user_id)
    new_refresh_token = create_refresh_token(subject=user_id)

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    summary="Logout",
    description="Invalidate the current access token by adding it to the blacklist. "
    "The token remains blacklisted until its natural expiration time.",
    responses={
        200: {"description": "Successfully logged out"},
    },
)
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
                        slog.info(
                            "user_logout",
                            jti_prefix=jti[:8],
                            ttl_seconds=ttl,
                        )
        except Exception as e:
            # Token may be invalid or expired, no need to blacklist
            slog.debug("logout_token_processing_skipped", error=str(e))

    return {"message": "Successfully logged out"}


@router.get(
    "/me",
    summary="Get current user",
    description="Return the profile of the currently authenticated user including ID, email, "
    "role, and full name. Falls back to token claims for demo users without a database record.",
    responses={
        200: {"description": "Current user profile"},
        401: {"description": "Invalid, expired, or revoked token"},
    },
)
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
    db_user = await user_crud.get(db, id=int(user_id)) if user_id is not None else None
    if db_user:
        return {
            "id": db_user.id,
            "email": db_user.email,
            "role": db_user.role,
            "full_name": db_user.full_name,
        }

    # Fallback for demo users (no DB record)
    return {
        "id": int(user_id) if user_id is not None else 0,
        "email": payload.get("email", "demo@bandrcapital.com"),
        "role": payload.get("role", "viewer"),
        "full_name": payload.get("full_name"),
        "is_active": True,
    }
