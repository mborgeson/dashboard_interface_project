# Wave 9: Additional Integrations - Detailed Specification

**Version:** 1.0.0
**Date:** 2026-01-14
**Author:** SPARC Specification Agent
**Status:** Ready for Architecture Review

---

## Table of Contents

1. [Overview](#1-overview)
2. [Feature 1: Property Activity Feed](#2-feature-1-property-activity-feed)
3. [Feature 2: Quick Actions](#3-feature-2-quick-actions)
4. [Feature 3: Deal Comparison](#4-feature-3-deal-comparison)
5. [Data Flow Diagrams](#5-data-flow-diagrams)
6. [Validation Checklist](#6-validation-checklist)

---

## 1. Overview

### 1.1 Purpose

Wave 9 adds three integration features to enhance user productivity and provide contextual information throughout the B&R Capital Dashboard:

1. **Property Activity Feed** - Real-time activity tracking embedded in property detail pages
2. **Quick Actions** - Contextual action buttons with keyboard shortcuts
3. **Deal Comparison** - Side-by-side deal metric comparison tool

### 1.2 Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| React Query | ^5.x | Data fetching and caching |
| Radix UI | ^1.x | Accessible UI primitives |
| Tailwind CSS | ^3.x | Styling |
| dnd-kit | ^6.x | Drag-and-drop (existing) |
| recharts | ^2.x | Comparison charts |
| cmdk | ^1.x | Command palette (new) |

### 1.3 Constraints

- **Technical**: Must integrate with existing WebSocket infrastructure
- **Performance**: Activity feed updates must not exceed 100ms render time
- **Accessibility**: All features must be WCAG 2.1 AA compliant
- **Mobile**: FAB must work on touch screens (min 44x44px touch targets)

---

## 2. Feature 1: Property Activity Feed

### 2.1 Requirements Specification

#### 2.1.1 Functional Requirements

| ID | Description | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-PAF-001 | Display activity feed on PropertyDetailPage | High | Feed renders within Overview tab with property-specific activities |
| FR-PAF-002 | Filter activities by property_id | High | Only activities related to current property are shown |
| FR-PAF-003 | Support activity types: view, edit, comment, status_change, document_upload | High | Each type has distinct icon and styling |
| FR-PAF-004 | Real-time updates via WebSocket | Medium | New activities appear within 500ms of creation |
| FR-PAF-005 | Display user avatar, timestamp, description | High | All three elements visible for each activity |
| FR-PAF-006 | Paginate activities (limit 20 per page) | Medium | "Load more" button or infinite scroll |
| FR-PAF-007 | Relative timestamps with tooltip for absolute | Low | "2 hours ago" with hover showing "Jan 14, 2026 10:30 AM" |

#### 2.1.2 Non-Functional Requirements

| ID | Category | Description | Measurement |
|----|----------|-------------|-------------|
| NFR-PAF-001 | Performance | Activity feed initial load < 200ms | p95 latency |
| NFR-PAF-002 | Performance | WebSocket activity push < 100ms render | Time from message to DOM update |
| NFR-PAF-003 | Accessibility | Screen reader announces new activities | NVDA/VoiceOver testing |

### 2.2 API Endpoint Specifications

#### 2.2.1 GET /api/v1/properties/{property_id}/activities

**Request:**
```http
GET /api/v1/properties/123/activities?page=1&page_size=20&activity_type=all HTTP/1.1
Authorization: Bearer <token>
```

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| page | int | No | 1 | Page number (1-indexed) |
| page_size | int | No | 20 | Items per page (max 100) |
| activity_type | string | No | "all" | Filter: all, view, edit, comment, status_change, document_upload |
| start_date | datetime | No | null | Filter activities after this date |
| end_date | datetime | No | null | Filter activities before this date |

**Response Schema (200 OK):**
```json
{
  "items": [
    {
      "id": "act_abc123",
      "property_id": 123,
      "activity_type": "edit",
      "description": "Updated occupancy rate from 94% to 96%",
      "user": {
        "id": 1,
        "name": "John Smith",
        "email": "john@brcapital.com",
        "avatar_url": "https://..."
      },
      "metadata": {
        "field": "occupancy_rate",
        "old_value": "94",
        "new_value": "96"
      },
      "created_at": "2026-01-14T10:30:00Z"
    }
  ],
  "total": 45,
  "page": 1,
  "page_size": 20,
  "has_next": true,
  "has_prev": false
}
```

**Backend Schema (Pydantic):**
```python
# backend/app/schemas/activity.py

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from .base import BaseSchema, PaginatedResponse


class ActivityType(str, Enum):
    VIEW = "view"
    EDIT = "edit"
    COMMENT = "comment"
    STATUS_CHANGE = "status_change"
    DOCUMENT_UPLOAD = "document_upload"


class ActivityUserResponse(BaseSchema):
    """User summary for activity display."""
    id: int
    name: str
    email: str
    avatar_url: str | None = None


class PropertyActivityResponse(BaseSchema):
    """Individual activity item."""
    id: str
    property_id: int
    activity_type: ActivityType
    description: str
    user: ActivityUserResponse
    metadata: dict[str, Any] | None = None
    created_at: datetime


class PropertyActivityListResponse(PaginatedResponse):
    """Paginated property activities."""
    items: list[PropertyActivityResponse]


class PropertyActivityCreate(BaseSchema):
    """Create a new property activity."""
    activity_type: ActivityType
    description: str
    metadata: dict[str, Any] | None = None
```

#### 2.2.2 POST /api/v1/properties/{property_id}/activities

**Request:**
```json
{
  "activity_type": "comment",
  "description": "Reviewed lease renewal terms with property manager",
  "metadata": {
    "lease_id": "lease_456"
  }
}
```

**Response (201 Created):**
```json
{
  "id": "act_def456",
  "property_id": 123,
  "activity_type": "comment",
  "description": "Reviewed lease renewal terms with property manager",
  "user": { ... },
  "metadata": { "lease_id": "lease_456" },
  "created_at": "2026-01-14T11:00:00Z"
}
```

#### 2.2.3 WebSocket Event: property_activity

**Message Format:**
```json
{
  "type": "property_activity",
  "action": "created",
  "property_id": 123,
  "data": {
    "id": "act_def456",
    "activity_type": "edit",
    "description": "Updated NOI to $1.2M",
    "user": { "id": 1, "name": "John Smith", "avatar_url": "..." },
    "created_at": "2026-01-14T11:00:00Z"
  },
  "timestamp": "2026-01-14T11:00:00.123Z"
}
```

### 2.3 Component Specifications

#### 2.3.1 PropertyActivityFeed Component

**File:** `src/features/property-detail/components/PropertyActivityFeed.tsx`

```typescript
// TypeScript Interface
interface PropertyActivityFeedProps {
  /** Property ID to fetch activities for */
  propertyId: string;

  /** Maximum number of activities to show initially */
  maxItems?: number;

  /** Show the add activity form */
  showAddForm?: boolean;

  /** Allow collapsing the feed */
  collapsible?: boolean;

  /** Custom className for styling */
  className?: string;

  /** Activity types to display (filters) */
  activityTypes?: ActivityType[];

  /** Enable real-time WebSocket updates */
  enableRealtime?: boolean;
}

type ActivityType = 'view' | 'edit' | 'comment' | 'status_change' | 'document_upload';

interface PropertyActivity {
  id: string;
  propertyId: string;
  activityType: ActivityType;
  description: string;
  user: {
    id: number;
    name: string;
    email: string;
    avatarUrl: string | null;
  };
  metadata: Record<string, unknown> | null;
  createdAt: Date;
}

interface PropertyActivityFeedResponse {
  activities: PropertyActivity[];
  total: number;
  hasNext: boolean;
}
```

**Behavior:**
1. Fetches activities on mount using `usePropertyActivities(propertyId)`
2. Subscribes to WebSocket room `property:{propertyId}` for real-time updates
3. Prepends new activities to the list with fade-in animation
4. Supports infinite scroll or "Load more" button for pagination
5. Displays skeleton loader during initial fetch

#### 2.3.2 ActivityItem Component

**File:** `src/features/property-detail/components/ActivityItem.tsx`

```typescript
interface ActivityItemProps {
  activity: PropertyActivity;
  /** Compact mode for sidebar display */
  compact?: boolean;
}
```

**Visual Design:**
- Avatar (32x32px, rounded)
- User name + relative timestamp
- Activity description
- Activity type icon badge
- Metadata expandable (if present)

### 2.4 User Stories

#### US-PAF-001: View Property Activity History
**As a** property manager
**I want to** see all recent activities on a property
**So that** I can track changes and stay informed

**Acceptance Criteria:**
- [ ] Activity feed is visible on PropertyDetailPage
- [ ] Activities show user avatar, name, timestamp, and description
- [ ] Activities are sorted by most recent first
- [ ] Can load more activities with pagination

#### US-PAF-002: Real-time Activity Updates
**As a** portfolio analyst
**I want to** see new activities appear automatically
**So that** I don't need to refresh the page

**Acceptance Criteria:**
- [ ] New activities appear within 1 second of creation
- [ ] New activities have subtle highlight animation
- [ ] Activity count updates in real-time

#### US-PAF-003: Filter Activities by Type
**As a** due diligence manager
**I want to** filter activities by type (edits, comments, documents)
**So that** I can focus on specific activity categories

**Acceptance Criteria:**
- [ ] Filter dropdown shows all activity types
- [ ] Multiple filters can be selected
- [ ] Filter state persists during session

---

## 3. Feature 2: Quick Actions

### 3.1 Requirements Specification

#### 3.1.1 Functional Requirements

| ID | Description | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-QA-001 | Deal card actions: Watchlist, Compare, Report | High | Three action buttons visible on deal card hover |
| FR-QA-002 | Property page actions: Share, Export PDF, Add Note | High | Action bar visible in property page header |
| FR-QA-003 | Dashboard actions: Quick Add Deal, Refresh Data | Medium | Action buttons in dashboard header |
| FR-QA-004 | Command palette (Cmd/Ctrl + K) | High | Opens searchable action menu |
| FR-QA-005 | Mobile FAB with expandable menu | High | Floating button with 4+ quick actions |
| FR-QA-006 | Keyboard shortcuts for common actions | Medium | Shortcuts work when no input is focused |

#### 3.1.2 Non-Functional Requirements

| ID | Category | Description | Measurement |
|----|----------|-------------|-------------|
| NFR-QA-001 | Performance | Command palette opens < 50ms | Time from keypress to render |
| NFR-QA-002 | Accessibility | All actions keyboard accessible | Tab navigation test |
| NFR-QA-003 | Mobile | FAB touch target >= 44x44px | Design spec compliance |

### 3.2 API Endpoint Specifications

#### 3.2.1 POST /api/v1/deals/{deal_id}/watchlist

**Request:**
```json
{
  "action": "add"  // or "remove"
}
```

**Response (200 OK):**
```json
{
  "deal_id": 123,
  "in_watchlist": true,
  "watchlist_added_at": "2026-01-14T12:00:00Z"
}
```

#### 3.2.2 POST /api/v1/exports/pdf

**Request:**
```json
{
  "type": "property",  // or "deal", "comparison"
  "id": "123",
  "options": {
    "include_charts": true,
    "include_financials": true,
    "include_photos": false
  }
}
```

**Response (202 Accepted):**
```json
{
  "export_id": "exp_abc123",
  "status": "processing",
  "estimated_completion": "2026-01-14T12:01:00Z"
}
```

**Response (via WebSocket when ready):**
```json
{
  "type": "export_ready",
  "export_id": "exp_abc123",
  "download_url": "https://...",
  "expires_at": "2026-01-14T13:00:00Z"
}
```

### 3.3 Component Specifications

#### 3.3.1 QuickActions Component

**File:** `src/components/QuickActions/QuickActions.tsx`

```typescript
interface QuickActionsProps {
  /** Context for action availability */
  context: QuickActionContext;

  /** Entity ID (deal, property, etc.) */
  entityId?: string;

  /** Entity type */
  entityType?: 'deal' | 'property' | 'portfolio';

  /** Display mode */
  variant?: 'inline' | 'dropdown' | 'fab';

  /** Custom className */
  className?: string;
}

type QuickActionContext =
  | 'deal_card'
  | 'deal_detail'
  | 'property_detail'
  | 'dashboard'
  | 'comparison';

interface QuickAction {
  id: string;
  label: string;
  icon: React.ComponentType;
  shortcut?: string;  // e.g., "Cmd+W" for watchlist
  action: () => void | Promise<void>;
  enabled?: boolean;
  loading?: boolean;
}
```

#### 3.3.2 CommandPalette Component

**File:** `src/components/CommandPalette/CommandPalette.tsx`

```typescript
interface CommandPaletteProps {
  /** Open state (controlled) */
  open: boolean;

  /** Callback when open state changes */
  onOpenChange: (open: boolean) => void;
}

interface Command {
  id: string;
  title: string;
  description?: string;
  icon?: React.ComponentType;
  shortcut?: string;
  keywords?: string[];  // For search
  action: () => void;
  category?: 'navigation' | 'actions' | 'search' | 'recent';
}
```

**Commands to Include:**
```typescript
const defaultCommands: Command[] = [
  // Navigation
  { id: 'nav-dashboard', title: 'Go to Dashboard', shortcut: 'G D', category: 'navigation' },
  { id: 'nav-deals', title: 'Go to Deals', shortcut: 'G L', category: 'navigation' },
  { id: 'nav-properties', title: 'Go to Investments', shortcut: 'G I', category: 'navigation' },

  // Actions
  { id: 'action-add-deal', title: 'Quick Add Deal', shortcut: 'C D', category: 'actions' },
  { id: 'action-refresh', title: 'Refresh Data', shortcut: 'R', category: 'actions' },
  { id: 'action-export', title: 'Export Current View', shortcut: 'E', category: 'actions' },
  { id: 'action-compare', title: 'Compare Deals', shortcut: 'Cmd+Shift+C', category: 'actions' },

  // Search
  { id: 'search-deals', title: 'Search Deals...', shortcut: '/', category: 'search' },
  { id: 'search-properties', title: 'Search Properties...', category: 'search' },
];
```

#### 3.3.3 FloatingActionButton Component

**File:** `src/components/QuickActions/FloatingActionButton.tsx`

```typescript
interface FloatingActionButtonProps {
  /** Actions to show in expanded menu */
  actions: QuickAction[];

  /** Position on screen */
  position?: 'bottom-right' | 'bottom-left' | 'bottom-center';

  /** Custom className */
  className?: string;
}
```

**Mobile Behavior:**
- Default: Collapsed single button with "+" icon
- Tap: Expands to show action buttons in arc pattern
- Outside tap: Collapses menu
- Swipe up on FAB: Opens command palette alternative

### 3.4 Keyboard Shortcuts

| Shortcut | Action | Context |
|----------|--------|---------|
| Cmd/Ctrl + K | Open command palette | Global |
| Cmd/Ctrl + Shift + C | Open comparison mode | Deals page |
| Cmd/Ctrl + W | Add/remove from watchlist | Deal card/detail |
| Cmd/Ctrl + E | Export current view | Any page |
| Cmd/Ctrl + N | Add note | Property/deal detail |
| G then D | Go to Dashboard | Global |
| G then L | Go to Deals (pipeline) | Global |
| G then I | Go to Investments | Global |
| / | Focus search | Global |
| Esc | Close modals/palette | Global |

### 3.5 User Stories

#### US-QA-001: Quick Watchlist Toggle
**As a** deal analyst
**I want to** quickly add deals to my watchlist from the card
**So that** I can track deals without opening the detail page

**Acceptance Criteria:**
- [ ] "Add to Watchlist" button visible on deal card hover
- [ ] Visual feedback (heart icon fills) when added
- [ ] Toast notification confirms action
- [ ] Keyboard shortcut Cmd+W works on focused card

#### US-QA-002: Command Palette Navigation
**As a** power user
**I want to** use keyboard shortcuts to navigate quickly
**So that** I can work efficiently without using the mouse

**Acceptance Criteria:**
- [ ] Cmd+K opens command palette
- [ ] Typing filters available commands
- [ ] Enter executes selected command
- [ ] Recent commands shown at top

#### US-QA-003: Mobile Quick Actions
**As a** mobile user
**I want to** access common actions via floating button
**So that** I can perform actions without navigating menus

**Acceptance Criteria:**
- [ ] FAB visible on mobile viewports
- [ ] Tap expands to show 4 action buttons
- [ ] Actions contextual to current page
- [ ] Haptic feedback on action tap

---

## 4. Feature 3: Deal Comparison

### 4.1 Requirements Specification

#### 4.1.1 Functional Requirements

| ID | Description | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-DC-001 | Compare 2-4 deals side-by-side | High | Selection UI limits to 4 deals |
| FR-DC-002 | Display key metrics: cap_rate, noi, price_per_sqft, irr, cash_on_cash | High | All metrics shown in comparison table |
| FR-DC-003 | Visual charts comparing metrics | High | Bar/radar charts for metric comparison |
| FR-DC-004 | Export comparison as PDF | Medium | PDF includes table and charts |
| FR-DC-005 | URL shareable comparison | High | /deals/compare?ids=1,2,3 works |
| FR-DC-006 | Highlight best/worst values | Low | Green for best, red for worst per metric |
| FR-DC-007 | Add/remove deals from comparison | High | UI to modify comparison set |

#### 4.1.2 Non-Functional Requirements

| ID | Category | Description | Measurement |
|----|----------|-------------|-------------|
| NFR-DC-001 | Performance | Comparison page loads < 500ms | Time to interactive |
| NFR-DC-002 | Accessibility | Charts have text alternatives | Screen reader audit |

### 4.2 API Endpoint Specifications

#### 4.2.1 GET /api/v1/deals/compare

**Request:**
```http
GET /api/v1/deals/compare?ids=1,2,3,4 HTTP/1.1
Authorization: Bearer <token>
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| ids | string | Yes | Comma-separated deal IDs (2-4) |

**Response Schema (200 OK):**
```json
{
  "deals": [
    {
      "id": 1,
      "name": "Phoenix Multifamily Portfolio",
      "property_name": "Sunrise Apartments",
      "property_type": "multifamily",
      "address": {
        "city": "Phoenix",
        "state": "AZ"
      },
      "metrics": {
        "asking_price": 15000000,
        "cap_rate": 5.5,
        "noi": 825000,
        "price_per_unit": 187500,
        "price_per_sqft": 215,
        "projected_irr": 18.5,
        "cash_on_cash": 8.2,
        "equity_multiple": 2.1,
        "total_units": 80,
        "total_sf": 69767,
        "year_built": 2015,
        "occupancy_rate": 95.5
      },
      "stage": "underwriting",
      "priority": "high"
    }
    // ... more deals
  ],
  "comparison_summary": {
    "best_cap_rate": { "deal_id": 2, "value": 6.1 },
    "best_irr": { "deal_id": 1, "value": 18.5 },
    "lowest_price_per_unit": { "deal_id": 3, "value": 165000 },
    "highest_noi": { "deal_id": 1, "value": 825000 }
  },
  "generated_at": "2026-01-14T12:00:00Z"
}
```

**Backend Schema (Pydantic):**
```python
# backend/app/schemas/comparison.py

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import Field

from .base import BaseSchema


class DealMetricsForComparison(BaseSchema):
    """Metrics subset for deal comparison."""
    asking_price: Decimal | None = None
    cap_rate: Decimal | None = None
    noi: Decimal | None = None
    price_per_unit: Decimal | None = None
    price_per_sqft: Decimal | None = None
    projected_irr: Decimal | None = None
    cash_on_cash: Decimal | None = None
    equity_multiple: Decimal | None = None
    total_units: int | None = None
    total_sf: int | None = None
    year_built: int | None = None
    occupancy_rate: Decimal | None = None


class DealAddressForComparison(BaseSchema):
    """Address subset for comparison display."""
    city: str
    state: str


class DealForComparison(BaseSchema):
    """Deal data optimized for comparison view."""
    id: int
    name: str
    property_name: str | None = None
    property_type: str
    address: DealAddressForComparison
    metrics: DealMetricsForComparison
    stage: str
    priority: str


class ComparisonBestValue(BaseSchema):
    """Best value indicator for a metric."""
    deal_id: int
    value: Decimal


class ComparisonSummary(BaseSchema):
    """Summary of best values across compared deals."""
    best_cap_rate: ComparisonBestValue | None = None
    best_irr: ComparisonBestValue | None = None
    lowest_price_per_unit: ComparisonBestValue | None = None
    highest_noi: ComparisonBestValue | None = None


class DealComparisonResponse(BaseSchema):
    """Full comparison response."""
    deals: list[DealForComparison]
    comparison_summary: ComparisonSummary
    generated_at: datetime


class DealComparisonRequest(BaseSchema):
    """Request for deal comparison - validates ID count."""
    ids: list[int] = Field(..., min_length=2, max_length=4)
```

### 4.3 Component Specifications

#### 4.3.1 DealComparisonPage Component

**File:** `src/features/deals/DealComparisonPage.tsx`

```typescript
interface DealComparisonPageProps {
  /** Initial deal IDs from URL params */
  initialDealIds?: string[];
}

// URL: /deals/compare?ids=1,2,3
```

#### 4.3.2 ComparisonTable Component

**File:** `src/features/deals/components/ComparisonTable.tsx`

```typescript
interface ComparisonTableProps {
  /** Deals to compare */
  deals: DealForComparison[];

  /** Metrics to display */
  metrics?: ComparisonMetric[];

  /** Highlight best/worst values */
  highlightBestWorst?: boolean;

  /** Custom className */
  className?: string;
}

type ComparisonMetric =
  | 'asking_price'
  | 'cap_rate'
  | 'noi'
  | 'price_per_unit'
  | 'price_per_sqft'
  | 'projected_irr'
  | 'cash_on_cash'
  | 'equity_multiple'
  | 'total_units'
  | 'total_sf'
  | 'occupancy_rate';

interface MetricConfig {
  key: ComparisonMetric;
  label: string;
  format: 'currency' | 'percent' | 'number' | 'sqft';
  higherIsBetter: boolean;  // For highlighting
}

const DEFAULT_METRICS: MetricConfig[] = [
  { key: 'asking_price', label: 'Asking Price', format: 'currency', higherIsBetter: false },
  { key: 'cap_rate', label: 'Cap Rate', format: 'percent', higherIsBetter: true },
  { key: 'noi', label: 'NOI', format: 'currency', higherIsBetter: true },
  { key: 'price_per_unit', label: 'Price/Unit', format: 'currency', higherIsBetter: false },
  { key: 'price_per_sqft', label: 'Price/SF', format: 'currency', higherIsBetter: false },
  { key: 'projected_irr', label: 'Projected IRR', format: 'percent', higherIsBetter: true },
  { key: 'cash_on_cash', label: 'Cash-on-Cash', format: 'percent', higherIsBetter: true },
  { key: 'equity_multiple', label: 'Equity Multiple', format: 'number', higherIsBetter: true },
  { key: 'total_units', label: 'Total Units', format: 'number', higherIsBetter: false },
  { key: 'total_sf', label: 'Total SF', format: 'sqft', higherIsBetter: false },
  { key: 'occupancy_rate', label: 'Occupancy', format: 'percent', higherIsBetter: true },
];
```

#### 4.3.3 ComparisonCharts Component

**File:** `src/features/deals/components/ComparisonCharts.tsx`

```typescript
interface ComparisonChartsProps {
  /** Deals to chart */
  deals: DealForComparison[];

  /** Chart type to display */
  chartType?: 'bar' | 'radar' | 'both';

  /** Custom className */
  className?: string;
}
```

**Chart Configurations:**
1. **Bar Chart**: Side-by-side bars for each metric, color-coded by deal
2. **Radar Chart**: Multi-axis comparison showing deal profiles
3. **Financial Summary**: Grouped bars for price, NOI, returns

#### 4.3.4 DealSelector Component

**File:** `src/features/deals/components/DealSelector.tsx`

```typescript
interface DealSelectorProps {
  /** Currently selected deal IDs */
  selectedIds: string[];

  /** Callback when selection changes */
  onSelectionChange: (ids: string[]) => void;

  /** Maximum deals that can be selected */
  maxSelection?: number;  // default: 4

  /** Deals available for selection */
  availableDeals: Deal[];
}
```

### 4.4 React Query Hook

**File:** `src/hooks/api/useDeals.ts` (additions)

```typescript
// Query key
export const dealKeys = {
  // ... existing keys
  comparison: (ids: string[]) => [...dealKeys.all, 'comparison', ids.sort().join(',')] as const,
};

// Hook
export function useDealComparison(
  dealIds: string[],
  options?: Omit<UseQueryOptions<DealComparisonResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: dealKeys.comparison(dealIds),
    queryFn: () => get<DealComparisonResponse>(
      '/deals/compare',
      { ids: dealIds.join(',') }
    ),
    enabled: dealIds.length >= 2 && dealIds.length <= 4,
    staleTime: 1000 * 60 * 5, // 5 minutes
    ...options,
  });
}

// Mock fallback version
export function useDealComparisonWithMockFallback(dealIds: string[]) {
  return useQuery({
    queryKey: dealKeys.comparison(dealIds),
    queryFn: async (): Promise<DealComparisonResponse> => {
      if (USE_MOCK_DATA || dealIds.length < 2) {
        return buildMockComparison(dealIds);
      }

      try {
        return await get<DealComparisonResponse>(
          '/deals/compare',
          { ids: dealIds.join(',') }
        );
      } catch (error) {
        if (IS_DEV) {
          console.warn('API unavailable, falling back to mock comparison:', error);
          return buildMockComparison(dealIds);
        }
        throw error;
      }
    },
    enabled: dealIds.length >= 2 && dealIds.length <= 4,
  });
}
```

### 4.5 User Stories

#### US-DC-001: Compare Deals from Pipeline
**As a** portfolio manager
**I want to** compare multiple deals side-by-side
**So that** I can make informed investment decisions

**Acceptance Criteria:**
- [ ] Can select 2-4 deals for comparison
- [ ] Comparison table shows all key metrics
- [ ] Best values are highlighted in green
- [ ] Can add/remove deals from comparison

#### US-DC-002: Share Comparison Link
**As a** investment committee member
**I want to** share a comparison URL with colleagues
**So that** we can review the same comparison

**Acceptance Criteria:**
- [ ] URL format: /deals/compare?ids=1,2,3
- [ ] URL loads comparison directly
- [ ] Invalid IDs show appropriate error
- [ ] URL is copyable via share button

#### US-DC-003: Export Comparison PDF
**As a** deal analyst
**I want to** export the comparison as a PDF
**So that** I can include it in presentations

**Acceptance Criteria:**
- [ ] Export button visible on comparison page
- [ ] PDF includes table and charts
- [ ] PDF has professional formatting
- [ ] Download starts automatically when ready

#### US-DC-004: Visual Metric Comparison
**As a** investment analyst
**I want to** see charts comparing deal metrics
**So that** I can quickly visualize differences

**Acceptance Criteria:**
- [ ] Bar chart shows metric values side-by-side
- [ ] Radar chart shows overall deal profile
- [ ] Charts are responsive on mobile
- [ ] Charts have accessible color palette

---

## 5. Data Flow Diagrams

### 5.1 Property Activity Feed Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PROPERTY ACTIVITY FEED                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────┐     ┌──────────────┐     ┌──────────────┐     ┌───────────┐ │
│  │ Property  │     │   useProperty │     │   FastAPI    │     │ PostgreSQL│ │
│  │ Detail    │────▶│   Activities │────▶│   Endpoint   │────▶│  Activity │ │
│  │ Page      │     │   Hook       │     │   /activities│     │  Table    │ │
│  └───────────┘     └──────────────┘     └──────────────┘     └───────────┘ │
│        │                  │                    │                    │       │
│        │                  │                    │                    │       │
│        ▼                  ▼                    ▼                    ▼       │
│  ┌───────────┐     ┌──────────────┐     ┌──────────────┐     ┌───────────┐ │
│  │ Activity  │◀────│ React Query  │◀────│   JSON       │◀────│   SELECT  │ │
│  │ Feed      │     │ Cache        │     │   Response   │     │   Query   │ │
│  │ Component │     │              │     │              │     │           │ │
│  └───────────┘     └──────────────┘     └──────────────┘     └───────────┘ │
│        │                                                                    │
│        │  Real-time Updates                                                 │
│        ▼                                                                    │
│  ┌───────────┐     ┌──────────────┐     ┌──────────────┐                   │
│  │ WebSocket │◀────│ WS Manager   │◀────│ Activity     │                   │
│  │ Client    │     │ (singleton)  │     │ Created Hook │                   │
│  └───────────┘     └──────────────┘     └──────────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Quick Actions Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          QUICK ACTIONS SYSTEM                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  User Input                                                                 │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐ │
│  │ Keyboard    │   │ Button      │   │ FAB Tap     │   │ Command Palette │ │
│  │ Shortcut    │   │ Click       │   │ (Mobile)    │   │ Selection       │ │
│  │ (Cmd+K)     │   │             │   │             │   │                 │ │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └────────┬────────┘ │
│         │                 │                 │                    │          │
│         └─────────────────┼─────────────────┼────────────────────┘          │
│                           ▼                                                 │
│                    ┌──────────────┐                                         │
│                    │ QuickActions │                                         │
│                    │ Context      │                                         │
│                    │ Provider     │                                         │
│                    └──────┬───────┘                                         │
│                           │                                                 │
│         ┌─────────────────┼─────────────────┐                               │
│         ▼                 ▼                 ▼                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                      │
│  │ Navigation   │  │ API Action   │  │ Local Action │                      │
│  │ (router.push)│  │ (mutation)   │  │ (state)      │                      │
│  └──────────────┘  └──────────────┘  └──────────────┘                      │
│                           │                                                 │
│                           ▼                                                 │
│                    ┌──────────────┐                                         │
│                    │ Toast        │                                         │
│                    │ Notification │                                         │
│                    └──────────────┘                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Deal Comparison Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DEAL COMPARISON FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Entry Points                                                               │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────────────────────┐ │
│  │ Deal Card     │   │ Kanban Board  │   │ URL: /deals/compare?ids=1,2,3 │ │
│  │ "Compare" btn │   │ Multi-select  │   │ (Direct link / shared)        │ │
│  └───────┬───────┘   └───────┬───────┘   └─────────────┬─────────────────┘ │
│          │                   │                         │                    │
│          └───────────────────┼─────────────────────────┘                    │
│                              ▼                                              │
│                    ┌──────────────────┐                                     │
│                    │ ComparisonContext │                                    │
│                    │ selectedDealIds[] │                                    │
│                    └─────────┬────────┘                                     │
│                              │                                              │
│                              ▼                                              │
│                    ┌──────────────────┐     ┌─────────────────────────────┐│
│                    │useDealComparison │────▶│ GET /api/v1/deals/compare   ││
│                    │     Hook         │     │ ?ids=1,2,3                  ││
│                    └─────────┬────────┘     └─────────────────────────────┘│
│                              │                                              │
│          ┌───────────────────┼───────────────────┐                         │
│          ▼                   ▼                   ▼                         │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐                 │
│  │ Comparison    │   │ Comparison    │   │ Deal Selector │                 │
│  │ Table         │   │ Charts        │   │ (modify set)  │                 │
│  │               │   │ (Recharts)    │   │               │                 │
│  └───────────────┘   └───────────────┘   └───────────────┘                 │
│          │                   │                                              │
│          └───────────────────┘                                              │
│                              │                                              │
│                              ▼                                              │
│                    ┌──────────────────┐                                     │
│                    │ Export PDF       │                                     │
│                    │ POST /exports/pdf│                                     │
│                    └─────────┬────────┘                                     │
│                              │                                              │
│                              ▼                                              │
│                    ┌──────────────────┐                                     │
│                    │ WebSocket:       │                                     │
│                    │ export_ready     │                                     │
│                    └──────────────────┘                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Validation Checklist

### 6.1 Specification Completeness

- [x] All requirements are testable
- [x] Acceptance criteria are clear and measurable
- [x] Edge cases documented (empty states, error states, limits)
- [x] Performance metrics defined with targets
- [x] Security requirements specified (authentication on all endpoints)
- [x] Dependencies identified (cmdk for command palette)
- [x] Constraints documented (mobile FAB size, WebSocket integration)
- [x] API schemas include request/response examples

### 6.2 Architecture Readiness

- [x] Component interfaces defined (TypeScript)
- [x] API endpoints specified with schemas
- [x] Data flow diagrams provided
- [x] State management approach documented (React Query + Context)
- [x] WebSocket integration points identified
- [x] Mock data fallback patterns defined

### 6.3 Implementation Readiness

- [x] File paths specified for all new components
- [x] Existing patterns referenced (ActivityFeed, useDeals hooks)
- [x] UI/UX specifications (touch targets, animations, responsive)
- [x] Keyboard shortcuts documented
- [x] Mobile-specific behaviors defined

---

## Appendix A: File Structure

```
src/
├── components/
│   ├── CommandPalette/
│   │   ├── CommandPalette.tsx
│   │   ├── CommandItem.tsx
│   │   └── index.ts
│   └── QuickActions/
│       ├── QuickActions.tsx
│       ├── FloatingActionButton.tsx
│       ├── QuickActionButton.tsx
│       └── index.ts
├── features/
│   ├── property-detail/
│   │   └── components/
│   │       ├── PropertyActivityFeed.tsx
│   │       ├── PropertyActivityItem.tsx
│   │       └── PropertyActivityForm.tsx
│   └── deals/
│       ├── DealComparisonPage.tsx
│       └── components/
│           ├── ComparisonTable.tsx
│           ├── ComparisonCharts.tsx
│           ├── DealSelector.tsx
│           └── ComparisonExport.tsx
├── hooks/
│   └── api/
│       └── usePropertyActivities.ts  (new hook)
└── contexts/
    ├── ComparisonContext.tsx
    └── QuickActionsContext.tsx

backend/app/
├── api/v1/endpoints/
│   └── activities.py  (new)
├── schemas/
│   ├── activity.py  (new)
│   └── comparison.py  (new)
├── crud/
│   └── activity.py  (new)
└── models/
    └── activity.py  (new)
```

## Appendix B: Dependencies to Add

```json
// package.json additions
{
  "dependencies": {
    "cmdk": "^1.0.0"  // Command palette
  }
}
```

---

**Document Status:** Ready for Architecture Agent Review

**Next Steps:**
1. Architecture Agent: Review and create system design
2. Coder Agent: Implement features following this spec
3. Tester Agent: Write tests based on acceptance criteria
