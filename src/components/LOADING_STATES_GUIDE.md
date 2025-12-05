# Loading States and Error Handling Guide

Comprehensive guide for implementing loading states and error handling in the B&R Capital Dashboard.

## Table of Contents

1. [Skeleton Components](#skeleton-components)
2. [Error States](#error-states)
3. [Empty States](#empty-states)
4. [Loading Context](#loading-context)
5. [Suspense Wrappers](#suspense-wrappers)
6. [Error Boundary](#error-boundary)
7. [Usage Examples](#usage-examples)

---

## Skeleton Components

Skeleton loaders provide visual feedback while content is loading.

### Base Skeleton

```tsx
import { Skeleton } from '@/components/ui/skeleton';

// Simple skeleton
<Skeleton className="h-4 w-full" />

// Rounded skeleton
<Skeleton className="h-12 w-12 rounded-full" />
```

### PropertyCardSkeleton

For investment property cards:

```tsx
import { PropertyCardSkeleton, PropertyCardSkeletonGrid } from '@/components/ui/skeleton';

// Single card
<PropertyCardSkeleton />

// Grid of cards
<PropertyCardSkeletonGrid count={6} />
```

### TableSkeleton

For data tables:

```tsx
import { TableSkeleton, CompactTableSkeleton } from '@/components/ui/skeleton';

// Standard table
<TableSkeleton 
  rows={5} 
  columns={4} 
  showHeader={true}
  columnWidths={['w-32', 'flex-1', 'w-24', 'w-20']}
/>

// Compact list view
<CompactTableSkeleton rows={8} />
```

### ChartSkeleton

For analytics charts:

```tsx
import { ChartSkeleton, ChartCardSkeleton, LineChartSkeleton } from '@/components/ui/skeleton';

// Bar chart skeleton
<ChartSkeleton showLegend={true} height={300} />

// Chart in card
<ChartCardSkeleton />

// Line chart skeleton
<LineChartSkeleton />
```

### DealCardSkeleton

For deal pipeline:

```tsx
import { DealCardSkeleton, DealCardSkeletonList, DealPipelineSkeleton } from '@/components/ui/skeleton';

// Single deal card
<DealCardSkeleton />

// List of deals
<DealCardSkeletonList count={3} />

// Full pipeline view
<DealPipelineSkeleton />
```

### StatCardSkeleton

For summary statistics:

```tsx
import { StatCardSkeleton, StatCardSkeletonGrid, MiniStatSkeleton } from '@/components/ui/skeleton';

// Single stat card
<StatCardSkeleton orientation="horizontal" />

// Grid of stat cards
<StatCardSkeletonGrid count={4} orientation="horizontal" />

// Mini stat (for sidebars)
<MiniStatSkeleton />
```

---

## Error States

Display error messages with retry functionality.

### ErrorState Component

```tsx
import { ErrorState, InlineError, ErrorAlert } from '@/components/ui/error-state';

// Full error page
<ErrorState
  title="Failed to load data"
  description="Unable to fetch property information. Please try again."
  variant="error"
  onRetry={() => refetch()}
  retryLabel="Retry"
  fullScreen={true}
/>

// Warning variant
<ErrorState
  title="Connection Issue"
  description="Some features may be unavailable."
  variant="warning"
/>

// Info variant
<ErrorState
  title="Maintenance Notice"
  description="System will be updated at 2 AM EST."
  variant="info"
/>

// Inline error
<InlineError 
  message="Invalid email format. Please check and try again."
  variant="error"
/>

// Dismissible alert
<ErrorAlert
  title="Upload Failed"
  message="File size exceeds 10MB limit."
  onDismiss={() => setError(null)}
/>
```

---

## Empty States

Display when no data is available.

### EmptyState Component

```tsx
import { 
  EmptyState, 
  CompactEmptyState,
  TableEmptyState,
  EmptyInvestments,
  EmptyTransactions,
  EmptyDocuments,
  EmptyDeals
} from '@/components/ui/empty-state';
import { Home } from 'lucide-react';

// Custom empty state
<EmptyState
  icon={Home}
  title="No properties yet"
  description="Start building your portfolio by adding your first property."
  action={{
    label: 'Add Property',
    onClick: () => navigate('/properties/new')
  }}
/>

// Compact version
<CompactEmptyState
  icon={Inbox}
  title="No results"
  description="Try adjusting your filters."
/>

// Table empty state with search
<TableEmptyState
  searchTerm={searchQuery}
  onClearSearch={() => setSearchQuery('')}
/>

// Preset empty states
<EmptyInvestments onAdd={() => openAddDialog()} />
<EmptyTransactions />
<EmptyDocuments onUpload={() => openUploadDialog()} />
<EmptyDeals onAdd={() => openDealForm()} />
```

---

## Loading Context

Global loading state management.

### Setup LoadingProvider

Wrap your app in `LoadingProvider`:

```tsx
// App.tsx or main.tsx
import { LoadingProvider } from '@/contexts/LoadingContext';

function App() {
  return (
    <LoadingProvider>
      <YourApp />
    </LoadingProvider>
  );
}
```

### Using the Loading Context

```tsx
import { useLoading, InlineLoading, LoadingButton, LoadingSpinner } from '@/contexts/LoadingContext';

function MyComponent() {
  const { isLoading, startLoading, stopLoading, setLoading } = useLoading();

  const fetchData = async () => {
    startLoading('Loading properties...');
    try {
      const data = await api.getProperties();
      // ... handle data
    } finally {
      stopLoading();
    }
  };

  return (
    <>
      {/* Inline loading indicator */}
      {isLoading && <InlineLoading message="Processing..." size="md" />}
      
      {/* Loading button */}
      <LoadingButton
        isLoading={isLoading}
        loadingText="Saving..."
        onClick={handleSave}
      >
        Save Changes
      </LoadingButton>
      
      {/* Loading spinner */}
      <LoadingSpinner size="lg" />
    </>
  );
}
```

---

## Suspense Wrappers

Simplify React Suspense with error boundaries.

### Basic Usage

```tsx
import { 
  SuspenseWrapper, 
  PageSuspenseWrapper,
  CardSuspenseWrapper,
  TableSuspenseWrapper,
  withSuspense
} from '@/components/SuspenseWrapper';

// Page-level suspense
<PageSuspenseWrapper>
  <LazyComponent />
</PageSuspenseWrapper>

// Card-level suspense
<CardSuspenseWrapper>
  <LazyChart />
</CardSuspenseWrapper>

// Table-level suspense
<TableSuspenseWrapper>
  <LazyDataTable />
</TableSuspenseWrapper>

// Custom fallback
<SuspenseWrapper 
  fallback={<PropertyCardSkeletonGrid count={6} />}
  errorFallback={<ErrorState title="Failed to load" />}
>
  <PropertyGrid />
</SuspenseWrapper>

// HOC pattern
const LazyPage = withSuspense(MyPage, {
  fallback: <LoadingSpinner size="xl" />,
  errorFallback: <ErrorState fullScreen />
});
```

---

## Error Boundary

Catch and handle React errors.

### Basic Usage

```tsx
import { ErrorBoundary } from '@/components/ErrorBoundary';

// Wrap components
<ErrorBoundary>
  <YourComponent />
</ErrorBoundary>

// Custom fallback
<ErrorBoundary 
  fallback={
    <ErrorState 
      title="Component Error"
      description="This component failed to render."
      fullScreen
    />
  }
>
  <YourComponent />
</ErrorBoundary>
```

The ErrorBoundary automatically:
- Catches rendering errors
- Logs errors to console
- Shows stack trace in development
- Provides retry functionality
- Offers page reload option

---

## Usage Examples

### Example 1: Data Table with Loading States

```tsx
import { useState, useEffect } from 'react';
import { TableSkeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/ui/error-state';
import { TableEmptyState } from '@/components/ui/empty-state';

function TransactionsTable() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchTransactions();
  }, []);

  const fetchTransactions = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.getTransactions();
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <TableSkeleton rows={8} columns={5} />;
  }

  if (error) {
    return (
      <ErrorState
        title="Failed to load transactions"
        description={error}
        onRetry={fetchTransactions}
      />
    );
  }

  if (!data || data.length === 0) {
    return (
      <TableEmptyState
        searchTerm={searchTerm}
        onClearSearch={() => setSearchTerm('')}
      />
    );
  }

  return <DataTable data={data} />;
}
```

### Example 2: Property Grid with Suspense

```tsx
import { Suspense } from 'react';
import { PropertyCardSkeletonGrid } from '@/components/ui/skeleton';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { ErrorState } from '@/components/ui/error-state';
import { EmptyInvestments } from '@/components/ui/empty-state';

const LazyPropertyGrid = lazy(() => import('./PropertyGrid'));

function PropertiesPage() {
  return (
    <ErrorBoundary
      fallback={
        <ErrorState
          title="Failed to load properties"
          description="An error occurred while loading the property grid."
        />
      }
    >
      <Suspense fallback={<PropertyCardSkeletonGrid count={6} />}>
        <LazyPropertyGrid />
      </Suspense>
    </ErrorBoundary>
  );
}
```

### Example 3: Form with Loading Button

```tsx
import { useState } from 'react';
import { LoadingButton } from '@/contexts/LoadingContext';
import { ErrorAlert } from '@/components/ui/error-state';

function PropertyForm() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (data) => {
    setLoading(true);
    setError(null);
    
    try {
      await api.createProperty(data);
      toast.success('Property created successfully');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {error && (
        <ErrorAlert
          title="Submission Failed"
          message={error}
          onDismiss={() => setError(null)}
        />
      )}
      
      {/* Form fields... */}
      
      <LoadingButton
        type="submit"
        isLoading={loading}
        loadingText="Creating property..."
      >
        Create Property
      </LoadingButton>
    </form>
  );
}
```

### Example 4: Dashboard Stats with Global Loading

```tsx
import { useLoading } from '@/contexts/LoadingContext';
import { StatCardSkeletonGrid } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/ui/error-state';

function DashboardStats() {
  const { startLoading, stopLoading } = useLoading();
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    startLoading('Loading dashboard statistics...');
    try {
      const data = await api.getStats();
      setStats(data);
    } catch (err) {
      setError(err.message);
    } finally {
      stopLoading();
    }
  };

  if (error) {
    return (
      <ErrorState
        title="Failed to load statistics"
        description={error}
        onRetry={loadStats}
        variant="error"
      />
    );
  }

  if (!stats) {
    return <StatCardSkeletonGrid count={4} />;
  }

  return <StatsGrid data={stats} />;
}
```

---

## Best Practices

1. **Always show loading states** - Users should never see a blank screen
2. **Match skeleton structure** - Skeletons should match actual content layout
3. **Provide retry options** - Always offer users a way to recover from errors
4. **Use appropriate variants** - Match error severity with correct variant
5. **Keep error messages clear** - Explain what went wrong and how to fix it
6. **Combine with React Query** - Use with data fetching libraries for automatic handling
7. **Test error states** - Always test loading and error scenarios
8. **Accessibility** - Include proper ARIA labels for screen readers

---

## Component API Reference

### Skeleton Components
- `PropertyCardSkeleton`: Single property card skeleton
- `TableSkeleton`: Data table skeleton with configurable rows/columns
- `ChartSkeleton`: Chart placeholder with animated bars
- `DealCardSkeleton`: Deal pipeline card skeleton
- `StatCardSkeleton`: Stat card skeleton with orientation option

### Error Components
- `ErrorState`: Full error display with retry button
- `InlineError`: Compact inline error message
- `ErrorAlert`: Dismissible error alert

### Empty State Components
- `EmptyState`: Full empty state with action button
- `CompactEmptyState`: Minimal empty state
- `TableEmptyState`: Table-specific empty state with search support

### Loading Components
- `LoadingProvider`: Global loading state context
- `LoadingOverlay`: Full-screen loading overlay
- `InlineLoading`: Inline loading indicator
- `LoadingButton`: Button with loading state
- `LoadingSpinner`: Standalone spinner

### Suspense Components
- `SuspenseWrapper`: Basic suspense with error boundary
- `PageSuspenseWrapper`: Page-level suspense
- `CardSuspenseWrapper`: Card-level suspense
- `TableSuspenseWrapper`: Table-level suspense

---

## Questions?

For issues or questions, refer to:
- Component source code in `/src/components/`
- Existing shadcn/ui components
- React documentation for Suspense and Error Boundaries
