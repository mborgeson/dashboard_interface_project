# Wave 10 Performance Optimization Architecture

## Overview

This document specifies the architecture for Wave 10 frontend performance optimizations, designed to integrate seamlessly with the existing codebase patterns and technology stack.

### Current Stack Context
- **React 19.2** with React Router DOM 6.30
- **Tanstack React Query 5** for data fetching
- **Tailwind CSS 3.4** with cn() utility (clsx + tailwind-merge)
- **TypeScript 5.9** with strict mode
- **Zustand 5** for global state
- **Radix UI** for accessible primitives

---

## 1. LazyImage Component

### Purpose
IntersectionObserver-based image lazy loading to reduce initial page load time and network bandwidth by deferring off-screen image loading.

### Component Interface

```typescript
// File: src/components/ui/lazy-image.tsx

import * as React from 'react';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';

export interface LazyImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  /** Image source URL */
  src: string;
  /** Alt text for accessibility */
  alt: string;
  /** Optional placeholder to show while loading */
  placeholder?: 'skeleton' | 'blur' | 'none';
  /** Blur data URL for blur-up effect */
  blurDataURL?: string;
  /** Root margin for IntersectionObserver (default: '100px') */
  rootMargin?: string;
  /** Threshold for IntersectionObserver (default: 0) */
  threshold?: number;
  /** Aspect ratio for container (e.g., '16/9', '4/3', '1/1') */
  aspectRatio?: string;
  /** Callback when image enters viewport */
  onInView?: () => void;
  /** Callback when image finishes loading */
  onImageLoad?: () => void;
  /** Callback on load error */
  onImageError?: (error: Error) => void;
  /** Fallback image URL on error */
  fallbackSrc?: string;
}

export interface LazyImageState {
  isInView: boolean;
  isLoaded: boolean;
  hasError: boolean;
}
```

### Implementation Architecture

```
LazyImage
├── useIntersectionObserver (custom hook)
│   ├── IntersectionObserver API
│   ├── ref management
│   └── cleanup on unmount
├── Loading States
│   ├── skeleton (Skeleton component)
│   ├── blur (CSS filter + blurDataURL)
│   └── none (no placeholder)
├── Image Loading
│   ├── native loading="lazy" fallback
│   ├── decode() for smooth rendering
│   └── error handling with fallback
└── Accessibility
    ├── alt text required
    ├── loading state announcement
    └── proper focus handling
```

### useIntersectionObserver Hook

```typescript
// File: src/hooks/useIntersectionObserver.ts

export interface UseIntersectionObserverOptions {
  /** Root element for intersection (default: viewport) */
  root?: Element | null;
  /** Margin around root */
  rootMargin?: string;
  /** Visibility threshold(s) */
  threshold?: number | number[];
  /** Only trigger once */
  triggerOnce?: boolean;
  /** Initial inView state */
  initialInView?: boolean;
  /** Skip observation */
  skip?: boolean;
}

export interface UseIntersectionObserverReturn {
  /** Ref to attach to observed element */
  ref: React.RefCallback<Element>;
  /** Whether element is in viewport */
  inView: boolean;
  /** Full IntersectionObserverEntry */
  entry: IntersectionObserverEntry | undefined;
}

export function useIntersectionObserver(
  options?: UseIntersectionObserverOptions
): UseIntersectionObserverReturn;
```

### Integration Points

1. **PropertyCardSkeleton** - Replace static image placeholder with LazyImage
2. **DealCard** - If images are added, use LazyImage
3. **DocumentCard** - Thumbnails for document previews
4. **PropertyMap** - Map marker images
5. **Gallery components** - Any image gallery features

### Performance Considerations

- **Root Margin**: Default `100px` to preload slightly before entering viewport
- **Native Fallback**: Use `loading="lazy"` for browsers without IO support
- **Image Decoding**: Use `img.decode()` to prevent jank during render
- **Memory**: Disconnect observer after image loads (triggerOnce)

