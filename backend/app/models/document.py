"""
Document model for storing property-related documents and files.
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    JSON,
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import SoftDeleteMixin, TimestampMixin


class DocumentType(str, PyEnum):
    """Document type categories."""

    LEASE = "lease"
    FINANCIAL = "financial"
    LEGAL = "legal"
    DUE_DILIGENCE = "due_diligence"
    PHOTO = "photo"
    OTHER = "other"


class Document(Base, TimestampMixin, SoftDeleteMixin):
    """Document model representing uploaded files and documents."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Basic Information
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # lease, financial, legal, due_diligence, photo, other

    # Property Relationship
    property_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    property_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # File Information
    size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # bytes
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    uploaded_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Metadata
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # File Storage
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<Document {self.name} ({self.type})>"

    def get_size_formatted(self) -> str:
        """Return file size in human-readable format."""
        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f} KB"
        elif self.size < 1024 * 1024 * 1024:
            return f"{self.size / (1024 * 1024):.1f} MB"
        else:
            return f"{self.size / (1024 * 1024 * 1024):.1f} GB"
