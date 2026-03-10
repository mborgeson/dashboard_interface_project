"""
Structured error handling middleware.

Catches common exception types and returns consistent JSON error responses
with request_id correlation. This eliminates the need for repetitive
try/except blocks in individual endpoint handlers.

Exception handling priority:
1. HTTPException — passed through to FastAPI's built-in handler
2. SQLAlchemyError — logged, returns 500 with generic message
3. pydantic ValidationError — returns 422 with details
4. PermissionError — returns 403
5. ValueError — returns 400
6. Generic Exception — logged, returns 500 with request_id for correlation
"""

import structlog
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.middleware.request_id import get_request_id

slog = structlog.get_logger("app.middleware.error_handler")


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
            slog.error(
                "database_error",
                request_id=rid,
                path=request.url.path,
                method=request.method,
                error_type="database_error",
                error=str(exc),
            )
            return _build_error_response(
                status_code=500,
                detail="A database error occurred. Please try again later.",
                error_type="database_error",
                request_id=rid,
            )
        except ValidationError as exc:
            rid = get_request_id() or "unknown"
            slog.warning(
                "validation_error",
                request_id=rid,
                path=request.url.path,
                method=request.method,
                error_type="validation_error",
                error_count=exc.error_count(),
            )
            return _build_error_response(
                status_code=422,
                detail=str(exc),
                error_type="validation_error",
                request_id=rid,
            )
        except PermissionError as exc:
            rid = get_request_id() or "unknown"
            slog.warning(
                "permission_denied",
                request_id=rid,
                path=request.url.path,
                method=request.method,
                error_type="permission_error",
            )
            return _build_error_response(
                status_code=403,
                detail=str(exc) or "Permission denied",
                error_type="permission_error",
                request_id=rid,
            )
        except ValueError as exc:
            rid = get_request_id() or "unknown"
            slog.warning(
                "value_error",
                request_id=rid,
                path=request.url.path,
                method=request.method,
                error_type="value_error",
                error=str(exc),
            )
            return _build_error_response(
                status_code=400,
                detail=str(exc),
                error_type="value_error",
                request_id=rid,
            )
        except Exception:
            rid = get_request_id() or "unknown"
            slog.exception(
                "unhandled_exception",
                request_id=rid,
                path=request.url.path,
                method=request.method,
                error_type="internal_error",
            )
            return _build_error_response(
                status_code=500,
                detail="An unexpected error occurred",
                error_type="internal_error",
                request_id=rid,
            )
