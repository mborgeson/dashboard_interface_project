import { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Fuse from 'fuse.js';
import {
  Search,
  Building2,
  FileText,
  TrendingUp,
  Clock,
  X,
  Command,
  ArrowRight,
  Home,
  BarChart3,
  Map,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSearchStore, type SearchResult } from '@/stores/searchStore';
import { useProperties, selectProperties } from '@/hooks/api/useProperties';
import { useDealsWithMockFallback } from '@/hooks/api/useDeals';
import { useDocumentsWithMockFallback } from '@/hooks/api/useDocuments';
import { useTransactionsWithMockFallback } from '@/hooks/api/useTransactions';
import { useToast } from '@/hooks/useToast';

// Quick navigation actions
interface QuickAction {
  id: string;
  label: string;
  path: string;
  icon: React.ElementType;
  description: string;
}

const quickActions: QuickAction[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    path: '/',
    icon: Home,
    description: 'Overview and key metrics',
  },
  {
    id: 'investments',
    label: 'Investments',
    path: '/investments',
    icon: Building2,
    description: 'Property portfolio',
  },
  {
    id: 'deals',
    label: 'Deals',
    path: '/deals',
    icon: TrendingUp,
    description: 'Active deal pipeline',
  },
  {
    id: 'documents',
    label: 'Documents',
    path: '/documents',
    icon: FileText,
    description: 'Files and contracts',
  },
  {
    id: 'market',
    label: 'Market Data',
    path: '/market',
    icon: Map,
    description: 'Market insights',
  },
  {
    id: 'analytics',
    label: 'Analytics',
    path: '/analytics',
    icon: BarChart3,
    description: 'Performance analytics',
  },
];

