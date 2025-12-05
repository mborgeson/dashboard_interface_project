import { useMemo } from 'react';
import type { Transaction } from '@/types';
import { formatCurrency } from '@/lib/utils/formatters';
import { ArrowUpRight, Building2, Hammer, TrendingUp } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

interface TransactionSummaryProps {
  transactions: Transaction[];
}

const TYPE_COLORS = {
  acquisition: '#2563eb',
  disposition: '#dc2626',
  capital_improvement: '#f97316',
  refinance: '#9333ea',
  distribution: '#16a34a',
};

export function TransactionSummary({ transactions }: TransactionSummaryProps) {
  const stats = useMemo(() => {
    const byType = {
      acquisition: 0,
      disposition: 0,
      capital_improvement: 0,
      refinance: 0,
      distribution: 0,
    };

    let totalVolume = 0;

    transactions.forEach((txn) => {
      byType[txn.type] += txn.amount;
      totalVolume += txn.amount;
    });

    const chartData = [
      { name: 'Acquisitions', value: byType.acquisition, color: TYPE_COLORS.acquisition },
      { name: 'CapEx', value: byType.capital_improvement, color: TYPE_COLORS.capital_improvement },
      { name: 'Refinance', value: byType.refinance, color: TYPE_COLORS.refinance },
      { name: 'Distributions', value: byType.distribution, color: TYPE_COLORS.distribution },
    ].filter((item) => item.value > 0);

    return {
      totalVolume,
      acquisitions: byType.acquisition,
      capEx: byType.capital_improvement,
      distributions: byType.distribution,
      chartData,
    };
  }, [transactions]);

  const statCards = [
    {
      label: 'Total Volume',
      value: formatCurrency(stats.totalVolume, true),
      icon: TrendingUp,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
    },
    {
      label: 'Acquisitions',
      value: formatCurrency(stats.acquisitions, true),
      icon: Building2,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
    },
    {
      label: 'CapEx',
      value: formatCurrency(stats.capEx, true),
      icon: Hammer,
      color: 'text-orange-600',
      bgColor: 'bg-orange-100',
    },
    {
      label: 'Distributions',
      value: formatCurrency(stats.distributions, true),
      icon: ArrowUpRight,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
    },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
      {statCards.map((stat) => {
        const Icon = stat.icon;
        return (
          <div
            key={stat.label}
            className="bg-white rounded-lg shadow-md p-6 border border-neutral-200"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-neutral-600">{stat.label}</span>
              <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                <Icon className={`w-5 h-5 ${stat.color}`} />
              </div>
            </div>
            <div className="text-2xl font-bold text-neutral-900">{stat.value}</div>
          </div>
        );
      })}

      <div className="bg-white rounded-lg shadow-md p-6 border border-neutral-200">
        <h3 className="text-sm font-medium text-neutral-600 mb-4">Distribution by Type</h3>
        <ResponsiveContainer width="100%" height={120}>
          <PieChart>
            <Pie
              data={stats.chartData}
              cx="50%"
              cy="50%"
              innerRadius={30}
              outerRadius={50}
              paddingAngle={2}
              dataKey="value"
            >
              {stats.chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="mt-3 space-y-1">
          {stats.chartData.map((item) => (
            <div key={item.name} className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-sm"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-neutral-600">{item.name}</span>
              </div>
              <span className="font-medium text-neutral-900">
                {formatCurrency(item.value, true)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
