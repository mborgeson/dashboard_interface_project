"""
Server-side file upload validation.

Validates file type, size, extension, and magic bytes for uploaded documents.
Allowed types: Excel (.xlsx, .xlsm, .xls), PDF, CSV, DOCX — typical real estate
proforma and deal files.
"""

import mimetypes
from dataclasses import dataclass

from app.core.config import settings

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def _build_max_file_sizes() -> dict[str, int]:
    """Build max file size map from settings (values in MB -> bytes)."""
    return {
        ".xlsx": settings.UPLOAD_MAX_EXCEL_MB * 1024 * 1024,
        ".xlsm": settings.UPLOAD_MAX_EXCEL_MB * 1024 * 1024,
        ".xls": settings.UPLOAD_MAX_EXCEL_MB * 1024 * 1024,
        ".pdf": settings.UPLOAD_MAX_PDF_MB * 1024 * 1024,
        ".csv": settings.UPLOAD_MAX_CSV_MB * 1024 * 1024,
        ".docx": settings.UPLOAD_MAX_DOCX_MB * 1024 * 1024,
    }


# Max file sizes in bytes (built from config)
MAX_FILE_SIZES: dict[str, int] = _build_max_file_sizes()

# Extension -> acceptable MIME types
ALLOWED_MIME_TYPES: dict[str, set[str]] = {
    ".xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/octet-stream",
    },
    ".xlsm": {
        "application/vnd.ms-excel.sheet.macroEnabled.12",
        "application/vnd.ms-excel.sheet.macroenabled.12",
        "application/octet-stream",
    },
    ".xls": {
        "application/vnd.ms-excel",
        "application/octet-stream",
    },
    ".pdf": {
        "application/pdf",
        "application/octet-stream",
    },
    ".csv": {
        "text/csv",
        "text/plain",
        "application/csv",
        "application/octet-stream",
    },
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
}

ALLOWED_EXTENSIONS: set[str] = set(ALLOWED_MIME_TYPES.keys())

# Magic byte signatures (prefix bytes that identify file format)
# PK header = ZIP-based formats (xlsx, xlsm, docx)
# D0 CF 11 E0 = OLE2 compound document (xls)
# %PDF = PDF
MAGIC_BYTES: dict[str, list[bytes]] = {
    ".xlsx": [b"PK\x03\x04"],
    ".xlsm": [b"PK\x03\x04"],
    ".xls": [b"\xd0\xcf\x11\xe0"],
    ".pdf": [b"%PDF"],
    ".docx": [b"PK\x03\x04"],
    # CSV has no magic bytes — skip check
}


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Result of file validation."""

    valid: bool
    error: str | None = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_upload(
    filename: str | None,
    content_type: str | None,
    file_content: bytes,
) -> ValidationResult:
    """Validate an uploaded file's name, MIME type, size, and magic bytes.

    Args:
        filename: Original filename from the upload.
        content_type: MIME content-type header sent by the client.
        file_content: Raw bytes of the uploaded file.

    Returns:
        A ``ValidationResult`` indicating success or an error message.
    """
    # 1. Filename required
    if not filename or not filename.strip():
        return ValidationResult(valid=False, error="Filename is required.")

    # 2. Extension check
    ext = _get_extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        return ValidationResult(
            valid=False,
            error=(
                f"File type '{ext}' is not allowed. "
                f"Accepted types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    # 3. Empty file check
    if len(file_content) == 0:
        return ValidationResult(valid=False, error="Uploaded file is empty.")

    # 4. Size check
    max_size = MAX_FILE_SIZES[ext]
    if len(file_content) > max_size:
        max_mb = max_size / (1024 * 1024)
        file_mb = len(file_content) / (1024 * 1024)
        return ValidationResult(
            valid=False,
            error=(
                f"File size {file_mb:.1f} MB exceeds the {max_mb:.0f} MB "
                f"limit for {ext} files."
            ),
        )

    # 5. MIME type check
    resolved_content_type = content_type or mimetypes.guess_type(filename)[0] or ""
    allowed_mimes = ALLOWED_MIME_TYPES[ext]
    if resolved_content_type and resolved_content_type.lower() not in {
        m.lower() for m in allowed_mimes
    }:
        return ValidationResult(
            valid=False,
            error=(
                f"Content type '{resolved_content_type}' does not match "
                f"expected types for {ext} files."
            ),
        )

    # 6. Magic bytes check (skip for CSV — no reliable signature)
    signatures = MAGIC_BYTES.get(ext)
    if signatures and not any(file_content.startswith(sig) for sig in signatures):
        return ValidationResult(
            valid=False,
            error=(
                f"File content does not match expected format for {ext}. "
                "The file may be corrupted or mislabeled."
            ),
        )

    return ValidationResult(valid=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_extension(filename: str) -> str:
    """Return the lowercased file extension including the dot."""
    dot_idx = filename.rfind(".")
    if dot_idx == -1:
        return ""
    return filename[dot_idx:].lower()
