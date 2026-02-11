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
import type { ClassificationBreakdownItem } from '../types';

interface ClassificationBreakdownProps {
  data: ClassificationBreakdownItem[];
  isLoading: boolean;
}

const numFmt = new Intl.NumberFormat('en-US');

const CLASSIFICATION_LABELS: Record<string, string> = {
  CONV_MR: 'Conventional/Market-Rate',
  CONV_CONDO: 'Conventional/Condo',
  BTR: 'Build-to-Rent',
  LIHTC: 'LIHTC (Affordable)',
  AGE_55: 'Age-Restricted (55+)',
  WORKFORCE: 'Workforce Housing',
  MIXED_USE: 'Mixed-Use',
  CONVERSION: 'Conversion',
};

export function ClassificationBreakdown({ data, isLoading }: ClassificationBreakdownProps) {
  // Map raw classification codes to human-readable labels for chart display
  const chartData = data.map((item) => ({
    ...item,
    classification: CLASSIFICATION_LABELS[item.classification] ?? item.classification,
  }));
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Classification Breakdown</CardTitle>
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
          <CardTitle>Classification Breakdown</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-center text-muted-foreground py-8">No data available</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Units by Classification Type</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} layout="vertical" margin={{ left: 20, right: 20 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" tickFormatter={(v) => numFmt.format(v)} />
            <YAxis type="category" dataKey="classification" width={180} />
            <Tooltip
              formatter={(value: number) => [numFmt.format(value), 'Units']}
            />
            <Bar dataKey="totalUnits" name="Total Units" fill="#3b82f6" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
