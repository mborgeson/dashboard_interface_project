# ADR-008: Unified fetch client (supersedes dual-client pattern)

## Status
Accepted

## Context
ADR-004 established a dual-client pattern where new code used a fetch-based client while legacy code remained on axios. Over time, all axios call sites were migrated to the fetch client, making the axios dependency unnecessary. Maintaining two clients added cognitive overhead and bundle size with no remaining benefit.

## Decision
We fully removed the axios client (`src/lib/api.ts`) and consolidated all API communication through the fetch-based client at `src/lib/api/client.ts`. The unified client provides:

- Typed request helpers (`get`, `post`, `put`, `delete`) with generic response types.
- Automatic Bearer token injection from `localStorage` via the auth store.
- ETag-based caching to avoid redundant network requests for unchanged resources.
- Automatic token refresh on 401 responses with request retry.
- Structured error handling via a custom `ApiError` class with status codes and response bodies.
- Zod schema validation on responses (schemas in `src/lib/api/schemas/`).

This supersedes ADR-004.

## Consequences
- Single client pattern eliminates the "which client do I use?" question for developers.
- The axios dependency is removed, reducing the frontend bundle size.
- ETag caching reduces unnecessary data transfer for frequently polled endpoints.
- All API error handling follows a single, consistent pattern across the application.
