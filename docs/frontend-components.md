# Frontend Component Deep Documentation

> **Generated:** 2026-03-10 | **Team 61 (Regeneration) -- Frontend Component Deep Documentation**
> **Source:** Complete read-through of every component and hook in the codebase
> **Reference Inventory:** `docs/frontend-architecture.md` (Team 57)

---

## Table of Contents

1. [Application Bootstrap & Entry Points](#1-application-bootstrap--entry-points)
2. [API Client (`src/lib/api/client.ts`)](#2-api-client)
3. [API Convenience Layer (`src/lib/api/index.ts`)](#3-api-convenience-layer)
4. [Stores](#4-stores)
5. [Error Tracking Service (`src/services/errorTracking.ts`)](#5-error-tracking-service)
6. [Contexts](#6-contexts)
7. [Shared Hooks](#7-shared-hooks)
8. [API Hooks (React Query)](#8-api-hooks-react-query)
9. [Feature-Level Hooks](#9-feature-level-hooks)
10. [Error Boundaries](#10-error-boundaries)
11. [Shared Components](#11-shared-components)
12. [Skeleton Components](#12-skeleton-components)
13. [Feature Components: Dashboard](#13-feature-components-dashboard)
14. [Feature Components: Deals](#14-feature-components-deals)
15. [Feature Components: Properties](#15-feature-components-properties)
16. [Feature Components: Property Detail](#16-feature-components-property-detail)
17. [Feature Components: Transactions](#17-feature-components-transactions)
18. [Feature Components: Market Data / Sales Analysis](#18-feature-components-market-data--sales-analysis)
19. [Feature Components: Interest Rates](#19-feature-components-interest-rates)
20. [Feature Components: Reporting Suite](#20-feature-components-reporting-suite)
21. [Feature Components: Extraction](#21-feature-components-extraction)
22. [Feature Components: Documents](#22-feature-components-documents)
23. [Feature Components: Construction Pipeline](#23-feature-components-construction-pipeline)
24. [Feature Components: Settings](#24-feature-components-settings)
25. [Feature Components: Login](#25-feature-components-login)
26. [Utility Libraries](#26-utility-libraries)
27. [Zod Schemas](#27-zod-schemas)
28. [Type Definitions](#28-type-definitions)
29. [Issues Found](#29-issues-found)

---

## 1. Application Bootstrap & Entry Points

### `src/main.tsx`
**Purpose:** Application entry point. Initializes error tracking, then renders the React tree.

**Boot sequence (order matters):**
1. `initErrorTracking()` -- installs global `window.onerror` and `unhandledrejection` listeners
2. `ReactDOM.createRoot` renders: `StrictMode > ErrorBoundary > QueryClientProvider > App`

**Side effects:** `initErrorTracking()` called at module level (before React mount).

**Children:** `<App />`

---

### `src/app/App.tsx`
**Purpose:** Root application component. Initializes auth and warms cache.

**Internal state:** None (delegates to stores/hooks).

**Side effects:**
- `useEffect` calls `useAuthStore.getState().initialize()` on mount -- checks localStorage for existing JWT, fetches `/auth/me` if token found.
- `usePrefetchDashboard()` fires on mount to warm React Query cache with dashboard data.

**Children:** `<RouterProvider>` with the data router from `router.tsx`.

**Stores accessed:** `authStore` (indirectly via `initialize()`).

---

### `src/app/router.tsx`
**Purpose:** React Router v6 data router configuration. Defines all routes, auth gating, and lazy loading.

**Key internal components:**

#### `RequireAuth`
- Reads `useAuthStore()` for `isAuthenticated` and `isLoading`
- Shows full-page spinner while `isLoading` is true
- Redirects to `/login` if not authenticated (preserving `location` in state)
- Renders `<Outlet />` when authenticated

#### `LazyRoute`
- Generic wrapper that takes a `React.lazy()` component
- Wraps it in `<Suspense fallback={<PageLoadingState ...>}>`

**Route structure:**
- `/login` -- public, no auth guard
- `/` -- `RequireAuth` layout wrapping all protected routes
  - `""` (index) -- Dashboard
  - `deals` -- Deals page (with `FeatureErrorBoundary`)
  - `properties` -- Properties page (with `FeatureErrorBoundary`)
  - `properties/:id` -- Property detail
  - `transactions` -- Transactions page (with `FeatureErrorBoundary`)
  - `market-data` -- Market data
  - `sales-analysis` -- Sales analysis (with `FeatureErrorBoundary`)
  - `interest-rates` -- Interest rates (with `FeatureErrorBoundary`)
  - `reports` -- Reporting suite
  - `extraction` -- Extraction management
  - `documents` -- Documents
  - `construction` -- Construction pipeline
  - `settings` -- Settings
  - `*` -- 404 fallback

**Edge cases:**
- All feature routes use `React.lazy()` for code splitting
- 5 routes have `FeatureErrorBoundary` wrappers; others rely on the root `ErrorBoundary`

---

## 2. API Client

**File:** `src/lib/api/client.ts` (151 lines)

**Purpose:** Sole fetch-based HTTP client for all backend communication. Replaces the legacy axios client (`src/lib/api.ts`).

**Exported:** `apiClient` object with methods: `get<T>`, `post<T>`, `put<T>`, `patch<T>`, `delete<T>`; `ApiError` class.

### Features

#### ETag Caching
- Module-scoped `etagCache = new Map<string, { etag: string; data: unknown }>()`
- On GET: sends `If-None-Match` header if cached ETag exists for the URL
- On 304 response: returns cached `data` without re-parsing
- On successful GET with `etag` response header: stores `{ etag, data }` in map

#### Auth Token
- Reads `localStorage.getItem('access_token')` on every request
- Attaches as `Authorization: Bearer <token>`

#### 401 Handling
- On 401: removes `access_token` and `refresh_token` from localStorage
- Dispatches `window.dispatchEvent(new CustomEvent('auth:unauthorized'))`
- `authStore` listens for this event and clears auth state

#### URLSearchParams Detection
- When `body instanceof URLSearchParams`, skips `Content-Type: application/json` header
- Lets fetch auto-set `application/x-www-form-urlencoded`
- Used by `authStore.login()` for OAuth2 form login

#### Query Parameters
- `params?: Record<string, string | number | boolean | undefined>`
- Filters out `undefined` values
- Builds URL with `URLSearchParams`

**Edge cases:**
- 304 without cached data: falls through to empty-response handling, returns `{} as T`
- Non-JSON responses: returns `{} as T`
- Network errors: thrown as native `TypeError` (not wrapped in `ApiError`)

---

## 3. API Convenience Layer

**File:** `src/lib/api/index.ts` (44 lines)

**Purpose:** Re-exports convenience functions that wrap `apiClient` methods.

**Exports:**
- `get<T>(endpoint, params?)` -- calls `apiClient.get` with `{ params }`
- `post<T>(endpoint, data?, options?)` -- calls `apiClient.post`
- `put<T>(endpoint, data?, options?)` -- calls `apiClient.put`
- `patch<T>(endpoint, data?, options?)` -- calls `apiClient.patch`
- `del<T>(endpoint, options?)` -- calls `apiClient.delete`

All React Query hooks import from this layer, not directly from `client.ts`.

---

## 4. Stores

### `authStore` -- `src/stores/authStore.ts` (111 lines)
**Purpose:** JWT authentication state management via Zustand.

**State:**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `user` | `User \| null` | `null` | Current user profile |
| `accessToken` | `string \| null` | `null` | JWT access token |
| `refreshToken` | `string \| null` | `null` | JWT refresh token |
| `isAuthenticated` | `boolean` | `false` | Auth status |
| `isLoading` | `boolean` | `true` | Initial load state |

**Actions:**
- `login(email, password)` -- POST `/auth/login` with `URLSearchParams` (OAuth2 form), stores tokens in localStorage, fetches `/auth/me`, sets user state
- `logout()` -- POST `/auth/logout` (fire-and-forget), clears localStorage tokens, resets state
- `initialize()` -- reads `access_token` from localStorage, if present calls GET `/auth/me`, on failure clears tokens

**Side effects (module-level):**
- `window.addEventListener('auth:unauthorized', ...)` -- when API client gets 401, auto-clears auth state if currently authenticated

**Edge cases:**
- `login` does not catch errors -- callers (LoginPage) must handle `ApiError`
- `logout` swallows errors from the POST call
- `initialize` silently clears tokens on any fetch failure (network error or expired token)

---

### `notificationStore` -- `src/stores/notificationStore.ts` (51 lines)
**Purpose:** Toast notification queue with auto-removal.

**State:**
| Field | Type | Description |
|-------|------|-------------|
| `toasts` | `Toast[]` | Current toast queue |

**Actions:**
- `addToast(options: ToastOptions)` -- generates ID (`toast-{timestamp}-{random}`), appends to array, schedules `setTimeout` for auto-removal after `duration` (default 5000ms). Returns the toast ID.
- `removeToast(id)` -- filters toast from array
- `clearAll()` -- empties array

**Edge cases:**
- `duration: 0` skips auto-removal (persistent toast)
- No upper bound on toast queue size -- rapid-fire calls could accumulate many toasts
- `setTimeout` timer is not cleaned up if toast is manually removed early (harmless -- `removeToast` is idempotent via filter)

---

### `searchStore` -- `src/stores/searchStore.ts` (78 lines)
**Purpose:** Global search state with localStorage persistence for recent searches.

**State:**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `searchQuery` | `string` | `''` | Current search input |
| `recentSearches` | `string[]` | from localStorage | Last 10 searches |
| `searchResults` | `SearchResult[]` | `[]` | Current results |
| `isOpen` | `boolean` | `false` | Search panel visibility |

**Actions:**
- `setQuery(query)` -- updates `searchQuery`
- `addRecentSearch(query)` -- deduplicates, prepends, caps at 10, persists to localStorage key `br-capital-recent-searches`
- `clearRecentSearches()` -- empties array and localStorage
- `setResults(results)` -- updates results
- `toggleOpen()` / `setOpen(open)` -- controls panel visibility

**localStorage key:** `br-capital-recent-searches`

---

### `useAppStore` -- `src/store/useAppStore.ts` (19 lines)
**Purpose:** UI layout state (sidebar collapse, theme).

**State:**
| Field | Type | Default |
|-------|------|---------|
| `sidebarCollapsed` | `boolean` | `false` |
| `theme` | `'light' \| 'dark'` | `'light'` |

**Actions:** `toggleSidebar()`, `setTheme(theme)`

---

## 5. Error Tracking Service

**File:** `src/services/errorTracking.ts` (214 lines)

**Purpose:** Lightweight error capture and batch reporting service.

**Architecture:**
- Module-scoped buffer (`ErrorReport[]`), rate limiter, flush timer
- In development: logs to console. In production: POST to `/errors/report`

**Constants:**
| Name | Value | Purpose |
|------|-------|---------|
| `MAX_ERRORS_PER_MINUTE` | 10 | Rate limit per 60s window |
| `FLUSH_INTERVAL_MS` | 5000 | Buffer flush interval |
| `MAX_BUFFER_SIZE` | 50 | Max buffered errors (FIFO drop) |

**Public API:**

#### `initErrorTracking()`
- Idempotent (checks `initialized` flag)
- Registers `window.addEventListener('error', ...)` for uncaught errors
- Registers `window.addEventListener('unhandledrejection', ...)` for promise rejections
- Starts `setInterval` for periodic flush
- Registers `visibilitychange` listener to flush on page hide (uses `keepalive: true` fetch)

#### `reportError(error: Error, context?: Record<string, unknown>)`
- Checks rate limit, increments counter
- Creates `ErrorReport` with message, stack, timestamp, url, userAgent
- Enqueues (drops oldest if buffer full)

#### `reportComponentError(error: Error, componentStack: string)`
- Same as `reportError` but includes React component stack trace
- Used by `FeatureErrorBoundary`

#### `_resetForTesting()`, `_getBuffer()`, `_flush()`
- Test helpers for unit tests

**Edge cases:**
- Rate limit window resets 60s after first error, not on a rolling basis
- `flush()` splices entire buffer atomically -- no partial flush
- Production POST failure is silently swallowed
- `keepalive: true` on page-hide flush ensures in-flight request survives navigation

---

## 6. Contexts

### `QuickActionsContext` -- `src/contexts/QuickActionsContext.tsx` (179 lines)
**Purpose:** Command palette, deal comparison list, and watchlist management.

**Context value:**
| Field | Type | Description |
|-------|------|-------------|
| `isCommandPaletteOpen` | `boolean` | Palette visibility |
| `toggleCommandPalette()` | function | Toggle palette |
| `comparisonDeals` | `Deal[]` | Deals selected for comparison (max 4) |
| `addToComparison(deal)` | function | Add deal, FIFO drop if >4 |
| `removeFromComparison(dealId)` | function | Remove by ID |
| `clearComparison()` | function | Clear all |
| `isInComparison(dealId)` | function | Check membership |
| `watchlistIds` | `string[]` | Watched deal IDs |
| `toggleWatchlist(dealId)` | function | Add/remove from watchlist |
| `isWatched(dealId)` | function | Check if watched |
| `recentActions` | `RecentAction[]` | Last 10 actions |
| `addRecentAction(action)` | function | Prepend action, cap at 10 |

**Internal state:** All via `useState`. Watchlist persisted to `localStorage` key `br-capital-watchlist`.

**Edge cases:**
- Comparison max 4: when adding a 5th, oldest is dropped (FIFO)
- `recentActions` capped at 10 items

---

### `ToastContext` -- `src/contexts/ToastContext.tsx` (15 lines)
**Purpose:** Thin wrapper that renders `<ToastContainer />` from notificationStore.

**Children:** Renders `children` + `<ToastContainer />` overlay.

---

## 7. Shared Hooks

### `useNotify` -- `src/hooks/useNotify.ts` (23 lines)
**Purpose:** Thin wrapper around `useToast` providing a consistent notification API.

**Returns:** `{ success, error, warning, info, dismiss }` -- all functions from `useToast`.

**Usage:** `const notify = useNotify(); notify.success('Saved!');`

---

### `useToast` -- `src/hooks/useToast.ts` (75 lines)
**Purpose:** Toast creation methods wrapping `notificationStore`.

**Returns:** `useCallback`-wrapped methods:
- `success(title, description?, duration?)` -- adds toast with variant `success`
- `error(title, description?, duration?)` -- variant `destructive`
- `warning(title, description?, duration?)` -- variant `warning`
- `info(title, description?, duration?)` -- variant `default`
- `dismiss(id)` -- removes toast by ID

**Stores accessed:** `notificationStore.addToast`, `notificationStore.removeToast`

---

### `useGlobalSearch` -- `src/hooks/useGlobalSearch.ts` (94 lines)
**Purpose:** Fuse.js-powered search across properties and transactions.

**Internal state:**
- `debouncedQuery` -- 300ms debounced version of input query
- `results` -- top 10 Fuse.js matches

**Dependencies:** `useProperties()`, `useTransactions()` for search corpus.

**Behavior:**
- Builds Fuse.js index from properties (name, address, city) and transactions (description, type)
- Searches on `debouncedQuery` change
- Returns max 10 results, each with `type`, `id`, `title`, `subtitle`, `score`

---

### `useFilterPersistence` -- `src/hooks/useFilterPersistence.ts` (157 lines)
**Purpose:** Bidirectional sync between filter state objects and URL search params.

**Props:**
- `filters` -- current filter state object
- `setFilters` -- state setter
- `prefix?` -- URL param prefix to namespace filters
- `exclude?` -- keys to exclude from URL

**Behavior:**
- On mount: reads URL params, merges into filter state
- On filter change: updates URL params (via `useSearchParams`)
- On URL change (e.g. back/forward): updates filter state

**Edge cases:**
- Uses `useRef` for "source of truth" tracking to prevent infinite loops between URL and state sync
- Boolean and number params are coerced from strings

---

### `useWebSocket` -- `src/hooks/useWebSocket.ts` (232 lines)
**Purpose:** WebSocket connection with auto-reconnect and exponential backoff.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `channel` | `string` | required | WebSocket channel name |
| `options.enabled` | `boolean` | `true` | Whether connection should be active |
| `options.maxRetries` | `number` | `10` | Max reconnect attempts |
| `options.baseDelay` | `number` | `1000` | Base backoff delay (ms) |
| `options.maxDelay` | `number` | `30000` | Max backoff delay (ms) |
| `options.onOpen` | `() => void` | -- | Connection opened callback |
| `options.onClose` | `(event: CloseEvent) => void` | -- | Connection closed callback |
| `options.onMessage` | `(message: WSMessage) => void` | -- | Message received callback |
| `options.onError` | `(event: Event) => void` | -- | Error callback |

**Returns:** `{ status, lastMessage, sendMessage, subscribe, unsubscribe }`

**Internal state:**
- `status: ConnectionStatus` -- `'connecting' | 'open' | 'closing' | 'closed'`
- `lastMessage: WSMessage | null`
- `wsRef` -- WebSocket instance ref
- `retriesRef` -- current retry count
- `reconnectTimerRef` -- pending reconnect timeout
- `unmountedRef` -- prevents setState after unmount

**Side effects:**
- Opens WebSocket to `ws://{API_URL}/ws/{channel}?token={accessToken}`
- Auto-responds to server `ping` messages with `pong`
- On close: schedules reconnect with exponential backoff (`baseDelay * 2^retries`, capped at `maxDelay`)
- Cleanup: closes WebSocket, clears timers on unmount

**Stores accessed:** `authStore.getState().accessToken` (read-only, not subscribed)

**Edge cases:**
- Auth token is read at connect time from `authStore.getState()` -- does not re-read on token refresh during an active connection
- Uses `callbacksRef` pattern to keep callback references stable without re-running the connection effect
- `connectWsRef` indirection allows reconnect timers to call the latest `connectWs` closure
- Initial connection deferred via `setTimeout(0)` to avoid synchronous setState in effect body

---

### `useCursorPagination` -- `src/hooks/useCursorPagination.ts` (183 lines)
**Purpose:** Cursor-based pagination with forward/back navigation.

**Type parameter:** `T` -- the page response type

**Parameters:**
- `queryKey` -- base React Query key
- `queryFn(cursor?)` -- fetches page, returns `{ items: T[], nextCursor?, hasMore }`
- `options?` -- staleTime, enabled

**Returns:**
- `data` -- current page data
- `isLoading`, `isFetching`, `error`
- `goForward()` -- push current cursor to history stack, advance to `nextCursor`
- `goBack()` -- pop cursor from history stack
- `canGoForward` -- `hasMore` flag
- `canGoBack` -- history stack length > 0

**Internal state:**
- `cursorStack: string[]` -- history of previous cursors for back navigation
- `currentCursor: string | undefined`

**React Query integration:** Uses `placeholderData: keepPreviousData` for smooth transitions.

---

### `useIntersectionObserver` -- `src/hooks/useIntersectionObserver.ts` (135 lines)
**Purpose:** IntersectionObserver wrapper for lazy-loading and visibility detection.

**Parameters:**
- `options.threshold?` -- visibility threshold (default 0)
- `options.root?` -- scroll ancestor
- `options.rootMargin?` -- margin around root
- `options.triggerOnce?` -- if true, disconnects after first intersection

**Returns:** `{ ref, isIntersecting, entry }`

**Edge cases:**
- Falls back to `isIntersecting: true` if `IntersectionObserver` is not supported
- Disconnects observer on unmount
- `triggerOnce` mode: sets `isIntersecting` permanently to true, then disconnects

---

### `usePrefetch` -- `src/hooks/usePrefetch.ts` (329 lines)
**Purpose:** Route-level data and component chunk prefetching on link hover/focus.

**Behavior:**
- 150ms debounce prevents prefetch on quick mouse movements
- Tracks already-prefetched routes in a `Set` (avoids redundant prefetch)
- For each route, defines `RoutePrefetchConfig[]` with query keys, query functions, stale times
- Also triggers dynamic `import()` for lazy-loaded route components

**Route configs:**
| Route | Data Prefetched | Stale Time |
|-------|----------------|------------|
| `/properties` | property list | 5min |
| `/deals` | deals list, kanban | 5min |
| `/transactions` | transaction list | 5min |
| `/market-data` | market overview | 15min |
| `/interest-rates` | current rates | 5min |
| `/reports` | templates | 15min |
| `/documents` | document list | 5min |
| `/extraction` | extraction runs | 2min |

**Returns:** `{ prefetchRoute(path), PrefetchLink }` -- `PrefetchLink` is a `<Link>` with `onMouseEnter`/`onFocus` handlers.

---

### `usePrefetchDashboard` -- `src/hooks/usePrefetchDashboard.ts` (124 lines)
**Purpose:** Warms React Query cache on app boot with dashboard-critical data.

**Prefetched on mount:**
- Market overview (15min stale)
- Interest rates (5min stale)
- Report templates (15min stale)
- Properties list (5min stale)

**No return value** -- pure side-effect hook.

---

## 8. API Hooks (React Query)

All API hooks follow this pattern:
- **Query key factory** -- hierarchical keys for granular invalidation
- **Query hooks** -- `useQuery` with typed responses and staleTime
- **Mutation hooks** -- `useMutation` with cache invalidation via `queryClient.invalidateQueries`
- **Prefetch utilities** -- `queryClient.prefetchQuery` helpers

### `useProperties` -- `src/hooks/api/useProperties.ts` (232 lines)

**Query key factory:** `propertyKeys`
```
all: ['properties']
lists: ['properties', 'list']
list(filters): ['properties', 'list', filters]
details: ['properties', 'detail']
detail(id): ['properties', 'detail', id]
summary: ['properties', 'summary']
```

**Query hooks:**

| Hook | Endpoint | StaleTime | Notes |
|------|----------|-----------|-------|
| `useProperties(filters?)` | via `fetchProperties` | 10min | Mock-fallback enabled |
| `usePropertiesApi(filters?)` | GET `/properties` | default | API-first, no fallback |
| `useProperty(id?)` | via `fetchPropertyById` | 10min | `enabled: !!id` |
| `usePropertyApi(id)` | GET `/properties/{id}` | default | API-first |
| `usePortfolioSummary()` | via `fetchPortfolioSummary` | 10min | Portfolio aggregates |
| `usePropertySummary()` | GET `/properties/summary` | default | API-first summary |

**Mutation hooks:**
- `useCreateProperty()` -- POST `/properties`, invalidates lists + summary
- `useUpdateProperty()` -- PUT `/properties/{id}`, updates detail cache + invalidates lists + summary
- `useDeleteProperty()` -- DELETE `/properties/{id}`, removes detail cache + invalidates lists

**Prefetch utilities:**
- `usePrefetchProperty()` -- returns function to prefetch a single property (5min stale)
- `usePrefetchNextPage()` -- prefetch next page of property list

**Helper:** `selectProperties(data)` -- extracts `properties` array from response, defaulting to `[]`.

---

### `useDeals` -- `src/hooks/api/useDeals.ts` (620 lines)

**Query key factory:** `dealKeys`
```
all: ['deals']
lists: ['deals', 'list']
list(filters): ['deals', 'list', filters]
details: ['deals', 'detail']
detail(id): ['deals', 'detail', id]
pipeline: ['deals', 'pipeline']
pipelineByStage(stage): ['deals', 'pipeline', stage]
kanban(filters?): ['deals', 'kanban', filters]
stats: ['deals', 'stats']
activities(dealId): ['deals', 'activities', dealId]
proformaReturns(dealId): ['deals', 'proforma-returns', dealId]
```

**Query hooks:**

| Hook | Endpoint | StaleTime | Notes |
|------|----------|-----------|-------|
| `useDealsWithMockFallback()` | GET `/deals?page_size=100` | 5min | Parses via `backendDealSchema` |
| `useKanbanBoardWithMockFallback(filters?)` | GET `/deals/kanban` | 5min | Maps backend stages to frontend |
| `useDealsApi(filters)` | GET `/deals` | default | API-first, typed `DealListResponse` |
| `useDealApi(id)` | GET `/deals/{id}` | default | `enabled: !!id` |
| `useDealStats()` | GET `/deals/stats` | default | Summary statistics |
| `useDealActivities(dealId)` | GET `/deals/{id}/activities` | 5min | Activity feed |
| `useDealProformaReturns(dealId)` | GET `/deals/{id}/proforma-returns` | 5min | Extracted financial data |

**Mutation hooks:**
- `useCreateDeal()` -- POST `/deals`, invalidates lists + kanban + stats
- `useUpdateDeal()` -- PUT `/deals/{id}`, updates detail + invalidates lists + kanban + stats
- `useUpdateDealStage()` -- PATCH `/deals/{id}/stage`, **optimistic update** on kanban cache (moves deal between columns instantly, rolls back on error)
- `useDeleteDeal()` -- DELETE `/deals/{id}`, removes detail + invalidates lists + kanban + stats

**Stage mapping:** Backend uses lowercase stages (`initial_review`, `active_review`, etc.). `mapBackendStage()` converts between frontend and backend stage names.

**Optimistic update pattern (useUpdateDealStage):**
1. `onMutate`: snapshots kanban cache, optimistically moves deal to new stage
2. `onError`: rolls back to snapshot
3. `onSettled`: invalidates kanban to get server truth

---

### `useExtraction` -- `src/hooks/api/useExtraction.ts` (271 lines)

**Query key factory:** `extractionKeys`
```
all: ['extraction']
runs: ['extraction', 'runs']
run(id): ['extraction', 'runs', id]
results(runId): ['extraction', 'results', runId]
fileResults(runId, fileId): ['extraction', 'results', runId, fileId]
```

**Query hooks:**

| Hook | Endpoint | StaleTime | Polling |
|------|----------|-----------|---------|
| `useExtractionRuns()` | GET `/extraction/runs` | 2min | -- |
| `useExtractionRun(id)` | GET `/extraction/runs/{id}` | 2min | 2s when `status === 'running'` |
| `useExtractionResults(runId)` | GET `/extraction/runs/{id}/results` | 5min | -- |

**Mutation hooks:**
- `useStartExtraction()` -- POST `/extraction/runs`, invalidates runs
- `useValidateExtraction(runId)` -- POST `/extraction/runs/{id}/validate`, invalidates run + results
- `useRetryExtraction(runId)` -- POST `/extraction/runs/{id}/retry`, invalidates runs
- `useCancelExtraction(runId)` -- POST `/extraction/runs/{id}/cancel`, invalidates runs

**Polling:** `useExtractionRun` uses `refetchInterval: (query) => query.state.data?.status === 'running' ? 2000 : false` for live status updates during active extraction.

---

### `useDealComparison` -- `src/hooks/api/useDealComparison.ts` (97 lines)

**Purpose:** Fetches comparison data for selected deals.

**Hook:** `useDealComparison(dealIds: string[])`
- Endpoint: GET `/deals/compare?ids=a,b,c`
- `enabled: dealIds.length >= 2`
- Response validated via Zod schema
- StaleTime: 5min

---

### `usePropertyActivities` -- `src/hooks/api/usePropertyActivities.ts` (198 lines)

**Query key factory:** `propertyActivityKeys`

**Hook:** `usePropertyActivities(propertyId, filters?)`
- Endpoint: GET `/properties/{id}/activities`
- StaleTime: 2min
- Transform: snake_case API response to camelCase via manual mapping

**Mutation:** `useCreatePropertyActivity()` -- POST, invalidates activities for the property.

---

### `useInterestRates` -- `src/hooks/api/useInterestRates.ts` (592 lines)

**Query key factory:** `interestRateKeys`
```
all: ['interest-rates']
current: ['interest-rates', 'current']
yieldCurve: ['interest-rates', 'yield-curve']
historical(months): ['interest-rates', 'historical', months]
spreads(months): ['interest-rates', 'spreads', months]
dataSources: ['interest-rates', 'data-sources']
lendingContext: ['interest-rates', 'lending-context']
```

**Query hooks:**

| Hook | Endpoint | StaleTime | Notes |
|------|----------|-----------|-------|
| `useKeyRates()` | GET `/interest-rates/current` | 15min | Transforms snake_case response |
| `useYieldCurve()` | GET `/interest-rates/yield-curve` | 15min | Array of yield curve points |
| `useHistoricalRates(months)` | GET `/interest-rates/historical` | 30min | Time series data |
| `useRateSpreads(months)` | GET `/interest-rates/spreads` | 30min | Spread calculations |
| `useRateDataSources()` | GET `/interest-rates/data-sources` | 1hr | Source metadata |
| `useLendingContext()` | GET `/interest-rates/lending-context` | 30min | CRE lending environment |

**Transform functions:** Each hook has a dedicated transform function (e.g., `transformKeyRates`, `transformYieldCurve`) that maps snake_case API fields to camelCase TypeScript types.

**Prefetch:** `usePrefetchInterestRates()` -- prefetches current rates + yield curve.

---

### `useTransactions` -- `src/hooks/api/useTransactions.ts` (350 lines)

**Query key factory:** `transactionKeys`

**Query hooks:**

| Hook | Endpoint | StaleTime |
|------|----------|-----------|
| `useTransactions(filters?)` | via `fetchTransactions` | 7min |
| `useTransactionsApi(filters)` | GET `/transactions` | default |
| `useTransaction(id)` | via `fetchTransactionById` | 7min |
| `useTransactionApi(id)` | GET `/transactions/{id}` | default |

**Mutation hooks:** `useCreateTransaction`, `useUpdateTransaction`, `useDeleteTransaction`, `usePatchTransaction` -- all invalidate lists.

---

### `useDocuments` -- `src/hooks/api/useDocuments.ts` (337 lines)

**Query key factory:** `documentKeys`

**Query hooks:**

| Hook | Endpoint | StaleTime |
|------|----------|-----------|
| `useDocuments(filters?)` | GET `/documents` | 5min |
| `useDocument(id)` | GET `/documents/{id}` | 5min |

**Mutation hooks:** `useUploadDocument`, `useUpdateDocument`, `useDeleteDocument`

**Transform:** Handles dual field name mapping (`file_name` / `filename`, `file_size` / `filesize`) for backend compatibility.

---

### `useMarketData` -- `src/hooks/api/useMarketData.ts` (418 lines)

**Query key factory:** `marketDataKeys`

**Query hooks:**

| Hook | Endpoint | StaleTime |
|------|----------|-----------|
| `useMarketOverview()` | GET `/market/overview` | 15min |
| `useMarketSubmarkets()` | GET `/market/submarkets` | 15min |
| `useSubmarketDetail(id)` | GET `/market/submarkets/{id}` | 15min |
| `useMarketTrends(params)` | GET `/market/trends` | 15min |

**Transforms:** Full snake_case to camelCase transforms for all response types.

---

### `useReporting` -- `src/hooks/api/useReporting.ts` (755 lines)

**Query key factory:** `reportingKeys`

**Query hooks:**

| Hook | Endpoint | StaleTime | Notes |
|------|----------|-----------|-------|
| `useReportTemplates()` | GET `/reports/templates` | 15min | Template list |
| `useReportTemplate(id)` | GET `/reports/templates/{id}` | 15min | Single template |
| `useReportQueue()` | GET `/reports/queue` | 30sec | **Frequent polling** |
| `useReportWidgets()` | GET `/reports/widgets` | 30min | Dashboard widgets |
| `useDistributionSchedules()` | GET `/reports/schedules` | 15min | Email schedules |

**Mutation hooks:**
- `useCreateTemplate`, `useUpdateTemplate`, `useDeleteTemplate`
- `useGenerateReport` -- POST `/reports/generate`, invalidates queue
- `useCreateSchedule`, `useUpdateSchedule`, `useDeleteSchedule`

**Notable:** Report queue has 30-second staleTime for near-real-time status updates during report generation.

---

## 9. Feature-Level Hooks

### `useGroupPipeline` -- `src/features/extraction/hooks/useGroupPipeline.ts` (360 lines)

**Purpose:** UW model group pipeline management -- scanning, grouping, extracting.

**8 mutation hooks:**
- `useScanGroups()` -- POST `/extraction/groups/scan`
- `useCreateGroup()` -- POST `/extraction/groups`
- `useUpdateGroup()` -- PUT `/extraction/groups/{id}`
- `useDeleteGroup()` -- DELETE `/extraction/groups/{id}`
- `useRunGroupExtraction()` -- POST `/extraction/groups/{id}/extract`
- `useBulkRunExtraction()` -- POST `/extraction/groups/bulk-extract`
- `useAssignFilesToGroup()` -- POST `/extraction/groups/{id}/assign`
- `useUnassignFiles()` -- POST `/extraction/groups/{id}/unassign`

**Pattern:** Each mutation follows consistent pattern:
1. Call API
2. Invalidate relevant query keys
3. Return `mutateAsync` (not `mutate`)

---

### `useExtraction` (feature) -- `src/features/extraction/hooks/useExtraction.ts` (354 lines)

**Purpose:** Legacy extraction hook with client-side filtering and value grouping.

**Internal state:**
- `activeTab` -- `'runs' | 'results' | 'values'`
- `searchQuery` -- filter text
- `selectedRunId` -- currently selected extraction run

**Computed values (via `useMemo`):**
- `filteredRuns` -- runs filtered by search query
- `groupedValues` -- extracted values grouped by category (e.g., financial, property, operating)

**Dependencies:** `useExtractionRuns()`, `useExtractionResults()`

---

## 10. Error Boundaries

### `ErrorBoundary` -- `src/components/ErrorBoundary.tsx` (122 lines)

**Purpose:** Root-level error boundary. Class component (required by React error boundary API).

**Props:**
| Prop | Type | Description |
|------|------|-------------|
| `children` | `ReactNode` | Protected content |
| `fallback` | `ReactNode \| ((error, reset) => ReactNode)` | Custom fallback UI |
| `onError` | `(error, errorInfo) => void` | Error callback |

**Internal state:** `hasError`, `error`, `errorInfo`

**Behavior:**
- `getDerivedStateFromError` -- sets `hasError: true`
- `componentDidCatch` -- logs to console, calls `onError` prop
- Default fallback: centered card with error message, "Try Again" and "Reload Page" buttons
- Dev mode: collapsible stack trace details
- `handleReset()` -- clears error state to re-attempt render

---

### `FeatureErrorBoundary` -- `src/components/FeatureErrorBoundary.tsx` (78 lines)

**Purpose:** Feature-scoped error boundary that reports to error tracking service.

**Props:**
| Prop | Type | Description |
|------|------|-------------|
| `children` | `ReactNode` | Feature content |
| `featureName` | `string` | Display name (e.g. "Analytics") |

**Behavior:**
- Wraps `<ErrorBoundary>` with render-function fallback
- `onError` calls `reportComponentError(error, componentStack)` -- sends to error tracking service
- Fallback shows compact card: "{featureName} failed to load" with error message and "Try Again" button
- Explicitly states "The rest of the application is unaffected"

**Used on routes:** deals, properties, transactions, sales-analysis, interest-rates

---

## 11. Shared Components

### `StatCard` -- `src/components/shared/StatCard.tsx` (117 lines)

**Purpose:** Reusable stat display card with optional icon and trend indicator.

**Props:**
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `label` | `string` | required | Title above (or below for hero) the value |
| `value` | `string` | required | Pre-formatted display value |
| `subtitle` | `string` | -- | Description below value |
| `icon` | `LucideIcon` | -- | Optional icon component |
| `iconColor` | `string` | `'text-neutral-600'` | Icon color class |
| `iconBgColor` | `string` | `'bg-neutral-100'` | Icon background class |
| `trend` | `'up' \| 'down' \| 'neutral'` | -- | Trend direction |
| `trendValue` | `number` | -- | Trend percentage (absolute value displayed) |
| `variant` | `'default' \| 'compact' \| 'hero'` | `'default'` | Size variant |
| `className` | `string` | -- | Additional classes |

**Rendering:**
- `hero`: larger padding, shadow-card-hover on hover, label below value
- `compact`: smaller padding, smaller text
- `default`: standard padding and text
- Trend indicator: TrendingUp/TrendingDown icon + percentage, green/red/neutral coloring
- Trend hidden when `trend === 'neutral'`

---

### `PageLoadingState` -- `src/components/shared/PageLoadingState.tsx` (83 lines)

**Purpose:** Page-level loading skeleton with configurable stat cards and charts.

**Props:**
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `title` | `string` | required | Page title shown during load |
| `subtitle` | `string` | -- | Optional subtitle |
| `statCards` | `number` | `4` | Number of stat card skeletons |
| `statCardColumns` | `string` | responsive grid | Grid column classes |
| `chartHeights` | `number[]` | `[]` | Heights for chart skeletons |
| `chartLayout` | `'grid' \| 'stack'` | `'stack'` | Chart arrangement |
| `headerExtra` | `ReactNode` | -- | Extra header content (tabs, buttons) |
| `titleClassName` | `string` | page-title styles | Title CSS classes |
| `className` | `string` | -- | Container classes |

**Dependencies:** `StatCardSkeleton`, `ChartSkeleton` from `@/components/skeletons`

---

### `InlineEmptyState` -- `src/components/shared/InlineEmptyState.tsx` (25 lines)

**Purpose:** Lightweight inline "no data" message for widgets and sections.

**Props:**
| Prop | Type | Default |
|------|------|---------|
| `message` | `string` | `'No data available'` |
| `className` | `string` | -- |

**Renders:** Centered muted text with vertical padding.

---

### `VirtualizedTable` -- `src/components/shared/VirtualizedTable.tsx` (194 lines)

**Purpose:** Virtualized table using `@tanstack/react-virtual` with shadcn/ui Table styling.

**Generic type:** `VirtualizedTable<T>` -- rows are typed `T[]`.

**Props:**
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `rows` | `T[]` | required | Data array |
| `renderHeader` | `() => ReactNode` | required | Table header content |
| `renderRow` | `(row: T, index: number) => ReactNode` | required | Row render function |
| `estimateRowHeight` | `number` | `52` | Estimated row height (px) |
| `overscan` | `number` | `10` | Extra rows rendered outside viewport |
| `getRowKey` | `(row: T, index: number) => string \| number` | required | Unique key extractor |
| `height` | `number \| string` | `600` | Scroll container height |
| `virtualizeThreshold` | `number` | `50` | Min rows before virtualization activates |
| `className` | `string` | -- | Outer container classes |
| `tableClassName` | `string` | -- | Table element classes |

**Architecture:**
- Below threshold: renders plain `<table>` with all rows (no virtualization overhead)
- Above threshold: delegates to `VirtualizedTableInner` which uses `useVirtualizer`
  - Sticky header via `position: sticky; top: 0; z-10`
  - Padding spacer rows for scroll position
  - `VirtualizedTableRowWrapper` -- trivial fragment wrapper for key management

**Edge cases:**
- Spacer `<td>` elements use `colSpan` of 1 -- may cause visual issues if table has multiple columns (spacer only fills first column). See Issues Found.

---

## 12. Skeleton Components

### `ComparisonSkeleton` -- `src/features/deals/components/comparison/ComparisonSkeleton.tsx` (101 lines)
**Purpose:** Loading skeleton for deal comparison view.
**Renders:** 3-column grid of skeleton cards with metric rows, mimicking comparison table layout.

### `InterestRatesSkeleton` -- `src/features/interest-rates/components/InterestRatesSkeleton.tsx` (66 lines)
**Purpose:** Loading skeleton for interest rates page.
**Renders:** 4 stat card skeletons + 2 chart skeletons (yield curve + historical).

### `PropertyDetailSkeleton` -- `src/features/property-detail/components/PropertyDetailSkeleton.tsx` (110 lines)
**Purpose:** Loading skeleton for property detail page.
**Renders:** Header skeleton (image placeholder + stat cards) + tabbed content skeletons.

---

## 13. Feature Components: Dashboard

**Location:** `src/features/dashboard/`

### `DashboardPage`
- **Purpose:** Main dashboard view with KPI cards, charts, and activity feed
- **Hooks:** `useProperties()`, `useTransactions()`, `usePortfolioSummary()`, `useDealStats()`
- **Children:** `StatCard` grid, chart components (Recharts), `ActivityTimeline`
- **Loading:** `PageLoadingState` with 4 stat cards + 2 chart skeletons

### `ActivityTimeline`
- **Purpose:** Recent activity feed with date grouping
- **Hooks:** `usePropertyActivities()`
- **Uses:** `formatRelativeTime()`, `getDateGroupLabel()` from `dateUtils.ts`

---

## 14. Feature Components: Deals

**Location:** `src/features/deals/`

### `DealsPage`
- **Purpose:** Deals management with Kanban board and list views
- **Hooks:** `useKanbanBoardWithMockFallback()`, `useDealsWithMockFallback()`
- **State:** View mode (`kanban` | `list`), filters, selected deal
- **Children:** `KanbanBoard`, `DealsList`, `DealDetailModal`, `DealFilters`

### `KanbanBoard`
- **Purpose:** Drag-and-drop deal pipeline visualization
- **Hooks:** `useUpdateDealStage()` for optimistic stage changes
- **Stages:** Dead, Initial Review, Active Review, Under Contract, Closed, Realized

### `DealDetailModal`
- **Purpose:** Full deal detail view in modal overlay
- **Hooks:** `useDealApi()`, `useDealActivities()`, `useDealProformaReturns()`
- **Sections:** Overview, financials, activity, proforma returns (collapsible, 30 fields)

### `CompareDealsView`
- **Purpose:** Side-by-side deal comparison
- **Context:** `QuickActionsContext` for `comparisonDeals`
- **Hooks:** `useDealComparison(dealIds)`
- **Loading:** `ComparisonSkeleton`

---

## 15. Feature Components: Properties

**Location:** `src/features/properties/`

### `PropertiesPage`
- **Purpose:** Property portfolio list with filtering and sorting
- **Hooks:** `useProperties()`, `useFilterPersistence()`
- **Children:** Property table/grid, filters, `StatCard` summary row

---

## 16. Feature Components: Property Detail

**Location:** `src/features/property-detail/`

### `PropertyDetailPage`
- **Purpose:** Individual property deep-dive with tabbed sections
- **Hooks:** `useProperty(id)`, `usePropertyActivities(id)`
- **Tabs:** Overview, financials, operations, documents, activity
- **Loading:** `PropertyDetailSkeleton`

---

## 17. Feature Components: Transactions

**Location:** `src/features/transactions/`

### `TransactionsPage`
- **Purpose:** Transaction management with filtering and CRUD
- **Hooks:** `useTransactions()`, `useFilterPersistence()`
- **Children:** Transaction table, create/edit forms, filters

---

## 18. Feature Components: Market Data / Sales Analysis

**Location:** `src/features/market-data/`, `src/features/sales-analysis/`

### `MarketDataPage`
- **Purpose:** CoStar submarket analytics with charts
- **Hooks:** `useMarketOverview()`, `useMarketSubmarkets()`, `useMarketTrends()`

### `SalesAnalysisPage`
- **Purpose:** Sales comp analysis with interactive charts
- **Hooks:** `useMarketData` hooks for sales data
- **Charts:** Recharts bar/line/scatter for comp analysis

---

## 19. Feature Components: Interest Rates

**Location:** `src/features/interest-rates/`

### `InterestRatesPage`
- **Purpose:** Interest rate dashboard with multiple data views
- **Hooks:** `useKeyRates()`, `useYieldCurve()`, `useHistoricalRates()`, `useRateSpreads()`, `useLendingContext()`
- **Charts:** Yield curve chart, historical rate trends, spread analysis
- **Loading:** `InterestRatesSkeleton`

---

## 20. Feature Components: Reporting Suite

**Location:** `src/features/reporting-suite/`

### `ReportingPage`
- **Purpose:** Report management -- templates, queue, schedules, widgets
- **Hooks:** `useReportTemplates()`, `useReportQueue()`, `useDistributionSchedules()`, `useReportWidgets()`
- **Tabs:** Templates, Queue, Schedules, Widgets

### `ReportSettings`
- **Purpose:** Report template configuration form
- **Hooks:** `useCreateTemplate()`, `useUpdateTemplate()`
- **Validation:** Zod schema for form data

---

## 21. Feature Components: Extraction

**Location:** `src/features/extraction/`

### `ExtractionPage`
- **Purpose:** UW model extraction management
- **Hooks:** `useExtraction()` (feature hook), `useGroupPipeline()`
- **Tabs:** Runs, Results, Values, Group Pipeline
- **Children:** Run list, result viewer, value browser, group manager

---

## 22. Feature Components: Documents

**Location:** `src/features/documents/`

### `DocumentsPage`
- **Purpose:** Document management with upload and search
- **Hooks:** `useDocuments()`, `useUploadDocument()`
- **Features:** File upload, search, filtering by type/property

---

## 23. Feature Components: Construction Pipeline

**Location:** `src/features/construction/`

### `ConstructionPage`
- **Purpose:** Construction project tracking
- **Features:** Project timeline, milestone tracking, budget vs actual

---

## 24. Feature Components: Settings

**Location:** `src/features/settings/`

### `SettingsPage`
- **Purpose:** Application settings and user preferences
- **Sections:** Profile, notifications, display preferences

---

## 25. Feature Components: Login

**Location:** `src/features/login/`

### `LoginPage`
- **Purpose:** Authentication form
- **Hooks:** `useAuthStore()` for `login()` action
- **State:** email, password, error message, loading
- **Behavior:** On success, redirects to saved location or `/`. On error, displays error message.
- **Edge case:** Must handle `ApiError` from authStore.login()

---

## 26. Utility Libraries

### `dateUtils.ts` -- `src/lib/dateUtils.ts` (166 lines)

**Purpose:** Consolidated date/time formatting. All functions null-safe, never throw.

| Function | Signature | Output Example |
|----------|-----------|----------------|
| `parseDate(value)` | `string \| Date \| null \| undefined => Date \| null` | `Date` or `null` |
| `isValidDate(value)` | `unknown => boolean` | `true`/`false` |
| `formatDate(date, style?)` | `..., 'short'\|'medium'\|'long' => string` | `"Mar 10, 2026"` (medium) |
| `formatDateTime(date)` | `... => string` | `"Mar 10, 2026 2:30 PM"` |
| `formatTime(date)` | `... => string` | `"2:30 PM"` |
| `formatRelativeTime(date)` | `... => string` | `"just now"`, `"5m ago"`, `"3d ago"` |
| `getDateGroupLabel(date)` | `... => string` | `"Today"`, `"Yesterday"`, `"Monday"` |

**Implementation notes:**
- `parseDate` handles `Date` objects, ISO strings, and rejects `NaN` dates
- `isValidDate` accepts `unknown`, handles Date/string/number inputs
- `formatRelativeTime` thresholds: <1min="just now", <60min="{n}m ago", <24hr="{n}h ago", <7d="{n}d ago", else short date
- `getDateGroupLabel` uses date-only comparison (strips time), omits year if same as current

---

### `formatters.ts` -- `src/lib/utils/formatters.ts` (112 lines)

**Purpose:** Number, currency, and percentage formatters with OrNA variants.

**Key functions:**
- `formatCurrency(value)` -- `$1,234,567`
- `formatCurrencyOrNA(value)` -- returns `"N/A"` for null/undefined/0
- `formatPercent(value)` -- `5.2%`
- `formatPercentOrNA(value)` -- returns `"N/A"` for null/undefined
- `formatNumber(value)` -- locale-formatted number
- `formatCompact(value)` -- `$1.2M`, `$500K`

**Edge case:** `formatCurrencyOrNA` treats `0` as N/A -- this is intentional for real estate metrics where 0 typically means "not available" rather than zero dollars.

---

### `config.ts` -- `src/lib/config.ts` (76 lines)

**Exports:**
- `API_URL` -- from `VITE_API_BASE_URL` env var, defaults to `http://localhost:8000/api/v1`
- `APP_ENV` -- `'development' | 'staging' | 'production'`
- `IS_DEV`, `IS_PROD` -- boolean helpers
- `FEATURE_FLAGS` -- object with boolean flags for progressive feature rollout
- `MOCK_FALLBACK_ENABLED` -- whether to use mock data when API fails

---

### `queryClient.ts` -- `src/lib/queryClient.ts` (41 lines)

**Purpose:** React Query client configuration.

**Defaults:**
| Setting | Value | Purpose |
|---------|-------|---------|
| `staleTime` | `5 * 60 * 1000` (5min) | Default for queries without explicit staleTime |
| `gcTime` | `30 * 60 * 1000` (30min) | Garbage collection of unused cache entries |
| `retry` | `1` | Retry failed queries once |
| `refetchOnWindowFocus` | `false` | Disabled to prevent unwanted refetches |

---

## 27. Zod Schemas

**Location:** `src/lib/api/schemas/`

**Purpose:** All Zod schemas validate and transform API responses from snake_case (backend) to camelCase (frontend).

### `deal.ts`
- `backendDealSchema` -- parses raw deal API response
- `mapBackendStage(stage)` -- maps backend stage strings to frontend enum
- Handles nullable fields with `.nullable().optional()` pattern

### `property.ts`
- Property schema with nested address, financial, and operations transforms

### `transaction.ts`
- Transaction schema with amount, date, and type transforms

### `document.ts`
- Handles dual field names (`file_name`/`filename`, `file_size`/`filesize`)

**Pattern:** All schemas use `.nullable().optional()` with `?? undefined` (NOT `?? 0`) to ensure N/A display rather than misleading zeros.

---

## 28. Type Definitions

**Location:** `src/types/`

**Key type files:**
- `deal.ts` -- `Deal`, `DealStage`, `DealType`
- `property.ts` -- `Property`, `PropertySummaryStats`
- `api.ts` -- Request/response types for all API endpoints (`*Filters`, `*ApiResponse`, `*CreateInput`, `*UpdateInput`)
- `interest-rates.ts` -- `KeyRate`, `YieldCurvePoint`, `HistoricalRate`, `RateDataSource`
- `notification.ts` -- `Toast`, `ToastOptions`
- `search.ts` -- `SearchResult`

---

## 29. Issues Found

| # | Severity | File:Line | Description | Recommended Fix |
|---|----------|-----------|-------------|-----------------|
| 1 | **Medium** | `src/lib/api/client.ts:14` | ETag cache (`etagCache`) is a module-scoped `Map` with no eviction policy. Long-running sessions with many unique GET URLs will accumulate unbounded entries. | Add LRU eviction (e.g., cap at 500 entries) or use `WeakRef`-based cache. Consider clearing on logout. |
| 2 | **Medium** | `src/lib/api/client.ts:80-86` | 304 response without cache hit falls through silently. If `etagCache.get(url)` returns `undefined` after a 304, the function continues to the `!response.ok` check. Since 304 is not `ok`, it would throw an `ApiError`. | Add explicit handling: throw a descriptive error or retry without `If-None-Match`. |
| 3 | **Low** | `src/lib/api/client.ts:120` | Non-JSON successful responses return `{} as T` -- a type assertion that silently produces an incorrect type at runtime. | Return `undefined` or `null` and update `T` constraint to `T | null`, or throw if JSON was expected. |
| 4 | **Medium** | `src/hooks/useWebSocket.ts:119` | Auth token is read from `authStore.getState().accessToken` at WebSocket connect time. If the token refreshes while the WebSocket is connected, the connection continues with the old token. If it reconnects after token refresh, it picks up the new token, which is correct. | Document this behavior. For long-lived connections, consider a mechanism to re-authenticate the WebSocket when the token changes. |
| 5 | **Low** | `src/hooks/useWebSocket.ts:108-110` | `callbacksRef` is updated in an effect without a dependency array, meaning it runs on every render. This is intentional (keeps refs current) but will trigger ESLint `react-hooks/exhaustive-deps` warnings. | Add `// eslint-disable-next-line react-hooks/exhaustive-deps` comment, or use a layout effect. |
| 6 | **Medium** | `src/hooks/useFilterPersistence.ts` | Bidirectional sync between URL params and filter state has potential for infinite update loops if the "source of truth" ref tracking has edge cases (e.g., rapid navigation + filter changes). | Add a guard counter or stabilize with `useRef` debounce to break any potential cycle. |
| 7 | **Low** | `src/components/shared/VirtualizedTable.tsx:169` | Spacer `<td>` elements do not set `colSpan` to match the actual number of table columns. In tables with multiple columns, the spacer only occupies the first column, potentially causing visual misalignment. | Accept a `columnCount` prop or infer from `renderHeader()` output, and set `colSpan={columnCount}` on spacer `<td>` elements. |
| 8 | **Low** | `src/services/errorTracking.ts:42-45` | Rate limit window uses a fixed 60s timeout from the first error. If 10 errors occur in the first second, all remaining errors in the next 59 seconds are dropped. | Consider a sliding window (ring buffer of timestamps) for more even rate limiting. |
| 9 | **Low** | `src/stores/notificationStore.ts:34` | Toast auto-removal `setTimeout` is not cleared if the toast is manually dismissed before the timer fires. The `removeToast` call is idempotent (filter by ID), so this is harmless but wastes timer resources. | Store timer IDs in a `Map<string, number>` and `clearTimeout` on manual removal. |
| 10 | **Low** | `src/stores/authStore.ts:100` | The `auth:unauthorized` event listener is registered at module load time (side effect of importing the module). If the module is imported in SSR or test environments without `window`, this would throw. | Guard with `typeof window !== 'undefined'` check. Currently safe since the app is SPA-only. |
| 11 | **Info** | `src/lib/dateUtils.ts` | `formatDate` in `dateUtils.ts` shares a name with potential duplicate `formatDate` functions in individual components. Components that have not been migrated to use `dateUtils.ts` may still have local implementations. | Audit all components for local date formatting and migrate to `dateUtils.ts`. |
| 12 | **Low** | `src/hooks/api/useDeals.ts:66` | `useDealsWithMockFallback` fetches with `page_size: 100` hardcoded. For portfolios with more than 100 deals, this silently truncates the result set. | Accept `pageSize` as parameter or implement pagination/infinite scroll. |
| 13 | **Info** | `src/hooks/api/useReporting.ts` | Report queue uses 30-second `staleTime` which means frequent refetches. If many users have the reporting page open, this creates significant server load. | Consider WebSocket-based updates for report queue status instead of polling. |
| 14 | **Low** | `src/contexts/QuickActionsContext.tsx` | Watchlist is persisted to localStorage but comparison deals are not. If the user refreshes the page, comparison selection is lost. | Consider persisting comparison deals to localStorage or sessionStorage. |