---

## 2. Route Prefetching Hook (usePrefetch)

### Purpose
Prefetch route data on link hover to improve navigation performance, building on the existing `usePrefetchDashboard` pattern.

### Hook Interface

```typescript
// File: src/hooks/usePrefetch.ts

import { useQueryClient } from '@tanstack/react-query';

export interface PrefetchConfig {
  /** Query key to prefetch */
  queryKey: readonly unknown[];
  /** Query function to execute */
  queryFn: () => Promise<unknown>;
  /** Stale time for prefetched data */
  staleTime?: number;
  /** Cache time for prefetched data */
  gcTime?: number;
}

export interface UsePrefetchOptions {
  /** Delay before prefetching starts (ms) */
  delay?: number;
  /** Whether to prefetch on hover */
  prefetchOnHover?: boolean;
  /** Whether to prefetch on focus */
  prefetchOnFocus?: boolean;
  /** Whether to prefetch on touch start (mobile) */
  prefetchOnTouch?: boolean;
  /** Custom prefetch configs for the route */
  configs?: PrefetchConfig[];
}

export interface UsePrefetchReturn {
  /** Props to spread on link element */
  prefetchProps: {
    onMouseEnter: () => void;
    onFocus: () => void;
    onTouchStart: () => void;
  };
  /** Manually trigger prefetch */
  prefetch: () => void;
  /** Whether prefetch is in progress */
  isPrefetching: boolean;
}

export function usePrefetch(
  route: string,
  options?: UsePrefetchOptions
): UsePrefetchReturn;
```

### Route Prefetch Registry

```typescript
// File: src/lib/prefetch-registry.ts

import { propertyKeys } from '@/hooks/api/useProperties';
import { marketDataKeys } from '@/hooks/api/useMarketData';
import { interestRateKeys } from '@/hooks/api/useInterestRates';
import { reportingKeys } from '@/hooks/api/useReporting';

export interface RoutePrefetchConfig {
  queryKey: readonly unknown[];
  queryFn: () => Promise<unknown>;
  staleTime: number;
}

/**
 * Registry of prefetch configurations per route
 * Maps route paths to arrays of query configs to prefetch
 */
export const routePrefetchRegistry: Record<string, RoutePrefetchConfig[]> = {
  '/': [
    { queryKey: propertyKeys.lists(), queryFn: fetchProperties, staleTime: 5 * 60 * 1000 },
    { queryKey: marketDataKeys.overview(), queryFn: fetchMarketOverview, staleTime: 15 * 60 * 1000 },
  ],
  '/investments': [
    { queryKey: propertyKeys.lists(), queryFn: fetchProperties, staleTime: 5 * 60 * 1000 },
  ],
  '/deals': [
    { queryKey: ['deals', 'list'], queryFn: fetchDeals, staleTime: 2 * 60 * 1000 },
  ],
  '/market': [
    { queryKey: marketDataKeys.overview(), queryFn: fetchMarketOverview, staleTime: 15 * 60 * 1000 },
    { queryKey: marketDataKeys.submarkets(), queryFn: fetchSubmarkets, staleTime: 15 * 60 * 1000 },
  ],
  '/interest-rates': [
    { queryKey: interestRateKeys.current(), queryFn: fetchRates, staleTime: 10 * 60 * 1000 },
  ],
  '/reporting': [
    { queryKey: reportingKeys.templateList({}), queryFn: fetchTemplates, staleTime: 10 * 60 * 1000 },
  ],
};
```

### PrefetchLink Component

```typescript
// File: src/components/ui/prefetch-link.tsx

import { NavLink, NavLinkProps } from 'react-router-dom';
import { usePrefetch } from '@/hooks/usePrefetch';

export interface PrefetchLinkProps extends NavLinkProps {
  /** Delay before prefetching (default: 100ms) */
  prefetchDelay?: number;
  /** Disable prefetching */
  noPrefetch?: boolean;
}

export function PrefetchLink({
  to,
  prefetchDelay = 100,
  noPrefetch = false,
  children,
  ...props
}: PrefetchLinkProps): JSX.Element;
```

