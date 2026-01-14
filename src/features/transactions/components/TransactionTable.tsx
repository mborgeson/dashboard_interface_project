import { memo, useCallback } from 'react';
import { ArrowUpDown } from 'lucide-react';
import type { Transaction } from '@/types';
import type { SortConfig } from '../hooks/useTransactionFilters';
import { formatCurrency } from '@/lib/utils/formatters';
import { cn } from '@/lib/utils';

interface TransactionTableProps {
  transactions: Transaction[];
  sortConfig: SortConfig;
  onSort: (key: keyof Transaction) => void;
}

interface SortHeaderProps {
  label: string;
  sortKey: keyof Transaction;
  sortConfig: SortConfig;
  onSort: (key: keyof Transaction) => void;
}

// Memoized sort header component
const SortHeader = memo(function SortHeader({ label, sortKey, sortConfig, onSort }: SortHeaderProps) {
  const handleSort = useCallback(() => {
    onSort(sortKey);
  }, [onSort, sortKey]);

  return (
    <th className="px-6 py-3 text-left">
      <button
        onClick={handleSort}
        className="flex items-center gap-2 text-xs font-medium text-neutral-500 uppercase tracking-wider hover:text-neutral-700"
      >
        {label}
        <ArrowUpDown
          className={cn(
            'w-4 h-4',
            sortConfig.key === sortKey && 'text-blue-600'
          )}
        />
      </button>
    </th>
  );
});

const TYPE_CONFIG = {
  acquisition: {
    label: 'Acquisition',
    className: 'bg-blue-100 text-blue-800',
  },
  disposition: {
    label: 'Disposition',
    className: 'bg-red-100 text-red-800',
  },
  capital_improvement: {
    label: 'CapEx',
    className: 'bg-orange-100 text-orange-800',
  },
  refinance: {
    label: 'Refinance',
    className: 'bg-purple-100 text-purple-800',
  },
  distribution: {
    label: 'Distribution',
    className: 'bg-green-100 text-green-800',
  },
} as const;

// Memoized transaction row for better list performance
interface TransactionRowProps {
  txn: Transaction;
}

const TransactionRow = memo(function TransactionRow({ txn }: TransactionRowProps) {
  const typeConfig = TYPE_CONFIG[txn.type];

  return (
    <tr className="hover:bg-neutral-50 transition-colors">
      <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-900">
        {new Date(txn.date).toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
        })}
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="text-sm font-medium text-neutral-900">
          {txn.propertyName}
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <span
          className={`inline-flex px-2.5 py-1 rounded-full text-xs font-medium ${typeConfig.className}`}
        >
          {typeConfig.label}
        </span>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-600">
        {txn.category}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-neutral-900">
        {formatCurrency(txn.amount)}
      </td>
      <td className="px-6 py-4 text-sm text-neutral-600 max-w-md">
        {txn.description}
      </td>
    </tr>
  );
});

export const TransactionTable = memo(function TransactionTable({
  transactions,
  sortConfig,
  onSort,
}: TransactionTableProps) {
  if (transactions.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md border border-neutral-200 p-12 text-center">
        <p className="text-neutral-500">No transactions found matching your filters.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md border border-neutral-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-neutral-200">
          <thead className="bg-neutral-50">
            <tr>
              <SortHeader label="Date" sortKey="date" sortConfig={sortConfig} onSort={onSort} />
              <SortHeader label="Property" sortKey="propertyName" sortConfig={sortConfig} onSort={onSort} />
              <SortHeader label="Type" sortKey="type" sortConfig={sortConfig} onSort={onSort} />
              <SortHeader label="Category" sortKey="category" sortConfig={sortConfig} onSort={onSort} />
              <SortHeader label="Amount" sortKey="amount" sortConfig={sortConfig} onSort={onSort} />
              <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                Description
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-neutral-200">
            {transactions.map((txn) => (
              <TransactionRow key={txn.id} txn={txn} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
});
