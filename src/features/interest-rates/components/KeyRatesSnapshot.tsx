import { useMemo } from 'react';
import { TrendingUp, TrendingDown, Minus, Info } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { KeyRate } from '@/data/mockInterestRates';

interface KeyRatesSnapshotProps {
  rates: KeyRate[];
  asOfDate: string;
}

const categoryLabels: Record<string, string> = {
  federal: 'Federal Reserve Rates',
  treasury: 'Treasury Yields',
  sofr: 'SOFR Rates',
  mortgage: 'Mortgage Rates',
};

const categoryColors: Record<string, { bg: string; border: string; text: string }> = {
  federal: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700' },
  treasury: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700' },
  sofr: { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700' },
  mortgage: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700' },
};

function RateCard({ rate }: { rate: KeyRate }) {
  const colors = categoryColors[rate.category];
  const isPositive = rate.change > 0;
  const isNegative = rate.change < 0;
  const isUnchanged = rate.change === 0;

  return (
    <div className={cn(
      'bg-white rounded-lg border shadow-sm p-4 hover:shadow-md transition-shadow',
      colors.border
    )}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <h4 className="text-sm font-medium text-neutral-900">{rate.shortName}</h4>
          <p className="text-xs text-neutral-500 mt-0.5">{rate.name}</p>
        </div>
        <div className="group relative">
          <Info className="w-4 h-4 text-neutral-400 cursor-help" />
          <div className="absolute right-0 top-6 w-64 p-3 bg-neutral-900 text-white text-xs rounded-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10 shadow-lg">
            {rate.description}
          </div>
        </div>
      </div>

      <div className="flex items-end justify-between">
        <div>
          <span className="text-2xl font-bold text-neutral-900">
            {rate.currentValue.toFixed(2)}%
          </span>
        </div>

        <div className={cn(
          'flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium',
          isPositive && 'bg-red-100 text-red-700',
          isNegative && 'bg-green-100 text-green-700',
          isUnchanged && 'bg-neutral-100 text-neutral-600'
        )}>
          {isPositive && <TrendingUp className="w-3 h-3" />}
          {isNegative && <TrendingDown className="w-3 h-3" />}
          {isUnchanged && <Minus className="w-3 h-3" />}
          <span>
            {isUnchanged ? '0.00' : `${isPositive ? '+' : ''}${rate.change.toFixed(2)}`}
          </span>
        </div>
      </div>

      <div className="mt-2 flex items-center justify-between text-xs text-neutral-500">
        <span>Previous: {rate.previousValue.toFixed(2)}%</span>
        {!isUnchanged && (
          <span className={cn(
            isPositive && 'text-red-600',
            isNegative && 'text-green-600'
          )}>
            {isPositive ? '+' : ''}{rate.changePercent.toFixed(2)}%
          </span>
        )}
      </div>
    </div>
  );
}

export function KeyRatesSnapshot({ rates, asOfDate }: KeyRatesSnapshotProps) {
  const groupedRates = useMemo(() => {
    const groups: Record<string, KeyRate[]> = {};
    rates.forEach(rate => {
      if (!groups[rate.category]) {
        groups[rate.category] = [];
      }
      groups[rate.category].push(rate);
    });
    return groups;
  }, [rates]);

  const categoryOrder = ['federal', 'treasury', 'sofr', 'mortgage'];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-neutral-900">Key Rates Snapshot</h3>
          <p className="text-sm text-neutral-500">
            Current values and day-over-day changes
          </p>
        </div>
        <div className="text-sm text-neutral-500">
          As of: <span className="font-medium">{new Date(asOfDate).toLocaleDateString('en-US', {
            weekday: 'short',
            year: 'numeric',
            month: 'short',
            day: 'numeric'
          })}</span>
        </div>
      </div>

      {/* Rate Categories */}
      {categoryOrder.map(category => {
        const categoryRates = groupedRates[category];
        if (!categoryRates) return null;

        const colors = categoryColors[category];

        return (
          <div key={category}>
            <div className={cn(
              'inline-flex items-center px-3 py-1 rounded-full text-sm font-medium mb-3',
              colors.bg,
              colors.text
            )}>
              {categoryLabels[category]}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {categoryRates.map(rate => (
                <RateCard key={rate.id} rate={rate} />
              ))}
            </div>
          </div>
        );
      })}

      {/* Legend */}
      <div className="flex items-center gap-6 pt-4 border-t border-neutral-200 text-xs text-neutral-600">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-green-100 border border-green-300" />
          <span>Rate Decrease (Positive for borrowers)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-100 border border-red-300" />
          <span>Rate Increase</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-neutral-100 border border-neutral-300" />
          <span>Unchanged</span>
        </div>
      </div>
    </div>
  );
}
