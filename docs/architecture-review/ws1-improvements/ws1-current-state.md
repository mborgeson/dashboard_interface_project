# WS1 Current State Assessment

**Date:** 2026-03-25
**Branch:** `main` at `5bfc8d4`
**Scope:** Prior findings verification, middleware, auth, Redis/caching, logging, observability

---

## 1. Prior Findings Verification (F-001 through F-069+)

### F-001: Users Endpoints Use In-Memory Demo Data
**Status: FIXED**

The users endpoint (`backend/app/api/v1/endpoints/users.py`) has been completely rewritten. All endpoints now use database operations via `user_crud` (imported from `app.crud.crud_user`). There is no `DEMO_USERS` list or in-memory data structure.

Evidence:
- Line 22: `from app.crud.crud_user import user as user_crud`
- Line 70: `result = await user_crud.get_paginated(db, ...)`
- Line 118: `user = await user_crud.get(db, user_id)`
- Line 154: `existing = await user_crud.get_by_email(db, email=user_data.email)`
- Line 161: `new_user = await user_crud.create(db, obj_in=user_data)`

Note: Demo user *authentication* still exists in `backend/app/api/v1/endpoints/auth.py` (line 126: `demo_users = _get_demo_users()`), but this is the login fallback for dev environments -- not the user management CRUD. The config validator at `config.py:384` blocks demo passwords in production.

---

### F-002: Health Probes Guarded by `require_admin`
**Status: FIXED**

Three separate unauthenticated health check paths exist:

1. **Legacy endpoint** (`backend/app/api/v1/router.py:35`): `GET /api/v1/health` -- no auth, returns `{"status": "healthy"}`.
2. **Deep health check** (`backend/app/api/v1/endpoints/health.py`): `router = APIRouter()` (line 23, no auth dependency). Endpoints at `/health/status` and `/health/status/ready` check DB, Redis, SharePoint, disk space -- all unauthenticated.
3. **Monitoring probes** (`backend/app/api/v1/endpoints/monitoring.py`): `router = APIRouter()` (line 27, no router-level auth). Liveness (`/monitoring/health/live`, line 65) and readiness (`/monitoring/health/ready`, line 84) probes are unauthenticated. Admin-only endpoints (`/metrics`, `/health/detailed`, `/pool-stats`, `/stats`, `/info`) add `require_admin` per-route.

The monitoring router comment at line 25-26 explicitly documents this design decision.

---

### F-003: Report Generation Has No Background Worker
**Status: FIXED**

A background worker exists at `backend/app/services/report_worker.py`:
- `ReportWorker` class polls `queued_reports` table every 30 seconds
- Started in lifespan at `backend/app/main.py:260-261`: `report_worker = get_report_worker(); await report_worker.start()`
- Stopped gracefully on shutdown at line 282: `await report_worker.stop()`
- Generates PDF/Excel output to `generated_reports/` directory

---

### F-004: WebSocket Token Doesn't Check Blacklist
**Status: FIXED**

The `_authenticate_token()` function in `backend/app/api/v1/endpoints/ws.py` (lines 27-61) now:
- Imports `token_blacklist` (line 21)
- Extracts `jti` from payload (line 46)
- Calls `await token_blacklist.is_blacklisted(jti)` (line 49)
- Rejects blacklisted tokens by returning `None` (line 50-52)
- Fails closed on blacklist check errors (line 54-57)

---

### F-005: Frontend Doesn't Use Refresh Token
**Status: FIXED**

The fetch-based API client (`src/lib/api/client.ts`) implements full token refresh:
- `attemptTokenRefresh()` function (lines 39-71) calls `POST /auth/refresh`
- Deduplicates concurrent refresh calls via `refreshPromise` guard (line 32)
- On 401 response, attempts refresh before forcing logout (lines 163-203)
- Updates localStorage with new tokens on success (lines 57-59)

The auth store (`src/stores/authStore.ts`) also has a `refreshAccessToken` method (lines 75-97) and listens for `auth:unauthorized` events (lines 128-139) to clear state.