### Integration Points

1. **Sidebar.tsx** - Replace NavLink with PrefetchLink for navigation items
2. **DashboardMain.tsx** - Prefetch property details on card hover
3. **DealsPage.tsx** - Prefetch deal comparison on deal card hover
4. **Breadcrumbs** - Prefetch parent routes

---

## 3. Virtual List Component

### Purpose
Efficiently render large lists of properties/deals by only rendering visible items, critical for scaling beyond current dataset sizes.

### Component Interface

```typescript
// File: src/components/ui/virtual-list.tsx

import * as React from 'react';

export interface VirtualListProps<T> {
  /** Array of items to render */
  items: T[];
  /** Height of each item in pixels (or function for variable heights) */
  itemHeight: number | ((item: T, index: number) => number);
  /** Total height of the container */
  height: number;
  /** Width of the container */
  width?: number | string;
  /** Number of items to render outside visible area (default: 3) */
  overscan?: number;
  /** Render function for each item */
  renderItem: (item: T, index: number, style: React.CSSProperties) => React.ReactNode;
  /** Optional key extractor (default: index) */
  keyExtractor?: (item: T, index: number) => string | number;
  /** Container className */
  className?: string;
  /** Callback when scroll position changes */
  onScroll?: (scrollTop: number) => void;
  /** Initial scroll offset */
  initialScrollOffset?: number;
  /** Gap between items */
  gap?: number;
  /** Empty state component */
  emptyState?: React.ReactNode;
  /** Loading state */
  isLoading?: boolean;
  /** Loading skeleton count */
  loadingSkeletonCount?: number;
  /** Loading skeleton component */
  loadingSkeleton?: React.ReactNode;
}

export interface VirtualListRef {
  /** Scroll to specific item index */
  scrollToIndex: (index: number, align?: 'start' | 'center' | 'end') => void;
  /** Scroll to specific offset */
  scrollTo: (offset: number) => void;
  /** Get current scroll offset */
  getScrollOffset: () => number;
}

export const VirtualList: <T>(
  props: VirtualListProps<T> & { ref?: React.Ref<VirtualListRef> }
) => React.ReactElement;
```

### Virtual Grid Component

```typescript
// File: src/components/ui/virtual-grid.tsx

export interface VirtualGridProps<T> {
  /** Array of items to render */
  items: T[];
  /** Number of columns */
  columns: number | 'auto';
  /** Width of each column (for auto columns) */
  columnWidth?: number;
  /** Height of each row */
  rowHeight: number;
  /** Total height of the container */
  height: number;
  /** Total width of the container */
  width?: number | string;
  /** Gap between items */
  gap?: number;
  /** Number of rows to render outside visible area */
  overscan?: number;
  /** Render function for each item */
  renderItem: (item: T, index: number, style: React.CSSProperties) => React.ReactNode;
  /** Key extractor */
  keyExtractor?: (item: T, index: number) => string | number;
  /** Container className */
  className?: string;
  /** Empty state */
  emptyState?: React.ReactNode;
  /** Loading state */
  isLoading?: boolean;
  /** Loading skeleton */
  loadingSkeleton?: React.ReactNode;
}

export const VirtualGrid: <T>(
  props: VirtualGridProps<T> & { ref?: React.Ref<VirtualListRef> }
) => React.ReactElement;
```

### useVirtualList Hook

