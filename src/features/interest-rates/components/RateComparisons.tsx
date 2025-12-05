import { useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
  AreaChart,
  Area,
} from 'recharts';
import { cn } from '@/lib/utils';
import type { HistoricalRate } from '@/data/mockInterestRates';

interface RateComparisonsProps {
  historicalData: HistoricalRate[];
}

type ComparisonView = 'fed-vs-treasury' | 'treasury-spread' | 'mortgage-spread' | 'all-rates';

const comparisonOptions = [
  {
    value: 'fed-vs-treasury',
    label: 'Fed Funds vs 10Y Treasury',
    description: 'Key indicator for monetary policy vs market expectations'
  },
  {
    value: 'treasury-spread',
    label: '2Y/10Y Treasury Spread',
    description: 'Classic yield curve inversion indicator'
  },
  {
    value: 'mortgage-spread',
    label: 'Mortgage Spread over Treasury',
    description: '30Y Mortgage vs 10Y Treasury spread'
  },
  {
    value: 'all-rates',
    label: 'All Key Rates',
    description: 'Comprehensive view of all tracked rates'
  },
];

const chartColors = {
  federalFunds: '#3b82f6',
  treasury2Y: '#10b981',
  treasury5Y: '#8b5cf6',
  treasury10Y: '#f59e0b',
  treasury30Y: '#ef4444',
  sofr: '#ec4899',
  mortgage30Y: '#06b6d4',
  spread: '#6366f1',
  spreadFill: '#c7d2fe',
};

interface TooltipPayloadEntry {
  color: string;
  name: string;
  value: number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadEntry[];
  label?: string;
}

const formatDate = (dateStr: string) => {
  const [year, month] = dateStr.split('-');
  return `${month}/${year.slice(2)}`;
};

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null;

  return (
    <div className="bg-white p-3 rounded-lg shadow-lg border border-neutral-200">
      <p className="font-medium text-neutral-900 mb-2">{formatDate(label || '')}</p>
      {payload.map((entry, index) => (
        <div key={index} className="flex items-center justify-between gap-4 text-sm">
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-neutral-600">{entry.name}:</span>
          </div>
          <span className="font-medium">
            {entry.name === 'spread' || entry.name === 'Spread'
              ? `${(entry.value * 100).toFixed(0)} bps`
              : `${entry.value.toFixed(2)}%`
            }
          </span>
        </div>
      ))}
    </div>
  );
}

