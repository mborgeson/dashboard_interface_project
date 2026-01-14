import { memo, useMemo, useCallback } from 'react';
import { Card } from '@/components/ui/card';
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

interface PerformanceChartsProps {
  noiData: Array<{ month: string; noi: number }>;
  occupancyData: Array<{ month: string; occupancy: number }>;
}

// Memoized tooltip content style to prevent object recreation
const TOOLTIP_STYLE = {
  backgroundColor: '#fff',
  border: '1px solid #e5e7eb',
  borderRadius: '6px',
  fontSize: '12px',
} as const;

// Memoized chart axis style
const AXIS_STYLE = { fontSize: '12px' } as const;

export const PerformanceCharts = memo(function PerformanceCharts({ noiData, occupancyData }: PerformanceChartsProps) {
  // Memoized formatters to prevent recreation on every render
  const formatCurrency = useCallback((value: number) => {
    return `$${(value / 1000).toFixed(0)}K`;
  }, []);

  const formatPercentage = useCallback((value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  }, []);

  // Memoized tooltip formatters
  const noiTooltipFormatter = useCallback((value: number) => [formatCurrency(value), 'NOI'], [formatCurrency]);
  const occupancyTooltipFormatter = useCallback((value: number) => [formatPercentage(value), 'Occupancy'], [formatPercentage]);

  // Memoize the Y-axis domain for occupancy chart
  const occupancyDomain = useMemo(() => [0.85, 1.0] as [number, number], []);

  // Memoize chart gradient definition
  const noiGradient = useMemo(() => (
    <defs>
      <linearGradient id="noiGradient" x1="0" y1="0" x2="0" y2="1">
        <stop offset="5%" stopColor="#2A3F54" stopOpacity={0.8} />
        <stop offset="95%" stopColor="#2A3F54" stopOpacity={0.1} />
      </linearGradient>
    </defs>
  ), []);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* NOI Trend Chart */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-primary-500 mb-4">Net Operating Income Trend</h3>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={noiData}>
            {noiGradient}
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="month"
              stroke="#6b7280"
              style={AXIS_STYLE}
            />
            <YAxis
              stroke="#6b7280"
              style={AXIS_STYLE}
              tickFormatter={formatCurrency}
            />
            <Tooltip
              formatter={noiTooltipFormatter}
              contentStyle={TOOLTIP_STYLE}
            />
            <Area
              type="monotone"
              dataKey="noi"
              stroke="#2A3F54"
              strokeWidth={2}
              fill="url(#noiGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </Card>

      {/* Occupancy Trend Chart */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-primary-500 mb-4">Portfolio Occupancy Trend</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={occupancyData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="month"
              stroke="#6b7280"
              style={AXIS_STYLE}
            />
            <YAxis
              stroke="#6b7280"
              style={AXIS_STYLE}
              tickFormatter={formatPercentage}
              domain={occupancyDomain}
            />
            <Tooltip
              formatter={occupancyTooltipFormatter}
              contentStyle={TOOLTIP_STYLE}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="occupancy"
              stroke="#E74C3C"
              strokeWidth={2}
              dot={{ fill: '#E74C3C', r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </Card>
    </div>
  );
});
