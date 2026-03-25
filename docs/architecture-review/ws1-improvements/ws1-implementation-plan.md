# WS1 Implementation Plan

**Date:** 2026-03-25
**Scope:** BMAD-style epic/story/task breakdown for general improvements
**Execution order:** Epic 1 -> Epic 2 -> Epics 3-5 (parallelizable)

---

## Epic 1: Redis Enablement (P0)

**Goal:** Get Redis running, properly configured, and verified as the active backend for cache, token blacklist, and rate limiter.
**Priority:** P0 -- user confirmed "Let's add now!"
**Total effort:** S-M (1-2 hours)

### Story 1.1: Install and Configure Redis
**Size:** S

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 1.1.1 | Install Redis on WSL2 | System | `sudo apt install redis-server` |
| 1.1.2 | Configure Redis password | `/etc/redis/redis.conf` | Set `requirepass redis_secure_password_2026` |
| 1.1.3 | Start Redis service | System | `sudo service redis-server start` |
| 1.1.4 | Verify connectivity | System | `redis-cli -a redis_secure_password_2026 ping` |
| 1.1.5 | Fix REDIS_URL in .env | `backend/.env:62` | Change to `redis://:redis_secure_password_2026@localhost:6379/0` |
| 1.1.6 | Verify app connects | App startup | Start backend, check logs for "Redis connection established" |

### Story 1.2: Add Redis Startup Validation
**Size:** S

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 1.2.1 | Add `REDIS_REQUIRED` config | `backend/app/core/config.py` | Boolean, default `False`, document purpose |
| 1.2.2 | Add startup validation | `backend/app/main.py:190-196` | If `REDIS_REQUIRED` and Redis fails, raise `RuntimeError` |
| 1.2.3 | Add clear log message | `backend/app/main.py` | Log Redis mode: "active" vs "fallback (in-memory)" with URL (masked password) |
| 1.2.4 | Update health check | `backend/app/api/v1/endpoints/health.py` | Redis check already exists, just verify it reflects real status |
| 1.2.5 | Add test | `backend/tests/test_core/` | Test that `REDIS_REQUIRED=True` + no Redis raises during lifespan |

### Story 1.3: Verify Redis Integration
**Size:** S

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 1.3.1 | Test token blacklist with Redis | Manual | Login, logout, verify blacklisted token rejected |
| 1.3.2 | Test cache with Redis | Manual | Hit endpoint, verify `KEYS dashboard:*` shows entries |
| 1.3.3 | Test rate limiter with Redis | Manual | Rapid-fire requests, verify rate limit triggers |
| 1.3.4 | Test health check | Manual | `GET /api/v1/health/status` should show `redis: {status: "up"}` |

**Acceptance criteria:**
- Redis is running and accepting connections with authentication
- Application logs "Redis connection established" on startup
- Token blacklist survives server restart
- Health check shows Redis as "up"

---

## Epic 2: Security Config Hardening (P0-P1)

**Goal:** Ensure config settings are production-safe and no silent misconfigurations exist.
**Priority:** P0-P1
**Total effort:** S (30 min)

### Story 2.1: Config Validation
**Size:** S

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 2.1.1 | Validate REDIS_URL has password if REDIS_PASSWORD is set | `backend/app/core/config.py` | Add `model_validator` that warns if REDIS_PASSWORD is set but not in REDIS_URL |
| 2.1.2 | Validate SECRET_KEY strength in production | `backend/app/core/config.py` | Existing validator may already cover this -- verify |
| 2.1.3 | Add .env.example with documented variables | `backend/.env.example` | Template without secrets, documenting all required vars |

**Acceptance criteria:**
- Config validator warns on password mismatch
- New developers can copy `.env.example` and fill in secrets

---

## Epic 3: Observability Improvements (P1)

**Goal:** Unify logging, ensure correlation IDs work end-to-end, improve health checks.
**Priority:** P1
**Total effort:** M-L (4-8 hours)

