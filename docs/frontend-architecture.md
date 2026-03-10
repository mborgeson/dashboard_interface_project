# Frontend Architecture Inventory

Generated: 2026-03-10

## Table of Contents

1. [Application Bootstrap](#1-application-bootstrap)
2. [Router Configuration](#2-router-configuration)
3. [API Client](#3-api-client)
4. [Stores (Zustand)](#4-stores-zustand)
5. [Zod Schemas](#5-zod-schemas)
6. [Type Definitions](#6-type-definitions)
7. [Shared Hooks](#7-shared-hooks)
8. [API Hooks (React Query)](#8-api-hooks-react-query)
9. [Feature-Level Hooks](#9-feature-level-hooks)
10. [Shared Components](#10-shared-components)
11. [Feature Components](#11-feature-components)
12. [Utilities](#12-utilities)
13. [Services](#13-services)
14. [Contexts](#14-contexts)
15. [Component Hierarchy by Route](#15-component-hierarchy-by-route)

---

## 1. Application Bootstrap

**Entry point:** `src/main.tsx`

```
StrictMode
  ErrorBoundary                  (global crash boundary)
    QueryClientProvider          (TanStack React Query)
      App                        (auth init + prefetch)
        ToastProvider            (notification context)
          AppRouter              (React Router v6 data router)
      ReactQueryDevtools
```

**Key initialization sequence:**
1. `initErrorTracking()` -- sets up global error/rejection listeners before React mounts
2. React renders `<App>` which calls `useAuthStore.getState().initialize()` to validate stored JWT
3. `usePrefetchDashboard()` warms the React Query cache with market overview, interest rates, report templates, and properties

**React Query defaults** (`src/lib/queryClient.ts`):
- `staleTime`: 5 min (default), up to 60 min for reference data, down to 30 sec for report queues
- `gcTime`: 30 min
- `retry`: 2 for queries, 1 for mutations
- `refetchOnWindowFocus`: disabled

---

## 2. Router Configuration

**Files:** `src/app/router.tsx`, `src/app/routes.ts`

All page components are lazy-loaded via `React.lazy()`. Every authenticated route is wrapped in `<PageSuspenseWrapper>` (Suspense + ErrorBoundary). Five routes have an additional `<FeatureErrorBoundary>`.

### Route Table

| Path | Component | Auth | Lazy | Error Boundary |
|------|-----------|------|------|----------------|
| `/login` | `LoginPage` | No | Yes | No (PageSuspense only) |
| `/` (index) | `DashboardMain` | Yes | Yes | FeatureErrorBoundary("Dashboard") |
| `/investments` | `InvestmentsPage` | Yes | Yes | FeatureErrorBoundary("Investments") |
| `/properties/:id` | `PropertyDetailPage` | Yes | Yes | No |
| `/deals` | `DealsPage` | Yes | Yes | FeatureErrorBoundary("Deals") |
| `/deals/compare` | `DealComparisonPage` | Yes | Yes | No |
| `/analytics` | `AnalyticsPage` | Yes | Yes | FeatureErrorBoundary("Analytics") |
| `/mapping` | `MappingPage` | Yes | Yes | No |
| `/market` | `MarketPage` | Yes | Yes | No |
| `/market/usa` | `USAMarketPage` | Yes | Yes | No |
| `/documents` | `DocumentsPage` | Yes | Yes | No |
| `/interest-rates` | `InterestRatesPage` | Yes | Yes | No |
| `/reporting` | `ReportingSuitePage` | Yes | Yes | FeatureErrorBoundary("Reporting") |
| `/extraction` | `ExtractionDashboard` | Yes | Yes | No |
| `/extraction/:propertyName` | `ExtractionDashboard` | Yes | Yes | No |
| `/sales-analysis` | `SalesAnalysisPage` | Yes | Yes | No |
| `/construction-pipeline` | `ConstructionPipelinePage` | Yes | Yes | No |

**Auth gate:** `RequireAuth` component checks `useAuthStore()`. If `isLoading`, shows spinner. If not authenticated, redirects to `/login`.

**Layout:** All authenticated routes render inside `AppLayout` which provides:
- `Sidebar` (collapsible, responsive)
- `TopNav`
- `ComparisonBar` (floating, for deal comparison)
- `QuickActionsProvider` + `KeyboardShortcutsProvider`
- `CommandPalette` + `FloatingActionButton`

**Router future flags:** `v7_relativeSplatPath: true`, `v7_startTransition: true`

**Route path constants:** Exported from `src/app/routes.ts` as `ROUTES` object with type `RoutePath`.

---

## 3. API Client

**File:** `src/lib/api/client.ts` (sole API client -- axios was removed)

### Architecture

- **Base URL:** `VITE_API_BASE_URL` env var or `http://localhost:8000/api/v1`
- **Auth:** Reads `access_token` from `localStorage`, attaches as `Authorization: Bearer` header
- **ETag caching:** GET requests send `If-None-Match` with cached ETags; 304 responses return cached data
- **401 handling:** Clears tokens from localStorage, dispatches `auth:unauthorized` CustomEvent (authStore listens)
- **Content-Type:** JSON by default, auto-detects `URLSearchParams` for form-encoded bodies

### Exports

```typescript
export class ApiError extends Error {
  status: number;
  data?: unknown;
}

export const apiClient = {
  get<T>(endpoint, options?): Promise<T>,
  post<T>(endpoint, data?, options?): Promise<T>,
  put<T>(endpoint, data?, options?): Promise<T>,
  patch<T>(endpoint, data?, options?): Promise<T>,
  delete<T>(endpoint, options?): Promise<T>,
};
```

### Convenience Wrappers (`src/lib/api/index.ts`)

```typescript
get<T>(endpoint, params?)
post<T>(endpoint, data?, options?)
put<T>(endpoint, data?)
patch<T>(endpoint, data?)
del<T>(endpoint)
```

### Domain API Modules

| File | Endpoints | Zod Validation |
|------|-----------|----------------|
| `src/lib/api/properties.ts` | `/properties/dashboard`, `/properties/{id}`, `/properties/summary` | Yes (propertySchema, propertiesResponseSchema, propertySummaryStatsSchema) |
| `src/lib/api/reporting.ts` | `/reporting/settings` GET/PUT | Yes (reportSettingsResponseSchema) |
| `src/lib/api/sales.ts` | `/sales/*` (list, analytics, import, quality) | Yes (salesResponseSchema + analytics schemas) |
| `src/lib/api/construction.ts` | `/construction-pipeline/*` (list, analytics, import) | Yes (projectsResponseSchema + analytics schemas) |

---

## 4. Stores (Zustand)

### authStore (`src/stores/authStore.ts`)

| Field | Type | Description |
|-------|------|-------------|
| `user` | `User \| null` | `{ id, email, full_name, role, is_active }` |
| `accessToken` | `string \| null` | JWT access token |
| `refreshToken` | `string \| null` | JWT refresh token |
| `isAuthenticated` | `boolean` | Derived from token presence |
| `isLoading` | `boolean` | True during initialization |

**Actions:** `login(email, password)`, `logout()`, `initialize()`

**Side effects:** Listens for `auth:unauthorized` window event to auto-clear state on 401.

**Consumers:** `RequireAuth` (router), `AppLayout`, `useWebSocket`, all API hooks indirectly

### notificationStore (`src/stores/notificationStore.ts`)

| Field | Type | Description |
|-------|------|-------------|
| `toasts` | `Toast[]` | Active toast notifications |

**Actions:** `addToast(options) -> id`, `removeToast(id)`, `clearAll()`

Auto-removes toasts after `duration` ms (default 5000).

**Consumers:** `useToast` hook, `useNotify` wrapper, `ToastContainer`

### searchStore (`src/stores/searchStore.ts`)

| Field | Type | Description |
|-------|------|-------------|
| `searchQuery` | `string` | Current search text |
| `recentSearches` | `string[]` | Up to 10, persisted to localStorage |
| `searchResults` | `SearchResult[]` | Current results |
| `isOpen` | `boolean` | Search panel visibility |

**Actions:** `setQuery`, `addRecentSearch`, `clearRecentSearches`, `setResults`, `toggleOpen`, `setOpen`

**Consumers:** `GlobalSearch` component, `CommandPalette`

### useAppStore (`src/store/useAppStore.ts`)

| Field | Type | Description |
|-------|------|-------------|
| `sidebarCollapsed` | `boolean` | Sidebar collapsed state |
| `mobileMenuOpen` | `boolean` | Mobile menu state |

**Actions:** `toggleSidebar`, `setSidebarCollapsed`, `toggleMobileMenu`, `setMobileMenuOpen`

**Consumers:** `AppLayout`, `Sidebar`

---

## 5. Zod Schemas

All schemas live in `src/lib/api/schemas/`. They validate raw backend JSON (snake_case) and transform to camelCase frontend types.

### common.ts

| Schema | Input | Output |
|--------|-------|--------|
| `dateString` | ISO string | `Date` |
| `nullableDateString` | string \| null | `Date \| null` |
| `numericString` | string \| null | `number \| undefined` |
| `nullableNumericString` | string \| null | `number \| null` |

### property.ts

| Schema | Description |
|--------|-------------|
| `propertySchema` | Full property with nested address, details, acquisition, financing, valuation, operations, operationsByYear, performance, images |
| `propertiesResponseSchema` | `{ properties: Property[], total: number }` |
| `propertySummaryStatsSchema` | Portfolio-level aggregates (totalProperties, totalUnits, totalValue, etc.) |

Sub-schemas: `addressSchema`, `propertyDetailsSchema`, `acquisitionSchema`, `financingSchema`, `valuationSchema`, `expensesSchema`, `operationsSchema`, `operatingYearExpensesSchema`, `operatingYearSchema`, `performanceSchema`, `imagesSchema`

### deal.ts

| Schema | Description |
|--------|-------------|
| `backendDealSchema` | Raw deal JSON -> `Deal` type. Parses city/state from name, maps legacy stages, computes `daysInStage`/`daysInPipeline`, converts numeric strings |
| `dealsListResponseSchema` | `{ items: Deal[], total: number }` |

**Helpers:** `mapBackendStage(stage)` -- maps legacy 8-stage names to current 6-stage enum. `parseCityState(name)` -- extracts city/state from `"Name (City, ST)"` format.

### sales.ts

| Schema | Description |
|--------|-------------|
| `saleRecordSchema` | Individual sale record, snake_case -> camelCase |
| `salesResponseSchema` | Paginated: `{ data, total, page, pageSize, totalPages }` |
| `timeSeriesDataPointSchema` | Period aggregates |
| `submarketComparisonRowSchema` | Submarket-level comparison |
| `buyerActivityRowSchema` | Buyer transaction summaries |
| `distributionBucketSchema` | Distribution histogram buckets |
| `dataQualityReportSchema` | Data quality metrics |
| `importStatusSchema` | Import status |
| `reminderStatusSchema` | Monthly import reminder |
| `triggerImportResponseSchema` | Import trigger response |
| `filterOptionsSchema` | Available filter options |

### construction.ts

| Schema | Description |
|--------|-------------|
| `projectRecordSchema` | Individual project, snake_case -> camelCase (23 fields) |
| `projectsResponseSchema` | Paginated response |
| `constructionFilterOptionsSchema` | Filter options (submarkets, cities, statuses, etc.) |
| `pipelineSummaryItemSchema` | Status + counts |
| `pipelineFunnelItemSchema` | Status + cumulative units |
| `permitTrendPointSchema` | Permit time series |
| `employmentPointSchema` | Employment time series |
| `submarketPipelineItemSchema` | Per-submarket breakdown |
| `classificationBreakdownItemSchema` | Classification counts |
| `deliveryTimelineItemSchema` | Quarterly delivery |
| `constructionDataQualitySchema` | Source quality metrics |
| `constructionImportStatusSchema` | Import status |
| `triggerConstructionImportResponseSchema` | Import trigger response |

### reporting.ts

| Schema | Description |
|--------|-------------|
| `reportSettingsResponseSchema` | Report settings, snake_case -> camelCase (13 fields) |

---

## 6. Type Definitions

All type files in `src/types/`. Re-exported via `src/types/index.ts`.

### property.ts
- `OperatingYearExpenses` -- 12 expense line items
- `OperatingYear` -- Revenue breakdown (GPR, loss to lease, vacancy, bad debt, concessions, other loss, NRI, other income subcategories, EGI, NOI, total OpEx) + expenses
- `Property` -- Full property model (address, propertyDetails, acquisition, financing, valuation, operations, operationsByYear, performance, images, lastAnalyzed)
- `PropertySummaryStats` -- Portfolio aggregates (9 fields)

### deal.ts
- `DealStage` -- `'dead' | 'initial_review' | 'active_review' | 'under_contract' | 'closed' | 'realized'`
- `DealTimelineEvent` -- `{ id, date, stage, description, user? }`
- `Deal` -- Full deal model with address, enrichment fields (location, loss factors, NOI, basis, cap rates, capital, exit, returns, map coords), recent activities
- `DEAL_STAGE_LABELS` -- Record mapping stages to display labels
- `DEAL_STAGE_COLORS` -- Record mapping stages to Tailwind color classes

### transaction.ts
- `TransactionType` -- `'acquisition' | 'disposition' | 'capital_improvement' | 'refinance' | 'distribution'`
- `Transaction` -- `{ id, propertyId, propertyName, date, type, amount, description, category?, documents? }`

### document.ts
- `DocumentType` -- `'lease' | 'financial' | 'legal' | 'due_diligence' | 'photo' | 'other'`
- `Document` -- `{ id, name, type, propertyId, propertyName, size, uploadedAt, uploadedBy, description?, tags, url? }`
- `DocumentFilters` -- `{ searchTerm, type, propertyId, dateRange }`
- `DocumentStats` -- `{ totalDocuments, totalSize, byType, recentUploads }`

### notification.ts
- `ToastType` -- `'success' | 'error' | 'warning' | 'info'`
- `Toast` -- `{ id, type, title, description?, duration?, action? }`
- `ToastOptions` -- Toast without required id
- `AlertBannerProps` -- Banner component props

### extraction.ts
- `ExtractionStatus`, `TriggerType`, `DataValueType` -- String unions
- `ExtractionRun` -- Run metadata (id, started_at, status, file counts)
- `ExtractedValue` -- Individual extracted value (property, field, cell, value, error info)
- `ExtractedProperty` -- Property-level summary
- `ExtractionStats` -- Aggregate stats
- `ExtractionFilters` -- Filter state
- API response types: `ExtractionStatusResponse`, `ExtractionHistoryResponse`, `ExtractedPropertiesResponse`, `ExtractedPropertyValuesResponse`
- `GroupedExtractedValues` -- Values grouped by category

### underwriting.ts
- `PropertyClass`, `AssetType`, `LoanType`, `PrepaymentPenaltyType` -- String literal types
- `UnderwritingInputs` -- 39 input fields (property, acquisition, financing, revenue, expenses, exit)
- `UnderwritingResults` -- Computed results (acquisition metrics, year 1, 10-year projections, return metrics, exit analysis)
- `YearlyProjection` -- 13 annual metrics
- `SensitivityVariable` -- Sensitivity analysis output
- `AssumptionPreset` -- Named presets with partial inputs

### grouping.ts
- `PipelineStatus` -- Pipeline state (data_dir, phases, stats)
- `GroupSummary` -- Group list item (name, file_count, overlap, era, sub_variant_count)
- `GroupDetail` -- Full group (files, overlap, era, sub_variants, variances)
- Response types: `DiscoveryResponse`, `FingerprintResponse`, `GroupListResponse`, `ReferenceMappingResponse`, `ConflictCheckResponse`, `GroupExtractionResponse`, `GroupApprovalResponse`, `BatchExtractionResponse`, `ValidationResponse`

### market.ts
- `TimeframeComparison` -- `'mom' | 'qoq' | 'yoy'`
- `SubmarketMetrics` -- 6 metrics per submarket
- `MarketTrend` -- Monthly trend data
- `EconomicIndicator` -- Indicator + YoY change
- `MSAOverview` -- Population, employment, GDP + growth rates
- `MonthlyMarketData` -- Monthly snapshot (6 fields)
- `MarketData` -- Full market data record with metrics

### interest-rates.ts
- `KeyRate` -- Rate with current/previous/change values, category
- `YieldCurvePoint` -- Maturity + yield
- `HistoricalRate` -- Multi-rate time series row
- `RateDataSource` -- Data source metadata

### search.ts
- `SearchResult` -- `{ type, id, title, subtitle, matchedField?, category?, metadata?, item }`

### sales-analysis.ts
- `SaleRecord` -- 18 fields (camelCase)
- `SalesResponse` -- Paginated
- `SalesFilters` -- 12 filter fields
- `FilterOptions` -- Available submarkets
- Analytics: `TimeSeriesDataPoint`, `SubmarketComparisonRow`, `BuyerActivityRow`, `DistributionBucket`, `DistributionGroupBy`, `AllDistributions`
- Data quality: `DataQualityReport`, `ImportStatus`, `ReminderStatus`

### construction-pipeline.ts
- `ProjectRecord` -- 23 fields (camelCase)
- `ProjectsResponse` -- Paginated
- `ConstructionFilters` -- 10 filter fields
- `ConstructionFilterOptions` -- 5 option arrays
- Analytics: `PipelineSummaryItem`, `PipelineFunnelItem`, `PermitTrendPoint`, `EmploymentPoint`, `SubmarketPipelineItem`, `ClassificationBreakdownItem`, `DeliveryTimelineItem`
- Data quality: `ConstructionDataQuality`, `ConstructionImportStatus`

### api.ts
- Generic API types: `PaginatedResponse<T>`, `ApiError`, `SortParams`, `PaginationParams`
- Property API types: `PropertyFilters`, `PropertyApiResponse`, `PropertyListResponse`, `PropertyCreateInput`, `PropertyUpdateInput`
- Deal API types: `DealStageApi`, `DealFilters`, `DealTimelineEventApi`, `DealApiResponse`, `DealListResponse`, `DealCreateInput`, `DealUpdateInput`, `DealStageUpdateInput`
- Extraction API types: `ExtractionStatus`, `ExtractionSource`, `ExtractedValue`, `ExtractionRun`, `ExtractionHistoryFilters`, `StartExtractionInput`, `ExtractionStatusResponse`
- Auth types: `LoginInput`, `LoginResponse`, `User`

---

## 7. Shared Hooks

### General-purpose hooks (`src/hooks/`)

| Hook | File | Params | Returns | Description |
|------|------|--------|---------|-------------|
| `useNotify` | `useNotify.ts` | none | `{ success, error, warning, info, dismiss }` | Thin wrapper over `useToast` for consistent notification API |
| `useToast` | `useToast.ts` | none | `{ toast, success, error, warning, info, dismiss }` | Creates toasts via notificationStore |
| `useGlobalSearch` | `useGlobalSearch.ts` | `query: string` | `{ results, isSearching }` | Fuse.js search across properties and transactions with 300ms debounce |
| `useFilterPersistence` | `useFilterPersistence.ts` | `filters, setFilters, options?` | `{ clearFilters, getShareableUrl, copyShareableUrl }` | Syncs filter state to URL search params |
| `useWebSocket` | `useWebSocket.ts` | `channel, options?` | `{ status, lastMessage, sendMessage, subscribe, unsubscribe }` | WebSocket with auto-reconnect, exponential backoff (1s-30s), auth token, ping/pong |
| `useCursorPagination` | `useCursorPagination.ts` | `{ queryKey, queryFn, limit?, enabled? }` | `{ items, hasMore, total, isLoading, fetchNextPage, fetchPrevPage, resetPagination, ... }` | Cursor-based pagination with React Query, cursor history stack |
| `useIntersectionObserver` | `useIntersectionObserver.ts` | `options?` | `{ ref, isIntersecting, entry, reset }` | IntersectionObserver wrapper for lazy loading, infinite scroll |
| `usePrefetch` | `usePrefetch.ts` | `options?` | `{ prefetch, cancelPrefetch, isPrefetched }` | Route-level data + component chunk prefetching on hover/focus with 150ms debounce |
| `usePrefetchDashboard` | `usePrefetchDashboard.ts` | none | void | Warms React Query cache on app init (market overview, interest rates, templates, properties) |

---

## 8. API Hooks (React Query)

All in `src/hooks/api/`. Each module exports query key factories, query hooks (with mock fallback variants), mutation hooks, and prefetch utilities. Re-exported via `src/hooks/api/index.ts`.

### Properties (`useProperties.ts`)

| Hook | Key Pattern | Description |
|------|-------------|-------------|
| `useProperties` / `usePropertiesApi` | `['properties', 'list', ...]` | List properties with filters |
| `useProperty` / `usePropertyApi` | `['properties', 'detail', id]` | Single property |
| `usePortfolioSummary` | `['properties', 'summary']` | Aggregate stats |
| `usePropertySummary` | `['properties', 'summary-stats']` | Summary stats |
| `useCreateProperty` | mutation | POST /properties |
| `useUpdateProperty` | mutation | PUT /properties/:id |
| `useDeleteProperty` | mutation | DELETE /properties/:id |

### Deals (`useDeals.ts`)

| Hook | Description |
|------|-------------|
| `useDealsWithMockFallback` (aliased as `useDeals`) | List deals |
| `useKanbanBoard` / `useKanbanBoardWithMockFallback` | Kanban board data |
| `useDealActivities` / `useDealActivitiesWithMockFallback` | Activity feed |
| `useDealWithMockFallback` | Single deal |
| `useDealsApi`, `useDeal`, `useDealPipeline`, `useDealsByStage`, `useDealStats` | API-first variants |
| `useCreateDeal`, `useUpdateDeal`, `useUpdateDealStage`, `useDeleteDeal`, `useAddDealActivity` | Mutations |

### Deal Comparison (`useDealComparison.ts`)

| Hook | Description |
|------|-------------|
| `useDealComparisonWithMockFallback` (aliased as `useDealComparison`) | Compare 2+ deals |

Types: `ComparisonMetric`, `DealForComparison`

### Extraction (`useExtraction.ts`)

| Hook | Description |
|------|-------------|
| `useExtractionStatus`, `useExtractionRun`, `useExtractionHistory` | Run status and history |
| `useExtractedValues`, `usePropertyExtractions`, `useDealExtractions` | Extracted data |
| `useStartExtraction`, `useCancelExtraction`, `useRetryExtraction` | Run control mutations |
| `useValidateExtractedValue`, `useDeleteExtraction` | Value management |
| `useIsPropertyExtracting`, `useIsDealExtracting` | Status checks |

### Transactions (`useTransactions.ts`)

| Hook | Description |
|------|-------------|
| `useTransactionsWithMockFallback`, `useTransactionsApi` | List transactions |
| `useTransaction`, `useTransactionsByProperty`, `useTransactionsByType` | Filtered queries |
| `useTransactionSummary` | Aggregate summary |
| `useCreateTransaction`, `useUpdateTransaction`, `usePatchTransaction`, `useDeleteTransaction` | CRUD mutations |

### Interest Rates (`useInterestRates.ts`)

| Hook | Description |
|------|-------------|
| `useInterestRates` / `useKeyRatesWithMockFallback` | Current key rates |
| `useYieldCurve` / `useYieldCurveWithMockFallback` | Treasury yield curve |
| `useHistoricalRates` / `useHistoricalRatesWithMockFallback` | Historical rate data |
| `useDataSources` / `useDataSourcesWithMockFallback` | Rate data sources |
| `useRateSpreads` / `useRateSpreadsWithMockFallback` | Rate spreads |
| `useLendingContext` / `useLendingContextWithMockFallback` | Lending context |

### Documents (`useDocuments.ts`)

| Hook | Description |
|------|-------------|
| `useDocumentsWithMockFallback`, `useDocumentsApi` | List documents |
| `useDocument`, `useDocumentsByProperty` | Filtered queries |
| `useDocumentStats` / `useDocumentStatsWithMockFallback` | Document statistics |
| `useCreateDocument`, `useUpdateDocument`, `useDeleteDocument` | CRUD mutations |

### Market Data (`useMarketData.ts`)

| Hook | Description |
|------|-------------|
| `useMarketOverview` / `useMarketOverviewWithMockFallback` | MSA overview + economic indicators |
| `useSubmarkets` / `useSubmarketsWithMockFallback` | Submarket metrics |
| `useMarketTrends` / `useMarketTrendsWithMockFallback` | Trend time series |
| `useComparables` / `useComparablesWithMockFallback` | Comparable properties |

### Reporting (`useReporting.ts`)

| Hook | Description |
|------|-------------|
| `useReportTemplates` / `useReportTemplatesWithMockFallback` | Template list |
| `useReportTemplate` | Single template |
| `useQueuedReports` / `useQueuedReportsWithMockFallback` | Report queue |
| `useDistributionSchedules` / `useDistributionSchedulesWithMockFallback` | Distribution schedules |
| `useReportWidgets` / `useReportWidgetsWithMockFallback` | Dashboard widgets |
| `useCreateReportTemplate`, `useUpdateReportTemplate`, `useDeleteReportTemplate` | Template CRUD |
| `useGenerateReport` | Report generation |
| `useCreateDistributionSchedule`, `useUpdateDistributionSchedule`, `useDeleteDistributionSchedule` | Schedule CRUD |

### Property Activities (`usePropertyActivities.ts`)

| Hook | Description |
|------|-------------|
| `usePropertyActivities` / `usePropertyActivitiesWithMockFallback` | Activity list |
| `usePropertyActivitiesApi` | API-first variant |
| `useAddPropertyActivity` | Add activity mutation |

---

## 9. Feature-Level Hooks

### Extraction

| Hook | File | Description |
|------|------|-------------|
| `useExtraction` | `src/features/extraction/hooks/useExtraction.ts` | Legacy extraction queries (status, history, properties, values) with query key factory `extractionLegacyKeys` |
| `useGroupPipeline` | `src/features/extraction/hooks/useGroupPipeline.ts` | UW model grouping pipeline (discovery, fingerprinting, groups, reference mapping, conflict check, extraction, approval, validation) with query key factory `groupPipelineKeys` |

### Deals

| Hook | File | Description |
|------|------|-------------|
| `useDeals` | `src/features/deals/hooks/useDeals.ts` | Client-side deal filtering (stages, property types, assignees, value range, search) with drag-and-drop stage overrides |

### Market

| Hook | File | Description |
|------|------|-------------|
| `useMarketData` | `src/features/market/hooks/useMarketData.ts` | Aggregates market overview, submarkets, and trends into single interface. Derives sparkline data from monthly API data |
| `useUSAMarketData` | `src/features/market/hooks/useUSAMarketData.ts` | USA-wide market data |

### Documents

| Hook | File | Description |
|------|------|-------------|
| `useDocuments` | `src/features/documents/hooks/useDocuments.ts` | Client-side document filtering (search, type, property, date range) on top of API data |

### Interest Rates

| Hook | File | Description |
|------|------|-------------|
| `useInterestRates` | `src/features/interest-rates/hooks/useInterestRates.ts` | Combines key rates, yield curve, and historical data with refresh control |

### Underwriting

| Hook | File | Description |
|------|------|-------------|
| `useUnderwriting` | `src/features/underwriting/hooks/useUnderwriting.ts` | Full underwriting calculation engine (IRR, cash flows, sensitivity analysis) with default inputs |

### Transactions

| Hook | File | Description |
|------|------|-------------|
| `useTransactionFilters` | `src/features/transactions/hooks/useTransactionFilters.ts` | Client-side transaction filtering and sorting |

### Mapping

| Hook | File | Description |
|------|------|-------------|
| `useMapFilters` | `src/features/mapping/hooks/useMapFilters.ts` | Map filter state (property classes, submarkets, value/occupancy ranges) with coordinate validation |

### Sales Analysis

| Hook | File | Description |
|------|------|-------------|
| `useSalesData` | `src/features/sales-analysis/hooks/useSalesData.ts` | All sales queries (list, time series, submarket comparison, buyer activity, distributions, data quality, import) via React Query |

### Construction Pipeline

| Hook | File | Description |
|------|------|-------------|
| `useConstructionData` | `src/features/construction-pipeline/hooks/useConstructionData.ts` | All construction queries (projects, filters, pipeline summary, funnel, permits, employment, submarket, classification, delivery, quality, import) via React Query |

---

## 10. Shared Components

### Error Handling

| Component | File | Description |
|-----------|------|-------------|
| `ErrorBoundary` | `src/components/ErrorBoundary.tsx` | Class component. Props: `children`, `fallback?` (ReactNode or render function), `onError?`. Shows error card with "Try Again" and "Reload Page" buttons. Dev mode shows stack trace |
| `FeatureErrorBoundary` | `src/components/FeatureErrorBoundary.tsx` | Wraps ErrorBoundary with feature-specific fallback. Props: `children`, `featureName: string`. Reports errors via `reportComponentError`. Used on 5 routes |

### Suspense Wrappers

| Component | File | Description |
|-----------|------|-------------|
| `SuspenseWrapper` | `src/components/SuspenseWrapper.tsx` | ErrorBoundary + Suspense combo |
| `PageSuspenseWrapper` | same file | Full-page variant with centered spinner |
| `CardSuspenseWrapper` | same file | Card-level variant |
| `TableSuspenseWrapper` | same file | Table-level variant |
| `withSuspense` | same file | HOC pattern |

### Shared Components (`src/components/shared/`)

| Component | File | Props | Description |
|-----------|------|-------|-------------|
| `StatCard` | `StatCard.tsx` | `label, value, subtitle?, icon?, iconColor?, iconBgColor?, trend?, trendValue?, variant?, className?` | Stat display card with trend indicator. Variants: default, compact, hero |
| `PageLoadingState` | `PageLoadingState.tsx` | `title, subtitle?, statCards?, statCardColumns?, chartHeights?, chartLayout?, headerExtra?, className?` | Full-page loading skeleton with configurable stat cards and charts |
| `InlineEmptyState` | `InlineEmptyState.tsx` | `message?, className?` | Lightweight "No data available" text for widgets |
| `VirtualizedTable` | `VirtualizedTable.tsx` | `rows, renderHeader, renderRow, estimateRowHeight?, overscan?, getRowKey, height?, virtualizeThreshold?, className?` | Virtual scrolling table built on @tanstack/react-virtual. Falls back to plain table below threshold (default 50 rows) |

### Skeletons (`src/components/skeletons/`)

| Component | File |
|-----------|------|
| `StatCardSkeleton` | `StatCardSkeleton.tsx` |
| `ChartSkeleton` | `ChartSkeleton.tsx` |
| `TableSkeleton` | `TableSkeleton.tsx` |
| `PropertyCardSkeleton` | `PropertyCardSkeleton.tsx` |
| `DealCardSkeleton` | `DealCardSkeleton.tsx` |

### UI Primitives (`src/components/ui/`)

shadcn/ui components:
- `button`, `badge`, `card`, `input`, `textarea`, `label`, `select`, `checkbox`
- `dialog`, `dropdown-menu`, `accordion`, `tabs`, `table`, `tooltip`, `separator`
- `alert-dialog`, `alert-banner`, `skeleton`
- `toast`, `toast-container`
- `error-state`, `empty-state`
- `ToggleButton`, `LazyImage`

### Quick Actions (`src/components/quick-actions/`)

| Component | File | Description |
|-----------|------|-------------|
| `CommandPalette` | `CommandPalette.tsx` | Cmd+K command palette |
| `FloatingActionButton` | `FloatingActionButton.tsx` | Floating action button |
| `KeyboardShortcuts` | `KeyboardShortcuts.tsx` | KeyboardShortcutsProvider for global shortcuts |
| `QuickActionButton` | `QuickActionButton.tsx` | Individual quick action button |

### Other Shared Components

| Component | File | Description |
|-----------|------|-------------|
| `GlobalSearch` | `src/components/GlobalSearch.tsx` | Global search bar |
| `ComparisonBar` | `src/components/comparison/ComparisonBar.tsx` | Floating deal comparison bar |
| `PrefetchLink` | `src/components/PrefetchLink.tsx` | Link with prefetch on hover/focus |
| `VirtualList` | `src/components/VirtualList.tsx` | Generic virtual list |
| `SavedFilters` | `src/components/filters/SavedFilters.tsx` | Saved filter presets |

---

## 11. Feature Components

### Dashboard Main (`src/features/dashboard-main/`)

| Component | File |
|-----------|------|
| `DashboardMain` | `DashboardMain.tsx` |
| `PropertyMap` | `components/PropertyMap.tsx` |
| `PortfolioPerformanceChart` | `components/PortfolioPerformanceChart.tsx` |
| `PropertyDistributionChart` | `components/PropertyDistributionChart.tsx` |

### Investments (`src/features/investments/`)

| Component | File |
|-----------|------|
| `InvestmentsPage` | `InvestmentsPage.tsx` |
| `PropertyCard` | `components/PropertyCard.tsx` |
| `PropertyTable` | `components/PropertyTable.tsx` |
| `PropertyFilters` | `components/PropertyFilters.tsx` |

### Property Detail (`src/features/property-detail/`)

| Component | File |
|-----------|------|
| `PropertyDetailPage` | `PropertyDetailPage.tsx` |
| `PropertyHero` | `components/PropertyHero.tsx` |
| `OverviewTab` | `components/OverviewTab.tsx` |
| `PerformanceTab` | `components/PerformanceTab.tsx` |
| `OperationsTab` | `components/OperationsTab.tsx` |
| `FinancialsTab` | `components/FinancialsTab.tsx` |
| `TransactionsTab` | `components/TransactionsTab.tsx` |
| `PropertyDetailSkeleton` | `components/PropertyDetailSkeleton.tsx` |
| `PropertyActivityFeed` | `components/PropertyActivityFeed/PropertyActivityFeed.tsx` |
| `PropertyActivityTimeline` | `components/PropertyActivityFeed/PropertyActivityTimeline.tsx` |
| `PropertyActivityItem` | `components/PropertyActivityFeed/PropertyActivityItem.tsx` |

### Deals (`src/features/deals/`)

| Component | File |
|-----------|------|
| `DealsPage` | `DealsPage.tsx` |
| `DealComparisonPage` | `DealComparisonPage.tsx` |
| `KanbanBoard` | `components/KanbanBoard.tsx` |
| `KanbanColumn` | `components/KanbanColumn.tsx` |
| `KanbanHeader` | `components/KanbanHeader.tsx` |
| `KanbanFiltersBar` | `components/KanbanFiltersBar.tsx` |
| `KanbanSkeleton` | `components/KanbanSkeleton.tsx` |
| `KanbanBoardWidget` | `components/KanbanBoardWidget.tsx` |
| `DealCard` | `components/DealCard.tsx` |
| `DraggableDealCard` | `components/DraggableDealCard.tsx` |
| `DealDetailModal` | `components/DealDetailModal.tsx` |
| `DealTimeline` | `components/DealTimeline.tsx` |
| `DealFilters` | `components/DealFilters.tsx` |
| `DealPipeline` | `components/DealPipeline.tsx` |
| `DealAerialMap` | `components/DealAerialMap.tsx` |
| `ActivityFeed` | `components/ActivityFeed/ActivityFeed.tsx` |
| `ActivityTimeline` | `components/ActivityFeed/ActivityTimeline.tsx` |
| `ActivityItem` | `components/ActivityFeed/ActivityItem.tsx` |
| `ActivityForm` | `components/ActivityFeed/ActivityForm.tsx` |
| `ComparisonSelector` | `components/comparison/ComparisonSelector.tsx` |
| `ComparisonTable` | `components/comparison/ComparisonTable.tsx` |
| `ComparisonCharts` | `components/comparison/ComparisonCharts.tsx` |
| `ComparisonSkeleton` | `components/comparison/ComparisonSkeleton.tsx` |

### Analytics (`src/features/analytics/`)

| Component | File |
|-----------|------|
| `AnalyticsPage` | `AnalyticsPage.tsx` |
| `KPICard` | `components/KPICard.tsx` |
| `PerformanceCharts` | `components/PerformanceCharts.tsx` |
| `ComparisonCharts` | `components/ComparisonCharts.tsx` |
| `DistributionCharts` | `components/DistributionCharts.tsx` |

### Market (`src/features/market/`)

| Component | File |
|-----------|------|
| `MarketPage` | `MarketPage.tsx` |
| `USAMarketPage` | `USAMarketPage.tsx` |
| `MarketOverview` | `components/MarketOverview.tsx` |
| `MarketTrendsChart` | `components/MarketTrendsChart.tsx` |
| `MarketHeatmap` | `components/MarketHeatmap.tsx` |
| `SubmarketComparison` | `components/SubmarketComparison.tsx` |
| `EconomicIndicators` | `components/EconomicIndicators.tsx` |
| `MarketOverviewWidget` | `components/widgets/MarketOverviewWidget.tsx` |
| `MarketTrendsWidget` | `components/widgets/MarketTrendsWidget.tsx` |
| `EconomicIndicatorsWidget` | `components/widgets/EconomicIndicatorsWidget.tsx` |
| `SubmarketComparisonWidget` | `components/widgets/SubmarketComparisonWidget.tsx` |

### Documents (`src/features/documents/`)

| Component | File |
|-----------|------|
| `DocumentsPage` | `DocumentsPage.tsx` |
| `DocumentList` | `components/DocumentList.tsx` |
| `DocumentGrid` | `components/DocumentGrid.tsx` |
| `DocumentCard` | `components/DocumentCard.tsx` |
| `DocumentFilters` | `components/DocumentFilters.tsx` |
| `DocumentUploadModal` | `components/DocumentUploadModal.tsx` |

### Interest Rates (`src/features/interest-rates/`)

| Component | File |
|-----------|------|
| `InterestRatesPage` | `InterestRatesPage.tsx` |
| `KeyRatesSnapshot` | `components/KeyRatesSnapshot.tsx` |
| `TreasuryYieldCurve` | `components/TreasuryYieldCurve.tsx` |
| `RateComparisons` | `components/RateComparisons.tsx` |
| `DataSources` | `components/DataSources.tsx` |
| `InterestRatesSkeleton` | `components/InterestRatesSkeleton.tsx` |

### Reporting Suite (`src/features/reporting-suite/`)

| Component | File |
|-----------|------|
| `ReportingSuitePage` | `ReportingSuitePage.tsx` |
| `ReportTemplates` | `components/ReportTemplates.tsx` |
| `ReportQueue` | `components/ReportQueue.tsx` |
| `ReportSettings` | `components/ReportSettings.tsx` |
| `Distribution` | `components/Distribution.tsx` |
| `CustomReportBuilder` | `components/CustomReportBuilder.tsx` |
| `ReportWizard` | `components/ReportWizard/ReportWizard.tsx` |
| `WizardStepIndicator` | `components/ReportWizard/WizardStepIndicator.tsx` |
| `TemplateSelectionStep` | `components/ReportWizard/TemplateSelectionStep.tsx` |
| `ParameterConfigStep` | `components/ReportWizard/ParameterConfigStep.tsx` |
| `FormatSelectionStep` | `components/ReportWizard/FormatSelectionStep.tsx` |
| `GenerationProgressStep` | `components/ReportWizard/GenerationProgressStep.tsx` |

### Extraction (`src/features/extraction/`)

| Component | File |
|-----------|------|
| `ExtractionDashboard` | `ExtractionDashboard.tsx` |
| `ExtractionStatus` | `components/ExtractionStatus.tsx` |
| `ExtractionHistory` | `components/ExtractionHistory.tsx` |
| `ExtractedPropertyList` | `components/ExtractedPropertyList.tsx` |
| `ExtractedPropertyDetail` | `components/ExtractedPropertyDetail.tsx` |
| `ExtractedValueCard` | `components/ExtractedValueCard.tsx` |
| `BatchExtractionPanel` | `components/BatchExtractionPanel.tsx` |
| `GroupPipelineTab` | `components/GroupPipelineTab.tsx` |
| `GroupPipelineStepper` | `components/GroupPipelineStepper.tsx` |
| `GroupList` | `components/GroupList.tsx` |
| `GroupDetail` | `components/GroupDetail.tsx` |
| `DryRunPreview` | `components/DryRunPreview.tsx` |
| `ConflictReport` | `components/ConflictReport.tsx` |

### Sales Analysis (`src/features/sales-analysis/`)

| Component | File |
|-----------|------|
| `SalesAnalysisPage` | `SalesAnalysisPage.tsx` |
| `SalesTable` | `components/SalesTable.tsx` |
| `SalesFilterPanel` | `components/SalesFilterPanel.tsx` |
| `SalesMap` | `components/SalesMap.tsx` |
| `TimeSeriesTrends` | `components/TimeSeriesTrends.tsx` |
| `SubmarketComparison` | `components/SubmarketComparison.tsx` |
| `BuyerActivityAnalysis` | `components/BuyerActivityAnalysis.tsx` |
| `DistributionAnalysis` | `components/DistributionAnalysis.tsx` |
| `DataQualitySummary` | `components/DataQualitySummary.tsx` |
| `ImportNotificationBanner` | `components/ImportNotificationBanner.tsx` |
| `MonthlyReminderBanner` | `components/MonthlyReminderBanner.tsx` |

### Construction Pipeline (`src/features/construction-pipeline/`)

| Component | File |
|-----------|------|
| `ConstructionPipelinePage` | `ConstructionPipelinePage.tsx` |
| `PipelineTable` | `components/PipelineTable.tsx` |
| `PipelineMap` | `components/PipelineMap.tsx` |
| `PipelineFilterPanel` | `components/PipelineFilterPanel.tsx` |
| `PipelineFunnel` | `components/PipelineFunnel.tsx` |
| `SubmarketPipeline` | `components/SubmarketPipeline.tsx` |
| `ClassificationBreakdown` | `components/ClassificationBreakdown.tsx` |
| `DeliveryTimeline` | `components/DeliveryTimeline.tsx` |
| `PermitTrends` | `components/PermitTrends.tsx` |
| `EmploymentOverlay` | `components/EmploymentOverlay.tsx` |
| `SourceFreshness` | `components/SourceFreshness.tsx` |

### Mapping (`src/features/mapping/`)

| Component | File |
|-----------|------|
| `MappingPage` | `MappingPage.tsx` |
| `MapFilterPanel` | `components/MapFilterPanel.tsx` |
| `MapLegend` | `components/MapLegend.tsx` |
| `PropertyDetailPanel` | `components/PropertyDetailPanel.tsx` |

### Underwriting (`src/features/underwriting/`)

| Component | File |
|-----------|------|
| `UnderwritingModal` | `components/UnderwritingModal.tsx` |
| `InputsTab` | `components/InputsTab.tsx` |
| `ResultsTab` | `components/ResultsTab.tsx` |
| `ProjectionsTab` | `components/ProjectionsTab.tsx` |
| `SensitivityTab` | `components/SensitivityTab.tsx` |
| `AssumptionsPresets` | `components/AssumptionsPresets.tsx` |

### Transactions (`src/features/transactions/`)

| Component | File |
|-----------|------|
| `TransactionsPage` | `TransactionsPage.tsx` |
| `TransactionTable` | `components/TransactionTable.tsx` |
| `TransactionFilters` | `components/TransactionFilters.tsx` |
| `TransactionCharts` | `components/TransactionCharts.tsx` |
| `TransactionTimeline` | `components/TransactionTimeline.tsx` |
| `TransactionSummary` | `components/TransactionSummary.tsx` |

### Auth (`src/features/auth/`)

| Component | File |
|-----------|------|
| `LoginPage` | `LoginPage.tsx` |

### Search (`src/features/search/`)

| Component | File |
|-----------|------|
| `GlobalSearch` | `GlobalSearch.tsx` |

---

## 12. Utilities

### dateUtils.ts (`src/lib/dateUtils.ts`)

7 functions for null-safe date handling:

| Function | Signature | Description |
|----------|-----------|-------------|
| `parseDate` | `(string \| Date \| null \| undefined) -> Date \| null` | Safe parse, never throws |
| `isValidDate` | `(unknown) -> boolean` | Type guard for valid dates |
| `formatDate` | `(date, style?) -> string` | Short/medium/long format. Default: "Mar 10, 2026" |
| `formatDateTime` | `(date) -> string` | "Mar 10, 2026 2:30 PM" |
| `formatTime` | `(date) -> string` | "2:30 PM" |
| `formatRelativeTime` | `(date) -> string` | "just now", "5m ago", "3h ago", "2d ago", then short date |
| `getDateGroupLabel` | `(date) -> string` | "Today", "Yesterday", weekday name, or long date |

### formatters.ts (`src/lib/utils/formatters.ts`)

| Function | Signature | Description |
|----------|-----------|-------------|
| `formatCurrency` | `(number, compact?) -> string` | `$1.5M`, `$150K`, or `$1,500,000` |
| `formatPercent` | `(number, decimals?) -> string` | `15.0%` (input: 0.15) |
| `formatNumber` | `(number) -> string` | Thousand separators |
| `formatDate` | `(Date, format?) -> string` | Date formatting (legacy, prefer dateUtils) |
| `formatCurrencyOrNA` | `(number \| null \| undefined, compact?) -> string` | Returns "N/A" for null/0 |
| `formatPercentOrNA` | `(number \| null \| undefined, decimals?) -> string` | Returns "N/A" for null/0 |
| `formatNumberOrNA` | `(number \| null \| undefined) -> string` | Returns "N/A" for null/0 |
| `shortPropertyName` | `(string) -> string` | Strips `(City, ST)` suffix |
| `formatChange` | `(number, isPercent?) -> { text, colorClass }` | Signed change with color |

### config.ts (`src/lib/config.ts`)

| Export | Description |
|--------|-------------|
| `USE_MOCK_DATA` | `VITE_USE_MOCK_DATA === 'true'` |
| `IS_DEV` / `IS_PROD` | Environment checks |
| `API_URL` | Backend API base URL |
| `WS_URL` | WebSocket URL |
| `FEATURES` | Feature flags (analytics, debug, experimental) |
| `shouldUseMockData()` | Mock data check |
| `withMockFallback(apiCall, mockData)` | Auto-fallback in dev |

### utils.ts (`src/lib/utils.ts`)

`cn()` -- Tailwind class name merger (clsx + tailwind-merge)

### Calculation Libraries (`src/lib/calculations/`)

| File | Functions |
|------|-----------|
| `irr.ts` | `calculateIRR`, `calculateEquityMultiple` |
| `cashflow.ts` | `generateCashFlowProjections` |
| `sensitivity.ts` | `calculateSensitivity` |

### Underwriting Utils (`src/features/underwriting/utils/`)

| File | Functions |
|------|-----------|
| `calculations.ts` | `calculateDebtService`, `calculateDSCR`, `calculateLTV`, `calculateYieldOnCost`, `calculateBreakEvenOccupancy`, `calculatePricePerUnit`, `calculatePricePerSF` |
| `exporters.ts` | UW model export utilities |

### Deal Utils

| File | Functions |
|------|-----------|
| `src/features/deals/utils/sharepoint.ts` | SharePoint URL generation |

---

## 13. Services

### errorTracking.ts (`src/services/errorTracking.ts`)

Lightweight frontend error tracking:

| Export | Description |
|--------|-------------|
| `initErrorTracking()` | Sets up `window.onerror` + `unhandledrejection` listeners. Starts 5-second flush interval. Flushes on `visibilitychange` (hidden). Safe to call multiple times |
| `reportError(error, context?)` | Enqueues error report. Rate-limited: 10/minute max, 50-item buffer |
| `reportComponentError(error, componentStack)` | Same as reportError but includes React component stack |

- In dev mode: logs to console instead of sending to backend
- In production: POSTs batch to `POST /api/v1/errors/report` with `keepalive: true`

---

## 14. Contexts

### ToastContext (`src/contexts/ToastContext.tsx`)

Toast notification provider. Wraps `AppRouter`.

### LoadingContext (`src/contexts/LoadingContext.tsx`)

Exports `LoadingSpinner` component used by SuspenseWrapper fallbacks.

### QuickActionsContext (`src/contexts/QuickActionsContext.tsx`)

Manages:
- Command palette open/close state
- Deal comparison selection (add/remove/clear deal IDs)
- Watchlist management
- Recent action tracking
- Quick action dispatch

Used by: `AppLayout`, `ComparisonBar`, `DealCard`, `CommandPalette`, `FloatingActionButton`

---

## 15. Component Hierarchy by Route

### `/` (Dashboard)

```
AppLayout
  DashboardMain
    StatCard (x4-6)
    PortfolioPerformanceChart
    PropertyDistributionChart
    PropertyMap
    KanbanBoardWidget
```

### `/investments`

```
AppLayout
  InvestmentsPage
    PropertyFilters
    PropertyCard (grid view) | PropertyTable (table view)
```

### `/properties/:id`

```
AppLayout
  PropertyDetailPage
    PropertyDetailSkeleton (loading)
    PropertyHero
    Tabs:
      OverviewTab -> StatCard, charts
      PerformanceTab -> charts
      OperationsTab -> expense breakdowns
      FinancialsTab -> financial tables
      TransactionsTab -> TransactionTable
    PropertyActivityFeed
      PropertyActivityTimeline
        PropertyActivityItem (xN)
```

### `/deals`

```
AppLayout
  DealsPage
    KanbanFiltersBar / DealFilters
    KanbanBoard
      KanbanColumn (x6 stages)
        KanbanHeader
        DraggableDealCard (xN)
          DealCard
    DealDetailModal (on card click)
      DealTimeline
      DealAerialMap
      ActivityFeed
        ActivityTimeline
          ActivityItem (xN)
        ActivityForm
```

### `/deals/compare`

```
AppLayout
  DealComparisonPage
    ComparisonSelector
    ComparisonTable
    ComparisonCharts
    ComparisonSkeleton (loading)
```

### `/analytics`

```
AppLayout
  AnalyticsPage
    KPICard (x4+)
    PerformanceCharts
    ComparisonCharts
    DistributionCharts
```

### `/market`

```
AppLayout
  MarketPage
    MarketOverview / MarketOverviewWidget
    MarketTrendsChart / MarketTrendsWidget
    SubmarketComparison / SubmarketComparisonWidget
    EconomicIndicators / EconomicIndicatorsWidget
    MarketHeatmap
```

### `/documents`

```
AppLayout
  DocumentsPage
    DocumentFilters
    DocumentList | DocumentGrid
      DocumentCard (xN)
    DocumentUploadModal
```

### `/interest-rates`

```
AppLayout
  InterestRatesPage
    InterestRatesSkeleton (loading)
    KeyRatesSnapshot
    TreasuryYieldCurve
    RateComparisons
    DataSources
```

### `/reporting`

```
AppLayout
  ReportingSuitePage
    Tabs:
      ReportTemplates
      ReportQueue
      Distribution
      ReportSettings
      CustomReportBuilder
    ReportWizard (modal)
      WizardStepIndicator
      TemplateSelectionStep
      ParameterConfigStep
      FormatSelectionStep
      GenerationProgressStep
```

### `/extraction`

```
AppLayout
  ExtractionDashboard
    ExtractionStatus
    Tabs:
      ExtractionHistory
      ExtractedPropertyList
        ExtractedPropertyDetail
          ExtractedValueCard (xN)
      BatchExtractionPanel
      GroupPipelineTab
        GroupPipelineStepper
        GroupList
          GroupDetail
        DryRunPreview
        ConflictReport
```

### `/sales-analysis`

```
AppLayout
  SalesAnalysisPage
    ImportNotificationBanner
    MonthlyReminderBanner
    SalesFilterPanel
    Tabs/sections:
      SalesTable (VirtualizedTable)
      SalesMap
      TimeSeriesTrends
      SubmarketComparison
      BuyerActivityAnalysis
      DistributionAnalysis
      DataQualitySummary
```

### `/construction-pipeline`

```
AppLayout
  ConstructionPipelinePage
    PipelineFilterPanel
    ConstructionSummaryCards (StatCard xN)
    Tabs/sections:
      PipelineTable (VirtualizedTable)
      PipelineMap
      PipelineFunnel
      SubmarketPipeline
      ClassificationBreakdown
      DeliveryTimeline
      PermitTrends
      EmploymentOverlay
      SourceFreshness
```

### `/mapping`

```
AppLayout
  MappingPage
    MapFilterPanel
    Map (Leaflet/Mapbox)
    MapLegend
    PropertyDetailPanel (on marker click)
```