export function GlobalSearch() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  const {
    searchQuery,
    recentSearches,
    isOpen,
    setQuery,
    addRecentSearch,
    clearRecentSearches,
    setOpen,
  } = useSearchStore();

  // Fetch properties from API
  const { data } = useProperties();
  const properties = selectProperties(data);

  // Fetch deals from API
  const { data: dealsData } = useDealsWithMockFallback();

  // Fetch documents from API
  const { data: documentsData } = useDocumentsWithMockFallback();

  // Fetch transactions from API
  const { data: transactionsData } = useTransactionsWithMockFallback();

  const [selectedIndex, setSelectedIndex] = useState(0);
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const { info } = useToast();

  // Handler to update query and reset selection
  const handleQueryChange = useCallback((value: string) => {
    setQuery(value);
    setSelectedIndex(0);
  }, [setQuery]);

  // Debounce search query for search execution
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Perform search
  const results = useMemo(() => {
    if (!debouncedQuery.trim()) {
      return [];
    }

    const query = debouncedQuery.trim();
    const deals = dealsData?.deals ?? [];
    const documents = documentsData?.documents ?? [];
    const transactions = transactionsData?.transactions ?? [];

    // Configure Fuse.js for properties (using API data)
    const propertyFuse = new Fuse(properties, {
      keys: [
        { name: 'name', weight: 2 },
        { name: 'address.street', weight: 1.5 },
        { name: 'address.city', weight: 1.5 },
        { name: 'address.submarket', weight: 1 },
        { name: 'propertyDetails.propertyClass', weight: 0.8 },
      ],
      threshold: 0.3,
      includeScore: true,
    });

    // Configure Fuse.js for deals
    const dealFuse = new Fuse(deals, {
      keys: [
        { name: 'propertyName', weight: 2 },
        { name: 'address.city', weight: 1.5 },
        { name: 'propertyType', weight: 1 },
        { name: 'stage', weight: 0.8 },
      ],
      threshold: 0.3,
      includeScore: true,
    });

    // Configure Fuse.js for documents
    const documentFuse = new Fuse(documents, {
      keys: [
        { name: 'name', weight: 2 },
        { name: 'propertyName', weight: 1.5 },
        { name: 'description', weight: 1 },
        { name: 'type', weight: 0.8 },
      ],
      threshold: 0.3,
      includeScore: true,
    });

    // Configure Fuse.js for transactions
    const transactionFuse = new Fuse(transactions, {
      keys: [
        { name: 'propertyName', weight: 2 },
        { name: 'description', weight: 1.5 },
        { name: 'type', weight: 1 },
        { name: 'category', weight: 0.8 },
      ],
      threshold: 0.3,
      includeScore: true,
    });

    // Search all data sources
    const propertyResults: SearchResult[] = propertyFuse
      .search(query)
      .slice(0, 5)
      .map((result) => ({
        type: 'property' as const,
        id: result.item.id,
        title: result.item.name,
        subtitle: `${result.item.address.street}, ${result.item.address.city}`,
        category: result.item.propertyDetails.propertyClass,
        metadata: {
          value: result.item.acquisition.purchasePrice.toLocaleString('en-US', {
            style: 'currency',
            currency: 'USD',
            maximumFractionDigits: 0,
          }),
        },
        item: result.item,
      }));

    const dealResults: SearchResult[] = dealFuse
      .search(query)
      .slice(0, 5)
      .map((result) => ({
        type: 'deal' as const,
        id: result.item.id,
        title: result.item.propertyName,
        subtitle: `${result.item.address.city} • ${result.item.stage}`,
        category: result.item.propertyType,
        metadata: {
          value: result.item.value.toLocaleString('en-US', {
            style: 'currency',
            currency: 'USD',
            maximumFractionDigits: 0,
          }),
        },
        item: result.item,
      }));

    const documentResults: SearchResult[] = documentFuse
      .search(query)
      .slice(0, 5)
      .map((result) => ({
        type: 'document' as const,
        id: result.item.id,
        title: result.item.name,
        subtitle: result.item.propertyName || result.item.description || 'Document',
        category: result.item.type,
        metadata: {
          property: result.item.propertyName,
        },
        item: result.item,
      }));

    const transactionResults: SearchResult[] = transactionFuse
      .search(query)
      .slice(0, 5)
      .map((result) => ({
        type: 'transaction' as const,
        id: result.item.id,
        title: result.item.propertyName,
        subtitle: result.item.description,
        category: result.item.type,
        metadata: {
          amount: result.item.amount.toLocaleString('en-US', {
            style: 'currency',
            currency: 'USD',
            maximumFractionDigits: 0,
          }),
          date: new Date(result.item.date).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
          }),
        },
        item: result.item,
      }));

    return [
      ...propertyResults,
      ...dealResults,
      ...documentResults,
      ...transactionResults,
    ];
  }, [debouncedQuery, properties, dealsData, documentsData, transactionsData]);

  // Use results directly - no need to sync to store
  // The local results are already computed and available for rendering

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd+K or Ctrl+K to open
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setOpen(true);
      }

      // Escape to close
      if (e.key === 'Escape' && isOpen) {
        setOpen(false);
        setQuery('');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, setOpen, setQuery]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(e.target as Node)) {
        setOpen(false);
        setQuery('');
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, setOpen, setQuery]);

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Determine available items based on search query
    let items: (SearchResult | string | QuickAction)[];
    if (searchQuery) {
      items = results;
    } else if (recentSearches.length > 0) {
      items = recentSearches;
    } else {
      items = quickActions;
    }

    const maxIndex = items.length - 1;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, maxIndex));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (searchQuery && results[selectedIndex]) {
          handleResultClick(results[selectedIndex]);
        } else if (!searchQuery && recentSearches.length > 0 && recentSearches[selectedIndex]) {
          setQuery(recentSearches[selectedIndex]);
        } else if (!searchQuery && recentSearches.length === 0 && quickActions[selectedIndex]) {
          handleQuickActionClick(quickActions[selectedIndex]);
        }
        break;
    }
  };

  const handleResultClick = (result: SearchResult) => {
    addRecentSearch(searchQuery);
    setOpen(false);
    setQuery('');

    // Navigate based on result type with highlighted item
    switch (result.type) {
      case 'property':
        navigate(`/investments?highlight=${result.id}`);
        break;
      case 'deal':
        navigate(`/deals?highlight=${result.id}`);
        break;
      case 'document':
        navigate(`/documents?highlight=${result.id}`);
        break;
      case 'transaction':
        navigate(`/transactions?highlight=${result.id}`);
        break;
    }
  };

  const handleRecentSearchClick = (query: string) => {
    setQuery(query);
    inputRef.current?.focus();
  };

  const handleClearRecentSearches = () => {
    clearRecentSearches();
    info('Recent searches cleared');
  };

  const handleQuickActionClick = (action: QuickAction) => {
    setOpen(false);
    setQuery('');
    navigate(action.path);
  };

  const getResultIcon = (type: SearchResult['type']) => {
    switch (type) {
      case 'property':
        return Building2;
      case 'deal':
        return TrendingUp;
      case 'document':
        return FileText;
      case 'transaction':
        return TrendingUp;
    }
  };

  const getCategoryColor = (type: SearchResult['type']) => {
    switch (type) {
      case 'property':
        return 'bg-blue-100 text-blue-700';
      case 'deal':
        return 'bg-green-100 text-green-700';
      case 'document':
        return 'bg-purple-100 text-purple-700';
      case 'transaction':
        return 'bg-orange-100 text-orange-700';
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/50 z-50 flex items-start justify-center pt-[10vh]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="search-dialog-title"
    >
      <div
        ref={modalRef}
        className="bg-white rounded-lg shadow-2xl w-full max-w-2xl mx-4"
      >
        <h2 id="search-dialog-title" className="sr-only">Global Search</h2>
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-neutral-200">
          <Search className="w-5 h-5 text-neutral-400" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Search properties, deals, documents..."
            value={searchQuery}
            onChange={(e) => handleQueryChange(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 outline-none text-neutral-900 placeholder-neutral-400"
            aria-label="Search properties, deals, documents"
            aria-autocomplete="list"
            aria-controls="search-results"
            aria-expanded={results.length > 0 || recentSearches.length > 0 || !searchQuery}
          />
          {searchQuery && (
            <button
              onClick={() => handleQueryChange('')}
              className="text-neutral-400 hover:text-neutral-600"
              aria-label="Clear search"
            >
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          )}
          <div className="flex items-center gap-1 text-xs text-neutral-400">
            <Command className="w-3 h-3" />
            <span>K</span>
          </div>
        </div>

        {/* Results */}
        <div id="search-results" className="max-h-[60vh] overflow-y-auto" role="listbox" aria-label="Search results">
          {searchQuery ? (
            <>
              {results.length > 0 ? (
                <div className="py-2">
                  {results.map((result, index) => {
                    const Icon = getResultIcon(result.type);
                    return (
                      <button
                        key={`${result.type}-${result.id}`}
                        onClick={() => handleResultClick(result)}
                        className={cn(
                          'w-full px-4 py-3 flex items-center gap-3 hover:bg-neutral-50 transition-colors text-left',
                          selectedIndex === index && 'bg-neutral-100'
                        )}
                      >
                        <div
                          className={cn(
                            'w-10 h-10 rounded-lg flex items-center justify-center',
                            getCategoryColor(result.type)
                          )}
                        >
                          <Icon className="w-5 h-5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-neutral-900 truncate">
                            {result.title}
                          </div>
                          <div className="text-sm text-neutral-500 truncate">
                            {result.subtitle}
                          </div>
                          {/* Metadata display */}
                          {result.metadata && (
                            <div className="flex items-center gap-2 mt-1 text-xs text-neutral-400">
                              {result.metadata.value && (
                                <span className="font-medium text-neutral-600">
                                  {result.metadata.value}
                                </span>
                              )}
                              {result.metadata.amount && (
                                <span className="font-medium text-neutral-600">
                                  {result.metadata.amount}
                                </span>
                              )}
                              {result.metadata.date && (
                                <span>{result.metadata.date}</span>
                              )}
                            </div>
                          )}
                        </div>
                        {result.category && (
                          <div className="text-xs text-neutral-400 px-2 py-1 bg-neutral-100 rounded">
                            {result.category}
                          </div>
                        )}
                        <ArrowRight className="w-4 h-4 text-neutral-400" />
                      </button>
                    );
                  })}
                </div>
              ) : (
                <div className="py-12 text-center text-neutral-400">
                  <Search className="w-12 h-12 mx-auto mb-3 opacity-40" />
                  <p>No results found</p>
                </div>
              )}
            </>
          ) : (
            <>
              {/* Recent Searches */}
              {recentSearches.length > 0 && (
                <div className="py-2">
                  <div className="px-4 py-2 flex items-center justify-between">
                    <div className="text-xs font-medium text-neutral-500 uppercase tracking-wide">
                      Recent Searches
                    </div>
                    <button
                      onClick={handleClearRecentSearches}
                      className="text-xs text-neutral-400 hover:text-neutral-600"
                    >
                      Clear
                    </button>
                  </div>
                  {recentSearches.map((query, index) => (
                    <button
                      key={query}
                      onClick={() => handleRecentSearchClick(query)}
                      className={cn(
                        'w-full px-4 py-3 flex items-center gap-3 hover:bg-neutral-50 transition-colors text-left',
                        selectedIndex === index && 'bg-neutral-100'
                      )}
                    >
                      <Clock className="w-4 h-4 text-neutral-400" />
                      <span className="text-neutral-900">{query}</span>
                    </button>
                  ))}
                </div>
              )}

              {/* Quick Actions (when no recent searches) */}
              {recentSearches.length === 0 && (
                <div className="py-2">
                  <div className="px-4 py-2">
                    <div className="text-xs font-medium text-neutral-500 uppercase tracking-wide">
                      Quick Navigation
                    </div>
                  </div>
                  {quickActions.map((action, index) => {
                    const Icon = action.icon;
                    return (
                      <button
                        key={action.id}
                        onClick={() => handleQuickActionClick(action)}
                        className={cn(
                          'w-full px-4 py-3 flex items-center gap-3 hover:bg-neutral-50 transition-colors text-left',
                          selectedIndex === index && 'bg-neutral-100'
                        )}
                      >
                        <div className="w-10 h-10 rounded-lg bg-neutral-100 flex items-center justify-center">
                          <Icon className="w-5 h-5 text-neutral-600" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-neutral-900">
                            {action.label}
                          </div>
                          <div className="text-sm text-neutral-500 truncate">
                            {action.description}
                          </div>
                        </div>
                        <ArrowRight className="w-4 h-4 text-neutral-400" />
                      </button>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-neutral-200 flex items-center justify-between text-xs text-neutral-400">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-neutral-100 rounded text-neutral-600">
                ^
              </kbd>
              <kbd className="px-1.5 py-0.5 bg-neutral-100 rounded text-neutral-600">
                v
              </kbd>
              <span>Navigate</span>
            </div>
            <div className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-neutral-100 rounded text-neutral-600">
                Enter
              </kbd>
              <span>Select</span>
            </div>
            <div className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-neutral-100 rounded text-neutral-600">
                ESC
              </kbd>
              <span>Close</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
