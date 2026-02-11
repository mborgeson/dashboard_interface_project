import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
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
import type { PipelineFunnelItem } from '../types';

interface PipelineFunnelProps {
  data: PipelineFunnelItem[];
  isLoading: boolean;
}

const STATUS_LABELS: Record<string, string> = {
  proposed: 'Proposed',
  final_planning: 'Final Planning',
  permitted: 'Permitted',
  under_construction: 'Under Constr.',
  delivered: 'Delivered',
};

const STATUS_COLORS: Record<string, string> = {
  proposed: '#9ca3af',
  final_planning: '#eab308',
  permitted: '#f97316',
  under_construction: '#ef4444',
  delivered: '#22c55e',
};

const numFmt = new Intl.NumberFormat('en-US');

export function PipelineFunnel({ data, isLoading }: PipelineFunnelProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Pipeline Funnel</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[300px] w-full" />
        </CardContent>
      </Card>
    );
  }

  const chartData = data.map((d) => ({
    ...d,
    label: STATUS_LABELS[d.status] ?? d.status,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline Funnel — Units by Stage</CardTitle>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="text-center text-muted-foreground py-8">No data available</p>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData} layout="vertical" margin={{ left: 20, right: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" tickFormatter={(v) => numFmt.format(v)} />
              <YAxis type="category" dataKey="label" width={110} />
              <Tooltip
                formatter={(value: number) => [numFmt.format(value), 'Units']}
                labelFormatter={(label) => `Stage: ${label}`}
              />
              <Bar dataKey="totalUnits" name="Units">
                {chartData.map((entry) => (
                  <Cell
                    key={entry.status}
                    fill={STATUS_COLORS[entry.status] ?? '#6b7280'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
