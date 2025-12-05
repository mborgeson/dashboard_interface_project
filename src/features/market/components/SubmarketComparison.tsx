import { useState } from 'react';
import { Card } from '@/components/ui/card';
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
import type { SubmarketMetrics } from '@/types/market';

interface SubmarketComparisonProps {
  submarkets: Array<SubmarketMetrics & { rentGrowthPct: number; occupancyPct: number; capRatePct: number }>;
}

type ComparisonMetric = 'avgRent' | 'rentGrowth' | 'occupancy' | 'capRate';

export function SubmarketComparison({ submarkets }: SubmarketComparisonProps) {
  const [selectedMetric, setSelectedMetric] = useState<ComparisonMetric>('avgRent');

  const metrics = [
    { key: 'avgRent' as ComparisonMetric, label: 'Avg Rent', format: (v: number) => `$${v.toLocaleString()}` },
    { key: 'rentGrowth' as ComparisonMetric, label: 'Rent Growth', format: (v: number) => `${v.toFixed(1)}%` },
    { key: 'occupancy' as ComparisonMetric, label: 'Occupancy', format: (v: number) => `${v.toFixed(1)}%` },
    { key: 'capRate' as ComparisonMetric, label: 'Cap Rate', format: (v: number) => `${v.toFixed(2)}%` },
  ];

  const currentMetric = metrics.find(m => m.key === selectedMetric) || metrics[0];

  const chartData = submarkets.map(submarket => ({
    name: submarket.name,
    value: selectedMetric === 'avgRent' ? submarket.avgRent :
           selectedMetric === 'rentGrowth' ? submarket.rentGrowthPct :
           selectedMetric === 'occupancy' ? submarket.occupancyPct :
           submarket.capRatePct,
  })).sort((a, b) => b.value - a.value);

  // Color scale based on performance
  const getBarColor = (index: number, total: number) => {
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
  };

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border border-neutral-200 rounded-lg shadow-lg">
          <p className="text-sm font-semibold text-neutral-900">{payload[0].payload.name}</p>
          <p className="text-sm text-neutral-600 mt-1">
            {currentMetric.label}: <span className="font-semibold">{currentMetric.format(payload[0].value)}</span>
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-card-title text-primary-500">Submarket Comparison</h3>
        <div className="flex gap-2">
          {metrics.map(metric => (
            <button
              key={metric.key}
              onClick={() => setSelectedMetric(metric.key)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
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
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getBarColor(index, chartData.length)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="mt-6 overflow-x-auto">
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
            {submarkets.sort((a, b) => b.avgRent - a.avgRent).map((submarket, index) => (
              <tr key={submarket.name} className={index % 2 === 0 ? 'bg-neutral-50' : ''}>
                <td className="py-2 px-4 font-medium text-neutral-900">{submarket.name}</td>
                <td className="py-2 px-4 text-right text-neutral-600">${submarket.avgRent.toLocaleString()}</td>
                <td className="py-2 px-4 text-right text-green-600 font-medium">{submarket.rentGrowthPct.toFixed(1)}%</td>
                <td className="py-2 px-4 text-right text-neutral-600">{submarket.occupancyPct.toFixed(1)}%</td>
                <td className="py-2 px-4 text-right text-neutral-600">{submarket.capRatePct.toFixed(2)}%</td>
                <td className="py-2 px-4 text-right text-neutral-600">{submarket.inventory.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
