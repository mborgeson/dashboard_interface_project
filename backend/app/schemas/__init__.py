"""Pydantic schemas for API request/response validation."""
from .user import UserCreate, UserUpdate, UserResponse, UserInDB
from .property import PropertyCreate, PropertyUpdate, PropertyResponse
from .deal import DealCreate, DealUpdate, DealResponse, DealStageUpdate
from .auth import Token, TokenPayload, LoginRequest

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
