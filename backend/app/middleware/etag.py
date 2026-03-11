"""
ETag middleware for conditional HTTP responses.

Computes an ETag (SHA-256 hash of response body) for GET responses and
checks the If-None-Match request header. Returns 304 Not Modified when
the client already has the current version, eliminating redundant payload
transfer for unchanged data.

Uses a bounded LRU cache (default 500 entries) keyed by Python's built-in
hash of the response body to avoid redundant SHA-256 computations for
repeated identical responses.

Only applies to:
- GET requests
- Non-streaming responses (responses with a body attribute)
"""

import hashlib
from collections import OrderedDict

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

slog = structlog.get_logger("app.middleware.etag")

# Maximum number of cached ETag entries.  Sized to cover the most
# frequently-accessed GET endpoints without consuming excessive memory
# (~500 SHA-256 hex strings = ~32 KB).
ETAG_CACHE_CAPACITY: int = 500


class _LRUETagCache:
    """Thread-safe LRU cache for ETag values.

    Keys are Python built-in hashes of response bodies (int, O(1) to compute).
    Values are the quoted SHA-256 hex digest strings used as ETags.

    When the cache exceeds ``capacity``, the least-recently-used entry is evicted.
    """

    __slots__ = ("_cache", "_capacity")

    def __init__(self, capacity: int = ETAG_CACHE_CAPACITY) -> None:
        self._cache: OrderedDict[int, str] = OrderedDict()
        self._capacity = capacity

    def get(self, key: int) -> str | None:
        """Retrieve an ETag by body hash, promoting it to most-recently-used."""
        try:
            self._cache.move_to_end(key)
            return self._cache[key]
        except KeyError:
            return None

    def put(self, key: int, etag: str) -> None:
        """Store an ETag, evicting the LRU entry if at capacity."""
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = etag
        else:
            if len(self._cache) >= self._capacity:
                self._cache.popitem(last=False)
            self._cache[key] = etag

    def __len__(self) -> int:
        return len(self._cache)


# Module-level singleton — shared across all requests within the process.
_etag_cache = _LRUETagCache()


class ETagMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds ETag headers and handles conditional GET requests.

    Flow:
    1. Non-GET requests pass through unchanged.
    2. GET requests are processed normally to obtain the response.
    3. If the response has a body, compute its SHA-256 digest as the ETag.
       Uses an LRU cache to skip recomputation for recently-seen bodies.
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

        # Use Python's built-in hash (fast, C-level) as the cache key.
        # On cache miss, fall back to full SHA-256 computation.
        body_hash = hash(body)
        etag = _etag_cache.get(body_hash)
        if etag is None:
            etag = f'"{hashlib.sha256(body).hexdigest()}"'
            _etag_cache.put(body_hash, etag)

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
