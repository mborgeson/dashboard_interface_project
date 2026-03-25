# B&R Capital Dashboard — Project Structure Discovery

**Date:** 2026-03-25  
**Scope:** Complete exploration of backend and frontend architecture, entry points, scheduled jobs, configuration, module boundaries, middleware chain, and dependencies.

---

## 1. Directory Structure Map

### Backend (`backend/`)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py (428 lines) — FastAPI app entry point with lifespan context manager
│   ├── api/
│   │   └── v1/
│   │       ├── router.py (74 lines) — Route aggregator, include_router calls for 18 endpoints
│   │       └── endpoints/
│   │           ├── admin.py
│   │           ├── analytics.py
│   │           ├── auth.py
│   │           ├── construction_pipeline.py
│   │           ├── deals.py
│   │           ├── documents.py
│   │           ├── exports.py
│   │           ├── extraction.py
│   │           ├── health.py
│   │           ├── interest_rates.py
│   │           ├── market_data.py
│   │           ├── market_data_admin.py
│   │           ├── monitoring.py
│   │           ├── properties.py
│   │           ├── reporting.py
│   │           ├── sales_analysis.py
│   │           ├── tasks.py
│   │           ├── transactions.py
│   │           ├── users.py
│   │           └── ws.py
│   ├── core/
│   │   ├── config.py (451 lines) — Pydantic Settings with 7 groups (AppSettings, AuthSettings, DatabaseSettings, ExternalServiceSettings, ExtractionSettings, ConstructionSettings, MarketDataSettings)
│   │   ├── errors.py
│   │   ├── logging.py
│   │   ├── permissions.py
│   │   ├── security.py
│   │   └── token_blacklist.py
│   ├── crud/
│   │   ├── base.py
│   │   ├── deals.py
│   │   ├── documents.py
│   │   ├── extraction.py
│   │   ├── properties.py
│   │   ├── transactions.py
│   │   ├── users.py
│   │   └── [other models]
│   ├── database/
│   │   ├── __init__.py
│   │   └── session.py — AsyncSession factory
│   ├── db/
│   │   └── base.py — Alembic registry and model imports
│   ├── events/
│   │   ├── lifespan.py
│   │   └── [lifecycle hooks]
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── cell_mapping.py — Template-specific cell references
│   │   ├── extractor.py — Core extraction logic
│   │   ├── file_filter.py — File classification
│   │   ├── fingerprint.py — UW model type identification
│   │   ├── group_pipeline.py — Batch extraction orchestration
│   │   ├── reference_mapper.py — Cell address mapping
│   │   ├── validation.py — Extracted value checks
│   │   └── monitor_scheduler.py
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── cors.py
│   │   ├── error_handler.py
│   │   ├── etag.py
│   │   ├── metrics.py
│   │   ├── origin_validation.py
│   │   ├── rate_limit.py
│   │   ├── request_id.py
│   │   ├── security_headers.py
│   │   └── ws_manager.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── deal.py
│   │   ├── document.py
│   │   ├── extraction.py
│   │   ├── property.py
│   │   ├── transaction.py
│   │   ├── user.py
│   │   └── underwriting/
│   │       ├── __init__.py
│   │       ├── operating_expense.py
│   │       ├── underwriting_data.py
│   │       └── [financial models]
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── deals.py
│   │   ├── extraction.py
│   │   ├── properties.py
│   │   └── [response/request schemas]
│   ├── services/
│   │   ├── __init__.py
│   │   ├── batch/
│   │   │   └── batch_processor.py
│   │   ├── construction_api/
│   │   │   ├── __init__.py
│   │   │   ├── census.py
│   │   │   ├── fred.py
│   │   │   ├── municipal.py
│   │   │   └── scheduler.py
│   │   ├── data_extraction/
│   │   │   ├── __init__.py
│   │   │   ├── cache.py
│   │   │   ├── enrichment.py
│   │   │   ├── scheduler.py
│   │   │   └── worker.py
│   │   ├── extraction/
│   │   │   ├── __init__.py
│   │   │   ├── monitor_scheduler.py
│   │   │   ├── scheduler.py
│   │   │   └── worker.py
│   │   ├── ml/ — Model-based predictions (optional, in requirements-ml.txt)
│   │   ├── monitoring/
│   │   │   ├── __init__.py
│   │   │   └── metrics.py
│   │   ├── workflow/
│   │   ├── report_worker.py
│   │   ├── interest_rate_scheduler.py
│   │   └── [business logic services]
│   ├── tasks/
│   │   └── [async task definitions]
│   └── templates/
│       └── [Jinja2 email templates]
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── [migration files: c5d6e7f8a9b0 is current head]
├── tests/
│   ├── conftest.py
│   ├── test_api/
│   ├── test_crud/
│   ├── test_extraction/
│   └── [2,956+ total backend tests]
├── requirements.txt (75 lines)
├── requirements-ml.txt (optional ML deps)
├── Dockerfile
└── docker-compose.yml
```

### Frontend (`src/`)

```
src/
├── main.tsx (24 lines) — React entry point, StrictMode wrapper, QueryClientProvider
├── app/
│   ├── App.tsx (22 lines) — useAuthStore.initialize(), usePrefetchDashboard, ToastProvider
│   ├── router.tsx (260 lines) — createBrowserRouter with 14 authenticated routes + 1 login
│   ├── layout/
│   │   └── AppLayout.tsx
│   └── routes/
│       ├── index.ts — Route exports and routerOptions
│       ├── DashboardMain.tsx
│       ├── AnalyticsPage.tsx
│       ├── InvestmentsPage.tsx
│       ├── PropertyDetailPage.tsx
│       ├── MappingPage.tsx
│       ├── DealsPage.tsx
│       ├── DealComparisonPage.tsx
│       ├── MarketPage.tsx
│       ├── USAMarketPage.tsx
│       ├── DocumentsPage.tsx
│       ├── InterestRatesPage.tsx
│       ├── ReportingSuitePage.tsx
│       ├── ExtractionDashboard.tsx
│       ├── SalesAnalysisPage.tsx
│       ├── ConstructionPipelinePage.tsx
│       ├── TransactionsPage.tsx
│       └── LoginPage.tsx
├── assets/
│   └── [static images, fonts]
├── components/
│   ├── SuspenseWrapper.tsx
│   ├── FeatureErrorBoundary.tsx
│   ├── [shadcn/ui primitives and custom components]
│   └── [reusable UI components]
├── contexts/
│   ├── ToastContext.tsx
│   └── [React Context providers]
├── features/ (feature-based modules)
│   ├── analytics/
│   ├── auth/
│   ├── construction-pipeline/
│   ├── dashboard-main/
│   ├── deals/
│   ├── documents/
│   ├── extraction/
│   ├── interest-rates/
│   ├── investments/
│   ├── mapping/
│   ├── market/
│   ├── property-detail/
│   ├── reporting-suite/
│   ├── sales-analysis/
│   ├── search/
│   ├── transactions/
│   └── underwriting/
├── hooks/
│   ├── useApi.ts
│   ├── usePrefetchDashboard.ts
│   ├── usePagination.ts
│   ├── [custom React hooks]
│   └── [1,274+ frontend tests colocated with features]
├── lib/
│   ├── api.ts (axios client, legacy, don't extend)
│   ├── api/
│   │   ├── client.ts (fetch client, use for new work)
│   │   ├── endpoints/ (API client methods)
│   │   ├── schemas/ (Zod schemas for API responses, snake_case → camelCase)
│   │   └── types.ts
│   ├── utils/
│   └── [utility functions, constants]
├── services/
│   ├── api.ts
│   └── [service layer logic]
├── store/ (legacy)
│   └── [older state management]
├── stores/ (current, Zustand)
│   ├── authStore.ts (JWT token + isAuthenticated flag)
│   ├── dashboardStore.ts
│   ├── [Zustand stores]
│   └── [state management]
├── test/
│   ├── fixtures/
│   └── [test utilities]
├── types/
│   ├── api.ts
│   ├── dashboard.ts
│   ├── deals.ts
│   ├── properties.ts
│   ├── reporting.ts
│   ├── [type definitions for features]
│   └── [extracted from API responses and schemas]
├── vite-env.d.ts
├── index.css
├── tailwind.config.ts
└── globals.css
```

---

## 2. Entry Points

### Backend Entry Point: `backend/app/main.py` (428 lines)

**Purpose:** FastAPI application factory with async lifespan context manager, middleware chain, scheduler initialization, and route registration.

**Key Sections:**

1. **Imports (lines 1-60):**
   - `FastAPI`, `lifespan` from `fastapi`
   - Middleware classes: `SecurityHeadersMiddleware`, `OriginValidationMiddleware`, `ErrorHandlerMiddleware`, `ETagMiddleware`, `RateLimitMiddleware`, `MetricsMiddleware`, `CORSMiddleware`, `RequestIDMiddleware`, `WebSocketManager`
   - Schedulers: `ExtractionScheduler`, `MonitorScheduler`, `MarketDataScheduler`, `InterestRateScheduler`, `ReportWorker`
   - Logger: `loguru.logger`
   - Config: `settings` from `app.core.config`
   - API router: `from app.api.v1.router import api_router`

2. **Lifespan Context Manager (lines ~65-150):**
   - Yields control during app startup/shutdown
   - Initializes 5 scheduler services during startup
   - Gracefully shuts down schedulers on app exit
   - Example: `ExtractionScheduler.initialize(settings)` starts cron-based extraction

3. **FastAPI App Creation (lines ~155-175):**
   - `app = FastAPI(title="B&R Capital Dashboard API", version="2.0.0", lifespan=lifespan)`
   - Root endpoint at `/`: returns app metadata

4. **Middleware Chain Registration (lines ~180-220):**
   - Order (inner to outer): RequestIDMiddleware → OriginValidationMiddleware → ErrorHandlerMiddleware → SecurityHeadersMiddleware → ETagMiddleware → RateLimitMiddleware → MetricsMiddleware → CORSMiddleware
   - Each middleware configured with relevant settings (CORS_ORIGINS, rate limits, security headers)
   - CORS origins parsed from `settings.CORS_ORIGINS` (supports comma-separated, JSON array, or list formats)

5. **Route Registration (lines ~225-250):**
   - `app.include_router(api_router, prefix="/api/v1")`
   - API router registers all 18 endpoint routers (health, auth, properties, deals, analytics, users, exports, monitoring, extraction, interest-rates, transactions, documents, market-data, reporting, admin, market_data_admin, sales-analysis, construction-pipeline, tasks, ws)

6. **Event Handlers (lines ~260-300):**
   - `@app.on_event("startup")`: initialize logger, metrics
   - `@app.on_event("shutdown")`: cleanup, flush metrics

7. **Static Files & Exception Handlers (lines ~310-428):**
   - Custom exception handlers for HTTPException, validation errors
   - WebSocket endpoint at `/ws` for real-time updates (managed by WebSocketManager)

---

### Frontend Entry Point: `src/main.tsx` (24 lines)

**Purpose:** React application root, query client setup, error boundary initialization.

```typescript
// Line 1-5: React imports
import React from 'react';
import ReactDOM from 'react-dom/client';

// Line 6-10: App component and providers
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import App from './app/App';

// Line 11-15: Global error tracking
import { initErrorTracking } from '@/services/errorTracking'; // Line 15

// Line 16-24: ReactDOM render with StrictMode, QueryClientProvider, ErrorBoundary
initErrorTracking();
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  </React.StrictMode>
);
```

---

### Frontend App Setup: `src/app/App.tsx` (22 lines)

**Purpose:** Initialize authentication state, prefetch common dashboard data, wrap routes with ToastProvider.

```typescript
// Line 1-10: Hooks and providers
import { useEffect } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { usePrefetchDashboard } from '@/hooks/usePrefetchDashboard';
import { ToastProvider } from '@/contexts/ToastContext';

