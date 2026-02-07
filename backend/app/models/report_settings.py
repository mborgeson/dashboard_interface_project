"""
Report settings model — single-row, org-wide configuration for report generation.
"""

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin


class ReportSettings(Base, TimestampMixin):
    """Singleton settings row controlling default report appearance."""

    __tablename__ = "report_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_name: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default="B&R Capital"
    )
    company_logo: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    primary_color: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="#1e40af"
    )
    secondary_color: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="#059669"
    )
    default_font: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="Inter"
    )
    default_page_size: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="letter"
    )
    default_orientation: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="portrait"
    )
    include_page_numbers: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="1"
    )
    include_table_of_contents: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="1"
    )
    include_timestamp: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="1"
    )
    footer_text: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        server_default="Confidential - For Internal Use Only",
    )
    header_text: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        server_default="B&R Capital Real Estate Analytics",
    )
    watermark_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