export function RateComparisons({ historicalData }: RateComparisonsProps) {
  const [selectedView, setSelectedView] = useState<ComparisonView>('fed-vs-treasury');

  const fedVsTreasuryData = useMemo(() => {
    return historicalData.map(d => ({
      date: d.date,
      'Fed Funds': d.federalFunds,
      '10Y Treasury': d.treasury10Y,
      spread: d.federalFunds - d.treasury10Y,
    }));
  }, [historicalData]);

  const treasurySpreadData = useMemo(() => {
    return historicalData.map(d => ({
      date: d.date,
      '2Y Treasury': d.treasury2Y,
      '10Y Treasury': d.treasury10Y,
      spread: d.treasury10Y - d.treasury2Y,
    }));
  }, [historicalData]);

  const mortgageSpreadData = useMemo(() => {
    return historicalData.map(d => ({
      date: d.date,
      '30Y Mortgage': d.mortgage30Y,
      '10Y Treasury': d.treasury10Y,
      spread: d.mortgage30Y - d.treasury10Y,
    }));
  }, [historicalData]);

  const allRatesData = useMemo(() => {
    return historicalData.map(d => ({
      date: d.date,
      'Fed Funds': d.federalFunds,
      '2Y Treasury': d.treasury2Y,
      '10Y Treasury': d.treasury10Y,
      '30Y Mortgage': d.mortgage30Y,
      'SOFR': d.sofr,
    }));
  }, [historicalData]);

  const currentSpread = useMemo(() => {
    const latest = historicalData[historicalData.length - 1];
    if (!latest) return null;

    switch (selectedView) {
      case 'fed-vs-treasury':
        return {
          value: latest.federalFunds - latest.treasury10Y,
          label: 'Fed Funds - 10Y Treasury',
        };
      case 'treasury-spread':
        return {
          value: latest.treasury10Y - latest.treasury2Y,
          label: '10Y - 2Y Treasury',
        };
      case 'mortgage-spread':
        return {
          value: latest.mortgage30Y - latest.treasury10Y,
          label: 'Mortgage - 10Y Treasury',
        };
      default:
        return null;
    }
  }, [historicalData, selectedView]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold text-neutral-900">Rate Comparisons</h3>
        <p className="text-sm text-neutral-500">
          Historical comparison of key interest rates and spreads
        </p>
      </div>

      {/* View Selector */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {comparisonOptions.map(option => (
          <button
            key={option.value}
            onClick={() => setSelectedView(option.value as ComparisonView)}
            className={cn(
              'p-4 rounded-lg border-2 text-left transition-all',
              selectedView === option.value
                ? 'border-primary-500 bg-primary-50'
                : 'border-neutral-200 bg-white hover:border-neutral-300'
            )}
          >
            <p className={cn(
              'text-sm font-medium',
              selectedView === option.value ? 'text-primary-700' : 'text-neutral-900'
            )}>
              {option.label}
            </p>
            <p className="text-xs text-neutral-500 mt-1">{option.description}</p>
          </button>
        ))}
      </div>

      {/* Current Spread Indicator */}
      {currentSpread && (
        <div className={cn(
          'flex items-center justify-between p-4 rounded-lg',
          currentSpread.value < 0 ? 'bg-red-50 border border-red-200' : 'bg-green-50 border border-green-200'
        )}>
          <div>
            <p className="text-sm text-neutral-600">{currentSpread.label}</p>
            <p className={cn(
              'text-2xl font-bold',
              currentSpread.value < 0 ? 'text-red-700' : 'text-green-700'
            )}>
              {currentSpread.value >= 0 ? '+' : ''}{(currentSpread.value * 100).toFixed(0)} bps
            </p>
          </div>
          {selectedView === 'treasury-spread' && currentSpread.value < 0 && (
            <div className="bg-red-100 px-3 py-1 rounded-full">
              <span className="text-sm font-medium text-red-700">Yield Curve Inverted</span>
            </div>
          )}
        </div>
      )}

      {/* Chart */}
      <div className="bg-white rounded-lg border border-neutral-200 p-4">
        <ResponsiveContainer width="100%" height={400}>
          {selectedView === 'fed-vs-treasury' ? (
            <LineChart data={fedVsTreasuryData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fontSize: 12 }} />
              <YAxis
                domain={['dataMin - 0.5', 'dataMax + 0.5']}
                tickFormatter={(v) => `${v.toFixed(1)}%`}
                tick={{ fontSize: 12 }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="3 3" />
              <Line
                type="monotone"
                dataKey="Fed Funds"
                stroke={chartColors.federalFunds}
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="10Y Treasury"
                stroke={chartColors.treasury10Y}
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          ) : selectedView === 'treasury-spread' ? (
            <AreaChart data={treasurySpreadData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fontSize: 12 }} />
              <YAxis
                yAxisId="left"
                domain={['dataMin - 0.5', 'dataMax + 0.5']}
                tickFormatter={(v) => `${v.toFixed(1)}%`}
                tick={{ fontSize: 12 }}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tickFormatter={(v) => `${(v * 100).toFixed(0)} bps`}
                tick={{ fontSize: 12 }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <ReferenceLine yAxisId="right" y={0} stroke="#ef4444" strokeWidth={2} strokeDasharray="5 5" label="Inversion" />
              <Area
                yAxisId="right"
                type="monotone"
                dataKey="spread"
                name="Spread"
                fill={chartColors.spreadFill}
                stroke={chartColors.spread}
                fillOpacity={0.6}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="2Y Treasury"
                stroke={chartColors.treasury2Y}
                strokeWidth={2}
                dot={false}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="10Y Treasury"
                stroke={chartColors.treasury10Y}
                strokeWidth={2}
                dot={false}
              />
            </AreaChart>
          ) : selectedView === 'mortgage-spread' ? (
            <AreaChart data={mortgageSpreadData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fontSize: 12 }} />
              <YAxis
                yAxisId="left"
                domain={['dataMin - 0.5', 'dataMax + 0.5']}
                tickFormatter={(v) => `${v.toFixed(1)}%`}
                tick={{ fontSize: 12 }}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tickFormatter={(v) => `${(v * 100).toFixed(0)} bps`}
                tick={{ fontSize: 12 }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Area
                yAxisId="right"
                type="monotone"
                dataKey="spread"
                name="Spread"
                fill="#cffafe"
                stroke={chartColors.mortgage30Y}
                fillOpacity={0.6}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="30Y Mortgage"
                stroke={chartColors.mortgage30Y}
                strokeWidth={2}
                dot={false}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="10Y Treasury"
                stroke={chartColors.treasury10Y}
                strokeWidth={2}
                dot={false}
              />
            </AreaChart>
          ) : (
            <LineChart data={allRatesData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fontSize: 12 }} />
              <YAxis
                domain={['dataMin - 0.5', 'dataMax + 0.5']}
                tickFormatter={(v) => `${v.toFixed(1)}%`}
                tick={{ fontSize: 12 }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Line type="monotone" dataKey="Fed Funds" stroke={chartColors.federalFunds} strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="2Y Treasury" stroke={chartColors.treasury2Y} strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="10Y Treasury" stroke={chartColors.treasury10Y} strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="30Y Mortgage" stroke={chartColors.mortgage30Y} strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="SOFR" stroke={chartColors.sofr} strokeWidth={2} dot={false} strokeDasharray="5 5" />
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>

      {/* Insights */}
      <div className="bg-neutral-50 rounded-lg p-4">
        <h4 className="text-sm font-medium text-neutral-900 mb-3">Key Insights</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          {selectedView === 'fed-vs-treasury' && (
            <>
              <div className="bg-white p-3 rounded-lg border border-neutral-200">
                <p className="font-medium text-neutral-700">Policy vs Market</p>
                <p className="text-neutral-500 mt-1">
                  When Fed Funds exceed the 10Y Treasury, it signals tight monetary policy relative to long-term growth expectations.
                </p>
              </div>
              <div className="bg-white p-3 rounded-lg border border-neutral-200">
                <p className="font-medium text-neutral-700">Real Estate Impact</p>
                <p className="text-neutral-500 mt-1">
                  Higher short-term rates increase floating-rate loan costs, while the 10Y Treasury influences permanent financing rates.
                </p>
              </div>
            </>
          )}
          {selectedView === 'treasury-spread' && (
            <>
              <div className="bg-white p-3 rounded-lg border border-neutral-200">
                <p className="font-medium text-neutral-700">Yield Curve Shape</p>
                <p className="text-neutral-500 mt-1">
                  A negative spread (inverted curve) has historically preceded recessions. Currently monitoring for normalization.
                </p>
              </div>
              <div className="bg-white p-3 rounded-lg border border-neutral-200">
                <p className="font-medium text-neutral-700">Investment Timing</p>
                <p className="text-neutral-500 mt-1">
                  Curve steepening often signals improving economic outlook and may indicate opportunity for longer-term financing.
                </p>
              </div>
            </>
          )}
          {selectedView === 'mortgage-spread' && (
            <>
              <div className="bg-white p-3 rounded-lg border border-neutral-200">
                <p className="font-medium text-neutral-700">Spread Analysis</p>
                <p className="text-neutral-500 mt-1">
                  The mortgage-Treasury spread typically ranges 150-200 bps. Wider spreads indicate credit tightening or market stress.
                </p>
              </div>
              <div className="bg-white p-3 rounded-lg border border-neutral-200">
                <p className="font-medium text-neutral-700">Refinancing Window</p>
                <p className="text-neutral-500 mt-1">
                  Narrower spreads combined with falling Treasury yields create favorable refinancing conditions.
                </p>
              </div>
            </>
          )}
          {selectedView === 'all-rates' && (
            <>
              <div className="bg-white p-3 rounded-lg border border-neutral-200">
                <p className="font-medium text-neutral-700">Rate Environment</p>
                <p className="text-neutral-500 mt-1">
                  Comprehensive view shows the relationship between policy rates, market rates, and consumer lending rates.
                </p>
              </div>
              <div className="bg-white p-3 rounded-lg border border-neutral-200">
                <p className="font-medium text-neutral-700">SOFR Transition</p>
                <p className="text-neutral-500 mt-1">
                  SOFR closely tracks the Fed Funds rate and is now the primary benchmark for floating-rate commercial loans.
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
