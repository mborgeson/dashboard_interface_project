/**
 * PropertyDetailSkeleton - Content-specific loading skeleton for the Property Detail page.
 * Mimics the hero section, tabs, main content area, and activity feed sidebar.
 */
import { Skeleton } from '@/components/ui/skeleton';

export function PropertyDetailSkeleton() {
  return (
    <div className="space-y-6">
      {/* Hero Section Skeleton */}
      <div className="bg-white rounded-lg border border-neutral-200 shadow-card overflow-hidden">
        {/* Hero image/banner placeholder */}
        <Skeleton className="h-48 w-full rounded-none" />

        {/* Property header info */}
        <div className="p-6 space-y-4">
          <div className="flex items-start justify-between">
            <div className="space-y-2 flex-1">
              <Skeleton className="h-8 w-72" /> {/* Property name */}
              <Skeleton className="h-4 w-56" /> {/* Address */}
              <div className="flex items-center gap-3 mt-2">
                <Skeleton className="h-6 w-20 rounded-full" /> {/* Badge */}
                <Skeleton className="h-6 w-24 rounded-full" /> {/* Badge */}
                <Skeleton className="h-6 w-16 rounded-full" /> {/* Badge */}
              </div>
            </div>
            <div className="text-right space-y-2">
              <Skeleton className="h-8 w-32 ml-auto" /> {/* Value */}
              <Skeleton className="h-4 w-24 ml-auto" /> {/* Label */}
            </div>
          </div>

          {/* Key metrics row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-neutral-200">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="space-y-1">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-6 w-24" />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Tabs Skeleton */}
      <div className="bg-white border-b">
        <div className="flex gap-8 px-6">
          {['Overview', 'Financials', 'Operations', 'Performance', 'Transactions'].map(
            (tab) => (
              <Skeleton key={tab} className="h-4 w-20 my-4" />
            )
          )}
        </div>
      </div>

      {/* Tab Content + Activity Feed Sidebar Skeleton */}
      <div className="bg-neutral-50 min-h-[600px]">
        <div className="grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-6 p-6">
          {/* Main Content Area */}
          <div className="space-y-6">
            {/* Stat cards row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <div
                  key={i}
                  className="bg-white rounded-lg border border-neutral-200 p-4 space-y-2"
                >
                  <Skeleton className="h-3 w-20" />
                  <Skeleton className="h-7 w-28" />
                  <Skeleton className="h-3 w-24" />
                </div>
              ))}
            </div>

            {/* Chart area */}
            <div className="bg-white rounded-lg border border-neutral-200 p-6 space-y-4">
              <Skeleton className="h-6 w-40" />
              <Skeleton className="h-64 w-full" />
            </div>

            {/* Table area */}
            <div className="bg-white rounded-lg border border-neutral-200 p-6 space-y-3">
              <Skeleton className="h-6 w-36" />
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          </div>

          {/* Activity Feed Sidebar */}
          <aside className="space-y-4">
            <div className="bg-white rounded-lg border border-neutral-200 p-4 space-y-4">
              <Skeleton className="h-6 w-32" /> {/* Title */}
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex items-start gap-3">
                  <Skeleton className="h-8 w-8 rounded-full flex-shrink-0" />
                  <div className="space-y-1 flex-1">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-3 w-3/4" />
                    <Skeleton className="h-3 w-20" />
                  </div>
                </div>
              ))}
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
