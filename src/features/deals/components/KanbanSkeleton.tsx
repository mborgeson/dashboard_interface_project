/**
 * KanbanSkeleton - Loading skeleton for the Kanban board
 */
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

interface KanbanSkeletonProps {
  className?: string;
  columns?: number;
  cardsPerColumn?: number;
}

export function KanbanSkeleton({
  className,
  columns = 6,
  cardsPerColumn = 3,
}: KanbanSkeletonProps) {
  return (
    <div className={cn('bg-white rounded-lg border border-neutral-200 shadow-card', className)}>
      {/* Header Skeleton */}
      <div className="p-4 border-b border-neutral-200 bg-gradient-to-r from-blue-50 to-indigo-50">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-48" />
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1 bg-white rounded-lg border border-neutral-200 p-1">
              <Skeleton className="h-8 w-8" />
              <Skeleton className="h-8 w-8" />
            </div>
            <div className="text-right space-y-1">
              <Skeleton className="h-4 w-24 ml-auto" />
              <Skeleton className="h-8 w-28" />
            </div>
          </div>
        </div>
      </div>

      {/* Filters Skeleton */}
      <div className="flex items-center gap-4 px-4 py-3 border-b border-neutral-200 bg-neutral-50">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-9 w-40" />
        <Skeleton className="h-9 w-36" />
      </div>

      {/* Columns Skeleton */}
      <div className={`grid grid-cols-${columns} min-h-[500px]`}>
        {Array.from({ length: columns }).map((_, colIndex) => (
          <div
            key={colIndex}
            className="flex flex-col border-r border-neutral-200 last:border-r-0 bg-neutral-50/50"
          >
            {/* Column Header */}
            <div className="p-4 border-b border-neutral-200/50">
              <div className="flex items-center gap-2 mb-2">
                <Skeleton className="h-6 w-6" />
                <Skeleton className="h-5 w-24" />
              </div>
              <div className="flex items-center justify-between">
                <Skeleton className="h-6 w-6 rounded-full" />
                <Skeleton className="h-4 w-16" />
              </div>
            </div>

            {/* Column Cards */}
            <div className="flex-1 p-3 space-y-3">
              {Array.from({ length: cardsPerColumn }).map((_, cardIndex) => (
                <div
                  key={cardIndex}
                  className="bg-white rounded-lg border border-neutral-200 p-4 space-y-3"
                >
                  {/* Card Header */}
                  <div className="flex items-start justify-between">
                    <div className="space-y-1 flex-1">
                      <Skeleton className="h-5 w-3/4" />
                      <Skeleton className="h-3 w-1/2" />
                    </div>
                    <Skeleton className="h-6 w-20 rounded-md" />
                  </div>

                  {/* Card Metrics */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Skeleton className="h-4 w-16" />
                      <Skeleton className="h-4 w-20" />
                    </div>
                    <div className="flex items-center justify-between">
                      <Skeleton className="h-4 w-16" />
                      <Skeleton className="h-4 w-12" />
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <Skeleton className="h-1.5 w-full rounded-full" />

                  {/* Card Footer */}
                  <div className="flex items-center justify-between pt-2 border-t border-neutral-100">
                    <Skeleton className="h-3 w-20" />
                    <Skeleton className="h-3 w-16" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