---

### F-006: Financial Calculation Libraries Have No Tests
**Status: FIXED**

Tests now exist for frontend financial calculations:
- `src/lib/calculations/__tests__/irr.test.ts`
- `src/lib/calculations/__tests__/cashflow.test.ts`
- `src/lib/calculations/__tests__/sensitivity.test.ts`

Backend financial tests also exist:
- `backend/tests/test_models/test_financial_constraints.py`
- `backend/tests/test_api/test_property_financial_enrichment.py`
- `backend/tests/test_services/test_financial_boundaries.py`

And the original underwriting calculation tests:
- `src/features/underwriting/utils/__tests__/calculations.test.ts`

---

### F-007: Transaction DELETE/Restore Only Require `require_viewer`
**Status: FIXED**

In `backend/app/api/v1/endpoints/transactions.py`:
- Router-level default: `require_viewer` (line 25) -- for read endpoints
- DELETE (line 366): `dependencies=[Depends(require_manager)]`
- POST (create, line 264): `dependencies=[Depends(require_manager)]`
- PUT (update, line 292): `dependencies=[Depends(require_manager)]`
- PATCH (partial update, line 329): `dependencies=[Depends(require_manager)]`
- POST restore (line 403): `dependencies=[Depends(require_manager)]`

---

### Other Prior Findings -- Status Summary

| Finding | Description | Status |
|---------|-------------|--------|
| F-007a | structlog startup crash | FIXED -- `logging.getLevelName()` used instead |
| F-008 | Document route shadowing | Needs verification (not in WS1 scope) |
| F-009 | Document upload auth | FIXED -- `require_analyst` on upload (documents.py:249) |
| F-012 | 304 without cache hit | FIXED -- retry logic in client.ts:136-160 |
| F-014 | Analytics export mock data | FIXED -- uses DB queries (exports.py:211-214) |
| F-016 | Redis services commented out | FIXED -- Redis init in lifespan (main.py:190-194) |
| D-10 | No `pool_recycle` | FIXED -- `pool_recycle=3600` on both engines (session.py:40,75) |
| D-09 | `lazy="dynamic"` deprecated | FIXED -- no `lazy="dynamic"` found in models |
| S-02 | Document write auth | FIXED -- `require_analyst` on writes, `require_manager` on delete |
| S-03 | Report template write auth | FIXED -- `require_analyst`/`require_manager` per endpoint |
| S-09 | Same secret for access/refresh | FIXED -- `REFRESH_TOKEN_SECRET` setting, separate `_refresh_secret()` function |
| V-01 | Sort `sort_by` without allowlist | FIXED -- `_SORTABLE_COLUMNS` dict in transactions.py |

---

## 2. Middleware Chain

The middleware chain is configured in `backend/app/main.py`. Due to Starlette's LIFO registration, the effective execution order (outermost to innermost on request) is:

| Order | Middleware | File | Purpose |
|-------|-----------|------|---------|
| 1 | `RequestIDMiddleware` | `middleware/request_id.py` | Generates/propagates `X-Request-ID` via `ContextVar` |
| 2 | `OriginValidationMiddleware` | `middleware/origin_validation.py` | CSRF: validates `Origin` on POST/PUT/PATCH/DELETE |
| 3 | `ErrorHandlerMiddleware` | `middleware/error_handler.py` | Catches unhandled exceptions, returns structured JSON |
| 4 | `SecurityHeadersMiddleware` | `main.py` (inline class) | X-Content-Type-Options, X-Frame-Options, CSP, HSTS |
| 5 | `ETagMiddleware` | `middleware/etag.py` | Computes ETags, returns 304 on cache hit |
| 6 | `RateLimitMiddleware` | `middleware/rate_limiter.py` | Per-client rate limiting (configurable) |
| 7 | `MetricsMiddleware` | `services/monitoring/middleware.py` | Request duration, status codes, endpoint metrics |
| 8 | `CORSMiddleware` | Starlette built-in | CORS headers, preflight handling |

