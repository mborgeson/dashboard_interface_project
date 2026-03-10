# ADR-011: Structured error handling middleware with correlation IDs

## Status
Accepted

## Context
Error responses across the API were inconsistent — some endpoints returned plain strings, others returned ad-hoc JSON objects, and unhandled exceptions surfaced as generic 500 responses with no traceability. Debugging production issues required correlating logs across multiple services and request boundaries, which was difficult without a shared identifier.

## Decision
We implemented a structured error handling middleware (`backend/app/middleware/error_handler.py`) that standardizes all error responses and adds request tracing:

- **Consistent error format**: All error responses follow a single schema with `status`, `error_code`, `message`, `detail` (optional), and `request_id` fields.
- **Request ID tracking**: Every incoming request is assigned a unique `X-Request-ID` (UUID). If the client sends one, it is preserved; otherwise the middleware generates it. The ID is included in the response headers and the error body.
- **Correlation IDs**: For operations that span multiple internal calls (e.g., extraction pipelines), a `X-Correlation-ID` header groups related requests for log aggregation.
- **Exception mapping**: Known exception types (`ValidationError`, `NotFoundError`, `PermissionError`, `ApiError`) map to appropriate HTTP status codes. Unknown exceptions return 500 with the request ID but no internal details.
- **Logging integration**: All errors are logged with the request ID and correlation ID via Loguru, enabling end-to-end tracing from client to server logs.

## Consequences
- API consumers receive predictable error shapes with actionable error codes, improving frontend error handling.
- Request IDs enable rapid debugging by correlating a user-reported error to the exact server-side log entry.
- All exceptions are caught at the middleware layer, so endpoints do not need individual try/except blocks for generic error formatting.
- The middleware adds a small overhead to every request for ID generation and header injection, which is negligible in practice.
