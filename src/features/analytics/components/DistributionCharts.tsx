import { Card } from '@/components/ui/card';
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

interface DistributionChartsProps {
  valueByClass: Array<{ class: string; value: number }>;
  noiBySubmarket: Array<{ submarket: string; noi: number }>;
}

const COLORS = ['#2A3F54', '#E74C3C', '#3498db', '#2ecc71', '#f39c12', '#9b59b6'];

export function DistributionCharts({ valueByClass, noiBySubmarket }: DistributionChartsProps) {
  const formatCurrency = (value: number) => {
    return `$${(value / 1000000).toFixed(1)}M`;
  };

  const CustomPieLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }: any) => {
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor={x > cx ? 'start' : 'end'}
        dominantBaseline="central"
        style={{ fontSize: '12px', fontWeight: 'bold' }}
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Value by Property Class */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-primary-500 mb-4">Portfolio Value by Property Class</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={valueByClass}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis 
              dataKey="class" 
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
            />
            <YAxis 
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
              tickFormatter={formatCurrency}
            />
            <Tooltip
              formatter={(value: number) => [formatCurrency(value), 'Total Value']}
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e5e7eb',
                borderRadius: '6px',
                fontSize: '12px',
              }}
            />
            <Bar dataKey="value" fill="#2A3F54" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      {/* NOI by Submarket */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-primary-500 mb-4">NOI Distribution by Submarket</h3>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={noiBySubmarket}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={CustomPieLabel}
              outerRadius={100}
              innerRadius={60}
              fill="#8884d8"
              dataKey="noi"
            >
              {noiBySubmarket.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number) => [formatCurrency(value), 'NOI']}
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e5e7eb',
                borderRadius: '6px',
                fontSize: '12px',
              }}
            />
            <Legend 
              verticalAlign="bottom" 
              height={36}
              formatter={(value, entry: any) => `${value} (${formatCurrency(entry.payload.noi)})`}
            />
          </PieChart>
        </ResponsiveContainer>
      </Card>
    </div>
  );
}