// Line 11-15: Initialize auth on mount
useEffect(() => {
  useAuthStore.initialize(); // Validates JWT from localStorage
}, []);

// Line 16-22: Render router with providers
usePrefetchDashboard(); // Prefetch frequently-used data (properties, deals, market data)
return (
  <ToastProvider>
    <AppRouter />
  </ToastProvider>
);
```

---

### Frontend Router Setup: `src/app/router.tsx` (260 lines)

**Purpose:** Define all authenticated and public routes, apply auth guards, lazy-load route components.

**Key Elements:**

1. **Public Route (lines ~60-70):**
   - `/login` → `LoginPage` (wrapped with LazyRoute)

2. **Auth Guard Component (lines ~42-58):**
   ```typescript
   function RequireAuth() {
     const { isAuthenticated, isLoading } = useAuthStore();
     if (isLoading) return <LoadingSpinner />;
     if (!isAuthenticated) return <Navigate to="/login" replace />;
     return <Outlet />;
   }
   ```

3. **Authenticated Routes (lines ~73-250):**
   - Base route: `/` → `AppLayout` (page wrapper)
   - Child routes (all wrapped with `FeatureErrorBoundary` + `LazyRoute`):
     - `/investments` → `InvestmentsPage`
     - `/properties/:id` → `PropertyDetailPage`
     - `/deals` → `DealsPage`
     - `/deals/compare` → `DealComparisonPage`
     - `/analytics` → `AnalyticsPage`
     - `/mapping` → `MappingPage`
     - `/market` → `MarketPage`
     - `/market/usa` → `USAMarketPage`
     - `/documents` → `DocumentsPage`
     - `/interest-rates` → `InterestRatesPage`
     - `/reporting` → `ReportingSuitePage`
     - `/extraction` → `ExtractionDashboard`
     - `/extraction/:propertyName` → `ExtractionDashboard`
     - `/sales-analysis` → `SalesAnalysisPage`
     - `/construction-pipeline` → `ConstructionPipelinePage`
     - `/transactions` → `TransactionsPage`

4. **Router Creation (lines ~252-259):**
   - `createBrowserRouter()` with future flag `v7_startTransition: true`
   - Exported via `AppRouter` component for use in App.tsx

---

## 3. Scheduled Jobs

### APScheduler Configuration

All schedulers use `APScheduler.AsyncIOScheduler` for async/await execution in FastAPI lifespan context.

#### 1. ExtractionScheduler (`backend/app/services/extraction/scheduler.py`)

**Purpose:** Automatically extract financial data from SharePoint/local UW model files on a cron schedule.

- **State Model:** `ExtractionSchedulerState` tracks enabled, cron_expression, timezone, next_run, last_run, last_run_id, running
- **Default Schedule:** `0 17 * * *` (5 PM daily), timezone `America/Phoenix`
- **Config Keys:**
  - `EXTRACTION_SCHEDULE_ENABLED: bool = True`
  - `EXTRACTION_SCHEDULE_CRON: str = "0 17 * * *"`
  - `EXTRACTION_SCHEDULE_TIMEZONE: str = "America/Phoenix"`
- **Trigger:** `ExtractionScheduler.initialize(settings)` in main.py lifespan
- **Job:** Call `backend/app/services/extraction/worker.py::run_extraction()` with batch processing (up to 10 files, 4 concurrent workers)

#### 2. MonitorScheduler (`backend/app/services/extraction/monitor_scheduler.py`)

**Purpose:** Monitor SharePoint/local directories for new or changed files and optionally trigger auto-extraction.

- **Config Keys:**
  - `FILE_MONITOR_ENABLED: bool = False`
  - `FILE_MONITOR_INTERVAL_MINUTES: int = 30`
  - `AUTO_EXTRACT_ON_CHANGE: bool = True`
  - `MONITOR_CHECK_CRON: str = "*/30 * * * *"`
- **Trigger:** Runs every 30 minutes; checks file modification times
- **Job:** If file changed and `AUTO_EXTRACT_ON_CHANGE=True`, queue extraction for that file

#### 3. MarketDataScheduler (`backend/app/services/data_extraction/scheduler.py`)

**Purpose:** Fetch external market data (CoStar, FRED, Census, BLS) and update local database.

- **Config Keys:**
  - `MARKET_DATA_EXTRACTION_ENABLED: bool = False`
  - `MARKET_FRED_SCHEDULE_CRON: str = "0 10 * * *"` (10 AM daily)
  - `MARKET_COSTAR_SCHEDULE_CRON: str = "0 10 15 * *"` (10 AM on 15th)
  - `MARKET_CENSUS_SCHEDULE_CRON: str = "0 10 15 1 *"` (10 AM on 1st of month, 15th)
- **Trigger:** Multiple cron expressions for different data sources
- **Job:** Call `backend/app/services/data_extraction/worker.py` → fetch from FRED, CoStar APIs; populate `MarketData` table

#### 4. InterestRateScheduler (`backend/app/services/interest_rate_scheduler.py`)

**Purpose:** Fetch FRED API interest rate data (Treasury rates, mortgage rates) and store in database.

- **Config Keys:**
  - `INTEREST_RATE_SCHEDULE_ENABLED: bool = False`
  - `INTEREST_RATE_SCHEDULE_CRON_AM: str = "0 8 * * *"` (8 AM daily)
  - `INTEREST_RATE_SCHEDULE_CRON_PM: str = "0 15 * * *"` (3 PM daily)
- **Trigger:** Two separate cron jobs (morning and afternoon updates)
- **Job:** Fetch FRED rates via `FRED_API_KEY`, store in `InterestRate` table

#### 5. ConstructionScheduler (`backend/app/services/construction_api/scheduler.py`)

**Purpose:** Fetch construction permit data from Census, FRED, BLS, and municipal data sources.

- **Config Keys:**
  - `CONSTRUCTION_CENSUS_CRON: str = "0 4 15 * *"` (4 AM on 15th)
  - `CONSTRUCTION_FRED_CRON: str = "0 4 15 * *"`
  - `CONSTRUCTION_BLS_CRON: str = "0 5 15 * *"` (5 AM on 15th)
  - `CONSTRUCTION_MUNICIPAL_CRON: str = "0 6 16 * *"` (6 AM on 16th)
  - `CONSTRUCTION_DATA_DIR: str = "data/construction"`
  - `CONSTRUCTION_MIN_UNITS: int = 50` (filter projects with >50 units)
- **Trigger:** Separate cron for each data source
- **Job:** Orchestrate batch fetch from Census, FRED, BLS, then municipal endpoints (Mesa SODA, Tempe ArcGIS, Gilbert ArcGIS)

#### 6. ReportWorker (`backend/app/services/report_worker.py`)

**Purpose:** Generate PDF reports asynchronously (triggered on-demand via `POST /api/v1/reporting/generate`).

- **Not a scheduled job** — background task worker triggered by API requests
- **Job:** Call `report_generator.generate_pdf()` with property/deal selection, store result in `ReportOutput` table

---

## 4. Configuration

### Backend Configuration: `backend/app/core/config.py` (451 lines)

**Architecture:** Pydantic Settings V2 with 7 logical setting groups, each inheriting from `BaseSettings`.

**Shared Configuration:**
```python
_SHARED_CONFIG = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    case_sensitive=False,
    extra="ignore",
    env_nested_delimiter="__",  # NESTED_VAR__SUBVAR format
)
```

#### 4.1 AppSettings (lines ~41-139)

| Setting | Default | Purpose |
|---------|---------|---------|
| `APP_NAME` | "B&R Capital Dashboard API" | API title |
| `APP_VERSION` | "2.0.0" | Version string |
| `DEBUG` | False | Debug mode |
| `ENVIRONMENT` | "development" | Literal["development", "staging", "production", "testing"] |
| `HOST` | "0.0.0.0" | Bind address |
| `PORT` | 8000 | Uvicorn port |
| `WORKERS` | 4 | Gunicorn worker count |
| `LOG_LEVEL` | "INFO" | Log severity threshold |
| `LOG_FORMAT` | "%(asctime)s..." | Log format string |
| `LOG_RETENTION_DAYS` | 30 | Info log retention |
| `LOG_ERROR_RETENTION_DAYS` | 90 | Error log retention |
| `SLOW_QUERY_THRESHOLD_MS` | 500 | SQL query timing threshold |
| `SLOW_QUERY_LOG_PARAMS` | False | Log SQL parameters in slow query logs |
| `CACHE_SHORT_TTL` | 300 | 5 minutes (frequently-changing data) |
| `CACHE_LONG_TTL` | 7200 | 2 hours (rarely-changing aggregates) |
| `HTTP_TIMEOUT` | 10.0 | Default HTTP client timeout |
| `HTTP_TIMEOUT_LONG` | 15.0 | Extended timeout for slow endpoints |
| `UPLOAD_MAX_EXCEL_MB` | 50 | Max Excel file upload size |
| `UPLOAD_MAX_PDF_MB` | 25 | Max PDF upload size |
| `UPLOAD_MAX_CSV_MB` | 10 | Max CSV upload size |
| `UPLOAD_MAX_DOCX_MB` | 25 | Max DOCX upload size |
| `PDF_MAX_PROPERTIES` | 10 | Max properties per PDF report |
| `PDF_MAX_DEALS` | 10 | Max deals per PDF report |
| `WS_HEARTBEAT_INTERVAL` | 30 | WebSocket ping interval (seconds) |
| `WS_MAX_CONNECTIONS` | 1000 | Max concurrent WebSocket connections |
| `ML_MODEL_PATH` | "./models" | Path to ML models directory |
| `ML_BATCH_SIZE` | 32 | ML inference batch size |
| `ML_PREDICTION_CACHE_TTL` | 300 | ML prediction cache TTL |
| `GEOCODING_RATE_LIMIT_DELAY` | 1.1 | Delay between geocoding requests (seconds) |
| `WORKFLOW_HTTP_TIMEOUT` | 30 | Timeout for workflow HTTP steps |
| `CORS_ORIGINS` | List of 7 domains | CORS allowed origins (custom validator supports comma-separated, JSON array, list) |

#### 4.2 AuthSettings (lines ~144-187)

| Setting | Default | Purpose |
|---------|---------|---------|
| `SECRET_KEY` | None (generated in dev) | JWT signing key (required in prod, min 32 chars) |
| `ALGORITHM` | "HS256" | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | JWT access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Refresh token lifetime |
| `REFRESH_TOKEN_SECRET` | "" | Separate refresh token signing key (fallback to SECRET_KEY) |
| `DEMO_USER_PASSWORD` | "" | Demo user password (env var only) |
| `DEMO_ADMIN_PASSWORD` | "" | Demo admin password (env var only) |
| `DEMO_ANALYST_PASSWORD` | "" | Demo analyst password (env var only) |
| `API_KEYS` | [] | Service-to-service API keys (comma-separated or list) |
| `API_KEY_HEADER` | "X-API-Key" | Header name for API key auth |
| `RATE_LIMIT_ENABLED` | True | Enable rate limiting |
| `RATE_LIMIT_BACKEND` | "auto" | Rate limit backend (redis or memory) |
| `RATE_LIMIT_REQUESTS` | 100 | Requests per window |
| `RATE_LIMIT_WINDOW` | 60 | Time window (seconds) |
| `RATE_LIMIT_AUTH_REQUESTS` | 5 | Auth endpoint rate limit |
| `RATE_LIMIT_AUTH_WINDOW` | 60 | Auth window (seconds) |
| `RATE_LIMIT_REFRESH_REQUESTS` | 10 | Refresh token rate limit |
| `RATE_LIMIT_CLEANUP_WINDOW` | 3600 | Rate limit data cleanup interval |

**Validators (lines ~357-411):**
- `validate_secrets()`: Ensures SECRET_KEY is set and >=32 chars in production; generates random key in dev
- `validate_demo_credentials()`: Prevents demo passwords in production; warns if empty in dev

#### 4.3 DatabaseSettings (lines ~192-216)

| Setting | Default | Purpose |
|---------|---------|---------|
| `DATABASE_URL` | "sqlite:///./test.db" | Primary database URL (SQLite for dev, PostgreSQL for prod) |
| `DATABASE_POOL_SIZE` | 10 | SQLAlchemy connection pool size |
| `DATABASE_MAX_OVERFLOW` | 20 | Max overflow connections |
| `DATABASE_POOL_TIMEOUT` | 30 | Pool timeout (seconds) |
| `MARKET_ANALYSIS_DB_URL` | None | Separate PostgreSQL DB for market analysis |
| `REDIS_URL` | "redis://localhost:6379/0" | Redis connection URL |
| `REDIS_CACHE_TTL` | 3600 | Default Redis TTL (seconds) |
| `REDIS_MAX_CONNECTIONS` | 50 | Max Redis connection pool size |
| `REDIS_SOCKET_CONNECT_TIMEOUT` | 5 | Redis connection timeout (seconds) |
| `INTEREST_RATE_CACHE_TTL` | 300 | Interest rate cache TTL |
| `INTEREST_RATE_DB_POOL_SIZE` | 2 | Interest rate DB pool size |
| `INTEREST_RATE_DB_MAX_OVERFLOW` | 1 | Interest rate DB overflow connections |

**Property (lines ~413-416):**
- `database_url_async`: Converts sync URL to async (`postgresql://` → `postgresql+asyncpg://`)

