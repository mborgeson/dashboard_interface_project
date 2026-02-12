import { useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
  PieChart,
  Pie,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ChartSkeleton } from '@/components/ui/skeleton';
import { ToggleButton } from '@/components/ui/ToggleButton';
import type { AllDistributions, DistributionBucket } from '../types';

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

// Color palette for charts
const COLORS = [
  '#2563eb', // blue-600
  '#9333ea', // purple-600
  '#16a34a', // green-600
  '#ea580c', // orange-600
  '#dc2626', // red-600
  '#0891b2', // cyan-600
  '#4f46e5', // indigo-600
  '#c026d3', // fuchsia-600
];

type ViewMode = 'vintage' | 'unitCount' | 'starRating';
type ChartType = 'bar' | 'pie';

interface DistributionAnalysisProps {
  data: AllDistributions | undefined;
  isLoading: boolean;
}

const VIEW_OPTIONS: { value: ViewMode; label: string; description: string }[] = [
  { value: 'vintage', label: 'By Vintage', description: 'Distribution by property age' },
  { value: 'unitCount', label: 'By Unit Count', description: 'Distribution by property size' },
  { value: 'starRating', label: 'By Star Rating', description: 'Distribution by property class' },
];

function getDataForView(data: AllDistributions, view: ViewMode): DistributionBucket[] {
  switch (view) {
    case 'vintage':
      return data.vintage;
    case 'unitCount':
      return data.unitCount;
    case 'starRating':
      return data.starRating;
  }
}

function getViewTitle(view: ViewMode): string {
  switch (view) {
    case 'vintage':
      return 'Property Vintage';
    case 'unitCount':
      return 'Unit Count Range';
    case 'starRating':
      return 'Star Rating';
  }
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: DistributionBucket;
    value: number;
    name: string;
    dataKey: string;
  }>;
  label?: string;
}

function CustomBarTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const bucket = payload[0].payload;
  return (
    <div className="bg-white border border-neutral-200 rounded-lg shadow-lg p-3 text-sm">
      <p className="font-medium text-neutral-900 mb-1">{label}</p>
      <p className="text-neutral-600">
        Transactions: <span className="font-medium text-neutral-900">{bucket.count.toLocaleString()}</span>
      </p>
      {bucket.avgPricePerUnit != null && (
        <p className="text-neutral-600">
          Avg $/Unit: <span className="font-medium text-neutral-900">{currencyFormatter.format(bucket.avgPricePerUnit)}</span>
        </p>
      )}
    </div>
  );
}

interface CustomPieTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: DistributionBucket & { percent: number };
    value: number;
  }>;
}

function CustomPieTooltip({ active, payload }: CustomPieTooltipProps) {
  if (!active || !payload?.length) return null;
  const bucket = payload[0].payload;
  return (
    <div className="bg-white border border-neutral-200 rounded-lg shadow-lg p-3 text-sm">
      <p className="font-medium text-neutral-900 mb-1">{bucket.label}</p>
      <p className="text-neutral-600">
        Count: <span className="font-medium text-neutral-900">{bucket.count.toLocaleString()}</span>
      </p>
      <p className="text-neutral-600">
        Share: <span className="font-medium text-neutral-900">{(bucket.percent * 100).toFixed(1)}%</span>
      </p>
      {bucket.avgPricePerUnit != null && (
        <p className="text-neutral-600">
          Avg $/Unit: <span className="font-medium text-neutral-900">{currencyFormatter.format(bucket.avgPricePerUnit)}</span>
        </p>
      )}
    </div>
  );
}

