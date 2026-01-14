"""Pydantic schemas for API request/response validation."""

from .activity import (
    ActivityType,
    DealActivityCreate,
    DealActivityListResponse,
    DealActivityResponse,
    PropertyActivityCreate,
    PropertyActivityListResponse,
    PropertyActivityResponse,
    WatchlistCreate,
    WatchlistListResponse,
    WatchlistResponse,
    WatchlistToggleResponse,
)
from .auth import LoginRequest, Token, TokenPayload
from .comparison import (
    ComparisonSummary,
    DealComparisonRequest,
    DealComparisonResponse,
    DealMetrics,
    MetricComparison,
    QuickCompareResponse,
)
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
    # Activity schemas
    "ActivityType",
    "PropertyActivityCreate",
    "PropertyActivityResponse",
    "PropertyActivityListResponse",
    "DealActivityCreate",
    "DealActivityResponse",
    "DealActivityListResponse",
    "WatchlistCreate",
    "WatchlistResponse",
    "WatchlistListResponse",
    "WatchlistToggleResponse",
    # Comparison schemas
    "DealMetrics",
    "MetricComparison",
    "ComparisonSummary",
    "DealComparisonResponse",
    "DealComparisonRequest",
    "QuickCompareResponse",
]