#### 4.4 ExternalServiceSettings (lines ~221-259)

| Setting | Default | Purpose |
|---------|---------|---------|
| **Email** | | |
| `SMTP_HOST` | "smtp.gmail.com" | SMTP server |
| `SMTP_PORT` | 465 | SMTP port (SSL) |
| `SMTP_USER` | None | Gmail username (env var only) |
| `SMTP_PASSWORD` | None | Gmail app password (env var only) |
| `EMAIL_FROM_NAME` | "Dashboard Interface (B&R Capital)" | From address display name |
| `EMAIL_FROM_ADDRESS` | None | From email address (env var only) |
| `EMAIL_RATE_LIMIT` | 60 | Max emails per minute |
| `EMAIL_MAX_RETRIES` | 3 | SMTP retry attempts |
| `EMAIL_RETRY_DELAY` | 300 | Retry delay (seconds) |
| `EMAIL_BATCH_SIZE` | 10 | Batch send size |
| `EMAIL_DEV_MODE` | False | Log emails instead of sending in dev |
| **SharePoint/Azure AD** | | |
| `AZURE_CLIENT_ID` | None | Azure AD app ID (env var only) |
| `AZURE_CLIENT_SECRET` | None | Azure AD app secret (env var only) |
| `AZURE_TENANT_ID` | None | Azure AD tenant ID (env var only) |
| `SHAREPOINT_SITE_URL` | None | SharePoint site URL (env var only) |
| `SHAREPOINT_SITE` | "BRCapital-Internal" | SharePoint site name |
| `SHAREPOINT_LIBRARY` | "Real Estate" | Document library name |
| `SHAREPOINT_DEALS_FOLDER` | "Deals" | Deals folder within library |
| `DEALS_FOLDER` | "Real Estate/Deals" | Legacy alias for deals folder path |
| `LOCAL_DEALS_ROOT` | "" | Local OneDrive mount path (for file extraction) |
| **External APIs** | | |
| `FRED_API_KEY` | None | Federal Reserve FRED API key (env var only) |
| `CENSUS_API_KEY` | None | Census Bureau API key (env var only) |
| `BLS_API_KEY` | None | Bureau of Labor Statistics API key (env var only) |

