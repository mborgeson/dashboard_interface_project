# ADR-004: Dual API client pattern (axios legacy + fetch new)

## Status
Accepted

## Context
The frontend originally used an axios-based API client (`src/lib/api.ts`) with interceptors for auth token injection and automatic refresh on 401 responses. As the codebase grew, we wanted a lighter client without the axios dependency for new feature modules, but could not justify a full migration of existing call sites.

## Decision
New API code uses a fetch-based client (`src/lib/api/client.ts`) with typed request helpers and explicit error handling via a custom `ApiError` class. The legacy axios client remains for existing features but is not extended with new endpoints. Zod schemas in `src/lib/api/schemas/` validate responses for both clients.

Convention documented in `CLAUDE.md`:
- `src/lib/api.ts` -- axios instance with interceptors (legacy, do not extend)
- `src/lib/api/client.ts` -- fetch-based client (use for all new work)

## Consequences
- New feature modules avoid the axios bundle cost and have simpler, more predictable error handling.
- Two client patterns coexist, which increases cognitive overhead for developers unfamiliar with the convention.
- The legacy client cannot be removed until all existing call sites are migrated, creating ongoing tech debt.
- Both clients share the same auth token storage (`localStorage`) and API base URL, so auth behavior is consistent.
