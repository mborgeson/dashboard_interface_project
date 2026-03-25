# WS1 Recommendations

**Date:** 2026-03-25
**Scope:** Prioritized recommendations for general improvements

---

## P0 -- Critical (Security / Data Integrity)

### R-001: Enable Redis with Correct Authentication
**What:** Install and start Redis, fix the `REDIS_URL` to include the password, verify connectivity.
**Why:** Without Redis, the token blacklist is in-memory (lost on restart), cache is per-process (inconsistent data), rate limiter is per-process (bypassable with multiple workers), and pub/sub is non-functional. The user has confirmed this should be done now.
**Where:**
- `backend/.env:14` -- `REDIS_PASSWORD` is set but not used in URL
- `backend/.env:62` -- `REDIS_URL` needs password: `redis://:redis_secure_password_2026@localhost:6379/0`
- WSL2: `sudo apt install redis-server && sudo service redis-server start`
- Verify: `redis-cli -a redis_secure_password_2026 ping`
**Effort:** S (Small) -- config change + service start
**Priority:** P0

---

### R-002: Add Redis Startup Validation
**What:** After Redis is enabled, add a startup check that logs clearly whether Redis is connected or falling back, and optionally fail-fast in production if Redis is not available.
**Why:** Silent degradation to in-memory is dangerous in production -- rate limiting, token blacklist, and cache all lose their guarantees.
**Where:**
- `backend/app/main.py:190-196` (lifespan Redis init)
- Add `REDIS_REQUIRED` config setting (default `False` in dev, `True` in production)
- If `REDIS_REQUIRED=True` and Redis is unreachable, raise during startup
**Effort:** S (Small)
**Priority:** P0

---

## P1 -- Important (Production Readiness)

### R-003: Unify Logging to Single System
**What:** Choose either loguru or structlog as the single logging system and migrate all modules.
**Why:** Two logging systems produce two output formats, making log aggregation and parsing harder. Both are configured to inject `request_id`, so the infrastructure is there -- but maintaining two formatters, two configuration paths, and two mental models is unnecessary overhead.
**Recommendation:** Keep **loguru** as the primary (67 files already use it, it is the project standard per CLAUDE.md). Migrate the 35 structlog files to loguru. structlog's `.bind(component="...")` pattern can be replicated with loguru's `logger.bind(component="ExcelDataExtractor")`.
**Where:**
- `backend/app/extraction/` (13 files use structlog)
- `backend/app/services/extraction/` (5 files)
- `backend/app/services/data_extraction/` (3 files)
- `backend/app/services/construction_api/` (6 files)
- `backend/app/middleware/etag.py`, `backend/app/db/query_logger.py`
- `backend/app/core/logging.py` -- remove `setup_structlog()` after migration
**Effort:** M (Medium) -- 35 files, mostly search-and-replace with `logger.bind()`
**Priority:** P1

---

### R-004: Verify Correlation IDs in Log Output
**What:** Confirm that `request_id` appears in all log output, including background tasks. Add a sentinel value (e.g., `bg-report-worker`, `bg-extraction-scheduler`) for background task logs so they can be distinguished from request-scoped logs.
**Why:** The `ContextVar`-based request_id injection is correctly implemented for HTTP requests. Background tasks (report worker, extraction scheduler, cache cleanup) run outside request context and will have `request_id = "-"`. This is technically correct but makes it harder to filter background task logs.
**Where:**
- `backend/app/services/report_worker.py` -- set `request_id_ctx` before processing
- `backend/app/extraction/group_pipeline.py` -- set `request_id_ctx` for extraction runs
- `backend/app/services/extraction/scheduler.py` -- set `request_id_ctx` for scheduled runs
**Effort:** S (Small) -- a few lines per background task entry point
**Priority:** P1

---

