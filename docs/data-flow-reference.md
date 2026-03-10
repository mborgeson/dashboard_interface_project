# Data Flow Reference

Generated: 2026-03-10

Complete end-to-end data flow traces for every major user action in the B&R Capital Dashboard.

---

## Table of Contents

1. [Cross-Cutting Concerns](#cross-cutting-concerns)
2. [Auth Login](#1-auth-login)
3. [Token Refresh](#2-token-refresh)
4. [Deal List (Kanban Board)](#3-deal-list-kanban-board)
5. [Deal Detail](#4-deal-detail)
6. [Deal Creation](#5-deal-creation)
7. [Property List (Dashboard)](#6-property-list-dashboard)
8. [Property Detail](#7-property-detail)
9. [Deal Comparison](#8-deal-comparison)
10. [Extraction Run](#9-extraction-run)
11. [Grouping Pipeline](#10-grouping-pipeline)
12. [Market Data](#11-market-data)
13. [Report Generation](#12-report-generation)
14. [WebSocket Subscription](#13-websocket-subscription)
15. [Issues Found](#issues-found)

---

## Cross-Cutting Concerns

### API Client (Single Fetch Client)

All frontend HTTP traffic flows through one client: `src/lib/api/client.ts`. The legacy axios client (`src/lib/api.ts`) is deprecated and no longer extended. The fetch client provides:

- **Bearer token injection**: Reads `access_token` from `localStorage` on every request.
- **ETag caching**: Maintains an in-memory `Map<URL, {etag, data}>`. On GET requests, sends `If-None-Match`. On 304 responses, returns cached data without parsing the empty body.
- **401 auto-clear**: On any 401 response, removes both tokens from `localStorage` and dispatches a `auth:unauthorized` CustomEvent. The `authStore` listens for this event and clears its Zustand state.
- **Content-Type handling**: Detects `URLSearchParams` bodies (for OAuth2 form-encoded login) and skips setting `Content-Type: application/json`.

### Backend Middleware Chain

Requests traverse middleware outermost-first (last-registered executes first in Starlette):

```
Request
  -> RequestIDMiddleware        (assigns X-Request-ID UUID4, sets ContextVar)
  -> OriginValidationMiddleware (rejects POST/PUT/PATCH/DELETE from unknown origins)
  -> ErrorHandlerMiddleware     (catches exceptions, returns structured JSON with request_id)
  -> SecurityHeadersMiddleware  (X-Content-Type-Options, CSP, HSTS, Cache-Control)
  -> ETagMiddleware             (SHA-256 body hash, 304 on If-None-Match match)
  -> RateLimitMiddleware        (sliding window, per-path rules, Redis or memory backend)
  -> MetricsMiddleware          (request duration, status code counters)
  -> CORSMiddleware             (allow_origins from settings, exposes X-Request-ID + ETag)
  -> FastAPI Router
```

### Error Response Format

All unhandled exceptions are caught by `ErrorHandlerMiddleware` and returned as:

```json
{
  "detail": "Human-readable error message",
  "request_id": "uuid4-correlation-id",
  "type": "database_error | validation_error | permission_error | value_error | internal_error"
}
```

Exception mapping: `SQLAlchemyError` -> 500, `ValidationError` -> 422, `PermissionError` -> 403, `ValueError` -> 400, generic `Exception` -> 500. `HTTPException` is re-raised to FastAPI's built-in handler.

### Caching Layer

`backend/app/core/cache.py` provides a `CacheService` with Redis preferred and in-memory fallback:

- **Key prefix**: `dashboard:` (e.g., `dashboard:portfolio_summary`, `dashboard:property_dashboard_list`)
- **TTL tiers**: `DEFAULT_TTL` (1h), `SHORT_TTL` (5min), `LONG_TTL` (2h)
- **Invalidation**: Pattern-based (`invalidate_properties()` clears `property_*`, `portfolio_summary*`, `analytics_dashboard*`). Mutations (create/update/delete) call the relevant invalidation method.

### ETag/304 Conditional Requests

Operates at two levels:

1. **Backend** (`backend/app/middleware/etag.py`): For every GET response with a body, computes `SHA-256(body)` as a quoted ETag. If `If-None-Match` from the client matches, returns 304 with no body.
2. **Frontend** (`src/lib/api/client.ts`): Stores `{etag, data}` per URL in a Map. On GET, attaches `If-None-Match`. On 304, returns the cached `data` without parsing.

Net effect: unchanged data is never re-transferred. The backend still queries the DB and serializes the response (needed to compute the hash), but the response body is not sent over the wire.

### Pagination

Two pagination strategies are available on list endpoints:

1. **Offset-based** (default): `page` + `page_size` query params. Returns `{items, total, page, page_size}`.
2. **Cursor-based** (alternative): Keyset pagination via `/cursor` sub-endpoints. Encodes `(sort_value, id)` as opaque base64 cursor. Returns `{items, next_cursor, prev_cursor, has_more, total}`. No offset scans -- efficient for large tables. Uses `limit + 1` fetch to detect `has_more`.

Both strategies respect soft-delete filters and support arbitrary SQLAlchemy conditions.

### Soft Delete

Models with `SoftDeleteMixin` (`Deal`, `Transaction`, `ReportTemplate`, etc.) are filtered by `is_deleted = False` by default. All CRUD methods accept `include_deleted=False`. The `remove()` method sets `is_deleted=True` + `deleted_at=now()` instead of issuing a SQL DELETE. The `restore()` method reverses soft-delete.

### N+1 Query Fix Pattern

List endpoints that need financial enrichment use batch methods (e.g., `enrich_financial_data_batch`) that issue 2 bulk queries (base fields + YEAR_N fields) for ALL properties needing enrichment, instead of 2-3 queries per property. Results are partitioned by property name in Python and delegated to per-property enrichment logic.

---

## 1. Auth Login

**User action**: Enter email + password on login form, click Login.

### Frontend Flow

```
LoginForm.handleSubmit()
  -> useAuthStore.login(email, password)
       -> apiClient.post('/auth/login', URLSearchParams{username, password})
            // Content-Type: application/x-www-form-urlencoded (auto-detected by fetch client)
       <- {access_token, refresh_token, token_type, expires_in}
       -> localStorage.setItem('access_token', ...)
       -> localStorage.setItem('refresh_token', ...)
       -> apiClient.get('/auth/me')
       <- {id, email, role, full_name, is_active}
       -> Zustand set({user, accessToken, refreshToken, isAuthenticated: true, isLoading: false})
  -> React Router redirects to /dashboard (or stored redirect target)
  -> usePrefetchDashboard() warms React Query cache
```

### Backend Flow

```
POST /api/v1/auth/login
  Middleware chain: RequestID -> Origin -> ErrorHandler -> Security -> ETag -> RateLimit -> Metrics -> CORS
  Rate limit: 5 requests / 60 seconds on /api/v1/auth/login (rl:auth prefix)

  -> OAuth2PasswordRequestForm(username=email, password)
  -> user_crud.authenticate(db, email, password)
       // SELECT * FROM users WHERE email=?
       // bcrypt.verify(password, user.hashed_password)
  -> if db_user found and is_active:
       -> user_crud.update_last_login(db, user)  // UPDATE users SET last_login=now()
       -> create_access_token(subject=str(user_id), additional_claims={role})
            // jose.jwt.encode, HS256, exp=ACCESS_TOKEN_EXPIRE_MINUTES, jti=uuid4
       -> create_refresh_token(subject=str(user_id))
            // type="refresh", exp=REFRESH_TOKEN_EXPIRE_DAYS, jti=uuid4
       <- Token{access_token, refresh_token, token_type="bearer", expires_in}
  -> if db_user found but not is_active: 403 "User account is disabled"
  -> if no db_user: try demo users (non-production only, passwords from env vars)
  -> if neither: 401 "Incorrect email or password"
```

### Data stores touched

| Store | Operation |
|-------|-----------|
| PostgreSQL `users` | SELECT (authenticate), UPDATE (last_login) |
| localStorage | SET access_token, refresh_token |
| Zustand authStore | SET user, tokens, isAuthenticated |
| React Query cache | Prefetch: market overview, interest rates, report templates, properties |

---

## 2. Token Refresh

**Trigger**: Access token expires or is about to expire.

### Frontend Flow (current behavior)

```
apiClient.request() receives 401
  -> localStorage.removeItem('access_token')
  -> localStorage.removeItem('refresh_token')
  -> window.dispatchEvent(CustomEvent('auth:unauthorized'))
  -> authStore listener fires:
       set({user: null, accessToken: null, refreshToken: null, isAuthenticated: false})
  -> ProtectedRoute detects isAuthenticated=false -> redirect to /login
```

Note: The frontend does NOT currently call `POST /auth/refresh`. On 401, state is cleared and the user must re-login. The refresh_token stored in localStorage is unused after initial login. The backend endpoint is fully implemented and ready for frontend integration.

### Backend Flow (POST /auth/refresh -- available but not called by frontend)

```
POST /api/v1/auth/refresh
  Rate limit: separate limit from login (RATE_LIMIT_REFRESH_REQUESTS per window)
  Body: {refresh_token: "eyJ..."}

  -> decode_token(refresh_token)
  -> Verify payload.type == "refresh" (reject access tokens used as refresh)
  -> Check token_blacklist.is_user_revoked(user_id)
       // Redis: GET revoked:user:{user_id}
       // If revoked: 401 "All sessions have been revoked"
  -> Check token_blacklist.is_blacklisted(jti)
       // Redis: GET blacklist:{jti}
       // If found: REPLAY ATTACK DETECTED
       //   -> token_blacklist.revoke_user_tokens(user_id, ttl=REFRESH_TOKEN_EXPIRE_DAYS*86400)
       //   -> 401 "Refresh token reuse detected. All sessions have been revoked for security."
  -> token_blacklist.add(old_jti, remaining_ttl)  // blacklist used refresh token
  -> create_access_token(subject=user_id)          // new access token
  -> create_refresh_token(subject=user_id)         // new refresh token with new jti
  <- Token{access_token, refresh_token, token_type, expires_in}
```

### Security properties

- **Rotation**: Each refresh issues a NEW refresh token and blacklists the old one (one-time use).
- **Replay detection**: Reusing a blacklisted refresh token revokes ALL tokens for the user (nuclear option).
- **Blacklist storage**: Redis with TTL matching token expiry, or in-memory dict fallback.
- **Token type enforcement**: Refresh endpoint rejects access tokens (checks `payload.type == "refresh"`).

---

## 3. Deal List (Kanban Board)

**User action**: Navigate to /deals page.

### Frontend Flow

```
DealsPage renders
  -> useDeals() hook (React Query, staleTime=5min)
       -> apiClient.get('/deals/kanban', {params: {deal_type, assigned_user_id}})
            // ETag: If-None-Match header sent if URL previously cached
       <- KanbanBoardResponse {stages: {stage_name: [Deal]}, total_deals, stage_counts}
       -> Zod schema parse: snake_case -> camelCase transformation
       -> React Query stores in cache
  -> KanbanBoard renders one column per DealStage:
       INITIAL_REVIEW -> ACTIVE_REVIEW -> UNDER_CONTRACT -> CLOSED -> PASSED
  -> Each DealCard shows: name, property, stage, priority, total_units, cap_rate, IRR/MOIC
  -> Drag-and-drop triggers PATCH /deals/{id}/stage
```

### Backend Flow

```
GET /api/v1/deals/kanban?deal_type=acquisition&assigned_user_id=1
  Auth: require_analyst (JWT decode -> user lookup -> role check >= analyst)

  -> cache.get("deal_kanban:{deal_type}:{user_id}")
  -> if cache miss:
       -> deal_crud.get_kanban_data(db, deal_type, assigned_user_id)
            -> SELECT * FROM deals WHERE is_deleted=False [AND deal_type=?] [AND assigned_user_id=?]
               ORDER BY stage_order ASC
            -> Python grouping: {stage.value: [deals]} for each DealStage enum
            -> Returns {stages, total_deals, stage_counts}
       -> Serialize deals to DealResponse list
       -> _enrich_deals_with_extraction(db, deal_responses)
            // Batch query: subquery for latest completed extraction_run per property_id
            // Main query: SELECT extracted_values WHERE property_id IN (...) AND field_name IN (30+ fields)
            //   Fields: TOTAL_UNITS, AVERAGE_UNIT_SF, CURRENT_OWNER, LP_RETURNS_IRR, LEVERED_RETURNS_IRR,
            //           T3_RETURN_ON_COST, PURCHASE_PRICE, EXIT_CAP_RATE, PROPERTY_LATITUDE, etc.
            // Build lookup: {property_id: {field_name: ExtractedValue}}
            // Patch each DealResponse with extracted values
       -> cache.set(key, result, ttl=SHORT_TTL)  // 5 minutes
  <- KanbanBoardResponse
  ETag middleware: SHA-256 hash of serialized JSON body -> ETag header
```

### Data stores touched

| Store | Operation |
|-------|-----------|
| Redis/memory cache | GET kanban key, SET on miss (5min TTL) |
| PostgreSQL `deals` | SELECT with soft-delete filter, ordered by stage_order |
| PostgreSQL `extracted_values` + `extraction_runs` | Batch SELECT for enrichment (single query) |
| React Query cache | SET with staleTime=5min |
| Frontend ETag cache | SET url -> {etag, data} |

---

## 4. Deal Detail

**User action**: Click a deal card to open the detail modal.

### Frontend Flow

```
DealDetailModal opens
  -> useDeal(dealId) hook (React Query)
       -> apiClient.get(`/deals/${dealId}`)
       <- DealResponse with all fields + extraction enrichment
  -> Tabs render:
       Overview: name, property, stage, priority, assigned_user, notes
       Financials: purchase_price, cap_rate, NOI, financing, returns
       Proforma Returns (collapsible, lazy-loaded):
         -> apiClient.get(`/deals/${dealId}/proforma-returns`)
         <- 30 extracted financial fields from latest extraction run
       Activity Feed:
         -> apiClient.get(`/deals/${dealId}/activity`)
         <- Paginated activity log (views, edits, comments, stage changes)
       Watchlist:
         -> apiClient.get(`/deals/${dealId}/watchlist`)
         <- {is_watching: bool}
```

### Backend Flow

```
GET /api/v1/deals/{deal_id}
  Auth: require_analyst
  -> deal_crud.get_with_relations(db, deal_id)
       -> SELECT * FROM deals WHERE id=? AND is_deleted=False
  -> if not found: 404 {detail: "Deal not found", request_id: "...", type: "..."}
  -> Serialize to DealResponse
  -> _enrich_deals_with_extraction(db, [deal_response])
       // Same batch pattern but with single property_id
  <- DealResponse

GET /api/v1/deals/{deal_id}/proforma-returns
  Auth: require_analyst
  -> Fetch deal -> get property_id
  -> SELECT field_name, value_numeric, value_text, confidence, source_cell
     FROM extracted_values
     WHERE property_id=? AND field_name IN (30 proforma fields)
     ORDER BY field_name, created_at DESC
  -> Deduplicate by field_name (latest value wins)
  <- {property_name, extraction_run_id, fields: [{name, value_numeric, value_text, ...}]}

GET /api/v1/deals/{deal_id}/activity
  Auth: require_analyst
  -> deal_activity.get_by_deal(db, deal_id, skip, limit)
  <- DealActivityListResponse {activities, total, page, page_size}
```

### Data stores touched

| Store | Operation |
|-------|-----------|
| PostgreSQL `deals` | SELECT by id |
| PostgreSQL `extracted_values` | SELECT for enrichment + proforma returns |
| PostgreSQL `deal_activities` | SELECT for activity feed |
| PostgreSQL `watchlist` | SELECT for watch status |

---

## 5. Deal Creation

**User action**: Click "New Deal", fill form, submit.

### Frontend Flow

```
CreateDealForm.handleSubmit()
  -> apiClient.post('/deals/', {name, property_id, stage, deal_type, priority, ...})
       // Content-Type: application/json
  <- DealResponse (201 Created)
  -> queryClient.invalidateQueries(['deals'])  // refetch kanban + list
  -> Toast notification "Deal created successfully"
  -> Close modal / navigate to deal detail
```

### Backend Flow

```
POST /api/v1/deals/
  Auth: require_manager (role >= manager required for mutations)
  Middleware: OriginValidationMiddleware validates Origin header against CORS_ORIGINS

  -> DealCreate Pydantic validation
       name: required, max_length=200
       stage: DealStage enum, default=INITIAL_REVIEW
       deal_type, priority, property_id, assigned_user_id: optional
  -> deal_crud.create(db, obj_in=deal_data)
       -> db_obj = Deal(**validated_data)
       -> db.add(db_obj)
       -> db.commit()
       -> db.refresh(db_obj)  // returns full row with server defaults (id, created_at, version)
  -> activity_log_crud.create(db, ActivityLogCreate{
       action=DEAL_CREATED, resource_type="deal", resource_id=deal.id,
       user_id=current_user.id, details={name, stage}
     })
  -> cache.invalidate_deals()
       // Deletes: dashboard:deal_*, dashboard:analytics_dashboard*
  -> WebSocket broadcast to "deals" channel:
       {type: "deal_created", deal_id, name, stage}
  <- DealResponse (201)
```

### Optimistic locking (for updates)

Deal updates support optimistic locking via `version` column:

```
PUT /api/v1/deals/{deal_id}
  -> deal_crud.update_optimistic(db, deal_id, expected_version, update_data)
       -> UPDATE deals SET version=expected_version+1, ... WHERE id=? AND version=expected_version
       -> if rowcount=0: None (stale version -- concurrent edit detected)
       -> 409 "Deal was modified by another user"
```

### Data stores touched

| Store | Operation |
|-------|-----------|
| PostgreSQL `deals` | INSERT |
| PostgreSQL `activity_logs` | INSERT |
| Redis/memory cache | DELETE deal_* + analytics_dashboard* patterns |
| WebSocket manager | Broadcast to "deals" channel subscribers |
| React Query cache | Invalidate ['deals'] queries |

---

## 6. Property List (Dashboard)

**User action**: Navigate to /properties (dashboard home showing property cards/grid).

### Frontend Flow

```
PropertiesPage renders
  -> useProperties() hook (React Query)
       -> apiClient.get('/properties/dashboard')
            // ETag: If-None-Match from previous response
       <- {properties: [FrontendProperty], total: N}
       -> Each property is a nested object:
            {id, name, address, city, state, market, totalUnits, yearBuilt,
             purchasePrice, capRate, noi, occupancyRate, avgRentPerUnit,
             financialData: {
               acquisition: {purchasePrice, pricePerUnit, totalAcquisitionBudget},
               financing: {loanAmount, ltv, interestRate, loanTermMonths, annualDebtService},
               returns: {leveredIrr, leveredMoic, unleveredIrr, unleveredMoic, lpIrr, lpMoic},
               operations: {totalRevenueYear1, noiYear1, totalExpensesYear1, occupancy, avgRentPerUnit},
               expenses: {realEstateTaxes, propertyInsurance, staffingPayroll, ...},
               operationsByYear: {"1": {grossPotentialRevenue, noi, expenses: {...}}, "2": {...}, ...}
             }}
       -> Zod parse + cache
  -> usePortfolioSummary()
       -> apiClient.get('/properties/summary')
       <- {totalProperties, totalUnits, totalValue, totalNOI, averageOccupancy, averageCapRate, portfolioIRR}
  -> Dashboard renders: KPI cards (summary) + property grid/table
```

### Backend Flow

```
GET /api/v1/properties/dashboard
  Auth: require_analyst

  -> cache.get("property_dashboard_list")
  -> if cache hit: return cached (up to 2h old)
  -> if cache miss:
       -> property_crud.get_multi_filtered(db, skip=0, limit=200, order_by="name", order_desc=False)
            -> SELECT * FROM properties ORDER BY name ASC LIMIT 200
       -> property_crud.count_filtered(db)
            -> SELECT COUNT(*) FROM properties
       -> property_crud.enrich_financial_data_batch(db, items)
            N+1 FIX -- two bulk queries instead of 2-3 per property:

            Query 1 (base fields):
              SELECT property_name, field_name, value_numeric, value_text
              FROM extracted_values
              WHERE (property_name IN (...) OR property_name LIKE '...%')
                AND is_error=False
                AND field_name IN ('PURCHASE_PRICE', 'TOTAL_UNITS', 'YEAR_BUILT', 'GOING_IN_CAP_RATE',
                    'NOI', 'EFFECTIVE_GROSS_INCOME', 'LEVERED_RETURNS_IRR', ... 30+ fields)
              ORDER BY property_name, field_name, created_at DESC

            Query 2 (annual cashflow fields):
              SELECT property_name, field_name, value_numeric
              FROM extracted_values
              WHERE (property_name IN (...) OR property_name LIKE '...%')
                AND is_error=False
                AND field_name LIKE '%_YEAR_%'
              ORDER BY property_name, created_at DESC

            Python processing:
              -> Partition rows by property name (fuzzy match: exact, short name, starts-with)
              -> For each property needing enrichment:
                   -> Backfill direct columns (purchase_price, total_units, year_built, cap_rate, noi, ...)
                   -> Build financial_data JSON: acquisition, financing, returns, operations
                   -> Build operationsByYear from YEAR_N fields (regex match PREFIX_YEAR_N)
                   -> Build expenses from per-unit fields * total_units (or YEAR_1 expenses)
                   -> COMMIT changes to property row (lazy persistence for future cache hits)

       -> [to_frontend_property(p) for p in items]
            // Transforms SQLAlchemy model -> nested dict matching frontend Property type
       -> cache.set("property_dashboard_list", result, ttl=LONG_TTL)  // 2 hours
  <- {properties: [...], total: N}
  ETag middleware: SHA-256 of serialized JSON body

GET /api/v1/properties/summary
  Auth: require_analyst
  -> cache.get("portfolio_summary")
  -> if miss:
       -> Fetch all properties + batch enrich
       -> Aggregate: totalProperties, totalUnits, totalValue, totalNOI
       -> Compute: averageOccupancy, averageCapRate (from annual NOI / purchase price)
       -> Compute: portfolioIRR, portfolioCashOnCash (equity-weighted from financial_data.returns)
       -> cache.set("portfolio_summary", result, ttl=LONG_TTL)
  <- Portfolio summary JSON
```

### Cursor-based pagination alternative

```
GET /api/v1/properties/cursor?cursor=abc&limit=20&direction=next&sort_by=name&sort_order=asc
  -> Decode cursor -> (sort_value, id)
  -> Build keyset WHERE clause (no OFFSET scan):
       if order_desc and direction=next: WHERE (sort_col < cursor_val) OR (sort_col = cursor_val AND id < cursor_id)
  -> Fetch limit+1 rows (detect has_more)
  -> Encode next_cursor from last item, prev_cursor from first item
  <- {items, next_cursor, prev_cursor, has_more, total}
```

### Data stores touched

| Store | Operation |
|-------|-----------|
| Redis/memory cache | GET then SET on miss (2h TTL) |
| PostgreSQL `properties` | SELECT + COUNT |
| PostgreSQL `extracted_values` | 2 bulk SELECTs for batch enrichment |
| PostgreSQL `properties` | UPDATE per property (backfill columns, COMMIT each) |
| Frontend ETag cache | Store etag + response body per URL |
| React Query cache | SET with staleTime |

---

## 7. Property Detail

**User action**: Click a property card to view full detail.

### Frontend Flow

```
PropertyDetailPage / PropertyDetailModal
  -> useProperty(propertyId) hook (React Query)
       -> apiClient.get(`/properties/dashboard/${propertyId}`)
       <- FrontendProperty (nested JSON with full financialData)
  -> Tabs:
       Overview: name, address, city, state, market, totalUnits, yearBuilt, totalSf
       Financials: acquisition, financing, returns, operations
       Operations by Year: multi-year cashflow table from operationsByYear dict
       Expenses: breakdown pie chart from expenses dict
  -> usePropertyAnalytics(propertyId)
       -> apiClient.get(`/properties/${propertyId}/analytics`)
       <- {property_id, property_name, data_source, metrics, trends, comparables}
  -> usePropertyActivities(propertyId)
       -> apiClient.get(`/properties/${propertyId}/activities`)
       <- {activities, total, page, page_size}
```

### Backend Flow

```
GET /api/v1/properties/dashboard/{property_id}
  Auth: require_analyst
  -> property_crud.get(db, property_id)
  -> if not found: 404
  -> Check if financial_data needs enrichment:
       if fd is NULL or missing "expenses" or missing "operationsByYear":
         -> property_crud.enrich_financial_data(db, prop)
              // Per-property queries (not batch, since single property)
              // Queries extracted_values for base fields + YEAR_N fields
              // Builds full financial_data JSON + operationsByYear
              // Backfills direct columns
              // COMMITs to property row
  -> to_frontend_property(prop)
  <- Nested frontend Property JSON

GET /api/v1/properties/{property_id}/analytics
  Auth: require_analyst
  -> property_crud.get(db, property_id)
  -> if not found: 404
  -> Query market comparables:
       SELECT AVG(avg_rent_per_unit), AVG(occupancy_rate), AVG(cap_rate), COUNT(id)
       FROM properties
       WHERE market=? AND property_type=? AND id != ?
  -> Build response:
       - metrics: current_rent, occupancy, cap_rate, noi, rent_vs_market ratio
       - trends: single-point (current values only -- no historical time series)
       - comparables: market averages + count
  -> If no real data: return mock fallback with data_source="mock"
  <- Analytics response
```

### Data stores touched

| Store | Operation |
|-------|-----------|
| PostgreSQL `properties` | SELECT by id, possible UPDATE (lazy enrichment) |
| PostgreSQL `extracted_values` | SELECT for enrichment (2 queries, if needed) |
| PostgreSQL `properties` | SELECT for market comparables (AVG aggregates) |
| PostgreSQL `property_activities` | SELECT for activity feed |

---

## 8. Deal Comparison

**User action**: Select 2-5 deals on the kanban board and click "Compare Deals".

### Frontend Flow

```
CompareDealsModal receives selected deal IDs
  -> useCompareDeal(dealIds) hook
       -> apiClient.get('/deals/compare', {params: {ids: "1,2,3"}})
       <- DealComparisonResponse {
            deals: [DealResponse],
            metrics: [MetricComparison],
            summary: ComparisonSummary
          }
  -> Renders side-by-side table:
       Each row = one metric (purchase_price, total_units, cap_rate, NOI, IRR, MOIC, ...)
       Each column = one deal
       Best/worst values highlighted per row
  -> Summary card shows overall best deal and key differences
```

### Backend Flow

```
GET /api/v1/deals/compare?ids=1,2,3
  Auth: require_analyst

  -> Parse comma-separated IDs (validate: 2-5 deals required)
  -> deal_crud.get_by_ids(db, ids=parsed_ids)
       -> SELECT * FROM deals WHERE id IN (1,2,3) AND is_deleted=False
  -> if any ID not found: 404
  -> Serialize to DealResponse list
  -> _enrich_deals_with_extraction(db, deal_responses)
       // Single batch query for all comparison deal property_ids
       // Same subquery pattern: latest completed run per property
  -> Build MetricComparison list:
       For each metric (purchase_price, total_units, cap_rate, noi_per_unit,
                        levered_irr, levered_moic, t3_return_on_cost, exit_cap_rate, ...):
         -> Extract values from each enriched deal
         -> Determine best/worst based on metric semantics:
              higher_is_better: IRR, MOIC, NOI, units
              lower_is_better: purchase_price, cap_rate (context-dependent)
  -> Build ComparisonSummary: overall_best_deal_id, key_differences count
  <- DealComparisonResponse
```

### Data stores touched

| Store | Operation |
|-------|-----------|
| PostgreSQL `deals` | SELECT IN (...) with soft-delete filter |
| PostgreSQL `extracted_values` + `extraction_runs` | Batch SELECT for enrichment |

---

## 9. Extraction Run

**User action**: Click "Start Extraction" on the extraction management page.

### Frontend Flow

```
ExtractionPage
  -> Click "Start Extraction"
  -> apiClient.post('/extraction/start', {source: "local"|"sharepoint", file_paths?: [...]})
  <- ExtractionStartResponse {run_id, status: "running", files_total, message}
  -> Subscribe to WebSocket "extraction" channel for real-time progress
  -> Periodic status poll as backup:
       apiClient.get('/extraction/status')
       <- {status, progress, files_processed, files_total, current_file, errors}
  -> Progress bar updates from WebSocket or poll
  -> On completion: queryClient.invalidateQueries(['properties', 'deals'])
  -> Toast: "Extraction complete: N files processed, M values extracted"
```

### Backend Flow

```
POST /api/v1/extraction/start
  Auth: require_manager

  -> ExtractionRunCRUD.get_running(db)  // check for in-progress run
  -> if running: 409 "Extraction already running (id=...)"
  -> Determine file source:
       "local": validate file_paths exist on filesystem
       "sharepoint":
         -> Validate settings: AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, SHAREPOINT_SITE_URL
         -> discover_sharepoint_files()  // list files from SharePoint document library
         -> if 0 files: 404 "No UW model files found"
  -> ExtractionRunCRUD.create(db, ExtractionRun{status="running", files_total=N, source=...})
  -> BackgroundTasks.add_task(run_extraction_task, run_id, files, db_url)
  <- ExtractionStartResponse{run_id, status, files_total}

Background task: run_extraction_task(run_id, files, db_url)
  -> Create sync DB session from db_url
  For each file:
    1. file_filter.classify(file_path)
         -> Check file extension (.xlsx, .xlsm)
         -> Check file size (reject too small/large)
         -> Check sheet names for UW model indicators
         -> Returns: {"is_uw_model": True/False, "confidence": 0-1, "model_type": "..."}

    2. fingerprint.identify(file_path)
         -> Read sheet structure (row/column counts, header patterns)
         -> Hash key cell values to create template fingerprint
         -> Match against known UW model fingerprints
         -> Returns: {"template_type": "BRC_Standard_v3", "confidence": 0.95}

    3. extractor.extract(file_path, template_type)
         -> reference_mapper.get_mappings(template_type)
              // Returns: {field_name: CellReference(sheet, cell_address)}
         -> openpyxl.load_workbook(file_path, data_only=True)
         -> For each mapping: read cell value at specified address
         -> Returns: [{field_name, value_numeric, value_text, source_cell, sheet_name}]

    4. validation.validate(extracted_values)
         -> Check required fields present
         -> Check numeric ranges (e.g., cap_rate 0-1, units > 0)
         -> Flag outliers and errors
         -> Returns: validated values with is_error flags

    5. INSERT INTO extracted_values (batch):
         field_name, value_numeric, value_text, property_name, property_id,
         extraction_run_id, source_file, source_cell, sheet_name,
         confidence, is_error, error_message

    6. UPDATE extraction_runs SET files_processed += 1

    7. WebSocket broadcast to "extraction" channel:
         {type: "extraction_progress", run_id, progress: (N/total*100), file: "filename.xlsx"}

  On completion:
    -> UPDATE extraction_runs SET status="completed", completed_at=now()
    -> hydrate_properties_from_extracted()
         // Sync extracted data -> properties table columns + financial_data JSON
    -> cache.invalidate_properties()
    -> WebSocket broadcast: {type: "extraction_complete", run_id, files_processed, values_extracted}

  On failure:
    -> UPDATE extraction_runs SET status="failed", error_message="..."
    -> WebSocket broadcast: {type: "extraction_failed", run_id, error}
```

### Pipeline stages

```
file_filter.py -> fingerprint.py -> reference_mapper.py -> extractor.py (openpyxl) -> validation.py
                                                                                         |
                                                                                         v
                                                                              extracted_values table
                                                                                         |
                                                                                         v
                                                                         hydrate_properties_from_extracted()
                                                                                         |
                                                                                         v
                                                                              properties table (enriched)
```

### Data stores touched

| Store | Operation |
|-------|-----------|
| PostgreSQL `extraction_runs` | INSERT (start), UPDATE (progress, completion/failure) |
| PostgreSQL `extracted_values` | INSERT (per field per file, batch) |
| PostgreSQL `properties` | UPDATE (hydration from extracted data) |
| Redis/memory cache | DELETE property_* pattern |
| WebSocket manager | Broadcast progress + completion to "extraction" channel |
| File system | READ .xlsx/.xlsm files from local path or SharePoint temp download |

---

## 10. Grouping Pipeline

**User action**: Run the UW model file grouping and batch extraction pipeline.

### Frontend Flow

```
GroupingPipelinePage

  Status check:
    -> apiClient.get('/extraction/grouping/status')
    <- PipelineStatusResponse {phase, groups_total, groups_processed, files_total, files_processed}

  Phase 1 - Discovery:
    -> apiClient.post('/extraction/grouping/discover', files?)
    <- DiscoveryResponse {files, total_files, grouped, ungrouped}

  Phase 2 - Fingerprinting:
    -> apiClient.post('/extraction/grouping/fingerprint')
    <- FingerprintResponse {fingerprints, groups}

  Phase 3 - Reference Mapping:
    -> apiClient.post('/extraction/grouping/reference-map')
    <- ReferenceMappingResponse {mappings, auto_mapped, needs_review}

  Phase 4 - Extraction per group:
    -> apiClient.post('/extraction/grouping/extract/{group_name}', {file_ids})
    <- GroupExtractionResponse {values_extracted, files_processed, errors}

  Batch extraction (all approved groups):
    -> apiClient.post('/extraction/grouping/batch-extract', {group_names: [...]})
    <- BatchExtractionResponse {groups_processed, total_values, errors}

  Group management:
    -> apiClient.get('/extraction/grouping/groups')
    <- GroupListResponse {groups: [{name, file_count, status, template_type}]}
    -> apiClient.get('/extraction/grouping/groups/{name}')
    <- GroupDetailResponse {name, files, mappings, extraction_status}
    -> apiClient.post('/extraction/grouping/groups/{name}/approve')
    <- GroupApprovalResponse
```

### Backend Flow

```
All under /api/v1/extraction/grouping/
  Auth: require_manager for mutations, require_analyst for reads

Phase 1 - Discovery:
  -> GroupExtractionPipeline().discover(files)
  -> Scan directories for .xlsx/.xlsm
  -> file_filter.classify() each
  -> Return manifest with grouped/ungrouped counts

Phase 2 - Fingerprinting:
  -> For each discovered file:
       fingerprint.identify(file_path)
       -> Hash sheet structure + key cells
  -> Cluster files by fingerprint similarity
  -> Auto-assign group names based on template family

Phase 3 - Reference Mapping:
  -> For each group:
       reference_mapper.resolve_group_mappings(template_type)
  -> Identify field -> cell address mappings
  -> Flag conflicts (ambiguous mappings)

Phase 4 - Extraction:
  -> Same pipeline as single extraction (extractor + validation)
  -> Per group: extract all files with group's reference mappings
  -> INSERT extracted_values in bulk
  -> hydrate_properties_from_extracted()
  -> cache.invalidate_properties()
```

### Data stores touched

| Store | Operation |
|-------|-----------|
| File system | SCAN directories, READ .xlsx/.xlsm |
| PostgreSQL `extraction_runs` | INSERT/UPDATE |
| PostgreSQL `extracted_values` | INSERT (bulk per group) |
| PostgreSQL `properties` | UPDATE (hydration) |
| Redis/memory cache | DELETE property_* pattern |

---

## 11. Market Data

**User action**: View Market Analytics page or dashboard market overview widget.

### Frontend Flow

```
MarketDataPage / Dashboard market widget
  -> useMarketOverview()
       -> apiClient.get('/market/overview')
       <- MarketOverviewResponse {msa_stats, economic_indicators, last_updated}
       React Query staleTime: 60min (reference data)

  -> useMarketTrends(periodMonths)
       -> apiClient.get('/market/trends', {params: {period_months: 12}})
       <- MarketTrendsResponse {monthly_data: [{period, rent_growth, occupancy, cap_rate, ...}]}

  -> useSubmarkets()
       -> apiClient.get('/market/submarkets')
       <- SubmarketsResponse {submarkets: [{name, avg_rent, occupancy, cap_rate, inventory, absorption}]}

  -> useUSAOverview()
       -> apiClient.get('/market/usa/overview')
       <- National indicators: unemployment, employment, CPI, GDP, mortgage, fed funds

  -> useUSATrends()
       -> apiClient.get('/market/usa/trends', {params: {period_months: 12}})
       <- National monthly trends

  -> useInterestRates()
       -> apiClient.get('/interest-rates/')
       <- {rates: [{date, treasury_10y, mortgage_30y, fed_funds, ...}]}
       React Query staleTime: 60min

  -> Manual refresh (admin only):
       -> apiClient.post('/market/refresh')
       <- {status, records_upserted, message, last_updated}
       -> queryClient.invalidateQueries(['market'])
```

### Backend Flow

```
GET /api/v1/market/overview
  Auth: require_viewer (lowest permission)
  -> market_data_service.get_market_overview()
       // Service-level caching (in-memory, checks staleness)
       // Queries market_data_records for Phoenix MSA FRED series:
       //   PHXRSA (employment), AZUR (unemployment), PHXPCPI (CPI),
       //   PHXNQGSP (GDP), plus housing starts, permits, etc.
       // Aggregates into MSA overview format
  <- MarketOverviewResponse

GET /api/v1/market/trends?period_months=12
  Auth: require_viewer
  -> market_data_service.get_market_trends(period_months)
       // Queries market_data_records for monthly time series
       // Returns: rent growth, occupancy, cap rates, economic metrics
  <- MarketTrendsResponse

POST /api/v1/market/refresh  (admin-only trigger)
  Auth: require_admin
  -> run_fred_extraction_async(engine, incremental=True)
       // HTTP GET to FRED API (api.stlouisfed.org) for each configured series
       // Parse JSON response -> extract observations
       // UPSERT into market_data_records (date + series_id composite key)
  -> market_data_service.update_last_refreshed()
  <- {status, records_upserted, message, last_updated}
```

### Scheduled data refresh (background)

```
Application startup (lifespan):
  -> MarketDataScheduler.start()
       // Cron-based schedule (MARKET_DATA_EXTRACTION_ENABLED, configurable cron)
       // Periodically runs: run_fred_extraction_async(incremental=True)
       // Updates market_data_records table

  -> InterestRateScheduler.start()
       // Cron-based schedule (INTEREST_RATE_SCHEDULE_ENABLED)
       // Fetches Treasury, mortgage, Fed Funds rates
       // Updates interest_rate_records table

Application shutdown:
  -> MarketDataScheduler.stop()
  -> InterestRateScheduler.stop()
```

### Data stores touched

| Store | Operation |
|-------|-----------|
| PostgreSQL `market_data_records` | SELECT (overview, trends, submarkets), UPSERT (refresh) |
| PostgreSQL `interest_rate_records` | SELECT (rates list), UPSERT (scheduled refresh) |
| FRED API (external) | HTTP GET time series data (on manual refresh + scheduled) |
| Service-level in-memory cache | Market overview caching within market_data_service |
| Frontend ETag cache | Conditional GET for all market endpoints |
| React Query cache | staleTime=60min for reference data, 5min for trends |

---

## 12. Report Generation

**User action**: Select a report template, configure options, click "Generate".

### Frontend Flow

```
ReportingPage
  -> useReportTemplates({page, pageSize, category})
       -> apiClient.get('/reporting/templates', {params: {page, page_size, category, is_default, search}})
       <- ReportTemplateListResponse {items: [ReportTemplate], total, page, page_size}

  -> Click template -> configure report
  -> Click "Generate"
       -> apiClient.post('/reporting/generate', {template_id, name, format: "pdf"|"xlsx"|"csv"})
       <- GenerateReportResponse {queued_report_id, status: "pending", message}

  -> Poll for completion:
       -> apiClient.get(`/reporting/queue/${reportId}`)
       <- QueuedReportResponse {id, status, progress, download_url, error, ...}
       -> Repeat every few seconds until status != "pending"/"generating"

  -> On completed: show download link / open report
  -> On failed: show error message

  Report Settings (global configuration):
    -> apiClient.get('/reporting/settings')
    <- ReportSettingsSchema (singleton row, auto-created if not exists)
    -> apiClient.put('/reporting/settings', updates)
    <- Updated ReportSettingsSchema

  Distribution Schedules (automated report delivery):
    -> apiClient.get('/reporting/schedules')
    <- DistributionScheduleListResponse
    -> apiClient.post('/reporting/schedules', {template_id, recipients, frequency, ...})
    <- DistributionScheduleResponse

  Available Widgets (for custom report building):
    -> apiClient.get('/reporting/widgets', {params: {widget_type}})
    <- ReportWidgetListResponse {widgets: [static widget definitions]}
```

### Backend Flow

```
POST /api/v1/reporting/generate
  Auth: require_viewer
  -> Verify template exists (template_crud.get) and not soft-deleted
  -> if not found: 404
  -> queued_crud.create_with_timestamp(db, QueuedReportCreate{
       name, template_id, format, requested_by="current_user", status="pending"
     })
       -> INSERT INTO queued_reports (name, template_id, format, status, requested_at)
  <- GenerateReportResponse{queued_report_id, status: "pending", message}

  NOTE: No background worker exists to process the queue.
  Reports remain in "pending" status indefinitely. See Issues Found section.

GET /api/v1/reporting/queue/{report_id}
  Auth: require_viewer
  -> queued_crud.get(db, report_id)
  -> template_crud.get(db, report.template_id)  // enrich with template name
  <- QueuedReportResponse

GET /api/v1/reporting/settings
  Auth: require_viewer
  -> SELECT * FROM report_settings WHERE id=1
  -> if not found: auto-initialize default row (INSERT id=1 with server_defaults)
  <- ReportSettingsSchema
```

### Data stores touched

| Store | Operation |
|-------|-----------|
| PostgreSQL `report_templates` | SELECT (list, get, verify existence) |
| PostgreSQL `queued_reports` | INSERT (generate), SELECT (status poll) |
| PostgreSQL `report_settings` | SELECT/INSERT (singleton row, id=1, auto-init) |
| PostgreSQL `distribution_schedules` | SELECT/INSERT/UPDATE/soft-DELETE |

---

## 13. WebSocket Subscription

**User action**: Pages with real-time features load (deals kanban, extraction progress).

### Frontend Flow

```
Component mounts with real-time data need
  -> new WebSocket(`ws://localhost:8000/api/v1/ws/${channel}?token=${accessToken}`)
  -> Server accepts and sends:
       {type: "connected", connection_id: "uuid", channels: ["deals"]}

Client -> Server messages:
  {type: "pong"}                           -- heartbeat response (server sends pings)
  {type: "subscribe", channel: "x"}        -- join additional channel
  {type: "unsubscribe", channel: "x"}      -- leave a channel

Server -> Client messages:
  {type: "ping"}                           -- heartbeat; client must respond with pong
  {type: "subscribed", channel: "x"}       -- confirmation of subscription
  {type: "unsubscribed", channel: "x"}     -- confirmation of unsubscription
  {type: "deal_update", deal_id, ...}      -- deals channel
  {type: "extraction_progress", ...}       -- extraction channel
  {type: "notification", ...}              -- per-user notification
  {type: "error", message: "..."}          -- error (e.g., unknown message type)

On WebSocket disconnect:
  -> Component cleanup / auto-reconnect (implementation varies by feature)
```

### Backend Flow

```
WebSocket /api/v1/ws/{channel}?token=JWT
  -> _authenticate_token(token)
       // jwt.decode(token, SECRET_KEY, algorithms=[HS256])
       // Extracts user_id from "sub" claim
       // Stateless: no DB lookup during handshake (performance)
       // Returns user_id or None (anonymous connections allowed)

  -> manager.connect(websocket, user_id=user_id, channels=[channel])
       // Validates connection limits (may raise ValueError -> close with 1008)
       // Assigns unique connection_id
       // Registers in channel subscription map
       // Sends: {type: "connected", connection_id, channels: [channel]}

  -> Event loop (while connected):
       data = await websocket.receive_json()
       Route by data["type"]:
         "pong"        -> manager.handle_pong(connection_id)  // reset heartbeat timer
         "subscribe"   -> manager.subscribe(connection_id, channel)
                          -> send {type: "subscribed", channel}
         "unsubscribe" -> manager.unsubscribe(connection_id, channel)
                          -> send {type: "unsubscribed", channel}
         other         -> send {type: "error", message: "Unknown message type: ..."}

  -> On disconnect (WebSocketDisconnect or exception):
       -> manager.disconnect(connection_id)
       // Removes from all channel subscriptions
       // Frees connection slot

Broadcasting (triggered by backend services):
  get_websocket_manager().broadcast_to_channel(channel, payload)
    -> For each connection subscribed to channel:
         websocket.send_json(payload)
```

### Available channels

| Channel | Event types | Triggered by |
|---------|------------|--------------|
| `deals` | `deal_created`, `deal_updated`, `deal_stage_changed` | Deal CRUD endpoints after successful DB commit |
| `extraction` | `extraction_progress`, `extraction_complete`, `extraction_failed` | Background extraction task (per file + on completion) |
| `properties` | `property_updated`, `property_created` | Property CRUD endpoints |
| `notifications` | `notification` | User-specific events (filtered by user_id at connection level) |
| `analytics` | `report_ready` | Report generation completion (when worker is implemented) |

### Data stores touched

| Store | Operation |
|-------|-----------|
| In-memory WebSocket connection manager | Register/unregister connections, channel subscriptions |
| JWT (stateless) | Decode token for user_id (no DB lookup on handshake) |

---

## Issues Found

### 1. Token refresh not wired on frontend

The backend implements full refresh token rotation with replay detection (`POST /auth/refresh`), but the frontend `authStore` does not call this endpoint. On 401, the frontend clears state and forces re-login. The `refresh_token` stored in localStorage is set but never used after initial login.

**Impact**: Users must re-login when the access token expires instead of seamlessly refreshing. Short session lifetime.

**Files**: `src/stores/authStore.ts` (missing refresh call), `src/lib/api/client.ts` (no 401 retry-with-refresh logic).

### 2. Redis services commented out in lifespan startup

In `backend/app/main.py` lines 189-191, Redis initialization (`init_redis()`) and WebSocket manager initialization (`init_websocket_manager()`) are commented out. The `CacheService` lazily initializes its own Redis connection, and the `token_blacklist` also lazily connects. But if other services expect a shared Redis connection pool, they silently fall back to in-memory storage.

**Impact**: Low in development (memory fallback works). In production with multiple workers, cache and rate-limit state would not be shared across processes without Redis.

**Files**: `backend/app/main.py` lines 189-191.

### 3. Report generation has no background worker

`POST /reporting/generate` creates a `queued_reports` row with status="pending", but no background worker or task runner processes the queue. Reports will remain in "pending" status indefinitely. The frontend poll loop will never see status="completed".

**Impact**: High -- report generation is non-functional. Users can queue reports but they never complete or produce downloadable output.

**Files**: `backend/app/api/v1/endpoints/reporting.py` (queue creation only). No worker found in `backend/app/services/`.

### 4. N+1 query in queued report list (template name enrichment)

In `list_queued_reports()` (`reporting.py` lines 246-266), each queued report triggers a separate `template_crud.get(db, item.template_id)` inside a for-loop. For N queued reports, this issues N+1 queries.

**Impact**: Slow response for large report queues. Fix: single JOIN query or batch template fetch.

**Files**: `backend/app/api/v1/endpoints/reporting.py` lines 246-266.

### 5. N+1 query in distribution schedule list (same pattern)

`list_schedules()` in `reporting.py` line 339 queries the template per schedule inside a loop. Same N+1 pattern as issue 4.

**Impact**: Minor (fewer schedules than reports typically), but should be fixed for consistency.

**Files**: `backend/app/api/v1/endpoints/reporting.py` lines 335-362.

### 6. Property analytics trends returns single-point data

`GET /properties/{id}/analytics` returns `trends.rent = [current_rent]` and `trends.periods = ["Current"]` with a note: "Historical trend data requires time-series tracking." The frontend chart components likely expect multi-point arrays.

**Impact**: Medium -- analytics charts render a single dot instead of a trend line. The `data_source` field distinguishes "database" vs "mock", but frontend components may not adapt their rendering.

**Files**: `backend/app/api/v1/endpoints/properties.py` lines 630-636.

### 7. Frontend ETag cache has no size limit or eviction

The `etagCache` Map in `src/lib/api/client.ts` (line 14) grows unbounded. Every unique GET URL adds a permanent entry. For long-running sessions with many distinct API calls (e.g., viewing all 305 property details), memory grows without bound.

**Impact**: Low for typical use (dozens of unique URLs). Relevant for power users and automated testing. Fix: LRU eviction or max-size cap.

**Files**: `src/lib/api/client.ts` line 14.

### 8. Deal kanban enrichment queries extraction data on every cache miss

When the kanban cache expires (5 min), the entire enrichment subquery runs: latest extraction_run per property_id, then field lookup across all property_ids. For 305 properties across many deals, this is a substantial query even though it is batched (not N+1).

**Impact**: Low -- query is efficient (batch, indexed). But the 5-minute TTL means this runs frequently. Consider longer cache TTL or materialized view for extraction enrichment.

**Files**: `backend/app/api/v1/endpoints/deals.py` (`_enrich_deals_with_extraction`).