```typescript
// File: src/hooks/useVirtualList.ts

export interface UseVirtualListOptions<T> {
  /** Total item count */
  itemCount: number;
  /** Item height (fixed or function) */
  itemHeight: number | ((index: number) => number);
  /** Container height */
  containerHeight: number;
  /** Overscan count */
  overscan?: number;
  /** Gap between items */
  gap?: number;
}

export interface UseVirtualListReturn {
  /** Virtual items to render */
  virtualItems: Array<{
    index: number;
    start: number;
    size: number;
    key: string | number;
  }>;
  /** Total scrollable height */
  totalHeight: number;
  /** Current scroll offset */
  scrollOffset: number;
  /** Scroll handler for container */
  handleScroll: (event: React.UIEvent<HTMLElement>) => void;
  /** Scroll to index */
  scrollToIndex: (index: number, align?: 'start' | 'center' | 'end') => void;
  /** Range of visible indices */
  visibleRange: { start: number; end: number };
}

export function useVirtualList<T>(
  options: UseVirtualListOptions<T>
): UseVirtualListReturn;
```

### Integration Points

1. **DealPipeline.tsx** - Virtualize deal cards in each stage column
2. **TransactionTable.tsx** - Virtualize table rows
3. **DocumentList.tsx** - Virtualize document items
4. **PropertyCardSkeletonGrid** - Use VirtualGrid for property cards
5. **KanbanColumn.tsx** - Virtualize cards within columns

### Performance Thresholds

| List Size | Strategy |
|-----------|----------|
| < 50 items | Standard rendering |
| 50-200 items | Consider virtual list |
| > 200 items | Always use virtual list |

---

## 4. Memoization Strategy

### Purpose
Prevent unnecessary re-renders through strategic use of React.memo, useMemo, and useCallback.

### Memoization Decision Matrix

```
Should Memoize?
├── Does component re-render often with same props? → YES
├── Is prop comparison expensive? → Consider custom comparator
├── Does component render many children? → YES
├── Is component in a list rendered by map()? → YES
├── Does component use context that changes often? → Consider memo
└── Is component simple/cheap to render? → NO (memo overhead)
```

### Components Requiring React.memo

```typescript
// HIGH PRIORITY - Rendered in lists
// File: src/components/memoized/index.ts

export { MemoizedDealCard } from './MemoizedDealCard';
export { MemoizedPropertyCard } from './MemoizedPropertyCard';
export { MemoizedTransactionRow } from './MemoizedTransactionRow';
export { MemoizedDocumentCard } from './MemoizedDocumentCard';
export { MemoizedKPICard } from './MemoizedKPICard';
export { MemoizedStatCard } from './MemoizedStatCard';
```

### Memoization Patterns by Component Type

#### 1. Card Components (DealCard, PropertyCard)

```typescript
// src/features/deals/components/DealCard.tsx

import { memo, useMemo, useCallback } from 'react';
import type { Deal } from '@/types/deal';

interface DealCardProps {
  deal: Deal;
  isDragging?: boolean;
  compact?: boolean;
  onClick?: (dealId: string) => void;
}

// Custom comparison for Deal object
function dealCardPropsAreEqual(
  prevProps: DealCardProps,
  nextProps: DealCardProps
): boolean {
  return (
    prevProps.deal.id === nextProps.deal.id &&
    prevProps.deal.stage === nextProps.deal.stage &&
    prevProps.deal.value === nextProps.deal.value &&
    prevProps.deal.daysInStage === nextProps.deal.daysInStage &&
    prevProps.isDragging === nextProps.isDragging &&
    prevProps.compact === nextProps.compact &&
    prevProps.onClick === nextProps.onClick
  );
}

export const DealCard = memo(function DealCard({
  deal,
  isDragging,
  compact,
  onClick
}: DealCardProps) {
  // Memoize expensive calculations
  const progressPercentage = useMemo(() => {
    const stages: Deal['stage'][] = ['lead', 'underwriting', 'loi', 'due_diligence', 'closing'];
    const currentIndex = stages.indexOf(deal.stage);
    if (currentIndex === -1) return 100;
    return ((currentIndex + 1) / stages.length) * 100;
  }, [deal.stage]);

  // Memoize callbacks
  const handleClick = useCallback(() => {
    onClick?.(deal.id);
  }, [onClick, deal.id]);

  // ... render
}, dealCardPropsAreEqual);
```

