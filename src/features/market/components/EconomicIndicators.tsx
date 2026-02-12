import { Card } from '@/components/ui/card';
import { TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';
import type { EconomicIndicator } from '@/types/market';
import type { TimeframeComparison } from '../MarketPage';

const TIMEFRAME_LABELS: Record<TimeframeComparison, string> = {
  mom: 'MoM',
  qoq: 'QoQ',
  yoy: 'YoY',
};

interface EconomicIndicatorsProps {
  indicators: EconomicIndicator[];
  sparklineData: {
    unemployment: number[];
    jobGrowth: number[];
    incomeGrowth: number[];
    populationGrowth: number[];
  };
  isSparklinePlaceholder?: boolean;
  timeframe?: TimeframeComparison;
}

export function EconomicIndicators({ indicators, sparklineData, isSparklinePlaceholder = false, timeframe = 'yoy' }: EconomicIndicatorsProps) {
  const formatValue = (value: number, unit: string): string => {
    if (unit === '$') {
      return `$${(value / 1000).toFixed(0)}K`;
    }
    return `${value.toFixed(1)}${unit}`;
  };

  const formatChange = (change: number): string => {
    return `${change > 0 ? '+' : ''}${(change * 100).toFixed(1)}%`;
  };

  const getTrendColor = (change: number) => {
    // For unemployment, negative is good
    if (change < 0) return 'text-green-600';
    return 'text-red-600';
  };

  const getSparklineData = (indicatorName: string) => {
    const dataMap: Record<string, number[]> = {
      'Unemployment Rate': sparklineData.unemployment,
      'Job Growth Rate': sparklineData.jobGrowth,
      'Median Household Income': sparklineData.incomeGrowth,
      'Population Growth': sparklineData.populationGrowth,
    };
    return (dataMap[indicatorName] || []).map((value, index) => ({ index, value }));
  };

  const getSparklineColor = (indicatorName: string, change: number) => {
    // Unemployment: negative change is good (green)
    if (indicatorName === 'Unemployment Rate') {
      return change < 0 ? '#10b981' : '#ef4444';
    }
    // Others: positive change is good (green)
    return change > 0 ? '#10b981' : '#ef4444';
  };

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-section-title text-primary-500">Key Economic Indicators</h2>
        {isSparklinePlaceholder && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-amber-700 bg-amber-100 rounded-full">
            <AlertTriangle className="h-3 w-3" />
            No trend data available
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {indicators.map((indicator) => {
          const TrendIcon = indicator.yoyChange < 0 ? TrendingDown : TrendingUp;
          const trendColor = getTrendColor(indicator.yoyChange);
          const sparkData = getSparklineData(indicator.indicator);
          const sparkColor = getSparklineColor(indicator.indicator, indicator.yoyChange);

          return (
            <Card key={indicator.indicator} className="p-6">
              <div className="space-y-3">
                {/* Header */}
                <div className="flex items-start justify-between">
                  <p className="text-sm font-medium text-neutral-600">{indicator.indicator}</p>
                  <div className={`flex items-center gap-1 text-xs font-medium ${trendColor}`}>
                    <TrendIcon className="h-3 w-3" />
                    <span>{formatChange(indicator.yoyChange)} {TIMEFRAME_LABELS[timeframe]}</span>
                  </div>
                </div>

                {/* Value */}
                <div>
                  <p className="text-3xl font-bold text-primary-500">
                    {formatValue(indicator.value, indicator.unit)}
                  </p>
                  <p className="text-xs text-neutral-500 mt-1">Current value</p>
                </div>

                {/* Sparkline */}
                <div className="h-12 -mx-2">
                  {sparkData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={sparkData}>
                        <Line
                          type="monotone"
                          dataKey="value"
                          stroke={sparkColor}
                          strokeWidth={2}
                          dot={false}
                          isAnimationActive={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex items-center justify-center h-full text-xs text-neutral-400">
                      No trend data
                    </div>
                  )}
                </div>

                <p className="text-xs text-neutral-400">
                  {sparkData.length === 0 ? 'Data unavailable' : isSparklinePlaceholder ? 'Sample trend' : 'Last 6 months'}
                </p>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
