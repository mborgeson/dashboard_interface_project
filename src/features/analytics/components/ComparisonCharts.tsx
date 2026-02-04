import { Card } from '@/components/ui/card';
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Cell,
  ReferenceLine,
} from 'recharts';

interface ComparisonChartsProps {
  propertyPerformance: Array<{
    name: string;
    irr: number;
    cashOnCash: number;
    capRate: number;
  }>;
  capRateDscr: Array<{
    name: string;
    capRate: number;
    dscr: number;
    noi: number;
    propertyClass: string;
    value: number;
  }>;
}

const CLASS_COLORS: Record<string, string> = {
  A: '#2563eb', // blue
  B: '#0d9488', // teal
  C: '#d97706', // amber
};

interface CapRateDscrTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: {
      name: string;
      capRate: number;
      dscr: number;
      noi: number;
      propertyClass: string;
      value: number;
    };
  }>;
}

function CapRateDscrTooltip({ active, payload }: CapRateDscrTooltipProps) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-white p-3 border border-neutral-200 rounded-lg shadow-lg">
        <p className="font-semibold text-primary-500 mb-2">{data.name}</p>
        <p className="text-sm text-neutral-600">
          Cap Rate: <span className="font-medium">{data.capRate.toFixed(2)}%</span>
        </p>
        <p className="text-sm text-neutral-600">
          DSCR: <span className="font-medium">{data.dscr.toFixed(2)}x</span>
        </p>
        <p className="text-sm text-neutral-600">
          NOI: <span className="font-medium">${(data.noi / 1000000).toFixed(2)}M</span>
        </p>
        <p className="text-sm text-neutral-600">
          Value: <span className="font-medium">${(data.value / 1000000).toFixed(1)}M</span>
        </p>
        <p className="text-sm text-neutral-600">
          Class: <span className="font-medium">{data.propertyClass}</span>
        </p>
      </div>
    );
  }
  return null;
}

export function ComparisonCharts({ propertyPerformance, capRateDscr }: ComparisonChartsProps) {
  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const formatShortName = (name: string) => {
    const words = name.split(' ');
    if (words.length <= 2) return name;
    return words.slice(0, 2).join(' ');
  };

  // Calculate average DSCR for reference line
  const avgDscr = capRateDscr.length > 0
    ? capRateDscr.reduce((sum, d) => sum + d.dscr, 0) / capRateDscr.length
    : 0;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Property Performance Comparison */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-primary-500 mb-4">Property Performance Metrics</h3>
        <ResponsiveContainer width="100%" height={350}>
          <ComposedChart data={propertyPerformance}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="name"
              stroke="#6b7280"
              style={{ fontSize: '10px' }}
              angle={-45}
              textAnchor="end"
              height={100}
              tickFormatter={formatShortName}
            />
            <YAxis
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
              tickFormatter={formatPercentage}
            />
            <Tooltip
              formatter={(value: number) => formatPercentage(value)}
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e5e7eb',
                borderRadius: '6px',
                fontSize: '12px',
              }}
            />
            <Legend wrapperStyle={{ fontSize: '12px' }} />
            <Bar dataKey="irr" fill="#2A3F54" name="IRR" radius={[4, 4, 0, 0]} />
            <Bar dataKey="cashOnCash" fill="#E74C3C" name="Cash-on-Cash" radius={[4, 4, 0, 0]} />
            <Line
              type="monotone"
              dataKey="capRate"
              stroke="#3498db"
              strokeWidth={2}
              name="Cap Rate"
              dot={{ fill: '#3498db', r: 4 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </Card>

      {/* Cap Rate vs DSCR Chart */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-primary-500 mb-4">Cap Rate vs DSCR</h3>
        <ResponsiveContainer width="100%" height={350}>
          <ComposedChart data={capRateDscr} margin={{ top: 10, right: 20, bottom: 60, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="name"
              stroke="#6b7280"
              style={{ fontSize: '10px' }}
              angle={-45}
              textAnchor="end"
              height={80}
              tickFormatter={formatShortName}
            />
            <YAxis
              yAxisId="capRate"
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
              tickFormatter={(v: number) => `${v.toFixed(1)}%`}
              label={{ value: 'Cap Rate %', angle: -90, position: 'insideLeft', style: { fontSize: '11px', fill: '#6b7280' } }}
            />
            <YAxis
              yAxisId="dscr"
              orientation="right"
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
              tickFormatter={(v: number) => `${v.toFixed(1)}x`}
              label={{ value: 'DSCR', angle: 90, position: 'insideRight', style: { fontSize: '11px', fill: '#6b7280' } }}
            />
            <Tooltip content={<CapRateDscrTooltip />} />
            <Legend wrapperStyle={{ fontSize: '12px' }} />
            <ReferenceLine yAxisId="dscr" y={1.25} stroke="#16a34a" strokeDasharray="4 4" label={{ value: 'DSCR 1.25x', position: 'right', style: { fontSize: '10px', fill: '#16a34a' } }} />
            <ReferenceLine yAxisId="dscr" y={1.0} stroke="#dc2626" strokeDasharray="4 4" label={{ value: 'DSCR 1.0x', position: 'right', style: { fontSize: '10px', fill: '#dc2626' } }} />
            <Bar yAxisId="capRate" dataKey="capRate" name="Cap Rate %" radius={[4, 4, 0, 0]}>
              {capRateDscr.map((entry, index) => (
                <Cell key={index} fill={CLASS_COLORS[entry.propertyClass] ?? '#6b7280'} fillOpacity={0.8} />
              ))}
            </Bar>
            <Line
              yAxisId="dscr"
              type="monotone"
              dataKey="dscr"
              stroke="#dc2626"
              strokeWidth={2}
              name="DSCR"
              dot={{ fill: '#dc2626', r: 4 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
        <div className="flex items-center justify-center gap-4 mt-2">
          {Object.entries(CLASS_COLORS).map(([cls, color]) => (
            <div key={cls} className="flex items-center gap-1.5 text-xs text-neutral-600">
              <div className="w-3 h-3 rounded" style={{ backgroundColor: color }} />
              Class {cls}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
