"""
Activity schemas for API request/response validation.
"""

from enum import StrEnum

from .base import BaseSchema, TimestampSchema


class ActivityType(StrEnum):
    """Types of activities that can be tracked."""

    VIEW = "view"
    EDIT = "edit"
    COMMENT = "comment"
    STATUS_CHANGE = "status_change"
    DOCUMENT_UPLOAD = "document_upload"


class PropertyActivityBase(BaseSchema):
    """Base schema for property activity."""

    property_id: int
    activity_type: ActivityType
    description: str | None = None


class PropertyActivityCreate(PropertyActivityBase):
    """Schema for creating a property activity."""

    # Optional metadata based on activity type
    field_changed: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    comment_text: str | None = None
    document_name: str | None = None
    document_url: str | None = None


class PropertyActivityResponse(PropertyActivityBase, TimestampSchema):
    """Schema for property activity response."""

    id: int
    user_id: int
    user_name: str | None = None  # Populated from join

    # Activity metadata
    field_changed: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    comment_text: str | None = None
    document_name: str | None = None
    document_url: str | None = None


class PropertyActivityListResponse(BaseSchema):
    """Paginated list of property activities."""

    activities: list[PropertyActivityResponse]
    total: int
    page: int = 1
    page_size: int = 50


class DealActivityBase(BaseSchema):
    """Base schema for deal activity."""

    deal_id: int
    activity_type: ActivityType
    description: str | None = None


class DealActivityCreate(DealActivityBase):
    """Schema for creating a deal activity."""

    field_changed: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    comment_text: str | None = None
    document_name: str | None = None
    document_url: str | None = None


class DealActivityResponse(DealActivityBase, TimestampSchema):
    """Schema for deal activity response."""

    id: int
    user_id: int
    user_name: str | None = None

    field_changed: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    comment_text: str | None = None
    document_name: str | None = None
    document_url: str | None = None


class DealActivityListResponse(BaseSchema):
    """Paginated list of deal activities."""

    items: list[DealActivityResponse]
    total: int
    page: int = 1
    page_size: int = 50


# Watchlist schemas
class WatchlistBase(BaseSchema):
    """Base schema for watchlist."""

    deal_id: int
    notes: str | None = None
    alert_on_stage_change: bool = True
    alert_on_price_change: bool = True
    alert_on_document: bool = False


class WatchlistCreate(WatchlistBase):
    """Schema for creating a watchlist entry."""

    pass


class WatchlistResponse(WatchlistBase, TimestampSchema):
    """Schema for watchlist response."""

    id: int
    user_id: int
    is_watched: bool = True

    # Include deal summary info
    deal_name: str | None = None
    deal_stage: str | None = None
    deal_type: str | None = None


class WatchlistToggleResponse(BaseSchema):
    """Response when toggling watchlist status."""

    deal_id: int
    is_watched: bool
    message: str
    watchlist_id: int | None = None


class WatchlistListResponse(BaseSchema):
    """List of watched deals for a user."""

    items: list[WatchlistResponse]
    total: int
