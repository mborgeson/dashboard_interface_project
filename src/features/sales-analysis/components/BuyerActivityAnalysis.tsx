import { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ChartSkeleton } from '@/components/ui/skeleton';
import type { BuyerActivityRow } from '../types';

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

interface BuyerActivityAnalysisProps {
  data: BuyerActivityRow[];
  isLoading: boolean;
}

export function BuyerActivityAnalysis({
  data,
  isLoading,
}: BuyerActivityAnalysisProps) {
  const topBuyers = useMemo(() => {
    return [...data]
      .sort((a, b) => b.totalVolume - a.totalVolume)
      .slice(0, 15);
  }, [data]);

  const chartData = useMemo(() => {
    return topBuyers.slice(0, 10).map((buyer) => ({
      name:
        buyer.buyer.length > 25
          ? buyer.buyer.substring(0, 22) + '...'
          : buyer.buyer,
      fullName: buyer.buyer,
      totalVolume: buyer.totalVolume,
      transactionCount: buyer.transactionCount,
    }));
  }, [topBuyers]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Buyer Activity Analysis</CardTitle>
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
          <CardTitle>Buyer Activity Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">
            No buyer activity data available for the current filters.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Buyer Activity Analysis</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Horizontal Bar Chart */}
        <div>
          <h4 className="text-sm font-medium text-muted-foreground mb-2">
            Top 10 Buyers by Total Volume
          </h4>
          <ResponsiveContainer width="100%" height={Math.max(300, chartData.length * 36)}>
            <BarChart data={chartData} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid
                strokeDasharray="3 3"
                className="opacity-30"
                horizontal={false}
              />
              <XAxis
                type="number"
                tickFormatter={(v: number) => compactCurrencyFormatter.format(v)}
                tick={{ fontSize: 11 }}
              />
              <YAxis
                type="category"
                dataKey="name"
                width={180}
                tick={{ fontSize: 11 }}
              />
              <Tooltip
                formatter={(value: number) => currencyFormatter.format(value)}
                labelFormatter={(label: string, payload) => {
                  if (payload?.[0]?.payload?.fullName) {
                    return payload[0].payload.fullName as string;
                  }
                  return label;
                }}
              />
              <Bar
                dataKey="totalVolume"
                name="Total Volume"
                fill="#2563eb"
                radius={[0, 4, 4, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Detailed Table */}
        <div>
          <h4 className="text-sm font-medium text-muted-foreground mb-2">
            Top Buyers Detail
          </h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 px-2 font-medium text-muted-foreground">
                    Buyer
                  </th>
                  <th className="text-right py-2 px-2 font-medium text-muted-foreground">
                    Transactions
                  </th>
                  <th className="text-right py-2 px-2 font-medium text-muted-foreground">
                    Total Volume
                  </th>
                  <th className="text-left py-2 px-2 font-medium text-muted-foreground">
                    Submarkets
                  </th>
                  <th className="text-left py-2 px-2 font-medium text-muted-foreground">
                    Active Period
                  </th>
                </tr>
              </thead>
              <tbody>
                {topBuyers.map((buyer) => (
                  <tr
                    key={buyer.buyer}
                    className="border-b last:border-b-0 hover:bg-muted/50"
                  >
                    <td className="py-2 px-2 font-medium max-w-[200px] truncate">
                      {buyer.buyer}
                    </td>
                    <td className="py-2 px-2 text-right">
                      {buyer.transactionCount}
                    </td>
                    <td className="py-2 px-2 text-right">
                      {currencyFormatter.format(buyer.totalVolume)}
                    </td>
                    <td className="py-2 px-2">
                      <div className="flex flex-wrap gap-1">
                        {buyer.submarkets.slice(0, 3).map((sm) => (
                          <span
                            key={sm}
                            className="inline-block bg-blue-100 text-blue-800 text-xs px-1.5 py-0.5 rounded"
                          >
                            {sm}
                          </span>
                        ))}
                        {buyer.submarkets.length > 3 && (
                          <span className="text-xs text-muted-foreground">
                            +{buyer.submarkets.length - 3} more
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-2 px-2 text-xs text-muted-foreground whitespace-nowrap">
                      {buyer.firstPurchase} - {buyer.lastPurchase}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