**Key design decisions:**
- RequestID is outermost so every response (including middleware short-circuits) carries a trace ID
- CORS is innermost to correctly handle OPTIONS preflight before other middleware
- ETag before RateLimit so conditional 304s reduce load before rate accounting

---

## 3. Auth System State

### JWT Token Flow
- **Login:** `POST /api/v1/auth/login` (OAuth2 password flow, form-urlencoded)
- **Access token:** 30-minute expiry (`ACCESS_TOKEN_EXPIRE_MINUTES=30`)
- **Refresh token:** 7-day expiry (`REFRESH_TOKEN_EXPIRE_DAYS=7`)
- **Separate signing keys:** `REFRESH_TOKEN_SECRET` for refresh tokens (falls back to `SECRET_KEY` if empty)
- **Frontend storage:** `localStorage` for both tokens

### Token Blacklist (`backend/app/core/token_blacklist.py`)
- Redis-backed with TTL-based auto-expiry (preferred)
- In-memory fallback with lazy eviction at 1000-entry high-water mark
- Used for logout/revocation of access tokens
- WebSocket connections now check blacklist (F-004 fixed)

### Refresh Token Implementation
- Backend: full refresh token rotation with replay detection (`POST /auth/refresh`)
- Frontend: `attemptTokenRefresh()` in `src/lib/api/client.ts` with dedup guard
- Auth store: `refreshAccessToken()` method + `auth:unauthorized` event listener
- On 401: client attempts refresh, retries original request, clears auth only on double failure

### Permission Guards (`backend/app/core/permissions.py`)
| Guard | Role Required |
|-------|---------------|
| `require_viewer` | Viewer or above |
| `require_analyst` | Analyst or above |
| `require_manager` | Manager or above |
| `require_admin` | Admin only |

### Demo User Authentication
- `auth.py:29`: `_get_demo_users()` builds demo user dict from config
- Config validator (`config.py:384`): blocks demo passwords in production environment
- Demo passwords must be provided via env vars -- no hardcoded defaults (empty string defaults)

---

## 4. Redis / Caching State

### Configuration
- `REDIS_URL` default: `redis://localhost:6379/0` (in `config.py:207`)
- `.env` file: `REDIS_URL=redis://localhost:6379/0` (line 62)
- `REDIS_PASSWORD=redis_secure_password_2026` (in `.env` line 14, but not used in URL)
- `REDIS_CACHE_TTL=3600`, `REDIS_MAX_CONNECTIONS=50`

### CacheService (`backend/app/core/cache.py`)
- Lazy Redis connection via `_ensure_redis()`
- Key prefix: `dashboard:`
- TTLs: DEFAULT=1h, SHORT=5min, LONG=2h
- In-memory fallback: `dict[str, tuple[str, float]]`
- Background cleanup task (every 5 minutes) purges expired in-memory entries
- Started in lifespan (main.py:264-267)

### RedisService (`backend/app/services/redis_service.py`)
- Connection pooling, pub/sub, bulk operations
- Typed key builders: `property_key()`, `deal_key()`, etc.
- Initialized in lifespan (main.py:190-194), with fallback on failure

### Current State Issue
Redis is **configured in `.env`** but may not be **running locally**. The code gracefully degrades to in-memory, but this means:
- Token blacklist uses in-memory (lost on restart)
- Cache entries are per-process (not shared across workers)
- No pub/sub for real-time cross-worker events
- Rate limiter state is per-process

The `REDIS_PASSWORD` in `.env` does not match the `REDIS_URL` (URL has no password). If Redis were running with authentication enabled, the connection would fail.

---

## 5. Logging State

### Dual Logging Systems

**Loguru** (primary -- 67 files):
- Used throughout most backend modules
- Console + file handlers configured in `backend/app/core/logging.py:113-160`
- File rotation: daily, with retention and gzip compression
- Format includes request_id via `_request_id_patcher()`