export function DistributionAnalysis({
  data,
  isLoading,
}: DistributionAnalysisProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('vintage');
  const [chartType, setChartType] = useState<ChartType>('bar');

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

  if (!data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Distribution Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">
            No distribution data available.
          </p>
        </CardContent>
      </Card>
    );
  }

  const chartData = getDataForView(data, viewMode);
  const totalCount = chartData.reduce((sum, d) => sum + d.count, 0);
  const pieData = chartData.map((d) => ({
    ...d,
    percent: totalCount > 0 ? d.count / totalCount : 0,
  }));

  const hasData = chartData.length > 0;

  return (
    <Card>
      <CardHeader className="flex flex-col space-y-4 sm:flex-row sm:items-center sm:justify-between sm:space-y-0">
        <div>
          <CardTitle>Distribution Analysis</CardTitle>
          <p className="text-sm text-muted-foreground mt-1">
            {VIEW_OPTIONS.find((v) => v.value === viewMode)?.description}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {/* View Mode Toggle */}
          <div className="flex gap-1">
            {VIEW_OPTIONS.map((opt) => (
              <ToggleButton
                key={opt.value}
                isActive={viewMode === opt.value}
                onClick={() => setViewMode(opt.value)}
                aria-label={`View by ${opt.label}`}
              >
                {opt.label}
              </ToggleButton>
            ))}
          </div>
          {/* Chart Type Toggle */}
          <div className="flex gap-1 border-l pl-2 ml-1">
            <ToggleButton
              isActive={chartType === 'bar'}
              onClick={() => setChartType('bar')}
              aria-label="Bar chart view"
            >
              Bar
            </ToggleButton>
            <ToggleButton
              isActive={chartType === 'pie'}
              onClick={() => setChartType('pie')}
              aria-label="Pie chart view"
            >
              Pie
            </ToggleButton>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {!hasData ? (
          <p className="text-muted-foreground text-center py-8">
            No data available for {getViewTitle(viewMode).toLowerCase()}.
          </p>
        ) : chartType === 'bar' ? (
          <>
            {/* Transaction Count Bar Chart */}
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-3">
                Transaction Count by {getViewTitle(viewMode)}
              </h4>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={chartData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" className="opacity-30" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis
                    dataKey="label"
                    type="category"
                    tick={{ fontSize: 11 }}
                    width={100}
                  />
                  <Tooltip content={<CustomBarTooltip />} />
                  <Bar
                    dataKey="count"
                    name="Transactions"
                    radius={[0, 4, 4, 0]}
                  >
                    {chartData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Price Per Unit Comparison */}
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-3">
                Average Price Per Unit by {getViewTitle(viewMode)}
              </h4>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={chartData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" className="opacity-30" horizontal={false} />
                  <XAxis
                    type="number"
                    tickFormatter={(v: number) => compactCurrencyFormatter.format(v)}
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis
                    dataKey="label"
                    type="category"
                    tick={{ fontSize: 11 }}
                    width={100}
                  />
                  <Tooltip
                    formatter={(value: number) => currencyFormatter.format(value)}
                    labelFormatter={(label: string) => label}
                  />
                  <Bar
                    dataKey="avgPricePerUnit"
                    name="Avg $/Unit"
                    radius={[0, 4, 4, 0]}
                  >
                    {chartData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </>
        ) : (
          /* Pie Chart View */
          <div className="grid gap-6 lg:grid-cols-2">
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-3 text-center">
                Transaction Distribution by {getViewTitle(viewMode)}
              </h4>
              <ResponsiveContainer width="100%" height={320}>
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="count"
                    nameKey="label"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    innerRadius={40}
                    paddingAngle={2}
                    label={({ label, percent }) => `${label} (${(percent * 100).toFixed(0)}%)`}
                    labelLine={{ stroke: '#9ca3af', strokeWidth: 1 }}
                  >
                    {pieData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomPieTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Summary Stats Table */}
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-3">
                Summary Statistics
              </h4>
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-neutral-50">
                    <tr>
                      <th className="text-left py-2 px-3 font-medium text-neutral-600">Category</th>
                      <th className="text-right py-2 px-3 font-medium text-neutral-600">Count</th>
                      <th className="text-right py-2 px-3 font-medium text-neutral-600">Share</th>
                      <th className="text-right py-2 px-3 font-medium text-neutral-600">Avg $/Unit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pieData.map((bucket, index) => (
                      <tr key={bucket.label} className="border-t">
                        <td className="py-2 px-3 font-medium flex items-center gap-2">
                          <span
                            className="w-3 h-3 rounded-full inline-block"
                            style={{ backgroundColor: COLORS[index % COLORS.length] }}
                          />
                          {bucket.label}
                        </td>
                        <td className="py-2 px-3 text-right text-neutral-600">
                          {bucket.count.toLocaleString()}
                        </td>
                        <td className="py-2 px-3 text-right text-neutral-600">
                          {(bucket.percent * 100).toFixed(1)}%
                        </td>
                        <td className="py-2 px-3 text-right text-neutral-600">
                          {bucket.avgPricePerUnit != null
                            ? currencyFormatter.format(bucket.avgPricePerUnit)
                            : '--'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-neutral-50 border-t">
                    <tr>
                      <td className="py-2 px-3 font-medium">Total</td>
                      <td className="py-2 px-3 text-right font-medium">{totalCount.toLocaleString()}</td>
                      <td className="py-2 px-3 text-right font-medium">100%</td>
                      <td className="py-2 px-3 text-right font-medium">--</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
