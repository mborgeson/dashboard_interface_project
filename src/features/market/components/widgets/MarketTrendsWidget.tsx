import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { ErrorState } from '@/components/ui/error-state';
import { Skeleton } from '@/components/ui/skeleton';
import { useMarketTrends } from '@/hooks/api/useMarketData';
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { cn } from '@/lib/utils';

interface MarketTrendsWidgetProps {
  className?: string;
  periodMonths?: number;
  chartType?: 'area' | 'line';
  height?: number;
  showPeriodSelector?: boolean;
}

type MetricType = 'rentGrowth' | 'occupancy' | 'capRate';

interface TooltipPayload {
  payload: { month: string };
  value: number;
  name: string;
  color: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayload[];
}

const metricConfigs = {
  rentGrowth: {
    label: 'Rent Growth',
    color: '#10b981',
    format: (v: number) => `${(v * 100).toFixed(1)}%`,
  },
  occupancy: {
    label: 'Occupancy',
    color: '#3b82f6',
    format: (v: number) => `${(v * 100).toFixed(1)}%`,
  },
  capRate: {
    label: 'Cap Rate',
    color: '#8b5cf6',
    format: (v: number) => `${(v * 100).toFixed(2)}%`,
  },
};

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white p-3 border border-neutral-200 rounded-lg shadow-lg">
        <p className="text-sm font-medium text-neutral-900 mb-2">{payload[0].payload.month}</p>
        {payload.map((entry) => {
          const config = metricConfigs[entry.name as MetricType];
          return (
            <p key={entry.name} className="text-sm text-neutral-600">
              <span style={{ color: entry.color }}>{config?.label || entry.name}:</span>{' '}
              <span className="font-semibold">{config?.format(entry.value) || entry.value}</span>
            </p>
          );
        })}
      </div>
    );
  }
  return null;
}

const periodOptions = [
  { value: 6, label: '6M' },
  { value: 12, label: '1Y' },
  { value: 24, label: '2Y' },
];

export function MarketTrendsWidget({
  className,
  periodMonths: initialPeriod = 12,
  chartType = 'area',
  height = 350,
  showPeriodSelector = true,
}: MarketTrendsWidgetProps) {
  const [periodMonths, setPeriodMonths] = useState(initialPeriod);
  const [selectedMetric, setSelectedMetric] = useState<MetricType>('rentGrowth');
  const { data, isLoading, error, refetch } = useMarketTrends(periodMonths);

  const currentMetric = metricConfigs[selectedMetric];

  if (isLoading) {
    return (
      <Card className={cn('p-6', className)}>
        <div className="flex items-center justify-between mb-6">
          <Skeleton className="h-6 w-36" />
          <div className="flex gap-2">
            {[1, 2, 3].map(i => (
              <Skeleton key={i} className="h-9 w-24" />
            ))}
          </div>
        </div>
        <Skeleton className="w-full" style={{ height: `${height}px` }} />
        <div className="mt-4 flex items-center justify-center gap-8">
          {[1, 2, 3].map(i => (
            <div key={i} className="flex items-center gap-2">
              <Skeleton className="h-3 w-3 rounded-full" />
              <Skeleton className="h-4 w-20" />
            </div>
          ))}
        </div>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <div className={className}>
        <ErrorState
          title="Failed to load market trends"
          description="Unable to fetch trend data. Please try again."
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  const chartData = data.trends.map(trend => ({
    month: trend.month,
    rentGrowth: trend.rentGrowth,
    occupancy: trend.occupancy,
    capRate: trend.capRate,
  }));

  const ChartComponent = chartType === 'area' ? AreaChart : LineChart;

  return (
    <Card className={cn('p-6', className)}>
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <h3 className="text-card-title text-primary-500">Market Trends</h3>
        <div className="flex flex-wrap gap-2">
          {/* Metric selector */}
          {Object.entries(metricConfigs).map(([key, config]) => (
            <button
              key={key}
              onClick={() => setSelectedMetric(key as MetricType)}
              className={cn(
                'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                selectedMetric === key
                  ? 'bg-primary-500 text-white'
                  : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'
              )}
            >
              {config.label}
            </button>
          ))}

          {/* Period selector */}
          {showPeriodSelector && (
            <div className="flex gap-1 ml-2 pl-2 border-l border-neutral-200">
              {periodOptions.map(option => (
                <button
                  key={option.value}
                  onClick={() => setPeriodMonths(option.value)}
                  className={cn(
                    'px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                    periodMonths === option.value
                      ? 'bg-neutral-800 text-white'
                      : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'
                  )}
                >
                  {option.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <ChartComponent data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={`gradient-${selectedMetric}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={currentMetric.color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={currentMetric.color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="month"
            tick={{ fill: '#6b7280', fontSize: 12 }}
            tickLine={{ stroke: '#e5e7eb' }}
          />
          <YAxis
            tick={{ fill: '#6b7280', fontSize: 12 }}
            tickLine={{ stroke: '#e5e7eb' }}
            tickFormatter={(value) => currentMetric.format(value)}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ paddingTop: '20px' }}
            formatter={(value) => metricConfigs[value as MetricType]?.label || value}
          />
          {chartType === 'area' ? (
            <Area
              type="monotone"
              dataKey={selectedMetric}
              stroke={currentMetric.color}
              strokeWidth={2}
              fill={`url(#gradient-${selectedMetric})`}
              animationDuration={500}
            />
          ) : (
            <Line
              type="monotone"
              dataKey={selectedMetric}
              stroke={currentMetric.color}
              strokeWidth={2}
              dot={{ fill: currentMetric.color, r: 4 }}
              activeDot={{ r: 6 }}
              animationDuration={500}
            />
          )}
        </ChartComponent>
      </ResponsiveContainer>

      <div className="mt-4 flex items-center justify-center gap-8 text-sm">
        <div className="flex items-center gap-2">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: currentMetric.color }}
          />
          <span className="text-neutral-600">{currentMetric.label}</span>
        </div>
        <div className="text-neutral-500">
          Last {periodMonths} months • Phoenix MSA
        </div>
      </div>
    </Card>
  );
}
