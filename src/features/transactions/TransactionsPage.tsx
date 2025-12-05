import { useState, useMemo } from 'react';
import { mockTransactions } from '@/data/mockTransactions';
import { mockProperties } from '@/data/mockProperties';
import { useTransactionFilters } from './hooks/useTransactionFilters';
import { TransactionSummary } from './components/TransactionSummary';
import { TransactionFilters } from './components/TransactionFilters';
import { TransactionTable } from './components/TransactionTable';
import { TransactionTimeline } from './components/TransactionTimeline';
import { TransactionCharts } from './components/TransactionCharts';
import { List, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

type ViewMode = 'table' | 'timeline';

export function TransactionsPage() {
  const [viewMode, setViewMode] = useState<ViewMode>('table');

  const {
    filters,
    updateFilters,
    clearFilters,
    sortConfig,
    toggleSort,
    filteredTransactions,
  } = useTransactionFilters(mockTransactions);

  const properties = useMemo(() => {
    return mockProperties.map((p) => ({ id: p.id, name: p.name }));
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-neutral-900">Transactions</h1>
          <p className="text-neutral-600 mt-1">
            Complete transaction history across all properties
          </p>
        </div>

        {/* View Toggle */}
        <div className="flex items-center gap-2 bg-white rounded-lg shadow-md border border-neutral-200 p-1">
          <button
            onClick={() => setViewMode('table')}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
              viewMode === 'table'
                ? 'bg-blue-600 text-white'
                : 'text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100'
            )}
          >
            <List className="w-4 h-4" />
            Table
          </button>
          <button
            onClick={() => setViewMode('timeline')}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
              viewMode === 'timeline'
                ? 'bg-blue-600 text-white'
                : 'text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100'
            )}
          >
            <Clock className="w-4 h-4" />
            Timeline
          </button>
        </div>
      </div>

      {/* Summary Stats */}
      <TransactionSummary transactions={filteredTransactions} />

      {/* Filters */}
      <TransactionFilters
        filters={filters}
        onUpdateFilters={updateFilters}
        onClearFilters={clearFilters}
        properties={properties}
      />

      {/* Results Count */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-neutral-600">
          Showing {filteredTransactions.length} of {mockTransactions.length} transactions
        </p>
      </div>

      {/* Transactions View */}
      {viewMode === 'table' ? (
        <TransactionTable
          transactions={filteredTransactions}
          sortConfig={sortConfig}
          onSort={toggleSort}
        />
      ) : (
        <TransactionTimeline transactions={filteredTransactions} />
      )}

      {/* Charts */}
      <div className="pt-6">
        <h2 className="text-2xl font-bold text-neutral-900 mb-6">Analytics</h2>
        <TransactionCharts transactions={filteredTransactions} />
      </div>
    </div>
  );
}
