"""
DeltaToken model for tracking Microsoft Graph delta query tokens.

Delta tokens enable incremental sync with SharePoint/OneDrive by
tracking the last known state. On subsequent requests, only changes
since the token was issued are returned, reducing API calls and
bandwidth.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin


class DeltaToken(Base, TimestampMixin):
    """Stores delta query tokens per drive for incremental sync.

    Each SharePoint/OneDrive drive has its own delta token that tracks
    the sync cursor position. When a token expires (HTTP 410), the
    client falls back to a full scan and stores the new token.
    """

    __tablename__ = "delta_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    drive_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    delta_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    last_sync_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<DeltaToken drive_id={self.drive_id!r}>"
