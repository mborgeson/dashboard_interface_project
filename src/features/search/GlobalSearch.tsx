import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Building2, DollarSign, X } from 'lucide-react';
import { useGlobalSearch } from '@/hooks/useGlobalSearch';
import { cn } from '@/lib/utils';

export function GlobalSearch() {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const { results, isSearching } = useGlobalSearch(query);

  // Group results by type
  const propertyResults = results.filter((r) => r.type === 'property');
  const transactionResults = results.filter((r) => r.type === 'transaction');

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        resultsRef.current &&
        !resultsRef.current.contains(event.target as Node) &&
        !inputRef.current?.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle keyboard navigation
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (!isOpen || results.length === 0) return;

      switch (event.key) {
        case 'ArrowDown':
          event.preventDefault();
          setSelectedIndex((prev) => (prev < results.length - 1 ? prev + 1 : prev));
          break;
        case 'ArrowUp':
          event.preventDefault();
          setSelectedIndex((prev) => (prev > 0 ? prev - 1 : 0));
          break;
        case 'Enter':
          event.preventDefault();
          if (results[selectedIndex]) {
            handleSelectResult(results[selectedIndex]);
          }
          break;
        case 'Escape':
          event.preventDefault();
          setIsOpen(false);
          setQuery('');
          inputRef.current?.blur();
          break;
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, results, selectedIndex]);

  // Reset selected index when results change
  useEffect(() => {
    setSelectedIndex(0);
  }, [results]);

  const handleSelectResult = (result: typeof results[0]) => {
    if (result.type === 'property') {
      navigate(`/properties/${result.id}`);
    } else if (result.type === 'transaction') {
      // Navigate to transactions page (or property page with transaction highlighted)
      navigate(`/properties/${result.item.propertyId}`);
    }
    setIsOpen(false);
    setQuery('');
    inputRef.current?.blur();
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    setIsOpen(value.trim().length > 0);
  };

  const handleClearSearch = () => {
    setQuery('');
    setIsOpen(false);
    inputRef.current?.focus();
  };

  return (
    <div className="relative flex-1 max-w-2xl">
      {/* Search Input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={handleInputChange}
          onFocus={() => query.trim() && setIsOpen(true)}
          placeholder="Search properties, transactions..."
          className="w-full pl-10 pr-10 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
        />
        {query && (
          <button
            onClick={handleClearSearch}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Search Results Dropdown */}
      {isOpen && (
        <div
          ref={resultsRef}
          className="absolute top-full left-0 right-0 mt-2 bg-white border border-neutral-200 rounded-lg shadow-lg max-h-[500px] overflow-y-auto z-50"
        >
          {isSearching && (
            <div className="px-4 py-3 text-sm text-neutral-500">Searching...</div>
          )}

          {!isSearching && results.length === 0 && (
            <div className="px-4 py-8 text-center">
              <p className="text-sm text-neutral-500">No results found</p>
              <p className="text-xs text-neutral-400 mt-1">
                Try searching for a property name, address, or transaction
              </p>
            </div>
          )}

          {!isSearching && results.length > 0 && (
            <>
              {/* Properties Section */}
              {propertyResults.length > 0 && (
                <div className="border-b border-neutral-200">
                  <div className="px-4 py-2 text-xs font-semibold text-neutral-500 uppercase tracking-wider bg-neutral-50">
                    Properties ({propertyResults.length})
                  </div>
                  {propertyResults.map((result, index) => {
                    const globalIndex = results.findIndex((r) => r.id === result.id);
                    return (
                      <button
                        key={result.id}
                        onClick={() => handleSelectResult(result)}
                        className={cn(
                          'w-full px-4 py-3 text-left hover:bg-neutral-50 transition-colors flex items-start gap-3',
                          selectedIndex === globalIndex && 'bg-primary-50'
                        )}
                      >
                        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-primary-100 text-primary-600 flex items-center justify-center mt-0.5">
                          <Building2 className="w-4 h-4" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-neutral-900 truncate">
                            {result.title}
                          </div>
                          <div className="text-xs text-neutral-500 truncate">
                            {result.subtitle}
                          </div>
                          {result.matchedField && (
                            <div className="text-xs text-neutral-400 mt-0.5">
                              Matched: {formatFieldName(result.matchedField)}
                            </div>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}

              {/* Transactions Section */}
              {transactionResults.length > 0 && (
                <div>
                  <div className="px-4 py-2 text-xs font-semibold text-neutral-500 uppercase tracking-wider bg-neutral-50">
                    Transactions ({transactionResults.length})
                  </div>
                  {transactionResults.map((result, index) => {
                    const globalIndex = results.findIndex((r) => r.id === result.id);
                    return (
                      <button
                        key={result.id}
                        onClick={() => handleSelectResult(result)}
                        className={cn(
                          'w-full px-4 py-3 text-left hover:bg-neutral-50 transition-colors flex items-start gap-3',
                          selectedIndex === globalIndex && 'bg-primary-50'
                        )}
                      >
                        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-emerald-100 text-emerald-600 flex items-center justify-center mt-0.5">
                          <DollarSign className="w-4 h-4" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-neutral-900 truncate">
                            {result.title}
                          </div>
                          <div className="text-xs text-neutral-500 line-clamp-2">
                            {result.subtitle}
                          </div>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs text-neutral-400">
                              {formatTransactionType(result.item.type)}
                            </span>
                            {result.item.category && (
                              <>
                                <span className="text-neutral-300">•</span>
                                <span className="text-xs text-neutral-400">
                                  {result.item.category}
                                </span>
                              </>
                            )}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </>
          )}

          {/* Keyboard Hints */}
          {results.length > 0 && (
            <div className="px-4 py-2 border-t border-neutral-200 bg-neutral-50">
              <div className="flex items-center gap-4 text-xs text-neutral-500">
                <span>
                  <kbd className="px-1.5 py-0.5 bg-white border border-neutral-300 rounded text-xs">
                    ↑↓
                  </kbd>{' '}
                  Navigate
                </span>
                <span>
                  <kbd className="px-1.5 py-0.5 bg-white border border-neutral-300 rounded text-xs">
                    Enter
                  </kbd>{' '}
                  Select
                </span>
                <span>
                  <kbd className="px-1.5 py-0.5 bg-white border border-neutral-300 rounded text-xs">
                    Esc
                  </kbd>{' '}
                  Close
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function formatFieldName(field: string): string {
  const fieldMap: Record<string, string> = {
    name: 'Property Name',
    'address.street': 'Street Address',
    'address.city': 'City',
    'address.submarket': 'Submarket',
    'propertyDetails.propertyClass': 'Property Class',
    propertyName: 'Property Name',
    description: 'Description',
    type: 'Transaction Type',
    category: 'Category',
  };
  return fieldMap[field] || field;
}

function formatTransactionType(type: string): string {
  const typeMap: Record<string, string> = {
    acquisition: 'Acquisition',
    disposition: 'Disposition',
    capital_improvement: 'Capital Improvement',
    refinance: 'Refinance',
    distribution: 'Distribution',
  };
  return typeMap[type] || type;
}
