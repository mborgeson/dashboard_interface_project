import { useMemo } from 'react';
import type { Transaction } from '@/types';
import { formatCurrency } from '@/lib/utils/formatters';
import { Building2, Hammer, RefreshCw, ArrowUpRight } from 'lucide-react';

interface TransactionTimelineProps {
  transactions: Transaction[];
}

interface GroupedTransactions {
  [key: string]: Transaction[];
}

const TYPE_CONFIG = {
  acquisition: {
    label: 'Acquisition',
    icon: Building2,
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
  },
  disposition: {
    label: 'Disposition',
    icon: Building2,
    color: 'text-red-600',
    bgColor: 'bg-red-100',
  },
  capital_improvement: {
    label: 'CapEx',
    icon: Hammer,
    color: 'text-orange-600',
    bgColor: 'bg-orange-100',
  },
  refinance: {
    label: 'Refinance',
    icon: RefreshCw,
    color: 'text-purple-600',
    bgColor: 'bg-purple-100',
  },
  distribution: {
    label: 'Distribution',
    icon: ArrowUpRight,
    color: 'text-green-600',
    bgColor: 'bg-green-100',
  },
};

export function TransactionTimeline({ transactions }: TransactionTimelineProps) {
  const groupedByMonth = useMemo(() => {
    const groups: GroupedTransactions = {};

    transactions.forEach((txn) => {
      const date = new Date(txn.date);
      const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      if (!groups[key]) {
        groups[key] = [];
      }
      groups[key].push(txn);
    });

    // Sort each group by date descending
    Object.keys(groups).forEach((key) => {
      groups[key].sort(
        (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
      );
    });

    return groups;
  }, [transactions]);

  const sortedMonths = useMemo(() => {
    return Object.keys(groupedByMonth).sort().reverse();
  }, [groupedByMonth]);

  const getMonthLabel = (monthKey: string) => {
    const [year, month] = monthKey.split('-');
    const date = new Date(parseInt(year), parseInt(month) - 1);
    return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  };

  const getMonthTotal = (transactions: Transaction[]) => {
    return transactions.reduce((sum, txn) => sum + txn.amount, 0);
  };

  if (transactions.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md border border-neutral-200 p-12 text-center">
        <p className="text-neutral-500">No transactions found matching your filters.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md border border-neutral-200 p-6">
      <div className="space-y-8">
        {sortedMonths.map((monthKey) => {
          const monthTransactions = groupedByMonth[monthKey];
          const monthTotal = getMonthTotal(monthTransactions);

          return (
            <div key={monthKey} className="relative">
              {/* Month Header */}
              <div className="flex items-center justify-between mb-4 pb-3 border-b border-neutral-200">
                <h3 className="text-lg font-semibold text-neutral-900">
                  {getMonthLabel(monthKey)}
                </h3>
                <div className="text-sm">
                  <span className="text-neutral-600">Total: </span>
                  <span className="font-semibold text-neutral-900">
                    {formatCurrency(monthTotal, true)}
                  </span>
                </div>
              </div>

              {/* Timeline */}
              <div className="space-y-4 pl-8 border-l-2 border-neutral-200">
                {monthTransactions.map((txn) => {
                  const config = TYPE_CONFIG[txn.type];
                  const Icon = config.icon;

                  return (
                    <div key={txn.id} className="relative">
                      {/* Timeline dot */}
                      <div
                        className={`absolute -left-[37px] w-6 h-6 rounded-full ${config.bgColor} ${config.color} flex items-center justify-center`}
                      >
                        <Icon className="w-3.5 h-3.5" />
                      </div>

                      {/* Transaction card */}
                      <div className="bg-neutral-50 rounded-lg p-4 hover:bg-neutral-100 transition-colors">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-semibold text-neutral-900">
                                {txn.propertyName}
                              </span>
                              <span
                                className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${config.bgColor} ${config.color}`}
                              >
                                {config.label}
                              </span>
                            </div>
                            <p className="text-sm text-neutral-600">
                              {txn.description}
                            </p>
                            <p className="text-xs text-neutral-500 mt-1">
                              {txn.category}
                            </p>
                          </div>
                          <div className="text-right ml-4">
                            <div className="text-lg font-bold text-neutral-900">
                              {formatCurrency(txn.amount, true)}
                            </div>
                            <div className="text-xs text-neutral-500">
                              {new Date(txn.date).toLocaleDateString('en-US', {
                                month: 'short',
                                day: 'numeric',
                              })}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