**structlog** (extraction + specialized -- 35 files):
- Used in extraction layer: `extractor.py`, `file_filter.py`, `fingerprint.py`, `reference_mapper.py`, `grouping.py`, `validation.py`, `cell_mapping.py`, `sharepoint.py`, etc.
- Also in: `etag.py`, `query_logger.py`, construction API services, data extraction services
- Component binding: `.bind(component="ExcelDataExtractor")`
- JSON output in production, console in development

### Unification State
Both systems are configured in `backend/app/core/logging.py`:
- `setup_logging()` configures loguru first, then calls `setup_structlog()`
- stdlib `logging` is intercepted and routed through loguru via `_InterceptHandler`
- Both inject request_id: loguru via patcher, structlog via `_add_request_id` processor

### Request ID / Correlation
- `RequestIDMiddleware` sets a `ContextVar` per request (`middleware/request_id.py`)
- Loguru patcher injects `request_id` into every log record
- structlog processor injects `request_id` into every event
- **Usage in code:** Only 6 files explicitly import or reference `request_id` or `get_request_id`:
  - `middleware/request_id.py` (defines it)
  - `middleware/error_handler.py` (uses in error response)
  - `core/logging.py` (both patchers)
  - `services/monitoring/middleware.py` (metrics)
  - `main.py` (global exception handler)
  - `middleware/__init__.py`
- Most log calls use plain `logger.info("message")` or `self.logger.info("event")` -- the request_id is injected automatically, but developers do not see it unless they look at formatted output

---

## 6. Observability

### Health Checks

| Endpoint | Auth | Checks |
|----------|------|--------|
| `GET /api/v1/health` | None | Simple "healthy" response |
| `GET /api/v1/health/status` | None | DB, Redis, SharePoint, external APIs, disk space |
| `GET /api/v1/health/status/ready` | None | DB + Redis (returns 503 if DB is down) |
| `GET /api/v1/monitoring/health/live` | None | Simple "alive" response |
| `GET /api/v1/monitoring/health/ready` | None | DB connectivity |
| `GET /api/v1/monitoring/health/detailed` | Admin | Full system + component status |
| `GET /api/v1/monitoring/metrics` | Admin | Prometheus format |
| `GET /api/v1/monitoring/pool-stats` | Admin | DB + Redis pool statistics |
| `GET /api/v1/monitoring/stats` | Admin | Performance statistics |
| `GET /api/v1/monitoring/info` | Admin | App info and config |

### Metrics Collection
- `MetricsMiddleware` records request duration, status codes, endpoint performance
- `get_metrics_manager()` collects system metrics
- Prometheus-format export at `/monitoring/metrics` (admin-only)
- Collector registry for custom metric sources

### What's Missing
- No APM integration (Datadog, New Relic, etc.)
- No distributed tracing (OpenTelemetry) -- request_id is correlation only, not span/trace
- No alerting rules or threshold monitoring
- No structured log aggregation pipeline (ELK, Loki, etc.) -- just file rotation
- Prometheus endpoint exists but no Prometheus/Grafana stack is deployed
- No synthetic monitoring or uptime checks

---

## 7. CI/CD State

### GitHub Actions Workflows
| File | Status |
|------|--------|
| `backend-ci.yml` | Active |
| `frontend-ci.yml` | Active |
| `e2e.yml` | Active |
| `deploy.yml.disabled` | Disabled (workflow_run trigger caused Action spam) |

### Pre-Commit
- ruff linting and formatting enforced

---

## 8. Key Metrics

| Metric | Value |
|--------|-------|
| Backend test files | 135 |
| Backend test functions | 3,130 |
| Frontend test files | 72 |
| Total tests | ~4,400+ |
| Middleware layers | 8 |
| API routers | 20 |
| Files using loguru | 67 |
| Files using structlog | 35 |
| Alembic migrations | 20+ |
| SQLAlchemy models | 30+ |
