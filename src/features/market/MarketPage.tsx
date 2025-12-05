import { useMarketData } from './hooks/useMarketData';
import { MarketOverview } from './components/MarketOverview';
import { EconomicIndicators } from './components/EconomicIndicators';
import { MarketTrendsChart } from './components/MarketTrendsChart';
import { SubmarketComparison } from './components/SubmarketComparison';
import { MarketHeatmap } from './components/MarketHeatmap';
import { Download, TrendingUp } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function MarketPage() {
  const {
    msaOverview,
    economicIndicators,
    marketTrends,
    submarketMetrics,
    sparklineData,
  } = useMarketData();

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
          <Button className="flex items-center gap-2">
            <Download className="h-4 w-4" />
            Export Report
          </Button>
        </div>
      </div>

      {/* Phoenix MSA Overview */}
      <MarketOverview overview={msaOverview} />

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
            Data sourced from CoStar, U.S. Census Bureau, Bureau of Labor Statistics, and Arizona Commerce Authority.
            Market metrics are updated monthly and reflect the Phoenix Metropolitan Statistical Area (MSA).
          </p>
        </div>
      </div>
    </div>
  );
}
