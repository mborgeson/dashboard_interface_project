import { Card } from '@/components/ui/card';
import { TrendingUp, TrendingDown, Users, Briefcase, DollarSign } from 'lucide-react';
import type { MSAOverview } from '@/types/market';
import type { TimeframeComparison } from '../MarketPage';

const TIMEFRAME_LABELS: Record<TimeframeComparison, string> = {
  mom: 'MoM',
  qoq: 'QoQ',
  yoy: 'YoY',
};

interface MarketOverviewProps {
  overview: MSAOverview;
  regionLabel?: string;
  timeframe?: TimeframeComparison;
}

export function MarketOverview({ overview, regionLabel = 'Phoenix MSA', timeframe = 'yoy' }: MarketOverviewProps) {
  const formatNumber = (value: number, prefix: string = ''): string => {
    if (value >= 1000000000) {
      return `${prefix}${(value / 1000000000).toFixed(1)}B`;
    }
    if (value >= 1000000) {
      return `${prefix}${(value / 1000000).toFixed(1)}M`;
    }
    if (value >= 1000) {
      return `${prefix}${(value / 1000).toFixed(1)}K`;
    }
    return `${prefix}${value.toLocaleString()}`;
  };

  const formatPercentage = (value: number): string => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const getTrendIcon = (change: number) => {
    return change > 0 ? TrendingUp : TrendingDown;
  };

  const getTrendColor = (change: number) => {
    return change > 0 ? 'text-green-600' : 'text-red-600';
  };

  const metrics = [
    {
      label: 'Population',
      value: formatNumber(overview.population),
      change: overview.populationGrowth,
      icon: Users,
      description: `${regionLabel} residents`,
    },
    {
      label: 'Employment',
      value: formatNumber(overview.employment),
      change: overview.employmentGrowth,
      icon: Briefcase,
      description: 'Total employed',
    },
    {
      label: 'GDP',
      value: formatNumber(overview.gdp, '$'),
      change: overview.gdpGrowth,
      icon: DollarSign,
      description: 'Regional GDP',
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-section-title text-primary-500">{regionLabel} Overview</h2>
        <p className="text-sm text-neutral-500">
          Last updated: {new Date(overview.lastUpdated).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
          })}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          const TrendIcon = getTrendIcon(metric.change);
          const trendColor = getTrendColor(metric.change);

          return (
            <Card key={metric.label} className="p-6">
              <div className="flex items-start justify-between mb-3">
                <div className="p-3 rounded-lg bg-primary-50">
                  <Icon className="h-6 w-6 text-primary-500" />
                </div>
                <div className={`flex items-center gap-1 text-sm font-medium ${trendColor}`}>
                  <TrendIcon className="h-4 w-4" />
                  <span>{formatPercentage(Math.abs(metric.change))} {TIMEFRAME_LABELS[timeframe]}</span>
                </div>
              </div>

              <div className="space-y-1">
                <p className="text-sm font-medium text-neutral-600">{metric.label}</p>
                <p className="text-3xl font-bold text-primary-500">{metric.value}</p>
                <p className="text-xs text-neutral-500">{metric.description}</p>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
