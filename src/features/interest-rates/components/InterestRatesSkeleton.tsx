/**
 * InterestRatesSkeleton - Content-specific loading skeleton for the Interest Rates page.
 * Mimics the layout of rate cards grouped by category.
 */
import { Skeleton } from '@/components/ui/skeleton';

export function InterestRatesSkeleton() {
  // Mimics the 4 rate categories: Federal (3 cards), Treasury (6 cards), SOFR (3 cards), Mortgage (2 cards)
  const categories = [
    { label: 'Federal Reserve Rates', count: 3 },
    { label: 'Treasury Yields', count: 6 },
    { label: 'SOFR Rates', count: 3 },
    { label: 'Mortgage Rates', count: 2 },
  ];

  return (
    <div className="space-y-8">
      {/* As-of date header */}
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-4 w-32" />
      </div>

      {categories.map((category) => (
        <div key={category.label} className="space-y-3">
          {/* Category label */}
          <Skeleton className="h-5 w-44" />

          {/* Rate cards grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: category.count }).map((_, i) => (
              <RateCardSkeleton key={i} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function RateCardSkeleton() {
  return (
    <div className="bg-white rounded-lg border border-neutral-200 shadow-sm p-4">
      {/* Header: name + info icon */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1 space-y-1">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-3 w-36" />
        </div>
        <Skeleton className="h-4 w-4 rounded-full" />
      </div>

      {/* Value + change badge */}
      <div className="flex items-end justify-between">
        <Skeleton className="h-8 w-20" />
        <Skeleton className="h-6 w-16 rounded-full" />
      </div>

      {/* Previous value */}
      <div className="mt-2 flex items-center justify-between">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="h-3 w-12" />
      </div>
    </div>
  );
}
