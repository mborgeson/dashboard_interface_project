import { useMemo } from 'react';
import type { Transaction } from '@/types';
import { formatCurrency } from '@/lib/utils/formatters';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
} from 'recharts';

interface TransactionChartsProps {
  transactions: Transaction[];
}

const TYPE_COLORS = {
  acquisition: '#2563eb',
  capital_improvement: '#f97316',
  refinance: '#9333ea',
  distribution: '#16a34a',
};

export function TransactionCharts({ transactions }: TransactionChartsProps) {
  // Monthly volume data (last 12 months)
  const monthlyData = useMemo(() => {
    const months: { [key: string]: number } = {};
    const now = new Date();
    const twelveMonthsAgo = new Date(now.getFullYear(), now.getMonth() - 11, 1);

    transactions.forEach((txn) => {
      const date = new Date(txn.date);
      if (date >= twelveMonthsAgo) {
        const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
        months[key] = (months[key] || 0) + txn.amount;
      }
    });

    return Object.entries(months)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, value]) => {
        const [year, month] = key.split('-');
        const date = new Date(parseInt(year), parseInt(month) - 1);
        return {
          month: date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' }),
          volume: value,
        };
      });
  }, [transactions]);

  // Type breakdown data
  const typeData = useMemo(() => {
    const byType: { [key: string]: number } = {
      acquisition: 0,
      capital_improvement: 0,
      refinance: 0,
      distribution: 0,
    };

    transactions.forEach((txn) => {
      byType[txn.type] += txn.amount;
    });

    return [
      { name: 'Acquisitions', value: byType.acquisition, color: TYPE_COLORS.acquisition },
      { name: 'CapEx', value: byType.capital_improvement, color: TYPE_COLORS.capital_improvement },
      { name: 'Refinance', value: byType.refinance, color: TYPE_COLORS.refinance },
      { name: 'Distributions', value: byType.distribution, color: TYPE_COLORS.distribution },
    ].filter((item) => item.value > 0);
  }, [transactions]);

  // Cumulative investment data
  const cumulativeData = useMemo(() => {
    const sorted = [...transactions].sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    );

    let cumulative = 0;
    const data: { [key: string]: number } = {};

    sorted.forEach((txn) => {
      // Only count acquisitions and capex for cumulative investment
      if (txn.type === 'acquisition' || txn.type === 'capital_improvement') {
        cumulative += txn.amount;
        const date = new Date(txn.date);
        const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
        data[key] = cumulative;
      }
    });

    return Object.entries(data).map(([key, value]) => {
      const [year, month] = key.split('-');
      const date = new Date(parseInt(year), parseInt(month) - 1);
      return {
        month: date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' }),
        investment: value,
      };
    });
  }, [transactions]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Monthly Volume */}
      <div className="bg-white rounded-lg shadow-md p-6 border border-neutral-200">
        <h3 className="text-lg font-semibold text-neutral-900 mb-4">
          Monthly Transaction Volume (Last 12 Months)
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={monthlyData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis tickFormatter={(value) => formatCurrency(value, true)} />
            <Tooltip
              formatter={(value: number) => formatCurrency(value)}
              labelStyle={{ color: '#171717' }}
            />
            <Bar dataKey="volume" fill="#2563eb" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Type Breakdown */}
      <div className="bg-white rounded-lg shadow-md p-6 border border-neutral-200">
        <h3 className="text-lg font-semibold text-neutral-900 mb-4">
          Transaction Type Breakdown
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={typeData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              outerRadius={100}
              fill="#8884d8"
              dataKey="value"
            >
              {typeData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip formatter={(value: number) => formatCurrency(value)} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Cumulative Investment */}
      <div className="bg-white rounded-lg shadow-md p-6 border border-neutral-200 lg:col-span-2">
        <h3 className="text-lg font-semibold text-neutral-900 mb-4">
          Cumulative Investment (Acquisitions + CapEx)
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={cumulativeData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis tickFormatter={(value) => formatCurrency(value, true)} />
            <Tooltip
              formatter={(value: number) => formatCurrency(value)}
              labelStyle={{ color: '#171717' }}
            />
            <Line
              type="monotone"
              dataKey="investment"
              stroke="#2563eb"
              strokeWidth={2}
              dot={{ fill: '#2563eb', r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
