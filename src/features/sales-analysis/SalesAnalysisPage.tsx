import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  useSalesData,
  useTimeSeriesAnalytics,
  useSubmarketComparison,
  useBuyerActivity,
  useDistributions,
  useDataQuality,
  useImportStatus,
  useTriggerImport,
  useReminderStatus,
  useDismissReminder,
} from './hooks/useSalesData';
import type { SalesFilters } from './types';
import { SalesTable } from './components/SalesTable';
import { TimeSeriesTrends } from './components/TimeSeriesTrends';
import { SubmarketComparison } from './components/SubmarketComparison';
import { BuyerActivityAnalysis } from './components/BuyerActivityAnalysis';
import { DistributionAnalysis } from './components/DistributionAnalysis';
import { DataQualitySummary } from './components/DataQualitySummary';
import { SalesMap } from './components/SalesMap';
import { ImportNotificationBanner } from './components/ImportNotificationBanner';
import { MonthlyReminderBanner } from './components/MonthlyReminderBanner';

export function SalesAnalysisPage() {
  const [filters, setFilters] = useState<SalesFilters>({});
  const [page, setPage] = useState(1);
  const pageSize = 50;

  // Data hooks
  const salesQuery = useSalesData(filters, page, pageSize);
  const timeSeriesQuery = useTimeSeriesAnalytics(filters);
  const submarketQuery = useSubmarketComparison(filters);
  const buyerQuery = useBuyerActivity(filters);
  const distributionsQuery = useDistributions(filters);
  const dataQualityQuery = useDataQuality();
  const importStatusQuery = useImportStatus();
  const reminderStatusQuery = useReminderStatus();

  // Mutations
  const triggerImportMutation = useTriggerImport();
  const dismissReminderMutation = useDismissReminder();

  // Loading state
  const isLoading = salesQuery.isLoading;

  // Error state
  if (salesQuery.error) {
    return (
      <div className="space-y-6 p-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Sales Analysis</h1>
          <p className="text-muted-foreground">
            Phoenix MSA multifamily sales comps from CoStar
          </p>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <h2 className="text-lg font-semibold text-red-800 mb-2">Error Loading Sales Data</h2>
          <p className="text-red-600 mb-4">
            {salesQuery.error instanceof Error
              ? salesQuery.error.message
              : 'Failed to load sales data'}
          </p>
          <Button onClick={() => salesQuery.refetch()}>Retry</Button>
        </div>
      </div>
    );
  }

  // Loading skeleton
  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Sales Analysis</h1>
          <p className="text-muted-foreground">
            Phoenix MSA multifamily sales comps from CoStar
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
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
        <Card>
          <CardContent className="pt-6">
            <Skeleton className="h-10 w-full" />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-8 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const salesData = salesQuery.data;

  return (
    <div className="space-y-6 p-6">
      {/* Notification Banners */}
      <ImportNotificationBanner
        importStatus={importStatusQuery.data}
        isLoading={importStatusQuery.isLoading}
        onTriggerImport={() => triggerImportMutation.mutate()}
        isImporting={triggerImportMutation.isPending}
      />
      <MonthlyReminderBanner
        reminderStatus={reminderStatusQuery.data}
        isLoading={reminderStatusQuery.isLoading}
        onDismiss={() => dismissReminderMutation.mutate()}
      />

      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Sales Analysis</h1>
          <p className="text-muted-foreground">
            Phoenix MSA multifamily sales comps from CoStar
          </p>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Sales</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {salesData?.total.toLocaleString() ?? '--'}
            </div>
            <p className="text-xs text-muted-foreground">Records in database</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Current Page</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {salesData?.page ?? '--'} / {salesData?.totalPages ?? '--'}
            </div>
            <p className="text-xs text-muted-foreground">
              Showing {salesData?.data.length ?? 0} records
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Filters Active</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {Object.values(filters).filter(Boolean).length}
            </div>
            <p className="text-xs text-muted-foreground">Filter criteria applied</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Data Quality</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dataQualityQuery.data?.totalRecords.toLocaleString() ?? '--'}
            </div>
            <p className="text-xs text-muted-foreground">Total records tracked</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters placeholder */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Filters — coming in Wave 3. Use the tabs below to explore data.
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setFilters({});
                  setPage(1);
                }}
              >
                Clear Filters
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabs: Table, Charts, Map */}
      <Tabs defaultValue="table">
        <TabsList>
          <TabsTrigger value="table">Table</TabsTrigger>
          <TabsTrigger value="charts">Charts</TabsTrigger>
          <TabsTrigger value="map">Map</TabsTrigger>
          <TabsTrigger value="quality">Data Quality</TabsTrigger>
        </TabsList>

        <TabsContent value="table">
          <SalesTable
            data={salesData?.data ?? []}
            isLoading={salesQuery.isLoading}
          />
          {/* Pagination */}
          {salesData && salesData.totalPages > 1 && (
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
                Page {page} of {salesData.totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= salesData.totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </TabsContent>

        <TabsContent value="charts" className="space-y-6">
          <TimeSeriesTrends
            data={timeSeriesQuery.data ?? []}
            isLoading={timeSeriesQuery.isLoading}
          />
          <SubmarketComparison
            data={submarketQuery.data ?? []}
            isLoading={submarketQuery.isLoading}
          />
          <BuyerActivityAnalysis
            data={buyerQuery.data ?? []}
            isLoading={buyerQuery.isLoading}
          />
          <DistributionAnalysis
            data={distributionsQuery.data ?? []}
            isLoading={distributionsQuery.isLoading}
          />
        </TabsContent>

        <TabsContent value="map">
          <SalesMap
            data={salesData?.data ?? []}
            isLoading={salesQuery.isLoading}
          />
        </TabsContent>

        <TabsContent value="quality">
          <DataQualitySummary
            data={dataQualityQuery.data}
            isLoading={dataQualityQuery.isLoading}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