### Story 3.1: Unify Logging to Loguru
**Size:** M

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 3.1.1 | Create migration pattern | Documentation | Define loguru equivalent of `structlog.get_logger().bind(component="X")` -- use `logger.bind(component="X")` |
| 3.1.2 | Migrate extraction core (13 files) | `backend/app/extraction/*.py` | Replace `structlog.get_logger()` with `from loguru import logger` + `.bind()` |
| 3.1.3 | Migrate extraction services (5 files) | `backend/app/services/extraction/*.py` | Same pattern |
| 3.1.4 | Migrate data extraction (3 files) | `backend/app/services/data_extraction/*.py` | Same pattern |
| 3.1.5 | Migrate construction API (6 files) | `backend/app/services/construction_api/*.py` | Same pattern |
| 3.1.6 | Migrate middleware/db (2 files) | `backend/app/middleware/etag.py`, `backend/app/db/query_logger.py` | Same pattern |
| 3.1.7 | Remove structlog config | `backend/app/core/logging.py` | Remove `setup_structlog()`, `_add_request_id()`, and structlog import |
| 3.1.8 | Remove structlog dependency | `backend/requirements.txt` | Remove `structlog` (verify no remaining imports first) |
| 3.1.9 | Run tests | `cd backend && python -m pytest` | Verify no regressions from logging changes |
| 3.1.10 | Run frontend tests | `npm run test:run` | Ensure no indirect breakage |

### Story 3.2: Background Task Correlation IDs
**Size:** S

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 3.2.1 | Set request_id for report worker | `backend/app/services/report_worker.py` | Set `request_id_ctx.set(f"bg-report-{job_id}")` before processing each job |
| 3.2.2 | Set request_id for extraction scheduler | `backend/app/services/extraction/scheduler.py` | Set `request_id_ctx.set(f"bg-extract-{run_id}")` |
| 3.2.3 | Set request_id for cache cleanup | `backend/app/core/cache.py` | Set `request_id_ctx.set("bg-cache-cleanup")` |
| 3.2.4 | Set request_id for market data scheduler | `backend/app/services/data_extraction/scheduler.py` | Set `request_id_ctx.set("bg-market-refresh")` |

### Story 3.3: SharePoint Health Check Enhancement
**Size:** M

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 3.3.1 | Add Graph API connectivity check | `backend/app/api/v1/endpoints/health.py` | Attempt `GET /me` or list known folder, with 3-second timeout |
| 3.3.2 | Handle auth failure gracefully | Same | If MSAL token acquisition fails, return `{status: "auth_failed"}` |
| 3.3.3 | Add to readiness check | Same | Include SharePoint status in `/health/status/ready` optional checks |
| 3.3.4 | Add test | `backend/tests/test_api/` | Mock SharePoint check, verify health response |

**Acceptance criteria:**
- All log output uses loguru exclusively
- Background tasks have identifiable correlation IDs
- Health check validates actual SharePoint connectivity (not just config)

---

## Epic 4: Auth System Polish (P1)

**Goal:** Ensure the auth system is complete and production-ready.
**Priority:** P1
**Total effort:** S (30 min -- mostly verification)

### Story 4.1: Verify Refresh Token Flow End-to-End
**Size:** S

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 4.1.1 | Manual test: login, wait for token expiry, verify auto-refresh | Browser | Set `ACCESS_TOKEN_EXPIRE_MINUTES=1` temporarily, perform API call after expiry |
| 4.1.2 | Verify concurrent refresh dedup | Browser | Open multiple tabs, expire token, verify only one refresh call fires |
| 4.1.3 | Verify refresh failure -> logout | Browser | Invalidate refresh token, verify user is redirected to login |
| 4.1.4 | Document auth flow | `docs/` | Create sequence diagram of login -> refresh -> logout flow (if requested) |