#### 2. Table Row Components

```typescript
// src/features/transactions/components/TransactionRow.tsx

import { memo } from 'react';
import type { Transaction } from '@/types/transaction';

interface TransactionRowProps {
  transaction: Transaction;
  onSelect?: (id: string) => void;
  isSelected?: boolean;
}

export const TransactionRow = memo(function TransactionRow({
  transaction,
  onSelect,
  isSelected
}: TransactionRowProps) {
  // ... render
});
```

#### 3. Chart Components

```typescript
// src/features/dashboard-main/components/PortfolioPerformanceChart.tsx

import { memo, useMemo } from 'react';
import type { Property } from '@/types/property';

interface PortfolioPerformanceChartProps {
  properties: Property[];
}

export const PortfolioPerformanceChart = memo(function PortfolioPerformanceChart({
  properties
}: PortfolioPerformanceChartProps) {
  // Memoize chart data transformation
  const chartData = useMemo(() => {
    return transformPropertiesToChartData(properties);
  }, [properties]);

  // ... render Recharts component
});
```

### useMemo Usage Guidelines

```typescript
// GOOD: Expensive computation
const sortedDeals = useMemo(() => {
  return [...deals].sort((a, b) => b.value - a.value);
}, [deals]);

// GOOD: Object creation preventing child re-renders
const filterOptions = useMemo(() => ({
  propertyTypes: extractPropertyTypes(deals),
  assignees: extractAssignees(deals),
}), [deals]);

// BAD: Simple value
const count = useMemo(() => items.length, [items]); // Just use items.length

// BAD: Primitive transformation
const formatted = useMemo(() => value.toFixed(2), [value]); // Cheap operation
```

### useCallback Usage Guidelines

```typescript
// GOOD: Handler passed to memoized children
const handleDealClick = useCallback((dealId: string) => {
  setSelectedDealId(dealId);
}, []);

// GOOD: Handler in dependency array
const fetchData = useCallback(async () => {
  const data = await api.get('/deals');
  setDeals(data);
}, []);

// BAD: Handler not passed to children or used in deps
const handleClick = useCallback(() => {
  console.log('clicked');
}, []); // Unnecessary, just use regular function
```

### Context Optimization

```typescript
// File: src/store/contexts/DealContext.tsx

import { createContext, useContext, useMemo, type ReactNode } from 'react';

interface DealContextValue {
  selectedDealId: string | null;
  setSelectedDealId: (id: string | null) => void;
}

const DealContext = createContext<DealContextValue | null>(null);

export function DealProvider({ children }: { children: ReactNode }) {
  const [selectedDealId, setSelectedDealId] = useState<string | null>(null);

  // Memoize context value to prevent re-renders
  const value = useMemo(() => ({
    selectedDealId,
    setSelectedDealId,
  }), [selectedDealId]);

  return (
    <DealContext.Provider value={value}>
      {children}
    </DealContext.Provider>
  );
}

// Split contexts for different update frequencies
// Separate "data" context from "actions" context
```

---

## Integration Architecture

### File Structure

```
src/
├── components/
│   ├── ui/
│   │   ├── lazy-image.tsx          # LazyImage component
│   │   ├── prefetch-link.tsx       # PrefetchLink component
│   │   ├── virtual-list.tsx        # VirtualList component
│   │   └── virtual-grid.tsx        # VirtualGrid component
│   └── memoized/
│       ├── index.ts                # Memoized component exports
│       ├── MemoizedDealCard.tsx
│       ├── MemoizedPropertyCard.tsx
│       └── ...
├── hooks/
│   ├── useIntersectionObserver.ts  # IO hook for LazyImage
│   ├── usePrefetch.ts              # Route prefetching hook
│   ├── useVirtualList.ts           # Virtual list logic hook
│   └── index.ts                    # Updated exports
└── lib/
    └── prefetch-registry.ts        # Route prefetch configurations
```

