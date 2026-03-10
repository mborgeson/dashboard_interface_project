"""
B&R Capital Real Estate Analytics Dashboard - FastAPI Application Entry Point

This is the main application entry point that configures:
- FastAPI application with metadata
- CORS middleware for frontend integration
- API versioning and routing
- Startup/shutdown lifecycle events
- Exception handlers
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.etag import ETagMiddleware
from app.middleware.rate_limiter import RateLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware, get_request_id
from app.services.data_extraction.scheduler import MarketDataScheduler
from app.services.extraction.monitor_scheduler import get_monitor_scheduler
from app.services.extraction.scheduler import (
    get_extraction_scheduler,
    run_scheduled_extraction,
)
from app.services.interest_rate_scheduler import InterestRateScheduler
from app.services.monitoring import MetricsMiddleware, get_metrics_manager
from app.services.report_worker import get_report_worker


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Security headers middleware for defense-in-depth.

    Adds security headers to all responses as a fallback
    if Nginx headers are not present.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Security headers (only add if not already present)
        if "X-Content-Type-Options" not in response.headers:
            response.headers["X-Content-Type-Options"] = "nosniff"
        if "X-Frame-Options" not in response.headers:
            response.headers["X-Frame-Options"] = "DENY"
        if "X-XSS-Protection" not in response.headers:
            # Set to 0: the "1; mode=block" value can introduce XSS vulnerabilities
            # in older browsers. Modern browsers ignore this header entirely.
            # See: https://owasp.org/www-project-secure-headers/
            response.headers["X-XSS-Protection"] = "0"
        if "Referrer-Policy" not in response.headers:
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if "Permissions-Policy" not in response.headers:
            response.headers["Permissions-Policy"] = (
                "geolocation=(), microphone=(), camera=(), payment=()"
            )

        # Cache control for API responses (prevent caching of sensitive data)
        if (
            request.url.path.startswith("/api/")
            and "Cache-Control" not in response.headers
        ):
            response.headers["Cache-Control"] = "no-store, private"

        # HSTS — only in production (behind TLS termination)
        if (
            settings.ENVIRONMENT == "production"
            and "Strict-Transport-Security" not in response.headers
        ):
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )

        # Content Security Policy (restrictive default)
        if "Content-Security-Policy" not in response.headers:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self' wss:; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )

        return response


class OriginValidationMiddleware(BaseHTTPMiddleware):
    """
    Origin validation for state-changing requests.

    CSRF NOTE: This application uses JWT Bearer tokens from localStorage,
    NOT cookies. Browsers do not auto-attach localStorage values to
    cross-origin requests, so CSRF attacks are inherently mitigated.
    This middleware provides defense-in-depth by rejecting state-changing
    requests from unexpected origins.

    Validates the Origin (or Referer) header on POST/PUT/PATCH/DELETE
    requests against the configured CORS_ORIGINS list. Requests without
    an Origin header (e.g., server-to-server, curl) are allowed through
    since they cannot be triggered by a browser-based CSRF attack.
    """

    # Methods that modify state and should be origin-checked
    STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in self.STATE_CHANGING_METHODS:
            origin = request.headers.get("origin")
            referer = request.headers.get("referer")

            # Extract origin from Referer if Origin header is absent
            check_origin = origin
            if not check_origin and referer:
                # Parse scheme + host from referer URL
                from urllib.parse import urlparse

                parsed = urlparse(referer)
                if parsed.scheme and parsed.netloc:
                    check_origin = f"{parsed.scheme}://{parsed.netloc}"

            # If an origin is present, validate it against allowed origins
            if check_origin:
                allowed = settings.CORS_ORIGINS
                if check_origin not in allowed:
                    logger.warning(
                        "Rejected request from disallowed origin",
                        origin=check_origin,
                        method=request.method,
                        path=request.url.path,
                    )
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Origin not allowed"},
                    )

            # No origin/referer header = non-browser client (curl, server-to-server)
            # These are safe because browsers always send Origin on cross-origin requests

        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifecycle manager.

    Handles startup and shutdown events for:
    - Database connections
    - Redis cache
    - WebSocket manager
    - ML model loading
    """
    # Startup
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    # Initialize metrics manager
    metrics_manager = get_metrics_manager()
    metrics_manager.initialize()
    logger.info("Metrics manager initialized")

    # Wire database engines into monitoring collectors
    from app.db.session import engine, sync_engine
    from app.services.monitoring.collectors import get_collector_registry

    collector_registry = get_collector_registry()
    collector_registry.database.set_engine(engine)
    collector_registry.database.set_sync_engine(sync_engine)
    collector_registry.connection_pool.set_engine(engine)
    collector_registry.connection_pool.set_sync_engine(sync_engine)
    logger.info("Connection pool monitoring initialized")

    # Initialize Redis (cache, rate limiter, token blacklist)
    try:
        from app.services.redis_service import get_redis_service

        await get_redis_service()
        logger.info("Redis service initialized", url=settings.REDIS_URL)
    except Exception as e:
        logger.warning(f"Redis unavailable, falling back to in-memory: {e}")

    # Initialize WebSocket connection manager
    try:
        from app.services.websocket_manager import get_connection_manager

        ws_manager = get_connection_manager()
        logger.info(
            "WebSocket connection manager initialized",
            max_per_client=ws_manager._max_connections_per_client,
        )
    except Exception as e:
        logger.warning(f"WebSocket manager initialization failed: {e}")
        ws_manager = None

    # await load_ml_models()

    # Initialize extraction scheduler
    extraction_scheduler = get_extraction_scheduler()
    await extraction_scheduler.initialize(
        enabled=settings.EXTRACTION_SCHEDULE_ENABLED,
        cron_expression=settings.EXTRACTION_SCHEDULE_CRON,
        timezone=settings.EXTRACTION_SCHEDULE_TIMEZONE,
    )
    extraction_scheduler.set_extraction_callback(run_scheduled_extraction)
    logger.info(
        "Extraction scheduler initialized",
        enabled=settings.EXTRACTION_SCHEDULE_ENABLED,
        cron=settings.EXTRACTION_SCHEDULE_CRON,
        timezone=settings.EXTRACTION_SCHEDULE_TIMEZONE,
    )

    # Initialize file monitor scheduler
    monitor_scheduler = get_monitor_scheduler()
    await monitor_scheduler.initialize(
        enabled=settings.FILE_MONITOR_ENABLED,
        interval_minutes=settings.FILE_MONITOR_INTERVAL_MINUTES,
        auto_extract=settings.AUTO_EXTRACT_ON_CHANGE,
        timezone=settings.EXTRACTION_SCHEDULE_TIMEZONE,
    )
    logger.info(
        "File monitor scheduler initialized",
        enabled=settings.FILE_MONITOR_ENABLED,
        interval_minutes=settings.FILE_MONITOR_INTERVAL_MINUTES,
        auto_extract=settings.AUTO_EXTRACT_ON_CHANGE,
    )

    # Initialize market data scheduler
    market_data_scheduler = MarketDataScheduler(settings)
    await market_data_scheduler.start()
    logger.info(
        "Market data scheduler initialized",
        enabled=settings.MARKET_DATA_EXTRACTION_ENABLED,
    )

    # Initialize interest rate scheduler
    interest_rate_scheduler = InterestRateScheduler(settings)
    await interest_rate_scheduler.start()
    logger.info(
        "Interest rate scheduler initialized",
        enabled=settings.INTEREST_RATE_SCHEDULE_ENABLED,
    )

    # Start report generation background worker
    report_worker = get_report_worker()
    await report_worker.start()
    logger.info("Report generation worker started")

    # Start cache background cleanup task (evicts expired in-memory entries)
    from app.core.cache import cache as cache_service

    await cache_service.start_cleanup_task()
    logger.info("Cache cleanup task started")

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application...")

    # Stop cache cleanup task
    await cache_service.stop_cleanup_task()
    logger.info("Cache cleanup task stopped")

    # Shutdown report worker
    await report_worker.stop()
    logger.info("Report generation worker stopped")

    # Shutdown interest rate scheduler
    await interest_rate_scheduler.stop()
    logger.info("Interest rate scheduler shutdown complete")

    # Shutdown market data scheduler
    await market_data_scheduler.stop()
    logger.info("Market data scheduler shutdown complete")

    # Shutdown file monitor scheduler
    await monitor_scheduler.shutdown()
    logger.info("File monitor scheduler shutdown complete")

    # Shutdown extraction scheduler
    await extraction_scheduler.shutdown()
    logger.info("Extraction scheduler shutdown complete")

    # Cleanup Redis
    try:
        from app.services.redis_service import _redis_service

        if _redis_service is not None:
            await _redis_service.disconnect()
            logger.info("Redis service disconnected")
    except Exception as e:
        logger.debug(f"Redis cleanup: {e}")

    # Gracefully disconnect all WebSocket connections
    try:
        if ws_manager is not None:
            active = ws_manager.connection_count
            if active > 0:
                for cid in list(ws_manager._connections.keys()):
                    await ws_manager.disconnect(cid)
                logger.info(
                    "WebSocket connections closed",
                    disconnected=active,
                )
            else:
                logger.info("WebSocket manager shutdown (no active connections)")
    except Exception as e:
        logger.warning(f"WebSocket manager shutdown error: {e}")

    logger.info("Application shutdown complete")


