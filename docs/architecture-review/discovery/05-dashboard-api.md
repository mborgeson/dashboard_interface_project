# Discovery 05 -- Dashboard & API Layer

## Overview

This document covers the FastAPI backend application, router architecture, middleware chain, authentication system, frontend architecture, caching layer, and startup services. It serves as the canonical reference for how the dashboard's API surface is structured and secured.

---

## 1. FastAPI Application (`backend/app/main.py`)

- **Size**: ~428 lines
- **Lifespan**: Uses an async context manager (`lifespan`) for startup/shutdown orchestration
- **OpenAPI docs**: Conditionally exposed only in development mode
  - Swagger UI: `/api/docs`
  - ReDoc: `/api/redoc`
- **API prefix**: All versioned routes live under `/api/v1`

### Global Exception Handling

A catch-all `@app.exception_handler(Exception)` is registered at the application level:

- Returns structured JSON with `request_id` (propagated from `RequestIDMiddleware`)
- Logs the full exception traceback via loguru
- Ensures no unhandled 500s leak raw stack traces to clients

---

## 2. Router Architecture (`backend/app/api/v1/router.py`)

The main API router is configured with `redirect_slashes=False` to prevent automatic 307 redirects when a trailing slash is missing. This is intentional -- it avoids confusion with browser/client redirect behavior in single-page app contexts.

### Legacy Health Check

A standalone `GET /api/v1/health` endpoint exists directly on the main router (outside the health sub-router). This was retained to ensure unauthenticated health probes remain available (see F-002 in Known Findings).

### Registered Routers (20 total)

| Router | Prefix | Tags | Notes |
|--------|--------|------|-------|
| `health` | `/health/status` | `health` | Dedicated health/readiness probes |
| `auth` | `/auth` | `authentication` | Login, refresh, logout |
| `properties` | `/properties` | `properties` | Property CRUD |
| `deals` | `/deals` | `deals` | Deal pipeline, kanban, stages |
| `analytics` | `/analytics` | `analytics` | Dashboard KPIs, charts |
| `users` | `/users` | `users` | User management (see F-001) |
| `exports` | `/exports` | `exports` | Data export endpoints |
| `monitoring` | `/monitoring` | `monitoring` | System metrics, logs |
| `extraction` | `/extraction` | `extraction` | Proforma extraction pipeline |
| `interest_rates` | `/interest-rates` | `interest-rates` | Rate data ingestion/display |
| `transactions` | `/transactions` | `transactions` | Financial transactions |
| `documents` | `/documents` | `documents` | Document management |
| `market_data` | `/market` | `market-data` | CoStar submarket data |
| `reporting` | `/reporting` | `reporting` | Report generation |
| `admin` | `/admin` | `admin` | Admin operations |
| `market_data_admin` | _(has own prefix `/admin/market-data`)_ | `Admin - Market Data` | Market data admin operations |
| `sales_analysis` | `/sales-analysis` | `sales-analysis` | Sales comp analysis |
| `construction_pipeline` | `/construction-pipeline` | `construction-pipeline` | Construction tracking |
| `tasks` | _(no prefix)_ | `tasks` | Background task status |
| `ws` | _(no prefix)_ | `websocket` | WebSocket connections |

**Note**: `market_data_admin` carries its own prefix internally (`/admin/market-data`), so it is included without an additional prefix on the main router. Similarly, `tasks` and `ws` are mounted at the router root.

---

## 3. Middleware Chain

Middleware is applied via `app.add_middleware()`. Due to Starlette's LIFO registration order, the **last registered** middleware executes **first** on the request path. The effective execution order (outermost to innermost) is:

| Order | Middleware | Responsibility |
|-------|-----------|----------------|
| 1 | `RequestIDMiddleware` | Generates or propagates `X-Request-ID` header for request tracing |
| 2 | `OriginValidationMiddleware` | CSRF defense-in-depth: validates `Origin` header on state-changing methods (POST, PUT, PATCH, DELETE) |
| 3 | `ErrorHandlerMiddleware` | Catches unhandled exceptions and returns structured JSON error responses |
| 4 | `SecurityHeadersMiddleware` | Sets `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`, `Permissions-Policy`; adds `Strict-Transport-Security` in production only |
| 5 | `ETagMiddleware` | Computes ETags for GET responses; returns `304 Not Modified` when `If-None-Match` matches |
| 6 | `RateLimitMiddleware` | Per-client rate limiting (enabled/disabled via settings) |
| 7 | `MetricsMiddleware` | Records request duration, status codes, and endpoint performance metrics |
| 8 | `CORSMiddleware` | Handles CORS preflight and response headers; origins, credentials, methods, and headers are configurable |

