"""
Document schemas for API request/response validation.
"""

from datetime import datetime

from pydantic import Field

from .base import BaseSchema, TimestampSchema


class DocumentBase(BaseSchema):
    """Base document schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(
        ..., pattern="^(lease|financial|legal|due_diligence|photo|other)$"
    )
    property_id: str | None = None
    property_name: str | None = Field(None, max_length=255)


class DocumentCreate(DocumentBase):
    """Schema for creating a new document (metadata only)."""

    size: int = Field(default=0, ge=0)
    uploaded_at: datetime | None = None
    uploaded_by: str | None = Field(None, max_length=255)
    description: str | None = None
    tags: list[str] | None = None
    url: str | None = Field(None, max_length=2048)
    file_path: str | None = Field(None, max_length=1024)
    mime_type: str | None = Field(None, max_length=255)


class DocumentUpdate(BaseSchema):
    """Schema for updating a document. All fields optional."""

    name: str | None = Field(None, min_length=1, max_length=255)
    type: str | None = Field(
        None, pattern="^(lease|financial|legal|due_diligence|photo|other)$"
    )
    property_id: str | None = None
    property_name: str | None = Field(None, max_length=255)
    description: str | None = None
    tags: list[str] | None = None
    url: str | None = Field(None, max_length=2048)


class DocumentUpload(BaseSchema):
    """Schema for file upload response/request metadata."""

    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(
        ..., pattern="^(lease|financial|legal|due_diligence|photo|other)$"
    )
    property_id: str | None = None
    property_name: str | None = Field(None, max_length=255)
    description: str | None = None
    tags: list[str] | None = None


class DocumentResponse(DocumentBase, TimestampSchema):
    """Schema for document response."""

    id: int
    size: int
    uploaded_at: datetime
    uploaded_by: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    url: str | None = None
    file_path: str | None = None
    mime_type: str | None = None


class DocumentListResponse(BaseSchema):
    """Paginated list of documents."""

    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class DocumentStats(BaseSchema):
    """Document statistics for dashboard."""

    total_documents: int
    total_size: int
    by_type: dict[str, int]
    recent_uploads: int  # Last 30 days


class DocumentUploadResponse(BaseSchema):
    """Response for document upload."""

    document: DocumentResponse
    message: str
