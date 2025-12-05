import { useState } from 'react';
import { TrendingUp, LineChart, GitCompare, Database, RefreshCw, Wifi, WifiOff } from 'lucide-react';
import { cn } from '@/lib/utils';
import { KeyRatesSnapshot } from './components/KeyRatesSnapshot';
import { TreasuryYieldCurve } from './components/TreasuryYieldCurve';
import { RateComparisons } from './components/RateComparisons';
import { DataSources } from './components/DataSources';
import { useInterestRates, getAsOfDate } from './hooks/useInterestRates';
import { mockDataSources } from '@/data/mockInterestRates';

type TabId = 'snapshot' | 'yield-curve' | 'comparisons' | 'sources';

interface Tab {
  id: TabId;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
}

const tabs: Tab[] = [
  {
    id: 'snapshot',
    label: 'Key Rates Snapshot',
    icon: TrendingUp,
    description: 'Current rates and day-over-day changes',
  },
  {
    id: 'yield-curve',
    label: 'Treasury Yield Curve',
    icon: LineChart,
    description: 'Treasury yields across maturities',
  },
  {
    id: 'comparisons',
    label: 'Rate Comparisons',
    icon: GitCompare,
    description: 'Historical rate comparisons and spreads',
  },
  {
    id: 'sources',
    label: 'Data Sources',
    icon: Database,
    description: 'Official data sources and API information',
  },
];

export function InterestRatesPage() {
  const [activeTab, setActiveTab] = useState<TabId>('snapshot');

  const {
    keyRates,
    yieldCurve,
    historicalRates,
    lastUpdated,
    isLiveData,
    isLoading,
    refresh,
    isApiConfigured,
  } = useInterestRates({
    refreshInterval: 5 * 60 * 1000, // Refresh every 5 minutes
    autoRefresh: true,
  });

  const asOfDate = getAsOfDate(keyRates);

  const renderContent = () => {
    switch (activeTab) {
      case 'snapshot':
        return <KeyRatesSnapshot rates={keyRates} asOfDate={asOfDate} />;
      case 'yield-curve':
        return <TreasuryYieldCurve data={yieldCurve} asOfDate={asOfDate} />;
      case 'comparisons':
        return <RateComparisons historicalData={historicalRates} />;
      case 'sources':
        return <DataSources sources={mockDataSources} />;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Page Header */}
      <div className="bg-white border-b border-neutral-200">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-neutral-900">Interest Rate Analysis</h1>
              <p className="text-sm text-neutral-500 mt-1">
                Track key interest rates, Treasury yields, and market benchmarks for real estate financing decisions
              </p>
            </div>
            <div className="flex items-center gap-4">
              {/* Data Source Indicator */}
              <div className={cn(
                'flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium',
                isLiveData
                  ? 'bg-green-50 text-green-700 border border-green-200'
                  : 'bg-amber-50 text-amber-700 border border-amber-200'
              )}>
                {isLiveData ? (
                  <>
                    <Wifi className="w-3 h-3" />
                    <span>Live Data</span>
                  </>
                ) : (
                  <>
                    <WifiOff className="w-3 h-3" />
                    <span>Mock Data</span>
                  </>
                )}
              </div>

              {/* Refresh Button */}
              <button
                onClick={() => refresh()}
                disabled={isLoading}
                className={cn(
                  'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                  'bg-neutral-100 text-neutral-700 hover:bg-neutral-200',
                  isLoading && 'opacity-50 cursor-not-allowed'
                )}
              >
                <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
                <span>Refresh</span>
              </button>

              {/* Last Updated */}
              <div className="flex items-center gap-2 text-sm text-neutral-500">
                <span>Last updated:</span>
                <span className="font-medium text-neutral-700">
                  {lastUpdated
                    ? lastUpdated.toLocaleString('en-US', {
                        weekday: 'short',
                        month: 'short',
                        day: 'numeric',
                        hour: 'numeric',
                        minute: '2-digit',
                      })
                    : 'Loading...'}
                </span>
              </div>
            </div>
          </div>

          {/* API Configuration Notice */}
          {!isApiConfigured && (
            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-800">
                <strong>Want live data?</strong> Add your free FRED API key to <code className="bg-blue-100 px-1 rounded">.env</code>:
                <code className="bg-blue-100 px-1 rounded ml-1">VITE_FRED_API_KEY=your_key_here</code>
                <a
                  href="https://fred.stlouisfed.org/docs/api/api_key.html"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-2 underline hover:text-blue-600"
                >
                  Get free API key →
                </a>
              </p>
            </div>
          )}

          {/* Tab Navigation */}
          <div className="mt-6 flex items-center gap-1 border-b border-neutral-200 -mb-px">
            {tabs.map(tab => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;

              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                    isActive
                      ? 'border-primary-500 text-primary-700 bg-primary-50/50'
                      : 'border-transparent text-neutral-600 hover:text-neutral-900 hover:bg-neutral-50'
                  )}
                >
                  <Icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Tab Content */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="bg-white rounded-lg border border-neutral-200 p-6">
          {isLoading && !keyRates.length ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="w-8 h-8 text-neutral-400 animate-spin" />
              <span className="ml-3 text-neutral-500">Loading rate data...</span>
            </div>
          ) : (
            renderContent()
          )}
        </div>
      </div>

      {/* Footer Note */}
      <div className="max-w-7xl mx-auto px-6 pb-8">
        <div className="text-xs text-neutral-500 text-center">
          {isLiveData ? (
            <>
              Live rate data is fetched from FRED (Federal Reserve Economic Data) and updates automatically every 5 minutes.
              Data may be delayed by up to one business day from official sources.
            </>
          ) : (
            <>
              Currently displaying mock data. Configure your FRED API key to see live rates.
              This information is provided for educational purposes and should not be considered financial advice.
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default InterestRatesPage;
