import type { ReactNode } from 'react';
import { StatCardSkeleton } from '@/components/skeletons';
import { ChartSkeleton } from '@/components/skeletons';
import { cn } from '@/lib/utils';

interface PageLoadingStateProps {
  /** Page title displayed while loading */
  title: string;
  /** Optional subtitle/description */
  subtitle?: string;
  /** Number of stat card skeletons to show (default: 4) */
  statCards?: number;
  /** Grid columns for stat card skeletons (default: "grid-cols-1 md:grid-cols-2 lg:grid-cols-4") */
  statCardColumns?: string;
  /** Chart skeleton heights to render below stats (default: none) */
  chartHeights?: number[];
  /** Layout for charts: "grid" places them in 2-col grid, "stack" stacks vertically */
  chartLayout?: 'grid' | 'stack';
  /** Optional extra content to render in the header area (e.g. nav tabs) */
  headerExtra?: ReactNode;
  /** Title style class override */
  titleClassName?: string;
  className?: string;
}

export function PageLoadingState({
  title,
  subtitle,
  statCards = 4,
  statCardColumns,
  chartHeights = [],
  chartLayout = 'stack',
  headerExtra,
  titleClassName = 'text-page-title text-neutral-900 font-semibold',
  className,
}: PageLoadingStateProps) {
  const gridClass =
    statCardColumns ??
    'grid-cols-1 md:grid-cols-2 lg:grid-cols-4';

  return (
    <div className={cn('space-y-6', className)}>
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={titleClassName}>{title}</h1>
          {subtitle && (
            <p className="text-neutral-600 mt-1 text-sm">{subtitle}</p>
          )}
        </div>
        {headerExtra}
      </div>

      {/* Stat Card Skeletons */}
      {statCards > 0 && (
        <div className={cn('grid gap-6', gridClass)}>
          {Array.from({ length: statCards }).map((_, i) => (
            <StatCardSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Chart Skeletons */}
      {chartHeights.length > 0 && (
        chartLayout === 'grid' ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {chartHeights.map((height, i) => (
              <ChartSkeleton key={i} height={height} />
            ))}
          </div>
        ) : (
          <div className="space-y-6">
            {chartHeights.map((height, i) => (
              <ChartSkeleton key={i} height={height} />
            ))}
          </div>
        )
      )}
    </div>
  );
}

export type { PageLoadingStateProps };
