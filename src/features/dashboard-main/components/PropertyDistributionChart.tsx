import { useMemo } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from 'recharts';
import { mockProperties } from '@/data/mockProperties';
import { formatCurrency, formatPercent } from '@/lib/utils/formatters';

type DistributionType = 'class' | 'submarket';

interface PropertyDistributionChartProps {
  type?: DistributionType;
}

interface ChartDataItem {
  name: string;
  value: number;
  count: number;
  color: string;
}

const CLASS_COLORS = {
  'Class A': '#2A3F54', // primary-500
  'Class B': '#E74C3C', // accent-500
  'Class C': '#10b981', // green-500
};

const SUBMARKET_COLORS = {
  Scottsdale: '#2A3F54',
  Tempe: '#E74C3C',
  Mesa: '#10b981',
  Gilbert: '#f59e0b',
  Chandler: '#8b5cf6',
  'Phoenix Central': '#ec4899',
};

export function PropertyDistributionChart({ type = 'class' }: PropertyDistributionChartProps) {
  const chartData = useMemo<ChartDataItem[]>(() => {
    if (type === 'class') {
      // Distribution by property class
      const classCounts: Record<string, { value: number; count: number }> = {};

      mockProperties.forEach((property) => {
        const className = `Class ${property.propertyDetails.propertyClass}`;
        if (!classCounts[className]) {
          classCounts[className] = { value: 0, count: 0 };
        }
        classCounts[className].value += property.valuation.currentValue;
        classCounts[className].count += 1;
      });

      return Object.entries(classCounts).map(([name, data]) => ({
        name,
        value: data.value,
        count: data.count,
        color: CLASS_COLORS[name as keyof typeof CLASS_COLORS] || '#6b7280',
      }));
    } else {
      // Distribution by submarket
      const submarketCounts: Record<string, { value: number; count: number }> = {};

      mockProperties.forEach((property) => {
        const submarket = property.address.submarket;
        if (!submarketCounts[submarket]) {
          submarketCounts[submarket] = { value: 0, count: 0 };
        }
        submarketCounts[submarket].value += property.valuation.currentValue;
        submarketCounts[submarket].count += 1;
      });

      return Object.entries(submarketCounts)
        .map(([name, data]) => ({
          name,
          value: data.value,
          count: data.count,
          color: SUBMARKET_COLORS[name as keyof typeof SUBMARKET_COLORS] || '#6b7280',
        }))
        .sort((a, b) => b.value - a.value);
    }
  }, [type]);

  const totalValue = useMemo(
    () => chartData.reduce((sum, item) => sum + item.value, 0),
    [chartData]
  );

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const percentage = (data.value / totalValue) * 100;

      return (
        <div className="bg-white p-4 border border-neutral-200 rounded-lg shadow-lg">
          <p className="text-sm font-semibold text-neutral-900 mb-2">{data.name}</p>
          <div className="space-y-1">
            <p className="text-sm text-neutral-700">
              Value: {formatCurrency(data.value, true)}
            </p>
            <p className="text-sm text-neutral-700">
              Properties: {data.count}
            </p>
            <p className="text-sm text-neutral-700">
              Share: {formatPercent(percentage / 100)}
            </p>
          </div>
        </div>
      );
    }
    return null;
  };

  const CustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }: any) => {
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    if (percent < 0.05) return null; // Don't show label for small slices

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor={x > cx ? 'start' : 'end'}
        dominantBaseline="central"
        className="text-sm font-semibold"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  const CustomLegend = ({ payload }: any) => {
    return (
      <div className="flex flex-wrap justify-center gap-4 mt-4">
        {payload.map((entry: any, index: number) => {
          const dataItem = chartData[index];
          const percentage = (dataItem.value / totalValue) * 100;

          return (
            <div key={`legend-${index}`} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-sm text-neutral-700">
                {entry.value} ({dataItem.count}) - {percentage.toFixed(1)}%
              </span>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="w-full h-[400px]">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={CustomLabel}
            outerRadius={120}
            innerRadius={60}
            fill="#8884d8"
            dataKey="value"
            paddingAngle={2}
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend content={<CustomLegend />} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
