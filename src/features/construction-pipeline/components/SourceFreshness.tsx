import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import type { ConstructionDataQuality } from '../types';

interface SourceFreshnessProps {
  data: ConstructionDataQuality | undefined;
  isLoading: boolean;
}

const numFmt = new Intl.NumberFormat('en-US');
const pctFmt = new Intl.NumberFormat('en-US', { style: 'percent', minimumFractionDigits: 1 });

export function SourceFreshness({ data, isLoading }: SourceFreshnessProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Data Quality & Sources</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Data Quality & Sources</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-center text-muted-foreground py-8">No data available</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Projects</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{numFmt.format(data.totalProjects)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Permit Records</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{numFmt.format(data.permitDataCount)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Employment Records</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{numFmt.format(data.employmentDataCount)}</div>
          </CardContent>
        </Card>
      </div>

      {/* Projects by source */}
      <Card>
        <CardHeader>
          <CardTitle>Projects by Source</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {Object.entries(data.projectsBySource).map(([source, count]) => (
              <div key={source} className="flex justify-between items-center">
                <span className="text-sm font-medium capitalize">{source}</span>
                <span className="text-sm text-muted-foreground">{numFmt.format(count)}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Null rates */}
      <Card>
        <CardHeader>
          <CardTitle>Field Completeness</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {Object.entries(data.nullRates).map(([field, rate]) => (
              <div key={field} className="flex justify-between items-center">
                <span className="text-sm">{field.replace(/_/g, ' ')}</span>
                <span className={`text-sm ${rate > 0.2 ? 'text-red-600' : rate > 0.05 ? 'text-yellow-600' : 'text-green-600'}`}>
                  {pctFmt.format(1 - rate)} complete
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Recent source logs */}
      {data.sourceLogs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Recent Data Fetches</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {data.sourceLogs.map((log, i) => (
                <div key={i} className="flex justify-between items-center text-sm">
                  <span className="font-medium">{String(log.source_name)}</span>
                  <span className={log.success ? 'text-green-600' : 'text-red-600'}>
                    {log.success ? 'OK' : 'Failed'} — {String(log.records_fetched)} records
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
