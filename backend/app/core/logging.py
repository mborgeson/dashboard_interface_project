"""
Logging configuration using Loguru.

Request ID integration:
    The ``request_id`` field is automatically included in every log line
    when a request is in flight.  It reads from a :class:`contextvars.ContextVar`
    set by :class:`app.middleware.request_id.RequestIDMiddleware`, so no explicit
    plumbing is needed — just ``logger.info("...")`` from anywhere inside a
    request handler or downstream service and the ID will appear.
"""

import sys

from loguru import logger

from .config import settings


def _request_id_patcher(record: dict) -> None:
    """Inject the current request ID (if any) into every log record."""
    from app.middleware.request_id import get_request_id

    record["extra"]["request_id"] = get_request_id() or "-"


def setup_logging() -> None:
    """Configure application logging."""
    # Remove default handler
    logger.remove()

    # Patch every record with request_id before formatting
    logger.configure(patcher=_request_id_patcher)  # type: ignore[arg-type]

    # Console handler with colored output (includes request_id)
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<dim>{extra[request_id]}</dim> | "
        "<level>{message}</level>",
        level=settings.LOG_LEVEL,
    )

    # File handler for production
    if settings.ENVIRONMENT == "production":
        logger.add(
            "logs/app_{time:YYYY-MM-DD}.log",
            rotation="00:00",
            retention="30 days",
            compression="gz",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{name}:{function}:{line} | {extra[request_id]} | {message}",
            level="INFO",
        )

        # Error log file
        logger.add(
            "logs/error_{time:YYYY-MM-DD}.log",
            rotation="00:00",
            retention="90 days",
            compression="gz",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{name}:{function}:{line} | {extra[request_id]} | {message}",
            level="ERROR",
        )


# Export configured logger
__all__ = ["logger", "setup_logging"]
