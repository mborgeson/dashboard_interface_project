import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ChartSkeleton } from '@/components/ui/skeleton';
import type { DataQualityReport } from '../types';

const FIELD_LABELS: Record<string, string> = {
  actual_cap_rate: 'Cap Rate',
  price_per_unit: 'Price Per Unit',
  avg_unit_sf: 'Avg Unit SF',
  property_name: 'Property Name',
  sale_price: 'Sale Price',
  sale_date: 'Sale Date',
};

function getNullRateColor(rate: number): string {
  if (rate <= 0.05) return 'text-green-700 bg-green-100';
  if (rate <= 0.15) return 'text-amber-700 bg-amber-100';
  return 'text-red-700 bg-red-100';
}

function getNullRateBar(rate: number): string {
  if (rate <= 0.05) return 'bg-green-500';
  if (rate <= 0.15) return 'bg-amber-500';
  return 'bg-red-500';
}

interface DataQualitySummaryProps {
  data: DataQualityReport | undefined;
  isLoading: boolean;
}

export function DataQualitySummary({
  data,
  isLoading,
}: DataQualitySummaryProps) {
  const [showFiles, setShowFiles] = useState(false);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Data Quality Summary</CardTitle>
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
          <CardTitle>Data Quality Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">
            No data quality information available.
          </p>
        </CardContent>
      </Card>
    );
  }

  const fileEntries = Object.entries(data.recordsByFile);
  const nullEntries = Object.entries(data.nullRates).sort(
    (a, b) => b[1] - a[1]
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Data Quality Summary</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Stats Cards */}
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border p-4">
            <p className="text-sm text-muted-foreground">Total Records</p>
            <p className="text-2xl font-bold">
              {data.totalRecords.toLocaleString()}
            </p>
          </div>
          <div className="rounded-lg border p-4">
            <p className="text-sm text-muted-foreground">Source Files</p>
            <p className="text-2xl font-bold">{fileEntries.length}</p>
          </div>
          <div className="rounded-lg border p-4">
            <p className="text-sm text-muted-foreground">Flagged Outliers</p>
            <p className="text-2xl font-bold">
              {Object.values(data.flaggedOutliers).reduce((a, b) => a + b, 0)}
            </p>
          </div>
        </div>

        {/* Records by File (collapsible) */}
        <div>
          <button
            type="button"
            onClick={() => setShowFiles(!showFiles)}
            className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            <span
              className={`inline-block transition-transform ${showFiles ? 'rotate-90' : ''}`}
            >
              &#9654;
            </span>
            Records by Source File ({fileEntries.length} files)
          </button>
          {showFiles && (
            <div className="mt-2 space-y-1">
              {fileEntries.map(([fileName, count]) => (
                <div
                  key={fileName}
                  className="flex items-center justify-between text-sm py-1 px-2 rounded hover:bg-muted/50"
                >
                  <span className="truncate max-w-[300px] text-muted-foreground">
                    {fileName}
                  </span>
                  <span className="font-medium ml-4">
                    {count.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Null Rates */}
        <div>
          <h4 className="text-sm font-medium text-muted-foreground mb-3">
            Field Completeness (Null Rates)
          </h4>
          <div className="space-y-2">
            {nullEntries.map(([field, rate]) => (
              <div key={field} className="flex items-center gap-3">
                <span className="text-sm w-[140px] truncate">
                  {FIELD_LABELS[field] ?? field}
                </span>
                <div className="flex-1 h-4 bg-muted rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${getNullRateBar(rate)}`}
                    style={{ width: `${Math.max(rate * 100, 1)}%` }}
                  />
                </div>
                <span
                  className={`text-xs font-medium px-2 py-0.5 rounded ${getNullRateColor(rate)}`}
                >
                  {(rate * 100).toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Flagged Outliers */}
        {Object.keys(data.flaggedOutliers).length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-muted-foreground mb-2">
              Flagged Outliers
            </h4>
            <div className="space-y-1">
              {Object.entries(data.flaggedOutliers).map(([category, count]) => (
                <div
                  key={category}
                  className="flex items-center justify-between text-sm py-1 px-2 rounded hover:bg-muted/50"
                >
                  <span className="text-amber-700">
                    {category.replace(/_/g, ' ')}
                  </span>
                  <span className="font-medium">{count.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
