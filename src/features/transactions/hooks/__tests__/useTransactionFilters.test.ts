import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useTransactionFilters } from '../useTransactionFilters';
import type { Transaction, TransactionType } from '@/types';

// =============================================================================
// Test Data
// =============================================================================

function createTransaction(overrides: Partial<Transaction> = {}): Transaction {
  return {
    id: '1',
    propertyId: 'prop-1',
    propertyName: 'Sunset Apartments',
    date: new Date('2025-06-15'),
    type: 'acquisition' as TransactionType,
    amount: 10_000_000,
    description: 'Initial acquisition',
    ...overrides,
  };
}

const sampleTransactions: Transaction[] = [
  createTransaction({
    id: '1',
    propertyId: 'prop-1',
    propertyName: 'Sunset Apartments',
    date: new Date('2025-06-15'),
    type: 'acquisition',
    amount: 10_000_000,
    description: 'Initial acquisition of Sunset',
  }),
  createTransaction({
    id: '2',
    propertyId: 'prop-1',
    propertyName: 'Sunset Apartments',
    date: new Date('2025-08-01'),
    type: 'capital_improvement',
    amount: 250_000,
    description: 'Unit renovations phase 1',
  }),
  createTransaction({
    id: '3',
    propertyId: 'prop-2',
    propertyName: 'Mesa Ridge',
    date: new Date('2025-07-20'),
    type: 'acquisition',
    amount: 12_000_000,
    description: 'Mesa Ridge acquisition',
  }),
  createTransaction({
    id: '4',
    propertyId: 'prop-2',
    propertyName: 'Mesa Ridge',
    date: new Date('2025-09-10'),
    type: 'distribution',
    amount: 75_000,
    description: 'Q3 distribution to LPs',
  }),
];

// =============================================================================
// Initial State
// =============================================================================

