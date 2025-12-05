import { useState } from 'react';
import { TrendingUp, LineChart, GitCompare, Database } from 'lucide-react';
import { cn } from '@/lib/utils';
import { KeyRatesSnapshot } from './components/KeyRatesSnapshot';
import { TreasuryYieldCurve } from './components/TreasuryYieldCurve';
import { RateComparisons } from './components/RateComparisons';
import { DataSources } from './components/DataSources';
import {
  mockKeyRates,
  mockYieldCurve,
  mockHistoricalRates,
  mockDataSources,
} from '@/data/mockInterestRates';

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

  const asOfDate = mockKeyRates[0]?.asOfDate || new Date().toISOString().split('T')[0];

  const renderContent = () => {
    switch (activeTab) {
      case 'snapshot':
        return <KeyRatesSnapshot rates={mockKeyRates} asOfDate={asOfDate} />;
      case 'yield-curve':
        return <TreasuryYieldCurve data={mockYieldCurve} asOfDate={asOfDate} />;
      case 'comparisons':
        return <RateComparisons historicalData={mockHistoricalRates} />;
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
            <div className="flex items-center gap-2 text-sm text-neutral-500">
              <span>Last updated:</span>
              <span className="font-medium text-neutral-700">
                {new Date(asOfDate).toLocaleDateString('en-US', {
                  weekday: 'short',
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric',
                })}
              </span>
            </div>
          </div>

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
          {renderContent()}
        </div>
      </div>

      {/* Footer Note */}
      <div className="max-w-7xl mx-auto px-6 pb-8">
        <div className="text-xs text-neutral-500 text-center">
          Rate data is updated daily from official sources. For real-time rates, please consult the data sources directly.
          This information is provided for educational purposes and should not be considered financial advice.
        </div>
      </div>
    </div>
  );
}

export default InterestRatesPage;
