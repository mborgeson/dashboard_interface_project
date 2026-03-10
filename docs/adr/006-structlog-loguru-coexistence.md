# ADR-006: structlog + loguru coexistence for structured logging

## Status
Accepted

## Context
The application needs two logging audiences: developers reading console output during development, and log aggregation systems ingesting machine-parseable events in production. A single logging library does not serve both needs well. Loguru excels at colored, human-readable console output with file rotation; structlog excels at structured key-value event logging with JSON serialization.

## Decision
Both libraries are configured in `backend/app/core/logging.py` and coexist throughout the codebase:

- **loguru** (`from loguru import logger`): Used for general application logging -- startup messages, debug traces, error reporting. Configured with colored console output in development and rotating file handlers in production.
- **structlog** (`structlog.get_logger()`): Used for structured event logging in security-sensitive and auditable paths -- auth events, CRUD mutations, extraction pipeline operations. Outputs JSON in production for log aggregator ingestion.

Both systems share a request ID injected via `contextvars` from `RequestIDMiddleware`, ensuring log correlation across the two outputs. The loguru `patcher` and structlog `_add_request_id` processor both read from the same `ContextVar`.

## Consequences
- Developers get readable console logs during development without sacrificing structured output in production.
- Two logging imports (`logger` from loguru, `slog` from structlog) coexist in some modules (e.g., `auth.py`), which requires discipline about which to use where.
- Log aggregation pipelines only need to parse structlog's JSON output; loguru's file output serves as a human-readable backup.
- Request ID correlation works across both systems, enabling end-to-end request tracing.
