import { useMemo } from 'react';
import { Card } from '@/components/ui/card';
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
  '#2A3F54', // Primary navy
  '#E74C3C', // Accent red
  '#3498db', // Blue
  '#27ae60', // Green
  '#9b59b6', // Purple
  '#f39c12', // Orange
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

export function ComparisonCharts({
  deals,
  chartType = 'both',
}: ComparisonChartsProps) {
  // Prepare bar chart data
  const barChartData = useMemo((): BarChartData[] => {
    const metrics = [
      {
        key: 'capRate',
        label: 'Cap Rate (%)',
        getValue: (d: DealForComparison) => d.capRate,
      },
      {
        key: 'projectedIrr',
        label: 'IRR (%)',
        getValue: (d: DealForComparison) => (d.projectedIrr ?? 0) * 100,
      },
      {
        key: 'cashOnCash',
        label: 'Cash-on-Cash (%)',
        getValue: (d: DealForComparison) => (d.cashOnCash ?? 0) * 100,
      },
      {
        key: 'equityMultiple',
        label: 'Equity Multiple (x)',
        getValue: (d: DealForComparison) => d.equityMultiple ?? 0,
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

    // Define metrics with their normalization ranges
    const metrics = [
      {
        key: 'capRate',
        label: 'Cap Rate',
        getValue: (d: DealForComparison) => d.capRate,
        normalize: (v: number, min: number, max: number) =>
          max === min ? 50 : ((v - min) / (max - min)) * 100,
      },
      {
        key: 'projectedIrr',
        label: 'IRR',
        getValue: (d: DealForComparison) => (d.projectedIrr ?? 0) * 100,
        normalize: (v: number, min: number, max: number) =>
          max === min ? 50 : ((v - min) / (max - min)) * 100,
      },
      {
        key: 'cashOnCash',
        label: 'Cash-on-Cash',
        getValue: (d: DealForComparison) => (d.cashOnCash ?? 0) * 100,
        normalize: (v: number, min: number, max: number) =>
          max === min ? 50 : ((v - min) / (max - min)) * 100,
      },
      {
        key: 'equityMultiple',
        label: 'Equity Multiple',
        getValue: (d: DealForComparison) => d.equityMultiple ?? 0,
        normalize: (v: number, min: number, max: number) =>
          max === min ? 50 : ((v - min) / (max - min)) * 100,
      },
      {
        key: 'occupancyRate',
        label: 'Occupancy',
        getValue: (d: DealForComparison) => (d.occupancyRate ?? 0) * 100,
        normalize: (v: number, min: number, max: number) =>
          max === min ? 50 : ((v - min) / (max - min)) * 100,
      },
      {
        key: 'units',
        label: 'Units',
        getValue: (d: DealForComparison) => d.units,
        normalize: (v: number, min: number, max: number) =>
          max === min ? 50 : ((v - min) / (max - min)) * 100,
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
        dataPoint[deal.propertyName] = Number(
          metric.normalize(rawValue, min, max).toFixed(1)
        );
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
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-primary-500 mb-4">
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
              <YAxis stroke="#6b7280" style={{ fontSize: '12px' }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#fff',
                  border: '1px solid #e5e7eb',
                  borderRadius: '6px',
                  fontSize: '12px',
                }}
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
        </Card>
      )}

      {/* Radar Chart - Overall Comparison */}
      {showRadar && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-primary-500 mb-4">
            Overall Deal Profile Comparison
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
                tick={{ fill: '#6b7280', fontSize: 10 }}
                tickFormatter={(value) => `${value}`}
              />
              {deals.map((deal, index) => (
                <Radar
                  key={deal.id}
                  name={deal.propertyName}
                  dataKey={deal.propertyName}
                  stroke={DEAL_COLORS[index % DEAL_COLORS.length]}
                  fill={DEAL_COLORS[index % DEAL_COLORS.length]}
                  fillOpacity={0.2}
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
                  borderRadius: '6px',
                  fontSize: '12px',
                }}
                formatter={(value: number) => `${value.toFixed(1)} (normalized)`}
              />
            </RadarChart>
          </ResponsiveContainer>
          <p className="text-xs text-neutral-500 text-center mt-2">
            Values normalized 0-100 for comparison. Higher is better for all metrics.
          </p>
        </Card>
      )}
    </div>
  );
}
