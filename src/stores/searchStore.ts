import { create } from 'zustand';

import type { Property } from '@/types/property';
import type { Deal } from '@/types/deal';
import type { Document } from '@/types/document';
import type { Transaction } from '@/types/transaction';

export interface SearchResult {
  type: 'property' | 'deal' | 'document' | 'transaction';
  id: string;
  title: string;
  subtitle: string;
  category?: string;
  metadata?: {
    value?: string;
    amount?: string;
    date?: string;
    property?: string;
  };
  item: Property | Deal | Document | Transaction;
}

interface SearchState {
  searchQuery: string;
  recentSearches: string[];
  searchResults: SearchResult[];
  isOpen: boolean;
  
  // Actions
  setQuery: (query: string) => void;
  addRecentSearch: (query: string) => void;
  clearRecentSearches: () => void;
  setResults: (results: SearchResult[]) => void;
  toggleOpen: () => void;
  setOpen: (open: boolean) => void;
}

const MAX_RECENT_SEARCHES = 10;
const STORAGE_KEY = 'br-capital-recent-searches';

// Load recent searches from localStorage
const loadRecentSearches = (): string[] => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
};

// Save recent searches to localStorage
const saveRecentSearches = (searches: string[]) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(searches));
  } catch {
    // Silently fail if localStorage is not available
  }
};

export const useSearchStore = create<SearchState>((set, get) => ({
  searchQuery: '',
  recentSearches: loadRecentSearches(),
  searchResults: [],
  isOpen: false,

  setQuery: (query) => set({ searchQuery: query }),

  addRecentSearch: (query) => {
    const trimmed = query.trim();
    if (!trimmed) return;

    const { recentSearches } = get();
    
    // Remove duplicate if exists
    const filtered = recentSearches.filter((s) => s !== trimmed);
    
    // Add to beginning and limit to MAX
    const updated = [trimmed, ...filtered].slice(0, MAX_RECENT_SEARCHES);
    
    set({ recentSearches: updated });
    saveRecentSearches(updated);
  },

  clearRecentSearches: () => {
    set({ recentSearches: [] });
    saveRecentSearches([]);
  },

  setResults: (results) => set({ searchResults: results }),

  toggleOpen: () => set((state) => ({ isOpen: !state.isOpen })),

  setOpen: (open) => set({ isOpen: open }),
}));
