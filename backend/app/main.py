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

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.middleware.rate_limiter import RateLimitMiddleware
from app.services.extraction.scheduler import (
    get_extraction_scheduler,
    run_scheduled_extraction,
)
from app.services.monitoring import MetricsMiddleware, get_metrics_manager


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

    # Initialize services (will be implemented in services module)
    # await init_redis()
    # await init_websocket_manager()
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

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application...")

    # Shutdown extraction scheduler
    await extraction_scheduler.shutdown()
    logger.info("Extraction scheduler shutdown complete")

    # Cleanup services
    # await close_redis()
    # await close_websocket_manager()

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
    expose_headers=["X-Request-ID"],
    max_age=600,  # Cache preflight responses for 10 minutes
)

# Add performance monitoring middleware
app.add_middleware(MetricsMiddleware)

# Add rate limiting middleware (if enabled)
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions globally."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred",
            "error_id": str(id(exc)),  # For log correlation
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
