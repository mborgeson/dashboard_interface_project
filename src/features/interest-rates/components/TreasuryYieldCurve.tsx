import { useMemo, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  ComposedChart,
} from 'recharts';
import { TrendingDown, TrendingUp, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { YieldCurvePoint } from '@/data/mockInterestRates';

interface TreasuryYieldCurveProps {
  data: YieldCurvePoint[];
  asOfDate: string;
}

type ViewMode = 'curve' | 'comparison' | 'spread';

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

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null;

  return (
    <div className="bg-white p-3 rounded-lg shadow-lg border border-neutral-200">
      <p className="font-medium text-neutral-900 mb-2">{label} Maturity</p>
      {payload.map((entry, index) => (
        <div key={index} className="flex items-center justify-between gap-4 text-sm">
          <span style={{ color: entry.color }}>{entry.name}:</span>
          <span className="font-medium">{entry.value.toFixed(3)}%</span>
        </div>
      ))}
    </div>
  );
}

export function TreasuryYieldCurve({ data, asOfDate }: TreasuryYieldCurveProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('curve');

  const curveAnalysis = useMemo(() => {
    const shortTerm = data.find(d => d.maturity === '2Y')?.yield || 0;
    const longTerm = data.find(d => d.maturity === '10Y')?.yield || 0;
    const spread = longTerm - shortTerm;

    const isInverted = spread < 0;
    const isFlat = Math.abs(spread) < 0.25;
    const isNormal = spread > 0.25;

    return {
      shortTerm,
      longTerm,
      spread,
      isInverted,
      isFlat,
      isNormal,
      shape: isInverted ? 'Inverted' : isFlat ? 'Flat' : 'Normal',
    };
  }, [data]);

  const spreadData = useMemo(() => {
    return data.map(point => ({
      ...point,
      spread: point.yield - point.previousYield,
    }));
  }, [data]);

  return (
    <div className="space-y-6">
      {/* Header & Analysis */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold text-neutral-900">Treasury Yield Curve</h3>
          <p className="text-sm text-neutral-500">
            U.S. Treasury yields across maturities
          </p>
        </div>

        {/* Curve Shape Indicator */}
        <div className={cn(
          'flex items-center gap-2 px-4 py-2 rounded-lg',
          curveAnalysis.isInverted && 'bg-red-50 border border-red-200',
          curveAnalysis.isFlat && 'bg-amber-50 border border-amber-200',
          curveAnalysis.isNormal && 'bg-green-50 border border-green-200'
        )}>
          {curveAnalysis.isInverted && <AlertTriangle className="w-4 h-4 text-red-600" />}
          {curveAnalysis.isFlat && <TrendingDown className="w-4 h-4 text-amber-600" />}
          {curveAnalysis.isNormal && <TrendingUp className="w-4 h-4 text-green-600" />}
          <div>
            <p className={cn(
              'text-sm font-medium',
              curveAnalysis.isInverted && 'text-red-700',
              curveAnalysis.isFlat && 'text-amber-700',
              curveAnalysis.isNormal && 'text-green-700'
            )}>
              {curveAnalysis.shape} Curve
            </p>
            <p className="text-xs text-neutral-500">
              2Y/10Y Spread: {curveAnalysis.spread >= 0 ? '+' : ''}{(curveAnalysis.spread * 100).toFixed(0)} bps
            </p>
          </div>
        </div>
      </div>

      {/* View Mode Toggle */}
      <div className="flex items-center gap-2 bg-neutral-100 rounded-lg p-1 w-fit">
        {[
          { value: 'curve', label: 'Yield Curve' },
          { value: 'comparison', label: 'vs Previous Day' },
          { value: 'spread', label: 'Change Analysis' },
        ].map(option => (
          <button
            key={option.value}
            onClick={() => setViewMode(option.value as ViewMode)}
            className={cn(
              'px-4 py-2 rounded-md text-sm font-medium transition-colors',
              viewMode === option.value
                ? 'bg-white text-primary-700 shadow-sm'
                : 'text-neutral-600 hover:text-neutral-900'
            )}
          >
            {option.label}
          </button>
        ))}
      </div>

      {/* Chart */}
      <div className="bg-white rounded-lg border border-neutral-200 p-4">
        <ResponsiveContainer width="100%" height={400}>
          {viewMode === 'curve' ? (
            <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="maturity"
                tick={{ fontSize: 12 }}
                axisLine={{ stroke: '#d1d5db' }}
              />
              <YAxis
                domain={['dataMin - 0.5', 'dataMax + 0.5']}
                tickFormatter={(value) => `${value.toFixed(1)}%`}
                tick={{ fontSize: 12 }}
                axisLine={{ stroke: '#d1d5db' }}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine y={curveAnalysis.shortTerm} stroke="#94a3b8" strokeDasharray="5 5" />
              <Line
                type="monotone"
                dataKey="yield"
                name="Current Yield"
                stroke="#059669"
                strokeWidth={3}
                dot={{ fill: '#059669', strokeWidth: 2, r: 5 }}
                activeDot={{ r: 7, fill: '#059669' }}
              />
            </LineChart>
          ) : viewMode === 'comparison' ? (
            <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="maturity"
                tick={{ fontSize: 12 }}
                axisLine={{ stroke: '#d1d5db' }}
              />
              <YAxis
                domain={['dataMin - 0.5', 'dataMax + 0.5']}
                tickFormatter={(value) => `${value.toFixed(1)}%`}
                tick={{ fontSize: 12 }}
                axisLine={{ stroke: '#d1d5db' }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="yield"
                name="Current"
                stroke="#059669"
                strokeWidth={3}
                dot={{ fill: '#059669', strokeWidth: 2, r: 5 }}
              />
              <Line
                type="monotone"
                dataKey="previousYield"
                name="Previous Day"
                stroke="#94a3b8"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={{ fill: '#94a3b8', strokeWidth: 2, r: 4 }}
              />
            </LineChart>
          ) : (
            <ComposedChart data={spreadData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="maturity"
                tick={{ fontSize: 12 }}
                axisLine={{ stroke: '#d1d5db' }}
              />
              <YAxis
                yAxisId="left"
                domain={['dataMin - 0.5', 'dataMax + 0.5']}
                tickFormatter={(value) => `${value.toFixed(1)}%`}
                tick={{ fontSize: 12 }}
                axisLine={{ stroke: '#d1d5db' }}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tickFormatter={(value) => `${(value * 100).toFixed(0)} bps`}
                tick={{ fontSize: 12 }}
                axisLine={{ stroke: '#d1d5db' }}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine yAxisId="right" y={0} stroke="#94a3b8" />
              <Area
                yAxisId="right"
                type="monotone"
                dataKey="spread"
                name="Change"
                fill="#dbeafe"
                stroke="#3b82f6"
                fillOpacity={0.6}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="yield"
                name="Current Yield"
                stroke="#059669"
                strokeWidth={2}
                dot={{ fill: '#059669', r: 4 }}
              />
            </ComposedChart>
          )}
        </ResponsiveContainer>
      </div>

      {/* Key Points Table */}
      <div className="bg-neutral-50 rounded-lg p-4">
        <h4 className="text-sm font-medium text-neutral-900 mb-3">Key Maturities</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {data.filter(d => ['1M', '3M', '1Y', '2Y', '5Y', '10Y', '30Y'].includes(d.maturity)).map(point => (
            <div key={point.maturity} className="bg-white rounded-lg p-3 border border-neutral-200">
              <p className="text-xs text-neutral-500">{point.maturity}</p>
              <p className="text-lg font-semibold text-neutral-900">{point.yield.toFixed(2)}%</p>
              <p className={cn(
                'text-xs',
                point.yield < point.previousYield ? 'text-green-600' : 'text-red-600'
              )}>
                {point.yield < point.previousYield ? '↓' : '↑'} {Math.abs((point.yield - point.previousYield) * 100).toFixed(1)} bps
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Source Attribution */}
      <div className="text-xs text-neutral-500 flex items-center justify-between">
        <span>Source: U.S. Treasury Department</span>
        <span>As of {new Date(asOfDate).toLocaleDateString()}</span>
      </div>
    </div>
  );
}
