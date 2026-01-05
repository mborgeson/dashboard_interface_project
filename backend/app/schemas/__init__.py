"""Pydantic schemas for API request/response validation."""
from .auth import LoginRequest, Token, TokenPayload
from .deal import DealCreate, DealResponse, DealStageUpdate, DealUpdate
from .property import PropertyCreate, PropertyResponse, PropertyUpdate
from .user import UserCreate, UserInDB, UserResponse, UserUpdate

__all__ = [
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserInDB",
    "PropertyCreate",
    "PropertyUpdate",
    "PropertyResponse",
    "DealCreate",
    "DealUpdate",
    "DealResponse",
    "DealStageUpdate",
    "Token",
    "TokenPayload",
    "LoginRequest",
]
