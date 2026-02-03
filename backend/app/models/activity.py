"""
Activity models for tracking user interactions with properties and deals.
"""

from enum import StrEnum as PyEnum

from sqlalchemy import Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin


class ActivityType(PyEnum):
    """Types of activities that can be tracked."""

    VIEW = "view"
    EDIT = "edit"
    COMMENT = "comment"
    STATUS_CHANGE = "status_change"
    DOCUMENT_UPLOAD = "document_upload"


class PropertyActivity(Base, TimestampMixin):
    """
    Activity log for tracking user interactions with properties.

    Tracks views, edits, comments, status changes, and document uploads.
    """

    __tablename__ = "property_activities"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Relationships
    property_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("properties.id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # Activity details
    activity_type: Mapped[ActivityType] = mapped_column(
        Enum(ActivityType),
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata for different activity types
    # For edits: field changed, old/new values
    field_changed: Mapped[str | None] = mapped_column(String(100), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    # For comments
    comment_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # For document uploads
    document_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # IP and user agent for security/audit
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<PropertyActivity {self.activity_type.value} on property {self.property_id}>"


class DealActivity(Base, TimestampMixin):
    """
    Activity log for tracking user interactions with deals.

    Tracks views, edits, comments, status changes, and document uploads.
    """

    __tablename__ = "deal_activities"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Relationships
    deal_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("deals.id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # Activity details
    activity_type: Mapped[ActivityType] = mapped_column(
        Enum(ActivityType),
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata for different activity types
    field_changed: Mapped[str | None] = mapped_column(String(100), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    # For comments
    comment_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # For document uploads
    document_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # IP and user agent for security/audit
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<DealActivity {self.activity_type.value} on deal {self.deal_id}>"


class UserWatchlist(Base, TimestampMixin):
    """
    Watchlist model for tracking deals that users want to follow.

    Users can add/remove deals from their watchlist to receive updates
    and quick access.
    """

    __tablename__ = "user_watchlists"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Relationships
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    deal_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("deals.id"),
        nullable=False,
        index=True,
    )

    # Optional: track when user added this to watchlist with note
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Alert preferences for this specific watch
    alert_on_stage_change: Mapped[bool] = mapped_column(default=True)
    alert_on_price_change: Mapped[bool] = mapped_column(default=True)
    alert_on_document: Mapped[bool] = mapped_column(default=False)

    __table_args__ = (
        UniqueConstraint("user_id", "deal_id", name="uq_user_deal_watchlist"),
    )

    def __repr__(self) -> str:
        return f"<UserWatchlist user={self.user_id} deal={self.deal_id}>"
