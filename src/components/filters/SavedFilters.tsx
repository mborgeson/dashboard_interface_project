import { useState, useEffect } from 'react';
import { Star, Trash2, Plus, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/useToast';

export interface SavedFilter {
  id: string;
  name: string;
  filters: Record<string, any>;
  createdAt: Date;
}

interface SavedFiltersProps {
  currentFilters: Record<string, any>;
  onApplyFilter: (filters: Record<string, any>) => void;
  storageKey?: string;
}

const DEFAULT_STORAGE_KEY = 'br-capital-saved-filters';

export function SavedFilters({
  currentFilters,
  onApplyFilter,
  storageKey = DEFAULT_STORAGE_KEY,
}: SavedFiltersProps) {
  const [savedFilters, setSavedFilters] = useState<SavedFilter[]>([]);
  const [isAddingNew, setIsAddingNew] = useState(false);
  const [newFilterName, setNewFilterName] = useState('');
  const [appliedFilterId, setAppliedFilterId] = useState<string | null>(null);
  const { success, info } = useToast();

  // Load saved filters from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        // Convert date strings back to Date objects
        const filters = parsed.map((f: any) => ({
          ...f,
          createdAt: new Date(f.createdAt),
        }));
        setSavedFilters(filters);
      }
    } catch (error) {
      console.error('Failed to load saved filters:', error);
    }
  }, [storageKey]);

  // Save filters to localStorage
  const saveToStorage = (filters: SavedFilter[]) => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(filters));
    } catch (error) {
      console.error('Failed to save filters:', error);
    }
  };

  // Check if current filters match any saved filter
  useEffect(() => {
    const matchingFilter = savedFilters.find((saved) =>
      JSON.stringify(saved.filters) === JSON.stringify(currentFilters)
    );
    setAppliedFilterId(matchingFilter?.id || null);
  }, [currentFilters, savedFilters]);

  const handleSaveFilter = () => {
    if (!newFilterName.trim()) return;

    const newFilter: SavedFilter = {
      id: `filter-${Date.now()}`,
      name: newFilterName.trim(),
      filters: currentFilters,
      createdAt: new Date(),
    };

    const updated = [...savedFilters, newFilter];
    setSavedFilters(updated);
    saveToStorage(updated);

    success('Filter saved', { description: newFilterName.trim() });

    setNewFilterName('');
    setIsAddingNew(false);
  };

  const handleDeleteFilter = (id: string) => {
    const updated = savedFilters.filter((f) => f.id !== id);
    setSavedFilters(updated);
    saveToStorage(updated);

    info('Filter deleted');

    if (appliedFilterId === id) {
      setAppliedFilterId(null);
    }
  };

  const handleApplyFilter = (filter: SavedFilter) => {
    onApplyFilter(filter.filters);
    setAppliedFilterId(filter.id);
    info('Filter applied');
  };

  const hasActiveFilters = Object.keys(currentFilters).length > 0;

  return (
    <div className="bg-white border border-neutral-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Star className="w-4 h-4 text-primary-600" />
          <h3 className="font-medium text-neutral-900">Saved Filters</h3>
        </div>
        {hasActiveFilters && !isAddingNew && (
          <button
            onClick={() => setIsAddingNew(true)}
            className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
          >
            <Plus className="w-4 h-4" />
            Save Current
          </button>
        )}
      </div>

      {/* Save New Filter Form */}
      {isAddingNew && (
        <div className="mb-3 flex gap-2">
          <input
            type="text"
            value={newFilterName}
            onChange={(e) => setNewFilterName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSaveFilter();
              if (e.key === 'Escape') {
                setIsAddingNew(false);
                setNewFilterName('');
              }
            }}
            placeholder="Filter name..."
            className="flex-1 px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            autoFocus
          />
          <button
            onClick={handleSaveFilter}
            disabled={!newFilterName.trim()}
            className="px-3 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Check className="w-4 h-4" />
          </button>
          <button
            onClick={() => {
              setIsAddingNew(false);
              setNewFilterName('');
            }}
            className="px-3 py-2 border border-neutral-300 rounded-lg hover:bg-neutral-50"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Saved Filters List */}
      {savedFilters.length > 0 ? (
        <div className="space-y-2">
          {savedFilters.map((filter) => {
            const isApplied = appliedFilterId === filter.id;
            const filterCount = Object.keys(filter.filters).length;

            return (
              <div
                key={filter.id}
                className={cn(
                  'flex items-center justify-between p-3 rounded-lg border transition-colors',
                  isApplied
                    ? 'bg-primary-50 border-primary-200'
                    : 'bg-neutral-50 border-neutral-200 hover:bg-neutral-100'
                )}
              >
                <button
                  onClick={() => handleApplyFilter(filter)}
                  className="flex-1 text-left"
                >
                  <div className="font-medium text-neutral-900 flex items-center gap-2">
                    {filter.name}
                    {isApplied && (
                      <Check className="w-4 h-4 text-primary-600" />
                    )}
                  </div>
                  <div className="text-xs text-neutral-500 mt-1">
                    {filterCount} filter{filterCount !== 1 ? 's' : ''} •{' '}
                    {filter.createdAt.toLocaleDateString()}
                  </div>
                </button>
                <button
                  onClick={() => handleDeleteFilter(filter.id)}
                  className="p-2 text-neutral-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                  title="Delete filter"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-center py-8 text-neutral-400">
          <Star className="w-12 h-12 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No saved filters yet</p>
          <p className="text-xs mt-1">
            Apply filters and save them for quick access
          </p>
        </div>
      )}
    </div>
  );
}
