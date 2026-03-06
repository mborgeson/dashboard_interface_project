import { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts';
import type { DealForComparison } from '@/hooks/api/useDealComparison';

interface ComparisonChartsProps {
  deals: DealForComparison[];
  chartType?: 'bar' | 'radar' | 'both';
}

// Color palette for deals (supports up to 6 deals)
const DEAL_COLORS = [
  '#2563eb', // blue-600
  '#dc2626', // red-600
  '#16a34a', // green-600
  '#9333ea', // purple-600
  '#ea580c', // orange-600
  '#0891b2', // cyan-600
];

interface BarChartData {
  metric: string;
  [dealName: string]: string | number;
}

interface RadarChartData {
  metric: string;
  fullMark: number;
  [dealName: string]: string | number;
}

function fmtPctTick(v: number): string {
  return `${v.toFixed(1)}%`;
}

export function ComparisonCharts({
  deals,
  chartType = 'both',
}: ComparisonChartsProps) {
  // Prepare bar chart data — real UW metrics (displayed as percentages)
  const barChartData = useMemo((): BarChartData[] => {
    const metrics = [
      {
        label: 'Cap Rate PP (T12)',
        getValue: (d: DealForComparison) => (d.t12CapOnPp ? d.t12CapOnPp * 100 : 0),
      },
      {
        label: 'Cap Rate TC (T12)',
        getValue: (d: DealForComparison) => (d.totalCostCapT12 ? d.totalCostCapT12 * 100 : 0),
      },
      {
        label: 'NOI Margin',
        getValue: (d: DealForComparison) => (d.noiMargin ? d.noiMargin * 100 : 0),
      },
      {
        label: 'Unlevered IRR',
        getValue: (d: DealForComparison) => (d.unleveredIrr ? d.unleveredIrr * 100 : 0),
      },
      {
        label: 'Levered IRR',
        getValue: (d: DealForComparison) => (d.leveredIrr ? d.leveredIrr * 100 : 0),
      },
      {
        label: 'LP IRR',
        getValue: (d: DealForComparison) => (d.lpIrr ? d.lpIrr * 100 : 0),
      },
    ];

    return metrics.map((metric) => {
      const dataPoint: BarChartData = { metric: metric.label };
      deals.forEach((deal) => {
        dataPoint[deal.propertyName] = Number(metric.getValue(deal).toFixed(2));
      });
      return dataPoint;
    });
  }, [deals]);

  // Prepare radar chart data (normalized values for comparison)
  const radarChartData = useMemo((): RadarChartData[] => {
    if (deals.length === 0) return [];

    const metrics = [
      {
        label: 'Cap Rate PP',
        getValue: (d: DealForComparison) => (d.t12CapOnPp ? d.t12CapOnPp * 100 : 0),
      },
      {
        label: 'Cap Rate TC',
        getValue: (d: DealForComparison) => (d.totalCostCapT12 ? d.totalCostCapT12 * 100 : 0),
      },
      {
        label: 'NOI Margin',
        getValue: (d: DealForComparison) => (d.noiMargin ? d.noiMargin * 100 : 0),
      },
      {
        label: 'Unlevered IRR',
        getValue: (d: DealForComparison) => (d.unleveredIrr ? d.unleveredIrr * 100 : 0),
      },
      {
        label: 'Units',
        getValue: (d: DealForComparison) => d.units ?? 0,
      },
      {
        label: 'Basis/Unit',
        getValue: (d: DealForComparison) => d.basisPerUnit ?? 0,
      },
    ];

    return metrics.map((metric) => {
      const values = deals.map((d) => metric.getValue(d));
      const min = Math.min(...values);
      const max = Math.max(...values);

      const dataPoint: RadarChartData = {
        metric: metric.label,
        fullMark: 100,
      };

      deals.forEach((deal) => {
        const rawValue = metric.getValue(deal);
        const normalized = max === min ? 50 : ((rawValue - min) / (max - min)) * 100;
        dataPoint[deal.propertyName] = Number(normalized.toFixed(1));
      });

      return dataPoint;
    });
  }, [deals]);

  // Short name helper for chart labels
  const getShortName = (name: string): string => {
    const words = name.split(' ');
    if (words.length <= 2) return name;
    return words.slice(0, 2).join(' ');
  };

  if (deals.length === 0) {
    return (
      <div className="text-center py-8 text-neutral-500">
        No deals selected for comparison
      </div>
    );
  }

  const showBar = chartType === 'bar' || chartType === 'both';
  const showRadar = chartType === 'radar' || chartType === 'both';

  return (
    <div className={`grid gap-6 ${chartType === 'both' ? 'grid-cols-1 lg:grid-cols-2' : 'grid-cols-1'}`}>
      {/* Bar Chart - Key Metrics Comparison */}
      {showBar && (
        <div className="bg-white rounded-lg border border-neutral-200 shadow-card p-6">
          <h3 className="text-base font-semibold text-neutral-900 mb-4">
            Key Metrics Comparison
          </h3>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart
              data={barChartData}
              margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="metric"
                stroke="#6b7280"
                style={{ fontSize: '11px' }}
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis
                stroke="#6b7280"
                style={{ fontSize: '12px' }}
                tickFormatter={fmtPctTick}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#fff',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  fontSize: '12px',
                  boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                }}
                formatter={(value: number) => [`${value.toFixed(2)}%`, '']}
              />
              <Legend
                wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }}
                formatter={(value) => getShortName(value)}
              />
              {deals.map((deal, index) => (
                <Bar
                  key={deal.id}
                  dataKey={deal.propertyName}
                  fill={DEAL_COLORS[index % DEAL_COLORS.length]}
                  radius={[4, 4, 0, 0]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Radar Chart - Overall Comparison */}
      {showRadar && (
        <div className="bg-white rounded-lg border border-neutral-200 shadow-card p-6">
          <h3 className="text-base font-semibold text-neutral-900 mb-4">
            Overall Deal Profile
          </h3>
          <ResponsiveContainer width="100%" height={350}>
            <RadarChart
              cx="50%"
              cy="50%"
              outerRadius="70%"
              data={radarChartData}
            >
              <PolarGrid stroke="#e5e7eb" />
              <PolarAngleAxis
                dataKey="metric"
                tick={{ fill: '#6b7280', fontSize: 11 }}
              />
              <PolarRadiusAxis
                angle={90}
                domain={[0, 100]}
                tick={{ fill: '#9ca3af', fontSize: 10 }}
                tickFormatter={(value) => `${value}`}
              />
              {deals.map((deal, index) => (
                <Radar
                  key={deal.id}
                  name={deal.propertyName}
                  dataKey={deal.propertyName}
                  stroke={DEAL_COLORS[index % DEAL_COLORS.length]}
                  fill={DEAL_COLORS[index % DEAL_COLORS.length]}
                  fillOpacity={0.15}
                  strokeWidth={2}
                />
              ))}
              <Legend
                wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }}
                formatter={(value) => getShortName(value)}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#fff',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  fontSize: '12px',
                  boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                }}
                formatter={(value: number) => `${value.toFixed(1)} (normalized)`}
              />
            </RadarChart>
          </ResponsiveContainer>
          <p className="text-xs text-neutral-500 text-center mt-2">
            Values normalized 0-100 for comparison. Higher is better for all metrics.
          </p>
        </div>
      )}
    </div>
  );
}
