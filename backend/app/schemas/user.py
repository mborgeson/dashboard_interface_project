"""
User schemas for API request/response validation.
"""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from .base import BaseSchema, TimestampSchema


class UserBase(BaseSchema):
    """Base user schema with common fields."""

    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(default="viewer", pattern="^(admin|analyst|viewer)$")
    department: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseSchema):
    """Schema for updating a user. All fields optional."""

    email: EmailStr | None = None
    full_name: str | None = Field(None, min_length=1, max_length=255)
    role: str | None = Field(None, pattern="^(admin|analyst|viewer)$")
    department: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)
    avatar_url: str | None = Field(None, max_length=500)
    is_active: bool | None = None
    email_notifications: bool | None = None


class UserResponse(UserBase, TimestampSchema):
    """Schema for user response (public data)."""

    id: int
    is_active: bool
    is_verified: bool
    avatar_url: str | None = None
    last_login: datetime | None = None
    email_notifications: bool = True


class UserInDB(UserResponse):
    """Schema for user with hashed password (internal use)."""

    hashed_password: str


class UserListResponse(BaseModel):
    """Paginated list of users."""

    items: list[UserResponse]
    total: int
    page: int
    page_size: int
