# Loading States Quick Reference Card

## 🎯 Common Patterns

### Pattern 1: Data Fetching with Loading State
```tsx
import { PropertyCardSkeletonGrid } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/ui/error-state';
import { EmptyInvestments } from '@/components/ui/empty-state';

const { data, isLoading, error, refetch } = useQuery();

if (isLoading) return <PropertyCardSkeletonGrid count={6} />;
if (error) return <ErrorState title="Load failed" onRetry={refetch} />;
if (!data?.length) return <EmptyInvestments onAdd={handleAdd} />;
return <DataView data={data} />;
```

### Pattern 2: Global Loading Operations
```tsx
import { useLoading } from '@/contexts/LoadingContext';

const { startLoading, stopLoading } = useLoading();

const handleSave = async () => {
  startLoading('Saving...');
  await api.save(data);
  stopLoading();
};
```

### Pattern 3: Suspense + Error Boundary
```tsx
import { PageSuspenseWrapper } from '@/components/SuspenseWrapper';
import { StatCardSkeletonGrid } from '@/components/ui/skeleton';

<PageSuspenseWrapper fallback={<StatCardSkeletonGrid count={4} />}>
  <LazyComponent />
</PageSuspenseWrapper>
```

---

## 📦 Component Reference

### Skeletons
```tsx
// Properties
<PropertyCardSkeleton />
<PropertyCardSkeletonGrid count={6} />

// Tables
<TableSkeleton rows={5} columns={4} />
<CompactTableSkeleton rows={8} />

// Charts
<ChartSkeleton height={300} />
<ChartCardSkeleton />
<LineChartSkeleton />

// Deals
<DealCardSkeleton />
<DealPipelineSkeleton />

// Stats
<StatCardSkeleton orientation="horizontal" />
<StatCardSkeletonGrid count={4} />
```

### Error States
```tsx
// Full error
<ErrorState 
  title="Error" 
  description="Details"
  onRetry={retry}
  variant="error" // error | warning | info
/>

// Inline
<InlineError message="Error message" variant="error" />

// Alert
<ErrorAlert title="Error" message="Details" onDismiss={close} />
```

### Empty States
```tsx
// Custom
<EmptyState
  icon={Home}
  title="No data"
  description="Add items to get started"
  action={{ label: "Add", onClick: handleAdd }}
/>

// Presets
<EmptyInvestments onAdd={handleAdd} />
<EmptyTransactions />
<EmptyDocuments onUpload={handleUpload} />
<EmptyDeals onAdd={handleAdd} />

// Table
<TableEmptyState 
  searchTerm={search} 
  onClearSearch={clear} 
/>
```

### Loading Components
```tsx
// Overlay
<LoadingOverlay message="Loading..." />

// Inline
<InlineLoading message="Processing..." size="md" />

// Button
<LoadingButton 
  isLoading={loading}
  loadingText="Saving..."
  onClick={save}
>
  Save
</LoadingButton>

// Spinner
<LoadingSpinner size="lg" />
```

---

## 🔑 Import Paths

```tsx
// Skeletons
import { 
  PropertyCardSkeleton,
  TableSkeleton,
  ChartSkeleton,
  DealCardSkeleton,
  StatCardSkeleton
} from '@/components/ui/skeleton';

// Error & Empty States
import { ErrorState, InlineError, ErrorAlert } from '@/components/ui/error-state';
import { EmptyState, EmptyInvestments } from '@/components/ui/empty-state';

// Loading Context
import { 
  useLoading, 
  LoadingOverlay,
  LoadingButton,
  LoadingSpinner 
} from '@/contexts/LoadingContext';

// Suspense
import { 
  SuspenseWrapper,
  PageSuspenseWrapper 
} from '@/components/SuspenseWrapper';

// Error Boundary
import { ErrorBoundary } from '@/components/ErrorBoundary';
```

---

## 🎨 Variants

### Error State Variants
- `error` - Red, for failures
- `warning` - Yellow, for cautions
- `info` - Blue, for information

### Skeleton Orientations
- `horizontal` - Side-by-side layout
- `vertical` - Stacked layout

### Loading Sizes
- `sm` - 16px (h-4 w-4)
- `md` - 24px (h-6 w-6)
- `lg` - 32px (h-8 w-8)
- `xl` - 48px (h-12 w-12)

---

## 🚀 Setup Checklist

- [ ] Wrap app in `<LoadingProvider>`
- [ ] Add `<ErrorBoundary>` to routes
- [ ] Replace loading indicators with skeletons
- [ ] Add error states with retry
- [ ] Show empty states when no data
- [ ] Test all loading scenarios

---

## 📚 Full Documentation

See `src/components/LOADING_STATES_GUIDE.md` for:
- Complete API reference
- Detailed usage examples
- Best practices
- Accessibility guidelines
