import { lazy, Suspense, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useUSAMarketData } from './hooks/useUSAMarketData';
import { MarketOverview } from './components/MarketOverview';
import { EconomicIndicators } from './components/EconomicIndicators';
import { MarketTrendsChart } from './components/MarketTrendsChart';
import { Download, TrendingUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ErrorState } from '@/components/ui/error-state';
import { StatCardSkeleton, ChartSkeleton } from '@/components/skeletons';

// Lazy load ReportWizard modal for code splitting
const ReportWizard = lazy(() =>
  import('@/features/reporting-suite/components/ReportWizard/ReportWizard').then(m => ({ default: m.ReportWizard }))
);

function MarketSubNav() {
  const location = useLocation();
  const navigate = useNavigate();
  const isUSA = location.pathname === '/market/usa';

  const tabs = [
    { label: 'Phoenix MSA', path: '/market', active: !isUSA },
    { label: 'USA', path: '/market/usa', active: isUSA },
  ];

  return (
    <div className="flex gap-1 p-1 bg-neutral-100 rounded-lg w-fit">
      {tabs.map(tab => (
        <button
          key={tab.path}
          onClick={() => navigate(tab.path)}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            tab.active
              ? 'bg-white text-primary-500 shadow-sm'
              : 'text-neutral-600 hover:text-neutral-900'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

export function USAMarketPage() {
  const [showReportWizard, setShowReportWizard] = useState(false);

  const {
    msaOverview,
    economicIndicators,
    marketTrends,
    sparklineData,
    isLoading,
    error,
  } = useUSAMarketData();

  // Show error state
  if (error) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-page-title text-primary-500">Market Data</h1>
            <p className="text-sm text-neutral-600 mt-1">
              United States national economic indicators
            </p>
          </div>
          <MarketSubNav />
        </div>
        <ErrorState
          title="Failed to load market data"
          description="Unable to fetch national market data. Please try again later."
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
              United States national economic indicators
            </p>
          </div>
          <MarketSubNav />
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
            United States national economic indicators
          </p>
        </div>
        <div className="flex items-center gap-3">
          <MarketSubNav />
          <Button className="flex items-center gap-2" onClick={() => setShowReportWizard(true)}>
            <Download className="h-4 w-4" />
            Export Report
          </Button>
        </div>
      </div>

      {/* National Overview */}
      {msaOverview && <MarketOverview overview={msaOverview} regionLabel="United States" />}

      {/* Economic Indicators */}
      <EconomicIndicators
        indicators={economicIndicators}
        sparklineData={sparklineData}
      />

      {/* Market Trends Chart */}
      <MarketTrendsChart trends={marketTrends} regionLabel="United States" />

      {/* Footer Note */}
      <div className="flex items-start gap-3 p-4 bg-neutral-50 border border-neutral-200 rounded-lg">
        <TrendingUp className="h-5 w-5 text-primary-500 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-neutral-600">
          <p className="font-medium text-neutral-900 mb-1">Market Data Sources</p>
          <p>
            Data sourced from FRED (Federal Reserve Economic Data). National indicators include
            unemployment (UNRATE), nonfarm payrolls (PAYEMS), CPI (CPIAUCSL), GDP,
            30-year mortgage rate, Federal Funds rate, housing starts, and building permits.
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
