import { useState, lazy, Suspense } from 'react';
import { useMarketData } from './hooks/useMarketData';
import { MarketOverview } from './components/MarketOverview';
import { EconomicIndicators } from './components/EconomicIndicators';
import { MarketTrendsChart } from './components/MarketTrendsChart';
import { SubmarketComparison } from './components/SubmarketComparison';
import { MarketHeatmap } from './components/MarketHeatmap';
import { Download, TrendingUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ErrorState } from '@/components/ui/error-state';
import { StatCardSkeleton, ChartSkeleton } from '@/components/skeletons';

// Lazy load ReportWizard modal for code splitting
const ReportWizard = lazy(() =>
  import('@/features/reporting-suite/components/ReportWizard/ReportWizard').then(m => ({ default: m.ReportWizard }))
);

export function MarketPage() {
  const [showReportWizard, setShowReportWizard] = useState(false);

  const {
    msaOverview,
    economicIndicators,
    marketTrends,
    submarketMetrics,
    sparklineData,
    isLoading,
    error,
  } = useMarketData();

  // Show error state
  if (error) {
    return (
      <div className="p-6">
        <ErrorState
          title="Failed to load market data"
          description="Unable to fetch market data. Please try again later."
          onRetry={() => window.location.reload()}
        />
      </div>
    );
  }

  // Show loading state
  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-page-title text-primary-500">Market Data</h1>
            <p className="text-sm text-neutral-600 mt-1">
              Phoenix MSA real estate market analysis and economic indicators
            </p>
          </div>
        </div>

        {/* Overview Stats Skeleton */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <StatCardSkeleton key={i} />
          ))}
        </div>

        {/* Economic Indicators Skeleton */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <StatCardSkeleton key={i} />
          ))}
        </div>

        {/* Charts Skeleton */}
        <ChartSkeleton height={384} />
        <ChartSkeleton height={384} />
        <ChartSkeleton height={500} />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-page-title text-primary-500">Market Data</h1>
          <p className="text-sm text-neutral-600 mt-1">
            Phoenix MSA real estate market analysis and economic indicators
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button className="flex items-center gap-2" onClick={() => setShowReportWizard(true)}>
            <Download className="h-4 w-4" />
            Export Report
          </Button>
        </div>
      </div>

      {/* Phoenix MSA Overview */}
      {msaOverview && <MarketOverview overview={msaOverview} />}

      {/* Economic Indicators */}
      <EconomicIndicators
        indicators={economicIndicators}
        sparklineData={sparklineData}
      />

      {/* Market Trends Chart */}
      <MarketTrendsChart trends={marketTrends} />

      {/* Market Performance Heatmap */}
      <MarketHeatmap submarkets={submarketMetrics} />

      {/* Submarket Comparison */}
      <SubmarketComparison submarkets={submarketMetrics} />

      {/* Footer Note */}
      <div className="flex items-start gap-3 p-4 bg-neutral-50 border border-neutral-200 rounded-lg">
        <TrendingUp className="h-5 w-5 text-primary-500 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-neutral-600">
          <p className="font-medium text-neutral-900 mb-1">Market Data Sources</p>
          <p>
            Data sourced from CoStar, FRED (Federal Reserve), and U.S. Census Bureau.
            Market metrics reflect the Phoenix Metropolitan Statistical Area (MSA).
          </p>
        </div>
      </div>

      {/* Report Wizard Dialog - Lazy loaded */}
      {showReportWizard && (
        <Suspense fallback={null}>
          <ReportWizard
            open={showReportWizard}
            onOpenChange={setShowReportWizard}
          />
        </Suspense>
      )}
    </div>
  );
}
