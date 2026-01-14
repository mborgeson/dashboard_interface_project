import { useState, useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { ErrorState } from '@/components/ui/error-state';
import { Skeleton } from '@/components/ui/skeleton';
import { useSubmarkets } from '@/hooks/api/useMarketData';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { cn } from '@/lib/utils';
import type { SubmarketMetrics } from '@/types/market';

interface SubmarketComparisonWidgetProps {
  className?: string;
  showChart?: boolean;
  showTable?: boolean;
  limit?: number;
}

type ComparisonMetric = 'avgRent' | 'rentGrowth' | 'occupancy' | 'capRate';

interface TooltipPayload {
  payload: { name: string };
  value: number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayload[];
  metricLabel: string;
  metricFormat: (v: number) => string;
}

function CustomTooltip({ active, payload, metricLabel, metricFormat }: CustomTooltipProps) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white p-3 border border-neutral-200 rounded-lg shadow-lg">
        <p className="text-sm font-semibold text-neutral-900">{payload[0].payload.name}</p>
        <p className="text-sm text-neutral-600 mt-1">
          {metricLabel}: <span className="font-semibold">{metricFormat(payload[0].value)}</span>
        </p>
      </div>
    );
  }
  return null;
}

const metrics = [
  { key: 'avgRent' as ComparisonMetric, label: 'Avg Rent', format: (v: number) => `$${v.toLocaleString()}` },
  { key: 'rentGrowth' as ComparisonMetric, label: 'Rent Growth', format: (v: number) => `${(v * 100).toFixed(1)}%` },
  { key: 'occupancy' as ComparisonMetric, label: 'Occupancy', format: (v: number) => `${(v * 100).toFixed(1)}%` },
  { key: 'capRate' as ComparisonMetric, label: 'Cap Rate', format: (v: number) => `${(v * 100).toFixed(2)}%` },
];

// Color scale based on performance
function getBarColor(index: number, total: number) {
  const colors = [
    '#10b981', // Green for best
    '#34d399',
    '#6ee7b7',
    '#fbbf24', // Yellow for middle
    '#fb923c',
    '#f87171', // Red for worst
  ];

  const colorIndex = Math.floor((index / total) * colors.length);
  return colors[Math.min(colorIndex, colors.length - 1)];
}