describe('useTransactionFilters', () => {
  it('returns all transactions with default filters', () => {
    const { result } = renderHook(() =>
      useTransactionFilters(sampleTransactions)
    );

    expect(result.current.filteredTransactions).toHaveLength(4);
  });

  it('initializes with empty filter state', () => {
    const { result } = renderHook(() =>
      useTransactionFilters(sampleTransactions)
    );

    expect(result.current.filters.searchTerm).toBe('');
    expect(result.current.filters.types).toEqual([]);
    expect(result.current.filters.dateFrom).toBe('');
    expect(result.current.filters.dateTo).toBe('');
    expect(result.current.filters.propertyId).toBe('');
  });

  it('default sort is by date descending', () => {
    const { result } = renderHook(() =>
      useTransactionFilters(sampleTransactions)
    );

    expect(result.current.sortConfig.key).toBe('date');
    expect(result.current.sortConfig.direction).toBe('desc');
  });

  // =============================================================================
  // Search Filter
  // =============================================================================

  it('filters by search term matching property name', () => {
    const { result } = renderHook(() =>
      useTransactionFilters(sampleTransactions)
    );

    act(() => {
      result.current.updateFilters({ searchTerm: 'Mesa' });
    });

    expect(result.current.filteredTransactions).toHaveLength(2);
    expect(
      result.current.filteredTransactions.every(
        (t) => t.propertyName === 'Mesa Ridge'
      )
    ).toBe(true);
  });

  it('filters by search term matching description', () => {
    const { result } = renderHook(() =>
      useTransactionFilters(sampleTransactions)
    );

    act(() => {
      result.current.updateFilters({ searchTerm: 'renovation' });
    });

    expect(result.current.filteredTransactions).toHaveLength(1);
    expect(result.current.filteredTransactions[0].id).toBe('2');
  });

  it('search is case-insensitive', () => {
    const { result } = renderHook(() =>
      useTransactionFilters(sampleTransactions)
    );

    act(() => {
      result.current.updateFilters({ searchTerm: 'SUNSET' });
    });

    expect(result.current.filteredTransactions).toHaveLength(2);
  });

  // =============================================================================
  // Type Filter
  // =============================================================================

  it('filters by single transaction type', () => {
    const { result } = renderHook(() =>
      useTransactionFilters(sampleTransactions)
    );

    act(() => {
      result.current.updateFilters({ types: ['acquisition'] });
    });

    expect(result.current.filteredTransactions).toHaveLength(2);
    expect(
      result.current.filteredTransactions.every((t) => t.type === 'acquisition')
    ).toBe(true);
  });

  it('filters by multiple transaction types', () => {
    const { result } = renderHook(() =>
      useTransactionFilters(sampleTransactions)
    );

    act(() => {
      result.current.updateFilters({
        types: ['acquisition', 'distribution'],
      });
    });

    expect(result.current.filteredTransactions).toHaveLength(3);
  });

  it('empty types array shows all', () => {
    const { result } = renderHook(() =>
      useTransactionFilters(sampleTransactions)
    );

    act(() => {
      result.current.updateFilters({ types: [] });
    });

    expect(result.current.filteredTransactions).toHaveLength(4);
  });

  // =============================================================================
  // Property Filter
  // =============================================================================

  it('filters by property ID', () => {
    const { result } = renderHook(() =>
      useTransactionFilters(sampleTransactions)
    );

    act(() => {
      result.current.updateFilters({ propertyId: 'prop-2' });
    });

    expect(result.current.filteredTransactions).toHaveLength(2);
    expect(
      result.current.filteredTransactions.every(
        (t) => t.propertyId === 'prop-2'
      )
    ).toBe(true);
  });

  // =============================================================================
  // Date Range Filter
  // =============================================================================

  it('filters by dateFrom', () => {
    const { result } = renderHook(() =>
      useTransactionFilters(sampleTransactions)
    );

    act(() => {
      result.current.updateFilters({ dateFrom: '2025-08-01' });
    });

    // Should include Aug 1 and Sep 10
    expect(result.current.filteredTransactions).toHaveLength(2);
  });

  it('filters by dateTo', () => {
    const { result } = renderHook(() =>
      useTransactionFilters(sampleTransactions)
    );

    act(() => {
      result.current.updateFilters({ dateTo: '2025-07-20' });
    });

    // Should include Jun 15 and Jul 20
    expect(result.current.filteredTransactions).toHaveLength(2);
  });

  it('filters by date range', () => {
    const { result } = renderHook(() =>
      useTransactionFilters(sampleTransactions)
    );

    act(() => {
      result.current.updateFilters({
        dateFrom: '2025-07-01',
        dateTo: '2025-08-31',
      });
    });

    // Should include Jul 20 and Aug 1
    expect(result.current.filteredTransactions).toHaveLength(2);
  });

  // =============================================================================
  // Combined Filters
  // =============================================================================

  it('applies multiple filters simultaneously', () => {
    const { result } = renderHook(() =>
      useTransactionFilters(sampleTransactions)
    );

    act(() => {
      result.current.updateFilters({
        types: ['acquisition'],
        propertyId: 'prop-1',
      });
    });

    expect(result.current.filteredTransactions).toHaveLength(1);
    expect(result.current.filteredTransactions[0].propertyName).toBe(
      'Sunset Apartments'
    );
  });

  // =============================================================================
  // Clear Filters
  // =============================================================================

  it('clearFilters resets all filters', () => {
    const { result } = renderHook(() =>
      useTransactionFilters(sampleTransactions)
    );

    act(() => {
      result.current.updateFilters({
        searchTerm: 'test',
        types: ['acquisition'],
        propertyId: 'prop-1',
      });
    });

    act(() => {
      result.current.clearFilters();
    });

    expect(result.current.filters.searchTerm).toBe('');
    expect(result.current.filters.types).toEqual([]);
    expect(result.current.filters.propertyId).toBe('');
    expect(result.current.filteredTransactions).toHaveLength(4);
  });

  // =============================================================================
  // Sorting
  // =============================================================================

  it('toggleSort switches direction on same key', () => {
    const { result } = renderHook(() =>
      useTransactionFilters(sampleTransactions)
    );

    // Default: date desc
    expect(result.current.sortConfig.direction).toBe('desc');

    act(() => {
      result.current.toggleSort('date');
    });

    expect(result.current.sortConfig.key).toBe('date');
    expect(result.current.sortConfig.direction).toBe('asc');
  });

  it('toggleSort sets new key with asc direction', () => {
    const { result } = renderHook(() =>
      useTransactionFilters(sampleTransactions)
    );

    act(() => {
      result.current.toggleSort('amount');
    });

    expect(result.current.sortConfig.key).toBe('amount');
    expect(result.current.sortConfig.direction).toBe('asc');
  });

  it('sorts numerically by amount', () => {
    const { result } = renderHook(() =>
      useTransactionFilters(sampleTransactions)
    );

    act(() => {
      result.current.toggleSort('amount');
    });

    const amounts = result.current.filteredTransactions.map((t) => t.amount);
    for (let i = 1; i < amounts.length; i++) {
      expect(amounts[i]).toBeGreaterThanOrEqual(amounts[i - 1]);
    }
  });

  // =============================================================================
  // Edge Cases
  // =============================================================================

  it('handles empty transactions array', () => {
    const { result } = renderHook(() => useTransactionFilters([]));

    expect(result.current.filteredTransactions).toHaveLength(0);
  });
});
