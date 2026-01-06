import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useSearchStore } from './searchStore';

// Mock localStorage
const mockStorage: Record<string, string> = {};
vi.stubGlobal('localStorage', {
  getItem: vi.fn((key: string) => mockStorage[key] || null),
  setItem: vi.fn((key: string, value: string) => { mockStorage[key] = value; }),
  removeItem: vi.fn((key: string) => { delete mockStorage[key]; }),
  clear: vi.fn(() => { Object.keys(mockStorage).forEach(k => delete mockStorage[k]); }),
});

describe('searchStore', () => {
  beforeEach(() => {
    // Reset store before each test
    useSearchStore.setState({
      searchQuery: '',
      recentSearches: [],
      searchResults: [],
      isOpen: false,
    });
  });

  describe('query management', () => {
    it('sets search query', () => {
      useSearchStore.getState().setQuery('test query');
      expect(useSearchStore.getState().searchQuery).toBe('test query');
    });

    it('clears search query', () => {
      useSearchStore.getState().setQuery('test query');
      useSearchStore.getState().setQuery('');
      expect(useSearchStore.getState().searchQuery).toBe('');
    });
  });

  describe('recent searches', () => {
    it('adds a search to recent searches', () => {
      useSearchStore.getState().addRecentSearch('property search');
      const recent = useSearchStore.getState().recentSearches;
      expect(recent).toHaveLength(1);
      expect(recent[0]).toBe('property search');
    });

    it('limits recent searches to 10 items', () => {
      for (let i = 1; i <= 12; i++) {
        useSearchStore.getState().addRecentSearch(`search ${i}`);
      }
      const recent = useSearchStore.getState().recentSearches;
      expect(recent).toHaveLength(10);
      // Most recent should be first
      expect(recent[0]).toBe('search 12');
    });

    it('moves duplicate searches to the top', () => {
      useSearchStore.getState().addRecentSearch('search 1');
      useSearchStore.getState().addRecentSearch('search 2');
      useSearchStore.getState().addRecentSearch('search 1');
      const recent = useSearchStore.getState().recentSearches;
      expect(recent).toHaveLength(2);
      expect(recent[0]).toBe('search 1');
    });

    it('clears recent searches', () => {
      useSearchStore.getState().addRecentSearch('search 1');
      useSearchStore.getState().addRecentSearch('search 2');
      useSearchStore.getState().clearRecentSearches();
      expect(useSearchStore.getState().recentSearches).toHaveLength(0);
    });

    it('does not add empty searches', () => {
      useSearchStore.getState().addRecentSearch('');
      useSearchStore.getState().addRecentSearch('  ');
      expect(useSearchStore.getState().recentSearches).toHaveLength(0);
    });
  });

  describe('search results', () => {
    it('sets search results', () => {
      const mockResults = [
        {
          id: '1',
          title: 'Result 1',
          type: 'property' as const,
          subtitle: 'Sub 1',
          item: { id: '1', name: 'Test Property' } as never,
        },
        {
          id: '2',
          title: 'Result 2',
          type: 'transaction' as const,
          subtitle: 'Sub 2',
          item: { id: '2', name: 'Test Transaction' } as never,
        },
      ];
      useSearchStore.getState().setResults(mockResults);
      expect(useSearchStore.getState().searchResults).toEqual(mockResults);
    });

    it('clears results', () => {
      useSearchStore.getState().setResults([
        { id: '1', title: 'Result', type: 'property' as const, subtitle: 'Sub', item: { id: '1' } as never },
      ]);
      useSearchStore.getState().setResults([]);
      expect(useSearchStore.getState().searchResults).toHaveLength(0);
    });
  });

  describe('UI state', () => {
    it('tracks open state with setOpen', () => {
      expect(useSearchStore.getState().isOpen).toBe(false);
      useSearchStore.getState().setOpen(true);
      expect(useSearchStore.getState().isOpen).toBe(true);
      useSearchStore.getState().setOpen(false);
      expect(useSearchStore.getState().isOpen).toBe(false);
    });

    it('toggles open state', () => {
      expect(useSearchStore.getState().isOpen).toBe(false);
      useSearchStore.getState().toggleOpen();
      expect(useSearchStore.getState().isOpen).toBe(true);
      useSearchStore.getState().toggleOpen();
      expect(useSearchStore.getState().isOpen).toBe(false);
    });
  });
});
