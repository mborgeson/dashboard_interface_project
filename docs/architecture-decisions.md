Generated: 2026-03-10

# Architecture Decisions & Patterns

B&R Capital Dashboard Interface Project -- recurring patterns, architectural decision records, coding conventions, and known issues.

---

## Table of Contents

1. [Recurring Patterns](#1-recurring-patterns)
2. [Architecture Decision Records](#2-architecture-decision-records)
3. [Coding Conventions](#3-coding-conventions)
4. [Issues Found](#4-issues-found)

---

## 1. Recurring Patterns

### 1.1 Middleware Chain (Layered Request Processing)

**Location:** `backend/app/main.py`, `backend/app/middleware/`

The backend uses an 8-layer Starlette middleware chain registered in a specific order. Starlette executes middleware in last-registered-first order, so the outermost middleware is registered last.

| Order | Middleware | Concern |
|-------|-----------|---------|
| 1 (outermost) | `RequestIDMiddleware` | Assigns UUID4 `X-Request-ID`, sets `ContextVar` |
| 2 | `OriginValidationMiddleware` | Defense-in-depth CSRF: validates `Origin`/`Referer` on POST/PUT/PATCH/DELETE against `CORS_ORIGINS` list |
| 3 | `ErrorHandlerMiddleware` | Structured JSON error responses with request_id |
| 4 | `SecurityHeadersMiddleware` | CSP, HSTS, X-Frame-Options, cache control |
| 5 | `ETagMiddleware` | Conditional GET responses (SHA-256 ETag, 304) |
| 6 | `RateLimitMiddleware` | Sliding-window rate limiting with X-RateLimit headers |
| 7 | `MetricsMiddleware` | Prometheus request counters and histograms |
| 8 (innermost) | `CORSMiddleware` | Origin allowlisting, exposed headers |

**Key principle:** Each middleware handles exactly one cross-cutting concern. Request ID is outermost so all other middleware can log with correlation. Error handler is near the top so exceptions from inner middleware are caught.

### 1.2 Structured Error Handling Middleware

**Location:** `backend/app/middleware/error_handler.py`

Replaces per-endpoint try/except blocks with a single middleware that maps exception types to HTTP status codes and structured JSON responses. Every error response includes `detail`, `request_id`, and `type` fields.

| Exception Type | HTTP Status | `type` field |
|---------------|-------------|--------------|
| `HTTPException` | Pass-through | (FastAPI handles) |
| `SQLAlchemyError` | 500 | `database_error` |
| `ValidationError` (Pydantic) | 422 | `validation_error` |
| `PermissionError` | 403 | `permission_error` |
| `ValueError` | 400 | `value_error` |
| `Exception` (catch-all) | 500 | `internal_error` |

All exceptions are logged via structlog with request_id, path, and method context. The middleware re-raises `HTTPException` so FastAPI's built-in handler preserves status codes and headers.

### 1.3 ETag Caching (Conditional Responses)

**Backend:** `backend/app/middleware/etag.py`
**Frontend:** `src/lib/api/client.ts`

The ETag system operates across both layers:

- **Backend middleware** computes SHA-256 of response body for every GET response, attaches it as a quoted ETag header, and returns 304 Not Modified when the client sends a matching `If-None-Match` header.
- **Frontend client** maintains an in-memory `Map<url, {etag, data}>` cache. On GET requests it sends `If-None-Match` with the cached ETag. On 304, it returns the cached data without re-parsing.

This eliminates redundant payload transfer for unchanged data while keeping the cache-invalidation model simple (server-side body hash).

### 1.4 Cursor-Based Pagination

**Location:** `backend/app/schemas/pagination.py`, `backend/app/crud/base.py`

Implements keyset pagination as an alternative to traditional offset-based pagination. The cursor is a base64-encoded JSON array of `[sort_value, row_id]` providing deterministic, O(1) page seeks.

**Components:**
- `CursorPaginationParams` -- Pydantic schema with `cursor`, `limit` (1-100), and `direction` (next/prev)
- `CursorPaginatedResponse[T]` -- Generic response wrapper with `items`, `next_cursor`, `prev_cursor`, `has_more`, `total`
- `CRUDBase.get_cursor_paginated()` -- Generic implementation with keyset WHERE clause, sort-value coercion for datetime/decimal types, and bidirectional traversal
- `encode_cursor()` / `decode_cursor()` -- Base64 encode/decode helpers

**Design decisions:**
- Fetches `limit + 1` rows to detect `has_more` without a separate COUNT query
- For "prev" direction, inverts sort order then reverses the result list
- `include_total` parameter allows skipping the COUNT query for large tables
- `_coerce_sort_value()` restores Python types (datetime, Decimal, int) from JSON-serialized cursor values

The traditional `PaginatedResult` (offset-based) is also available via `CRUDBase.get_paginated()` for endpoints where total page count matters.

### 1.5 CacheService (Redis with In-Memory Fallback)

**Location:** `backend/app/core/cache.py`

Global singleton `CacheService` (`cache`) providing async get/set/delete/invalidate with TTL-based expiration. Follows the same lazy-init pattern as `TokenBlacklist`.

**Architecture:**
- Lazy Redis connection via `_ensure_redis()` -- only connects on first cache operation
- Falls back to in-memory dict (`_memory_cache: dict[key, (json_str, expires_at)]`) when Redis is unavailable
- All keys prefixed with `dashboard:` for namespace isolation
- Three TTL tiers: `SHORT_TTL` (5 min), `DEFAULT_TTL` (1 hour), `LONG_TTL` (2 hours)
- `invalidate_pattern()` uses Redis SCAN with glob patterns; memory fallback uses `fnmatch`
- Domain-specific convenience methods: `invalidate_properties()`, `invalidate_deals()`

**Key helpers:**
- `make_cache_key(*parts)` -- Joins parts with colons for readable keys
- `make_cache_key_from_params(prefix, **params)` -- MD5 hash of sorted params for deterministic short keys

### 1.6 WebSocket ConnectionManager

**Location:** `backend/app/services/websocket_manager.py`

Channel-based WebSocket connection pool with per-client limits and heartbeat management.

**Architecture:**
- Named channels via `Channel` StrEnum: DEALS, EXTRACTION, NOTIFICATIONS, PROPERTIES, ANALYTICS
- Per-user connection limit (default 5) and global limit (`WS_MAX_CONNECTIONS`, default 1000)
- Heartbeat loop sends ping at `WS_HEARTBEAT_INTERVAL` (30s), auto-disconnects on failure
- Connection metadata tracks user_id, channels, connected_at, last_heartbeat
- Singleton via `get_connection_manager()`

**Messaging patterns:**
- `send_to_connection()` -- single connection by ID
- `send_to_user()` -- all connections for a user_id
- `send_to_channel()` -- broadcast to channel with optional exclude
- `broadcast()` -- all connections
- Domain helpers: `notify_deal_update()`, `notify_extraction_progress()`, `notify_property_update()`, `notify_user()`

### 1.7 Slow Query Logging

**Location:** `backend/app/db/query_logger.py`

SQLAlchemy event listeners (`before_cursor_execute` / `after_cursor_execute`) that detect queries exceeding `SLOW_QUERY_THRESHOLD_MS` (default 500ms).

**Features:**
- Works on both sync and async engines (attaches to `sync_engine` underneath `AsyncEngine`)
- Logs via structlog with duration_ms, statement_type, truncated SQL, and caller context (walks stack to find application frame)
- Records to Prometheus `database_slow_query_duration_seconds` histogram and `database_slow_queries_total` counter
- Parameter sanitization masks sensitive keys (password, secret, token, key, authorization, credential)
- Configurable: `SLOW_QUERY_THRESHOLD_MS`, `SLOW_QUERY_LOG_PARAMS`
- Also feeds the generic `DB_QUERY_LATENCY` histogram for all queries (fast and slow)

### 1.8 Input Sanitization Validators

**Location:** `backend/app/core/sanitization.py`

HTML/XSS prevention utilities using only Python stdlib (`re`, `html`). No external sanitization dependencies.

**Functions:**
- `strip_html_tags(value)` -- Multi-pass: strip tags, remove dangerous URI schemes (javascript:, vbscript:, data:), remove event handlers (onerror=, onclick=), unescape HTML entities, re-strip
- `sanitize_string(value)` -- Null-safe wrapper around `strip_html_tags`
- `sanitize_string_list(values)` -- Sanitizes each element in a list
- `make_sanitized_validator(*field_names)` -- Factory that returns a Pydantic `model_validator(mode="before")` for declarative sanitization in schemas

**Usage pattern in Pydantic schemas:**
```python
class DealUpdate(BaseModel):
    name: str
    notes: str | None = None

    _sanitize = model_validator(mode="before")(
        make_sanitized_validator("name", "notes")
    )
```

### 1.9 Soft-Delete Mixin

**Location:** `backend/app/models/base.py`, `backend/app/crud/base.py`

`SoftDeleteMixin` adds `is_deleted` (bool, indexed) and `deleted_at` (nullable timestamp) columns. Provides `soft_delete()` and `restore()` instance methods.

**Applied to:** `Deal`, `Transaction`, `Property`, `User`

**CRUDBase integration:**
- `_has_soft_delete(model)` -- Introspects model for mixin columns
- `_apply_soft_delete_filter()` -- Automatically adds `WHERE is_deleted = false` unless `include_deleted=True`
- `remove()` -- Calls `soft_delete()` on mixin models; hard-deletes otherwise
- `restore()` -- Reverses soft-delete; raises `ValueError` on non-mixin models

See [ADR-007](docs/adr/007-soft-delete-pattern.md) for rationale.

### 1.10 Optimistic Locking (Version Column)

**Location:** `backend/app/models/deal.py`

Integer `version` column on `Deal` model, incremented atomically on each update. Clients must send the current version with update requests; mismatch returns HTTP 409 Conflict.

**Flow:**
1. Client fetches deal, receives `version: N`
2. Client sends `PUT /deals/{id}` with `version: N`
3. Backend checks `deal.version == N`; if true, sets `version = N + 1`; if false, returns 409
4. Client handles conflict by re-fetching and showing a notification

Currently applied only to `Deal` -- other models do not have concurrent-edit concerns. See [ADR-005](docs/adr/005-optimistic-locking-version-column.md).

### 1.11 Rate Limiting (Sliding Window)

**Location:** `backend/app/middleware/rate_limiter.py`

Configurable per-path rate limiting with two backend implementations.

**Architecture:**
- `RateLimitBackend` ABC with `is_rate_limited()` and `cleanup()` methods
- `MemoryRateLimitBackend` -- Sliding window log algorithm (timestamp list per key, asyncio lock)
- `RedisRateLimitBackend` -- Fixed-bucket counter via Redis INCR + EXPIRE pipeline; fails open if Redis unavailable
- `RateLimiter` -- Rule engine with longest-prefix matching; rules sorted by path length descending

**Default rules:**
| Path prefix | Limit | Window | Purpose |
|-------------|-------|--------|---------|
| `/api/v1/auth/login` | 5 req | 60s | Brute-force prevention |
| `/api/v1/auth/register` | 5 req | 60s | Abuse prevention |
| `/api/v1/auth/refresh` | 10 req | 60s | Token refresh |
| `/api/` | 100 req | 60s | General API |

Response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`. Excluded paths: `/health`, `/metrics`, `/api/docs`, `/api/redoc`.

### 1.12 Request ID Correlation

**Location:** `backend/app/middleware/request_id.py`

`RequestIDMiddleware` (outermost) assigns or propagates a UUID4 correlation ID via the `X-Request-ID` header and a `ContextVar`. Both loguru and structlog inject this ID into all log entries, enabling end-to-end request tracing across middleware, endpoints, CRUD operations, and background tasks.

### 1.13 Lazy-Init Singleton Pattern

Several services follow the same "lazy-init singleton with fallback" pattern:

| Service | Singleton | Fallback |
|---------|-----------|----------|
| `CacheService` | `cache` in `core/cache.py` | In-memory dict |
| `TokenBlacklist` | `token_blacklist` in `core/token_blacklist.py` | In-memory dict |
| `RateLimiter` | `_instance` class var | In-memory backend |
| `ConnectionManager` | `_manager` in `websocket_manager.py` | N/A (no fallback) |

Pattern: lazy `_ensure_redis()` on first operation, Redis preferred, memory fallback on connection failure. This avoids startup failures when Redis is not configured (development) while using Redis in production.

### 1.14 Zod Schema Contract Layer

**Location:** `src/lib/api/schemas/`

Zod schemas validate and transform every API response from snake_case (backend) to camelCase (frontend). This catches contract drift at runtime rather than at build time.

**Conventions:**
- `.nullable().optional()` with `?? undefined` (never `?? 0`, which would show "0.0%" instead of "N/A")
- Schemas colocated with feature-specific API hooks
- Both the fetch-based client and convenience wrappers (`get`, `post`, `put`, `patch`, `del`) share the same Zod validation layer

### 1.15 Fetch-Based Unified API Client

**Location:** `src/lib/api/client.ts`, `src/lib/api/index.ts`

A single fetch-based API client with built-in ETag caching, automatic auth token injection from localStorage, and 401 event dispatching. The legacy axios client has been fully removed.

**Features:**
- `apiClient` object with typed `get<T>`, `post<T>`, `put<T>`, `patch<T>`, `delete<T>` methods
- Convenience wrappers re-exported from `@/lib/api`: `get()`, `post()`, `put()`, `patch()`, `del()`
- URLSearchParams body detection (auto-skips Content-Type header for form-encoded bodies)
- On 401: clears localStorage tokens, dispatches `auth:unauthorized` custom event

### 1.16 Enrichment-on-Read

**Location:** `backend/app/crud/crud_property.py`

Properties and deals are enriched with data from the `extracted_values` table at read time, not at write time. On first read, the CRUD layer checks if `financial_data` is populated; if empty, it queries `extracted_values`, maps field names (e.g., `GOING_IN_CAP_RATE` to `capRate`), and commits the enriched data. Subsequent reads are served from cache.

### 1.17 Auth Guard Pattern

**Location:** `backend/app/core/permissions.py`

FastAPI dependency injection with hierarchical role checking. Role hierarchy: VIEWER (0) < ANALYST (1) < MANAGER (2) < ADMIN (3). Convenience dependencies: `require_viewer`, `require_analyst`, `require_manager`, `require_admin`. GET endpoints use `require_analyst`; POST/PUT/PATCH/DELETE use `require_manager`.

### 1.18 Background Task Pattern

**Location:** `backend/app/api/v1/endpoints/extraction/`, `backend/app/api/v1/endpoints/market_data_admin.py`

Long-running operations (extraction, data pipeline) use FastAPI `BackgroundTasks`. The endpoint creates a run record, schedules the work via `background_tasks.add_task()`, and returns immediately with a run ID. Background tasks create their own database sessions since the request session closes after the response.

### 1.19 Generic CRUD Base with Typed Subclasses

**Location:** `backend/app/crud/base.py`, `backend/app/crud/crud_*.py`

`CRUDBase[ModelType, CreateSchemaType, UpdateSchemaType]` provides get, get_multi, create, update, remove, restore, count, get_paginated, and get_cursor_paginated. Subclasses add domain-specific methods (e.g., `CRUDDeal.get_kanban_data`, `CRUDProperty.enrich_financial_data`). Each has a module-level singleton instance (e.g., `deal = CRUDDeal(Deal)`).

---

## 2. Architecture Decision Records

### Existing ADRs (docs/adr/)

Seven formal ADRs exist in `docs/adr/`. The table below summarizes each with its current status.

| ADR | Title | Status | Key Decision |
|-----|-------|--------|-------------|
| [001](docs/adr/001-fastapi-sqlalchemy-async-backend.md) | FastAPI + SQLAlchemy Async Backend | Accepted | Async endpoints + sync CRUD, dual session factories, Alembic migrations, Pydantic schemas |
| [002](docs/adr/002-react-typescript-vite-frontend.md) | React + TypeScript + Vite Frontend | Accepted | Vite manual chunk splitting (11 vendor bundles), Zod contract layer, no SSR (internal tool) |
| [003](docs/adr/003-jwt-auth-with-refresh-token-rotation.md) | JWT Auth with Refresh Token Rotation | Accepted | HS256, 30-min access / 7-day refresh, jti-based blacklist, replay detection revokes all user tokens |
| [004](docs/adr/004-dual-api-client-pattern.md) | Dual API Client Pattern | **Superseded** | Originally: axios (legacy) + fetch (new). Axios has been fully removed; all imports now resolve to the fetch-based client via `src/lib/api/index.ts`. ADR should be updated to reflect this. |
| [005](docs/adr/005-optimistic-locking-version-column.md) | Optimistic Locking (Version Column) | Accepted | Integer version on Deal; 409 Conflict on mismatch; no pessimistic locking |
| [006](docs/adr/006-structlog-loguru-coexistence.md) | structlog + Loguru Coexistence | Accepted | Loguru for human-readable dev output; structlog for JSON production events; shared request_id ContextVar |
| [007](docs/adr/007-soft-delete-pattern.md) | Soft-Delete Pattern | Accepted | SoftDeleteMixin on Deal, Transaction, Property, User; CRUDBase auto-filters; restore() available |

### Proposed ADRs (not yet formalized)

The following decisions have been implemented but lack formal ADR documentation.

#### ADR-008 (proposed): Unified Fetch API Client

**Status:** Should be created (supersedes ADR-004)

**Context:** ADR-004 documented the dual axios/fetch client pattern. The axios client (`src/lib/api.ts`) and the `axios` npm dependency have both been removed. All API call sites now use the fetch-based `apiClient` from `src/lib/api/client.ts`, with convenience wrappers (`get`, `post`, `put`, `patch`, `del`) re-exported from `src/lib/api/index.ts`.

**Decision:** Consolidate on a single fetch-based client with built-in ETag caching and auth event dispatching. Mark ADR-004 as superseded.

**Consequences:**
- Removes the axios bundle from production build
- Single import path for all API calls: `@/lib/api`
- ETag caching integrated at the client level (no separate cache layer needed)
- No more cognitive overhead from two client patterns

#### ADR-009 (proposed): Cursor-Based Pagination

**Context:** Traditional offset-based pagination degrades on large tables (O(n) offset scans) and produces unstable results when rows are inserted or deleted between page fetches.

**Decision:** Implemented keyset (cursor-based) pagination in `CRUDBase.get_cursor_paginated()` using base64-encoded `[sort_value, row_id]` cursors. Available alongside existing offset-based pagination for backward compatibility.

**Consequences:**
- O(1) page seeks via indexed WHERE clause instead of OFFSET
- Stable results across concurrent inserts/deletes
- Cursors are opaque to clients, preventing direct page jumping (by design)
- Both pagination styles coexist; endpoints choose which to use

#### ADR-010 (proposed): Redis Caching Strategy

**Context:** Multiple services need caching with different TTL requirements: portfolio summaries (rarely change), property lists (moderate change frequency), and analytics dashboards (computed aggregates).

**Decision:** `CacheService` singleton with lazy Redis connection, in-memory fallback, three TTL tiers (5 min / 1 hour / 2 hours), `dashboard:` key prefix, and pattern-based invalidation via SCAN.

**Consequences:**
- No startup failure when Redis is unavailable (development)
- Automatic fallback prevents cache outages from becoming application outages
- Pattern invalidation (`invalidate_properties()`, `invalidate_deals()`) ensures cache coherence on writes
- In-memory fallback has no expiry cleanup scheduler (relies on `cleanup_memory()` being called)

#### ADR-011 (proposed): Structured Error Handling Middleware

**Context:** Individual endpoint handlers had repetitive try/except blocks mapping exceptions to HTTP responses. Error response formats were inconsistent (some included `request_id`, others did not).

**Decision:** A single `ErrorHandlerMiddleware` catches all non-HTTP exceptions, maps them to appropriate status codes, and returns a consistent `{detail, request_id, type}` JSON envelope.

**Consequences:**
- Endpoints can raise raw Python exceptions (ValueError, PermissionError) without wrapping them
- All error responses include request_id for correlation
- HTTPExceptions pass through unchanged (preserving FastAPI's built-in behavior)
- Cannot customize error responses per-endpoint without raising HTTPException explicitly

---

## 3. Coding Conventions

### 3.1 Python (Backend)

**Type hints:** Required on all function signatures and return types. The project uses mypy with strict-equivalent checks enabled.

**String formatting:** f-strings exclusively. No `.format()` or `%` formatting.

**Datetimes:** `datetime.now(UTC)` always. Never naive datetimes. SQLite tests require explicit `created_at`/`updated_at` values (no `server_default`).

**Imports:** stdlib, third-party, local (separated by blank lines). `known-first-party = ["app"]` in ruff isort config.

**Exceptions:** Always explicit exception types. Never bare `except:`. The `ErrorHandlerMiddleware` catches typed exceptions, so endpoints should raise `ValueError`, `PermissionError`, or `HTTPException` as appropriate.

**Logging:** Two logger imports are valid per ADR-006:
- `from loguru import logger` -- General application logging, debug traces, startup messages
- `structlog.get_logger()` -- Structured events for security, CRUD mutations, extraction pipeline

**Enums:** `StrEnum` for string enums. SQLAlchemy enum columns need `values_callable` for lowercase storage.

**Linting (Ruff):** Line length 88, rules E/F/W/I/UP/B/C4/SIM. B008 ignored (FastAPI `Depends`). E501 ignored (handled by formatter).

**Sanitization:** All user-facing string fields in Pydantic schemas should use `make_sanitized_validator()` for XSS prevention. This is a `model_validator(mode="before")` that strips HTML tags and dangerous patterns.

**Caching:** Use `CacheService` (`from app.core.cache import cache`) for data that is expensive to compute and changes infrequently. Choose TTL tier based on data volatility: `SHORT_TTL` (5 min) for frequently-changing data, `LONG_TTL` (2 hours) for aggregates.

**Pagination:** New list endpoints should offer cursor-based pagination via `CursorPaginationParams` / `CursorPaginatedResponse`. Offset-based pagination remains available for endpoints where total page count is needed in the UI.

**Error handling:** Prefer raising raw Python exceptions (`ValueError`, `PermissionError`) for domain errors; the `ErrorHandlerMiddleware` maps them to appropriate HTTP responses. Use `HTTPException` only when you need a specific status code not covered by the middleware mapping or need custom headers.

### 3.2 TypeScript/React (Frontend)

**API client:** Use `@/lib/api` for all API calls. The convenience wrappers `get<T>()`, `post<T>()`, etc. are preferred for simple calls; `apiClient` directly for advanced options. Axios is no longer in the project -- do not add it back.

**Zod schemas:** Validate and transform all API responses. Use `.nullable().optional()` with `?? undefined` (never `?? 0`). Schemas live in `src/lib/api/schemas/`.

**State management:**
- Server state: TanStack React Query (with `staleTime` 5 min default, up to 60 min for reference data)
- Client state: Zustand stores in `src/stores/`

**ESLint rules:** No `setState` in `useEffect`. No `ref.current` in render output. These are enforced by `eslint-plugin-react-hooks`.

**Component patterns:**
- `KPICard` trend checks: Use `trend !== undefined && trend !== 0` (not `trend && trend > 0`, which is falsy for 0)
- Error boundaries at the global level; feature modules handle their own loading/error states via React Query

**Bundle awareness:** ExcelJS (937KB) and jsPDF (386KB) must always be dynamically imported. Never add them to static imports.

### 3.3 Testing

**Backend (pytest):**
- SQLite in-memory with `StaticPool` for test isolation
- `created_at`/`updated_at` must be set explicitly (no `server_default` in SQLite)
- `begin_nested()` unreliable with StaticPool
- Auth fixtures: `auth_headers` (analyst role), `admin_auth_headers` (admin role)
- GET endpoints test with `auth_headers`; POST/PUT/DELETE with `admin_auth_headers`; also test no-auth returns 401
- Mock `extract_from_file` with `**kw` to accept `validate` kwarg

**Frontend (vitest):**
- Tests colocated with features or in `src/test/`
- React Router v7 future flags must be set in test wrappers as well as the prod router
- Always test extraction logic, financial calculations, API endpoint changes, and Zod schema changes
- Use judgment for UI glue code -- test the logic, not the framework

### 3.4 Git Conventions

- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`
- Scope in parens: `feat(extraction):`, `fix(tests):`
- Run linter/formatter and test suite before committing
- Never commit `.env`, generated files, or IDE configs

---

## 4. Issues Found

Architectural concerns and pattern violations remaining after the 51 completed tasks.

### 4.1 ADR-004 is Stale

**Severity:** Low (documentation only)
**Details:** ADR-004 documents the "Dual API Client Pattern" with axios (legacy) and fetch (new). Axios has been fully removed from the codebase -- no `src/lib/api.ts` file, no `axios` in `package.json`, no axios imports anywhere in `src/`. The ADR should be marked as Superseded with a pointer to the unified fetch client.

### 4.2 In-Memory Cache Fallback Has No Automatic Cleanup

**Severity:** Low
**Details:** `CacheService._memory_cache` in `backend/app/core/cache.py` stores entries with TTL-based expiration, but expired entries are only evicted on read (`_memory_get`) or explicit `cleanup_memory()` call. There is no background task that periodically calls `cleanup_memory()`. In long-running development sessions without Redis, expired entries accumulate in memory until they happen to be read.
**Recommendation:** Add periodic cleanup to the lifespan manager or use a TTL-aware data structure.

### 4.3 WebSocket ConnectionManager Not Integrated into Lifespan

**Severity:** Low
**Details:** The `ConnectionManager` singleton is defined in `backend/app/services/websocket_manager.py` and created lazily via `get_connection_manager()`. However, `main.py`'s lifespan function has Redis init, WebSocket init, and ML model loading commented out (`# await init_websocket_manager()`). The manager works but has no graceful shutdown that disconnects active connections on application exit.

### 4.4 Dual Logging Imports Require Discipline

**Severity:** Low
**Details:** Per ADR-006, both `loguru.logger` and `structlog.get_logger()` are valid imports. Some modules use both in the same file (e.g., `auth.py`). Without enforcement, new contributors may use the wrong one. The convention -- loguru for general logging, structlog for auditable events -- is documented in ADR-006 but not enforced by linting.
**Recommendation:** Consider a ruff rule or code review checklist item to flag structlog usage outside security/audit paths.

### 4.5 Optimistic Locking Only on Deal Model

**Severity:** Informational
**Details:** ADR-005 notes that only the `Deal` model uses the version column. As the application grows, `Property` edits from multiple users (especially during data cleanup or enrichment) could encounter the same lost-update problem. This is documented as intentional in ADR-005 but should be revisited if property concurrent-edit scenarios emerge.

### 4.6 SoftDeleteMixin Scope May Need Expansion

**Severity:** Informational
**Details:** ADR-007 lists `Deal`, `Transaction`, `Property`, and `User` as soft-delete models. However, activity logs, extracted values, and report templates are hard-deleted. For compliance and audit trail completeness, consider whether `ActivityLog` and `ExtractedValue` should also be soft-delete-aware (at the cost of increased storage).

### 4.7 Rate Limiter Redis Backend Uses Fixed-Bucket Approximation

**Severity:** Low
**Details:** `RedisRateLimitBackend` in `backend/app/middleware/rate_limiter.py` uses a fixed-bucket counter (`key = prefix:ip:timestamp//window`) rather than a true sliding window. This means a burst of requests at the end of one window and the start of the next could temporarily allow up to 2x the configured limit. The memory backend uses a true sliding window log. The approximation is acceptable for the current scale but diverges from the memory backend's behavior.

### 4.8 Frontend ETag Cache Unbounded

**Severity:** Low
**Details:** The `etagCache` Map in `src/lib/api/client.ts` grows without bound as the user navigates to different pages and endpoints. There is no LRU eviction or max-size limit. For a dashboard with moderate navigation patterns this is unlikely to cause issues, but heavy use of parameterized endpoints could accumulate stale entries.
**Recommendation:** Consider a bounded LRU map (e.g., keep last 100 entries) or clear the cache on logout.

### 4.9 Fetch Client Missing Token Refresh Logic

**Severity:** Medium
**Details:** The unified fetch client (`src/lib/api/client.ts`) dispatches `auth:unauthorized` on 401 responses, which logs the user out. There is no transparent token refresh -- if the access token expires mid-session, the user is forced to re-authenticate. The old axios client had interceptor-based token refresh that retried failed requests after obtaining a new token. This logic was not ported to the fetch client during the migration.
**Recommendation:** Implement a retry-after-refresh mechanism in the fetch client's `request()` function, similar to what the axios interceptor provided.

### 4.10 Enrichment Logic in CRUD Layer

**Severity:** Low
**Details:** `backend/app/crud/crud_property.py` contains 260+ lines of field-mapping and JSON-building logic in `enrich_financial_data()`. This mixes data access (CRUD) with business logic (field name mapping, unit conversion, JSON structure). The field mapping constants (`_CASHFLOW_FIELD_MAP`, `_YEAR_FIELD_RE`) are extraction-domain concepts defined at module level in the CRUD file.
**Recommendation:** Extract the field mapping and JSON building into a separate `services/enrichment.py` module. Move field mapping constants to a shared location referenced by both extraction and enrichment code.

---

**Audit completed:** 2026-03-10
**Patterns documented:** 19
**Existing ADRs:** 7 (in docs/adr/)
**Proposed ADRs:** 4 (008-011)
**Conventions documented:** 4 categories
**Issues identified:** 10 (1 medium, 5 low, 2 informational, 2 documentation)
