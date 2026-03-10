# Backend API Reference

Generated: 2026-03-10

B&R Capital Real Estate Analytics Dashboard — complete request/response cycle documentation for every API endpoint.

---

## Table of Contents

1. [Global API Conventions](#1-global-api-conventions)
2. [Authentication & Security Mechanisms](#2-authentication--security-mechanisms)
3. [Rate Limiting](#3-rate-limiting)
4. [ETag / 304 Caching](#4-etag--304-caching)
5. [Input Sanitization](#5-input-sanitization)
6. [Soft-Delete & Restore Pattern](#6-soft-delete--restore-pattern)
7. [Authentication Endpoints (`/api/v1/auth`)](#7-authentication-endpoints)
8. [Properties Endpoints (`/api/v1/properties`)](#8-properties-endpoints)
9. [Deals Endpoints (`/api/v1/deals`)](#9-deals-endpoints)
10. [Analytics Endpoints (`/api/v1/analytics`)](#10-analytics-endpoints)
11. [Market Data Endpoints (`/api/v1/market`)](#11-market-data-endpoints)
12. [Interest Rates Endpoints (`/api/v1/interest-rates`)](#12-interest-rates-endpoints)
13. [Transactions Endpoints (`/api/v1/transactions`)](#13-transactions-endpoints)
14. [Documents Endpoints (`/api/v1/documents`)](#14-documents-endpoints)
15. [Users Endpoints (`/api/v1/users`)](#15-users-endpoints)
16. [Exports Endpoints (`/api/v1/exports`)](#16-exports-endpoints)
17. [Extraction Endpoints (`/api/v1/extraction`)](#17-extraction-endpoints)
18. [Monitoring Endpoints (`/api/v1/monitoring`)](#18-monitoring-endpoints)
19. [WebSocket Connections (`/api/v1/ws`)](#19-websocket-connections)
20. [Health Endpoints](#20-health-endpoints)
21. [Issues Found](#21-issues-found)

---

## 1. Global API Conventions

### Base URL

All REST endpoints are prefixed with `/api/v1`. Interactive docs at `/api/docs` in development only.

### Common Response Headers

| Header | Value | When |
|--------|-------|------|
| `X-Request-ID` | UUID4 | All responses — correlation ID injected by `RequestIDMiddleware` |
| `ETag` | `sha256:<hash>` | All GET 200 responses |
| `X-RateLimit-Limit` | integer | All responses when rate limiting enabled |
| `X-RateLimit-Remaining` | integer | All responses when rate limiting enabled |
| `X-RateLimit-Reset` | Unix timestamp | All responses when rate limiting enabled |
| `X-Content-Type-Options` | `nosniff` | All responses |
| `X-Frame-Options` | `DENY` | All responses |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | All responses |
| `Cache-Control` | `no-store` | All responses |

In production only: `Strict-Transport-Security` (HSTS) is added by `SecurityHeadersMiddleware`.

### Error Response Format

All error responses from `ErrorHandlerMiddleware` follow:

```json
{
  "detail": "Human-readable error message",
  "request_id": "uuid4-correlation-id"
}
```

Middleware-level exception mappings:

| Exception type | HTTP status |
|---------------|------------|
| `SQLAlchemyError` | 500 |
| `ValidationError` (Pydantic) | 422 |
| `PermissionError` | 403 |
| `ValueError` | 400 |
| Unhandled `Exception` | 500 |

### Timestamp Fields

All schemas that extend `TimestampSchema` include:
- `created_at`: `datetime` (ISO 8601, UTC)
- `updated_at`: `datetime` (ISO 8601, UTC)

### Pagination — Offset-Based

Standard paginated list responses:

```json
{
  "items": [...],
  "total": 142,
  "page": 1,
  "page_size": 20
}
```

### Pagination — Cursor-Based

Cursor-paginated responses:

```json
{
  "items": [...],
  "next_cursor": "opaque-base64-cursor",
  "prev_cursor": "opaque-base64-cursor",
  "has_more": true,
  "total": null
}
```

Pass the cursor back as the `cursor` query parameter. Direction is `next` (default) or `prev`.

---

## 2. Authentication & Security Mechanisms

### JWT Bearer Token

Most endpoints require `Authorization: Bearer <access_token>`.

Access tokens are HS256 JWTs with a 30-minute expiry (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`). Each token carries a `jti` (UUID4) for blacklisting. On decode, the token blacklist is checked before any protected endpoint proceeds.

### API Key

Service-to-service callers may use `X-API-Key: <key>` instead of Bearer.

Keys are configured via the `API_KEYS` environment variable (comma-separated). Comparison uses `hmac.compare_digest` (constant-time, timing-attack resistant). The dependency `require_api_key_or_jwt` tries Bearer first, falls back to API key. Returns `ServiceIdentity(service_name="api_key_service")`.

### RBAC Hierarchy

| Role | Level | Guard dependency |
|------|-------|-----------------|
| `viewer` | 0 | `require_viewer` |
| `analyst` | 1 | `require_analyst` |
| `manager` | 2 | `require_manager` |
| `admin` | 3 | `require_admin` |

Role checks are hierarchical: a `manager` satisfies `require_analyst`. Use `get_current_user` for any authenticated user regardless of role.

### CSRF / Origin Validation

`OriginValidationMiddleware` validates the `Origin` or `Referer` header on all `POST`, `PUT`, `PATCH`, and `DELETE` requests against the `CORS_ORIGINS` list. Requests without a matching origin are rejected before reaching the endpoint.

---

## 3. Rate Limiting

`RateLimitMiddleware` implements a sliding-window algorithm (in-memory or Redis). Enabled when `RATE_LIMIT_ENABLED=true`.

| Endpoint pattern | Limit |
|-----------------|-------|
| `/api/v1/auth/login` | 5 requests / 60 seconds |
| `/api/v1/auth/refresh` | 10 requests / 60 seconds |
| All other `/api/v1/*` | 100 requests / 60 seconds |

**On limit exceeded:**

- HTTP `429 Too Many Requests`
- `X-RateLimit-Reset` header: Unix timestamp when the window resets
- Body: `{"detail": "Rate limit exceeded", "request_id": "..."}`

---

## 4. ETag / 304 Caching

`ETagMiddleware` computes SHA-256 of the response body for all GET responses and returns it as `ETag: sha256:<hex>`.

On subsequent requests, the client may send `If-None-Match: sha256:<hex>`. On match, the server returns `304 Not Modified` with no body.

---

## 5. Input Sanitization

String fields on `DealCreate`, `DealUpdate`, `PropertyCreate`, `PropertyUpdate`, and `TransactionCreate` / `TransactionUpdate` are passed through `sanitize_string()` via a Pydantic `model_validator(mode="before")`.

Sanitization steps:
1. Strip HTML tags (regex-based)
2. Remove dangerous URI schemes: `javascript:`, `vbscript:`, `data:`
3. Strip event-handler attributes: `onerror=`, `onclick=`, etc.
4. Decode HTML entities, then re-sanitize the decoded result

**Fields sanitized on `DealCreate` / `DealUpdate`:** `name`, `source`, `broker_name`, `broker_company`, `notes`, `investment_thesis`, `key_risks`, `tags`.

**Fields sanitized on `PropertyCreate` / `PropertyUpdate`:** `name`, `address`, `city`, `state`, `county`, `market`, `submarket`, `description`.

**Fields sanitized on `TransactionCreate` / `TransactionUpdate`:** `property_name`, `category`, `description`.

---

## 6. Soft-Delete & Restore Pattern

Deals, transactions, and documents implement soft-delete via an `is_deleted: bool` column. Soft-deleted records are excluded from all standard list and get queries by the CRUD layer.

Restore endpoints (`POST /{id}/restore`) fetch with `include_deleted=True`, verify `is_deleted = true`, and reset the flag.

Properties use soft-delete via `property_crud.remove()`. There is no restore endpoint for properties.

---

## 7. Authentication Endpoints

**Prefix:** `/api/v1/auth`

Rate limited: `/login` at 5 req/60s; `/refresh` at 10 req/60s.

---

### `POST /api/v1/auth/login`

**Auth:** None
**Rate limit:** 5 req / 60s

Authenticate with email and password using OAuth2 Password flow form encoding. Tries database lookup first; falls back to demo users (non-production only, controlled by `DEMO_USER_PASSWORD` env vars).

**Request** (form-encoded `application/x-www-form-urlencoded`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `username` | string | Yes | User email address |
| `password` | string | Yes | User password |
| `grant_type` | string | No | OAuth2 standard field |

**CRUD chain:** `user_crud.authenticate(db, email, password)` → bcrypt comparison via `verify_password()`. On success, `user_crud.update_last_login()` (non-critical, errors silently swallowed). If DB user not found, falls back to `_get_demo_users()` dict.

**Response 200** (`Token`):

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

| Field | Type | Notes |
|-------|------|-------|
| `access_token` | string | HS256 JWT; 30-min expiry; payload includes `sub` (user ID string), `role`, `jti` (UUID4) |
| `refresh_token` | string | HS256 JWT; 7-day expiry; `type="refresh"`, `jti` |
| `token_type` | string | Always `"bearer"` |
| `expires_in` | integer | Seconds until access token expires (`ACCESS_TOKEN_EXPIRE_MINUTES * 60`) |

**Error responses:**

| Status | Condition |
|--------|-----------|
| 401 | Invalid email or password; `WWW-Authenticate: Bearer` header included |
| 403 | Account disabled (`is_active = false`) |
| 429 | Rate limit exceeded |

---

### `POST /api/v1/auth/refresh`

**Auth:** None
**Rate limit:** 10 req / 60s

Exchange a refresh token for new access and refresh tokens. Implements **refresh token rotation with replay detection**.

**Request body** (`application/json`, `RefreshTokenRequest`):

| Field | Type | Required |
|-------|------|----------|
| `refresh_token` | string | Yes |

**Rotation sequence:**

1. Decode token; reject if invalid, expired, or not `type="refresh"`.
2. Check `token_blacklist.is_user_revoked(user_id)` — rejects globally revoked users.
3. Check `token_blacklist.is_blacklisted(jti)` — replay detection:
   - If blacklisted: call `revoke_user_tokens(user_id, expires_in)` to invalidate **all sessions** for the user, then return 401.
4. Blacklist the old refresh token `jti` with TTL equal to its remaining lifetime.
5. Issue a new access token and a new refresh token (both have new `jti` values).

**Response 200** (`Token`): Same schema as login response.

**Error responses:**

| Status | Condition | Detail text |
|--------|-----------|-------------|
| 401 | Invalid or non-refresh token | `"Invalid refresh token"` |
| 401 | User globally revoked | `"All sessions have been revoked. Please log in again."` |
| 401 | Replay attack detected | `"Refresh token reuse detected. All sessions have been revoked for security."` |
| 429 | Rate limit exceeded | |

---

### `POST /api/v1/auth/logout`

**Auth:** Bearer (optional)

Blacklists the presented access token `jti` with TTL equal to its remaining lifetime. Always returns 200 — invalid/expired tokens are silently ignored.

**Request headers:**

| Header | Notes |
|--------|-------|
| `Authorization` | Optional. `Bearer <access_token>` |

**Response 200:**

```json
{"message": "Successfully logged out"}
```

---

### `GET /api/v1/auth/me`

**Auth:** Bearer (required)

Returns the authenticated user's profile. Checks the token blacklist (rejects revoked tokens). Fetches the user from the database by `sub` claim; falls back to token claims for demo users without a database record.

**Response 200:**

```json
{
  "id": 1,
  "email": "matt@bandrcapital.com",
  "role": "admin",
  "full_name": "Matt Borgeson",
  "is_active": true
}
```

| Field | Type | Notes |
|-------|------|-------|
| `id` | integer | User ID from token `sub` claim |
| `email` | string | |
| `role` | string | `viewer`, `analyst`, `manager`, or `admin` |
| `full_name` | string or null | |
| `is_active` | boolean | Present for demo-user fallback only |

**Error responses:**

| Status | Condition |
|--------|-----------|
| 401 | Invalid or expired token |
| 401 | Token JTI found in blacklist |

---

## 8. Properties Endpoints

**Prefix:** `/api/v1/properties`
**Minimum auth:** `require_analyst` (all GETs); `require_manager` (POST, PUT, DELETE)

### N+1 Fix — Batch Enrichment

`GET /dashboard` and `GET /summary` use `property_crud.enrich_financial_data_batch(db, items)`, which resolves financial data for all properties in exactly 2 queries regardless of count. The single-property endpoint `GET /dashboard/{id}` uses lazy enrichment (`enrich_financial_data(db, prop)`).

---

### `GET /api/v1/properties/dashboard`

**Auth:** `require_analyst`
**Cache:** `LONG_TTL` (key: `property_dashboard_list`). Invalidated on any property create/update/delete.

Returns all properties in the nested frontend format built by `to_frontend_property()`.

**Response 200:**

```json
{
  "properties": [<FrontendProperty>, ...],
  "total": 305
}
```

Each `FrontendProperty` contains nested sub-objects: `acquisition`, `financing`, `returns`, `expenses`, `operationsByYear`, `metrics`. Shape is defined by `_property_transforms.py`.

---

### `GET /api/v1/properties/dashboard/{property_id}`

**Auth:** `require_analyst`

Returns a single property in frontend format. If `financial_data` on the ORM record is missing `expenses` or `operationsByYear` keys, lazy enrichment from `extracted_values` is triggered.

**Path params:**

| Param | Type |
|-------|------|
| `property_id` | integer |

**Response 200:** Single `FrontendProperty` object.

**Error responses:** 404 not found.

---

### `GET /api/v1/properties/summary`

**Auth:** `require_analyst`
**Cache:** `LONG_TTL` (key: `portfolio_summary`)

Portfolio-level aggregated statistics.

**Response 200:**

```json
{
  "totalProperties": 11,
  "totalUnits": 2450,
  "totalValue": 185000000.00,
  "totalInvested": 142000000.00,
  "totalNOI": 8200000.00,
  "averageOccupancy": 0.9460,
  "averageCapRate": 0.0573,
  "portfolioCashOnCash": 0.0812,
  "portfolioIRR": 0.1420
}
```

| Field | Calculation |
|-------|------------|
| `totalInvested` | Sum of `financial_data.acquisition.totalAcquisitionBudget`; fallback to `purchase_price` |
| `totalNOI` | Sum of `noi_per_unit * total_units` per property |
| `averageOccupancy` | Mean `occupancy_rate / 100` where `occupancy_rate` is not null |
| `averageCapRate` | Mean of `annual_noi / purchase_price` per property |
| `portfolioCashOnCash` | Equity-weighted average of `financial_data.returns.cashOnCashYear1` |
| `portfolioIRR` | Equity-weighted average of `financial_data.returns.lpIrr` |

---

### `GET /api/v1/properties/`

**Auth:** `require_analyst`

Paginated, filterable list of properties.

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | integer | 1 | ≥1 |
| `page_size` | integer | 20 | 1–100 |
| `property_type` | string | — | `multifamily`, `office`, `retail`, `industrial`, `mixed_use`, `other` |
| `city` | string | — | Exact match |
| `state` | string | — | Exact match |
| `market` | string | — | Exact match |
| `min_units` | integer | — | |
| `max_units` | integer | — | |
| `sort_by` | string | `name` | |
| `sort_order` | string | `asc` | `asc` or `desc` |

**CRUD chain:** `property_crud.get_multi_filtered()` + `property_crud.count_filtered()`

**Response 200** (`PropertyListResponse`): `items` (array of `PropertyResponse`), `total`, `page`, `page_size`.

`PropertyResponse` fields:

| Field | Type | Notes |
|-------|------|-------|
| `id` | integer | |
| `name` | string | Max 255 |
| `property_type` | string | Enum |
| `address` | string | Max 500 |
| `city` | string | Max 100 |
| `state` | string | Max 50 |
| `zip_code` | string | Max 20 |
| `county` | string or null | |
| `market` | string or null | |
| `submarket` | string or null | |
| `year_built` | integer or null | 1800–2100 |
| `year_renovated` | integer or null | 1800–2100 |
| `total_units` | integer or null | |
| `total_sf` | integer or null | |
| `lot_size_acres` | decimal or null | |
| `stories` | integer or null | |
| `parking_spaces` | integer or null | |
| `purchase_price` | decimal or null | |
| `current_value` | decimal or null | |
| `acquisition_date` | date or null | |
| `occupancy_rate` | decimal or null | Stored as 0–100 |
| `avg_rent_per_unit` | decimal or null | |
| `avg_rent_per_sf` | decimal or null | |
| `noi` | decimal or null | Annual per-unit |
| `cap_rate` | decimal or null | Stored as 0–1 |
| `description` | string or null | |
| `amenities` | object or null | Free-form JSON |
| `unit_mix` | object or null | Free-form JSON |
| `images` | string[] or null | |
| `external_id` | string or null | |
| `data_source` | string or null | |
| `price_per_unit` | decimal or null | Computed: `purchase_price / total_units` |
| `price_per_sf` | decimal or null | Computed: `purchase_price / total_sf` |
| `created_at` | datetime | |
| `updated_at` | datetime | |

---

### `GET /api/v1/properties/cursor`

**Auth:** `require_analyst`

Cursor-paginated properties list. Supports the same filters as `GET /properties/`.

**Additional query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `cursor` | string | null | Opaque cursor from previous response |
| `limit` | integer | 20 | 1–100 |
| `direction` | string | `next` | `next` or `prev` |

**CRUD chain:** `property_crud._build_property_conditions()` → `property_crud.get_cursor_paginated()`

**Response 200** (`PropertyCursorPaginatedResponse`): `items`, `next_cursor`, `prev_cursor`, `has_more`, `total`.

**Error responses:** 400 on invalid cursor.

---

### `GET /api/v1/properties/{property_id}`

**Auth:** `require_analyst`

**CRUD chain:** `property_crud.get(db, property_id)`

**Response 200:** `PropertyResponse`

**Error responses:** 404 not found.

---

### `POST /api/v1/properties/`

**Auth:** `require_manager`
**Status:** 201 Created

All string fields are sanitized. After creation, calls `cache.invalidate_properties()`.

**Request body** (`PropertyCreate`): Required: `name`, `property_type`, `address`, `city`, `state`, `zip_code`. All other fields optional.

**Response 201:** `PropertyResponse`

---

### `PUT /api/v1/properties/{property_id}`

**Auth:** `require_manager`

Full update. All `PropertyUpdate` fields are optional. Calls `cache.invalidate_properties()`.

**Response 200:** `PropertyResponse`

**Error responses:** 404 not found.

---

### `DELETE /api/v1/properties/{property_id}`

**Auth:** `require_manager`
**Status:** 204 No Content

Soft-delete via `property_crud.remove()`. Calls `cache.invalidate_properties()`. No restore endpoint.

**Error responses:** 404 not found.

---

### `GET /api/v1/properties/{property_id}/analytics`

**Auth:** `require_analyst`

Returns performance metrics, rent/occupancy trends, and market comparables. Falls back to static mock data when both `avg_rent_per_unit` and `occupancy_rate` are null.

Market comparables are computed as aggregates (`avg_rent`, `avg_occupancy`, `avg_cap_rate`, `comp_count`) from properties sharing the same `market` and `property_type`, excluding the current property.

**Response 200** (untyped dict, `data_source: "database"` or `"mock"`):

```json
{
  "property_id": 1,
  "property_name": "Arcadia Commons",
  "data_source": "database",
  "metrics": {
    "current_rent_per_unit": 1425.00,
    "current_occupancy": 94.5,
    "current_cap_rate": 5.8,
    "current_noi": 850000.00,
    "ytd_rent_growth": null,
    "ytd_noi_growth": null,
    "avg_occupancy_12m": 94.5,
    "rent_vs_market": 1.02
  },
  "trends": {
    "rent": [1425.0],
    "occupancy": [94.5],
    "periods": ["Current"],
    "note": "Historical trend data requires time-series tracking"
  },
  "comparables": {
    "market": "Phoenix Metro",
    "property_type": "multifamily",
    "market_avg_rent": 1398.00,
    "market_avg_occupancy": 93.8,
    "market_avg_cap_rate": 5.6,
    "comparable_count": 4
  }
}
```

**Error responses:** 404 not found.

---

### `GET /api/v1/properties/{property_id}/activities`

**Auth:** `require_analyst`

Paginated activity history.

**Query params:**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `skip` | integer | 0 | |
| `limit` | integer | 50 | 1–100 |
| `activity_type` | string | — | `view`, `edit`, `comment`, `status_change`, `document_upload` |

**CRUD chain:** `property_activity.get_by_property()` + `property_activity.count_by_property()`

**Response 200** (`PropertyActivityListResponse`): `activities`, `total`, `page`, `page_size`.

`PropertyActivityResponse` fields: `id`, `property_id`, `user_id`, `user_name` (always null — join not implemented), `activity_type`, `description`, `field_changed`, `old_value`, `new_value`, `comment_text`, `document_name`, `document_url`, `created_at`, `updated_at`.

**Error responses:** 400 invalid activity_type; 404 not found.

---

### `POST /api/v1/properties/{property_id}/activities`

**Auth:** `get_current_user` (any authenticated)

Logs a manual activity. `user_id` and client IP are captured from session/request context.

**Request body** (`PropertyActivityCreate`):

| Field | Required |
|-------|----------|
| `property_id` | Yes — must match path param |
| `activity_type` | Yes |
| `description` | Yes |
| `field_changed`, `old_value`, `new_value`, `comment_text`, `document_name`, `document_url` | No |

**Response 200:** `PropertyActivityResponse`

**Error responses:** 400 if body `property_id` != path param; 404 not found.

---

## 9. Deals Endpoints

**Prefix:** `/api/v1/deals`
**Minimum auth:** `require_analyst` (GETs); `require_manager` (PUT, PATCH, DELETE, restore, stage)

### Extraction Enrichment

Most deal read endpoints call `_enrich_deals_with_extraction(db, deal_responses)`. This function issues exactly 2 database queries for any batch size:

1. Subquery: finds the latest completed `ExtractionRun.completed_at` per `property_id`.
2. JOIN query: fetches up to 36 `ExtractedValue` fields for all property IDs in the batch.

All enrichment fields on `DealResponse` are `null` when no extraction data exists.

**Enriched fields and their extraction field names:**

| DealResponse field | ExtractedValue field_name |
|-------------------|--------------------------|
| `total_units` | `TOTAL_UNITS` |
| `avg_unit_sf` | `AVERAGE_UNIT_SF` |
| `current_owner` | `CURRENT_OWNER` |
| `last_sale_price_per_unit` | `LAST_SALE_PRICE_PER_UNIT` |
| `last_sale_date` | `LAST_SALE_DATE` |
| `t12_return_on_cost` | `T12_RETURN_ON_COST` |
| `levered_irr` | `LEVERED_RETURNS_IRR` |
| `levered_moic` | `LEVERED_RETURNS_MOIC` |
| `unlevered_irr` | `UNLEVERED_RETURNS_IRR` |
| `unlevered_moic` | `UNLEVERED_RETURNS_MOIC` |
| `lp_irr` | `LP_RETURNS_IRR` |
| `lp_moic` | `LP_RETURNS_MOIC` |
| `property_city` | `PROPERTY_CITY` |
| `submarket` | `SUBMARKET` |
| `year_built` | `YEAR_BUILT` |
| `year_renovated` | `YEAR_RENOVATED` |
| `vacancy_rate` | `VACANCY_LOSS_YEAR_1_RATE` |
| `bad_debt_rate` | `BAD_DEBTS_YEAR_1_RATE` |
| `other_loss_rate` | `OTHER_LOSS_YEAR_1_RATE` |
| `concessions_rate` | `CONCESSIONS_YEAR_1_RATE` |
| `noi_margin` | `NET_OPERATING_INCOME_MARGIN` |
| `purchase_price_extracted` | `PURCHASE_PRICE` |
| `total_acquisition_budget` | `TOTAL_ACQUISITION_BUDGET` |
| `basis_per_unit` | `BASIS_UNIT_AT_CLOSE` (computed from budget/units if null) |
| `t12_cap_on_pp` | `T12_RETURN_ON_PP` |
| `t3_cap_on_pp` | `T3_RETURN_ON_PP` |
| `total_cost_cap_t12` | `T12_RETURN_ON_COST` |
| `total_cost_cap_t3` | `T3_RETURN_ON_COST` |
| `loan_amount` | `LOAN_AMOUNT` |
| `lp_equity` / `total_equity_commitment` | `EQUITY_LP_CAPITAL` |
| `exit_months` | `EXIT_PERIOD_MONTHS` |
| `exit_cap_rate` | `EXIT_CAP_RATE` |
| `latitude` | `PROPERTY_LATITUDE` |
| `longitude` | `PROPERTY_LONGITUDE` |

---

### `GET /api/v1/deals/`

**Auth:** `require_analyst`

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | integer | 1 | ≥1 |
| `page_size` | integer | 20 | 1–100 |
| `stage` | string | — | `dead`, `initial_review`, `active_review`, `under_contract`, `closed`, `realized` |
| `deal_type` | string | — | `acquisition`, `disposition`, `development`, `refinance` |
| `priority` | string | — | `low`, `medium`, `high`, `urgent` |
| `assigned_user_id` | integer | — | |
| `sort_by` | string | `created_at` | |
| `sort_order` | string | `desc` | |

**CRUD chain:** `deal_crud.get_multi_filtered()` + `deal_crud.count_filtered()` → `_enrich_deals_with_extraction()`

**Response 200** (`DealListResponse`): `items`, `total`, `page`, `page_size`.

`DealResponse` core fields:

| Field | Type | Notes |
|-------|------|-------|
| `id` | integer | |
| `version` | integer | Optimistic locking counter; starts at 1 |
| `name` | string | Max 255; sanitized |
| `deal_type` | string | Enum |
| `property_id` | integer or null | FK to properties |
| `assigned_user_id` | integer or null | |
| `stage` | string | Enum: dead/initial_review/active_review/under_contract/closed/realized |
| `stage_order` | integer | Position within Kanban column |
| `asking_price` | decimal or null | |
| `offer_price` | decimal or null | |
| `final_price` | decimal or null | |
| `projected_irr` | decimal or null | Underwriter estimate; 0–1 |
| `projected_coc` | decimal or null | 0–1 |
| `projected_equity_multiple` | decimal or null | |
| `hold_period_years` | integer or null | 1–30 |
| `initial_contact_date` | date or null | |
| `loi_submitted_date` | date or null | |
| `due_diligence_start` | date or null | |
| `due_diligence_end` | date or null | |
| `target_close_date` | date or null | |
| `actual_close_date` | date or null | |
| `source` | string or null | Max 100; sanitized |
| `broker_name` | string or null | Max 255; sanitized |
| `broker_company` | string or null | Max 255; sanitized |
| `competition_level` | string or null | `low`, `medium`, `high` |
| `notes` | string or null | Sanitized |
| `investment_thesis` | string or null | Sanitized |
| `key_risks` | string or null | Sanitized |
| `tags` | string[] or null | Sanitized |
| `custom_fields` | object or null | |
| `deal_score` | integer or null | 0–100 |
| `priority` | string | `low`, `medium`, `high`, `urgent` |
| `stage_updated_at` | datetime or null | |
| `documents` | object[] or null | |
| `activity_log` | object[] or null | |
| `recent_activities` | `RecentActivityItem[]` or null | Populated by kanban endpoint only |
| `created_at` | datetime | |
| `updated_at` | datetime | |
| *(enrichment fields)* | float or null | See extraction enrichment table above |

`RecentActivityItem` fields: `action` (string), `description` (string), `created_at` (datetime).

---

### `GET /api/v1/deals/cursor`

**Auth:** `require_analyst`

Cursor-paginated deals with extraction enrichment.

**Additional query params:** `cursor`, `limit` (1–100, default 20), `direction` (`next`/`prev`).

Same filter params as `GET /deals/`.

**CRUD chain:** `deal_crud._build_deal_conditions()` → `deal_crud.get_cursor_paginated()` → `_enrich_deals_with_extraction()`

**Response 200** (`DealCursorPaginatedResponse`): `items`, `next_cursor`, `prev_cursor`, `has_more`, `total`.

**Error responses:** 400 on invalid cursor.

---

### `GET /api/v1/deals/kanban`

**Auth:** `require_analyst`

Returns all deals grouped by stage. Performs batch extraction enrichment across all stages in one pass, then batch-fetches up to 3 recent `ActivityLog` entries per deal (`activity_log_crud.get_recent_for_deals()`).

**Query params:** `deal_type`, `assigned_user_id` (both optional).

**CRUD chain:** `deal_crud.get_kanban_data()` → `_enrich_deals_with_extraction()` → `activity_log_crud.get_recent_for_deals(deal_ids, limit_per_deal=3)`

**Response 200** (`KanbanBoardResponse`):

```json
{
  "stages": {
    "initial_review": [<DealResponse>, ...],
    "active_review": [...],
    "under_contract": [...],
    "closed": [...],
    "dead": [...],
    "realized": [...]
  },
  "total_deals": 73,
  "stage_counts": {
    "initial_review": 28,
    "active_review": 23,
    "under_contract": 2,
    "closed": 5,
    "dead": 12,
    "realized": 3
  }
}
```

Each deal in the kanban response includes `recent_activities` (array of up to 3 `RecentActivityItem`).

---

### `GET /api/v1/deals/compare`

**Auth:** `get_current_user` (any authenticated)

Compare 2–10 deals side-by-side. Uses `deal_crud.get_by_ids()` batch fetch.

**Query params:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `ids` | string | Yes | Comma-separated deal IDs, e.g. `1,2,3` |

**Scoring algorithm (for `overall_recommendation`):**

```
score = (levered_irr * 0.30) + (projected_coc * 0.20) + (projected_equity_multiple * 0.20) + ((deal_score / 100) * 0.30)
```

Deal with highest `score` is recommended.

**Response 200** (`DealComparisonResponse`):

```json
{
  "deals": [<DealResponse>, ...],
  "comparison_summary": {
    "best_irr": 3,
    "best_coc": 1,
    "best_equity_multiple": 3,
    "lowest_price": 2,
    "highest_score": 3,
    "overall_recommendation": 3,
    "recommendation_reason": "Best overall metrics: 18.4% levered IRR, score of 82/100"
  },
  "metric_comparisons": [
    {
      "metric_name": "Levered IRR",
      "values": {"1": 0.142, "2": 0.115, "3": 0.184},
      "best_deal_id": 3,
      "best_value": 0.184,
      "comparison_type": "higher_is_better"
    }
  ],
  "deal_count": 3,
  "compared_at": "2026-03-10T09:15:00Z"
}
```

Metrics compared: `Levered IRR`, `NOI Margin`, `T12 Cap on PP`, `Asking Price` (lower_is_better), `Deal Score`, `Unlevered IRR`.

**Error responses:**

| Status | Condition |
|--------|-----------|
| 400 | Non-integer IDs, fewer than 2, or more than 10 IDs |
| 404 | Any specified deal ID not found |

---

### `GET /api/v1/deals/{deal_id}`

**Auth:** `require_analyst`

Single deal with full extraction enrichment. Uses `deal_crud.get_with_relations()` for eager-loading.

**Response 200:** `DealResponse` (all fields).

**Error responses:** 404 not found.

---

### `POST /api/v1/deals/`

**Auth:** `require_manager`
**Status:** 201 Created

Creates a deal. After creation, sends WebSocket notification (`action="created"`) and calls `cache.invalidate_deals()`.

**Request body** (`DealCreate`): Required: `name`, `deal_type`. All string fields sanitized. See enrichment section for full field list.

**Response 201:** `DealResponse`

---

### `PUT /api/v1/deals/{deal_id}` — Optimistic Locking Update

**Auth:** `require_manager`

Full update with optimistic locking. The `version` field is required and must match the stored value.

**Request body** (`DealUpdate`):

| Field | Required | Notes |
|-------|----------|-------|
| `version` | **Yes** | Must match current DB version |
| All other `DealUpdate` fields | No | Same fields as `DealCreate` plus `final_price`, timeline dates, `deal_score` |

**Optimistic locking:** `deal_crud.update_optimistic()` executes `UPDATE deals SET version = version + 1, ... WHERE id = :id AND version = :expected_version`. If 0 rows affected, returns `None` → 409.

On success: WebSocket `deal_update` (`action="updated"`). Calls `cache.invalidate_deals()`.

**Response 200:** `DealResponse`

**Error responses:**

| Status | Condition |
|--------|-----------|
| 404 | Deal not found |
| 409 | Version mismatch — another user modified the deal |

---

### `PATCH /api/v1/deals/{deal_id}`

**Auth:** `require_manager`

Partial update with identical optimistic locking semantics as `PUT`. Uses `model_dump(exclude_unset=True)`. Only provided fields are updated.

**Error responses:** Same as `PUT`.

---

### `PATCH /api/v1/deals/{deal_id}/stage`

**Auth:** `require_manager`

Updates deal stage for Kanban drag-and-drop. Does not use optimistic locking.

**Request body** (`DealStageUpdate`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `stage` | string | Yes | Enum: dead/initial_review/active_review/under_contract/closed/realized |
| `stage_order` | integer or null | No | ≥0; position within column |

**CRUD chain:** `deal_crud.get()` → `deal_crud.update_stage()` → WebSocket `stage_changed` → `cache.invalidate_deals()`

**Response 200:** `DealResponse`

**Error responses:** 400 invalid stage; 404 not found.

---

### `DELETE /api/v1/deals/{deal_id}`

**Auth:** `require_manager`
**Status:** 204 No Content

Soft-delete. Triggers WebSocket `deal_update` (`action="deleted"`). Calls `cache.invalidate_deals()`.

**Error responses:** 404 not found.

---

### `POST /api/v1/deals/{deal_id}/restore`

**Auth:** `require_manager`

Restores a soft-deleted deal. Fetches with `include_deleted=True`. Triggers WebSocket `deal_update` (`action="restored"`).

**Response 200:** `DealResponse`

**Error responses:**

| Status | Condition |
|--------|-----------|
| 400 | Deal is not currently deleted |
| 404 | Deal not found (including deleted) |
| 500 | `deal_crud.restore()` returned None |

---

### `POST /api/v1/deals/{deal_id}/activity`

**Auth:** `get_current_user`

Appends a `DealActivity` entry. `user_id` and `deal_id` are set server-side.

**Request body** (`DealActivityCreate`): `activity_type` (required), `description` (required), other activity fields optional.

**Response 200:** `DealActivityResponse`

**Error responses:** 404 not found.

---

### `GET /api/v1/deals/{deal_id}/activity`

**Auth:** `require_analyst`

Paginated deal activity history (reverse chronological).

**Query params:** `page` (default 1), `page_size` (default 50, max 100), `activity_type` (optional filter).

**CRUD chain:** `deal_activity.get_by_deal()` + `deal_activity.count_by_deal()`

**Response 200** (`DealActivityListResponse`): `items`, `total`, `page`, `page_size`.

**Error responses:** 404 not found.

---

### `POST /api/v1/deals/{deal_id}/watchlist`

**Auth:** `get_current_user`

Toggle the deal on/off the current user's watchlist.

**Response 200** (`WatchlistToggleResponse`):

```json
{
  "deal_id": 5,
  "is_watched": true,
  "message": "Deal 'Arcadia Commons' added to your watchlist",
  "watchlist_id": 12
}
```

**Error responses:** 404 not found.

---

### `GET /api/v1/deals/{deal_id}/watchlist/status`

**Auth:** `get_current_user`

**Response 200:** `{"deal_id": 5, "is_watched": true}`

**Error responses:** 404 not found.

---

### `GET /api/v1/deals/{deal_id}/activity-log`

**Auth:** `require_analyst`

UUID-based immutable `ActivityLog` entries (distinct from `DealActivity`). JSONB metadata support.

**Query params:** `page` (default 1), `page_size` (default 50, max 100), `action` (optional filter).

Valid `action` values: `created`, `updated`, `stage_changed`, `document_added`, `document_removed`, `note_added`, `assigned`, `unassigned`, `price_changed`, `viewed`.

**CRUD chain:** `activity_log_crud.get_by_deal()` + `activity_log_crud.count_by_deal()`

**Response 200** (`ActivityLogListResponse`): `items`, `total`, `page`, `page_size`.

`ActivityLogResponse` fields: `id` (UUID), `deal_id`, `action`, `description`, `user_id` (string), `metadata` (JSON object), `created_at`.

**Error responses:** 400 invalid action type; 404 not found.

---

### `POST /api/v1/deals/{deal_id}/activity-log`

**Auth:** `get_current_user`

Create a manual audit log entry. Immutable once written. `user_id` populated from authenticated session.

**Request body** (`ActivityLogCreate`):

| Field | Type | Required |
|-------|------|----------|
| `action` | string | Yes — must be valid `ActivityAction` enum value |
| `description` | string | Yes |
| `metadata` | object or null | No — arbitrary JSONB |

**Response 200:** `ActivityLogResponse`

**Error responses:** 404 not found.

---

### `GET /api/v1/deals/{deal_id}/proforma-returns`

**Auth:** `require_analyst`

Fetches proforma-specific extracted values for a deal. Matches by `ExtractedValue.property_name` against the deal name (also tries base name without `(City, ST)` suffix). Excludes rows where `is_error = true`.

**Proforma fields fetched (30 total):**

| Category | Field names |
|---------|------------|
| Year-specific IRR/MOIC | `LEVERED_RETURNS_IRR_YR2/3/7`, `LEVERED_RETURNS_MOIC_YR2/3/7`, `UNLEVERED_RETURNS_IRR_YR2/3/7`, `UNLEVERED_RETURNS_MOIC_YR2/3/7` |
| NOI per unit | `NOI_PER_UNIT_YR2/3/5/7` |
| Cap rates | `CAP_RATE_ALL_IN_YR3/5` |
| CoC / DSCR | `COC_YR5`, `DSCR_T3`, `DSCR_YR5` |
| Proforma NOI | `PROFORMA_NOI_YR1/2/3` |
| Proforma DSCR | `PROFORMA_DSCR_YR1/2/3` |
| Proforma Debt Yield | `PROFORMA_DEBT_YIELD_YR1/2/3` |

**Response 200:**

```json
{
  "deal_id": 5,
  "deal_name": "Arcadia Commons (Phoenix, AZ)",
  "groups": [
    {
      "category": "Returns",
      "fields": [
        {"field_name": "LEVERED_RETURNS_IRR_YR3", "value_numeric": 0.172, "value_text": null}
      ]
    }
  ],
  "total": 18
}
```

Returns `{"deal_id": ..., "groups": [], "total": 0}` when no proforma data found (not 404).

**Error responses:** 404 if deal not found.

---

## 10. Analytics Endpoints

**Prefix:** `/api/v1/analytics`
**Auth:** `require_viewer` (router-level dependency)

All endpoints fall back to static mock data when the database contains no properties.

---

### `GET /api/v1/analytics/dashboard`

**Cache:** `SHORT_TTL` (key: `analytics_dashboard`)

**Response 200:**

```json
{
  "portfolio_summary": {
    "total_properties": 11,
    "total_units": 2450,
    "total_sf": 750000,
    "total_value": 185000000.0,
    "avg_occupancy": 94.5,
    "avg_cap_rate": 5.8
  },
  "kpis": {
    "ytd_noi_growth": 0.0,
    "ytd_rent_growth": 0.0,
    "deals_in_pipeline": 8,
    "deals_closed_ytd": 2,
    "capital_deployed_ytd": 45000000.0
  },
  "alerts": [
    {"type": "warning", "message": "2 properties below 90% occupancy", "count": 2}
  ],
  "recent_activity": [
    {"type": "deal_update", "message": "Arcadia Commons moved to Active UW and Review", "timestamp": "2026-03-09T14:30:00Z"}
  ]
}
```

Note: `ytd_noi_growth` and `ytd_rent_growth` are always `0.0` — historical time-series data is not stored.

---

### `GET /api/v1/analytics/portfolio`

**Query params:**

| Param | Type | Default | Values |
|-------|------|---------|--------|
| `time_period` | string | `ytd` | `mtd`, `qtd`, `ytd`, `1y`, `3y`, `5y`, `all` |
| `property_type` | string | — | Optional filter |
| `market` | string | — | Optional filter |

**Response 200:** Portfolio composition by type and market (with counts, value, pct). Performance metrics (`total_return`, `income_return`, etc.) are always `0.0` — historical value data not available. Trend arrays contain a single "Current" point only.

---

### `GET /api/v1/analytics/market-data`

**Query params:** `market` (required), `property_type` (optional).

**Response 200:** Market metrics from internal portfolio data. Economic indicators (`unemployment_rate`, etc.) are always `null` — external BLS/Census integration pending.

---

### `POST /api/v1/analytics/rent-prediction`

ML-powered rent growth prediction.

**Request body:** Free-form `dict` of property attributes.

**Query params:** `prediction_months` (1–60, default 12).

**Response 200:** `property_id`, `current_rent`, `predicted_rent`, `predicted_growth_rate`, `confidence_interval` (`lower`, `upper`), `prediction_period_months`, `model_version`, `prediction_date`.

**Error responses:** 500 if prediction failed.

---

### `POST /api/v1/analytics/rent-prediction/batch`

**Request body:** Array of property attribute dicts.

**Query params:** `prediction_months` (1–60, default 12).

**Response 200:** `predictions` array, `count`, `model_version`.

---

### `GET /api/v1/analytics/deal-pipeline`

**Cache:** `SHORT_TTL` (key: `deal_stats:<time_period>`)

**Query params:** `time_period` (`mtd`, `qtd`, `ytd`, `1y`, `all`; default `ytd`).

**Response 200:** Deal funnel counts (6 stages), stage labels map, conversion rates, cycle times (all `null` — stage transition history not tracked), and volume metrics.

---

## 11. Market Data Endpoints

**Prefix:** `/api/v1/market`
**Auth:** `require_viewer` (router-level); `/refresh` requires `require_admin`

---

### `POST /api/v1/market/refresh`

**Auth:** `require_admin`

Triggers synchronous incremental FRED data extraction. Runs `run_fred_extraction_async(incremental=True)`.

**Response 200:** `status`, `records_upserted`, `message`, `last_updated`.

---

### `GET /api/v1/market/overview`

**Response model:** `MarketOverviewResponse` — Phoenix MSA overview (population, employment, GDP, economic indicators).

---

### `GET /api/v1/market/usa/overview`

**Response model:** `MarketOverviewResponse` — National overview using FRED series: `UNRATE`, `PAYEMS`, `CPIAUCSL`, `GDP`, `MORTGAGE30US`, `FEDFUNDS`, `HOUST`, `PERMIT`.

---

### `GET /api/v1/market/usa/trends`

**Query params:** `period_months` (1–36, default 12).

**Response model:** `MarketTrendsResponse` — monthly national trend data.

---

### `GET /api/v1/market/submarkets`

**Response model:** `SubmarketsResponse` — all 15 CoStar submarket clusters with rent, occupancy, cap rate, inventory, and absorption metrics.

---

### `GET /api/v1/market/trends`

**Query params:** `period_months` (1–36, default 12).

**Response model:** `MarketTrendsResponse` — Phoenix MSA monthly trend data.

---

### `GET /api/v1/market/comparables`

**Query params:**

| Param | Type | Default | Range |
|-------|------|---------|-------|
| `property_id` | string | — | Optional reference property |
| `submarket` | string | — | Optional filter |
| `radius_miles` | float | 5.0 | 0.5–25.0 |
| `limit` | integer | 10 | 1–50 |

**Response model:** `ComparablesResponse` — comparable properties with sale and performance data.

---

## 12. Interest Rates Endpoints

**Prefix:** `/api/v1/interest-rates`
**Auth:** `require_viewer` (router-level dependency)

Data sourced from FRED API; cached in database. Refreshed twice daily by `InterestRateScheduler`.

---

### `GET /api/v1/interest-rates/current`

**Query params:** `force_refresh` (boolean, default false — when true, queries FRED before returning).

**Response model:** `KeyRatesResponse`:

```json
{
  "key_rates": {
    "fed_funds": {"rate": 5.33, "change": -0.25},
    "sofr": {"rate": 5.31, "change": -0.02},
    "treasury_2y": {"rate": 4.72, "change": 0.05},
    "treasury_5y": {"rate": 4.38, "change": 0.03},
    "treasury_7y": {"rate": 4.32, "change": 0.02},
    "treasury_10y": {"rate": 4.28, "change": 0.01},
    "mortgage_30y": {"rate": 6.85, "change": -0.10}
  },
  "last_updated": "2026-03-10T08:00:00Z",
  "source": "database"
}
```

---

### `GET /api/v1/interest-rates/yield-curve`

**Query params:** `force_refresh` (boolean, default false).

**Response model:** `YieldCurveResponse` — yield data for maturities 1 month to 30 years.

---

### `GET /api/v1/interest-rates/historical`

**Query params:** `months` (1–60, default 12), `force_refresh` (boolean, default false).

**Response model:** `HistoricalRatesResponse` — monthly data for Fed Funds, Treasury yields (2Y, 5Y, 10Y, 30Y), SOFR, 30Y mortgage.

---

### `GET /api/v1/interest-rates/spreads`

**Query params:** `months` (1–60, default 12).

**Response model:** `RateSpreadsResponse` — 2s10s Treasury spread, mortgage spread, Fed Funds vs Treasury.

---

### `GET /api/v1/interest-rates/data-sources`

Returns static list of 4 data sources: FRED, U.S. Treasury, CME Group (SOFR), NY Fed. Each includes `id`, `name`, `url`, `description`, `data_types`, `update_frequency`.

---

### `GET /api/v1/interest-rates/lending-context`

Returns typical spreads and indicative rates for: multifamily permanent (spread over 10Y Treasury), multifamily bridge (spread over SOFR), commercial permanent, construction (spread over Prime).

---

## 13. Transactions Endpoints

**Prefix:** `/api/v1/transactions`
**Auth:** `require_viewer` (router-level dependency)

Supports soft-delete and restore.

---

### `GET /api/v1/transactions/`

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | integer | 1 | |
| `page_size` | integer | 20 | Max 100 |
| `type` | string | — | `acquisition`, `disposition`, `capital_improvement`, `refinance`, `distribution` |
| `property_id` | integer | — | |
| `category` | string | — | |
| `date_from` | date | — | `YYYY-MM-DD` |
| `date_to` | date | — | `YYYY-MM-DD` |
| `sort_by` | string | `date` | |
| `sort_order` | string | `desc` | |

**CRUD chain:** `transaction_crud.get_filtered()` + `transaction_crud.count_filtered()`

**Response 200** (`TransactionListResponse`): `items`, `total`, `page`, `page_size`.

`TransactionResponse` fields:

| Field | Type | Notes |
|-------|------|-------|
| `id` | integer | |
| `property_id` | integer or null | |
| `property_name` | string | Max 255; sanitized |
| `type` | string | Enum |
| `category` | string or null | Max 100; sanitized |
| `amount` | decimal | ≥0 |
| `date` | date | |
| `description` | string or null | Sanitized |
| `documents` | string[] or null | |
| `created_at` | datetime | |
| `updated_at` | datetime | |

---

### `GET /api/v1/transactions/summary`

**Query params:** `property_id`, `date_from`, `date_to` (all optional).

**Response 200** (`TransactionSummaryResponse`):

```json
{
  "total_acquisitions": 45000000.00,
  "total_dispositions": 0.00,
  "total_capital_improvements": 3200000.00,
  "total_refinances": 0.00,
  "total_distributions": 1500000.00,
  "transaction_count": 8,
  "transactions_by_type": {"acquisition": 2, "capital_improvement": 5, "distribution": 1}
}
```

---

### `GET /api/v1/transactions/by-property/{property_id}`

**Path params:** `property_id` (integer).

**Query params:** `skip` (default 0), `limit` (default 100, max 500).

**Response 200:** `list[TransactionResponse]`

---

### `GET /api/v1/transactions/by-type/{transaction_type}`

**Path params:** `transaction_type` — must be one of the 5 valid types.

**Query params:** `skip`, `limit` (max 500).

**Response 200:** `list[TransactionResponse]`

**Error responses:** 400 invalid type.

---

### `GET /api/v1/transactions/{transaction_id}`

**Response 200:** `TransactionResponse`

**Error responses:** 404 not found.

---

### `POST /api/v1/transactions/`

**Status:** 201 Created

**Request body** (`TransactionCreate`): `property_name` (required), `type` (required), `amount` (required, ≥0), `date` (required); `property_id`, `category`, `description`, `documents` optional.

**Response 201:** `TransactionResponse`

---

### `PUT /api/v1/transactions/{transaction_id}`

Full update. All `TransactionUpdate` fields optional.

**Response 200:** `TransactionResponse`. **Error:** 404.

---

### `PATCH /api/v1/transactions/{transaction_id}`

Partial update. Same CRUD path as PUT.

**Response 200:** `TransactionResponse`. **Error:** 404.

---

### `DELETE /api/v1/transactions/{transaction_id}`

**Status:** 204 No Content. Soft-delete.

**Error responses:** 404.

---

### `POST /api/v1/transactions/{transaction_id}/restore`

Restore soft-deleted transaction.

**Response 200:** `TransactionResponse`

**Error responses:** 400 not deleted; 404 not found.

---

## 14. Documents Endpoints

**Prefix:** `/api/v1/documents`
**Auth:** `require_viewer` (router-level dependency)

Supports soft-delete. File storage backend is not yet implemented — metadata is persisted but file content is not stored.

---

### `GET /api/v1/documents/`

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | integer | 1 | |
| `page_size` | integer | 20 | Max 100 |
| `type` | string | — | `lease`, `financial`, `legal`, `due_diligence`, `photo`, `other` |
| `property_id` | string | — | |
| `search` | string | — | Full-text on name/description |
| `date_range` | string | — | `all`, `7days`, `30days`, `90days`, `1year` |
| `sort_by` | string | `uploaded_at` | |
| `sort_order` | string | `desc` | |

**Response 200** (`DocumentListResponse`): `items`, `total`, `page`, `page_size`.

---

### `GET /api/v1/documents/stats`

**Response 200** (`DocumentStats`): `total_documents`, `total_size` (bytes), `by_type` (dict), `recent_uploads` (count, last 30 days).

---

### `GET /api/v1/documents/{document_id}`

Returns 404 if soft-deleted.

**Response 200:** `DocumentResponse`

---

### `POST /api/v1/documents/`

Create document metadata record (no file content).

**Request body** (`DocumentCreate`): `name`, `type`, `url`, `file_path` (required); other fields optional.

**Response 201:** `DocumentResponse`

---

### `POST /api/v1/documents/upload`

Upload a document with file validation.

**Allowed types and size limits:**

| Extension | Magic bytes | Max size |
|-----------|-------------|---------|
| `.xlsx`, `.xlsm` | `PK\x03\x04` | 50 MB |
| `.xls` | `\xd0\xcf\x11\xe0` | 50 MB |
| `.pdf` | `%PDF` | 25 MB |
| `.csv` | (any) | 10 MB |
| `.docx` | `PK\x03\x04` | 25 MB |

**Form params (multipart/form-data):**

| Param | Type | Required |
|-------|------|----------|
| `file` | UploadFile | Yes |
| `type` | string | No (default `other`) |
| `property_id` | string | No |
| `property_name` | string | No |
| `description` | string | No |
| `tags` | string | No — comma-separated |
| `uploaded_by` | string | No |

**Response 200** (`DocumentUploadResponse`): `document` (DocumentResponse) + `message`.

**Error responses:** 422 on validation failure (invalid type, size exceeded, magic bytes mismatch).

---

### `GET /api/v1/documents/{document_id}/download`

Always returns `501 Not Implemented` — storage backend not yet configured.

---

### `PUT /api/v1/documents/{document_id}`

Full metadata update. Returns 404 if soft-deleted.

**Response 200:** `DocumentResponse`

---

### `PATCH /api/v1/documents/{document_id}`

Partial metadata update.

**Response 200:** `DocumentResponse`

---

### `DELETE /api/v1/documents/{document_id}`

**Status:** 204 No Content. Soft-delete via `document_crud.soft_delete()`. Returns 404 if already deleted.

---

### `GET /api/v1/documents/property/{property_id}`

**Note:** Route conflict with `/{document_id}` — see Issues section.

**Path param:** `property_id` (string).

**Query params:** `page`, `page_size`.

**Response 200:** `DocumentListResponse`

---

## 15. Users Endpoints

**Prefix:** `/api/v1/users`
**Auth:** Varies per endpoint

**Implementation note:** All user endpoints operate on a module-level in-memory `DEMO_USERS` list. The database session is injected but unused. Changes do not persist across process restarts. See Issues section.

---

### `GET /api/v1/users/`

**Auth:** `require_admin`

**Query params:** `page`, `page_size`, `role`, `department`, `is_active`.

**Response 200** (`UserListResponse`): `items`, `total`, `page`, `page_size`.

`UserResponse` fields: `id`, `email`, `full_name`, `role`, `department`, `is_active`, `is_verified`, `email_notifications`, `created_at`, `updated_at`.

---

### `GET /api/v1/users/{user_id}`

**Auth:** `get_current_user` (self or admin)

Returns 403 if a non-admin requests another user's profile.

**Response 200:** `UserResponse`

**Error responses:** 403 not self/admin; 404 not found.

---

### `POST /api/v1/users/`

**Auth:** `require_admin`
**Status:** 201 Created

**Request body** (`UserCreate`): `email`, `full_name`, `role`, `password` (bcrypt-hashed server-side), `department` (optional).

**Error responses:** 400 email already registered.

---

### `PUT /api/v1/users/{user_id}`

**Auth:** `get_current_user` (self or admin)

Non-admin users cannot modify: `role`, `is_active`, `is_verified`.

**Error responses:** 400 email in use; 403 restricted field or not self/admin; 404 not found.

---

### `DELETE /api/v1/users/{user_id}`

**Auth:** `require_admin`
**Status:** 204 No Content

Sets `is_active = false` in memory. Cannot deactivate own account.

**Error responses:** 400 self-deactivation; 404 not found.

---

### `POST /api/v1/users/{user_id}/verify`

**Auth:** `require_admin`

Sets `is_verified = true` in memory.

**Response 200:** `{"message": "User {id} verified successfully"}`

**Error responses:** 404 not found.

---

## 16. Exports Endpoints

**Prefix:** `/api/v1/exports`
**Auth:** `require_analyst` (router-level dependency)

All endpoints return `StreamingResponse`.

---

### `GET /api/v1/exports/properties/excel`

**Query params:** `property_type`, `market`, `include_analytics` (bool, default true).

**Response:** `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`; `Content-Disposition: attachment; filename=properties_export_YYYYMMDD_HHMMSS.xlsx`

**Error responses:** 404 no matching properties; 500 openpyxl error.

---

### `GET /api/v1/exports/deals/excel`

**Query params:** `stage`, `deal_type`, `include_pipeline` (bool, default true).

**Response:** Excel file download. Filename: `deals_export_YYYYMMDD_HHMMSS.xlsx`

**Error responses:** 404 no matching deals.

---

### `GET /api/v1/exports/analytics/excel`

**Query params:** `time_period` (`mtd`, `qtd`, `ytd`, `1y`, `all`; default `ytd`).

**Note:** Uses hardcoded mock portfolio data in the analytics sections (not live DB values).

**Response:** Multi-sheet Excel. Filename: `analytics_report_YYYYMMDD_HHMMSS.xlsx`

---

### `GET /api/v1/exports/properties/{property_id}/pdf`

**Query params:** `include_analytics` (bool, default true).

**Response:** `application/pdf`; filename: `property_report_{id}_YYYYMMDD.pdf`

**Error responses:** 404 not found; 501 missing reportlab library; 500 generation error.

---

### `GET /api/v1/exports/deals/{deal_id}/pdf`

**Query params:** `include_property` (bool, default true).

**Response:** PDF file. Filename: `deal_report_{id}_YYYYMMDD.pdf`

**Error responses:** 404 not found; 501 missing library; 500 generation error.

---

### `GET /api/v1/exports/portfolio/pdf`

**Query params:** `time_period` (default `ytd`).

Fetches live deals and properties (up to 1000 each). Analytics section uses partially hardcoded values.

**Response:** Multi-section PDF. Filename: `portfolio_report_YYYYMMDD.pdf`

**Error responses:** 501 missing library; 500 generation error.

---

## 17. Extraction Endpoints

**Prefix:** `/api/v1/extraction`
**Minimum auth:** `require_analyst` (GET); `require_manager` (POST trigger endpoints)

Sub-router split across six files: `extract.py`, `status.py`, `filters.py`, `grouping.py`, `monitor.py`, `scheduler.py`.

---

### `POST /api/v1/extraction/run`

**Auth:** `require_manager`

Trigger a SharePoint extraction run.

---

### `POST /api/v1/extraction/run/local`

**Auth:** `require_manager`

Trigger a local file extraction run (reads from configured local path).

---

### `GET /api/v1/extraction/runs`

**Auth:** `require_analyst`

Paginated list of extraction runs.

---

### `GET /api/v1/extraction/runs/{run_id}`

**Auth:** `require_analyst`

Get details of a specific run: status, file counts, start/completion time.

---

### `GET /api/v1/extraction/runs/{run_id}/values`

**Auth:** `require_analyst`

Paginated list of `ExtractedValue` rows for a specific run.

---

### `GET /api/v1/extraction/values`

**Auth:** `require_analyst`

Query extracted values by `property_id` and/or `field_name`.

---

### `GET /api/v1/extraction/filter/candidates`

**Auth:** `require_manager`

List candidate Excel files from the configured local or SharePoint path.

---

### `GET /api/v1/extraction/grouping/groups`

**Auth:** `require_analyst`

List file groups identified by the grouping pipeline.

---

### `POST /api/v1/extraction/grouping/run`

**Auth:** `require_manager`

Run a grouping pipeline phase.

---

### `GET /api/v1/extraction/monitor/status`

**Auth:** `require_analyst`

Current file-change monitor status (enabled/disabled, last check time).

---

### `POST /api/v1/extraction/monitor/toggle`

**Auth:** `require_manager`

Enable or disable the file monitor.

---

### `GET /api/v1/extraction/scheduler/status`

**Auth:** `require_analyst`

Daily extraction scheduler status.

---

### `POST /api/v1/extraction/scheduler/toggle`

**Auth:** `require_manager`

Enable or disable scheduled extraction.

---

## 18. Monitoring Endpoints

**Prefix:** `/api/v1/monitoring`
**Auth:** `require_admin` (router-level dependency — see Issues section for liveness/readiness probe conflict)

---

### `GET /api/v1/monitoring/metrics`

**Response:** `text/plain` — Prometheus exposition format. Metrics: `http_requests_total`, `http_request_duration_seconds`, `app_info` gauge, DB connection pool counters.

---

### `GET /api/v1/monitoring/health/live`

Kubernetes liveness probe. Does not check dependencies.

**Response 200:** `{"status": "alive", "timestamp": "2026-03-10T09:00:00Z"}`

---

### `GET /api/v1/monitoring/health/ready`

Kubernetes readiness probe. Checks database connectivity.

**Response 200:** `{"status": "ready", "database": true, "timestamp": "..."}`

**Response 503:** When database ping fails.

---

### `GET /api/v1/monitoring/health/detailed`

Comprehensive health: app info, DB status, Redis status, system metrics from `collector_registry`.

**Response 200:**

```json
{
  "status": "healthy",
  "timestamp": "...",
  "application": {"name": "...", "version": "2.0.0", "environment": "development", "debug": true},
  "checks": {
    "database": {"status": "healthy", "type": "postgresql"},
    "redis": {"status": "not_configured"}
  },
  "metrics": {...}
}
```

---

### `GET /api/v1/monitoring/pool-stats`

Connection pool statistics for SQLAlchemy async engine, sync engine, and Redis connection pools.

**Response 200:**

```json
{
  "async_pool": {"size": 10, "checked_out": 2, "overflow": 0, "checked_in": 8},
  "sync_pool": {"size": 5, "checked_out": 0, "overflow": 0, "checked_in": 5},
  "redis_pools": {"cache": {...}, "token_blacklist": {...}},
  "summary": {"async_utilization_pct": 20.0}
}
```

---

### `GET /api/v1/monitoring/stats`

System metrics snapshot (CPU, memory, disk).

---

### `GET /api/v1/monitoring/info`

Non-sensitive application configuration.

**Response 200:**

```json
{
  "name": "B&R Capital Dashboard API",
  "version": "2.0.0",
  "environment": "development",
  "debug": true,
  "server": {"host": "0.0.0.0", "port": 8000, "workers": 1},
  "features": {"websocket": true, "ml_predictions": true, "email_notifications": false, "redis_cache": false},
  "api": {"version": "v1", "docs_enabled": true}
}
```

---

## 19. WebSocket Connections

**Endpoint:** `ws://<host>/api/v1/ws/{channel}`

**Auth:** JWT access token passed as `?token=<access_token>` query parameter. Anonymous connections (no token) are accepted but `user_id` is `None`.

### Available Channels

| Channel | Events |
|---------|--------|
| `deals` | Deal stage changes, create/update/delete/restore |
| `extraction` | Extraction run progress |
| `notifications` | Per-user notifications |
| `properties` | Property data updates |
| `analytics` | Analytics report readiness |

### Connection Lifecycle

On connect, server sends:

```json
{"type": "connected", "connection_id": "uuid", "channels": ["deals"], "user_id": 1}
```

On connection limit exceeded, server sends then closes:

```json
{"type": "error", "message": "Connection limit exceeded"}
```

Close code: `1008`.

### Heartbeat Protocol

Server sends periodically:

```json
{"type": "ping", "timestamp": "2026-03-10T09:00:00Z"}
```

Client must respond:

```json
{"type": "pong"}
```

### Client → Server Message Types

| `type` | Fields | Effect |
|--------|--------|--------|
| `pong` | — | Acknowledges heartbeat |
| `subscribe` | `channel: string` | Subscribe to additional channel; server confirms with `{"type": "subscribed", "channel": "..."}` |
| `unsubscribe` | `channel: string` | Leave a channel; server confirms with `{"type": "unsubscribed", "channel": "..."}` |

Unknown message types receive: `{"type": "error", "message": "Unknown message type: ..."}`.

### Server → Client Event Types

| `type` | Channel | Payload notes |
|--------|---------|--------------|
| `deal_update` | `deals` | `action`: `created`/`updated`/`stage_changed`/`deleted`/`restored`; `data`: deal ID and relevant fields |
| `extraction_progress` | `extraction` | Run status and progress |
| `notification` | `notifications` | Per-user notification data |
| `error` | any | Error message string |

**Deal update example (stage change):**

```json
{
  "type": "deal_update",
  "action": "stage_changed",
  "data": {
    "deal_id": 5,
    "old_stage": "initial_review",
    "new_stage": "active_review"
  }
}
```

---

## 20. Health Endpoints

### `GET /`

**Auth:** None

```json
{"name": "B&R Capital Dashboard API", "version": "2.0.0", "status": "running", "docs": "/api/docs"}
```

---

### `GET /api/v1/health`

**Auth:** None. Legacy load balancer probe.

```json
{"status": "ok"}
```

---

### `GET /api/v1/health/status`

**Auth:** None. Detailed health check covering database, Redis, SharePoint config, external API keys, disk space, and uptime.

---

## 21. Issues Found

The following issues were identified during documentation review. They represent schema mismatches, missing error handlers, incorrect authorization, and remaining N+1 patterns.

---

### Issue 1: Users endpoints backed by in-memory demo data, not the database

**File:** `backend/app/api/v1/endpoints/users.py`

All user endpoints operate on a module-level `DEMO_USERS` list. The database session is injected but never used. `POST /users/`, `PUT /users/{id}`, and `DELETE /users/{id}` mutate only the in-memory list — changes are lost on process restart. There is no actual persistent user management.

**Impact:** Critical for production. User creation, updates, and deactivation do not persist.

---

### Issue 2: Architecture doc says `POST /api/v1/deals/compare`; implementation is `GET`

**Files:** `backend/app/api/v1/endpoints/deals.py` (line ~506); `backend-architecture.md`

The endpoint is implemented as `GET /api/v1/deals/compare?ids=1,2,3`. The architecture reference document incorrectly lists it as `POST`. The GET implementation is appropriate for the use case (no body required).

---

### Issue 3: `PUT /api/v1/deals/{deal_id}` and `PATCH /api/v1/deals/{deal_id}` require `require_manager`, not `require_analyst`

**File:** `backend/app/api/v1/endpoints/deals.py` (lines 793, 869)

The architecture reference lists these as `analyst` auth. The actual code uses `require_manager`. Callers with `analyst` role will receive 403.

---

### Issue 4: `PUT` and `PATCH` on deals have identical behavior — true PUT semantics are not implemented

**File:** `backend/app/api/v1/endpoints/deals.py`

Both `update_deal` (PUT) and `patch_deal` (PATCH) accept `DealUpdate` (all fields optional) and both use `model_dump(exclude_unset=True)`. This means PUT behaves as a partial update, not a full replacement. Clients expecting PUT to null out omitted fields will encounter unexpected behavior.

---

### Issue 5: Proforma returns endpoint matches by `property_name` string, not `property_id`

**File:** `backend/app/api/v1/endpoints/deals.py` (line ~1562)

`GET /deals/{deal_id}/proforma-returns` queries `ExtractedValue.property_name` against the deal name. If the deal name doesn't exactly match the stored `property_name` (even after the base-name regex stripping for `(City, ST)` suffix), no data is returned. A join through `property_id` would be more reliable.

---

### Issue 6: `POST /api/v1/properties/{property_id}/activities` returns HTTP 200, not 201

**File:** `backend/app/api/v1/endpoints/properties.py` (line 748)

The `create_property_activity` endpoint does not set `status_code=201`. It returns 200, inconsistent with all other create endpoints in the codebase.

---

### Issue 7: `user_name` is always `None` in `PropertyActivityResponse`

**File:** `backend/app/api/v1/endpoints/properties.py` (line 727)

`user_name=None` is hardcoded with comment "Would need join with users table." Clients relying on this field for display will always receive null.

---

### Issue 8: Growth rate fields always return `0.0` or `null`

**Files:** `backend/app/api/v1/endpoints/analytics.py`, `backend/app/api/v1/endpoints/properties.py`

The following fields are hardcoded to `0.0` or `None` with comments noting missing historical data:
- `ytd_noi_growth`, `ytd_rent_growth` (analytics dashboard and property analytics)
- `total_return`, `income_return`, `appreciation_return`, `benchmark_return` (portfolio analytics)
- `cycle_times_days` (deal pipeline analytics — all null)

Historical time-series tracking is not yet implemented.

---

### Issue 9: `GET /api/v1/exports/analytics/excel` uses static mock data

**File:** `backend/app/api/v1/endpoints/exports.py` (lines 183–211)

The analytics Excel export uses a hardcoded `dashboard_metrics` dict (45 properties, $425M value, etc.) instead of querying the live database. The `portfolio_analytics` section is also static.

---

### Issue 10: Transaction DELETE and restore have no auth upgrade over router-level `require_viewer`

**File:** `backend/app/api/v1/endpoints/transactions.py`

`delete_transaction` and `restore_transaction` are protected only by the router-level `require_viewer` — any authenticated user (including viewers) can soft-delete and restore financial transactions. Compare to deals which require `require_manager` for these operations.

---

### Issue 11: `GET /api/v1/documents/property/{property_id}` route is shadowed by `/{document_id}`

**File:** `backend/app/api/v1/endpoints/documents.py` (line 394)

The route `/property/{property_id}` is registered after `/{document_id}`. FastAPI matches `/{document_id}` first for requests to `/documents/property/123` because the string `"property"` satisfies the `{document_id}` path parameter. Requests to this endpoint likely result in a 404 (no document with ID "property"). The sub-resource route should be defined before the wildcard route.

---

### Issue 12: Document upload does not require elevated role

**File:** `backend/app/api/v1/endpoints/documents.py`

`POST /documents/upload` inherits only `require_viewer` from the router. Any authenticated viewer can upload documents (up to 50 MB Excel files). Should require at minimum `analyst`.

---

### Issue 13: Monitoring liveness/readiness probes are guarded by `require_admin`

**File:** `backend/app/api/v1/endpoints/monitoring.py` (line 25)

`router = APIRouter(dependencies=[Depends(require_admin)])` applies admin authentication to all monitoring routes, including `/health/live` and `/health/ready`. Kubernetes liveness and readiness probes cannot authenticate with a Bearer token and will receive 401. This will cause the pod to be continuously marked unhealthy. These two probe endpoints must be exempted from the router-level auth dependency.

**Impact:** Critical for production Kubernetes deployment.

---

### Issue 14: WebSocket token validation does not check the token blacklist

**File:** `backend/app/api/v1/endpoints/ws.py` (lines 24–43)

`_authenticate_token()` decodes the JWT and extracts `user_id`, but does not call `token_blacklist.is_blacklisted(jti)`. A user who has logged out (token blacklisted) can still establish WebSocket connections using the revoked access token until the token's natural 30-minute expiry.

---

### Issue 15: Remaining N+1 patterns

The following cases have not been fully batched:

- `GET /api/v1/exports/portfolio/pdf`: iterates all properties and deals with separate `get_multi_filtered` calls; does not call `enrich_financial_data_batch` before export — financial data in the PDF may be incomplete.
- `GET /api/v1/deals/{deal_id}` (single deal): calls `_enrich_deals_with_extraction` with a list of one, executing the full 2-query batch for a single item. Not harmful, but slightly wasteful.
- `GET /api/v1/properties/{property_id}/activities`: `PropertyActivityResponse.user_name` is always null — resolving display names would require a join or a secondary user lookup per activity.

---

*End of Backend API Reference — Generated: 2026-03-10*
