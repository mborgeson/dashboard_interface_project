# WS1 Gap Analysis

**Date:** 2026-03-25
**Branch:** `main` at `5bfc8d4`
**Scope:** New findings since last review, cross-cutting patterns, infrastructure gaps

---

## 1. Prior Finding Disposition

All 7 critical findings from the v2 review (F-001 through F-007) have been verified as FIXED in code. See `ws1-current-state.md` Section 1 for evidence.

Key items from the remediation plan (73 findings) -- significant fixes verified:
- S-02/S-03: Document and report template auth guards upgraded
- S-09: Separate `REFRESH_TOKEN_SECRET` implemented
- D-10: `pool_recycle=3600` on both DB engines
- D-09: No `lazy="dynamic"` remaining in models
- F-016: Redis init no longer commented out in lifespan
- V-01: Sort column allowlists implemented (at least in transactions)

---

## 2. New Findings Since Last Review

### G-001: Redis URL Missing Password Authentication
**Severity:** HIGH
**Location:** `backend/.env:62`, `backend/app/core/config.py:207`

The `.env` file contains `REDIS_PASSWORD=redis_secure_password_2026` (line 14) and `REDIS_URL=redis://localhost:6379/0` (line 62). The password is **not embedded in the URL**. If Redis is running with `requirepass`, the application will fail to authenticate. The URL should be `redis://:redis_secure_password_2026@localhost:6379/0`.

Additionally, the config default `REDIS_URL: str = "redis://localhost:6379/0"` hardcodes a URL that assumes a locally running, unauthenticated Redis -- acceptable for dev but risky if this default is used in production.

---

### G-002: Redis Not Verified Running in Development
**Severity:** MEDIUM
**Location:** `backend/app/main.py:190-196`

The lifespan startup attempts Redis connection and logs a warning on failure, falling back to in-memory. There is no startup validation or health gate that warns the developer if Redis is supposed to be running but is not. The application silently degrades to in-memory cache, token blacklist, and rate limiting -- all of which lose state on restart.

**Impact:** Developer may believe Redis is active when it is silently falling back to in-memory. Token blacklist entries are lost on each server restart.

---

### G-003: Two API Clients in Frontend
**Severity:** LOW (tech debt)
**Location:** `src/lib/api/client.ts` (fetch), `src/lib/api/index.ts` (re-exports)

The legacy axios-based client (`src/lib/api.ts`) no longer exists as a separate file. It has been consolidated into the fetch-based client. However, 18 files still import from `@/lib/api` (which now re-exports from `./client`). Additionally, 6 files import directly from `@/lib/api/client`.

This is partially resolved -- there is now functionally one client, but the import paths are inconsistent. No action needed beyond eventual cleanup.

---

### G-004: Mixed Logging Systems (loguru + structlog)
**Severity:** MEDIUM
**Location:** 67 files use loguru, 35 files use structlog

Both logging systems are configured and both inject `request_id`. However:
- **Output format divergence:** loguru produces `YYYY-MM-DD HH:mm:ss | LEVEL | module:function:line | request_id | message`. structlog produces either JSON or colored console output with key-value pairs.
- **Log aggregation difficulty:** A log aggregation system would need to parse two distinct formats.
- **No shared context beyond request_id:** structlog modules use `.bind(component="...")` for context; loguru modules do not have an equivalent structured context mechanism.

The dual system is intentional (extraction layer adopted structlog for structured context binding), and both are configured in `core/logging.py`. This is not broken, but it is a maintenance burden that increases as the codebase grows.

---

### G-005: `error_category` Column Underutilized in Extraction
**Severity:** LOW
**Location:** `backend/app/models/extraction.py`, `backend/app/extraction/error_handler.py`

The `ExtractedValue.error_category` column (String(50)) exists and 9 error categories are defined in the pipeline. However, discovery document 06 notes the field is "often null in practice." The `error_handler.py` (line 447) has `get_recovery_suggestion()` keyed by category, and `validation.py` (line 171) references it. But the extraction pipeline itself does not consistently populate it.

**Impact:** Debugging extraction failures requires log analysis rather than simple DB queries.

---

### G-006: Demo User Authentication Bypass in Development
**Severity:** LOW (design intent, not a bug)
**Location:** `backend/app/api/v1/endpoints/auth.py:126-128`

The login endpoint has a fallback that checks demo user credentials if DB authentication fails. This is gated by:
- Config validator (`config.py:384`): raises `ValueError` if demo passwords are set in production
- Empty string defaults: demo passwords won't match unless explicitly configured

This is correctly designed but worth documenting: in development, the demo user fallback bypasses the normal DB + password hash flow.

---