### R-005: Fix Redis URL Password Mismatch
**What:** Update `REDIS_URL` in `.env` to include the password, or remove the separate `REDIS_PASSWORD` variable if not used.
**Why:** The current config has `REDIS_PASSWORD=redis_secure_password_2026` as a standalone variable and `REDIS_URL=redis://localhost:6379/0` without a password. If Redis requires authentication, every connection will fail and fall back to in-memory.
**Where:** `backend/.env:14,62`
**Effort:** S (Small) -- one line change
**Priority:** P1 (bundled with R-001)

---

### R-006: Standardize Frontend API Client Imports
**What:** Run a codemod to standardize all imports to `from '@/lib/api'` instead of the mix of `@/lib/api` (18 files) and `@/lib/api/client'` (6 files).
**Why:** Inconsistent imports create confusion about which module to import from. Since `@/lib/api/index.ts` re-exports everything from `./client`, the paths are functionally equivalent -- but new developers may not know that.
**Where:**
- `src/stores/authStore.ts` -- imports from `@/lib/api/client`
- `src/features/market/hooks/useMarketData.ts`
- `src/features/extraction/hooks/useExtraction.ts`
- `src/features/extraction/hooks/useGroupPipeline.ts`
- `src/stores/authStore.test.ts`
- `src/features/extraction/hooks/__tests__/useGroupPipeline.test.ts`
**Effort:** S (Small) -- 6 import path changes
**Priority:** P1

---

### R-007: Remove `deploy.yml.disabled` Artifact
**What:** Delete `.github/workflows/deploy.yml.disabled`.
**Why:** The disabled workflow has no function and creates minor confusion. If a deployment workflow is needed in the future, it should be written fresh for the actual deployment target (Oracle Cloud, Hetzner, etc.).
**Where:** `.github/workflows/deploy.yml.disabled`
**Effort:** S (Small) -- delete one file
**Priority:** P2

---

## P2 -- Nice to Have (Code Quality)

### R-008: Add Structured SharePoint Health Check
**What:** Extend the health check at `GET /api/v1/health/status` to attempt an actual SharePoint/Graph API call (e.g., list a known folder) rather than just checking if credentials are configured.
**Why:** Config-only checks pass even when credentials are expired or the service is unreachable.
**Where:** `backend/app/api/v1/endpoints/health.py:85-89`
**Effort:** M (Medium) -- needs async Graph API call with timeout, error handling
**Priority:** P2

---

### R-009: Populate `error_category` in Extraction Pipeline
**What:** Ensure the extraction pipeline consistently sets `error_category` on `ExtractedValue` records when errors occur, using the 9 defined categories.
**Why:** The column exists, the categories are defined, and the error_handler has recovery suggestions per category -- but the field is often null in practice. Populating it enables DB-level error analysis without log parsing.
**Where:** `backend/app/extraction/extractor.py`, `backend/app/extraction/group_pipeline.py`
**Effort:** M (Medium) -- needs audit of all error paths in extraction pipeline
**Priority:** P2

---

### R-010: Add Background Task Correlation IDs
**What:** Set meaningful `request_id_ctx` values for background tasks so their logs are traceable.
**Why:** Background tasks log with `request_id = "-"` which makes them hard to distinguish from each other in aggregated logs.
**Where:** Report worker, extraction scheduler, cache cleanup, market data scheduler
**Effort:** S (Small)
**Priority:** P2

---

## Summary Table

| ID | Recommendation | Effort | Priority | Category |
|----|---------------|--------|----------|----------|
| R-001 | Enable Redis with correct auth | S | P0 | Infrastructure |
| R-002 | Add Redis startup validation | S | P0 | Infrastructure |
| R-003 | Unify logging (loguru everywhere) | M | P1 | Observability |
| R-004 | Verify correlation IDs in log output | S | P1 | Observability |
| R-005 | Fix Redis URL password mismatch | S | P1 | Config |
| R-006 | Standardize frontend API imports | S | P1 | Code quality |
| R-007 | Remove deploy.yml.disabled | S | P2 | Cleanup |
| R-008 | Structured SharePoint health check | M | P2 | Observability |
| R-009 | Populate error_category in extraction | M | P2 | Data quality |
| R-010 | Background task correlation IDs | S | P2 | Observability |
