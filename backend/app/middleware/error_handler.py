"""
Structured error handling middleware.

Catches common exception types and returns consistent JSON error responses
with request_id correlation. This eliminates the need for repetitive
try/except blocks in individual endpoint handlers.

Exception handling priority:
1. HTTPException — passed through to FastAPI's built-in handler
2. SQLAlchemyError — logged, returns 500 with generic message
3. pydantic ValidationError — returns 422 with sanitized details
4. PermissionError — returns 403
5. ValueError — returns 400 with sanitized message
6. Generic Exception — logged, returns 500 with request_id for correlation

Security: Error messages are sanitized before being returned to clients.
Internal details (file paths, SQL queries, tracebacks) are logged server-side
but never exposed in API responses.
"""

import re

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.middleware.request_id import get_request_id

# Patterns that indicate internal details that should not be exposed to clients
_INTERNAL_DETAIL_PATTERNS = [
    re.compile(r"(File|Traceback|at 0x[0-9a-fA-F]+)", re.IGNORECASE),
    re.compile(r"(/[a-z_]+/[a-z_]+\.[a-z]+)", re.IGNORECASE),  # file paths
    re.compile(r"(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE)\s", re.IGNORECASE),  # SQL
    re.compile(r"(psycopg|asyncpg|sqlalchemy\.|sqlite3\.)", re.IGNORECASE),  # DB libs
    re.compile(r"(\.py:\d+|line \d+)", re.IGNORECASE),  # stack frames
]

_FALLBACK_MESSAGES = {
    "value_error": "Invalid request. Please check your input and try again.",
    "validation_error": "Request validation failed. Please check your input.",
    "permission_error": "Permission denied",
}


def _sanitize_error_message(message: str, error_type: str) -> str:
    """Sanitize an error message for client consumption.

    Returns the original message if it appears safe, or a generic fallback
    if the message contains internal details (file paths, SQL, tracebacks).
    """
    if not message:
        return _FALLBACK_MESSAGES.get(error_type, "An error occurred")
    for pattern in _INTERNAL_DETAIL_PATTERNS:
        if pattern.search(message):
            logger.debug(
                "error_message_sanitized error_type={} reason=internal details detected",
                error_type,
            )
            return _FALLBACK_MESSAGES.get(error_type, "An error occurred")
    return message


def _build_error_response(
    status_code: int,
    detail: str,
    error_type: str,
    request_id: str,
) -> JSONResponse:
    """Build a structured JSON error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": detail,
            "request_id": request_id,
            "type": error_type,
        },
    )


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware that catches unhandled exceptions and returns structured
    JSON error responses with request_id correlation.

    HTTPExceptions are re-raised so FastAPI's built-in handler processes
    them (preserving status codes, headers, and detail messages).

    All other exceptions are caught, logged, and mapped to appropriate
    HTTP status codes.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await call_next(request)
        except HTTPException:
            # Let FastAPI's built-in exception handler deal with these
            raise
        except SQLAlchemyError as exc:
            rid = get_request_id() or "unknown"
            logger.error(
                "database_error request_id={} path={} method={} error={}",
                rid,
                request.url.path,
                request.method,
                str(exc),
            )
            return _build_error_response(
                status_code=500,
                detail="A database error occurred. Please try again later.",
                error_type="database_error",
                request_id=rid,
            )
        except ValidationError as exc:
            rid = get_request_id() or "unknown"
            raw_message = str(exc)
            logger.warning(
                "validation_error request_id={} path={} method={} error_count={}",
                rid,
                request.url.path,
                request.method,
                exc.error_count(),
            )
            return _build_error_response(
                status_code=422,
                detail=_sanitize_error_message(raw_message, "validation_error"),
                error_type="validation_error",
                request_id=rid,
            )
        except PermissionError as exc:
            rid = get_request_id() or "unknown"
            raw_message = str(exc)
            logger.warning(
                "permission_denied request_id={} path={} method={}",
                rid,
                request.url.path,
                request.method,
            )
            return _build_error_response(
                status_code=403,
                detail=_sanitize_error_message(raw_message, "permission_error"),
                error_type="permission_error",
                request_id=rid,
            )
        except ValueError as exc:
            rid = get_request_id() or "unknown"
            raw_message = str(exc)
            logger.warning(
                "value_error request_id={} path={} method={} detail={}",
                rid,
                request.url.path,
                request.method,
                raw_message,
            )
            return _build_error_response(
                status_code=400,
                detail=_sanitize_error_message(raw_message, "value_error"),
                error_type="value_error",
                request_id=rid,
            )
        except Exception:
            rid = get_request_id() or "unknown"
            logger.opt(exception=True).error(
                "unhandled_exception request_id={} path={} method={}",
                rid,
                request.url.path,
                request.method,
            )
            return _build_error_response(
                status_code=500,
                detail="An unexpected error occurred",
                error_type="internal_error",
                request_id=rid,
            )