export function SubmarketComparisonWidget({
  className,
  showChart = true,
  showTable = true,
  limit,
}: SubmarketComparisonWidgetProps) {
  const { data, isLoading, error, refetch } = useSubmarkets();
  const [selectedMetric, setSelectedMetric] = useState<ComparisonMetric>('avgRent');

  const currentMetric = metrics.find(m => m.key === selectedMetric) || metrics[0];

  const sourceSubmarkets = data?.submarkets;
  const submarkets = useMemo(() => {
    if (!sourceSubmarkets) return [];
    const items = [...sourceSubmarkets];
    return limit ? items.slice(0, limit) : items;
  }, [sourceSubmarkets, limit]);

  const chartData = useMemo(() => {
    return submarkets.map((submarket: SubmarketMetrics) => ({
      name: submarket.name,
      value: submarket[selectedMetric],
    })).sort((a, b) => b.value - a.value);
  }, [submarkets, selectedMetric]);

  if (isLoading) {
    return (
      <Card className={cn('p-6', className)}>
        <div className="flex items-center justify-between mb-6">
          <Skeleton className="h-6 w-48" />
          <div className="flex gap-2">
            {[1, 2, 3, 4].map(i => (
              <Skeleton key={i} className="h-9 w-24" />
            ))}
          </div>
        </div>
        <Skeleton className="h-[350px] w-full mb-6" />
        <div className="space-y-3">
          <div className="flex gap-4 border-b pb-3">
            {[1, 2, 3, 4, 5, 6].map(i => (
              <Skeleton key={i} className="h-4 flex-1" />
            ))}
          </div>
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="flex gap-4">
              {[1, 2, 3, 4, 5, 6].map(j => (
                <Skeleton key={j} className="h-8 flex-1" />
              ))}
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
          title="Failed to load submarket data"
          description="Unable to fetch submarket metrics. Please try again."
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  return (
    <Card className={cn('p-6', className)}>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-card-title text-primary-500">Submarket Comparison</h3>
        <div className="flex gap-2">
          {metrics.map(metric => (
            <button
              key={metric.key}
              onClick={() => setSelectedMetric(metric.key)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                selectedMetric === metric.key
                  ? 'bg-primary-500 text-white'
                  : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'
              )}
            >
              {metric.label}
            </button>
          ))}
        </div>
      </div>

      {showChart && (
        <ResponsiveContainer width="100%" height={350}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={true} vertical={false} />
            <XAxis
              type="number"
              tick={{ fill: '#6b7280', fontSize: 12 }}
              tickLine={{ stroke: '#e5e7eb' }}
              tickFormatter={(value) => currentMetric.format(value)}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fill: '#6b7280', fontSize: 12 }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<CustomTooltip metricLabel={currentMetric.label} metricFormat={currentMetric.format} />} />
            <Bar dataKey="value" radius={[0, 4, 4, 0]}>
              {chartData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={getBarColor(index, chartData.length)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}

      {showTable && (
        <div className={cn('overflow-x-auto', showChart && 'mt-6')}>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-200">
                <th className="text-left py-2 px-4 font-semibold text-neutral-700">Submarket</th>
                <th className="text-right py-2 px-4 font-semibold text-neutral-700">Avg Rent</th>
                <th className="text-right py-2 px-4 font-semibold text-neutral-700">Rent Growth</th>
                <th className="text-right py-2 px-4 font-semibold text-neutral-700">Occupancy</th>
                <th className="text-right py-2 px-4 font-semibold text-neutral-700">Cap Rate</th>
                <th className="text-right py-2 px-4 font-semibold text-neutral-700">Inventory</th>
              </tr>
            </thead>
            <tbody>
              {submarkets.sort((a, b) => b.avgRent - a.avgRent).map((submarket: SubmarketMetrics, index: number) => (
                <tr key={submarket.name} className={index % 2 === 0 ? 'bg-neutral-50' : ''}>
                  <td className="py-2 px-4 font-medium text-neutral-900">{submarket.name}</td>
                  <td className="py-2 px-4 text-right text-neutral-600">${submarket.avgRent.toLocaleString()}</td>
                  <td className="py-2 px-4 text-right text-green-600 font-medium">
                    {(submarket.rentGrowth * 100).toFixed(1)}%
                  </td>
                  <td className="py-2 px-4 text-right text-neutral-600">
                    {(submarket.occupancy * 100).toFixed(1)}%
                  </td>
                  <td className="py-2 px-4 text-right text-neutral-600">
                    {(submarket.capRate * 100).toFixed(2)}%
                  </td>
                  <td className="py-2 px-4 text-right text-neutral-600">
                    {submarket.inventory.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Summary stats */}
      <div className="mt-6 pt-4 border-t border-neutral-200">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div>
            <p className="text-xs text-neutral-500">Total Inventory</p>
            <p className="text-lg font-bold text-primary-500">
              {data.totalInventory.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-xs text-neutral-500">Net Absorption</p>
            <p className="text-lg font-bold text-primary-500">
              {data.totalAbsorption.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-xs text-neutral-500">Avg Occupancy</p>
            <p className="text-lg font-bold text-primary-500">
              {(data.averageOccupancy * 100).toFixed(1)}%
            </p>
          </div>
          <div>
            <p className="text-xs text-neutral-500">Avg Rent Growth</p>
            <p className="text-lg font-bold text-green-600">
              +{(data.averageRentGrowth * 100).toFixed(1)}%
            </p>
          </div>
        </div>
      </div>
    </Card>
  );
}
