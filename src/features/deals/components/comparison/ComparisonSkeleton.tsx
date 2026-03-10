/**
 * ComparisonSkeleton - Content-specific loading skeleton for the Deal Comparison page.
 * Mimics the layout of the comparison table + charts view.
 */
import { Skeleton } from '@/components/ui/skeleton';

interface ComparisonSkeletonProps {
  dealCount?: number;
}

export function ComparisonSkeleton({ dealCount = 3 }: ComparisonSkeletonProps) {
  return (
    <div className="space-y-6">
      {/* Header skeleton */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-4 w-28" /> {/* Back link */}
          <Skeleton className="h-9 w-56" /> {/* Title */}
          <Skeleton className="h-4 w-44" /> {/* Subtitle */}
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="h-10 w-40 rounded-lg" /> {/* View toggle */}
          <Skeleton className="h-10 w-28 rounded-lg" /> {/* Add deals */}
          <Skeleton className="h-10 w-24 rounded-lg" /> {/* Share */}
          <Skeleton className="h-10 w-32 rounded-lg" /> {/* Export */}
        </div>
      </div>

      {/* Comparison Table Skeleton */}
      <div className="bg-white rounded-lg border border-neutral-200 shadow-card overflow-hidden">
        <div className="px-6 py-4 border-b border-neutral-200">
          <Skeleton className="h-6 w-44 mb-1" />
          <Skeleton className="h-4 w-72" />
        </div>
        <div className="p-6">
          {/* Table header row: Metric + deal columns */}
          <div className="flex gap-4 border-b border-neutral-200 pb-3 mb-3">
            <Skeleton className="h-5 w-36" />
            {Array.from({ length: dealCount }).map((_, i) => (
              <Skeleton key={`header-${i}`} className="h-5 flex-1" />
            ))}
          </div>

          {/* Metric rows */}
          {Array.from({ length: 12 }).map((_, rowIdx) => (
            <div
              key={rowIdx}
              className="flex gap-4 py-2.5 border-b border-neutral-100 last:border-0"
            >
              <Skeleton className="h-4 w-36" />
              {Array.from({ length: dealCount }).map((_, colIdx) => (
                <Skeleton
                  key={`cell-${rowIdx}-${colIdx}`}
                  className="h-4 flex-1"
                />
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Charts Skeleton */}
      <div className="space-y-4">
        <Skeleton className="h-6 w-40" /> {/* Visual Comparison heading */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Bar chart skeleton */}
          <div className="bg-white rounded-lg border border-neutral-200 p-6">
            <Skeleton className="h-5 w-32 mb-4" />
            <div className="flex items-end justify-around gap-3 h-48">
              {Array.from({ length: dealCount * 3 }).map((_, i) => (
                <Skeleton
                  key={`bar-${i}`}
                  className="w-full rounded-t"
                  style={{ height: `${30 + ((i * 17) % 60)}%` }}
                />
              ))}
            </div>
            <div className="flex justify-center gap-4 mt-4">
              {Array.from({ length: dealCount }).map((_, i) => (
                <Skeleton key={`legend-${i}`} className="h-3 w-20" />
              ))}
            </div>
          </div>

          {/* Radar/second chart skeleton */}
          <div className="bg-white rounded-lg border border-neutral-200 p-6">
            <Skeleton className="h-5 w-36 mb-4" />
            <div className="flex items-center justify-center h-48">
              <Skeleton className="h-40 w-40 rounded-full" />
            </div>
            <div className="flex justify-center gap-4 mt-4">
              {Array.from({ length: dealCount }).map((_, i) => (
                <Skeleton key={`legend2-${i}`} className="h-3 w-20" />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
