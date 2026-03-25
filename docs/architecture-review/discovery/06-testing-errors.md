# Discovery Document: Testing & Error Handling

**Date:** 2026-03-25
**Scope:** Test inventory, test infrastructure, error handling patterns, health checks, CI/CD
**Status:** Discovery complete

---

## 1. Test Inventory

### 1.1 Backend Tests (`backend/tests/`)

| Metric | Value |
|--------|-------|
| Total Python files in tests directory | 161 |
| Test files (`test_*.py`) | 135 |
| Test functions | 3,130 |

**Directory structure:**

| Directory | Purpose |
|-----------|---------|
| `test_api/` | API endpoint tests |
| `test_core/` | Core module tests (config, cache, token blacklist) |
| `test_middleware/` | Middleware tests (rate limiter) |
| `test_models/` | Model tests |
| `test_services/` | Service tests (redis, cache, batch, monitoring, workflow) |
| `test_security/` | Security tests (error sanitization) |
| `test_tasks/` | Task system tests (registry, fallback, definitions) |
| `conftest.py` | Shared fixtures |

### 1.2 Frontend Tests (`src/`)

| Metric | Value |
|--------|-------|
| Test files (`.test.tsx`, `.test.ts`, `.spec.tsx`, `.spec.ts`) | 72 |

**Key test areas:**

- `src/features/dashboard-main/__tests__/`
- `src/features/underwriting/hooks/__tests__/`
- `src/features/underwriting/utils/__tests__/calculations.test.ts`
- `src/features/transactions/hooks/__tests__/`
- `src/features/mapping/__tests__/`
- `src/features/analytics/__tests__/`
- `src/features/extraction/__tests__/`
- `src/features/extraction/components/__tests__/`
- `src/features/extraction/hooks/__tests__/`
- `src/features/property-detail/__tests__/`
- `src/features/market/__tests__/`
- `src/features/construction-pipeline/__tests__/`
- `src/features/construction-pipeline/components/__tests__/`

### 1.3 E2E Tests

Playwright configured and run via `npm run test:e2e`.

---

## 2. Test Infrastructure

### 2.1 Backend (pytest)

**Database:** SQLite in-memory for all DB tests.

| Constraint | Detail |
|------------|--------|
| Connection pool | `StaticPool` (single connection) |
| `server_default` | Not supported in SQLite -- timestamps must use `datetime.now(UTC)` |
| `begin_nested()` | Unreliable with StaticPool |

**Authentication fixtures:**

| Fixture | Role | Usage |
|---------|------|-------|
| `auth_headers` | Analyst | GET endpoints, analyst-level operations |
| `admin_auth_headers` | Admin | POST/PUT/DELETE on admin-only endpoints |

**Environment:**

- Conda env: `dashboard-backend`
- Run command: `cd backend && python -m pytest`

### 2.2 Frontend (vitest)

| Setting | Value |
|---------|-------|
| Test location | Colocated with features or in `src/test/` |
| Run command | `npm run test:run` |
| Router flags | React Router v7 future flags required in test wrappers |
| Lint rules | ESLint react-compiler rules enforced |

---

## 3. Error Handling Patterns

### 3.1 Backend Exception Architecture

**Middleware layer:**

- `ErrorHandlerMiddleware` catches unhandled exceptions and returns structured JSON responses.
- Global exception handler: `@app.exception_handler(Exception)` includes `request_id` in every error response.

**Custom exceptions:**

| Exception | Purpose |
|-----------|---------|
| `SharePointAuthError` | Authentication failures against SharePoint/Azure AD |
| `FileAccessError` | Corrupt or unreadable files (XLSB, BadZipFile) |
| `HTTPException` | Used throughout API endpoints for standard HTTP errors |

**Error sanitization in production:** Internal details (stack traces, SQL fragments, file paths) are stripped from responses before they reach the client.

### 3.2 Extraction Error Handling

**Retry mechanism:**
- On 401 responses: clears the token cache and retries once before failing.

**Corrupt file handling:**
- `BadZipFile` caught and converted to `FileAccessError`.
- Pipeline skips the file and continues processing remaining files.

**Per-file error tracking:**
- `ExtractionRun.per_file_status` (JSON field) records per-file outcome.
- Status values: `"completed"`, `"failed"`, `"skipped"`.
- Error message preserved for each file.