### Key Design Decisions

- **RequestID outermost**: Ensures every response (including those short-circuited by other middleware) carries a trace ID.
- **ErrorHandler before SecurityHeaders**: Security headers are set even on error responses because `ErrorHandlerMiddleware` catches exceptions before they bypass the downstream middleware.
- **ETag before RateLimit**: Conditional `304` responses reduce load before rate limit accounting occurs.
- **CORS innermost**: Must be innermost to correctly handle preflight `OPTIONS` requests that bypass other middleware.

---

## 4. Authentication System

### Token Flow

1. **Login**: `POST /api/v1/auth/login` accepts `application/x-www-form-urlencoded` (OAuth2 password flow), not JSON
2. **Token issuance**: Returns JWT access token (and refresh token in response body)
3. **Frontend storage**: Token is stored in `localStorage` and attached as `Authorization: Bearer <token>` on subsequent requests
4. **Refresh**: Backend implements refresh token rotation, but the frontend does not currently use it (see F-005)

### Permission Guards

Defined in `backend/app/core/permissions.py`, these are FastAPI dependencies injected into route functions:

| Guard | Role Required |
|-------|---------------|
| `require_viewer` | Viewer or above |
| `require_analyst` | Analyst or above |
| `require_manager` | Manager or above |
| `require_admin` | Admin only |

### Token Blacklist

Implemented in `backend/app/core/token_blacklist.py`:

- **Preferred backend**: Redis (with TTL-based expiry)
- **Fallback**: In-memory dictionary with periodic cleanup
- Used for logout/revocation of access tokens

### Known Auth Issues

| ID | Issue | Status |
|----|-------|--------|
| F-004 | WebSocket token validation does not check the token blacklist | OPEN |
| F-005 | Frontend does not use the refresh token mechanism; tokens expire without silent renewal | OPEN |
| F-007 | Transaction DELETE and Restore endpoints only require `require_viewer` (should be higher) | OPEN |

---

## 5. Frontend Architecture

### Stack

- **Framework**: React + TypeScript
- **Bundler**: Vite (dev server at `localhost:5173`)
- **Routing**: React Router v7 with future flags enabled
- **State**: React Query for server state; Zustand stores for client state (e.g., `authStore`)

### Code Splitting

17 feature modules in `src/features/` are lazy-loaded via `React.lazy()` / dynamic `import()`. This keeps the initial bundle small and loads feature code on demand.

### API Clients

Two API client implementations exist side by side:

| Client | Location | Transport | Status |
|--------|----------|-----------|--------|
| Legacy | `src/lib/api.ts` | axios | Do not extend; used by older features |
| Current | `src/lib/api/client.ts` | fetch | Use for all new work |

Both clients:
- Read the JWT from `localStorage`
- Attach it as `Authorization: Bearer <token>`
- Handle 401 responses (redirect to login)

### Response Validation

Zod schemas in `src/lib/api/schemas/` validate and transform every API response:
- Backend returns `snake_case` keys
- Zod `.transform()` maps them to `camelCase` for frontend consumption
- Pattern: `.nullable().optional()` with `?? undefined` (never `?? 0`, which causes `"0.0%"` instead of `"N/A"`)

### Server State Management

React Query is used throughout with centralized `staleTime` constants (extracted during tech debt remediation to replace 60+ magic numbers):
- Prevents redundant refetches within the staleness window
- Queries are keyed by endpoint + parameters for proper cache isolation

---

## 6. Caching Architecture

### Backend: CacheService (`backend/app/core/cache.py`)

