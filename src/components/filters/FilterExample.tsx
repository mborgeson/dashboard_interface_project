/**
 * EXAMPLE: How to use SavedFilters and useFilterPersistence
 * 
 * This example demonstrates integrating the Advanced Filters system into a page.
 * Copy this pattern to any page that needs filtering capabilities.
 */

import { useState } from 'react';
import { SavedFilters } from './SavedFilters';
import { useFilterPersistence } from '@/hooks/useFilterPersistence';

interface PropertyFilters {
  propertyClass?: string;
  city?: string;
  minUnits?: number;
  maxUnits?: number;
  searchTerm?: string;
}

export function FilterExample() {
  // 1. Define your filter state
  const [filters, setFilters] = useState<PropertyFilters>({});

  // 2. Enable URL persistence (optional but recommended)
  const { clearFilters, copyShareableUrl } = useFilterPersistence(
    filters,
    setFilters,
    {
      paramPrefix: 'prop_', // Unique prefix for your page
      excludeFields: ['searchTerm'], // Don't persist search in URL
      enabled: true,
    }
  );

  // 3. Apply filters to your data
  const filteredData = applyFilters(filters);

  return (
    <div className="p-6 space-y-6">
      {/* Filter Controls */}
      <div className="bg-white p-4 rounded-lg border border-neutral-200">
        <h2 className="font-semibold mb-4">Filters</h2>
        
        <div className="grid grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Property Class
            </label>
            <select
              value={filters.propertyClass || ''}
              onChange={(e) =>
                setFilters({ ...filters, propertyClass: e.target.value || undefined })
              }
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg"
            >
              <option value="">All Classes</option>
              <option value="A">Class A</option>
              <option value="B">Class B</option>
              <option value="C">Class C</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              City
            </label>
            <input
              type="text"
              value={filters.city || ''}
              onChange={(e) =>
                setFilters({ ...filters, city: e.target.value || undefined })
              }
              placeholder="Enter city..."
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Min Units
            </label>
            <input
              type="number"
              value={filters.minUnits || ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  minUnits: e.target.value ? parseInt(e.target.value) : undefined,
                })
              }
              placeholder="Min..."
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Max Units
            </label>
            <input
              type="number"
              value={filters.maxUnits || ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  maxUnits: e.target.value ? parseInt(e.target.value) : undefined,
                })
              }
              placeholder="Max..."
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg"
            />
          </div>
        </div>

        <div className="flex gap-2 mt-4">
          <button
            onClick={clearFilters}
            className="px-4 py-2 text-sm text-neutral-600 hover:text-neutral-900"
          >
            Clear All
          </button>
          <button
            onClick={async () => {
              const success = await copyShareableUrl();
              if (success) {
                alert('Filter URL copied to clipboard!');
              }
            }}
            className="px-4 py-2 text-sm text-primary-600 hover:text-primary-700"
          >
            Share Filters
          </button>
        </div>
      </div>

      {/* Saved Filters Sidebar */}
      <div className="grid grid-cols-4 gap-6">
        <div className="col-span-1">
          <SavedFilters
            currentFilters={filters as Record<string, unknown>}
            onApplyFilter={(savedFilters) => setFilters(savedFilters as PropertyFilters)}
            storageKey="property-filters" // Unique key for this page
          />
        </div>

        {/* Your filtered content */}
        <div className="col-span-3">
          <div className="bg-white p-6 rounded-lg border border-neutral-200">
            <h2 className="font-semibold mb-4">
              Results ({filteredData.length})
            </h2>
            {/* Render your filtered data here */}
            <pre className="text-xs text-neutral-600">
              {JSON.stringify(filters, null, 2)}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}

// Helper function to apply filters to your data
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function applyFilters(filters: PropertyFilters): unknown[] {
  // Implement your filter logic here
  // This is just a placeholder
  return [];
}