# Only expose API docs in development environment
_show_docs = settings.ENVIRONMENT == "development"

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    B&R Capital Real Estate Analytics Dashboard API

    Provides endpoints for:
    - Property analytics and deal management
    - ML-powered rent growth predictions
    - Real-time collaboration via WebSockets
    - Report generation and distribution
    """,
    openapi_url="/api/v1/openapi.json" if _show_docs else None,
    docs_url="/api/docs" if _show_docs else None,
    redoc_url="/api/redoc" if _show_docs else None,
    lifespan=lifespan,
)

# Configure CORS with production-ready settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
    expose_headers=["X-Request-ID", "ETag"],
    max_age=600,  # Cache preflight responses for 10 minutes
)

# Add performance monitoring middleware
app.add_middleware(MetricsMiddleware)

# Add rate limiting middleware (if enabled)
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)

# Add ETag middleware (conditional responses for GET requests)
app.add_middleware(ETagMiddleware)

# Add security headers middleware (defense-in-depth)
app.add_middleware(SecurityHeadersMiddleware)

# Add error handling middleware (catches unhandled exceptions, returns structured JSON)
app.add_middleware(ErrorHandlerMiddleware)

# Add origin validation middleware (defense-in-depth for state-changing requests)
app.add_middleware(OriginValidationMiddleware)

# Add request ID middleware (outermost — runs first so all other middleware can use it)
app.add_middleware(RequestIDMiddleware)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions globally."""
    rid = get_request_id() or str(id(exc))
    logger.exception(f"Unhandled exception (request_id={rid}): {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred",
            "request_id": rid,
        },
    )


# Include API router
app.include_router(api_router, prefix="/api/v1")


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint returning API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/api/docs" if _show_docs else "disabled",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.WORKERS,
        log_level=settings.LOG_LEVEL.lower(),
    )
