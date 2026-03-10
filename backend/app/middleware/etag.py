"""
ETag middleware for conditional HTTP responses.

Computes an ETag (SHA-256 hash of response body) for GET responses and
checks the If-None-Match request header. Returns 304 Not Modified when
the client already has the current version, eliminating redundant payload
transfer for unchanged data.

Only applies to:
- GET requests
- Non-streaming responses (responses with a body attribute)
"""

import hashlib

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

slog = structlog.get_logger("app.middleware.etag")


class ETagMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds ETag headers and handles conditional GET requests.

    Flow:
    1. Non-GET requests pass through unchanged.
    2. GET requests are processed normally to obtain the response.
    3. If the response has a body, compute its SHA-256 digest as the ETag.
    4. If the request's If-None-Match header matches the ETag, return 304.
    5. Otherwise, attach the ETag header and return the full response.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Only handle GET requests
        if request.method != "GET":
            return await call_next(request)

        response = await call_next(request)

        # Skip streaming responses (no .body attribute)
        if not hasattr(response, "body"):
            return response

        body: bytes = response.body

        # Skip empty bodies
        if not body:
            return response

        # Compute ETag as quoted SHA-256 hex digest
        etag = f'"{hashlib.sha256(body).hexdigest()}"'

        # Check If-None-Match header
        if_none_match = request.headers.get("if-none-match")
        if if_none_match:
            # Handle multiple ETags in If-None-Match (comma-separated)
            client_etags = [t.strip() for t in if_none_match.split(",")]
            if etag in client_etags or "*" in client_etags:
                slog.debug(
                    "etag_match_304",
                    path=request.url.path,
                    etag=etag,
                )
                return Response(
                    status_code=304,
                    headers={"ETag": etag},
                )

        # Attach ETag to the response
        response.headers["ETag"] = etag
        return response