### G-007: `deploy.yml.disabled` Artifact Remains
**Severity:** LOW
**Location:** `.github/workflows/deploy.yml.disabled`

The disabled deploy workflow file still exists. It has no functional impact but is a minor source of confusion for new developers.

---

### G-008: SharePoint Health Check is Config-Only
**Severity:** LOW
**Location:** `backend/app/api/v1/endpoints/health.py:85-89`

The SharePoint health check only verifies that credentials are configured (`settings.sharepoint_configured`). It does not attempt an actual API call to verify connectivity. A real health check would attempt a Graph API call (e.g., list a known folder) to confirm the credentials are valid and the service is reachable.

---

## 3. Cross-Cutting Patterns

### 3.1 Mixed Sync/Async
The extraction pipeline was identified in the remediation plan (D-11) as having sync sessions in async endpoints. Current state: the extraction monitor endpoints (`backend/app/api/v1/endpoints/extraction/monitor.py`) now use `AsyncSession` (verified at lines 12, 25, 70, 114, 179). The D-11 finding appears to be resolved for the monitor endpoints, though the core extraction pipeline still uses sync operations internally (openpyxl is sync).

### 3.2 Hardcoded Values
The tech debt remediation extracted 60+ magic numbers into `staleTime` constants (`src/lib/constants/query.ts`). This is well-addressed on the frontend. Backend still has some hardcoded values:
- Report worker poll interval: `POLL_INTERVAL = 30` (report_worker.py:39)
- Cache cleanup interval: `CLEANUP_INTERVAL = 300` (cache.py:51)
- Token blacklist eviction high-water: `_EVICTION_HIGH_WATER = 1000` (token_blacklist.py:24)

These are not problematic -- they are internal implementation constants with clear names and comments. No action needed.

### 3.3 Dual Import Paths for API Client
Frontend code imports the API client via two paths:
1. `from '@/lib/api'` (18 files) -- re-exports from `./client`
2. `from '@/lib/api/client'` (6 files) -- direct import

Functionally identical, but inconsistent. A codemod to standardize on `@/lib/api` would improve consistency.

### 3.4 Request ID Coverage
The `RequestIDMiddleware` sets a `ContextVar` that is automatically injected into both loguru and structlog output. The middleware covers all HTTP requests. However:
- WebSocket connections do not go through the middleware chain (they use the WebSocket protocol)
- Background tasks (report worker, extraction scheduler, cache cleanup) run outside request context and will have `request_id = "-"` in their logs

---

## 4. Infrastructure Gaps

### 4.1 Redis Not Running
Redis is configured but likely not running locally (WSL2 environment). The application gracefully degrades, but this means:
- Token blacklist: in-memory, lost on restart. A user who logged out has their token re-valid after restart.
- Cache: in-memory, per-process. Multiple Uvicorn workers would have independent caches.
- Rate limiter: in-memory, per-process. Rate limits are per-worker, not per-user across workers.
- Pub/sub: non-functional. WebSocket notifications cannot cross worker boundaries.

**User has confirmed: "Let's add now!"** -- Redis enablement is a P0 priority.

### 4.2 No Production Hosting
The project runs on WSL2 locally. Docker configuration exists but no deployment target is configured. The disabled `deploy.yml` workflow confirms CI/CD deployment is not operational.

### 4.3 No Log Aggregation
Logs go to stdout (development) and rotated files (production). No ELK, Loki, CloudWatch, or other aggregation pipeline is configured. For a single-instance deployment this is acceptable, but it means:
- No cross-request log correlation beyond manual file analysis
- No alerting on error rate spikes
- No log-based metrics or dashboards

### 4.4 No APM/Tracing
The Prometheus metrics endpoint exists (`/monitoring/metrics`) but there is no Prometheus server or Grafana dashboard to consume it. No OpenTelemetry, Datadog, or New Relic integration. The request_id provides correlation within a single request but there is no distributed tracing.

---

## 5. Summary of Open Items

| ID | Finding | Severity | Category |
|----|---------|----------|----------|
| G-001 | Redis URL missing password | HIGH | Security/Config |
| G-002 | Redis not verified running | MEDIUM | Infrastructure |
| G-003 | Inconsistent API client imports | LOW | Code quality |
| G-004 | Mixed loguru/structlog (35+67 files) | MEDIUM | Observability |
| G-005 | error_category column underutilized | LOW | Data quality |
| G-006 | Demo auth fallback in dev (by design) | LOW | Documentation |
| G-007 | deploy.yml.disabled artifact | LOW | Cleanup |
| G-008 | SharePoint health check is config-only | LOW | Observability |

All 7 original critical findings (F-001 through F-007) are verified FIXED.