#### 4.5 ExtractionSettings (lines ~264-298)

| Setting | Default | Purpose |
|---------|---------|---------|
| **File Filtering** | | |
| `FILE_PATTERN` | r".*UW\s*Model.*vCurrent.*" | Regex to identify UW model files |
| `EXCLUDE_PATTERNS` | "~$,.tmp,backup,old,archive,Speedboat,vOld" | Exclude patterns (comma-separated) |
| `FILE_EXTENSIONS` | ".xlsb,.xlsm,.xlsx" | Allowed file types |
| `CUTOFF_DATE` | "2024-07-15" | Only process files modified after this date |
| `MAX_FILE_SIZE_MB` | 100 | Max file size (MB) |
| **Batch Processing** | | |
| `EXTRACTION_BATCH_SIZE` | 10 | Files per batch |
| `EXTRACTION_MAX_WORKERS` | 4 | Concurrent extraction workers |
| **Scheduler** | | |
| `EXTRACTION_SCHEDULE_ENABLED` | True | Enable scheduled extraction |
| `EXTRACTION_SCHEDULE_CRON` | "0 17 * * *" | Cron expression (5 PM daily) |
| `EXTRACTION_SCHEDULE_TIMEZONE` | "America/Phoenix" | Scheduler timezone |
| **Group Extraction** | | |
| `GROUP_EXTRACTION_DATA_DIR` | "data/extraction_groups" | Directory for grouped extraction results |
| `GROUP_FINGERPRINT_WORKERS` | 4 | Concurrent fingerprinting workers |
| `GROUP_IDENTITY_THRESHOLD` | 0.95 | Similarity threshold for exact group match |
| `GROUP_VARIANT_THRESHOLD` | 0.80 | Similarity threshold for variant detection |
| `GROUP_EMPTY_TEMPLATE_THRESHOLD` | 20 | Min extracted values before treating as empty template |
| `GROUP_MAX_BATCH_SIZE` | 500 | Max files per group batch |
| **File Monitoring** | | |
| `FILE_MONITOR_ENABLED` | False | Enable file change monitoring |
| `FILE_MONITOR_INTERVAL_MINUTES` | 30 | Check interval (minutes) |
| `AUTO_EXTRACT_ON_CHANGE` | True | Auto-extract on file change |
| `MONITOR_CHECK_CRON` | "*/30 * * * *" | Cron for file checks |

#### 4.6 ConstructionSettings (lines ~303-321)

| Setting | Default | Purpose |
|---------|---------|---------|
| `CONSTRUCTION_DATA_DIR` | "data/construction" | Local storage for construction data |
| `CONSTRUCTION_API_ENABLED` | False | Enable construction API endpoints |
| `CONSTRUCTION_CENSUS_CRON` | "0 4 15 * *" | Census data fetch schedule |
| `CONSTRUCTION_FRED_CRON` | "0 4 15 * *" | FRED data fetch schedule |
| `CONSTRUCTION_BLS_CRON` | "0 5 15 * *" | BLS data fetch schedule |
| `CONSTRUCTION_MUNICIPAL_CRON` | "0 6 16 * *" | Municipal data fetch schedule |
| `CONSTRUCTION_MIN_UNITS` | 50 | Filter projects with >N units |
| `MESA_SODA_DATASET_ID` | "h2sj-gt3d" | Mesa city's Socrata Open Data API dataset |
| `MESA_SODA_APP_TOKEN` | None | Socrata app token (env var only) |
| `TEMPE_BLDS_LAYER_URL` | None | Tempe ArcGIS layer URL (env var only) |
| `GILBERT_ARCGIS_LAYER_URL` | None | Gilbert ArcGIS layer URL (env var only) |