**Per-value error tracking:**

| Field | Type | Description |
|-------|------|-------------|
| `ExtractedValue.is_error` | Boolean | Marks individual value extraction errors |
| `ExtractedValue.error_category` | String(50) | Exists but underutilized (often null) |

**Nine error categories defined in the pipeline:**

| Category | Description |
|----------|-------------|
| `auth` | SharePoint/Azure AD authentication failure |
| `network` | Network connectivity issues |
| `file_access` | File cannot be opened (corrupt, locked, wrong format) |
| `parse` | Excel parsing errors (openpyxl) |
| `mapping` | Cell mapping lookup failures |
| `validation` | Extracted value fails validation rules |
| `transform` | Type coercion/conversion errors |
| `storage` | Database upsert failures |
| `unknown` | Uncategorized errors |

### 3.3 Logging

| Logger | Scope | Style |
|--------|-------|-------|
| **loguru** | General application logging | Used throughout most modules |
| **structlog** | Extraction layer | Structured key-value logging with component binding |

**Mixed usage:** Some modules use loguru while extraction modules use structlog. The two systems are not unified.

**Request correlation:**
- `RequestIDMiddleware` generates `X-Request-ID` headers.
- Not consistently referenced in all log calls -- correlation between request and log entries is incomplete in practice.

---

## 4. Health Checks

### 4.1 Endpoints

| Endpoint | Auth Required | Purpose |
|----------|---------------|---------|
| `GET /api/v1/health` | No | Legacy simple status response |
| `GET /api/v1/health/status` | See note | Deep health checks |

**Deep checks cover:**
- Database connectivity
- Redis availability
- SharePoint accessibility

**Note on F-002:** The legacy health endpoint exists without auth. The detailed `/status` endpoint may still have an auth guard, which would prevent external monitoring tools from using it.

---

## 5. Test Coverage Observations

### 5.1 Strong Coverage Areas

- API endpoints
- Middleware (rate limiter, error handler)
- Core modules (config, cache, token blacklist)
- Extraction pipeline (49+ regression tests added 2026-03-05)

### 5.2 Partially Addressed

- Financial calculation tests (F-006 from prior architecture review)

### 5.3 Missing or Weak Coverage

- End-to-end extraction flow (SharePoint to database)
- WebSocket integration tests

---

## 6. CI/CD

### 6.1 GitHub Actions

- Workflows located in `.github/workflows/`.
- `deploy.yml` previously had a `workflow_run` trigger that caused Action spam. The file has been disabled (`.disabled` file remains in the directory).

### 6.2 Pre-Commit Hooks

- **ruff** linting and formatting enforced before commits.

---

## 7. Summary

### Test Counts

| Layer | Files | Functions |
|-------|-------|-----------|
| Backend (`backend/tests/`) | 135 test files (161 total) | 3,130 |
| Frontend (`src/`) | 72 test files | -- |
| E2E (Playwright) | Configured | -- |

### Error Handling Coverage

| Layer | Mechanism | Behavior |
|-------|-----------|----------|
| **HTTP middleware** | `ErrorHandlerMiddleware` | Catches all unhandled exceptions, returns structured JSON with `request_id` |
| **API endpoints** | `HTTPException` | Standard FastAPI error responses |
| **SharePoint auth** | 401 retry | Clears token cache, retries once |
| **File processing** | `BadZipFile` catch | Raises `FileAccessError`, pipeline skips and continues |
| **Extraction values** | `is_error` + `error_category` | Per-value error tracking (category field underutilized) |
| **Production responses** | Error sanitization | Strips internal details (paths, SQL, stack traces) |

### Key Infrastructure Decisions

| Decision | Rationale |
|----------|-----------|
| SQLite in-memory for backend tests | Speed; `StaticPool` avoids connection overhead |
| `datetime.now(UTC)` in tests | SQLite does not support `server_default` |
| Separate auth fixtures per role | Clean separation of analyst vs admin vs no-auth test paths |
| loguru + structlog coexistence | Organic growth; extraction layer adopted structlog independently |
| Nine extraction error categories | Granular classification, though `error_category` field is often null in practice |

---

*Discovery document for architecture review. No code modifications included.*
