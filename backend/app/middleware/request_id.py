"""
Request ID middleware for correlation tracking.

Generates or propagates a unique request ID for every HTTP request,
making it available via:
- Response header: X-Request-ID
- request.state.request_id
- contextvars (for loguru and any code in the request lifecycle)
"""

import uuid
from contextvars import ContextVar

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Context variable holding the current request's correlation ID.
# Accessible from anywhere in the async call stack during a request.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")

REQUEST_ID_HEADER = "X-Request-ID"


def get_request_id() -> str:
    """Return the current request ID from context (empty string if outside a request)."""
    return request_id_ctx.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that assigns a correlation ID to every request.

    Behaviour:
    - If the client sends an ``X-Request-ID`` header, that value is reused
      (enables end-to-end correlation across services).
    - Otherwise a new UUID-4 is generated.
    - The ID is stored in ``request.state.request_id`` and in a
      :class:`~contextvars.ContextVar` so loguru (and any other code)
      can include it without explicit plumbing.
    - The ID is returned to the client via the ``X-Request-ID`` response header.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Accept client-provided ID or generate a new one
        rid = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())

        # Store in request state (available to route handlers)
        request.state.request_id = rid

        # Store in contextvar (available to loguru and any async code)
        token = request_id_ctx.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)

        # Echo the ID back to the caller
        response.headers[REQUEST_ID_HEADER] = rid
        return response
