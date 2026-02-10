import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ChartSkeleton } from '@/components/ui/skeleton';
import type { DistributionBucket } from '../types';

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

interface DistributionAnalysisProps {
  data: DistributionBucket[];
  isLoading: boolean;
}

export function DistributionAnalysis({
  data,
  isLoading,
}: DistributionAnalysisProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Distribution Analysis</CardTitle>
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
          <CardTitle>Distribution Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">
            No distribution data available for the current filters.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Distribution Analysis</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Transaction Count by Bucket */}
        <div>
          <h4 className="text-sm font-medium text-muted-foreground mb-2">
            Transaction Count by Category
          </h4>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 11 }}
                interval={0}
                angle={-20}
                textAnchor="end"
                height={60}
              />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip
                formatter={(value: number, name: string) => {
                  if (name === 'Transactions') return value.toLocaleString();
                  return value;
                }}
              />
              <Bar
                dataKey="count"
                name="Transactions"
                fill="#2563eb"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Price Per Unit Comparison */}
        <div>
          <h4 className="text-sm font-medium text-muted-foreground mb-2">
            Price Per Unit by Category
          </h4>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 11 }}
                interval={0}
                angle={-20}
                textAnchor="end"
                height={60}
              />
              <YAxis
                tickFormatter={(v: number) => compactCurrencyFormatter.format(v)}
                tick={{ fontSize: 11 }}
              />
              <Tooltip
                formatter={(value: number) => currencyFormatter.format(value)}
              />
              <Legend />
              <Bar
                dataKey="medianPricePerUnit"
                name="Median $/Unit"
                fill="#9333ea"
                radius={[4, 4, 0, 0]}
              />
              <Bar
                dataKey="avgPricePerUnit"
                name="Avg $/Unit"
                fill="#d946ef"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