| Property | Value |
|----------|-------|
| Preferred backend | Redis |
| Fallback | In-memory dictionary |
| Connection strategy | Lazy (`_ensure_redis()` on first use) |
| Key prefix | `dashboard:` |
| TTL -- DEFAULT | 1 hour (from settings) |
| TTL -- SHORT | 5 minutes |
| TTL -- LONG | 2 hours |
| Pattern invalidation | Via Redis `SCAN` command |
| Cleanup | Background task purges expired in-memory entries |

### Backend: RedisService (`backend/app/services/redis_service.py`)

A more full-featured Redis wrapper providing:
- Connection pooling
- Pub/sub support
- Bulk operations
- Typed key builders: `property_key()`, `deal_key()`, `user_key()`, `analytics_key()`

### HTTP-Level: ETagMiddleware

- Computes ETag hashes for GET response bodies
- Returns `304 Not Modified` when the client sends a matching `If-None-Match` header
- Reduces bandwidth for unchanged resources

### Redis Initialization

During application lifespan startup:
1. Redis connection is attempted
2. On failure, the application continues with in-memory cache fallback
3. No hard dependency on Redis for application availability

---

## 7. Startup Services (Lifespan)

The `lifespan` async context manager in `main.py` initializes the following services in order. All are shut down gracefully on application exit.

| Order | Service | Purpose |
|-------|---------|---------|
| 1 | Metrics manager | Performance counters and system metrics collection |
| 2 | Database engine monitoring | Connection pool health tracking |
| 3 | Redis service | Cache backend (with in-memory fallback on failure) |
| 4 | WebSocket connection manager | Real-time client connection tracking |
| 5 | Extraction scheduler | APScheduler cron jobs for proforma extraction |
| 6 | File monitor scheduler | Interval-based file system watcher (default: 30 min) |
| 7 | Market data scheduler | Scheduled CoStar data refresh |
| 8 | Interest rate scheduler | Scheduled rate data ingestion |
| 9 | Report generation worker | Background report builder (addresses F-003) |
| 10 | Cache cleanup task | Periodic purge of expired in-memory cache entries |

---

## 8. WebSocket

- **Router**: `ws.py` handles WebSocket upgrade and message routing
- **Manager**: `WebSocketConnectionManager` is initialized during lifespan startup
- **Connection limits**: Max connections per client is configurable via settings
- **Use cases**: Real-time collaboration notifications, extraction progress updates

### Known Issue

- **F-004**: Token validation on WebSocket connections does not check the blacklist. A revoked token can still establish a WebSocket connection until it naturally expires.

---

## 9. Known Critical Findings (Prior Reviews)

| ID | Issue | Severity | Status |
|----|-------|----------|--------|
| F-001 | Users endpoints (`/api/v1/users`) serve in-memory demo data instead of querying the database | HIGH | OPEN |
| F-002 | Health probes at `/health/status` were guarded by `require_admin` | MEDIUM | Addressed -- legacy `GET /api/v1/health` exists without auth guard |
| F-003 | Report generation had no background worker; reports were generated synchronously in request handlers | HIGH | FIXED -- `report_worker` started in lifespan |
| F-004 | WebSocket token validation does not check the token blacklist | MEDIUM | OPEN |
| F-005 | Frontend does not use the refresh token mechanism; sessions expire without silent renewal | MEDIUM | OPEN |
| F-006 | Financial calculation libraries (cap rate, NOI, IRR/MOIC) had no dedicated test coverage | HIGH | Partially addressed |
| F-007 | Transaction DELETE and Restore endpoints only require `require_viewer` permission | HIGH | OPEN |

---

## 10. Summary of Architecture Risks

1. **Dual API clients**: Two parallel HTTP client implementations (`axios` and `fetch`) increase maintenance surface. The legacy client should be migrated incrementally.
2. **Redis optional**: The entire caching and pub/sub layer degrades to in-memory when Redis is unavailable. This is acceptable for single-instance deployments but will not work for horizontal scaling.
3. **Auth gaps**: Three open findings (F-004, F-005, F-007) represent real security surface area that should be addressed before production exposure.
4. **Demo data in users endpoint**: F-001 means the users management UI does not reflect actual database state -- a data integrity concern if administrators rely on it.
5. **Middleware ordering**: The chain is correctly ordered, but any future middleware additions must respect the execution-order semantics (LIFO registration = outermost-first execution).
