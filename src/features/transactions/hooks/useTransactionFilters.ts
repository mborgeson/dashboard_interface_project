import { useState, useMemo } from 'react';
import type { Transaction, TransactionType } from '@/types';

export interface TransactionFilters {
  searchTerm: string;
  types: TransactionType[];
  dateFrom: string;
  dateTo: string;
  propertyId: string;
}

export interface SortConfig {
  key: keyof Transaction;
  direction: 'asc' | 'desc';
}

export function useTransactionFilters(transactions: Transaction[]) {
  const [filters, setFilters] = useState<TransactionFilters>({
    searchTerm: '',
    types: [],
    dateFrom: '',
    dateTo: '',
    propertyId: '',
  });

  const [sortConfig, setSortConfig] = useState<SortConfig>({
    key: 'date',
    direction: 'desc',
  });

  // Filter transactions
  const filteredTransactions = useMemo(() => {
    return transactions.filter((txn) => {
      // Search filter
      if (filters.searchTerm) {
        const searchLower = filters.searchTerm.toLowerCase();
        const matchesSearch =
          txn.propertyName.toLowerCase().includes(searchLower) ||
          txn.description.toLowerCase().includes(searchLower);
        if (!matchesSearch) return false;
      }

      // Type filter
      if (filters.types.length > 0) {
        if (!filters.types.includes(txn.type)) return false;
      }

      // Property filter
      if (filters.propertyId && txn.propertyId !== filters.propertyId) {
        return false;
      }

      // Date range filter
      const txnDate = new Date(txn.date);
      if (filters.dateFrom) {
        const fromDate = new Date(filters.dateFrom);
        if (txnDate < fromDate) return false;
      }
      if (filters.dateTo) {
        const toDate = new Date(filters.dateTo);
        toDate.setHours(23, 59, 59, 999); // Include entire day
        if (txnDate > toDate) return false;
      }

      return true;
    });
  }, [transactions, filters]);

  // Sort transactions
  const sortedTransactions = useMemo(() => {
    const sorted = [...filteredTransactions];
    sorted.sort((a, b) => {
      const aValue = a[sortConfig.key];
      const bValue = b[sortConfig.key];

      // Handle dates
      if (aValue instanceof Date && bValue instanceof Date) {
        return sortConfig.direction === 'asc'
          ? aValue.getTime() - bValue.getTime()
          : bValue.getTime() - aValue.getTime();
      }

      // Handle numbers
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortConfig.direction === 'asc'
          ? aValue - bValue
          : bValue - aValue;
      }

      // Handle strings
      const aString = String(aValue);
      const bString = String(bValue);
      return sortConfig.direction === 'asc'
        ? aString.localeCompare(bString)
        : bString.localeCompare(aString);
    });
    return sorted;
  }, [filteredTransactions, sortConfig]);

  const updateFilters = (updates: Partial<TransactionFilters>) => {
    setFilters((prev) => ({ ...prev, ...updates }));
  };

  const clearFilters = () => {
    setFilters({
      searchTerm: '',
      types: [],
      dateFrom: '',
      dateTo: '',
      propertyId: '',
    });
  };

  const toggleSort = (key: keyof Transaction) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  return {
    filters,
    updateFilters,
    clearFilters,
    sortConfig,
    toggleSort,
    filteredTransactions: sortedTransactions,
  };
}
