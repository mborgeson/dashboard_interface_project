import { useState } from 'react';
import { Card } from '@/components/ui/card';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { MarketTrend } from '@/types/market';

interface MarketTrendsChartProps {
  trends: Array<MarketTrend & { rentGrowthPct: number; occupancyPct: number; capRatePct: number }>;
  regionLabel?: string;
}

type MetricType = 'rentGrowth' | 'occupancy' | 'capRate';

interface TooltipPayload {
  payload: { month: string };
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
        <p className="text-sm font-medium text-neutral-900">{payload[0].payload.month}</p>
        <p className="text-sm text-neutral-600 mt-1">
          {metricLabel}: <span className="font-semibold">{metricFormat(payload[0].value)}</span>
        </p>
      </div>
    );
  }
  return null;
}

export function MarketTrendsChart({ trends, regionLabel = 'Phoenix MSA' }: MarketTrendsChartProps) {
  const [selectedMetric, setSelectedMetric] = useState<MetricType>('rentGrowth');

  const metrics = [
    { key: 'rentGrowth' as MetricType, label: 'Rent Growth', color: '#10b981', format: (v: number) => `${v.toFixed(1)}%` },
    { key: 'occupancy' as MetricType, label: 'Occupancy', color: '#3b82f6', format: (v: number) => `${v.toFixed(1)}%` },
    { key: 'capRate' as MetricType, label: 'Cap Rate', color: '#8b5cf6', format: (v: number) => `${v.toFixed(2)}%` },
  ];

  const currentMetric = metrics.find(m => m.key === selectedMetric) || metrics[0];

  const chartData = trends.map(trend => ({
    month: trend.month,
    value: selectedMetric === 'rentGrowth' ? trend.rentGrowthPct :
           selectedMetric === 'occupancy' ? trend.occupancyPct :
           trend.capRatePct,
  }));

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-card-title text-primary-500">Market Trends</h3>
        <div className="flex gap-2">
          {metrics.map(metric => (
            <button
              key={metric.key}
              onClick={() => setSelectedMetric(metric.key)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                selectedMetric === metric.key
                  ? 'bg-primary-500 text-white'
                  : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'
              }`}
            >
              {metric.label}
            </button>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={350}>
        <AreaChart
          data={chartData}
          margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id={`color-${selectedMetric}`} x1="0" y1="0" x2="0" y2="1">
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
          <Tooltip content={<CustomTooltip metricLabel={currentMetric.label} metricFormat={currentMetric.format} />} />
          <Area
            type="monotone"
            dataKey="value"
            stroke={currentMetric.color}
            strokeWidth={2}
            fill={`url(#color-${selectedMetric})`}
            animationDuration={500}
          />
        </AreaChart>
      </ResponsiveContainer>

      <div className="mt-4 flex items-center justify-center gap-8 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: currentMetric.color }}></div>
          <span className="text-neutral-600">{currentMetric.label}</span>
        </div>
        <div className="text-neutral-500">
          Last 12 months &bull; {regionLabel}
        </div>
      </div>
    </Card>
  );
}
