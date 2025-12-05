import { Card } from '@/components/ui/card';
import {
  ComposedChart,
  Bar,
  Line,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ZAxis,
} from 'recharts';

interface ComparisonChartsProps {
  propertyPerformance: Array<{
    name: string;
    irr: number;
    cashOnCash: number;
    capRate: number;
  }>;
  riskReturn: Array<{
    name: string;
    risk: number;
    return: number;
    size: number;
  }>;
}

export function ComparisonCharts({ propertyPerformance, riskReturn }: ComparisonChartsProps) {
  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const formatShortName = (name: string) => {
    const words = name.split(' ');
    if (words.length <= 2) return name;
    return words.slice(0, 2).join(' ');
  };

  const CustomScatterTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-3 border border-neutral-200 rounded-lg shadow-lg">
          <p className="font-semibold text-primary-500 mb-2">{data.name}</p>
          <p className="text-sm text-neutral-600">
            Return (IRR): <span className="font-medium">{formatPercentage(data.return)}</span>
          </p>
          <p className="text-sm text-neutral-600">
            Risk Score: <span className="font-medium">{data.risk.toFixed(2)}</span>
          </p>
          <p className="text-sm text-neutral-600">
            Value: <span className="font-medium">${(data.size / 1000000).toFixed(1)}M</span>
          </p>
        </div>
      );
    }
    return null;
  };

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

      {/* Risk vs Return Scatter */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-primary-500 mb-4">Risk vs Return Analysis</h3>
        <ResponsiveContainer width="100%" height={350}>
          <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis 
              type="number" 
              dataKey="risk" 
              name="Risk Score"
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
              label={{ value: 'Risk Score (Lower is Better)', position: 'insideBottom', offset: -10, style: { fontSize: '12px' } }}
            />
            <YAxis 
              type="number" 
              dataKey="return" 
              name="Return"
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
              tickFormatter={formatPercentage}
              label={{ value: 'Return (IRR)', angle: -90, position: 'insideLeft', style: { fontSize: '12px' } }}
            />
            <ZAxis type="number" dataKey="size" range={[100, 1000]} />
            <Tooltip content={<CustomScatterTooltip />} />
            <Scatter 
              name="Properties" 
              data={riskReturn} 
              fill="#2A3F54"
              fillOpacity={0.6}
            />
          </ScatterChart>
        </ResponsiveContainer>
        <p className="text-xs text-neutral-500 text-center mt-2">
          Bubble size represents property value. Top-left quadrant represents optimal risk/return.
        </p>
      </Card>
    </div>
  );
}
