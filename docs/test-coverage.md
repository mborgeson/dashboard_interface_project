# Test Coverage Report

Generated: 2026-03-10

**Project:** Dashboard Interface -- B&R Capital
**Backend:** 2,155 tests collected (9 deselected) across 99 test files (pytest, SQLite in-memory)
**Frontend:** 985 tests across 63 test files (vitest)
**Total:** 3,140 tests
**Backend line coverage:** 26.20% (below 30% threshold -- see analysis in Section 6)
**Previous baseline (2026-03-09):** 3,099 tests

---

## Table of Contents

1. [Test Infrastructure](#1-test-infrastructure)
2. [Backend Test File Map](#2-backend-test-file-map)
3. [Frontend Test File Map](#3-frontend-test-file-map)
4. [Backend Coverage Gaps](#4-backend-coverage-gaps)
5. [Frontend Coverage Gaps](#5-frontend-coverage-gaps)
6. [Prioritized Gap List with Severity](#6-prioritized-gap-list-with-severity)
7. [Test Strategy and Conventions](#7-test-strategy-and-conventions)

---

## 1. Test Infrastructure

### Backend (pytest)

| Item | Value |
|------|-------|
| Framework | pytest + pytest-asyncio |
| Database | SQLite in-memory, `StaticPool`, `aiosqlite` |
| HTTP Client | httpx `AsyncClient` with `ASGITransport` |
| Factories | factory_boy (`tests/factories.py`): `UserFactory`, `AdminUserFactory`, `AnalystUserFactory`, `DealFactory`, `PropertyFactory` |
| Coverage tool | pytest-cov (HTML report to `coverage_html/`) |
| Run command | `cd backend && python -m pytest` |
| Config | `backend/pyproject.toml` -- `asyncio_mode = "auto"`, 30% coverage threshold |

**Key fixtures** (defined in `tests/conftest.py`):

| Fixture | Scope | Description |
|---------|-------|-------------|
| `db_session` | function | Fresh async session; creates/drops all tables per test |
| `cleanup_engine` | session | Disposes async engine after all tests |
| `client` | function | httpx `AsyncClient` wired to FastAPI app with DB override |
| `sample_user` / `sample_admin` | function | Pre-inserted User rows (analyst/admin) |
| `sample_property` | function | Pre-inserted Property with Phoenix MSA defaults |
| `sample_deal` | function | Pre-inserted Deal linked to sample_property |
| `auth_headers` | function | `{"Authorization": "Bearer <analyst_jwt>"}` |
| `admin_auth_headers` | function | `{"Authorization": "Bearer <admin_jwt>"}` |

**Auth testing convention:**
- GET endpoints: `auth_headers` (analyst role)
- POST/PUT/DELETE endpoints: `admin_auth_headers` (admin role)
- Unauthenticated requests: assert 401

**SQLite limitations in tests:**
- No `server_default` -- all timestamp defaults use Python-side `default=datetime.now(UTC)`
- `begin_nested()` unreliable with `StaticPool`
- Explicit `created_at`/`updated_at` required when inserting test data

### Frontend (vitest)

| Item | Value |
|------|-------|
| Framework | vitest + React Testing Library + jsdom |
| Run command | `npm run test:run` (single run), `npm run test` (watch) |
| E2E | Playwright (`npm run test:e2e`) -- separate from vitest suite |
| Test colocation | Tests in `__tests__/` directories adjacent to source, or in `src/test/` |

**Common test patterns:**
- `renderWithProviders()` -- wraps components in QueryClientProvider + MemoryRouter
- Mock API calls via `vi.mock()` on hook modules
- React Router future flags set in test wrappers to match production config

---

## 2. Backend Test File Map

### API Tests (`tests/test_api/`) -- 16 files

| Test File | Tests What | Source Under Test |
|-----------|-----------|-------------------|
| `test_auth.py` | Login, refresh rotation, logout, replay detection, JWT validation | `api/v1/endpoints/auth.py` |
| `test_deals.py` | CRUD, kanban, stage updates, filtering, pagination, comparison | `api/v1/endpoints/deals.py` |
| `test_deal_optimistic_locking.py` | Version column, concurrent update detection, 409 responses | `api/v1/endpoints/deals.py` (PATCH optimistic) |
| `test_properties.py` | CRUD, dashboard endpoint, enrichment, cursor pagination | `api/v1/endpoints/properties.py` |
| `test_property_financial_enrichment.py` | Batch enrichment from extracted_values | `api/v1/endpoints/properties.py` (dashboard) |
| `test_users.py` | User management, role enforcement | `api/v1/endpoints/users.py` |
| `test_analytics.py` | Dashboard analytics, deal pipeline stats | `api/v1/endpoints/analytics.py` |
| `test_exports.py` | CSV/Excel export generation | `api/v1/endpoints/exports.py` |
| `test_extraction.py` | Extraction run triggers, value queries | `api/v1/endpoints/extraction/` |
| `test_grouping.py` | Group pipeline API (phases 1-3) | `api/v1/endpoints/extraction/grouping.py` |
| `test_grouping_phase4.py` | Group pipeline phase 4 (extraction + approval) | `api/v1/endpoints/extraction/grouping.py` |
| `test_health.py` | Health check responses, dependency statuses | `api/v1/endpoints/health.py` |
| `test_monitoring.py` | Prometheus metrics endpoint, pool stats | `api/v1/endpoints/monitoring.py` |
| `test_construction_pipeline.py` | Pipeline CRUD | `api/v1/endpoints/construction_pipeline.py` |
| `test_sales_analysis.py` | Sales comp queries | `api/v1/endpoints/sales_analysis.py` |
| `test_reporting_settings.py` | Report settings read/write | `api/v1/endpoints/reporting.py` |
| `test_audit_log.py` | Audit log entries | `api/v1/endpoints/admin.py` |

### Activity API Tests (`tests/api/v1/`) -- 3 files

| Test File | Tests What | Source Under Test |
|-----------|-----------|-------------------|
| `test_activity_log.py` | Structured activity log CRUD | `api/v1/endpoints/deals.py` (activity-log) |
| `test_deal_activities.py` | Deal activity feed, creation | `api/v1/endpoints/deals.py` (activities) |
| `test_property_activities.py` | Property activity feed, creation | `api/v1/endpoints/properties.py` (activities) |

### CRUD Tests (`tests/test_crud/`) -- 7 files

| Test File | Tests What | Source Under Test |
|-----------|-----------|-------------------|
| `test_base_pagination.py` | `PaginatedResult`, `CursorPaginatedResult`, `get_paginated`, cursor encoding/decoding | `crud/base.py` |
| `test_cursor_pagination.py` | Keyset cursor pagination, direction handling, type coercion | `crud/base.py` |
| `test_crud.py` | Base CRUD operations, soft-delete, restore | `crud/base.py` |
| `test_crud_deal.py` | Deal CRUD, optimistic locking, kanban grouping | `crud/crud_deal.py` |
| `test_crud_transaction.py` | Transaction CRUD, soft-delete | `crud/crud_transaction.py` |
| `test_crud_user.py` | User authentication, password hashing | `crud/crud_user.py` |
| `test_extraction.py` | Extraction CRUD operations | `crud/extraction.py` |

### Core Tests (`tests/test_core/`) -- 7 files

| Test File | Tests What | Source Under Test |
|-----------|-----------|-------------------|
| `test_security.py` | JWT creation, decoding, expiry | `core/security.py` |
| `test_permissions.py` | Role hierarchy, `has_role`, dependency enforcement | `core/permissions.py` |
| `test_token_blacklist.py` | Blacklist add/check, memory/Redis fallback, TTL expiry | `core/token_blacklist.py` |
| `test_api_key_auth.py` | `hmac.compare_digest` validation, missing/invalid key rejection | `core/api_key_auth.py` |
| `test_sanitization.py` | HTML stripping, XSS patterns, event handlers, URI schemes | `core/sanitization.py` |
| `test_file_validation.py` | Magic bytes, extension, MIME, size limit checks | `core/file_validation.py` |
| `test_config.py` | Settings loading, `SECRET_KEY` validation, CORS parsing | `core/config.py` |

### Middleware Tests (`tests/test_middleware/`) -- 4 files

| Test File | Tests What | Source Under Test |
|-----------|-----------|-------------------|
| `test_request_id.py` | Header propagation, ContextVar availability, UUID generation | `middleware/request_id.py` |
| `test_error_handler.py` | Exception-to-status-code mapping, `request_id` in responses | `middleware/error_handler.py` |
| `test_rate_limiter.py` | Sliding window algorithm, 429 responses, headers, path-specific rules | `middleware/rate_limiter.py` |
| `test_security_headers.py` | CSP, HSTS, X-Frame-Options presence | `main.py` (inline middleware) |

### Model Tests (`tests/test_models/`) -- 8 files

| Test File | Tests What | Source Under Test |
|-----------|-----------|-------------------|
| `test_deal.py` | Stage updates, activity log, version column | `models/deal.py` |
| `test_property.py` | Computed properties, constraints | `models/property.py` |
| `test_financial_constraints.py` | All 41 CHECK constraints across Deal and Property | `models/deal.py`, `models/property.py` |
| `test_soft_delete.py` | `soft_delete()`, `restore()`, filter behavior | `models/base.py` (SoftDeleteMixin) |
| `test_construction.py` | Construction pipeline model | `models/construction.py` |
| `test_sales_data.py` | Sales data model | `models/sales_data.py` |
| `test_reminder_dismissal.py` | Dismissal model | `models/reminder_dismissal.py` |
| `test_user.py` | User model, password hash | `models/user.py` |

### Extraction Tests (`tests/test_extraction/`) -- 17 files

| Test File | Tests What | Source Under Test |
|-----------|-----------|-------------------|
| `test_extractor.py` | Cell value extraction, error handling, NaN fallback | `extraction/extractor.py` |
| `test_fingerprint.py` | `SheetFingerprint`, `FileFingerprint`, signature hashing | `extraction/fingerprint.py` |
| `test_grouping.py` | File grouping, clustering thresholds | `extraction/grouping.py` |
| `test_group_discovery.py` | Discovery phase, file scanning | `extraction/group_pipeline.py` |
| `test_group_extraction.py` | Extraction phase, batch processing | `extraction/group_pipeline.py` |
| `test_reference_mapper.py` | Field to canonical name mapping | `extraction/reference_mapper.py` |
| `test_output_validation.py` | All 9 validation rules (cap_rate, price, units, etc.) | `extraction/output_validation.py` |
| `test_candidate_filter.py` | FileFilter pattern matching | `extraction/file_filter.py` |
| `test_sharepoint_integration.py` | SharePoint listing/download mocks | `extraction/sharepoint.py` |
| `test_proforma_expansion.py` | Proforma Returns field extraction (30 fields) | `extraction/extractor.py` + `cell_mapping.py` |
| `test_cell_mapping_accuracy.py` | Cell address correctness per template | `extraction/cell_mapping.py` |
| `test_data_accuracy.py` | Known-value data correctness assertions | `extraction/` (integration) |
| `test_extraction_completeness.py` | Field completeness per property | `extraction/` (integration) |
| `test_extraction_regression.py` | 49 regression tests for known extraction results | `extraction/` (regression) |
| `test_phase1_fixes.py` | Phase 1 pipeline fixes | `extraction/` (regression) |
| `test_phase2_fixes.py` | Phase 2 pipeline fixes | `extraction/` (regression) |
| `test_phase3_performance.py` | Phase 3 performance optimizations | `extraction/` (regression) |
| `test_phase4_architecture.py` | Phase 4 architecture changes | `extraction/group_pipeline.py` |
| `test_phase4_extraction.py` | Phase 4 extraction correctness | `extraction/group_pipeline.py` |
| `test_phase5_observability.py` | Phase 5 observability/metrics | `extraction/metrics.py` |

### Service Tests (`tests/test_services/`) -- 21 files

| Test File | Tests What | Source Under Test |
|-----------|-----------|-------------------|
| `test_redis_service.py` | Redis connect, get, set, pub/sub | `services/redis_service.py` |
| `test_websocket_service.py` | Channel subscribe, broadcast, disconnect | `services/websocket_manager.py` |
| `test_export_service.py` | CSV/Excel generation | `services/export_service.py` |
| `test_pdf_service.py` | PDF report generation | `services/pdf_service.py` |
| `test_email_service.py` | SMTP send, rate limiting | `services/email_service.py` |
| `test_audit_service.py` | Audit log writes | `services/audit_service.py` |
| `test_construction_import.py` | Data import pipeline | `services/construction_import.py` |
| `test_sales_import.py` | Sales comp import | `services/sales_import.py` |
| `test_file_monitor.py` | Change detection | `services/extraction/file_monitor.py` |
| `batch/test_batch_processor.py` | Batch job processing | `services/batch/batch_processor.py` |
| `batch/test_job_queue.py` | Async job queue | `services/batch/job_queue.py` |
| `batch/test_scheduler.py` | Batch scheduler | `services/batch/scheduler.py` |
| `batch/test_task_executor.py` | Task execution | `services/batch/task_executor.py` |
| `ml/test_model_manager.py` | ML model lifecycle | `services/ml/model_manager.py` |
| `ml/test_rent_growth_predictor.py` | Rent growth prediction | `services/ml/rent_growth_predictor.py` |
| `monitoring/test_collectors.py` | Prometheus metric collection | `services/monitoring/collectors.py` |
| `monitoring/test_metrics.py` | Metrics manager | `services/monitoring/metrics.py` |
| `workflow/test_workflow_engine.py` | Workflow execution engine | `services/workflow/workflow_engine.py` |
| `workflow/test_step_handlers.py` | HTTP, DB, notification step handlers | `services/workflow/step_handlers.py` |
| `test_construction_api/` (7 files) | Census BPS, FRED permits, BLS employment, Mesa SODA, Tempe BLDS, Gilbert ArcGIS, address matcher, scheduler | `services/construction_api/` |

---

## 3. Frontend Test File Map

### Shared Components (`src/components/`) -- 17 files

| Test File | Tests What | Source Under Test |
|-----------|-----------|-------------------|
| `ErrorBoundary.test.tsx` | Error boundary rendering, fallback, recovery | `ErrorBoundary.tsx` |
| `quick-actions/QuickActions.test.tsx` | Quick actions panel | `quick-actions/` components |
| `skeletons/ChartSkeleton.test.tsx` | Chart skeleton rendering | `skeletons/ChartSkeleton.tsx` |
| `skeletons/DealCardSkeleton.test.tsx` | Deal card skeleton | `skeletons/DealCardSkeleton.tsx` |
| `skeletons/PropertyCardSkeleton.test.tsx` | Property card skeleton | `skeletons/PropertyCardSkeleton.tsx` |
| `skeletons/StatCardSkeleton.test.tsx` | Stat card skeleton | `skeletons/StatCardSkeleton.tsx` |
| `skeletons/TableSkeleton.test.tsx` | Table skeleton | `skeletons/TableSkeleton.tsx` |
| `ui/LazyImage.test.tsx` | Lazy image loading | `ui/LazyImage.tsx` |
| `ui/ToggleButton.test.tsx` | Toggle button state | `ui/ToggleButton.tsx` |
| `ui/badge.test.tsx` | Badge variants | `ui/badge.tsx` |
| `ui/button.test.tsx` | Button variants, click | `ui/button.tsx` |
| `ui/card.test.tsx` | Card composition | `ui/card.tsx` |
| `ui/empty-state.test.tsx` | Empty state rendering | `ui/empty-state.tsx` |
| `ui/error-state.test.tsx` | Error state rendering | `ui/error-state.tsx` |
| `ui/input.test.tsx` | Input component | `ui/input.tsx` |
| `ui/skeleton.test.tsx` | Skeleton animation | `ui/skeleton.tsx` |
| `ui/toast.test.tsx` | Toast notification | `ui/toast.tsx` |

### Feature Tests -- 28 files

| Test File | Tests What | Source Under Test |
|-----------|-----------|-------------------|
| `analytics/AnalyticsPage.test.tsx` | Analytics page rendering, KPI cards | `analytics/AnalyticsPage.tsx` |
| `construction-pipeline/types.test.ts` | Type shape validation | `construction-pipeline/` types |
| `construction-pipeline/ConstructionSummaryCards.test.tsx` | Summary cards | `construction-pipeline/components/ConstructionSummaryCards.tsx` |
| `construction-pipeline/PipelineFunnel.test.tsx` | Funnel chart | `construction-pipeline/components/PipelineFunnel.tsx` |
| `construction-pipeline/PipelineMap.test.tsx` | Map component | `construction-pipeline/components/PipelineMap.tsx` |
| `construction-pipeline/PipelineTable.test.tsx` | Table component | `construction-pipeline/components/PipelineTable.tsx` |
| `construction-pipeline/useConstructionData.test.tsx` | Data hook | `construction-pipeline/hooks/useConstructionData.ts` |
| `dashboard-main/DashboardMain.test.tsx` | Dashboard page rendering | `dashboard-main/DashboardMain.tsx` |
| `deals/data-display-regression.test.tsx` | Deal data display regression | `deals/` components |
| `deals/comparison/Comparison.test.tsx` | Deal comparison flow | `deals/components/comparison/` |
| `extraction/ExtractionDashboard.test.tsx` | Extraction dashboard | `extraction/ExtractionDashboard.tsx` |
| `extraction/GroupList.test.tsx` | Group list display | `extraction/components/GroupList.tsx` |
| `extraction/GroupPipelineStepper.test.tsx` | Pipeline stepper UI | `extraction/components/GroupPipelineStepper.tsx` |
| `extraction/useExtraction.test.ts` | Extraction hook queries | `extraction/hooks/useExtraction.ts` |
| `extraction/useGroupPipeline.test.ts` | Group pipeline hook | `extraction/hooks/useGroupPipeline.ts` |
| `investments/data-display-bugs.test.tsx` | Investments data display regression | `investments/` components |
| `mapping/PropertyDetailPanel.test.tsx` | Map property detail | `mapping/components/PropertyDetailPanel.tsx` |
| `mapping/useMapFilters.test.ts` | Map filter hook | `mapping/hooks/useMapFilters.ts` |
| `market/MarketPage.test.tsx` | Market page rendering | `market/MarketPage.tsx` |
| `property-detail/PropertyDetailPage.test.tsx` | Property detail page | `property-detail/PropertyDetailPage.tsx` |
| `property-detail/PropertyActivityFeed.test.tsx` | Activity feed component | `property-detail/components/PropertyActivityFeed/` |
| `sales-analysis/types.test.ts` | Type shape validation | `sales-analysis/` types |
| `sales-analysis/DataQualitySummary.test.tsx` | Data quality display | `sales-analysis/components/DataQualitySummary.tsx` |
| `sales-analysis/ImportNotificationBanner.test.tsx` | Import notification | `sales-analysis/components/ImportNotificationBanner.tsx` |
| `sales-analysis/MonthlyReminderBanner.test.tsx` | Monthly reminder banner | `sales-analysis/components/MonthlyReminderBanner.tsx` |
| `sales-analysis/SalesTable.test.tsx` | Sales table | `sales-analysis/components/SalesTable.tsx` |
| `sales-analysis/TimeSeriesTrends.test.tsx` | Time series chart | `sales-analysis/components/TimeSeriesTrends.tsx` |
| `sales-analysis/useSalesData.test.tsx` | Sales data hook | `sales-analysis/hooks/useSalesData.ts` |
| `transactions/useTransactionFilters.test.ts` | Transaction filter hook | `transactions/hooks/useTransactionFilters.ts` |
| `underwriting/calculations.test.ts` | Financial calculations (DSCR, LTV, YoC, etc.) | `underwriting/utils/calculations.ts` |

### Library / Infrastructure Tests -- 18 files

| Test File | Tests What | Source Under Test |
|-----------|-----------|-------------------|
| `lib/api.test.ts` | Legacy API client (axios) | `lib/api.ts` |
| `lib/config.test.ts` | Config exports, feature flags | `lib/config.ts` |
| `lib/dateUtils.test.ts` | Date parsing, formatting, relative time | `lib/dateUtils.ts` |
| `lib/api/client.test.ts` | Fetch API client, ETag, 401 handling | `lib/api/client.ts` |
| `lib/api/schemas/deal.test.ts` | Deal Zod schema transforms | `lib/api/schemas/deal.ts` |
| `lib/api/schemas/property.test.ts` | Property Zod schema transforms | `lib/api/schemas/property.ts` |
| `lib/api/schemas/reporting.test.ts` | Reporting Zod schema transforms | `lib/api/schemas/reporting.ts` |
| `lib/api/schemas/sales.test.ts` | Sales Zod schema transforms | `lib/api/schemas/sales.ts` |
| `lib/utils/formatters.test.ts` | Currency, percent, number formatters | `lib/utils/formatters.ts` |
| `hooks/useNotify.test.ts` | Notification wrapper hook | `hooks/useNotify.ts` |
| `hooks/useToast.test.ts` | Toast hook | `hooks/useToast.ts` |
| `hooks/api/useDealComparison.test.ts` | Deal comparison hook | `hooks/api/useDealComparison.ts` |
| `hooks/api/usePropertyActivities.test.ts` | Property activities hook | `hooks/api/usePropertyActivities.ts` |
| `services/errorTracking.test.ts` | Error tracking init, reporting, rate limiting | `services/errorTracking.ts` |
| `stores/notificationStore.test.ts` | Notification store actions | `stores/notificationStore.ts` |
| `stores/searchStore.test.ts` | Search store actions, recent searches | `stores/searchStore.ts` |

---

## 4. Backend Coverage Gaps

Cross-referencing the backend architecture inventory against existing test files. Each gap is an artifact documented in `docs/backend-architecture.md` that has **no dedicated test coverage**.

### 4.1 API Endpoints Without Dedicated Tests

| Endpoint Group | Path | Reason / Notes |
|---------------|------|----------------|
| Interest Rates | `GET /api/v1/interest-rates/current`, `GET /api/v1/interest-rates/history` | No `test_api/test_interest_rates.py` |
| Transactions | `GET/POST/PUT/DELETE /api/v1/transactions/*` | No `test_api/test_transactions.py` (CRUD tests exist but not API-level) |
| Documents | `GET/POST/DELETE /api/v1/documents/*` | No `test_api/test_documents.py` |
| Market Data | `GET /api/v1/market/submarkets`, `GET /api/v1/market/submarket/{name}`, `GET /api/v1/market/interest-rates` | No `test_api/test_market.py` |
| Reporting (templates/generate) | `GET /api/v1/reporting/templates`, `POST /api/v1/reporting/generate` | Only settings tested, not templates or generation |
| WebSocket | `WS /api/v1/ws/{channel}` | No WebSocket endpoint tests (service-level tests exist) |
| Deal Watchlist | `GET/POST /api/v1/deals/{id}/watchlist` | No dedicated watchlist endpoint tests |
| Deal Proforma Returns | `GET /api/v1/deals/{id}/proforma-returns` | No endpoint test |
| Admin Users | `GET /api/v1/admin/users` | Admin view not tested separately from users endpoint |

### 4.2 CRUD Layer Gaps

| CRUD Singleton | File | Test Status |
|---------------|------|-------------|
| `crud.property` | `crud_property.py` | **No dedicated test file** -- tested indirectly via API tests only. `enrich_financial_data`, `enrich_financial_data_batch`, `_build_property_conditions` untested at unit level |
| `crud.document` | `crud_document.py` | **No test file** -- `get_by_deal`, `get_by_property` untested |
| `crud.report_template` | `crud_report_template.py` | **No test file** |
| `watchlist_crud` | `crud_activity.py` | **No test file** for `toggle`, `get_user_watchlist` |
| `crud.file_monitor` | `file_monitor.py` (CRUD) | **No CRUD-level test** (service test exists) |

### 4.3 Model Gaps

| Model | File | Test Status |
|-------|------|-------------|
| `Document` | `models/document.py` | **No model test** |
| `AuditLog` | `models/audit_log.py` | **No model test** (service test exists) |
| `ActivityLog` | `models/activity_log.py` | **No model test** |
| `DealActivity` | `models/activity.py` | **No model test** (API test exists) |
| `PropertyActivity` | `models/activity.py` | **No model test** (API test exists) |
| `Watchlist` | `models/activity.py` | **No model test** |
| `ReportSettings` | `models/report_settings.py` | **No model test** |
| `ReportTemplate` | `models/report_template.py` | **No model test** |
| `MonitoredFile` | `models/monitored_file.py` | **No model test** |
| `ExtractionRun` | `models/extraction.py` | **No model test** (tested via CRUD) |
| `ExtractedValue` | `models/extraction.py` | **No model test** (tested via CRUD) |
| All 12 Underwriting models | `models/underwriting/*.py` | **No model tests** for `UnderwritingModel`, `AnnualCashflow`, `BudgetAssumptions`, `EquityReturns`, `ExitAssumptions`, `FinancingAssumptions`, `GeneralAssumptions`, `NOIAssumptions`, `PropertyReturns`, `RentComp`, `SalesComp`, `SourceTracking`, `UnitMix` |

### 4.4 Pydantic Schema Gaps

| Schema File | Test Status |
|------------|-------------|
| `schemas/deal.py` | Partially tested (via API tests), no dedicated schema validation tests for `DealCreate` sanitization edge cases |
| `schemas/property.py` | No dedicated schema tests |
| `schemas/auth.py` | Tested via API auth tests |
| `schemas/pagination.py` | Tested via `test_base_pagination.py` |
| `schemas/comparison.py` | No dedicated tests |
| `schemas/activity.py` | No dedicated schema tests |
| `schemas/activity_log.py` | No dedicated schema tests |
| `schemas/extraction.py` | No dedicated schema tests |
| `schemas/grouping.py` | No dedicated schema tests |
| `schemas/transaction.py` | No dedicated schema tests |
| `schemas/document.py` | No dedicated schema tests |
| `schemas/user.py` | No dedicated schema tests |
| `schemas/reporting.py` | No dedicated schema tests |
| `schemas/market_data.py` | No dedicated schema tests |
| `schemas/interest_rates.py` | No dedicated schema tests |
| `schemas/file_monitor.py` | No dedicated schema tests |

### 4.5 Service Gaps

| Service | File | Test Status |
|---------|------|-------------|
| `CacheService` | `core/cache.py` | **No test** -- Redis/memory fallback, TTL, invalidation patterns untested |
| `GeocodingService` | `services/geocoding.py` | **No test** |
| `MarketDataScheduler` | `services/data_extraction/scheduler.py` | **No test** |
| `InterestRateScheduler` | `services/interest_rate_scheduler.py` | **No test** |
| `InterestRateService` | `services/interest_rates.py` | **No test** -- FRED API + 5-min cache |
| `ChangeDetector` | `services/extraction/change_detector.py` | **No test** |
| `ExtractionMetrics` | `services/extraction/metrics.py` | Partially tested in phase5 tests |
| `ExtractionScheduler` | `services/extraction/scheduler.py` | **No test** |
| `MonitorScheduler` | `services/extraction/monitor_scheduler.py` | **No test** |

### 4.6 Other Backend Gaps

| Artifact | File | Test Status |
|----------|------|-------------|
| ETag middleware | `middleware/etag.py` | **No test** |
| Origin validation middleware | `main.py` (inline) | **No test** |
| Metrics middleware | `services/monitoring/middleware.py` | **No test** (collectors tested, not the middleware itself) |
| Structured logging setup | `core/logging.py` | **No test** |
| Slow query logger | `db/query_logger.py` | **No test** |
| Database session/engine | `db/session.py` | **No test** (implicitly exercised by all DB tests) |
| `ConnectionManager` (WebSocket) | `services/websocket_manager.py` | Tested, but no WebSocket protocol-level tests |

### 4.7 Coverage Number Context

The 26.20% line coverage is misleading. The test suite is strong in tested areas but many service modules have near-0% coverage because they contain production-only integrations (FRED API, SharePoint, Redis, Prometheus, APScheduler) that are difficult to test without external dependencies. The `workflow_engine.py` (8.92% covered) and `step_handlers.py` (17.76% covered) are the largest uncovered service files by line count.

---

## 5. Frontend Coverage Gaps

Cross-referencing the frontend architecture inventory against existing test files.

### 5.1 Stores Without Tests

| Store | File | Test Status |
|-------|------|-------------|
| `authStore` | `stores/authStore.ts` | **No test** -- login, logout, initialize, 401 listener untested |
| `useAppStore` | `store/useAppStore.ts` | **No test** -- sidebar/mobile menu state |

### 5.2 Zod Schemas Without Tests

| Schema | File | Test Status |
|--------|------|-------------|
| `common.ts` | `lib/api/schemas/common.ts` | **No test** -- `dateString`, `numericString` transforms |
| `construction.ts` | `lib/api/schemas/construction.ts` | **No test** -- 12 schemas |

### 5.3 Shared Hooks Without Tests

| Hook | File | Test Status |
|------|------|-------------|
| `useGlobalSearch` | `hooks/useGlobalSearch.ts` | **No test** -- Fuse.js search, debounce |
| `useFilterPersistence` | `hooks/useFilterPersistence.ts` | **No test** -- URL sync |
| `useWebSocket` | `hooks/useWebSocket.ts` | **No test** -- reconnect, backoff |
| `useCursorPagination` | `hooks/useCursorPagination.ts` | **No test** |
| `useIntersectionObserver` | `hooks/useIntersectionObserver.ts` | **No test** |
| `usePrefetch` | `hooks/usePrefetch.ts` | **No test** |
| `usePrefetchDashboard` | `hooks/usePrefetchDashboard.ts` | **No test** |

### 5.4 API Hooks Without Tests

| Hook Module | File | Test Status |
|------------|------|-------------|
| `useProperties` | `hooks/api/useProperties.ts` | **No test** -- 7 hooks |
| `useDeals` | `hooks/api/useDeals.ts` | **No test** -- 11 hooks |
| `useExtraction` (API) | `hooks/api/useExtraction.ts` | **No test** -- 10 hooks (feature hook tested, not API hook) |
| `useTransactions` | `hooks/api/useTransactions.ts` | **No test** -- 8 hooks |
| `useInterestRates` (API) | `hooks/api/useInterestRates.ts` | **No test** -- 6 hooks |
| `useDocuments` | `hooks/api/useDocuments.ts` | **No test** -- 6 hooks |
| `useMarketData` | `hooks/api/useMarketData.ts` | **No test** -- 4 hooks |
| `useReporting` | `hooks/api/useReporting.ts` | **No test** -- 8 hooks |

### 5.5 Feature-Level Hooks Without Tests

| Hook | File | Test Status |
|------|------|-------------|
| `useDeals` (feature) | `features/deals/hooks/useDeals.ts` | **No test** -- client-side filtering, drag-and-drop overrides |
| `useMarketData` (feature) | `features/market/hooks/useMarketData.ts` | **No test** -- sparkline derivation |
| `useUSAMarketData` | `features/market/hooks/useUSAMarketData.ts` | **No test** |
| `useDocuments` (feature) | `features/documents/hooks/useDocuments.ts` | **No test** |
| `useInterestRates` (feature) | `features/interest-rates/hooks/useInterestRates.ts` | **No test** |
| `useUnderwriting` | `features/underwriting/hooks/useUnderwriting.ts` | **No test** -- IRR, cash flow, sensitivity |

### 5.6 Feature Components Without Tests

Listed by feature. Only components with zero test coverage are listed.

**Dashboard Main:**
- `PropertyMap.tsx` -- map rendering
- `PortfolioPerformanceChart.tsx` -- chart
- `PropertyDistributionChart.tsx` -- chart

**Investments:**
- `InvestmentsPage.tsx` -- page-level (data-display-bugs.test.tsx covers regression only)
- `PropertyCard.tsx` -- card rendering
- `PropertyTable.tsx` -- table rendering
- `PropertyFilters.tsx` -- filter UI

**Property Detail:**
- `PropertyHero.tsx`, `OverviewTab.tsx`, `PerformanceTab.tsx`, `OperationsTab.tsx`, `FinancialsTab.tsx`, `TransactionsTab.tsx` -- all tab components

**Deals:**
- `DealsPage.tsx`, `KanbanBoard.tsx`, `KanbanColumn.tsx`, `KanbanHeader.tsx`, `KanbanFiltersBar.tsx`, `DealCard.tsx`, `DraggableDealCard.tsx`, `DealDetailModal.tsx`, `DealTimeline.tsx`, `DealFilters.tsx`, `DealPipeline.tsx`, `DealAerialMap.tsx` -- all deal page components
- `ActivityFeed/ActivityFeed.tsx`, `ActivityTimeline.tsx`, `ActivityItem.tsx`, `ActivityForm.tsx` -- activity feed
- `DealComparisonPage.tsx` -- page-level (comparison components have test)

**Analytics:**
- `KPICard.tsx`, `PerformanceCharts.tsx`, `ComparisonCharts.tsx`, `DistributionCharts.tsx`

**Market:**
- `MarketOverview.tsx`, `MarketTrendsChart.tsx`, `MarketHeatmap.tsx`, `SubmarketComparison.tsx`, `EconomicIndicators.tsx` -- all market components
- All 4 widget components

**Documents:**
- All 5 components: `DocumentsPage.tsx`, `DocumentList.tsx`, `DocumentGrid.tsx`, `DocumentCard.tsx`, `DocumentFilters.tsx`, `DocumentUploadModal.tsx`

**Interest Rates:**
- `InterestRatesPage.tsx`, `KeyRatesSnapshot.tsx`, `TreasuryYieldCurve.tsx`, `RateComparisons.tsx`, `DataSources.tsx`

**Reporting Suite:**
- All 10 components: `ReportingSuitePage.tsx`, `ReportTemplates.tsx`, `ReportQueue.tsx`, `ReportSettings.tsx`, `Distribution.tsx`, `CustomReportBuilder.tsx`, `ReportWizard/*.tsx` (6 files)

**Underwriting:**
- All 5 components: `UnderwritingModal.tsx`, `InputsTab.tsx`, `ResultsTab.tsx`, `ProjectionsTab.tsx`, `SensitivityTab.tsx`, `AssumptionsPresets.tsx`

**Transactions:**
- All 5 components: `TransactionsPage.tsx`, `TransactionTable.tsx`, `TransactionFilters.tsx`, `TransactionCharts.tsx`, `TransactionTimeline.tsx`, `TransactionSummary.tsx`

**Auth:**
- `LoginPage.tsx`

**Search:**
- `GlobalSearch.tsx`

**Mapping:**
- `MappingPage.tsx`, `MapFilterPanel.tsx`, `MapLegend.tsx` (PropertyDetailPanel tested)

### 5.7 Other Frontend Gaps

| Artifact | File | Test Status |
|----------|------|-------------|
| Calculation libraries | `lib/calculations/irr.ts`, `cashflow.ts`, `sensitivity.ts` | **No test** -- financial calculations (IRR, equity multiple, cash flow projections) |
| `cn()` utility | `lib/utils.ts` | **No test** (trivial) |
| UW exporters | `features/underwriting/utils/exporters.ts` | **No test** |
| SharePoint URL util | `features/deals/utils/sharepoint.ts` | **No test** |
| Router config | `app/router.tsx`, `app/routes.ts` | **No test** (route structure) |
| Contexts | `contexts/ToastContext.tsx`, `LoadingContext.tsx`, `QuickActionsContext.tsx` | **No test** |
| `AppLayout`, `Sidebar`, `TopNav` | `components/layout/` | **No test** |
| `ComparisonBar` | `components/comparison/ComparisonBar.tsx` | **No test** |
| `PrefetchLink` | `components/PrefetchLink.tsx` | **No test** |
| `VirtualizedTable` | `components/shared/VirtualizedTable.tsx` | **No test** |
| `VirtualList` | `components/VirtualList.tsx` | **No test** |
| `SavedFilters` | `components/filters/SavedFilters.tsx` | **No test** |

---

## 6. Prioritized Gap List with Severity

Severity levels:
- **CRITICAL** -- Financial calculations, auth/security, data integrity. Bugs here cause monetary errors or security breaches.
- **HIGH** -- Core business logic, API endpoints handling user data. Bugs affect data correctness.
- **MEDIUM** -- UI logic hooks, data transformation, middleware. Bugs cause user-facing issues but no data loss.
- **LOW** -- Presentational components, skeleton loaders, trivial utilities. Bugs are cosmetic.

### CRITICAL Gaps

| # | Artifact | Layer | Why Critical |
|---|----------|-------|-------------|
| C1 | `lib/calculations/irr.ts`, `cashflow.ts`, `sensitivity.ts` | Frontend | **Financial calculations** -- IRR, equity multiple, cash flow projections drive investment decisions. CLAUDE.md mandates tests for financial calculations. |
| C2 | `useUnderwriting` hook | Frontend | **Full underwriting engine** -- computes IRR, sensitivity analysis. Wrong output = wrong investment decisions. |
| C3 | `stores/authStore.ts` | Frontend | **Authentication state** -- login, logout, token refresh, 401 handling. Bugs lock users out or leave stale sessions. |
| C4 | `core/cache.py` (CacheService) | Backend | **Cache invalidation** -- stale cache serves wrong financial data to dashboard. Redis fallback to memory untested. |
| C5 | API: Transactions endpoints | Backend | **Financial transaction records** -- no API-level tests for CRUD operations on transactions. |
| C6 | API: Documents endpoints | Backend | **File upload with validation** -- file_validation.py is tested but the endpoint wiring is not. |
| C7 | `crud_property.py` (`enrich_financial_data_batch`) | Backend | **Batch enrichment** -- feeds all property financial data to frontend. Only tested indirectly. |

### HIGH Gaps

| # | Artifact | Layer | Why High |
|---|----------|-------|----------|
| H1 | API: Interest Rates endpoints | Backend | Business-critical market data served to users. |
| H2 | API: Market Data endpoints | Backend | Submarket/MSA data feeds multiple pages. |
| H3 | API: Deal watchlist + proforma-returns | Backend | User-facing features with no endpoint validation. |
| H4 | `hooks/api/useDeals.ts` (11 hooks) | Frontend | Core deal management -- kanban, stage updates, mutations. |
| H5 | `hooks/api/useProperties.ts` (7 hooks) | Frontend | Property CRUD and dashboard data fetching. |
| H6 | `features/deals/hooks/useDeals.ts` | Frontend | Client-side deal filtering + drag-and-drop stage overrides. |
| H7 | `crud_document.py` | Backend | Document retrieval by deal/property untested. |
| H8 | Underwriting models (12 models) | Backend | No model tests for any underwriting tables. |
| H9 | `services/interest_rates.py` | Backend | FRED API integration + caching -- data feeds InterestRatesPage. |
| H10 | API: Reporting templates + generation | Backend | Report generation endpoint not tested. |

### MEDIUM Gaps

| # | Artifact | Layer | Why Medium |
|---|----------|-------|-----------|
| M1 | `useGlobalSearch` | Frontend | Fuse.js search + debounce across entities. |
| M2 | `useWebSocket` | Frontend | Real-time updates with reconnect logic. |
| M3 | `useFilterPersistence` | Frontend | URL sync for shareable filter state. |
| M4 | `useCursorPagination` | Frontend | Pagination state management. |
| M5 | ETag middleware | Backend | Caching correctness -- wrong ETags cause stale data. |
| M6 | Origin validation middleware | Backend | CSRF defense-in-depth. |
| M7 | Zod `common.ts` schemas | Frontend | `dateString`, `numericString` transforms used by all other schemas. |
| M8 | Zod `construction.ts` schemas | Frontend | 12 schemas for construction pipeline data. |
| M9 | `GeocodingService` | Backend | Nominatim geocoding -- incorrect coords affect map display. |
| M10 | `store/useAppStore.ts` | Frontend | Sidebar/mobile menu state. |
| M11 | All 3 scheduler services | Backend | APScheduler lifecycle -- startup/shutdown correctness. |
| M12 | `db/query_logger.py` | Backend | Slow query detection + parameter sanitization. |
| M13 | Contexts (Toast, Loading, QuickActions) | Frontend | Provider state management. |
| M14 | `features/interest-rates/hooks/useInterestRates.ts` | Frontend | Rate data aggregation + refresh control. |

### LOW Gaps

| # | Artifact | Layer | Why Low |
|---|----------|-------|---------|
| L1 | All skeleton components (already tested: 5) | Frontend | Remaining skeletons are presentational-only. |
| L2 | Chart components (PortfolioPerformance, PropertyDistribution, etc.) | Frontend | Thin wrappers around Recharts. Test the data, not the chart library. |
| L3 | `LoginPage.tsx` | Frontend | Simple form -- auth logic is in authStore. |
| L4 | Layout components (AppLayout, Sidebar, TopNav) | Frontend | Framework glue. |
| L5 | `cn()` utility | Frontend | Single-line clsx + tailwind-merge. |
| L6 | `core/logging.py` | Backend | Logging setup -- hard to unit test meaningfully. |
| L7 | Map components (PipelineMap, SalesMap, PropertyMap) | Frontend | Leaflet/mapbox wrappers. |
| L8 | Wizard step components (4 steps) | Frontend | Form UI with minimal logic. |
| L9 | `SharePoint URL util` | Frontend | URL string construction. |

---

## 7. Test Strategy and Conventions

### 7.1 Backend Test Architecture

```
backend/tests/
  conftest.py            -- Core fixtures (db, client, auth, sample data)
  factories.py           -- factory_boy factories (User, Deal, Property)
  test_api/              -- API endpoint integration tests (httpx AsyncClient)
  api/v1/                -- Additional API tests (activity endpoints)
  test_crud/             -- CRUD layer unit tests (async session)
  test_core/             -- Security, permissions, config, validation
  test_middleware/        -- HTTP middleware behavior tests
  test_models/           -- SQLAlchemy model tests (constraints, methods)
  test_extraction/       -- Extraction pipeline tests (unit + regression)
  test_services/         -- Service layer tests (mocked dependencies)
    batch/               -- Batch processing subsystem
    ml/                  -- ML model subsystem
    monitoring/          -- Prometheus metrics subsystem
    workflow/            -- Workflow engine subsystem
    test_construction_api/ -- External API integration tests
```

### 7.2 Mock Patterns

**Backend:**
- Database: SQLite in-memory (real async sessions, not mocked)
- Redis: `unittest.mock.AsyncMock` or skip when unavailable
- External APIs (FRED, SharePoint, Census): `unittest.mock.patch` on HTTP clients
- File system: `tmp_path` fixture or `unittest.mock.patch` on `pathlib.Path`

**Frontend:**
- API hooks: `vi.mock()` entire hook module, return controlled data
- Fetch/axios: `vi.mock()` on `lib/api/client.ts`
- React Query: Custom `QueryClient` with `defaultOptions.queries.retry: false`
- Router: `MemoryRouter` with initial entries
- Zustand stores: Direct `getState()`/`setState()` in tests

### 7.3 Test Data Strategy

**Backend factories** (`factories.py`):
- `UserFactory` / `AdminUserFactory` / `AnalystUserFactory` -- user roles
- `DealFactory` -- realistic financial fields (asking_price $5M-$50M, IRR 10-25%)
- `PropertyFactory` -- Phoenix MSA properties with Class B defaults

**Frontend fixtures:**
- Inline mock objects matching Zod schema output shapes
- Type-safe via TypeScript -- test data matches component prop types

### 7.4 Test Execution

| Command | What It Runs | Duration |
|---------|-------------|----------|
| `cd backend && python -m pytest` | All 2,155 backend tests | ~7 seconds |
| `npm run test:run` | All 985 frontend tests | ~22 seconds |
| `npm run test:e2e` | Playwright E2E tests | Variable |
| `cd backend && python -m pytest --cov` | Backend with coverage report | ~7 seconds |
| `cd backend && python -m pytest tests/test_extraction/` | Extraction suite only | ~3 seconds |
| `npm run test:run -- --reporter=verbose` | Verbose frontend output | ~22 seconds |

### 7.5 Coverage Threshold

Backend: 30% minimum (currently 26.20% -- failing). The gap is driven by large, untested service modules with external dependencies (workflow engine, schedulers, construction API integrations). The actual tested code has strong coverage -- the denominator is inflated by production-only integration code.

### 7.6 Recommendations for Next Test Sprint

1. **Highest ROI:** Add tests for `lib/calculations/` (IRR, cash flow, sensitivity) -- ~50 tests, covers CRITICAL C1
2. **Quick wins:** `authStore` tests (~15 tests), Zod `common.ts` tests (~10 tests), `CacheService` tests (~20 tests)
3. **API gaps:** Transaction + Document + Interest Rate endpoints -- ~60 tests total
4. **Coverage threshold fix:** Adding tests for `cache.py`, `interest_rates.py`, and a few CRUD files would push past 30%

---

*End of report. 3,140 total tests (2,155 backend + 985 frontend) as of 2026-03-10.*
