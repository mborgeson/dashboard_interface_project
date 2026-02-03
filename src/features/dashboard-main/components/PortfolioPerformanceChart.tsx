import { useMemo } from 'react';
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
import { formatCurrency, formatPercent } from '@/lib/utils/formatters';
import type { Property } from '@/types';

interface PortfolioPerformanceChartProps {
  properties: Property[];
}

interface PropertyMetric {
  name: string;
  noi: number;
  occupancy: number;
  capRate: number;
}

interface TooltipPayload {
  payload: PropertyMetric;
  value: number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayload[];
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-white p-4 border border-neutral-200 rounded-lg shadow-lg">
        <p className="text-sm font-semibold text-neutral-900 mb-2">
          {data.name}
        </p>
        <div className="space-y-1">
          <p className="text-sm text-neutral-700">
            Annual NOI: {formatCurrency(data.noi, true)}
          </p>
          <p className="text-sm text-neutral-700">
            Occupancy: {formatPercent(data.occupancy)}
          </p>
          <p className="text-sm text-neutral-700">
            Cap Rate: {formatPercent(data.capRate)}
          </p>
        </div>
      </div>
    );
  }
  return null;
}

export function PortfolioPerformanceChart({ properties }: PortfolioPerformanceChartProps) {
  const chartData = useMemo<PropertyMetric[]>(() => {
    if (properties.length === 0) return [];

    return properties
      .filter(p => p.operations.noi > 0)
      .sort((a, b) => b.operations.noi - a.operations.noi)
      .slice(0, 10)
      .map(p => ({
        name: p.name.length > 20 ? p.name.substring(0, 18) + '...' : p.name,
        noi: p.operations.noi,
        occupancy: p.operations.occupancy,
        capRate: p.valuation.capRate,
      }));
  }, [properties]);

  if (chartData.length === 0) {
    return (
      <div className="w-full h-[400px] flex items-center justify-center text-neutral-500">
        No data available
      </div>
    );
  }

  return (
    <div className="w-full h-[400px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 120, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={true} vertical={false} />
          <XAxis
            type="number"
            stroke="#6b7280"
            style={{ fontSize: '0.75rem' }}
            tickFormatter={(value) => formatCurrency(value, true)}
          />
          <YAxis
            type="category"
            dataKey="name"
            stroke="#6b7280"
            style={{ fontSize: '0.75rem' }}
            tickLine={false}
            axisLine={false}
            width={115}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="noi" name="Annual NOI" radius={[0, 4, 4, 0]}>
            {chartData.map((_, index) => (
              <Cell
                key={`cell-${index}`}
                fill={index < 3 ? '#10b981' : index < 7 ? '#3b82f6' : '#6b7280'}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="text-xs text-neutral-500 text-center mt-2">
        Top properties by annual NOI from extraction data
      </p>
    </div>
  );
}
