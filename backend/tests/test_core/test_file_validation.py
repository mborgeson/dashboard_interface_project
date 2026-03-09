"""Tests for server-side file upload validation."""

import pytest

from app.core.file_validation import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZES,
    ValidationResult,
    validate_upload,
)

# ---------------------------------------------------------------------------
# Valid magic-byte prefixes for building test payloads
# ---------------------------------------------------------------------------

PK_HEADER = b"PK\x03\x04" + b"\x00" * 100  # ZIP-based (xlsx, xlsm, docx)
OLE2_HEADER = b"\xd0\xcf\x11\xe0" + b"\x00" * 100  # OLE2 (xls)
PDF_HEADER = b"%PDF-1.7" + b"\x00" * 100  # PDF
CSV_CONTENT = b"col_a,col_b\n1,2\n3,4\n"  # CSV (no magic bytes)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_content(ext: str) -> bytes:
    """Return minimal valid content for a given extension."""
    mapping: dict[str, bytes] = {
        ".xlsx": PK_HEADER,
        ".xlsm": PK_HEADER,
        ".xls": OLE2_HEADER,
        ".pdf": PDF_HEADER,
        ".csv": CSV_CONTENT,
        ".docx": PK_HEADER,
    }
    return mapping[ext]


# ---------------------------------------------------------------------------
# Tests: valid files pass
# ---------------------------------------------------------------------------

class TestValidFiles:
    """All supported file types should pass validation."""

    @pytest.mark.parametrize("ext", sorted(ALLOWED_EXTENSIONS))
    def test_valid_file_passes(self, ext: str) -> None:
        content = _valid_content(ext)
        result = validate_upload(f"report{ext}", "application/octet-stream", content)
        assert result.valid is True
        assert result.error is None

    def test_xlsx_with_correct_mime(self) -> None:
        result = validate_upload(
            "budget.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            PK_HEADER,
        )
        assert result.valid is True

    def test_pdf_with_correct_mime(self) -> None:
        result = validate_upload("lease.pdf", "application/pdf", PDF_HEADER)
        assert result.valid is True

    def test_csv_no_mime(self) -> None:
        """CSV with None content_type should still pass (guessed from ext)."""
        result = validate_upload("data.csv", None, CSV_CONTENT)
        assert result.valid is True


# ---------------------------------------------------------------------------
# Tests: invalid extensions rejected
# ---------------------------------------------------------------------------

class TestInvalidExtension:
    @pytest.mark.parametrize(
        "filename",
        ["malware.exe", "script.sh", "image.png", "archive.zip", "macro.bat"],
    )
    def test_disallowed_extension(self, filename: str) -> None:
        result = validate_upload(filename, "application/octet-stream", b"\x00" * 100)
        assert result.valid is False
        assert "not allowed" in (result.error or "")

    def test_no_extension(self) -> None:
        result = validate_upload("README", "application/octet-stream", b"hello")
        assert result.valid is False
        assert "not allowed" in (result.error or "")

    def test_no_filename(self) -> None:
        result = validate_upload(None, "application/octet-stream", b"hello")
        assert result.valid is False
        assert "Filename is required" in (result.error or "")

    def test_empty_filename(self) -> None:
        result = validate_upload("", "application/octet-stream", b"hello")
        assert result.valid is False
        assert "Filename is required" in (result.error or "")


# ---------------------------------------------------------------------------
# Tests: oversized files rejected
# ---------------------------------------------------------------------------

class TestOversizedFiles:
    def test_xlsx_over_limit(self) -> None:
        big = PK_HEADER + b"\x00" * (MAX_FILE_SIZES[".xlsx"] + 1)
        result = validate_upload("huge.xlsx", "application/octet-stream", big)
        assert result.valid is False
        assert "exceeds" in (result.error or "")

    def test_pdf_over_limit(self) -> None:
        big = PDF_HEADER + b"\x00" * (MAX_FILE_SIZES[".pdf"] + 1)
        result = validate_upload("huge.pdf", "application/pdf", big)
        assert result.valid is False
        assert "exceeds" in (result.error or "")

    def test_csv_over_limit(self) -> None:
        big = b"a,b\n" * (MAX_FILE_SIZES[".csv"] // 4 + 1)
        result = validate_upload("huge.csv", "text/csv", big)
        assert result.valid is False
        assert "exceeds" in (result.error or "")

    def test_file_exactly_at_limit(self) -> None:
        """File exactly at the limit should pass."""
        exact = PK_HEADER + b"\x00" * (MAX_FILE_SIZES[".xlsx"] - len(PK_HEADER))
        result = validate_upload("exact.xlsx", "application/octet-stream", exact)
        assert result.valid is True


# ---------------------------------------------------------------------------
# Tests: empty files
# ---------------------------------------------------------------------------

class TestEmptyFiles:
    @pytest.mark.parametrize("ext", [".xlsx", ".pdf", ".csv"])
    def test_empty_file_rejected(self, ext: str) -> None:
        result = validate_upload(f"empty{ext}", "application/octet-stream", b"")
        assert result.valid is False
        assert "empty" in (result.error or "").lower()


# ---------------------------------------------------------------------------
# Tests: MIME type mismatches
# ---------------------------------------------------------------------------

class TestMimeTypeMismatch:
    def test_pdf_extension_with_excel_mime(self) -> None:
        result = validate_upload(
            "fake.pdf",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            PDF_HEADER,
        )
        assert result.valid is False
        assert "Content type" in (result.error or "")

    def test_xlsx_extension_with_pdf_mime(self) -> None:
        result = validate_upload(
            "fake.xlsx",
            "application/pdf",
            PK_HEADER,
        )
        assert result.valid is False
        assert "Content type" in (result.error or "")

    def test_csv_with_html_mime(self) -> None:
        result = validate_upload("data.csv", "text/html", CSV_CONTENT)
        assert result.valid is False
        assert "Content type" in (result.error or "")


# ---------------------------------------------------------------------------
# Tests: magic bytes mismatch
# ---------------------------------------------------------------------------

class TestMagicBytesMismatch:
    def test_xlsx_with_pdf_content(self) -> None:
        """An .xlsx file whose bytes start with %PDF should fail."""
        result = validate_upload("report.xlsx", "application/octet-stream", PDF_HEADER)
        assert result.valid is False
        assert "does not match expected format" in (result.error or "")

    def test_pdf_with_zip_content(self) -> None:
        """A .pdf file whose bytes start with PK should fail."""
        result = validate_upload("doc.pdf", "application/pdf", PK_HEADER)
        assert result.valid is False
        assert "does not match expected format" in (result.error or "")

    def test_xls_with_random_content(self) -> None:
        result = validate_upload(
            "old.xls", "application/vnd.ms-excel", b"\x00\x01\x02\x03" + b"\x00" * 100
        )
        assert result.valid is False
        assert "does not match expected format" in (result.error or "")

    def test_csv_skips_magic_check(self) -> None:
        """CSV has no magic bytes — any content should pass magic check."""
        result = validate_upload("data.csv", "text/csv", b"anything,goes\n")
        assert result.valid is True


# ---------------------------------------------------------------------------
# Tests: ValidationResult dataclass
# ---------------------------------------------------------------------------

class TestValidationResult:
    def test_defaults(self) -> None:
        r = ValidationResult(valid=True)
        assert r.valid is True
        assert r.error is None

    def test_with_error(self) -> None:
        r = ValidationResult(valid=False, error="bad file")
        assert r.valid is False
        assert r.error == "bad file"