#### 4.7 MarketDataSettings (lines ~326-336)

| Setting | Default | Purpose |
|---------|---------|---------|
| `COSTAR_DATA_DIR` | "data/costar" | Local CoStar data storage |
| `MARKET_DATA_EXTRACTION_ENABLED` | False | Enable market data extraction |
| `MARKET_FRED_SCHEDULE_CRON` | "0 10 * * *" | FRED market data schedule (10 AM daily) |
| `MARKET_COSTAR_SCHEDULE_CRON` | "0 10 15 * *" | CoStar schedule (10 AM on 15th) |
| `MARKET_CENSUS_SCHEDULE_CRON` | "0 10 15 1 *" | Census schedule (10 AM, 1st & 15th) |

#### 4.8 Main Settings Class (lines ~341-450)

```python
class Settings(
    AppSettings,
    AuthSettings,
    DatabaseSettings,
    ExternalServiceSettings,
    ExtractionSettings,
    ConstructionSettings,
    MarketDataSettings,
):
    """Composes all settings groups; validates cross-cutting concerns."""
```

**Usage:** `from app.core.config import settings` → access via `settings.APP_NAME`, `settings.SECRET_KEY`, etc.

---

### Frontend Configuration: `vite.config.ts` (112 lines)

**Purpose:** Vite dev server setup, API proxying, chunk splitting strategy, dependency optimization.

**Key Settings:**

1. **Server (lines ~10-20):**
   ```typescript
   server: {
     port: 5173,
     proxy: {
       '/api/fred': {
         target: 'https://api.stlouisfed.org',
         changeOrigin: true,
         rewrite: (path) => path.replace(/^\/api\/fred/, ''),
       },
       '/api': {
         target: 'http://localhost:8000',
         changeOrigin: true,
       },
       '/ws': {
         target: 'ws://localhost:8000',
         ws: true,
       },
     },
   }
   ```

