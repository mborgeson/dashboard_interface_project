import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Database } from 'lucide-react';
import {
  useProjects,
  useAllProjects,
  usePipelineSummary,
  usePipelineFunnel,
  usePermitTrends,
  useEmploymentOverlay,
  useSubmarketPipeline,
  useClassificationBreakdown,
  useDeliveryTimeline,
  useConstructionDataQuality,
  useConstructionImportStatus,
  useTriggerConstructionImport,
  useConstructionFilterOptions,
} from './hooks/useConstructionData';
import type { ConstructionFilters } from './types';
import { PipelineTable } from './components/PipelineTable';
import { PipelineFilterPanel } from './components/PipelineFilterPanel';
import { PipelineFunnel } from './components/PipelineFunnel';
import { PermitTrends } from './components/PermitTrends';
import { EmploymentOverlay } from './components/EmploymentOverlay';
import { SubmarketPipeline } from './components/SubmarketPipeline';
import { ClassificationBreakdown } from './components/ClassificationBreakdown';
import { DeliveryTimeline } from './components/DeliveryTimeline';
import { SourceFreshness } from './components/SourceFreshness';
import { PipelineMap } from './components/PipelineMap';

const STATUS_LABELS: Record<string, string> = {
  proposed: 'Proposed',
  final_planning: 'Final Planning',
  permitted: 'Permitted',
  under_construction: 'Under Constr.',
  delivered: 'Delivered',
};

const numFmt = new Intl.NumberFormat('en-US');

