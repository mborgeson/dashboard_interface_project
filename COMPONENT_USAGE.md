# Error Boundary and Skeleton Components Usage

## Error Boundary

The `ErrorBoundary` component is already integrated into the application at the root level in `main.tsx`. It will automatically catch and display errors from any component in the app.

### Features
- Catches React component errors and displays a user-friendly message
- Shows error details in development mode only
- Provides "Retry" and "Reload Page" buttons for recovery
- Matches the dashboard's neutral color palette

### Usage in Components

You can also wrap specific sections with ErrorBoundary for more granular error handling:

```tsx
import { ErrorBoundary } from '@/components/ErrorBoundary';

function SomeFeature() {
  return (
    <ErrorBoundary fallback={<div>Something went wrong in this feature.</div>}>
      <ComplexComponent />
    </ErrorBoundary>
  );
}
```

## Skeleton Components

The skeleton components provide loading states while data is being fetched.

### Base Skeleton

```tsx
import { Skeleton } from '@/components/ui/skeleton';

<Skeleton className="h-4 w-[250px]" />
```

### Card Skeleton

Use `CardSkeleton` for dashboard card loading states:

```tsx
import { CardSkeleton } from '@/components/ui/skeleton';

function DashboardCard() {
  const { data, isLoading } = useQuery(...);

  if (isLoading) {
    return <CardSkeleton />;
  }

  return <Card>{/* actual content */}</Card>;
}
```

### Table Skeleton

Use `TableSkeleton` for data table loading states:

```tsx
import { TableSkeleton } from '@/components/ui/skeleton';

function DataTable() {
  const { data, isLoading } = useQuery(...);

  if (isLoading) {
    return <TableSkeleton rows={10} columns={5} />;
  }

  return <Table>{/* actual table */}</Table>;
}
```

### Chart Skeleton

Use `ChartSkeleton` for chart/graph loading states:

```tsx
import { ChartSkeleton } from '@/components/ui/skeleton';

function AnalyticsChart() {
  const { data, isLoading } = useQuery(...);

  if (isLoading) {
    return <ChartSkeleton />;
  }

  return <ResponsiveContainer>{/* actual chart */}</ResponsiveContainer>;
}
```

## Best Practices

1. **Error Boundaries**: Wrap major features in their own error boundaries for better error isolation
2. **Loading States**: Always show skeleton components during data fetching instead of blank screens
3. **Skeleton Matching**: Make skeleton layouts match the actual content layout as closely as possible
4. **Accessibility**: Skeletons automatically use `animate-pulse` for visual feedback

## Example: Complete Component

```tsx
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { CardSkeleton } from '@/components/ui/skeleton';
import { useQuery } from '@tanstack/react-query';

function PropertyOverview() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['properties'],
    queryFn: fetchProperties,
  });

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {data?.map(property => (
          <PropertyCard key={property.id} property={property} />
        ))}
      </div>
    </ErrorBoundary>
  );
}
```
