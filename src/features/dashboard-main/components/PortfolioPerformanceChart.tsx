import { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { mockProperties } from '@/data/mockProperties';
import { formatCurrency } from '@/lib/utils/formatters';

interface MonthlyData {
  month: string;
  portfolioValue: number;
  noi: number;
}

export function PortfolioPerformanceChart() {
  // Generate 12 months of mock historical data based on current values
  const chartData = useMemo<MonthlyData[]>(() => {
    const months = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ];

    const currentValue = mockProperties.reduce((sum, p) => sum + p.valuation.currentValue, 0);
    const currentNOI = mockProperties.reduce((sum, p) => sum + p.operations.noi, 0);

    // Generate data for last 12 months with realistic growth trend
    return months.map((month, index) => {
      // Simulate 1% monthly growth in portfolio value
      const monthsAgo = 11 - index;
      const growthFactor = Math.pow(1.01, monthsAgo);
      const baseValue = currentValue / growthFactor;

      // Add some realistic variance (+/- 2%)
      const variance = 1 + (Math.random() * 0.04 - 0.02);
      const portfolioValue = baseValue * variance;

      // NOI grows at similar rate but with different variance
      const noiGrowthFactor = Math.pow(1.008, monthsAgo);
      const baseNOI = (currentNOI / 12) / noiGrowthFactor;
      const noiVariance = 1 + (Math.random() * 0.06 - 0.03);
      const noi = baseNOI * noiVariance;

      return {
        month,
        portfolioValue: Math.round(portfolioValue),
        noi: Math.round(noi),
      };
    });
  }, []);

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-4 border border-neutral-200 rounded-lg shadow-lg">
          <p className="text-sm font-semibold text-neutral-900 mb-2">
            {payload[0].payload.month}
          </p>
          <div className="space-y-1">
            <p className="text-sm text-primary-500">
              Portfolio: {formatCurrency(payload[0].value, true)}
            </p>
            <p className="text-sm text-accent-500">
              Monthly NOI: {formatCurrency(payload[1].value, true)}
            </p>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full h-[400px]">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={chartData}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="month"
            stroke="#6b7280"
            style={{ fontSize: '0.875rem' }}
          />
          <YAxis
            yAxisId="left"
            stroke="#2A3F54"
            style={{ fontSize: '0.875rem' }}
            tickFormatter={(value) => formatCurrency(value, true)}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            stroke="#E74C3C"
            style={{ fontSize: '0.875rem' }}
            tickFormatter={(value) => formatCurrency(value, true)}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: '0.875rem' }}
            iconType="line"
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="portfolioValue"
            stroke="#2A3F54"
            strokeWidth={2}
            dot={{ fill: '#2A3F54', r: 4 }}
            activeDot={{ r: 6 }}
            name="Portfolio Value"
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="noi"
            stroke="#E74C3C"
            strokeWidth={2}
            dot={{ fill: '#E74C3C', r: 4 }}
            activeDot={{ r: 6 }}
            name="Monthly NOI"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