### Export Updates

```typescript
// File: src/hooks/index.ts

export { useGlobalSearch } from './useGlobalSearch';
export { useFilterPersistence } from './useFilterPersistence';
export { usePrefetchDashboard } from './usePrefetchDashboard';
export { useIntersectionObserver } from './useIntersectionObserver';
export { usePrefetch } from './usePrefetch';
export { useVirtualList } from './useVirtualList';

// File: src/components/ui/index.ts (if exists, otherwise create)

export { LazyImage } from './lazy-image';
export { PrefetchLink } from './prefetch-link';
export { VirtualList } from './virtual-list';
export { VirtualGrid } from './virtual-grid';
```

---

## Performance Metrics & Monitoring

### Key Metrics to Track

| Metric | Target | Measurement |
|--------|--------|-------------|
| First Contentful Paint | < 1.5s | Lighthouse |
| Largest Contentful Paint | < 2.5s | Lighthouse |
| Time to Interactive | < 3.5s | Lighthouse |
| Total Blocking Time | < 200ms | Lighthouse |
| Cumulative Layout Shift | < 0.1 | Lighthouse |
| List Render Time (100 items) | < 16ms | React DevTools |
| Re-render Count | Minimize | React DevTools |

### Testing Strategy

```typescript
// File: src/components/ui/__tests__/lazy-image.test.tsx

describe('LazyImage', () => {
  it('should not load image until in viewport');
  it('should show skeleton while loading');
  it('should handle load errors with fallback');
  it('should trigger onImageLoad callback');
  it('should cleanup observer on unmount');
});

// File: src/hooks/__tests__/usePrefetch.test.ts

describe('usePrefetch', () => {
  it('should prefetch on hover after delay');
  it('should not prefetch if route not in registry');
  it('should cancel prefetch if mouse leaves early');
  it('should handle concurrent prefetch requests');
});

// File: src/components/ui/__tests__/virtual-list.test.tsx

describe('VirtualList', () => {
  it('should only render visible items plus overscan');
  it('should scroll to index correctly');
  it('should handle variable item heights');
  it('should update when items change');
});
```

---

## Migration Guide

### Phase 1: Core Hooks (Week 1)
1. Implement `useIntersectionObserver`
2. Implement `usePrefetch`
3. Implement `useVirtualList`
4. Add unit tests for all hooks

### Phase 2: Components (Week 1-2)
1. Build `LazyImage` component
2. Build `PrefetchLink` component
3. Build `VirtualList` component
4. Build `VirtualGrid` component

### Phase 3: Integration (Week 2)
1. Replace `NavLink` with `PrefetchLink` in Sidebar
2. Add `LazyImage` to property card images
3. Apply `VirtualList` to deal pipeline columns
4. Wrap list item components with `memo()`

### Phase 4: Validation (Week 2)
1. Run Lighthouse audits before/after
2. Profile with React DevTools
3. Verify no regressions in e2e tests
4. Document performance improvements

---

## Appendix: Browser Support

| Feature | Chrome | Firefox | Safari | Edge |
|---------|--------|---------|--------|------|
| IntersectionObserver | 58+ | 55+ | 12.1+ | 16+ |
| ResizeObserver | 64+ | 69+ | 13.1+ | 79+ |
| CSS contain | 52+ | 69+ | 15.4+ | 79+ |
| loading="lazy" | 77+ | 75+ | 15.4+ | 79+ |

Polyfills recommended for Safari < 12.1:
- `intersection-observer` npm package

---

*Architecture designed by: SPARC Architecture Agent*
*Date: 2026-01-14*
*Version: 1.0.0*