### Story 4.2: Verify REFRESH_TOKEN_SECRET Separation
**Size:** S

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 4.2.1 | Set REFRESH_TOKEN_SECRET in .env | `backend/.env` | Add a distinct secret value |
| 4.2.2 | Verify access tokens cannot be used as refresh tokens | Manual | Attempt `POST /auth/refresh` with access token -- should fail |
| 4.2.3 | Verify refresh tokens cannot be used as access tokens | Manual | Attempt API call with refresh token as Bearer -- should get 401 |

**Acceptance criteria:**
- Refresh flow works end-to-end in browser
- Access and refresh tokens are not interchangeable

---

## Epic 5: Code Health (P2)

**Goal:** Clean up minor tech debt and improve developer experience.
**Priority:** P2
**Total effort:** S (30 min)

### Story 5.1: Standardize Frontend API Imports
**Size:** S

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 5.1.1 | Change direct client imports | 6 files | Replace `from '@/lib/api/client'` with `from '@/lib/api'` |
| 5.1.2 | Run frontend tests | `npm run test:run` | Verify no import resolution failures |
| 5.1.3 | Add lint rule (optional) | `eslint.config.js` | Ban direct `@/lib/api/client` imports |

### Story 5.2: Remove Disabled Deploy Workflow
**Size:** S

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 5.2.1 | Delete file | `.github/workflows/deploy.yml.disabled` | Remove artifact |
| 5.2.2 | Update any references | Search codebase | Verify no other files reference it |

### Story 5.3: Populate error_category in Extraction
**Size:** M

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 5.3.1 | Audit error paths in extractor.py | `backend/app/extraction/extractor.py` | Identify all `except` blocks that create/update ExtractedValue |
| 5.3.2 | Map exceptions to categories | Same | Use the 9 defined categories (auth, network, file_access, parse, mapping, validation, transform, storage, unknown) |
| 5.3.3 | Set error_category on failure | Same + `group_pipeline.py` | `extracted_value.error_category = category` |
| 5.3.4 | Add tests | `backend/tests/test_extraction/` | Verify category is set for each error type |

**Acceptance criteria:**
- All frontend API imports use `@/lib/api`
- No disabled workflow artifacts
- error_category populated for >90% of extraction errors

---

## Execution Timeline

```
Day 1 (2h):
  Epic 1: Redis Enablement ████████████████
    1.1: Install + Configure (30 min)
    1.2: Startup Validation (30 min)
    1.3: Integration Verification (30 min)
  Epic 2: Config Hardening (30 min) ████

Day 1-2 (4-6h):
  Epic 3.1: Logging Unification ████████████████████████
    35 files: structlog -> loguru migration

Day 2 (1h):
  Epic 3.2: Background Correlation IDs ████
  Epic 4: Auth Verification ████
  Epic 5.1-5.2: Import cleanup + artifact removal ████

Day 3 (optional, 2h):
  Epic 3.3: SharePoint Health Check ████████
  Epic 5.3: error_category Population ████████
```

---

## Dependencies

```
Epic 1 (Redis) ─── no dependencies, start immediately
     │
     ├──> Epic 2 (Config) ─── depends on Redis URL being correct
     │
     └──> Epic 3 (Observability) ─── independent of Redis
              │
              └──> Epic 4 (Auth) ─── can verify after Redis is active
                        │
                        └──> Epic 5 (Code Health) ─── independent
```

---

## Gate Criteria

| Gate | Criteria |
|------|----------|
| Epic 1 Done | Redis running, health check shows "up", token blacklist persists across restart |
| Epic 2 Done | Config validator warns on misconfigurations |
| Epic 3 Done | `grep -r "structlog" backend/app/` returns 0 results, all background tasks have correlation IDs |
| Epic 4 Done | Manual verification of refresh flow succeeds |
| Epic 5 Done | `npm run test:run` + `python -m pytest` both pass, no disabled workflow files |
| WS1 Complete | All epics pass gate criteria, no new regressions in test suites |