2. **Build Optimization (lines ~30-60):**
   - Manual chunk splitting into 8 vendor chunks:
     - `vendor-react`: React, React-DOM, React-Router
     - `vendor-radix`: @radix-ui/* components
     - `vendor-icons`: lucide-react
     - `vendor-charts`: recharts
     - `vendor-maps`: leaflet, react-leaflet, markercluster
     - `vendor-dnd`: @dnd-kit/*
     - `vendor-data`: @tanstack/react-query, @tanstack/react-table, zustand
     - `vendor-misc`: @hookform/*, zod, date-fns, fuse.js
     - `vendor-forms`: react-hook-form, zod
   - Dynamic imports for heavy libraries:
     - `jspdf` (lazy on demand)
     - `exceljs` (lazy on demand)
     - `html2canvas` (lazy on demand)

3. **Chunk Size Warnings (line ~65):**
   - `chunkSizeWarningLimit: 500 * 1024` (500 KB)
   - Known deferred warnings: exceljs (937KB), vendor-charts (455KB)

4. **Dependency Optimization (lines ~70-90):**
   ```typescript
   optimizeDeps: {
     include: [
       'react',
       'react-dom',
       'react-router-dom',
       'zustand',
       'lucide-react',
       // ... 20+ pre-bundled dependencies
     ],
   },
   ```

---

### Docker Compose: `docker-compose.yml` (121 lines)

**Purpose:** Local development environment with PostgreSQL, Redis, FastAPI backend, and Nginx-served frontend.

**Services:**

1. **PostgreSQL (lines ~5-20):**
   - Image: `postgres:15-alpine`
   - Username: `postgres`, Password: `postgres123`
   - Database: `dashboard_interface_data`
   - Port: 5432 (internal and exposed)
   - Volume: `postgres_data` (/var/lib/postgresql/data)
   - Environment: `POSTGRES_PASSWORD=postgres123`, `POSTGRES_DB=dashboard_interface_data`

2. **Redis (lines ~22-35):**
   - Image: `redis:7-alpine`
   - Port: 6379 (internal and exposed)
   - Volume: `redis_data` (/data)
   - Command: `redis-server --appendonly yes` (persistence enabled)

3. **Backend (lines ~37-60):**
   - Build: `./backend` with development target
   - Port: 8000 (exposed)
   - Environment:
     - `DATABASE_URL=postgresql://postgres:postgres123@postgres:5432/dashboard_interface_data`
     - `REDIS_URL=redis://redis:6379/0`
     - `ENVIRONMENT=development`
   - Volumes: `/app` (source), `/app/logs` (output logs)
   - Depends on: PostgreSQL, Redis
   - Command: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

4. **Frontend (lines ~62-85):**
   - Build: root directory with `Dockerfile.frontend`
   - Port: 5173 (internal) → 80 (host exposed)
   - Nginx serves built frontend + proxies `/api` to backend
   - Depends on: Backend
   - Environment: `BACKEND_URL=http://backend:8000`

**Network:** `dashboard-network` (bridge)

---

## 5. Module Boundaries

### Backend Module Organization

#### `api/v1/endpoints/` (18 route modules)

Each endpoint module exports a `router: APIRouter` with prefix-based registration in `api/v1/router.py`.

| Endpoint | Prefix | Purpose | Key Operations |
|----------|--------|---------|-----------------|
| health | /health/status | System health checks | GET /status, /readiness, /liveness |
| auth | /auth | JWT authentication | POST /login, /refresh, /logout |
| properties | /properties | Property CRUD & queries | GET/POST properties, GET /:id, filtering |
| deals | /deals | Deal management | GET/POST deals, metrics, sync status |
| analytics | /analytics | Dashboard analytics | GET market trends, property stats |
| users | /users | User management | GET/POST users, roles, permissions |
| exports | /exports | PDF/Excel exports | POST /export, GET /:id, DELETE /:id |
| monitoring | /monitoring | Real-time WebSocket updates | Metrics, alerts, activity feed |
| extraction | /extraction | File extraction pipeline | POST /extract, GET /runs, /status |
| interest-rates | /interest-rates | Interest rate data | GET rates, POST scheduler config |
| transactions | /transactions | Financial transactions | GET/POST transactions, filters |
| documents | /documents | Document management | GET/POST documents, metadata |
| market-data | /market | Market data (CoStar, FRED) | GET market trends, submarket data |
| reporting | /reporting | Report generation | GET templates, POST /generate |
| admin | /admin | Admin operations | Scheduler control, cleanup, seeds |
| market_data_admin | /admin/market-data | Admin market data | CoStar sync, FRED refresh |
| sales-analysis | /sales-analysis | Sales comps analysis | GET comps, trends, filters |
| construction-pipeline | /construction-pipeline | Construction projects | GET projects, filters, geospatial |
| tasks | /tasks | Background task tracking | GET /status, polling endpoints |
| ws | /ws | WebSocket | Real-time updates |

#### `crud/` (Database Operations Layer)

Each CRUD module provides database query operations (AsyncSession-based).

- `base.py`: Generic CRUD base class with create, read, update, delete
- `properties.py`: Property-specific queries (filters, aggregations, relationships)
- `deals.py`: Deal-specific queries (comparison, metrics, status tracking)
- `extraction.py`: Extraction run tracking, extracted_values queries
- `documents.py`: Document metadata queries, relationships
- `transactions.py`: Financial transaction queries, filtering
- `users.py`: User queries, role-based filtering
- [Others]: Modeled after the above pattern

#### `models/` (SQLAlchemy ORM Models)

Each model represents a database table with relationships.

- `property.py`: Property model (1:N with deals, extractions, documents)
- `deal.py`: Deal model (links to property, includes financial metrics)
- `extraction.py`: ExtractedValue model (stores cell values from UW models)
- `document.py`: Document model (file metadata, relationships)
- `transaction.py`: Transaction model (financial events)
- `user.py`: User model (authentication, roles, permissions)
- `underwriting/` subdirectory:
  - `underwriting_data.py`: Financial analysis data per property
  - `operating_expense.py`: Expense categories & amounts
  - [Others]: Financial model components

**Note:** All models use SQLAlchemy 2.0 async style (`Mapped[type]`, `mapped_column()`, relationship type hints).

#### `schemas/` (Pydantic Request/Response)

Each schema module defines request and response DTOs.

- `deals.py`: DealCreate, DealUpdate, DealResponse, DealDetailResponse
- `properties.py`: PropertyCreate, PropertyUpdate, PropertyResponse, PropertyWithDealsResponse
- `extraction.py`: ExtractionRunCreate, ExtractionStatusResponse, ExtractedValueResponse
- `users.py`: UserCreate, UserResponse, UserWithRoleResponse
- [Others]: Modeled after the above pattern

#### `services/` (Business Logic Layer)

Each service directory contains domain-specific business logic.

- `extraction/`:
  - `scheduler.py`: APScheduler setup, cron-based triggering
  - `worker.py`: Batch extraction orchestration
  - `monitor_scheduler.py`: File change detection
  - Integrates with: `backend/app/extraction/` (fingerprint, extractor, cell_mapping)

- `data_extraction/`:
  - `scheduler.py`: Market data fetch scheduling
  - `worker.py`: FRED, CoStar, Census data retrieval
  - `cache.py`: Redis caching for API responses
  - `enrichment.py`: Data enrichment logic

- `construction_api/`:
  - `scheduler.py`: Construction data scheduling
  - `census.py`: Census API integration
  - `fred.py`: FRED API integration
  - `municipal.py`: Municipal data source integration

- `batch/`:
  - `batch_processor.py`: Generic batch processing orchestrator (used by extraction, data_extraction, report_worker)

- `ml/` (optional, requires requirements-ml.txt):
  - Model-based predictions for underwriting

- `report_worker.py`: PDF generation, async background task

- `interest_rate_scheduler.py`: FRED interest rate fetching

#### `extraction/` (Proforma Extraction Pipeline)

Core module for parsing UW models from Excel files.

- `file_filter.py`: Classifies files by pattern matching (UW Model, vCurrent, etc.)
- `fingerprint.py`: Identifies UW model type/variant (template-specific)
- `extractor.py`: Main extraction logic (reads cells, returns ExtractedValue objects)
- `reference_mapper.py`: Maps template type → cell addresses
- `cell_mapping.py`: Template-specific cell address definitions (fragile module)
- `group_pipeline.py`: Batch orchestration (processes multiple files, groups by fingerprint)
- `validation.py`: Validates extracted values (non-negative cap rates, ranges, etc.)

#### `middleware/` (Request/Response Processing)

8-step middleware chain applied to all FastAPI requests.

| Order | Middleware | Purpose | Key Config |
|-------|-----------|---------|-----------|
| 1 | RequestIDMiddleware | Assign unique ID to each request | Adds X-Request-ID header |
| 2 | OriginValidationMiddleware | Validate request origin | Checks CORS_ORIGINS |
| 3 | ErrorHandlerMiddleware | Catch and format exceptions | Sanitizes response bodies |
| 4 | SecurityHeadersMiddleware | Add security headers | X-Frame-Options, CSP, etc. |
| 5 | ETagMiddleware | HTTP caching via ETags | Conditional GET support |
| 6 | RateLimitMiddleware | Rate limit by IP/user | RATE_LIMIT_REQUESTS, WINDOW |
| 7 | MetricsMiddleware | Collect Prometheus metrics | Tracks latency, errors |
| 8 | CORSMiddleware | CORS policy enforcement | CORS_ORIGINS, methods, credentials |

---

### Frontend Module Organization

#### `src/features/` (Feature-Based Modules)

Each feature is a self-contained module with components, hooks, API clients, types, and tests.

| Feature | Purpose | Key Components |
|---------|---------|-----------------|
| analytics | Dashboard KPI cards, trend charts | AnalyticsPage, KPICard, TrendChart |
| auth | Login, token management | LoginPage, authStore, useLogin hook |
| construction-pipeline | Construction projects map/table | ConstructionPipelinePage, ProjectTable, GeoMap |
| dashboard-main | Home page, property cards, quick stats | DashboardMain, PropertyCard, QuickStats |
| deals | Deal kanban, comparison, details | DealsPage, KanbanBoard, DealDetailModal, ComparisonPage |
| documents | Document library, upload, metadata | DocumentsPage, DocumentGrid, UploadForm |
| extraction | File upload, extraction status, results | ExtractionDashboard, FileUploader, StatusMonitor |
| interest-rates | FRED rate charts, scheduler controls | InterestRatesPage, RateChart, SchedulerControl |
| investments | Portfolio overview, allocation charts | InvestmentsPage, PortfolioChart, AllocationBreakdown |
| mapping | Geographic visualization of properties | MappingPage, PropertyMarkers, SubmarketLayer |
| market | CoStar submarket data, trends | MarketPage, SubmarketGrid, TrendAnalysis |
| property-detail | Single property detail view | PropertyDetailPage, PropertyMetrics, DealList |
| reporting-suite | Report template selection, PDF generation | ReportingSuitePage, TemplateSelector, PDFPreview |
| sales-analysis | Sales comps, trends, filters | SalesAnalysisPage, CompsTable, TrendChart |
| search | Global search, filters, suggestions | SearchPage, GlobalSearchInput, FilterPanel |
| transactions | Financial transaction ledger | TransactionsPage, TransactionTable, Filters |
| underwriting | Proforma display, returns analysis | [returns data lazy-loaded in deals detail] |

**Pattern:** Each feature has:
- `index.ts` (export main component)
- Components directory (UI components)
- `hooks.ts` (React hooks, API calls)
- `api.ts` (API client methods)
- `types.ts` (TypeScript types)
- `__tests__/` (colocated unit/integration tests)

#### `src/lib/api/` (API Client Layer)

**Two API clients:**

1. **Legacy Client: `src/lib/api.ts` (axios)**
   - Do NOT extend; deprecated
   - Used for some existing endpoints
   - Attaches Bearer token to all requests from `localStorage.token`

2. **Current Client: `src/lib/api/client.ts` (fetch-based)**
   - Use for all new work
   - Fetch-based with Zod schema validation
   - Attaches Bearer token from `authStore.getToken()`

**Schema Transformation:**
- `src/lib/api/schemas/`: Zod schemas that transform API responses
- Snake case (backend) → camelCase (frontend)
- Example: `going_in_cap_rate` → `goingInCapRate`

#### `src/stores/` (Zustand State Management)

- `authStore.ts`: JWT token, `isAuthenticated`, `initialize()` on app load
- `dashboardStore.ts`: Dashboard state (filters, selected properties)
- [Others]: Feature-specific state (deals, properties, etc.)

#### `src/components/` (Shared UI Components)

- shadcn/ui primitives (Button, Dialog, Input, Select, Tabs, etc.)
- Custom components: KPICard, PropertyCard, DealComparisonTable, etc.
- ErrorBoundary, SuspenseWrapper for error/loading handling

---

## 6. Frontend Architecture

### Routing Strategy

**Router Location:** `src/app/router.tsx`

**Guard Pattern:**
```typescript
function RequireAuth() {
  const { isAuthenticated, isLoading } = useAuthStore();
  if (isLoading) return <LoadingSpinner />;
  if (!isAuthenticated) return <Navigate to="/login" />;
  return <Outlet />;
}
```

**Lazy Loading Pattern:**
```typescript
function LazyRoute({ children }) {
  return <PageSuspenseWrapper>{children}</PageSuspenseWrapper>;
}

// All routes wrapped:
{
  path: 'deals',
  element: (
    <FeatureErrorBoundary featureName="Deals">
      <LazyRoute>
        <DealsPage />
      </LazyRoute>
    </FeatureErrorBoundary>
  ),
}
```

**Future Flags:**
- `v7_startTransition: true` enabled in `createBrowserRouter()` (React 19 compatibility)

### Code Splitting Strategy

**Vite Manual Chunks:** Organized by dependency type (see Vite config above).

**Dynamic Imports:** Heavy libraries lazy-loaded:
- `jspdf` (PDF export)
- `exceljs` (Excel export)
- `html2canvas` (screenshot capture)

**Chunk Sizes (actual from build):**
- vendor-charts: 455KB (⚠️ warning, deferred)
- exceljs: 937KB (⚠️ warning, deferred — loaded on-demand for export features)

### Authentication Flow

1. **On App Load:**
   - `src/app/App.tsx` calls `useAuthStore.initialize()`
   - Validates JWT from `localStorage` (or redirects to login)

2. **Login:**
   - POST `/api/v1/auth/login` with credentials
   - Response: `{ accessToken, refreshToken }`
   - Store tokens in `localStorage` + `authStore`

3. **Protected Requests:**
   - Both API clients attach Bearer token:
     - `Authorization: Bearer <token>`
   - Token from `localStorage` (legacy) or `authStore.getToken()` (new)

4. **Token Refresh:**
   - If 401 response, POST `/api/v1/auth/refresh` with refresh token
   - Get new access token, retry original request

5. **Logout:**
   - Clear `localStorage`, clear `authStore`, redirect to `/login`

### Data Fetching Pattern

**TanStack React Query:**
- All API calls via hooks from `@tanstack/react-query`
- Caching, refetch, staleTime managed automatically
- Example:
  ```typescript
  const { data: deals } = useQuery({
    queryKey: ['deals'],
    queryFn: () => dealsAPI.getDeals(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
  ```

**Prefetching:**
- `src/hooks/usePrefetchDashboard()` prefetches frequently-used queries on app load
- Improves perceived performance

### Form Handling

**React Hook Form + Zod:**
```typescript
const { register, handleSubmit, formState: { errors } } = useForm({
  resolver: zodResolver(dealSchema),
});

// Schema defined in src/lib/api/schemas/deals.ts
const dealSchema = z.object({
  address: z.string(),
  purchasePrice: z.number(),
  // ...
});
```

---

## 7. Middleware Chain (Backend)

### Middleware Execution Order

All middleware registered in `backend/app/main.py` (lines ~180-220).

**Order (inner-to-outer, request → response):**

1. **RequestIDMiddleware** (lines ~180-185)
   - **Purpose:** Assign unique ID to each request for tracing
   - **Config:** None (always enabled)
   - **Effect:** Adds `X-Request-ID` header to response
   - **Use case:** Debugging, log correlation

2. **OriginValidationMiddleware** (lines ~185-190)
   - **Purpose:** Validate request origin against CORS_ORIGINS
   - **Config:** `settings.CORS_ORIGINS` (list of 7 allowed domains)
   - **Effect:** Rejects requests from non-whitelisted origins with 403
   - **Use case:** CORS security

3. **ErrorHandlerMiddleware** (lines ~190-195)
   - **Purpose:** Catch exceptions and format error responses
   - **Config:** None (always enabled)
   - **Effect:** Returns JSON error response with status code, message, request ID
   - **Use case:** Consistent error responses, prevent info leaks

4. **SecurityHeadersMiddleware** (lines ~195-200)
   - **Purpose:** Add HTTP security headers
   - **Config:** None (hardcoded headers)
   - **Headers Added:**
     - `X-Content-Type-Options: nosniff` (prevent MIME type sniffing)
     - `X-Frame-Options: DENY` (prevent clickjacking)
     - `X-XSS-Protection: 1; mode=block` (XSS protection)
     - `Strict-Transport-Security: max-age=31536000` (HSTS)
   - **Use case:** Security hardening

5. **ETagMiddleware** (lines ~200-205)
   - **Purpose:** Support HTTP conditional caching via ETags
   - **Config:** None (auto-generated)
   - **Effect:** Adds `ETag` header; returns 304 Not Modified if matching If-None-Match
   - **Use case:** Bandwidth reduction, caching optimization

6. **RateLimitMiddleware** (lines ~205-210)
   - **Purpose:** Rate limit requests by IP and/or user
   - **Config:**
     - `RATE_LIMIT_ENABLED: bool = True`
     - `RATE_LIMIT_REQUESTS: int = 100` (per window)
     - `RATE_LIMIT_WINDOW: int = 60` (seconds)
     - `RATE_LIMIT_AUTH_REQUESTS: int = 5` (per window)
     - `RATE_LIMIT_AUTH_WINDOW: int = 60` (seconds)
   - **Effect:** Returns 429 Too Many Requests if limit exceeded
   - **Backend:** Redis (if available) or in-memory storage
   - **Use case:** DDoS mitigation, API abuse prevention

7. **MetricsMiddleware** (lines ~210-215)
   - **Purpose:** Collect Prometheus metrics for monitoring
   - **Config:** None (always enabled)
   - **Metrics Collected:**
     - Request count (by method, path, status)
     - Request latency (histogram)
     - Error count (by type)
   - **Endpoint:** `/metrics` (Prometheus format)
   - **Use case:** Performance monitoring, alerting

8. **CORSMiddleware** (lines ~215-220, last)
   - **Purpose:** CORS policy enforcement
   - **Config:**
     - `allow_origins`: `settings.CORS_ORIGINS` (7 domains)
     - `allow_methods`: ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
     - `allow_headers`: ["*"] (all headers)
     - `allow_credentials`: True (cookies, auth headers)
   - **Effect:** Adds CORS headers to response; handles preflight OPTIONS
   - **Use case:** Cross-origin request handling

---

## 8. Dependencies

### Backend Dependencies (`backend/requirements.txt`, 75 lines)

#### Core Framework & Server

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | >=0.109.0,<1.0.0 | Web framework |
| uvicorn[standard] | >=0.27.0,<1.0.0 | ASGI server |
| python-multipart | >=0.0.6,<1.0.0 | Form parsing |

#### Database & ORM

| Package | Version | Purpose |
|---------|---------|---------|
| sqlalchemy | >=2.0.25,<3.0.0 | ORM (2.0 async-first) |
| psycopg2-binary | >=2.9.9,<3.0.0 | PostgreSQL driver (sync) |
| asyncpg | >=0.29.0,<1.0.0 | PostgreSQL driver (async) |
| alembic | >=1.13.1,<2.0.0 | Schema migrations |

#### Caching & Real-Time

| Package | Version | Purpose |
|---------|---------|---------|
| redis | >=5.0.1,<6.0.0 | Cache & rate limit backend |
| websockets | >=12.0,<13.0 | WebSocket support |
| python-socketio | >=5.11.0,<6.0.0 | WebSocket server |

#### Email

| Package | Version | Purpose |
|---------|---------|---------|
| aiosmtplib | >=3.0.1,<4.0.0 | Async SMTP client |
| email-validator | >=2.1.0,<3.0.0 | Email validation |
| jinja2 | >=3.1.3,<4.0.0 | Email templates |

#### Data Processing

| Package | Version | Purpose |
|---------|---------|---------|
| numpy | >=1.26.3,<2.0.0 | Numerical computing (used by pandas, extraction) |
| pandas | >=2.2.0,<3.0.0 | Data analysis, Excel parsing |
| pydantic | >=2.5.3,<3.0.0 | API schemas, validation |
| pydantic-settings | >=2.1.0,<3.0.0 | Config management |
| python-dateutil | >=2.8.2,<3.0.0 | Date utilities |

#### Excel Extraction

| Package | Version | Purpose |
|---------|---------|---------|
| pyxlsb | >=1.0.10,<2.0.0 | Parse .xlsb files (binary Excel) |
| openpyxl | >=3.1.0,<4.0.0 | Parse .xlsx/.xlsm files |

#### External APIs & Scheduling

| Package | Version | Purpose |
|---------|---------|---------|
| msal | >=1.24.0,<2.0.0 | Azure AD authentication (SharePoint) |
| structlog | >=23.1.0,<24.0.0 | Structured logging |
| aiohttp | >=3.8.0,<4.0.0 | Async HTTP client (external APIs) |
| apscheduler | >=3.10.0,<4.0.0 | Cron job scheduling (extraction, market data) |

#### Authentication & Security

| Package | Version | Purpose |
|---------|---------|---------|
| PyJWT[crypto] | >=2.8.0,<3.0.0 | JWT token generation/validation |
| passlib[bcrypt] | >=1.7.4,<2.0.0 | Password hashing |
| bcrypt | >=4.1.0,<5.0.0 | bcrypt algorithm |
| httpx | >=0.26.0,<1.0.0 | HTTP client (rate limit, retry logic) |

#### Utilities & Logging

| Package | Version | Purpose |
|---------|---------|---------|
| python-dotenv | >=1.0.1,<2.0.0 | .env file loading |
| loguru | >=0.7.2,<1.0.0 | Enhanced logging (used throughout) |
| tenacity | >=8.2.3,<9.0.0 | Retry logic |

#### Monitoring

| Package | Version | Purpose |
|---------|---------|---------|
| prometheus-client | >=0.19.0,<1.0.0 | Prometheus metrics export |
| psutil | >=5.9.8,<6.0.0 | System resource monitoring |

#### API Documentation

| Package | Version | Purpose |
|---------|---------|---------|
| openapi-schema-pydantic | >=1.2.4,<2.0.0 | OpenAPI schema (FastAPI docs) |

#### Testing

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >=7.4.4,<8.0.0 | Test framework |
| pytest-asyncio | >=0.23.3,<1.0.0 | Async test support |
| pytest-cov | >=4.1.0,<5.0.0 | Coverage reporting |
| pytest-timeout | >=2.2.0,<3.0.0 | Test timeout protection |
| aiosqlite | >=0.19.0,<1.0.0 | SQLite async driver (test DB) |

#### Development

| Package | Version | Purpose |
|---------|---------|---------|
| ruff | >=0.4.0,<1.0.0 | Fast linter/formatter |
| black | >=24.1.1,<25.0.0 | Code formatter |
| isort | >=5.13.2,<6.0.0 | Import sorting |
| mypy | >=1.8.0,<2.0.0 | Static type checking |
| flake8 | >=7.0.0,<8.0.0 | Linting |
| ipython | >=8.21.0,<9.0.0 | Interactive shell |

### Frontend Dependencies (`package.json`, 55 direct dependencies)

#### React & Routing

| Package | Version | Purpose |
|---------|---------|---------|
| react | ^19.2.0 | UI library |
| react-dom | ^19.2.0 | DOM rendering |
| react-router-dom | ^6.30.1 | Client-side routing |

#### UI Components & Styling

| Package | Version | Purpose |
|---------|---------|---------|
| @radix-ui/react-* | ^1.x | Accessible UI components (9 packages: accordion, alert-dialog, checkbox, dialog, dropdown-menu, label, select, separator, slot, tabs, tooltip) |
| lucide-react | ^0.553.0 | Icon library |
| tailwindcss | ^3.4.18 | Utility CSS framework |
| tailwind-merge | ^3.4.0 | Merge Tailwind class names |
| class-variance-authority | ^0.7.1 | Component style variants |
| clsx | ^2.1.1 | Conditional CSS classes |

#### Data & State Management

| Package | Version | Purpose |
|---------|---------|---------|
| @tanstack/react-query | ^5.90.8 | Server state, caching |
| @tanstack/react-table | ^8.21.3 | Headless table component |
| @tanstack/react-virtual | ^3.13.21 | Virtual scrolling (large lists) |
| zustand | ^5.0.8 | Lightweight state management |

#### Forms & Validation

| Package | Version | Purpose |
|---------|---------|---------|
| react-hook-form | ^7.66.0 | Form state management |
| @hookform/resolvers | ^5.2.2 | Form validation resolvers (Zod, Yup, etc.) |
| zod | ^4.1.12 | Schema validation (API responses, forms) |
| cmdk | ^1.1.1 | Command menu (search/filters) |

#### Data Visualization

| Package | Version | Purpose |
|---------|---------|---------|
| recharts | ^2.15.4 | Chart library (line, bar, pie, etc.) |
| date-fns | ^4.1.0 | Date utilities |

#### Geographic Data

| Package | Version | Purpose |
|---------|---------|---------|
| leaflet | 1.9 | Maps library |
| react-leaflet | ^4.2.1 | React wrapper for Leaflet |
| leaflet.markercluster | 1.5 | Marker clustering plugin |

#### Drag & Drop

| Package | Version | Purpose |
|---------|---------|---------|
| @dnd-kit/core | ^6.3.1 | Drag-drop system |
| @dnd-kit/sortable | ^10.0.0 | Sortable lists/kanban |
| @dnd-kit/utilities | ^3.2.2 | Utility functions |

#### File Exports

| Package | Version | Purpose |
|---------|---------|---------|
| exceljs | ^4.4.0 | Excel (.xlsx) generation (large, lazy-loaded) |
| jspdf | ^4.2.0 | PDF generation (lazy-loaded) |

#### Utilities

| Package | Version | Purpose |
|---------|---------|---------|
| fuse.js | ^7.1.0 | Fuzzy search |

#### Development & Testing

| Package | Version | Purpose |
|---------|---------|---------|
| vite | ^7.2.2 | Build tool & dev server |
| vitest | ^4.0.15 | Unit test framework |
| @vitest/coverage-v8 | ^4.0.15 | Coverage reporting |
| @playwright/test | ^1.57.0 | E2E testing |
| typescript | ~5.9.3 | Static typing |
| typescript-eslint | ^8.46.3 | TypeScript linting |
| eslint | ^9.39.1 | Code linting |
| eslint-plugin-react-hooks | ^7.0.1 | React hooks linting |
| eslint-plugin-react-refresh | ^0.4.24 | React Fast Refresh linting |
| @vitejs/plugin-react | ^5.1.0 | Vite React plugin (Fast Refresh) |
| autoprefixer | ^10.4.22 | CSS vendor prefixes |
| postcss | ^8.5.6 | CSS processing |
| @testing-library/react | ^16.3.0 | React component testing utilities |
| @testing-library/dom | ^10.4.1 | DOM testing utilities |
| @testing-library/jest-dom | ^6.9.1 | Jest matchers for DOM |
| @testing-library/user-event | ^14.6.1 | User interaction simulation |
| jsdom | ^27.2.0 | DOM implementation (test environment) |
| concurrently | ^9.2.1 | Run multiple commands (dev:all) |
| globals | ^16.5.0 | Global variable definitions |

---

## Summary

This discovery document maps the complete architecture of the B&R Capital Dashboard project:

- **Backend:** FastAPI with 18 endpoint routers, 8-layer middleware chain, 6 scheduled job services (extraction, monitoring, market data, interest rates, construction, reporting)
- **Frontend:** React 19 with 17 feature modules, React Router v6 with RequireAuth guard, TanStack Query + Zustand for state
- **Configuration:** Pydantic Settings with 7 logical groups (App, Auth, Database, External, Extraction, Construction, Market)
- **Database:** PostgreSQL primary + separate market analysis DB, Redis for caching/rate-limit/token-blacklist
- **Deployment:** Docker Compose with PostgreSQL, Redis, FastAPI backend, Nginx frontend
- **Testing:** 4,230+ total tests (2,956 backend + 1,274 frontend), all passing
- **Dev Workflow:** `npm run dev:all` for concurrent backend + frontend development

All paths, line numbers, and technical details are concrete and verifiable.
