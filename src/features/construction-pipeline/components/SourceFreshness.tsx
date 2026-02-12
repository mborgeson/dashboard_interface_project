import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { CheckCircle, XCircle, Clock, Database } from 'lucide-react';
import type { ConstructionDataQuality } from '../types';

interface SourceFreshnessProps {
  data: ConstructionDataQuality | undefined;
  isLoading: boolean;
}

const numFmt = new Intl.NumberFormat('en-US');
const pctFmt = new Intl.NumberFormat('en-US', { style: 'percent', minimumFractionDigits: 1 });

// Friendly names for all data sources
const DATA_SOURCE_NAMES: Record<string, { name: string; description: string }> = {
  costar: { name: 'CoStar', description: 'Commercial real estate analytics' },
  census_bps: { name: 'Census BPS', description: 'Building Permits Survey' },
  fred_permits: { name: 'FRED', description: 'Federal Reserve Economic Data' },
  bls_employment: { name: 'BLS', description: 'Bureau of Labor Statistics' },
  mesa_soda: { name: 'Mesa SODA', description: 'Mesa Open Data API' },
  tempe_blds: { name: 'Tempe BLDS', description: 'Tempe Building Permits' },
  gilbert_arcgis: { name: 'Gilbert ArcGIS', description: 'Gilbert GIS Server' },
};

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
            <CardTitle className="text-sm font-medium">Total Units under Construction</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{numFmt.format(data.employmentDataCount)}</div>
          </CardContent>
        </Card>
      </div>

      {/* Data Sources - Combined view of all sources */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            Data Sources
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {/* CoStar projects (from projectsBySource) */}
            {Object.entries(data.projectsBySource).map(([source, count]) => {
              const sourceInfo = DATA_SOURCE_NAMES[source] || { name: source, description: '' };
              return (
                <div key={source} className="flex items-center justify-between p-2 bg-muted/50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <div>
                      <span className="text-sm font-medium">{sourceInfo.name}</span>
                      {sourceInfo.description && (
                        <p className="text-xs text-muted-foreground">{sourceInfo.description}</p>
                      )}
                    </div>
                  </div>
                  <span className="text-sm font-medium">{numFmt.format(count)} projects</span>
                </div>
              );
            })}

            {/* API Sources (from sourceLogs) */}
            {data.sourceLogs.length > 0 ? (
              data.sourceLogs.map((log, i) => {
                const sourceKey = String(log.source_name);
                const sourceInfo = DATA_SOURCE_NAMES[sourceKey] || { name: sourceKey, description: '' };
                const fetchDate = log.fetched_at ? new Date(String(log.fetched_at)).toLocaleDateString() : 'Unknown';
                return (
                  <div key={i} className="flex items-center justify-between p-2 bg-muted/50 rounded-lg">
                    <div className="flex items-center gap-3">
                      {log.success ? (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-600" />
                      )}
                      <div>
                        <span className="text-sm font-medium">{sourceInfo.name}</span>
                        {sourceInfo.description && (
                          <p className="text-xs text-muted-foreground">{sourceInfo.description}</p>
                        )}
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`text-sm font-medium ${log.success ? 'text-green-600' : 'text-red-600'}`}>
                        {numFmt.format(Number(log.records_fetched))} records
                      </span>
                      <p className="text-xs text-muted-foreground flex items-center gap-1 justify-end">
                        <Clock className="h-3 w-3" />
                        {fetchDate}
                      </p>
                    </div>
                  </div>
                );
              })
            ) : (
              /* Show expected sources as pending if no logs exist */
              Object.entries(DATA_SOURCE_NAMES)
                .filter(([key]) => key !== 'costar' && !Object.keys(data.projectsBySource).includes(key))
                .map(([key, info]) => (
                  <div key={key} className="flex items-center justify-between p-2 bg-muted/50 rounded-lg opacity-60">
                    <div className="flex items-center gap-3">
                      <Clock className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <span className="text-sm font-medium">{info.name}</span>
                        <p className="text-xs text-muted-foreground">{info.description}</p>
                      </div>
                    </div>
                    <span className="text-xs text-muted-foreground">Pending fetch</span>
                  </div>
                ))
            )}
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

    </div>
  );
}
