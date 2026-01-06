import { useMemo, useState, useEffect } from 'react';
import Fuse from 'fuse.js';
import { mockProperties } from '@/data/mockProperties';
import { mockTransactions } from '@/data/mockTransactions';

import type { Property } from '@/types/property';
import type { Transaction } from '@/types/transaction';

export interface SearchResult {
  type: 'property' | 'transaction';
  id: string;
  title: string;
  subtitle: string;
  matchedField?: string;
  item: Property | Transaction;
}

export function useGlobalSearch(query: string) {
  const [debouncedQuery, setDebouncedQuery] = useState(query);

  // Debounce the search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  const results = useMemo(() => {
    if (!debouncedQuery.trim()) {
      return [];
    }

    // Configure Fuse.js for properties
    const propertyFuse = new Fuse(mockProperties, {
      keys: [
        { name: 'name', weight: 2 },
        { name: 'address.street', weight: 1.5 },
        { name: 'address.city', weight: 1.5 },
        { name: 'address.submarket', weight: 1 },
        { name: 'propertyDetails.propertyClass', weight: 0.8 },
      ],
      threshold: 0.3,
      includeScore: true,
      includeMatches: true,
    });

    // Configure Fuse.js for transactions
    const transactionFuse = new Fuse(mockTransactions, {
      keys: [
        { name: 'propertyName', weight: 2 },
        { name: 'description', weight: 1.5 },
        { name: 'type', weight: 1 },
        { name: 'category', weight: 0.8 },
      ],
      threshold: 0.3,
      includeScore: true,
      includeMatches: true,
    });

    // Search properties
    const propertyResults = propertyFuse.search(debouncedQuery).map((result) => ({
      type: 'property' as const,
      id: result.item.id,
      title: result.item.name,
      subtitle: `${result.item.address.street}, ${result.item.address.city}`,
      matchedField: result.matches?.[0]?.key || undefined,
      item: result.item,
      score: result.score || 0,
    }));

    // Search transactions
    const transactionResults = transactionFuse.search(debouncedQuery).map((result) => ({
      type: 'transaction' as const,
      id: result.item.id,
      title: result.item.propertyName,
      subtitle: result.item.description,
      matchedField: result.matches?.[0]?.key || undefined,
      item: result.item,
      score: result.score || 0,
    }));

    // Combine and sort by score (lower is better with Fuse.js)
    const combined = [...propertyResults, ...transactionResults].sort(
      (a, b) => a.score - b.score
    );

    // Limit to top 10 results
    return combined.slice(0, 10);
  }, [debouncedQuery]);

  return {
    results,
    isSearching: query !== debouncedQuery,
  };
}
