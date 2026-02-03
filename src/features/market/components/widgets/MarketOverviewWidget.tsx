import { Card } from '@/components/ui/card';
import { ErrorState } from '@/components/ui/error-state';
import { StatCardSkeletonGrid } from '@/components/skeletons';
import { useMarketOverview } from '@/hooks/api/useMarketData';
import { TrendingUp, TrendingDown, Users, Briefcase, DollarSign } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { MSAOverview } from '@/types/market';

interface MarketOverviewWidgetProps {
  className?: string;
  variant?: 'compact' | 'detailed';
}

interface MetricConfig {
  label: string;
  value: number;
  change: number;
  icon: typeof Users;
  description: string;
}

function formatNumber(value: number): string {
  if (value >= 1000000000) {
    return `$${(value / 1000000000).toFixed(1)}B`;
  }
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(2)}M`;
  }
  return value.toLocaleString();
}

function formatPercentage(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function getMetrics(overview: MSAOverview): MetricConfig[] {
  return [
    {
      label: 'Population',
      value: overview.population,
      change: overview.populationGrowth,
      icon: Users,
      description: 'Phoenix MSA residents',
    },
    {
      label: 'Employment',
      value: overview.employment,
      change: overview.employmentGrowth,
      icon: Briefcase,
      description: 'Total employed',
    },
    {
      label: 'GDP',
      value: overview.gdp,
      change: overview.gdpGrowth,
      icon: DollarSign,
      description: 'Regional GDP',
    },
  ];
}

export function MarketOverviewWidget({
  className,
  variant = 'detailed'
}: MarketOverviewWidgetProps) {
  const { data, isLoading, error, refetch } = useMarketOverview();

  if (isLoading) {
    return (
      <div className={className}>
        <div className="flex items-center justify-between mb-4">
          <div className="h-7 w-48 bg-muted rounded animate-pulse" />
          <div className="h-4 w-32 bg-muted rounded animate-pulse" />
        </div>
        <StatCardSkeletonGrid count={3} orientation="vertical" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className={className}>
        <ErrorState
          title="Failed to load market overview"
          description="Unable to fetch Phoenix MSA data. Please try again."
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  const { msaOverview } = data;
  const metrics = getMetrics(msaOverview);

  if (variant === 'compact') {
    return (
      <Card className={cn('p-4', className)}>
        <h3 className="text-sm font-semibold text-primary-500 mb-3">Phoenix MSA</h3>
        <div className="grid grid-cols-3 gap-4">
          {metrics.map((metric) => {
            const isPositive = metric.change > 0;
            return (
              <div key={metric.label} className="text-center">
                <p className="text-xs text-neutral-500 mb-1">{metric.label}</p>
                <p className="text-lg font-bold text-primary-500">
                  {formatNumber(metric.value)}
                </p>
                <p className={cn(
                  'text-xs font-medium',
                  isPositive ? 'text-green-600' : 'text-red-600'
                )}>
                  {isPositive ? '+' : ''}{formatPercentage(metric.change)}
                </p>
              </div>
            );
          })}
        </div>
        <div className="mt-3 px-2 py-1.5 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
          Static reference data — not connected to live feeds.
        </div>
      </Card>
    );
  }

  return (
    <div className={className}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-section-title text-primary-500">Phoenix MSA Overview</h2>
        <p className="text-sm text-neutral-500">
          Last updated: {new Date(msaOverview.lastUpdated).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
          })}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          const TrendIcon = metric.change > 0 ? TrendingUp : TrendingDown;
          const trendColor = metric.change > 0 ? 'text-green-600' : 'text-red-600';

          return (
            <Card key={metric.label} className="p-6">
              <div className="flex items-start justify-between mb-3">
                <div className="p-3 rounded-lg bg-primary-50">
                  <Icon className="h-6 w-6 text-primary-500" />
                </div>
                <div className={cn('flex items-center gap-1 text-sm font-medium', trendColor)}>
                  <TrendIcon className="h-4 w-4" />
                  <span>{formatPercentage(Math.abs(metric.change))} YoY</span>
                </div>
              </div>

              <div className="space-y-1">
                <p className="text-sm font-medium text-neutral-600">{metric.label}</p>
                <p className="text-3xl font-bold text-primary-500">
                  {formatNumber(metric.value)}
                </p>
                <p className="text-xs text-neutral-500">{metric.description}</p>
              </div>
            </Card>
          );
        })}
      </div>
      <div className="mt-3 px-3 py-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
        Static reference data — not connected to live market feeds. Integration with third-party data sources is planned.
      </div>
    </div>
  );
}
