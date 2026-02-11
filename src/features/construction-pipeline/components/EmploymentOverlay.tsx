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
import type { EmploymentPoint } from '../types';

interface EmploymentOverlayProps {
  data: EmploymentPoint[];
  isLoading: boolean;
}

export function EmploymentOverlay({ data, isLoading }: EmploymentOverlayProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Construction Employment</CardTitle>
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
          <CardTitle>Construction Employment</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-center text-muted-foreground py-8">
            No employment data available. Data populates after BLS fetch.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Group by series, pivot for chart
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
        <CardTitle>Construction Employment — Phoenix MSA (BLS)</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData} margin={{ left: 10, right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="period" tick={{ fontSize: 11 }} />
            <YAxis label={{ value: 'Thousands', angle: -90, position: 'insideLeft' }} />
            <Tooltip />
            <Legend />
            {seriesIds.map((sid, i) => (
              <Line
                key={sid}
                type="monotone"
                dataKey={sid}
                stroke={['#3b82f6', '#f59e0b', '#10b981'][i % 3]}
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
