"""
Logging configuration using Loguru.

Loguru provides unified logging for all application components with:
- Colored console output during development
- Rotating file output in production
- Request ID injection via contextvars
- Stdlib logging interception for third-party libraries

Request ID integration:
    The ``request_id`` field is automatically included in every log line
    when a request is in flight.  It reads from a :class:`contextvars.ContextVar`
    set by :class:`app.middleware.request_id.RequestIDMiddleware`, so no explicit
    plumbing is needed — just ``logger.info("...")`` from anywhere inside a
    request handler or downstream service and the ID will appear.
"""

import logging
import sys
from types import FrameType

from loguru import logger

from .config import settings


def _request_id_patcher(record: dict) -> None:
    """Inject the current request ID (if any) into every log record."""
    from app.middleware.request_id import get_request_id

    record["extra"]["request_id"] = get_request_id() or "-"


class _InterceptHandler(logging.Handler):
    """Redirect stdlib logging records into loguru.

    Installed on the root logger so that any library or module using
    ``logging.getLogger(__name__)`` has its output captured by loguru
    with correct level mapping and caller information.
    """

    def emit(self, record: logging.LogRecord) -> None:
        # Map stdlib log level to loguru level name
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno  # type: ignore[assignment]

        # Find the caller frame outside of the logging/loguru machinery
        frame: FrameType | None = logging.currentframe()
        depth = 0
        while frame is not None:
            filename = frame.f_code.co_filename
            if "logging" not in filename and "loguru" not in filename:
                break
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> None:
    """Configure application logging with loguru.

    Intercepts stdlib ``logging`` so that any remaining ``logging.getLogger()``
    callers (third-party libraries, legacy code) are routed through loguru
    with consistent formatting and request-ID injection.
    """
    # ── Loguru setup ──────────────────────────────────────────────
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
            retention=f"{settings.LOG_RETENTION_DAYS} days",
            compression="gz",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{name}:{function}:{line} | {extra[request_id]} | {message}",
            level="INFO",
        )

        # Error log file
        logger.add(
            "logs/error_{time:YYYY-MM-DD}.log",
            rotation="00:00",
            retention=f"{settings.LOG_ERROR_RETENTION_DAYS} days",
            compression="gz",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{name}:{function}:{line} | {extra[request_id]} | {message}",
            level="ERROR",
        )

    # ── Intercept stdlib logging into loguru ──────────────────────
    # Replace the root logger's handlers with our intercept handler so that
    # any code using ``import logging; logging.getLogger(...)`` is routed
    # through loguru with consistent formatting and request-ID injection.
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)


# Export configured logger
__all__ = ["logger", "setup_logging"]
