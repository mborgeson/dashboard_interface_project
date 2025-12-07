"""
Authentication endpoints for login, logout, and token management.
"""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.db.session import get_db
from app.schemas.auth import Token, LoginRequest, RefreshTokenRequest

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return access tokens.

    - **username**: User email address
    - **password**: User password
    """
    # In production, this would query the database
    # For now, returning a demo token
    # TODO: Implement actual user authentication

    # Demo user validation (replace with actual database query)
    demo_users = {
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

    user = demo_users.get(form_data.username)
    if not user or not verify_password(form_data.password, get_password_hash(user["password"])):
        # For demo, also accept plain text comparison
        if not user or form_data.password != user["password"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Create tokens
    access_token = create_access_token(
        subject=str(user["id"]),
        additional_claims={"role": user["role"]},
    )
    refresh_token = create_refresh_token(subject=str(user["id"]))

    logger.info(f"User logged in: {form_data.username}")

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
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
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Get current authenticated user information.
    """
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # In production, fetch user from database
    user_id = payload.get("sub")

    return {
        "id": int(user_id),
        "email": "user@brcapital.com",  # Would come from DB
        "role": payload.get("role", "viewer"),
    }
