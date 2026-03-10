"""
Slow query detection and logging via SQLAlchemy event listeners.

Attaches ``before_cursor_execute`` / ``after_cursor_execute`` listeners to
a SQLAlchemy engine.  Queries that exceed the configurable threshold
(``SLOW_QUERY_THRESHOLD_MS``) are logged with structured context via
structlog and recorded in a Prometheus histogram.

Usage:
    from app.db.query_logger import attach_query_logger
    attach_query_logger(engine)       # async engine
    attach_query_logger(sync_engine)  # sync engine
"""

from __future__ import annotations

import re
import time
import traceback
from typing import Any

import structlog

from app.services.monitoring.metrics import DB_QUERY_LATENCY

logger = structlog.get_logger("app.db.query_logger")

# ---------------------------------------------------------------------------
# Prometheus histogram dedicated to slow-query tracking (finer buckets at the
# high end than the generic DB_QUERY_LATENCY histogram).
# ---------------------------------------------------------------------------
try:
    from prometheus_client import Counter, Histogram

    SLOW_QUERY_HISTOGRAM = Histogram(
        name="database_slow_query_duration_seconds",
        documentation="Duration of queries that exceeded the slow-query threshold",
        labelnames=["statement_type"],
        buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
    )

    SLOW_QUERY_COUNT = Counter(
        name="database_slow_queries_total",
        documentation="Total number of queries that exceeded the slow-query threshold",
        labelnames=["statement_type"],
    )
except Exception:
    # If prometheus_client is unavailable or metrics already registered, degrade
    # gracefully — logging still works.
    SLOW_QUERY_HISTOGRAM = None  # type: ignore[assignment]
    SLOW_QUERY_COUNT = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------
_MAX_QUERY_LOG_LENGTH = 1024  # Truncate logged SQL to this many characters
_PARAM_SANITIZE_PATTERN = re.compile(
    r"(password|secret|token|key|authorization|credential)",
    re.IGNORECASE,
)

# Key used to stash the start time on the execution context
_CONTEXT_KEY = "_slow_query_start_time"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _truncate(text: str, max_len: int = _MAX_QUERY_LOG_LENGTH) -> str:
    """Truncate *text* to *max_len* chars, appending an ellipsis if trimmed."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def _sanitize_params(params: Any) -> dict[str, Any] | str | None:
    """Return a sanitised representation of query parameters.

    Sensitive-looking keys (password, secret, token, …) are masked.
    """
    if params is None:
        return None

    # Handle tuple/list params (positional)
    if isinstance(params, list | tuple):
        return "[positional params hidden]"

    if not isinstance(params, dict):
        return str(type(params).__name__)

    sanitized: dict[str, Any] = {}
    for key, value in params.items():
        if _PARAM_SANITIZE_PATTERN.search(str(key)):
            sanitized[key] = "***"
        else:
            sanitized[key] = value
    return sanitized


def _extract_statement_type(statement: str) -> str:
    """Return the SQL verb (SELECT, INSERT, UPDATE, …) from a statement."""
    stripped = statement.lstrip().upper()
    for verb in (
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "CREATE",
        "ALTER",
        "DROP",
        "WITH",
    ):
        if stripped.startswith(verb):
            return verb
    return "OTHER"


def _caller_context() -> str:
    """Walk the stack to find the first frame outside SQLAlchemy / this module."""
    for frame_info in traceback.extract_stack():
        filename = frame_info.filename
        if (
            "sqlalchemy" not in filename
            and "query_logger" not in filename
            and "site-packages" not in filename
        ):
            return f"{frame_info.filename}:{frame_info.lineno} in {frame_info.name}"
    return "unknown"


# ---------------------------------------------------------------------------
# Event listeners
# ---------------------------------------------------------------------------


def _before_cursor_execute(
    conn: Any,
    cursor: Any,
    statement: str,
    parameters: Any,
    context: Any,
    executemany: bool,
) -> None:
    """Record the wall-clock time before a query executes."""
    conn.info[_CONTEXT_KEY] = time.perf_counter()


def _after_cursor_execute(
    conn: Any,
    cursor: Any,
    statement: str,
    parameters: Any,
    context: Any,
    executemany: bool,
) -> None:
    """Check elapsed time after a query and log if it exceeds the threshold."""
    start = conn.info.pop(_CONTEXT_KEY, None)
    if start is None:
        return

    elapsed_s = time.perf_counter() - start
    elapsed_ms = elapsed_s * 1000

    # Lazy import to avoid circular dependency at module load time
    from app.core.config import settings

    threshold_ms = settings.SLOW_QUERY_THRESHOLD_MS

    # Always feed the generic DB_QUERY_LATENCY histogram so overall query
    # duration tracking works even for fast queries.
    stmt_type = _extract_statement_type(statement)
    DB_QUERY_LATENCY.labels(operation=stmt_type.lower(), table="all").observe(elapsed_s)

    if elapsed_ms < threshold_ms:
        return

    # --- Slow query detected ---

    # Prometheus metrics
    if SLOW_QUERY_HISTOGRAM is not None:
        SLOW_QUERY_HISTOGRAM.labels(statement_type=stmt_type).observe(elapsed_s)
    if SLOW_QUERY_COUNT is not None:
        SLOW_QUERY_COUNT.labels(statement_type=stmt_type).inc()

    # Build structured log payload
    log_data: dict[str, Any] = {
        "event": "slow_query_detected",
        "duration_ms": round(elapsed_ms, 2),
        "threshold_ms": threshold_ms,
        "statement_type": stmt_type,
        "query": _truncate(statement),
        "caller": _caller_context(),
        "executemany": executemany,
    }

    if settings.SLOW_QUERY_LOG_PARAMS:
        log_data["params"] = _sanitize_params(parameters)

    logger.warning("slow query detected", **log_data)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def attach_query_logger(target_engine: Any) -> None:
    """Attach slow-query event listeners to a SQLAlchemy engine.

    Works for both sync ``Engine`` and async ``AsyncEngine`` (via its
    underlying ``sync_engine``).
    """
    from sqlalchemy import event
    from sqlalchemy.ext.asyncio import AsyncEngine

    # AsyncEngine wraps a sync engine — listeners must go on the sync side.
    if isinstance(target_engine, AsyncEngine):
        core_engine = target_engine.sync_engine
    else:
        core_engine = target_engine

    event.listen(core_engine, "before_cursor_execute", _before_cursor_execute)
    event.listen(core_engine, "after_cursor_execute", _after_cursor_execute)
