"""
User model for authentication and authorization.
"""
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, SoftDeleteMixin


class User(Base, TimestampMixin, SoftDeleteMixin):
    """User model for dashboard access and permissions."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Role and permissions
    role: Mapped[str] = mapped_column(
        String(50),
        default="viewer",
        nullable=False,
    )  # admin, analyst, viewer

    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Profile
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Session management
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Notification preferences
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    report_subscriptions: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )  # JSON string of subscribed report IDs

    # Relationships
    # deals: Mapped[List["Deal"]] = relationship("Deal", back_populates="assigned_user")

    def __repr__(self) -> str:
        return f"<User {self.email}>"

    def update_last_login(self) -> None:
        """Update the last login timestamp."""
        self.last_login = datetime.now(timezone.utc)
