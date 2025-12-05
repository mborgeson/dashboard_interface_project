import { Search, X } from 'lucide-react';
import type { TransactionType } from '@/types';
import type { TransactionFilters } from '../hooks/useTransactionFilters';

interface TransactionFiltersProps {
  filters: TransactionFilters;
  onUpdateFilters: (updates: Partial<TransactionFilters>) => void;
  onClearFilters: () => void;
  properties: Array<{ id: string; name: string }>;
}

const TRANSACTION_TYPES: Array<{ value: TransactionType; label: string }> = [
  { value: 'acquisition', label: 'Acquisition' },
  { value: 'disposition', label: 'Disposition' },
  { value: 'capital_improvement', label: 'Capital Improvement' },
  { value: 'refinance', label: 'Refinance' },
  { value: 'distribution', label: 'Distribution' },
];

export function TransactionFilters({
  filters,
  onUpdateFilters,
  onClearFilters,
  properties,
}: TransactionFiltersProps) {
  const handleTypeToggle = (type: TransactionType) => {
    const newTypes = filters.types.includes(type)
      ? filters.types.filter((t) => t !== type)
      : [...filters.types, type];
    onUpdateFilters({ types: newTypes });
  };

  const hasActiveFilters =
    filters.searchTerm ||
    filters.types.length > 0 ||
    filters.dateFrom ||
    filters.dateTo ||
    filters.propertyId;

  return (
    <div className="bg-white rounded-lg shadow-md p-6 border border-neutral-200">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-neutral-900">Filters</h2>
        {hasActiveFilters && (
          <button
            onClick={onClearFilters}
            className="flex items-center gap-1 px-3 py-1.5 text-sm text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100 rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
            Clear
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Search */}
        <div className="lg:col-span-2">
          <label className="block text-sm font-medium text-neutral-700 mb-2">
            Search
          </label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
            <input
              type="text"
              value={filters.searchTerm}
              onChange={(e) => onUpdateFilters({ searchTerm: e.target.value })}
              placeholder="Search property name or description..."
              className="w-full pl-10 pr-4 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Property Filter */}
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-2">
            Property
          </label>
          <select
            value={filters.propertyId}
            onChange={(e) => onUpdateFilters({ propertyId: e.target.value })}
            className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">All Properties</option>
            {properties.map((property) => (
              <option key={property.id} value={property.id}>
                {property.name}
              </option>
            ))}
          </select>
        </div>

        {/* Date From */}
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-2">
            From Date
          </label>
          <input
            type="date"
            value={filters.dateFrom}
            onChange={(e) => onUpdateFilters({ dateFrom: e.target.value })}
            className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Date To */}
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-2">
            To Date
          </label>
          <input
            type="date"
            value={filters.dateTo}
            onChange={(e) => onUpdateFilters({ dateTo: e.target.value })}
            className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Transaction Types */}
        <div className="lg:col-span-3">
          <label className="block text-sm font-medium text-neutral-700 mb-2">
            Transaction Type
          </label>
          <div className="flex flex-wrap gap-2">
            {TRANSACTION_TYPES.map((type) => {
              const isSelected = filters.types.includes(type.value);
              return (
                <button
                  key={type.value}
                  onClick={() => handleTypeToggle(type.value)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isSelected
                      ? 'bg-blue-600 text-white'
                      : 'bg-neutral-100 text-neutral-700 hover:bg-neutral-200'
                  }`}
                >
                  {type.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
