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
from .activity_log import (
    ActivityAction,
    ActivityLogCreate,
    ActivityLogListResponse,
    ActivityLogResponse,
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
from .grouping import (
    ConflictCheckResponse,
    DiscoveryResponse,
    FingerprintResponse,
    GroupDetailResponse,
    GroupExtractionRequest,
    GroupExtractionResponse,
    GroupListResponse,
    GroupSummary,
    PipelineStatusResponse,
    ReferenceMappingResponse,
)
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
    # Activity Log schemas (UUID-based)
    "ActivityAction",
    "ActivityLogCreate",
    "ActivityLogResponse",
    "ActivityLogListResponse",
    # Comparison schemas
    "DealMetrics",
    "MetricComparison",
    "ComparisonSummary",
    "DealComparisonResponse",
    "DealComparisonRequest",
    "QuickCompareResponse",
    # Grouping schemas
    "GroupSummary",
    "DiscoveryResponse",
    "FingerprintResponse",
    "GroupListResponse",
    "GroupDetailResponse",
    "ReferenceMappingResponse",
    "ConflictCheckResponse",
    "GroupExtractionRequest",
    "GroupExtractionResponse",
    "PipelineStatusResponse",
]
