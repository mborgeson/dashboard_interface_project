# Backend Architecture Reference

Generated: 2026-03-10

B&R Capital Real Estate Analytics Dashboard — FastAPI + SQLAlchemy 2.0 async backend.

---

## Table of Contents

1. [Application Entry Point & Middleware Chain](#1-application-entry-point--middleware-chain)
2. [Authentication & Authorization](#2-authentication--authorization)
3. [API Endpoints](#3-api-endpoints)
4. [CRUD Layer](#4-crud-layer)
5. [SQLAlchemy Models](#5-sqlalchemy-models)
6. [Pydantic Schemas](#6-pydantic-schemas)
7. [Extraction Pipeline](#7-extraction-pipeline)
8. [Services](#8-services)
9. [Database Layer](#9-database-layer)
10. [Alembic Migrations](#10-alembic-migrations)
11. [Test Suite](#11-test-suite)
12. [Settings Reference](#12-settings-reference)
13. [Architectural Decision Records](#13-architectural-decision-records)

---

## 1. Application Entry Point & Middleware Chain

**File:** `backend/app/main.py`

### FastAPI Application

- `title`: B&R Capital Dashboard API
- `version`: 2.0.0
- `docs_url`: `/api/docs` (development only; disabled in production)
- `openapi_url`: `/api/v1/openapi.json` (development only)
- All routers mounted under `/api/v1`

### Middleware Chain (registered outermost-first, executes top-down)

Starlette executes middleware in last-registered-first order. The chain below shows execution order from outermost to innermost:

| Order | Middleware | Class | Purpose |
|-------|-----------|-------|---------|
| 1 (outermost) | RequestIDMiddleware | `app/middleware/request_id.py` | Assigns/propagates UUID4 correlation ID via `X-Request-ID` header and `ContextVar` |
| 2 | OriginValidationMiddleware | `app/main.py` (inline) | Defense-in-depth CSRF: validates `Origin`/`Referer` on POST/PUT/PATCH/DELETE against `CORS_ORIGINS` list |
| 3 | ErrorHandlerMiddleware | `app/middleware/error_handler.py` | Catches `SQLAlchemyError` → 500, `ValidationError` → 422, `PermissionError` → 403, `ValueError` → 400, generic `Exception` → 500 with `request_id` |
| 4 | SecurityHeadersMiddleware | `app/main.py` (inline) | Adds `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection: 0`, `Referrer-Policy`, `Permissions-Policy`, `Content-Security-Policy`, `Cache-Control: no-store`, `HSTS` (production only) |
| 5 | ETagMiddleware | `app/middleware/etag.py` | Computes SHA-256 ETag for GET responses; returns 304 on `If-None-Match` match |
| 6 | RateLimitMiddleware | `app/middleware/rate_limiter.py` | Sliding-window rate limiting (memory or Redis); rules: auth endpoints 5 req/60s, token refresh 10 req/60s, API 100 req/60s. Adds `X-RateLimit-*` headers. Enabled when `RATE_LIMIT_ENABLED=true` |
| 7 | MetricsMiddleware | `app/services/monitoring/middleware.py` | Records Prometheus `http_requests_total`, `http_request_duration_seconds` counters/histograms per endpoint |
| 8 (innermost) | CORSMiddleware | FastAPI built-in | Allows `CORS_ORIGINS` origins; exposes `X-Request-ID`, `ETag` |

### Lifespan Events (startup/shutdown)

On startup:
1. `setup_logging()` — initializes Loguru + structlog
2. `MetricsManager.initialize()` — sets Prometheus APP_INFO gauge
3. `ConnectionPoolCollector.set_engine()` — wires async/sync engines to pool monitoring
4. `ExtractionScheduler.initialize()` — APScheduler for daily 5 PM extraction (configurable)
5. `MonitorScheduler.initialize()` — file-change monitor every 30 min (configurable)
6. `MarketDataScheduler.start()` — CoStar/FRED/Census data refresh scheduler
7. `InterestRateScheduler.start()` — twice-daily FRED interest rate fetch

On shutdown: all schedulers stopped in reverse order.

### Global Exception Handler

Catches any exception not handled by `ErrorHandlerMiddleware`. Returns:
```json
{"detail": "An unexpected error occurred", "request_id": "<uuid>"}
```

---

## 2. Authentication & Authorization

### JWT Authentication

**Files:** `backend/app/core/security.py`, `backend/app/core/permissions.py`

| Function | Purpose |
|---------|---------|
| `create_access_token(subject, additional_claims)` | HS256 JWT; 30-min expiry (configurable); includes `jti` UUID for blacklisting |
| `create_refresh_token(subject)` | HS256 JWT; 7-day expiry; `type="refresh"`; includes `jti` |
| `decode_token(token)` | Validates signature and expiry; returns payload dict or `None` |
| `verify_password(plain, hashed)` | bcrypt via passlib |
| `get_password_hash(password)` | bcrypt hash |

### Token Blacklist

**File:** `backend/app/core/token_blacklist.py`

Singleton `TokenBlacklist` instance (`token_blacklist`). Stores revoked JTIs as `blacklist:<jti>` keys with TTL equal to remaining token lifetime. Falls back to in-memory dict when Redis unavailable.

Methods: `add(jti, expires_in)`, `is_blacklisted(jti)`, `revoke_user_tokens(user_id, expires_in)`, `is_user_revoked(user_id)`, `clear_user_revocation(user_id)`, `remove(jti)`, `cleanup_memory()`, `get_stats()`

### Refresh Token Rotation with Replay Detection

**File:** `backend/app/api/v1/endpoints/auth.py`

- Each `POST /auth/refresh` call issues a new access token AND new refresh token
- The old refresh token JTI is added to the blacklist
- If a blacklisted refresh token is presented again (replay attack), `revoke_user_tokens()` is called, invalidating all sessions for that user

### API Key Authentication

**File:** `backend/app/core/api_key_auth.py`

- Header: `X-API-Key` (configurable via `API_KEY_HEADER`)
- Keys configured via `API_KEYS` env var (comma-separated)
- Comparison via `hmac.compare_digest` (constant-time, timing-attack resistant)
- Dependency `require_api_key` raises 401 if not valid
- Dependency `require_api_key_or_jwt` tries JWT Bearer first, falls back to API key
- Returns `ServiceIdentity(service_name="api_key_service")` for API key callers

### RBAC — Roles and Permissions

**File:** `backend/app/core/permissions.py`

| Role | Hierarchy Level | Capabilities |
|------|----------------|-------------|
| `viewer` | 0 | Read-only access to dashboards |
| `analyst` | 1 | Data entry, analysis, limited modifications |
| `manager` | 2 | Team management, deal approval, report generation |
| `admin` | 3 | Full system access, user management |

Convenience dependencies: `require_analyst`, `require_manager`, `require_admin`, `require_viewer`

`CurrentUser` class: carries `id`, `email`, `role`, `full_name`, `is_active`. Methods: `has_role(required_role)`, `can_modify_data()`, `can_approve_deals()`, `is_admin()`.

### Input Sanitization

**File:** `backend/app/core/sanitization.py`

Functions: `strip_html_tags(value)`, `sanitize_string(value)`, `sanitize_string_list(values)`, `make_sanitized_validator(*field_names)` — factory that generates Pydantic `model_validator(mode="before")` callables.

Strips HTML tags, dangerous URI schemes (`javascript:`, `vbscript:`, `data:`), event handler attributes (`onerror=`, `onclick=`), decodes HTML entities, and re-sanitizes.

### File Upload Validation

**File:** `backend/app/core/file_validation.py`

`validate_upload(filename, content_type, file_content)` returns `ValidationResult(valid, error)`.

Checks (in order): filename required, extension allowlist (`.xlsx`, `.xlsm`, `.xls`, `.pdf`, `.csv`, `.docx`), file non-empty, size limits (Excel 50 MB, PDF 25 MB, CSV 10 MB, DOCX 25 MB), MIME type match, magic bytes (`PK\x03\x04` for xlsx/xlsm/docx, `\xd0\xcf\x11\xe0` for xls, `%PDF` for pdf).

---

## 3. API Endpoints

All routes prefixed with `/api/v1`. Auth guard column uses the `require_*` dependency shorthand.

### Root

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | None | API info (name, version, status, docs URL) |
| GET | `/api/v1/health` | None | Legacy health check (load balancer probe) |

### Health (`/api/v1/health/status`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/health/status` | None | Detailed health: database ping, Redis ping, SharePoint config, external API keys, disk space, uptime |

### Authentication (`/api/v1/auth`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/login` | None | OAuth2 form login; returns `Token` (access + refresh). Rate limited: 5 req/60s |
| POST | `/api/v1/auth/refresh` | None | Refresh token rotation; blacklists old token; detects replay. Rate limited: 10 req/60s |
| POST | `/api/v1/auth/logout` | Bearer (optional) | Blacklists the presented access token JTI |
| GET | `/api/v1/auth/me` | Bearer | Returns current user profile |

### Properties (`/api/v1/properties`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/properties/dashboard` | analyst | Frontend-format property list with batch financial enrichment from `extracted_values`; cached (`LONG_TTL`) |
| GET | `/api/v1/properties/dashboard/{id}` | analyst | Single property in frontend format; lazy enrichment if `financial_data` missing |
| GET | `/api/v1/properties/summary` | analyst | Portfolio summary stats (totals, averages, IRR, CoC); cached (`LONG_TTL`) |
| GET | `/api/v1/properties/` | analyst | Paginated list; filters: `property_type`, `city`, `state`, `market`, `min_units`, `max_units`, `sort_by`, `sort_order` |
| GET | `/api/v1/properties/cursor` | analyst | Cursor-paginated list (same filters) |
| GET | `/api/v1/properties/{id}` | analyst | Single property (`PropertyResponse`) |
| POST | `/api/v1/properties/` | manager | Create property; invalidates property cache |
| PUT | `/api/v1/properties/{id}` | manager | Full update; invalidates property cache |
| DELETE | `/api/v1/properties/{id}` | manager | Soft-delete; invalidates property cache |
| GET | `/api/v1/properties/{id}/analytics` | analyst | Property analytics: metrics, rent/occupancy trends, market comparables |
| GET | `/api/v1/properties/{id}/activities` | analyst | Paginated property activity log; filter by `activity_type` |
| POST | `/api/v1/properties/{id}/activities` | authenticated | Log a property activity |

### Deals (`/api/v1/deals`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/deals/` | analyst | Paginated/filtered deal list |
| GET | `/api/v1/deals/cursor` | analyst | Cursor-paginated deal list |
| GET | `/api/v1/deals/kanban` | analyst | Kanban board data grouped by stage |
| GET | `/api/v1/deals/recent-activity` | analyst | Recent activity feed across all deals |
| GET | `/api/v1/deals/{id}` | analyst | Single deal (`DealResponse`) |
| POST | `/api/v1/deals/` | analyst | Create deal |
| PUT | `/api/v1/deals/{id}` | analyst | Full update with input sanitization |
| PATCH | `/api/v1/deals/{id}/stage` | analyst | Update deal stage (Kanban drag-and-drop) |
| PATCH | `/api/v1/deals/{id}/optimistic` | analyst | Optimistic-locking update; returns 409 on version conflict |
| DELETE | `/api/v1/deals/{id}` | manager | Soft-delete |
| GET | `/api/v1/deals/{id}/activities` | analyst | Paginated deal activity log |
| POST | `/api/v1/deals/{id}/activities` | authenticated | Log a deal activity |
| GET | `/api/v1/deals/{id}/watchlist` | authenticated | Check watchlist status |
| POST | `/api/v1/deals/{id}/watchlist` | authenticated | Toggle watchlist membership |
| GET | `/api/v1/deals/{id}/activity-log` | analyst | Structured activity log entries |
| GET | `/api/v1/deals/{id}/proforma-returns` | analyst | Extracted proforma return metrics from `extracted_values` |
| GET | `/api/v1/deals/compare?ids=1,2,3` | analyst | Compare 2-10 deals side-by-side (`DealComparisonResponse`) |

### Analytics (`/api/v1/analytics`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/analytics/dashboard` | analyst | Dashboard analytics summary |
| GET | `/api/v1/analytics/deals` | analyst | Deal pipeline analytics |
| GET | `/api/v1/analytics/properties` | analyst | Property portfolio analytics |
| GET | `/api/v1/analytics/market` | analyst | Market data analytics |

### Users (`/api/v1/users`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/users/` | admin | List users |
| GET | `/api/v1/users/{id}` | admin | Get user by ID |
| POST | `/api/v1/users/` | admin | Create user |
| PUT | `/api/v1/users/{id}` | admin | Update user |
| DELETE | `/api/v1/users/{id}` | admin | Soft-delete user |

### Exports (`/api/v1/exports`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/exports/properties` | analyst | Export properties (CSV/Excel) |
| GET | `/api/v1/exports/deals` | analyst | Export deals (CSV/Excel) |
| GET | `/api/v1/exports/transactions` | analyst | Export transactions (CSV/Excel) |

### Monitoring (`/api/v1/monitoring`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/monitoring/metrics` | admin | Prometheus metrics (text/plain) |
| GET | `/api/v1/monitoring/system` | admin | System metrics (CPU, memory, disk) |
| GET | `/api/v1/monitoring/database` | admin | Database connection pool stats |
| GET | `/api/v1/monitoring/application` | admin | Application business metrics |
| GET | `/api/v1/monitoring/connection-pools` | admin | Unified DB + Redis pool stats |

### Extraction (`/api/v1/extraction`)

Sub-routes split across `extract.py`, `status.py`, `filters.py`, `grouping.py`, `monitor.py`, `scheduler.py`:

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/extraction/run` | manager | Trigger extraction run (SharePoint or local) |
| POST | `/api/v1/extraction/run/local` | manager | Trigger local file extraction |
| GET | `/api/v1/extraction/runs` | analyst | List extraction runs |
| GET | `/api/v1/extraction/runs/{run_id}` | analyst | Get extraction run details |
| GET | `/api/v1/extraction/runs/{run_id}/values` | analyst | List extracted values for a run |
| GET | `/api/v1/extraction/values` | analyst | Query extracted values by property/field |
| GET | `/api/v1/extraction/filter/candidates` | manager | List candidate files from configured path |
| GET | `/api/v1/extraction/grouping/groups` | analyst | List file groups |
| POST | `/api/v1/extraction/grouping/run` | manager | Run grouping pipeline phase |
| GET | `/api/v1/extraction/monitor/status` | analyst | File monitor status |
| POST | `/api/v1/extraction/monitor/toggle` | manager | Enable/disable file monitor |
| GET | `/api/v1/extraction/scheduler/status` | analyst | Extraction scheduler status |
| POST | `/api/v1/extraction/scheduler/toggle` | manager | Enable/disable scheduled extraction |

### Interest Rates (`/api/v1/interest-rates`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/interest-rates/current` | analyst | Current rates (SOFR, 10Y Treasury, etc.) |
| GET | `/api/v1/interest-rates/history` | analyst | Historical rate series |

### Transactions (`/api/v1/transactions`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/transactions/` | analyst | List transactions |
| GET | `/api/v1/transactions/{id}` | analyst | Get transaction |
| POST | `/api/v1/transactions/` | analyst | Create transaction |
| PUT | `/api/v1/transactions/{id}` | analyst | Update transaction |
| DELETE | `/api/v1/transactions/{id}` | manager | Soft-delete transaction |

### Documents (`/api/v1/documents`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/documents/` | analyst | List documents |
| GET | `/api/v1/documents/{id}` | analyst | Get document |
| POST | `/api/v1/documents/` | analyst | Upload document (with file validation) |
| DELETE | `/api/v1/documents/{id}` | manager | Delete document |

### Market Data (`/api/v1/market`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/market/submarkets` | analyst | List CoStar submarkets |
| GET | `/api/v1/market/submarket/{name}` | analyst | Submarket data |
| GET | `/api/v1/market/interest-rates` | analyst | Market interest rates |

### Reporting (`/api/v1/reporting`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/reporting/settings` | analyst | Report settings |
| PUT | `/api/v1/reporting/settings` | manager | Update report settings |
| GET | `/api/v1/reporting/templates` | analyst | List report templates |
| POST | `/api/v1/reporting/generate` | analyst | Generate report |

### Admin (`/api/v1/admin`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/admin/audit-log` | admin | Audit log entries |
| GET | `/api/v1/admin/users` | admin | User management view |

### Sales Analysis (`/api/v1/sales-analysis`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/sales-analysis/` | analyst | Sales comp data |
| GET | `/api/v1/sales-analysis/summary` | analyst | Sales analysis summary stats |

### Construction Pipeline (`/api/v1/construction-pipeline`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/construction-pipeline/` | analyst | Construction pipeline records |
| GET | `/api/v1/construction-pipeline/summary` | analyst | Pipeline summary |
| POST | `/api/v1/construction-pipeline/import` | manager | Import pipeline data |

### WebSocket (`/api/v1/ws`)

| Type | Path | Auth | Description |
|------|------|------|-------------|
| WS | `/api/v1/ws/{channel}` | Bearer (token query param) | Real-time channel subscription. Channels: `deals`, `extraction`, `notifications`, `properties`, `analytics` |

---

## 4. CRUD Layer

### Base Classes

**File:** `backend/app/crud/base.py`

#### `PaginatedResult[ModelType]`

Container for offset-paginated results. Slots: `items`, `total`, `page`, `per_page`, `pages`, `has_next`, `has_prev`. Method: `to_dict()`.

#### `CursorPaginatedResult[ModelType]`

Container for cursor-paginated results. Slots: `items`, `next_cursor`, `prev_cursor`, `has_more`, `total`. Method: `to_dict()`.

#### `CRUDBase[ModelType, CreateSchemaType, UpdateSchemaType]`

Generic base with automatic soft-delete awareness.

| Method | Signature | Description |
|--------|-----------|-------------|
| `get` | `(db, id, *, include_deleted=False)` | Fetch by PK, excludes soft-deleted |
| `get_multi` | `(db, *, skip, limit, order_by, order_desc, include_deleted)` | Paginated list |
| `create` | `(db, *, obj_in)` | Insert; accepts schema or dict |
| `update` | `(db, *, db_obj, obj_in)` | Update; accepts schema or dict |
| `remove` | `(db, *, id)` | Soft-delete if model has `SoftDeleteMixin`, else hard delete |
| `restore` | `(db, *, id)` | Restore soft-deleted record |
| `count` | `(db, *, filters, include_deleted)` | Count with field equality filters |
| `_apply_ordering` | `(query, order_by, order_desc)` | Safe column ordering helper |
| `count_where` | `(db, *, conditions, include_deleted)` | Count with arbitrary SA expressions |
| `get_multi_ordered` | `(db, *, skip, limit, order_by, order_desc, conditions, include_deleted)` | Fetch with arbitrary filter conditions |
| `get_paginated` | `(db, *, page, per_page, order_by, order_desc, conditions, include_deleted)` | Returns `PaginatedResult` |
| `get_cursor_paginated` | `(db, *, params, order_by, order_desc, conditions, include_deleted, include_total)` | Keyset cursor pagination; returns `CursorPaginatedResult` |
| `_coerce_sort_value` | `(raw, col)` | Type-coerces cursor sort values after JSON round-trip |

### CRUD Singletons

| Singleton | File | Model | Extra Methods |
|-----------|------|-------|---------------|
| `crud.deal` | `crud_deal.py` | `Deal` | `get_with_relations`, `get_by_stage`, `get_multi_filtered`, `count_filtered`, `get_kanban_data`, `get_by_ids`, `update_optimistic`, `update_stage` |
| `crud.property` | `crud_property.py` | `Property` | `get_multi_filtered`, `count_filtered`, `enrich_financial_data`, `enrich_financial_data_batch`, `get_cursor_paginated`, `_build_property_conditions` |
| `crud.transaction` | `crud_transaction.py` | `Transaction` | `get_by_property`, `get_multi_filtered`, `count_filtered` |
| `crud.document` | `crud_document.py` | `Document` | `get_by_deal`, `get_by_property` |
| `crud.user` | `crud_user.py` | `User` | `get_by_email`, `authenticate`, `update_last_login`, `create_with_password` |
| `crud.report_template` | `crud_report_template.py` | `ReportTemplate` | Standard CRUD |
| `deal_activity` | `crud_activity.py` | `DealActivity` | `get_by_deal`, `count_by_deal` |
| `property_activity` | `crud_activity.py` | `PropertyActivity` | `get_by_property`, `count_by_property` |
| `watchlist_crud` | `crud_activity.py` | `Watchlist` | `get_by_user_and_deal`, `toggle`, `get_user_watchlist` |
| `activity_log` | `crud_activity_log.py` | `ActivityLog` | `get_by_entity`, `create_log_entry` |
| `crud.extraction` | `extraction.py` | `ExtractionRun`, `ExtractedValue` | Run management, value queries, property sync |
| `crud.file_monitor` | `file_monitor.py` | `MonitoredFile` | File change tracking |

### Key Design Notes

- **Optimistic locking** (`update_optimistic`): uses `UPDATE ... WHERE id=X AND version=Y` — returns `None` if version is stale (0 rows affected)
- **Batch enrichment** (`enrich_financial_data_batch`): executes 2 queries total for N properties instead of 2-3 per property (N+1 fix)
- **Cursor encoding**: `encode_cursor(sort_val, id)` / `decode_cursor(cursor)` in `schemas/pagination.py`; JSON-serialized + base64url

---

## 5. SQLAlchemy Models

All models use SQLAlchemy 2.0 `Mapped`/`mapped_column` style. Models are registered in `backend/app/db/base.py` (Alembic) and `backend/app/models/__init__.py` (runtime).

### Mixins

**File:** `backend/app/models/base.py`

| Mixin | Columns | Notes |
|-------|---------|-------|
| `TimestampMixin` | `created_at: DateTime(tz) NOT NULL`, `updated_at: DateTime(tz) NOT NULL` | Both have `lambda: datetime.now(UTC)` defaults; `created_at` is indexed |
| `SoftDeleteMixin` | `is_deleted: Boolean NOT NULL DEFAULT false` (indexed), `deleted_at: DateTime(tz)` | Methods: `soft_delete()`, `restore()` |

### Core Models

#### `User` — table `users`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer PK | indexed |
| `email` | String(255) | UNIQUE, indexed, NOT NULL |
| `hashed_password` | String(255) | NOT NULL |
| `full_name` | String(255) | NOT NULL |
| `role` | String(50) | NOT NULL, default `viewer` |
| `is_active` | Boolean | NOT NULL, default True |
| `is_verified` | Boolean | NOT NULL, default False |
| `avatar_url` | String(500) | nullable |
| `department` | String(100) | nullable |
| `phone` | String(20) | nullable |
| `last_login` | DateTime(tz) | nullable |
| `refresh_token` | Text | nullable |
| `email_notifications` | Boolean | default True |
| `report_subscriptions` | Text | nullable (JSON string) |

Mixins: `TimestampMixin`, `SoftDeleteMixin`

#### `Property` — table `properties`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer PK | indexed |
| `name` | String(255) | NOT NULL, indexed |
| `property_type` | String(50) | NOT NULL, indexed |
| `address` | String(500) | NOT NULL |
| `city` | String(100) | NOT NULL, indexed |
| `state` | String(50) | NOT NULL, indexed |
| `zip_code` | String(20) | NOT NULL |
| `county` | String(100) | nullable |
| `market` | String(100) | nullable, indexed |
| `submarket` | String(100) | nullable |
| `latitude` | Numeric(10,6) | nullable |
| `longitude` | Numeric(10,6) | nullable |
| `building_type` | String(50) | nullable |
| `year_built` | Integer | nullable |
| `year_renovated` | Integer | nullable |
| `total_units` | Integer | nullable |
| `total_sf` | Integer | nullable |
| `lot_size_acres` | Numeric(10,2) | nullable |
| `stories` | Integer | nullable |
| `parking_spaces` | Integer | nullable |
| `purchase_price` | Numeric(15,2) | nullable |
| `current_value` | Numeric(15,2) | nullable |
| `acquisition_date` | Date | nullable |
| `occupancy_rate` | Numeric(5,2) | nullable |
| `avg_rent_per_unit` | Numeric(10,2) | nullable |
| `avg_rent_per_sf` | Numeric(8,2) | nullable |
| `noi` | Numeric(15,2) | nullable |
| `cap_rate` | Numeric(5,3) | nullable |
| `financial_data` | JSON | nullable (nested frontend blob) |
| `description` | Text | nullable |
| `amenities` | JSON | nullable |
| `unit_mix` | JSON | nullable |
| `images` | JSON | nullable |
| `external_id` | String(100) | nullable, UNIQUE |
| `data_source` | String(50) | nullable |

CHECK constraints (13): `purchase_price >= 0`, `current_value >= 0`, `total_units > 0`, `total_sf > 0`, `stories > 0`, `year_built BETWEEN 1800 AND 2100`, `year_renovated BETWEEN 1800 AND 2100`, `cap_rate BETWEEN 0 AND 100`, `occupancy_rate BETWEEN 0 AND 100`, `avg_rent_per_unit >= 0`, `avg_rent_per_sf >= 0`, `parking_spaces >= 0`

Computed properties: `price_per_unit`, `price_per_sf`

Mixins: `TimestampMixin`, `SoftDeleteMixin`

#### `Deal` — table `deals`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer PK | indexed |
| `version` | Integer | NOT NULL, default 1 (optimistic locking) |
| `name` | String(255) | NOT NULL, indexed |
| `deal_type` | String(50) | NOT NULL, indexed |
| `stage` | Enum(DealStage) | NOT NULL, indexed, default `initial_review` |
| `stage_order` | Integer | NOT NULL, default 0 |
| `property_id` | Integer FK(properties.id) | nullable, indexed |
| `assigned_user_id` | Integer FK(users.id) | nullable, indexed |
| `asking_price` | Numeric(15,2) | nullable |
| `offer_price` | Numeric(15,2) | nullable |
| `final_price` | Numeric(15,2) | nullable |
| `projected_irr` | Numeric(6,3) | nullable |
| `projected_coc` | Numeric(6,3) | nullable |
| `projected_equity_multiple` | Numeric(5,2) | nullable |
| `hold_period_years` | Integer | nullable |
| `initial_contact_date` | Date | nullable |
| `loi_submitted_date` | Date | nullable |
| `due_diligence_start` | Date | nullable |
| `due_diligence_end` | Date | nullable |
| `target_close_date` | Date | nullable |
| `actual_close_date` | Date | nullable |
| `source` | String(100) | nullable |
| `broker_name` | String(255) | nullable |
| `broker_company` | String(255) | nullable |
| `competition_level` | String(50) | nullable |
| `notes` | Text | nullable |
| `investment_thesis` | Text | nullable |
| `key_risks` | Text | nullable |
| `documents` | JSON | nullable |
| `activity_log` | JSON | nullable |
| `tags` | JSON | nullable |
| `custom_fields` | JSON | nullable |
| `deal_score` | Integer | nullable |
| `priority` | String(20) | NOT NULL, indexed, default `medium` |
| `stage_updated_at` | DateTime(tz) | nullable |

Enum `DealStage` (StrEnum): `dead`, `initial_review`, `active_review`, `under_contract`, `closed`, `realized`

CHECK constraints (8): `asking_price >= 0`, `offer_price >= 0`, `final_price >= 0`, `projected_irr BETWEEN -100 AND 999`, `projected_coc >= -100`, `projected_equity_multiple >= 0`, `hold_period_years > 0`, `deal_score BETWEEN 0 AND 100`

Composite index: `ix_deals_stage_stage_order` (`stage`, `stage_order`)

Methods: `update_stage(new_stage)`, `add_activity(activity)`

Mixins: `TimestampMixin`, `SoftDeleteMixin`

#### `Transaction` — table `transactions`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer PK | indexed |
| `property_id` | Integer FK(properties.id) | nullable, indexed |
| `property_name` | String(255) | NOT NULL, indexed |
| `type` | String(50) | NOT NULL, indexed |
| `category` | String(100) | nullable, indexed |
| `amount` | Numeric(15,2) | NOT NULL |
| `date` | Date | NOT NULL, indexed |
| `description` | Text | nullable |
| `documents` | JSON | nullable |

Enum `TransactionType` (StrEnum): `acquisition`, `disposition`, `capital_improvement`, `refinance`, `distribution`

CHECK constraint (1): `amount >= 0`

Mixins: `TimestampMixin`, `SoftDeleteMixin`

#### `ExtractionRun` — table `extraction_runs`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID PK | indexed |
| `started_at` | DateTime(tz) | NOT NULL |
| `completed_at` | DateTime(tz) | nullable |
| `status` | String(50) | NOT NULL, indexed, default `running` |
| `trigger_type` | String(50) | NOT NULL, default `manual` |
| `files_discovered` | Integer | NOT NULL, default 0 |
| `files_processed` | Integer | NOT NULL, default 0 |
| `files_failed` | Integer | NOT NULL, default 0 |
| `error_summary` | JSON | nullable |
| `per_file_status` | JSON | nullable |
| `file_metadata` | JSON | nullable |

Relationship: `extracted_values` (cascade delete-orphan)

Computed properties: `duration_seconds`, `success_rate`

Mixins: `TimestampMixin`

#### `ExtractedValue` — table `extracted_values`

EAV (Entity-Attribute-Value) pattern for extracted Excel fields.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID PK | indexed |
| `extraction_run_id` | UUID FK(extraction_runs.id) | NOT NULL, indexed, CASCADE delete |
| `property_id` | Integer FK(properties.id) | nullable, indexed, SET NULL |
| `property_name` | String(255) | NOT NULL, indexed |
| `field_name` | String(255) | NOT NULL, indexed |
| `field_category` | String(100) | nullable |
| `sheet_name` | String(100) | nullable |
| `cell_address` | String(20) | nullable |
| `value_text` | Text | nullable |
| `value_numeric` | Numeric(20,4) | nullable |
| `value_date` | Date | nullable |
| `is_error` | Boolean | NOT NULL, default False |
| `error_category` | String(50) | nullable |
| `source_file` | String(500) | nullable |

Unique constraint: `uq_extracted_value` (`extraction_run_id`, `property_name`, `field_name`)
Index: `idx_extracted_values_lookup` (`property_name`, `field_name`)

Computed property: `value` — returns `value_numeric` then `value_date` then `value_text`

Mixins: `TimestampMixin`

### Underwriting Models

Located in `backend/app/models/underwriting/`. All inherit from `Base` + `TimestampMixin`.

| Model | Table | Purpose |
|-------|-------|---------|
| `UnderwritingModel` | `underwriting_models` | Top-level UW model record |
| `AnnualCashflow` | `annual_cashflows` | Year-by-year NOI/cash flow projections |
| `BudgetAssumptions` | `budget_assumptions` | CapEx and renovation budget inputs |
| `EquityReturns` | `equity_returns` | LP/GP IRR, MOIC, distributions |
| `ExitAssumptions` | `exit_assumptions` | Exit cap rate, hold period, reversion |
| `FinancingAssumptions` | `financing_assumptions` | LTV, rate, amortization, IO period |
| `GeneralAssumptions` | `general_assumptions` | Property details, acquisition cost |
| `NOIAssumptions` | `noi_assumptions` | Revenue, expenses, vacancy inputs |
| `PropertyReturns` | `property_returns` | Unlevered returns |
| `RentComp` | `rent_comps` | Comparable rent data |
| `SalesComp` | `sales_comps` | Comparable sales data |
| `SourceTracking` | `source_tracking` | Data provenance metadata |
| `UnitMix` | `unit_mixes` | Unit type breakdown |

### Other Models

| Model | Table | Key Columns | Mixins |
|-------|-------|-------------|--------|
| `Document` | `documents` | `id`, `name`, `url`, `deal_id`, `property_id`, `file_type`, `file_size` | TimestampMixin |
| `AuditLog` | `audit_logs` | `id`, `user_id`, `entity_type`, `entity_id`, `action`, `changes_json`, `ip_address` | TimestampMixin |
| `ActivityLog` | `activity_logs` | `id`, `user_id`, `entity_type`, `entity_id`, `action`, `metadata` | TimestampMixin |
| `DealActivity` | `deal_activities` | `id`, `deal_id`, `user_id`, `activity_type`, `description`, `field_changed`, `old_value`, `new_value`, `comment_text`, `document_name/url`, `ip_address`, `user_agent` | TimestampMixin |
| `PropertyActivity` | `property_activities` | same structure but `property_id` | TimestampMixin |
| `Watchlist` | `watchlist` | `id`, `user_id`, `deal_id` | TimestampMixin; UNIQUE(user_id, deal_id) |
| `ReportSettings` | `report_settings` | `id`, `user_id`, various display settings | TimestampMixin |
| `ReportTemplate` | `report_templates` | `id`, `name`, `description`, `template_type`, `config` | TimestampMixin |
| `SalesData` | `sales_data` | `id`, `address`, `city`, `state`, `sale_price`, `sale_date`, `cap_rate`, `units`, CoStar fields | TimestampMixin |
| `MonitoredFile` | `monitored_files` | `id`, `file_path`, `last_modified`, `file_hash`, `last_checked`, `status` | TimestampMixin |
| `ReminderDismissal` | `reminder_dismissals` | `id`, `user_id`, `reminder_key`, `dismissed_at` | TimestampMixin |
| `ConstructionProject` | `construction_projects` | `id`, `name`, `address`, `city`, `units`, `status`, `permit_date`, `completion_date`, `source` | TimestampMixin |

---

## 6. Pydantic Schemas

All schemas extend Pydantic `BaseModel`. Numeric fields use `Decimal` or `float` with `nullable().optional()` + `?? undefined` pattern (not `?? 0` to avoid "0.0%" instead of "N/A" display bugs).

### `schemas/deal.py`

| Schema | Purpose | Key Fields |
|--------|---------|-----------|
| `DealBase` | Shared base | `name`, `deal_type`, `stage`, `priority`, all financial/timeline fields |
| `DealCreate` | POST body | extends `DealBase`; sanitized via `make_sanitized_validator` on `name`, `notes`, `investment_thesis`, `key_risks`, `tags` |
| `DealUpdate` | PUT body | all optional; `version` required for optimistic lock route |
| `DealResponse` | GET response | `id`, `version`, all `DealBase` fields, `created_at`, `updated_at`, `is_deleted` |
| `DealStageUpdate` | PATCH stage body | `stage: DealStage`, `stage_order: int | None` |
| `DealListResponse` | paginated list | `items: list[DealResponse]`, `total`, `page`, `page_size` |
| `DealCursorPaginatedResponse` | cursor list | `items`, `next_cursor`, `prev_cursor`, `has_more`, `total` |
| `KanbanBoardResponse` | kanban | `stages: dict[str, list[DealResponse]]`, `total_deals`, `stage_counts` |
| `RecentActivityItem` | activity feed | `deal_id`, `deal_name`, `activity_type`, `description`, `created_at` |

### `schemas/property.py`

| Schema | Purpose | Key Fields |
|--------|---------|-----------|
| `PropertyBase` | Shared base | All `Property` model fields |
| `PropertyCreate` | POST body | extends `PropertyBase` |
| `PropertyUpdate` | PUT body | all optional |
| `PropertyResponse` | GET response | all fields + timestamps |
| `PropertyListResponse` | paginated list | `items`, `total`, `page`, `page_size` |
| `PropertyCursorPaginatedResponse` | cursor list | `items`, `next_cursor`, `prev_cursor`, `has_more`, `total` |

### `schemas/auth.py`

| Schema | Purpose | Key Fields |
|--------|---------|-----------|
| `Token` | Login/refresh response | `access_token: str`, `refresh_token: str`, `token_type: str`, `expires_in: int` |
| `RefreshTokenRequest` | Refresh body | `refresh_token: str` |

### `schemas/pagination.py`

| Schema/Function | Purpose |
|----------------|---------|
| `CursorPaginationParams` | `cursor: str | None`, `limit: int`, `direction: "next"/"prev"` |
| `encode_cursor(sort_val, id)` | JSON + base64url encoding |
| `decode_cursor(cursor)` | Decode to `(sort_val, id)` tuple; raises `ValueError` on malformed |

### `schemas/comparison.py`

| Schema | Fields |
|--------|--------|
| `MetricComparison` | `field_name`, `values: list[Any]`, `winner_index: int | None` |
| `ComparisonSummary` | `strongest_deal_index`, `key_differentiators: list[str]` |
| `DealComparisonResponse` | `deals: list[DealResponse]`, `metrics: list[MetricComparison]`, `summary: ComparisonSummary` |

### Other Schemas

| File | Key Schemas |
|------|-------------|
| `schemas/activity.py` | `DealActivityCreate`, `DealActivityResponse`, `DealActivityListResponse`, `PropertyActivityCreate`, `PropertyActivityResponse`, `WatchlistToggleResponse` |
| `schemas/activity_log.py` | `ActivityLogCreate`, `ActivityLogResponse`, `ActivityLogListResponse`, `ActivityAction` (StrEnum) |
| `schemas/extraction.py` | `ExtractionRunResponse`, `ExtractedValueResponse`, `ExtractionTriggerRequest` |
| `schemas/grouping.py` | `GroupInfo`, `GroupPipelineStatus`, `GroupExtractionRequest` |
| `schemas/transaction.py` | `TransactionCreate`, `TransactionUpdate`, `TransactionResponse`, `TransactionListResponse` |
| `schemas/document.py` | `DocumentCreate`, `DocumentResponse` |
| `schemas/user.py` | `UserCreate`, `UserUpdate`, `UserResponse` |
| `schemas/reporting.py` | `ReportSettingsUpdate`, `ReportSettingsResponse`, `ReportTemplateResponse` |
| `schemas/market_data.py` | `SubmarketResponse`, `MarketSummary` |
| `schemas/interest_rates.py` | `InterestRateResponse`, `RateHistory` |
| `schemas/file_monitor.py` | `MonitoredFileResponse`, `MonitorStatusResponse` |
| `schemas/base.py` | Common base schema utilities |

---

## 7. Extraction Pipeline

**Directory:** `backend/app/extraction/`

### Module Overview

| Module | Purpose | Inputs | Outputs |
|--------|---------|--------|---------|
| `file_filter.py` | Pre-filter candidate Excel files | Directory path, config patterns (`FILE_PATTERN`, `EXCLUDE_PATTERNS`, `FILE_EXTENSIONS`, `CUTOFF_DATE`, `MAX_FILE_SIZE_MB`) | List of `Path` objects |
| `fingerprint.py` | Structural fingerprinting | `Path` to xlsx/xlsb/xlsm | `FileFingerprint` (per-sheet `SheetFingerprint`: name, rows, cols, header labels, col-A labels, cell count, SHA hash) |
| `grouping.py` | Cluster files into structural groups | List of `FileFingerprint` | Groups (identity threshold 0.95, variant threshold 0.80, empty template threshold 20 cells) |
| `cell_mapping.py` | Cell address to field name mappings | Template-specific config | `CellMapping` dataclasses per field |
| `reference_mapper.py` | Auto-map fields to canonical vocabulary | File group, field names | `ReferenceMap` associating cell addresses to canonical field names |
| `extractor.py` | Extract cell values from Excel | `Path`, `dict[str, CellMapping]`, optional `FileFilter` | Dict of `field_name -> value`; `np.nan` for errors |
| `group_pipeline.py` | 4-phase orchestrator | `data_dir`, SQLAlchemy `Session` | Phases: Discovery, Fingerprinting, Reference Mapping, Extraction |
| `output_validation.py` | Post-extraction value validation | `dict[str, Any]` extracted values | `ValidationSummary` with per-field `ValidationResult` |
| `validation.py` | Schema-level input validation | Raw extraction parameters | Validates before running |
| `error_handler.py` | Structured error collection | Exceptions during cell reads | `ErrorHandler` with categorized errors |
| `sharepoint.py` | Azure AD + SharePoint integration | Azure credentials, site URL | File listings, file content bytes |

### Extraction Output Validation Rules (9 rules)

Calibrated for Phoenix MSA Class B multifamily:

| Rule | Field Patterns | Hard Bounds | Warning Bounds |
|------|---------------|-------------|----------------|
| `cap_rate` | cap_rate, caprate, cap_rt | 0-20% | 2-15% |
| `purchase_price` | purchase_price, acquisition_price, sale_price | $100K-$500M | $1M-$200M |
| `unit_count` | unit_count, total_units, num_units, number_of_units | 1-5000 | 10-2000 |
| `year_built` | year_built, yr_built, vintage | 1900-2026 | 1950-2026 |
| `noi` | noi, net_operating_income | -$10M-$100M | $0-$50M |
| `rent_per_unit` | rent_per_unit, avg_rent, average_rent, rent_unit, monthly_rent | $0-$10K/mo | $400-$5K/mo |
| `price_per_unit` | price_per_unit, cost_per_unit, ppu | $10K-$1M | $30K-$500K |
| `occupancy` | occupancy, occ_rate, physical_occupancy, economic_occ | 0-100% | 50-100% |
| `square_footage` | square_footage, sqft, sq_ft, total_sf, rentable_sf, gross_sf | 100-10M sf | 5K-5M sf |

### Group Pipeline Phases

`GroupExtractionPipeline` (`group_pipeline.py`) orchestrates:

1. **Discovery**: scans `LOCAL_DEALS_ROOT`, applies `FileFilter`, deduplicates
2. **Fingerprinting**: `ThreadPoolExecutor` (`GROUP_FINGERPRINT_WORKERS` threads) builds `FileFingerprint` per candidate
3. **Reference Mapping**: auto-maps discovered fields to canonical field names
4. **Extraction**: batch-extracts using `ExcelDataExtractor`, writes `ExtractedValue` rows; updates `ExtractionRun` progress

State persisted in `GROUP_EXTRACTION_DATA_DIR/config.json` (`PipelineConfig` dataclass) for phase-level resume.

### Extraction Schedulers

| Scheduler | File | Trigger | Settings |
|-----------|------|---------|---------|
| `ExtractionScheduler` | `services/extraction/scheduler.py` | APScheduler cron | `EXTRACTION_SCHEDULE_ENABLED`, `EXTRACTION_SCHEDULE_CRON` (default `0 17 * * *`), `EXTRACTION_SCHEDULE_TIMEZONE` |
| `MonitorScheduler` | `services/extraction/monitor_scheduler.py` | APScheduler interval | `FILE_MONITOR_ENABLED`, `FILE_MONITOR_INTERVAL_MINUTES`, `AUTO_EXTRACT_ON_CHANGE` |

---

## 8. Services

### `CacheService`

**File:** `backend/app/core/cache.py`

Async Redis cache with lazy connection and in-memory fallback. Global singleton: `cache`.

| Method | Description |
|--------|-------------|
| `get(key)` | Fetch; returns deserialized object or `None` |
| `set(key, value, ttl)` | Store with TTL (default `REDIS_CACHE_TTL` = 1 hour) |
| `delete(key)` | Delete single entry |
| `invalidate_pattern(pattern)` | SCAN + delete by glob pattern |
| `invalidate_properties()` | Bulk-invalidates `property_*`, `portfolio_summary*`, `analytics_dashboard*` |
| `invalidate_deals()` | Bulk-invalidates `deal_*`, `analytics_dashboard*` |
| `get_stats()` | Returns backend type and entry count |
| `cleanup_memory()` | Removes expired in-memory entries |

TTL constants: `SHORT_TTL = 300s`, `LONG_TTL = 7200s`, `DEFAULT_TTL = 3600s`

Key scheme: `dashboard:{key}` prefix for all entries.

Fallback: module-level `_memory_cache: dict[str, tuple[str, float]]`.

Helper functions: `make_cache_key(*parts)`, `make_cache_key_from_params(prefix, **params)` (MD5 hash of sorted params for deterministic short keys).

### `ConnectionManager` (WebSocket Pool)

**File:** `backend/app/services/websocket_manager.py`

Channel-based WebSocket connection manager. Channels: `deals`, `extraction`, `notifications`, `properties`, `analytics`.

| Method | Description |
|--------|-------------|
| `connect(websocket, user_id, channel)` | Register connection; enforce per-client limit (default 5) |
| `disconnect(connection_id)` | Remove from all channels |
| `broadcast(channel, message)` | Send to all channel subscribers |
| `send_to_user(user_id, message)` | Send to all connections for a user |
| `send_to_connection(connection_id, message)` | Direct unicast |

### `ConnectionPoolCollector`

**File:** `backend/app/services/monitoring/collectors.py`

Collects async + sync SQLAlchemy pool stats (`size`, `checked_out`, `overflow`, `checked_in`) and Redis pool stats. Updates Prometheus gauges `DB_CONNECTION_POOL_*` and `REDIS_CONNECTION_POOL_*`. Cache duration: 3 seconds.

Also contains: `SystemMetricsCollector` (CPU, memory, disk via psutil), `DatabaseMetricsCollector`, `ApplicationMetricsCollector` (user/deal/property counts via DB queries, 30-second cache).

`CollectorRegistry` singleton (`get_collector_registry()`) aggregates all four collectors via `collect_all()`.

### `MetricsManager` + Prometheus Metrics

**File:** `backend/app/services/monitoring/metrics.py`

Global singleton: `get_metrics_manager()`. Method `initialize()` sets `APP_INFO`. Method `generate_metrics()` returns `generate_latest(REGISTRY)`.

Prometheus metrics defined (full list — 26 metrics):

| Metric | Type | Labels |
|--------|------|--------|
| `http_requests_total` | Counter | method, endpoint, status_code |
| `http_request_duration_seconds` | Histogram | method, endpoint |
| `http_requests_in_progress` | Gauge | method, endpoint |
| `http_request_size_bytes` | Histogram | method, endpoint |
| `http_response_size_bytes` | Histogram | method, endpoint |
| `database_queries_total` | Counter | operation, table |
| `database_query_duration_seconds` | Histogram | operation, table |
| `database_connection_pool_size` | Gauge | pool_type |
| `database_connection_pool_checked_out` | Gauge | pool_type |
| `database_connection_pool_overflow` | Gauge | pool_type |
| `database_connection_pool_checked_in` | Gauge | pool_type |
| `database_slow_query_duration_seconds` | Histogram | statement_type |
| `database_slow_queries_total` | Counter | statement_type |
| `redis_connection_pool_created` | Gauge | pool_name |
| `redis_connection_pool_available` | Gauge | pool_name |
| `redis_connection_pool_in_use` | Gauge | pool_name |
| `cache_hits_total` | Counter | cache_name |
| `cache_misses_total` | Counter | cache_name |
| `cache_operations_total` | Counter | operation, cache_name |
| `cache_operation_duration_seconds` | Histogram | operation, cache_name |
| `websocket_connections_active` | Gauge | channel |
| `websocket_messages_total` | Counter | direction, channel, message_type |
| `active_users` | Gauge | user_type |
| `deals_total` | Gauge | status, stage |
| `properties_total` | Gauge | status |
| `underwriting_models_total` | Gauge | status |
| `ml_predictions_total` | Counter | model_name, prediction_type |
| `ml_prediction_duration_seconds` | Histogram | model_name |
| `app` | Info | name, version, environment |

### Slow Query Logger

**File:** `backend/app/db/query_logger.py`

`attach_query_logger(engine)` attaches SQLAlchemy `before_cursor_execute` / `after_cursor_execute` event listeners. Works on both `AsyncEngine` (via `.sync_engine`) and sync `Engine`.

- Threshold: `SLOW_QUERY_THRESHOLD_MS` (default 500 ms)
- On slow query: increments `database_slow_queries_total`, observes `database_slow_query_duration_seconds`, emits structlog warning with `duration_ms`, `statement_type`, truncated query (1024 chars), first non-SQLAlchemy caller from stack
- Optional: `SLOW_QUERY_LOG_PARAMS=true` logs sanitized parameters (masks password/secret/token/key/authorization/credential keys)
- All queries feed `DB_QUERY_LATENCY` histogram regardless of threshold

### Structured Logging

**File:** `backend/app/core/logging.py`

`setup_logging()` configures both Loguru and structlog:

- **Loguru**: colored console output with `request_id` field injected via `_request_id_patcher`. Production: rotated daily file logs (`logs/app_*.log`, 30-day retention; `logs/error_*.log`, 90-day retention, gz compressed)
- **structlog**: `_add_request_id` processor injects correlation ID from ContextVar. Production: JSON renderer. Development: colorized console renderer

### Other Services

| Service | File | Purpose |
|---------|------|---------|
| `AuditService` | `services/audit_service.py` | Structured audit log writes |
| `ExportService` | `services/export_service.py` | CSV/Excel export generation |
| `EmailService` | `services/email_service.py` | SMTP via Gmail; rate-limited, retries |
| `PDFService` | `services/pdf_service.py` | PDF report generation |
| `RedisService` | `services/redis_service.py` | General-purpose Redis client singleton |
| `GeocodingService` | `services/geocoding.py` | Nominatim geocoding with 1.1s rate limit |
| `MarketDataScheduler` | `services/data_extraction/scheduler.py` | CoStar/FRED/Census scheduled refresh |
| `InterestRateScheduler` | `services/interest_rate_scheduler.py` | Twice-daily FRED rate fetch |
| `InterestRateService` | `services/interest_rates.py` | FRED API + in-memory cache (5 min TTL) |
| `ConstructionImportService` | `services/construction_import.py` | Construction pipeline data import |
| `SalesImportService` | `services/sales_import.py` | Sales comp data import |
| `FileMonitorService` | `services/extraction/file_monitor.py` | Detect changed OneDrive files via SHA-256 hash comparison |
| `ChangeDetector` | `services/extraction/change_detector.py` | SHA-256 hash-based file change detection |
| `ExtractionMetrics` | `services/extraction/metrics.py` | Per-run extraction performance metrics |
| `BatchProcessor` | `services/batch/batch_processor.py` | Configurable batch job processor |
| `JobQueue` | `services/batch/job_queue.py` | Async job queue |
| `RentGrowthPredictor` | `services/ml/rent_growth_predictor.py` | ML rent growth prediction model |
| `ModelManager` | `services/ml/model_manager.py` | ML model lifecycle management |
| `WorkflowEngine` | `services/workflow/workflow_engine.py` | Step-based workflow execution |
| `StepHandlers` | `services/workflow/step_handlers.py` | HTTP, DB, notification step implementations |

### Construction API Integrations

Located in `backend/app/services/construction_api/`. APScheduler cron jobs:

| Module | Source | Cron Schedule |
|--------|--------|--------------|
| `census_bps.py` | Census Building Permits Survey | `0 4 15 * *` (Monthly 15th) |
| `fred_permits.py` | FRED construction permit series | `0 4 15 * *` |
| `bls_employment.py` | BLS employment data | `0 5 15 * *` |
| `mesa_soda.py` | Mesa Open Data (Socrata) | `0 6 16 * *` (Monthly 16th) |
| `tempe_blds.py` | Tempe ArcGIS Feature Layer | `0 6 16 * *` |
| `gilbert_arcgis.py` | Gilbert ArcGIS Feature Layer | `0 6 16 * *` |
| `address_matcher.py` | Address fuzzy-matching utility | On-demand |

---

## 9. Database Layer

**Files:** `backend/app/db/session.py`, `backend/app/db/base.py`, `backend/app/db/query_logger.py`

### Engine Configuration

Two engines created at module load time:

| Engine | Type | Config |
|--------|------|--------|
| `engine` (async) | `create_async_engine` with `asyncpg` driver | SQLite: `StaticPool`, `check_same_thread=False`. PostgreSQL: QueuePool with `pool_size=10`, `max_overflow=20`, `pool_timeout=30`, `pool_pre_ping=True` |
| `sync_engine` | `create_engine` | Same pool parameters |

Both engines have `attach_query_logger(engine)` called at creation.

### Session Factories

| Factory | Type | Usage |
|---------|------|-------|
| `AsyncSessionLocal` | `async_sessionmaker(AsyncSession, expire_on_commit=False)` | API endpoint `get_db()` dependency |
| `SessionLocal` | `sessionmaker(Session, expire_on_commit=False)` | Background tasks via `get_sync_db()` |

### FastAPI Dependencies

| Dependency | Behavior |
|-----------|---------|
| `get_db()` -> `AsyncSession` | Yields session; auto-commit on success; rollback on exception; always closes |
| `get_sync_db()` -> `Session` | Yields session; auto-commit; rollback on exception; always closes |

### Models Registry

**File:** `backend/app/db/base.py` — `Base = DeclarativeBase()`. Alembic `env.py` imports `Base.metadata`.

**File:** `backend/app/models/__init__.py` — all model classes imported to register in `Base.metadata`.

---

## 10. Alembic Migrations

**Directory:** `backend/alembic/versions/`

| Date | Rev ID (prefix) | Description |
|------|----------------|-------------|
| 2025-12-06 | `9fc6647c9407` | Add underwriting models (initial schema: users, properties, deals, underwriting submodels) |
| 2026-01-04 | `896670eb4597` | Add extraction tables (`extraction_runs`, `extracted_values`) |
| 2026-01-06 | `add_monitored_files_tables` | Add `monitored_files` table |
| 2026-01-13 | `5a6a158ce7de` | Add transaction and document models |
| 2026-01-13 | `add_reporting_models` | Add reporting/report template models |
| 2026-02-02 | `8e6fdd43a452` | Add `latitude`, `longitude` columns to properties |
| 2026-02-04 | `align_dealstage_6_stages` | Align DealStage enum to 6-stage model (add `realized`, rename stages) |
| 2026-02-07 | `add_report_settings` | Add report settings table |
| 2026-02-07 | `351e79816af3` | Add sales data table |
| 2026-02-11 | `9b81dcd19444` | Add `per_file_status` JSON column to extraction runs |
| 2026-02-11 | `b1e88c02306b` | Add `file_metadata` JSON column to extraction runs |
| 2026-02-11 | `2f2093cc37a2` | Add construction pipeline tables (current HEAD) |
| 2026-02-11 | `6f4865487bb2` | Widen `fema_flood_zone` column to Text |
| 2026-02-12 | `d7d1ad81d3c0` | Add reminder dismissals table |
| 2026-02-12 | `7c415cc1b77a` | Add activity logs table |

---

## 11. Test Suite

**Directory:** `backend/tests/`

### Test Configuration

- Framework: `pytest` with `pytest-asyncio`
- Database: SQLite in-memory with `StaticPool` and `aiosqlite`
- Critical: no `server_default` — all timestamp defaults use Python-side `default=datetime.now(UTC)`
- Fixtures: `conftest.py` provides `db` (async session), `auth_headers` (analyst JWT), `admin_auth_headers` (admin JWT)
- Auth pattern: GET requests use `auth_headers`, POST/PUT/DELETE use `admin_auth_headers`, unauthenticated requests assert 401

### Test Files by Category

#### API Tests (`tests/test_api/`)

| File | Coverage |
|------|---------|
| `test_auth.py` | Login, refresh rotation, logout, replay detection, JWT validation |
| `test_deals.py` | CRUD, kanban, stage updates, filtering, pagination, comparison |
| `test_deal_optimistic_locking.py` | Version column, concurrent update detection, 409 responses |
| `test_properties.py` | CRUD, dashboard endpoint, enrichment, cursor pagination |
| `test_users.py` | User management, role enforcement |
| `test_analytics.py` | Dashboard analytics, deal pipeline stats |
| `test_exports.py` | CSV/Excel export generation |
| `test_extraction.py` | Extraction run triggers, value queries |
| `test_grouping.py`, `test_grouping_phase4.py` | Group pipeline API |
| `test_health.py` | Health check responses, dependency statuses |
| `test_monitoring.py` | Metrics endpoint, pool stats |
| `test_construction_pipeline.py` | Pipeline CRUD |
| `test_sales_analysis.py` | Sales comp queries |
| `test_reporting_settings.py` | Report settings read/write |
| `test_property_financial_enrichment.py` | Batch enrichment from extracted_values |
| `test_audit_log.py` | Audit log entries |

#### CRUD Tests (`tests/test_crud/`)

| File | Coverage |
|------|---------|
| `test_base_pagination.py` | `PaginatedResult`, `CursorPaginatedResult`, `get_paginated`, cursor encoding/decoding |
| `test_cursor_pagination.py` | Keyset cursor pagination correctness, direction handling, type coercion |
| `test_crud.py` | Base CRUD operations, soft-delete, restore |
| `test_crud_deal.py` | Deal-specific CRUD, optimistic locking, kanban grouping |
| `test_crud_transaction.py` | Transaction CRUD, soft-delete |
| `test_crud_user.py` | User authentication, password hashing |
| `test_extraction.py` | Extraction CRUD operations |

#### Core Tests (`tests/test_core/`)

| File | Coverage |
|------|---------|
| `test_security.py` | JWT creation, decoding, expiry |
| `test_permissions.py` | Role hierarchy, `has_role`, dependency enforcement |
| `test_token_blacklist.py` | Blacklist add/check, memory/Redis fallback, TTL expiry |
| `test_api_key_auth.py` | `hmac.compare_digest` validation, missing/invalid key rejection |
| `test_sanitization.py` | HTML stripping, XSS patterns, event handlers, URI schemes |
| `test_file_validation.py` | Magic bytes, extension, MIME, size limit checks |
| `test_config.py` | Settings loading, `SECRET_KEY` validation, CORS parsing |

#### Middleware Tests (`tests/test_middleware/`)

| File | Coverage |
|------|---------|
| `test_request_id.py` | Header propagation, ContextVar availability, UUID generation |
| `test_error_handler.py` | Exception-to-status-code mapping, `request_id` in responses |
| `test_rate_limiter.py` | Sliding window algorithm, 429 responses, headers, path-specific rules |
| `test_security_headers.py` | CSP, HSTS, X-Frame-Options presence |

#### Model Tests (`tests/test_models/`)

| File | Coverage |
|------|---------|
| `test_deal.py` | Stage updates, activity log, version column |
| `test_property.py` | Computed properties, constraints |
| `test_financial_constraints.py` | All 41 CHECK constraints across Deal and Property |
| `test_soft_delete.py` | `soft_delete()`, `restore()`, filter behavior |
| `test_construction.py` | Construction pipeline model |
| `test_sales_data.py` | Sales data model |
| `test_reminder_dismissal.py` | Dismissal model |
| `test_user.py` | User model, password hash |

#### Extraction Tests (`tests/test_extraction/`)

| File | Coverage |
|------|---------|
| `test_extractor.py` | Cell value extraction, error handling, NaN fallback |
| `test_fingerprint.py` | `SheetFingerprint`, `FileFingerprint`, signature hashing |
| `test_grouping.py`, `test_group_discovery.py`, `test_group_extraction.py` | File grouping, clustering thresholds |
| `test_reference_mapper.py` | Field to canonical name mapping |
| `test_output_validation.py` | All 9 validation rules, error/warning/valid/skipped status |
| `test_phase1_fixes.py` through `test_phase5_observability.py` | Phased pipeline regression tests |
| `test_extraction_regression.py` | 49 regression tests for known extraction results |
| `test_data_accuracy.py`, `test_cell_mapping_accuracy.py`, `test_extraction_completeness.py` | Data correctness assertions |
| `test_candidate_filter.py` | FileFilter pattern matching |
| `test_sharepoint_integration.py` | SharePoint listing/download mocks |
| `test_proforma_expansion.py` | Proforma Returns field extraction (30 fields) |

#### Service Tests (`tests/test_services/`)

| File | Coverage |
|------|---------|
| `test_redis_service.py` | Redis connect, get, set, pub/sub |
| `test_websocket_service.py` | Channel subscribe, broadcast, disconnect |
| `test_export_service.py` | CSV/Excel generation |
| `test_pdf_service.py` | PDF report generation |
| `test_email_service.py` | SMTP send, rate limiting |
| `test_audit_service.py` | Audit log writes |
| `test_construction_import.py` | Data import pipeline |
| `test_sales_import.py` | Sales comp import |
| `test_file_monitor.py` | Change detection |
| `batch/test_batch_processor.py`, `test_job_queue.py`, `test_scheduler.py`, `test_task_executor.py` | Batch processing |
| `ml/test_model_manager.py`, `test_rent_growth_predictor.py` | ML model tests |
| `monitoring/test_collectors.py`, `test_metrics.py` | Prometheus metric collection |
| `workflow/test_workflow_engine.py`, `test_step_handlers.py` | Workflow execution |
| `test_construction_api/test_census_bps.py`, `test_fred_permits.py`, `test_bls_employment.py`, `test_mesa_soda.py`, `test_tempe_blds.py`, `test_gilbert_arcgis.py`, `test_address_matcher.py`, `test_scheduler.py` | External construction API integrations |

#### Activity Tests (`tests/api/v1/`)

| File | Coverage |
|------|---------|
| `test_activity_log.py` | Activity log API |
| `test_deal_activities.py` | Deal activity CRUD |
| `test_property_activities.py` | Property activity CRUD |

---

## 12. Settings Reference

**File:** `backend/app/core/config.py` — `Settings(BaseSettings)`. Loaded from `.env`. `@lru_cache` singleton via `get_settings()`.

Key settings grouped by domain:

| Setting | Default | Description |
|---------|---------|-------------|
| `SECRET_KEY` | Auto-generated (dev); required in prod | JWT signing key; min 32 chars in production |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `DATABASE_URL` | `sqlite:///./test.db` | SQLAlchemy sync URL (PostgreSQL in production) |
| `DATABASE_POOL_SIZE` | `10` | Connection pool size |
| `DATABASE_MAX_OVERFLOW` | `20` | Pool max overflow |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `REDIS_CACHE_TTL` | `3600` | Default cache TTL (seconds) |
| `CACHE_SHORT_TTL` | `300` | Short TTL (5 min) |
| `CACHE_LONG_TTL` | `7200` | Long TTL (2 hours) |
| `CORS_ORIGINS` | localhost:5173/:3000, production domains | Allowed CORS origins; JSON array or comma-separated |
| `API_KEYS` | `[]` | Service-to-service API keys; comma-separated |
| `API_KEY_HEADER` | `X-API-Key` | API key header name |
| `RATE_LIMIT_ENABLED` | `True` | Enable rate limiting |
| `RATE_LIMIT_REQUESTS` | `100` | Default requests per window |
| `RATE_LIMIT_WINDOW` | `60` | Rate limit window (seconds) |
| `RATE_LIMIT_AUTH_REQUESTS` | `5` | Auth endpoint rate limit |
| `RATE_LIMIT_AUTH_WINDOW` | `60` | Auth window (seconds) |
| `RATE_LIMIT_REFRESH_REQUESTS` | `10` | Token refresh rate limit |
| `SLOW_QUERY_THRESHOLD_MS` | `500` | Slow query log threshold (ms) |
| `SLOW_QUERY_LOG_PARAMS` | `False` | Include sanitized params in slow query logs |
| `LOG_LEVEL` | `INFO` | Application log level |
| `ENVIRONMENT` | `development` | `development` or `production` |
| `EXTRACTION_SCHEDULE_ENABLED` | `True` | Enable scheduled extraction |
| `EXTRACTION_SCHEDULE_CRON` | `0 17 * * *` | Extraction cron (daily 5 PM) |
| `EXTRACTION_SCHEDULE_TIMEZONE` | `America/Phoenix` | Scheduler timezone |
| `FILE_MONITOR_ENABLED` | `False` | Enable file change monitor |
| `FILE_MONITOR_INTERVAL_MINUTES` | `30` | Monitor check interval |
| `AUTO_EXTRACT_ON_CHANGE` | `True` | Auto-extract on file change |
| `FILE_PATTERN` | `.*UW\s*Model.*vCurrent.*` | Regex for UW model filenames |
| `EXCLUDE_PATTERNS` | `~$,.tmp,backup,old,archive,Speedboat,vOld` | Comma-separated exclusion substrings |
| `LOCAL_DEALS_ROOT` | `""` | Local OneDrive path to deals folder |
| `GROUP_IDENTITY_THRESHOLD` | `0.95` | File grouping identity threshold |
| `GROUP_VARIANT_THRESHOLD` | `0.80` | File grouping variant threshold |
| `UPLOAD_MAX_EXCEL_MB` | `50` | Excel upload size limit |
| `UPLOAD_MAX_PDF_MB` | `25` | PDF upload size limit |
| `UPLOAD_MAX_CSV_MB` | `10` | CSV upload size limit |
| `UPLOAD_MAX_DOCX_MB` | `25` | DOCX upload size limit |
| `AZURE_CLIENT_ID/SECRET/TENANT_ID` | None | Azure AD credentials for SharePoint |
| `SHAREPOINT_SITE_URL` | None | SharePoint site URL |
| `FRED_API_KEY` | None | FRED API key |
| `CENSUS_API_KEY` | None | Census API key |

Properties on `Settings`: `database_url_async` (converts `postgresql://` to `postgresql+asyncpg://`), `sharepoint_configured` (bool check), `get_sharepoint_config_errors()` (list of missing fields).

---

## 13. Architectural Decision Records

Located in `docs/adr/`:

| ADR | Title | Decision Summary |
|-----|-------|-----------------|
| 001 | FastAPI + SQLAlchemy Async Backend | FastAPI for async HTTP performance; SQLAlchemy 2.0 with asyncpg driver; Alembic for schema migrations; Pydantic for validation |
| 002 | React + TypeScript + Vite Frontend | React with TypeScript for type safety; Vite bundler; Zod schemas for API contract validation with snake_case to camelCase transformation |
| 003 | JWT Auth with Refresh Token Rotation | HS256 JWT; access tokens 30 min; refresh tokens 7 days, single-use with rotation; replay attack detection triggers full user session revocation |
| 004 | Dual API Client Pattern | `src/lib/api.ts` (axios) for legacy endpoints; `src/lib/api/client.ts` (fetch) for new work; both attach `Authorization: Bearer` from localStorage |
| 005 | Optimistic Locking via Version Column | Integer `version` column on `Deal`; `UPDATE WHERE version=N` atomically increments to `N+1`; 0 rowcount returned to caller as `None` → API returns 409 |
| 006 | structlog + Loguru Coexistence | Loguru for human-readable colored console/file output; structlog for JSON-structured machine-parseable events; `request_id` injected into both via ContextVar without explicit plumbing |
| 007 | Soft Delete Pattern | `SoftDeleteMixin` (`is_deleted`, `deleted_at`) applied to `Deal`, `Transaction`, `Property`, `User`; `CRUDBase` excludes soft-deleted rows by default; `include_deleted=True` parameter available for admin operations; `restore()` method available |
