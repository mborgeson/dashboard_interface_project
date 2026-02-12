import { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ChartSkeleton } from '@/components/ui/skeleton';
import type { TimeSeriesDataPoint } from '../types';

const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
});

const compactCurrencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  notation: 'compact',
  maximumFractionDigits: 1,
});

interface TimeSeriesTrendsProps {
  data: TimeSeriesDataPoint[];
  isLoading: boolean;
}

type Granularity = 'month' | 'quarter' | 'year';

/** Aggregate data points by quarter or year from monthly data */
function aggregateData(
  data: TimeSeriesDataPoint[],
  granularity: Granularity
): TimeSeriesDataPoint[] {
  if (granularity === 'month') return data;

  const groups = new Map<string, TimeSeriesDataPoint[]>();

  for (const point of data) {
    let key: string;
    if (granularity === 'quarter') {
      const [year, month] = point.period.split('-');
      const q = Math.ceil(Number(month) / 3);
      key = `${year}-Q${q}`;
    } else {
      key = point.period.split('-')[0];
    }

    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(point);
  }

  return Array.from(groups.entries()).map(([period, points]) => ({
    period,
    count: points.reduce((s, p) => s + p.count, 0),
    totalVolume: points.reduce((s, p) => s + p.totalVolume, 0),
    avgPricePerUnit:
      points.reduce((s, p) => s + (p.avgPricePerUnit ?? 0), 0) / points.length,
  }));
}

export function TimeSeriesTrends({ data, isLoading }: TimeSeriesTrendsProps) {
  const [granularity, setGranularity] = useState<Granularity>('year');

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Time-Series Trends</CardTitle>
        </CardHeader>
        <CardContent>
          <ChartSkeleton />
        </CardContent>
      </Card>
    );
  }

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Time-Series Trends</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">
            No time-series data available for the current filters.
          </p>
        </CardContent>
      </Card>
    );
  }

  const chartData = aggregateData(data, granularity);

  const granularityOptions: { value: Granularity; label: string }[] = [
    { value: 'month', label: 'Monthly' },
    { value: 'quarter', label: 'Quarterly' },
    { value: 'year', label: 'Yearly' },
  ];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle>Time-Series Trends</CardTitle>
        <div className="flex gap-1">
          {granularityOptions.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setGranularity(opt.value)}
              className={`px-3 py-1 rounded-md text-xs font-medium border transition-colors ${
                granularity === opt.value
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-neutral-700 border-neutral-300 hover:border-blue-400'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Sales Volume Chart */}
        <div>
          <h4 className="text-sm font-medium text-muted-foreground mb-2">
            Sales Volume
          </h4>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
              <XAxis
                dataKey="period"
                tick={{ fontSize: 11 }}
                interval="preserveStartEnd"
              />
              <YAxis
                yAxisId="count"
                orientation="left"
                tick={{ fontSize: 11 }}
                label={{
                  value: 'Transactions',
                  angle: -90,
                  position: 'insideLeft',
                  style: { fontSize: 11 },
                }}
              />
              <YAxis
                yAxisId="volume"
                orientation="right"
                tickFormatter={(v: number) => compactCurrencyFormatter.format(v)}
                tick={{ fontSize: 11 }}
                label={{
                  value: 'Total Volume',
                  angle: 90,
                  position: 'insideRight',
                  style: { fontSize: 11 },
                }}
              />
              <Tooltip
                formatter={(value: number, name: string) => {
                  if (name === 'Total Volume')
                    return currencyFormatter.format(value);
                  return value.toLocaleString();
                }}
              />
              <Legend />
              <Line
                yAxisId="count"
                type="monotone"
                dataKey="count"
                name="Transactions"
                stroke="#2563eb"
                strokeWidth={2}
                dot={{ r: 2 }}
                activeDot={{ r: 4 }}
              />
              <Line
                yAxisId="volume"
                type="monotone"
                dataKey="totalVolume"
                name="Total Volume"
                stroke="#16a34a"
                strokeWidth={2}
                dot={{ r: 2 }}
                activeDot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Average Price Per Unit Chart */}
        <div>
          <h4 className="text-sm font-medium text-muted-foreground mb-2">
            Average Price Per Unit
          </h4>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
              <XAxis
                dataKey="period"
                tick={{ fontSize: 11 }}
                interval="preserveStartEnd"
              />
              <YAxis
                tickFormatter={(v: number) => compactCurrencyFormatter.format(v)}
                tick={{ fontSize: 11 }}
              />
              <Tooltip
                formatter={(value: number) => currencyFormatter.format(value)}
              />
              <Line
                type="monotone"
                dataKey="avgPricePerUnit"
                name="Avg $/Unit"
                stroke="#9333ea"
                strokeWidth={2}
                dot={{ r: 2 }}
                activeDot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
