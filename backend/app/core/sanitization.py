"""
Input sanitization utilities for HTML/XSS prevention.

Strips HTML tags and escapes dangerous characters from user-facing text
fields. Uses Python stdlib only (re, html) — no external dependencies.
"""

import html
import re
from collections.abc import Callable
from typing import Any

# Pattern to match HTML tags (including self-closing and malformed)
_HTML_TAG_RE = re.compile(r"<[^>]*>|<[^>]*$", re.DOTALL)

# Pattern to match HTML/JS event handlers (e.g., onerror=, onclick=)
_EVENT_HANDLER_RE = re.compile(r"\b(on\w+)\s*=", re.IGNORECASE)

# Pattern to match javascript: / vbscript: / data: URI schemes
_DANGEROUS_URI_RE = re.compile(r"(javascript|vbscript|data)\s*:", re.IGNORECASE)


def strip_html_tags(value: str) -> str:
    """Remove all HTML tags from a string.

    Also removes event handler attributes and dangerous URI schemes
    that could survive tag stripping in malformed HTML.

    Args:
        value: The input string to sanitize.

    Returns:
        The sanitized string with HTML tags removed.
    """
    # First pass: strip HTML tags
    cleaned = _HTML_TAG_RE.sub("", value)

    # Remove dangerous URI schemes
    cleaned = _DANGEROUS_URI_RE.sub("", cleaned)

    # Remove event handler patterns (onerror=, onclick=, etc.)
    cleaned = _EVENT_HANDLER_RE.sub("", cleaned)

    # Decode any HTML entities that might have been used for obfuscation,
    # then strip tags again in case decoding revealed new tags
    decoded = html.unescape(cleaned)
    cleaned = _HTML_TAG_RE.sub("", decoded)

    # Final pass: remove dangerous patterns from decoded content
    cleaned = _DANGEROUS_URI_RE.sub("", cleaned)
    cleaned = _EVENT_HANDLER_RE.sub("", cleaned)

    return cleaned.strip()


def sanitize_string(value: str | None) -> str | None:
    """Sanitize a string value, handling None gracefully.

    Args:
        value: The input string or None.

    Returns:
        Sanitized string, or None if input was None.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    if not value.strip():
        return value
    return strip_html_tags(value)


def sanitize_string_list(values: list[str] | None) -> list[str] | None:
    """Sanitize a list of strings (e.g., tags).

    Args:
        values: List of strings or None.

    Returns:
        List with each string sanitized, or None if input was None.
    """
    if values is None:
        return None
    return [strip_html_tags(v) if isinstance(v, str) else v for v in values]


def make_sanitized_validator(*field_names: str) -> Callable[..., Any]:
    """Create a Pydantic model_validator that sanitizes specified string fields.

    Usage in a Pydantic model::

        from pydantic import model_validator
        from app.core.sanitization import make_sanitized_validator

        class MySchema(BaseSchema):
            name: str
            notes: str | None = None

            _sanitize = model_validator(mode="before")(
                make_sanitized_validator("name", "notes")
            )

    Args:
        *field_names: Names of string fields to sanitize.

    Returns:
        A classmethod-compatible validator function.
    """

    def _validator(cls: type, values: Any) -> Any:  # noqa: ANN401
        if isinstance(values, dict):
            for field in field_names:
                if field in values and isinstance(values[field], str):
                    values[field] = sanitize_string(values[field])
            # Also sanitize list[str] fields like tags
            for field in field_names:
                if field in values and isinstance(values[field], list):
                    values[field] = sanitize_string_list(values[field])
        return values

    return _validator  # type: ignore[return-value]
