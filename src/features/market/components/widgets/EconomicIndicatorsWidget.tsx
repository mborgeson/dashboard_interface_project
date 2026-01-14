import { Card } from '@/components/ui/card';
import { ErrorState } from '@/components/ui/error-state';
import { StatCardSkeletonGrid } from '@/components/skeletons';
import { useMarketOverview } from '@/hooks/api/useMarketData';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';
import { cn } from '@/lib/utils';
import type { EconomicIndicator } from '@/types/market';

interface EconomicIndicatorsWidgetProps {
  className?: string;
  columns?: 2 | 3 | 4;
  showSparklines?: boolean;
}

// Mock sparkline data for visualization
const sparklineData: Record<string, number[]> = {
  'Unemployment Rate': [4.2, 4.0, 3.9, 3.8, 3.7, 3.5],
  'Job Growth Rate': [2.8, 3.0, 3.2, 3.1, 3.4, 3.5],
  'Median Household Income': [68, 69, 70, 71, 72, 73],
  'Population Growth': [1.6, 1.7, 1.8, 1.9, 2.0, 2.1],
};

function formatValue(value: number, unit: string): string {
  if (unit === '$') {
    return `$${(value / 1000).toFixed(0)}K`;
  }
  return `${value.toFixed(1)}${unit}`;
}

function formatChange(change: number): string {
  return `${change > 0 ? '+' : ''}${(change * 100).toFixed(1)}%`;
}

function getSparklineData(indicatorName: string) {
  return (sparklineData[indicatorName] || [3, 3.2, 3.1, 3.4, 3.3, 3.5]).map((value, index) => ({
    index,
    value,
  }));
}

function getSparklineColor(indicatorName: string, change: number) {
  // Unemployment: negative change is good (green)
  if (indicatorName === 'Unemployment Rate') {
    return change < 0 ? '#10b981' : '#ef4444';
  }
  // Others: positive change is good (green)
  return change > 0 ? '#10b981' : '#ef4444';
}

function getTrendColor(indicatorName: string, change: number) {
  // For unemployment, negative is good
  if (indicatorName === 'Unemployment Rate') {
    return change < 0 ? 'text-green-600' : 'text-red-600';
  }
  return change > 0 ? 'text-green-600' : 'text-red-600';
}

export function EconomicIndicatorsWidget({
  className,
  columns = 4,
  showSparklines = true,
}: EconomicIndicatorsWidgetProps) {
  const { data, isLoading, error, refetch } = useMarketOverview();

  if (isLoading) {
    return (
      <div className={className}>
        <div className="h-7 w-52 bg-muted rounded animate-pulse mb-4" />
        <StatCardSkeletonGrid count={columns} orientation="vertical" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className={className}>
        <ErrorState
          title="Failed to load economic indicators"
          description="Unable to fetch indicator data. Please try again."
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  const { economicIndicators } = data;

  const gridCols = {
    2: 'grid-cols-1 md:grid-cols-2',
    3: 'grid-cols-1 md:grid-cols-3',
    4: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4',
  };

  return (
    <div className={className}>
      <h2 className="text-section-title text-primary-500 mb-4">Key Economic Indicators</h2>

      <div className={cn('grid gap-6', gridCols[columns])}>
        {economicIndicators.map((indicator: EconomicIndicator) => {
          const TrendIcon = indicator.yoyChange < 0 ? TrendingDown : TrendingUp;
          const trendColor = getTrendColor(indicator.indicator, indicator.yoyChange);
          const sparkData = getSparklineData(indicator.indicator);
          const sparkColor = getSparklineColor(indicator.indicator, indicator.yoyChange);

          return (
            <Card key={indicator.indicator} className="p-6">
              <div className="space-y-3">
                {/* Header */}
                <div className="flex items-start justify-between">
                  <p className="text-sm font-medium text-neutral-600">{indicator.indicator}</p>
                  <div className={cn('flex items-center gap-1 text-xs font-medium', trendColor)}>
                    <TrendIcon className="h-3 w-3" />
                    <span>{formatChange(indicator.yoyChange)}</span>
                  </div>
                </div>

                {/* Value */}
                <div>
                  <p className="text-3xl font-bold text-primary-500">
                    {formatValue(indicator.value, indicator.unit)}
                  </p>
                  <p className="text-xs text-neutral-500 mt-1">Current value</p>
                </div>

                {/* Sparkline */}
                {showSparklines && (
                  <>
                    <div className="h-12 -mx-2">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={sparkData}>
                          <Line
                            type="monotone"
                            dataKey="value"
                            stroke={sparkColor}
                            strokeWidth={2}
                            dot={false}
                            isAnimationActive={false}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>

                    <p className="text-xs text-neutral-400">Last 6 months</p>
                  </>
                )}
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
