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
} from 'recharts';
import type { DeliveryTimelineItem } from '../types';

interface DeliveryTimelineProps {
  data: DeliveryTimelineItem[];
  isLoading: boolean;
}

const numFmt = new Intl.NumberFormat('en-US');

export function DeliveryTimeline({ data, isLoading }: DeliveryTimelineProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Delivery Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[350px] w-full" />
        </CardContent>
      </Card>
    );
  }

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Delivery Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-center text-muted-foreground py-8">No delivery data available</p>
        </CardContent>
      </Card>
    );
  }

  const totalUnits = data.reduce((sum, d) => sum + d.totalUnits, 0);
  const totalProjects = data.reduce((sum, d) => sum + d.projectCount, 0);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle>Delivery Timeline (3-Year Horizon)</CardTitle>
        <span className="text-sm text-muted-foreground">
          {numFmt.format(totalUnits)} units across {totalProjects} projects
        </span>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={data} margin={{ top: 10, right: 20, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="quarter"
              tick={{ fontSize: 12 }}
              interval={0}
              angle={-45}
              textAnchor="end"
              height={60}
            />
            <YAxis tickFormatter={(v) => numFmt.format(v)} />
            <Tooltip
              formatter={(value: number, name: string) => [
                numFmt.format(value),
                name === 'totalUnits' ? 'Units' : 'Projects',
              ]}
              labelFormatter={(label) => `Delivery: ${label}`}
            />
            <Bar dataKey="totalUnits" name="Units" fill="#3b82f6" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
