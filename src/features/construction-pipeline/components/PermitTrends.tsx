import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { PermitTrendPoint } from '../types';

interface PermitTrendsProps {
  data: PermitTrendPoint[];
  isLoading: boolean;
}

const SERIES_COLORS: Record<string, string> = {
  'BLDG5O_UNITS': '#3b82f6',
  'BLDG_UNITS': '#8b5cf6',
  'BLDG5O_BLDGS': '#06b6d4',
  'PHOE004BPPRIVSA': '#f59e0b',
  'PHOE004BP1FHSA': '#ef4444',
  'BPPRIV004013': '#10b981',
};

export function PermitTrends({ data, isLoading }: PermitTrendsProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Permit Trends</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[300px] w-full" />
        </CardContent>
      </Card>
    );
  }

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Permit Trends</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-center text-muted-foreground py-8">
            No permit data available. Data populates after API fetch.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Group by series and pivot to chart-friendly format
  const seriesIds = [...new Set(data.map((d) => d.seriesId))];
  const byPeriod = new Map<string, Record<string, number>>();
  for (const d of data) {
    if (!byPeriod.has(d.period)) byPeriod.set(d.period, {});
    byPeriod.get(d.period)![d.seriesId] = d.value;
  }

  const chartData = [...byPeriod.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([period, values]) => ({ period, ...values }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Permit Trends — Census BPS + FRED</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData} margin={{ left: 10, right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="period" tick={{ fontSize: 11 }} />
            <YAxis />
            <Tooltip />
            <Legend />
            {seriesIds.map((sid) => (
              <Line
                key={sid}
                type="monotone"
                dataKey={sid}
                stroke={SERIES_COLORS[sid] ?? '#6b7280'}
                dot={false}
                strokeWidth={2}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