export function ConstructionPipelinePage() {
  const [filters, setFilters] = useState<ConstructionFilters>({});
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const handleFiltersChange = (newFilters: ConstructionFilters) => {
    setFilters(newFilters);
    setPage(1);
  };

  // Data hooks
  const filterOptionsQuery = useConstructionFilterOptions();
  const projectsQuery = useProjects(filters, page, pageSize);
  const summaryQuery = usePipelineSummary(filters);
  const funnelQuery = usePipelineFunnel(filters);
  const permitTrendsQuery = usePermitTrends();
  const employmentQuery = useEmploymentOverlay();
  const submarketQuery = useSubmarketPipeline(filters);
  const classificationQuery = useClassificationBreakdown(filters);
  const deliveryTimelineQuery = useDeliveryTimeline(filters);
  const dataQualityQuery = useConstructionDataQuality();
  const allProjectsQuery = useAllProjects(filters);
  const importStatusQuery = useConstructionImportStatus();

  // Mutations
  const triggerImportMutation = useTriggerConstructionImport();

  // Error state
  if (projectsQuery.error) {
    return (
      <div className="space-y-6 p-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Construction Pipeline</h1>
          <p className="text-muted-foreground">
            Phoenix MSA multifamily development pipeline
          </p>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <h2 className="text-lg font-semibold text-red-800 mb-2">Error Loading Data</h2>
          <p className="text-red-600 mb-4">
            {projectsQuery.error instanceof Error
              ? projectsQuery.error.message
              : 'Failed to load construction data'}
          </p>
          <Button onClick={() => projectsQuery.refetch()}>Retry</Button>
        </div>
      </div>
    );
  }

  // Loading skeleton
  if (projectsQuery.isLoading) {
    return (
      <div className="space-y-6 p-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Construction Pipeline</h1>
          <p className="text-muted-foreground">
            Phoenix MSA multifamily development pipeline
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          {[...Array(5)].map((_, i) => (
            <Card key={i}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16 mb-2" />
                <Skeleton className="h-3 w-32" />
              </CardContent>
            </Card>
          ))}
        </div>
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-[400px] w-full" />
      </div>
    );
  }

  const projectsData = projectsQuery.data;
  const summaryData = summaryQuery.data ?? [];

  return (
    <div className="space-y-6 p-6">
      {/* Import banner */}
      {importStatusQuery.data && importStatusQuery.data.unimportedFiles.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-blue-800">
              {importStatusQuery.data.unimportedFiles.length} new file(s) available
            </p>
            <p className="text-xs text-blue-600">
              {importStatusQuery.data.unimportedFiles.join(', ')}
            </p>
          </div>
          <Button
            size="sm"
            onClick={() => triggerImportMutation.mutate()}
            disabled={triggerImportMutation.isPending}
          >
            {triggerImportMutation.isPending ? 'Importing...' : 'Import Now'}
          </Button>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Construction Pipeline</h1>
          <p className="text-muted-foreground">
            Phoenix MSA multifamily development pipeline — 50+ units
          </p>
        </div>
      </div>

      {/* Summary stat cards by pipeline status */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        {['proposed', 'final_planning', 'permitted', 'under_construction', 'delivered'].map(
          (status) => {
            const item = summaryData.find((s) => s.status === status);
            return (
              <Card key={status}>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    {STATUS_LABELS[status]}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {item ? numFmt.format(item.totalUnits) : '0'}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {item?.projectCount ?? 0} project{(item?.projectCount ?? 0) !== 1 ? 's' : ''}
                  </p>
                </CardContent>
              </Card>
            );
          }
        )}
      </div>

      {/* Filters */}
      <PipelineFilterPanel
        filters={filters}
        onFiltersChange={handleFiltersChange}
        filterOptions={filterOptionsQuery.data}
        isLoadingOptions={filterOptionsQuery.isLoading}
      />

      {/* Tabs: Table, Charts, Map, Sources */}
      <Tabs defaultValue="table">
        <TabsList>
          <TabsTrigger value="table">Table</TabsTrigger>
          <TabsTrigger value="charts">Charts</TabsTrigger>
          <TabsTrigger value="map">Map</TabsTrigger>
          <TabsTrigger value="sources">Data Sources</TabsTrigger>
        </TabsList>

        <TabsContent value="table">
          <PipelineTable
            data={projectsData?.data ?? []}
            isLoading={projectsQuery.isLoading}
          />
          {/* Pagination */}
          {projectsData && projectsData.totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-4">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {projectsData.totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= projectsData.totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </TabsContent>

        <TabsContent value="charts" className="space-y-6">
          <PipelineFunnel
            data={funnelQuery.data ?? []}
            isLoading={funnelQuery.isLoading}
          />
          <DeliveryTimeline
            data={deliveryTimelineQuery.data ?? []}
            isLoading={deliveryTimelineQuery.isLoading}
          />
          <div className="grid gap-6 lg:grid-cols-2">
            <PermitTrends
              data={permitTrendsQuery.data ?? []}
              isLoading={permitTrendsQuery.isLoading}
            />
            <EmploymentOverlay
              data={employmentQuery.data ?? []}
              isLoading={employmentQuery.isLoading}
            />
          </div>
          <SubmarketPipeline
            data={submarketQuery.data ?? []}
            isLoading={submarketQuery.isLoading}
          />
          <ClassificationBreakdown
            data={classificationQuery.data ?? []}
            isLoading={classificationQuery.isLoading}
          />
        </TabsContent>

        <TabsContent value="map">
          <PipelineMap
            data={allProjectsQuery.data ?? []}
            isLoading={allProjectsQuery.isLoading}
          />
        </TabsContent>

        <TabsContent value="sources">
          <SourceFreshness
            data={dataQualityQuery.data}
            isLoading={dataQualityQuery.isLoading}
          />
        </TabsContent>
      </Tabs>

      {/* Data Sources Footer */}
      <div className="flex items-start gap-3 p-4 bg-neutral-50 border border-neutral-200 rounded-lg">
        <Database className="h-5 w-5 text-primary-500 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-neutral-600">
          <p className="font-medium text-neutral-900 mb-1">Construction Data Sources</p>
          <p>
            Data sourced from CoStar, Census BPS (Building Permits Survey), FRED (Federal Reserve Economic Data),
            and BLS (Bureau of Labor Statistics). Pipeline metrics reflect the Phoenix MSA multifamily market (50+ units).
          </p>
        </div>
      </div>
    </div>
  );
}
