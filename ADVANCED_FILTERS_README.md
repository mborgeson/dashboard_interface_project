# Advanced Filters System - B&R Capital Dashboard

Complete implementation of the Advanced Filters system with global search, saved filters, and URL persistence.

## 📁 File Structure

```
src/
├── stores/
│   ├── searchStore.ts              # Zustand store for search state
│   └── index.ts                    # Store exports
├── components/
│   ├── GlobalSearch.tsx            # Command palette search modal
│   ├── filters/
│   │   ├── SavedFilters.tsx        # Saved filter management
│   │   ├── FilterExample.tsx       # Usage example
│   │   └── index.ts                # Filter exports
│   └── index.ts                    # Component exports
├── hooks/
│   ├── useFilterPersistence.ts     # URL-based filter sync
│   ├── useGlobalSearch.ts          # Search hook (existing)
│   └── index.ts                    # Hook exports
└── app/layout/
    └── TopNav.tsx                  # Updated with search trigger
```

## 🎯 Features

### 1. Global Search (Cmd+K / Ctrl+K)

**File:** `src/components/GlobalSearch.tsx`

Command palette-style search across:
- Properties
- Deals
- Documents
- Transactions

**Features:**
- Fuzzy search with Fuse.js
- Keyboard navigation (↑↓ arrows, Enter, Escape)
- Recent searches (stored in localStorage, max 10)
- Grouped results by type with icons
- Click outside to close
- Visual feedback for selected items

**Usage:**
```tsx
import { GlobalSearch } from '@/components/GlobalSearch';
import { useSearchStore } from '@/stores/searchStore';

function MyComponent() {
  const { setOpen } = useSearchStore();
  
  return (
    <>
      <button onClick={() => setOpen(true)}>
        Open Search
      </button>
      <GlobalSearch />
    </>
  );
}
```

### 2. Search Store

**File:** `src/stores/searchStore.ts`

Zustand store managing:
- `searchQuery`: Current search text
- `recentSearches`: Last 10 searches (localStorage)
- `searchResults`: Grouped search results
- `isOpen`: Modal open/closed state

**API:**
```typescript
const {
  searchQuery,
  recentSearches,
  searchResults,
  isOpen,
  setQuery,
  addRecentSearch,
  clearRecentSearches,
  setResults,
  toggleOpen,
  setOpen,
} = useSearchStore();
```

### 3. Saved Filters

**File:** `src/components/filters/SavedFilters.tsx`

Save and manage filter configurations:
- Save current filters with custom name
- Quick-apply saved filters
- Delete saved filters
- Visual indicator for active filter
- localStorage persistence

**Usage:**
```tsx
import { SavedFilters } from '@/components/filters';

function MyPage() {
  const [filters, setFilters] = useState({});
  
  return (
    <SavedFilters
      currentFilters={filters}
      onApplyFilter={setFilters}
      storageKey="my-page-filters" // Unique per page
    />
  );
}
```

**Props:**
- `currentFilters`: Current filter state object
- `onApplyFilter`: Callback when filter is applied
- `storageKey`: localStorage key (default: 'br-capital-saved-filters')

### 4. Filter Persistence Hook

**File:** `src/hooks/useFilterPersistence.ts`

URL-based filter persistence for shareable views:
- Syncs filters to URL search parameters
- Restores filters from URL on load
- Shareable filtered views via URL
- Configurable field exclusions

**Usage:**
```tsx
import { useFilterPersistence } from '@/hooks/useFilterPersistence';

function MyPage() {
  const [filters, setFilters] = useState({
    city: '',
    propertyClass: '',
    minUnits: undefined,
  });

  const { clearFilters, copyShareableUrl } = useFilterPersistence(
    filters,
    setFilters,
    {
      paramPrefix: 'prop_',           // URL param prefix
      excludeFields: ['searchTerm'],  // Don't persist in URL
      enabled: true,                  // Enable/disable
    }
  );

  return (
    <div>
      {/* Your filter controls */}
      <button onClick={clearFilters}>Clear All</button>
      <button onClick={copyShareableUrl}>Share URL</button>
    </div>
  );
}
```

**Options:**
- `paramPrefix`: Prefix for URL params (default: 'f_')
- `excludeFields`: Fields to exclude from URL
- `enabled`: Enable/disable persistence (default: true)

**Returns:**
- `clearFilters()`: Clear all filters and URL params
- `getShareableUrl()`: Get current URL with filters
- `copyShareableUrl()`: Copy URL to clipboard

## 🚀 Quick Start

### Example: Properties Page with Full Filtering

```tsx
import { useState } from 'react';
import { SavedFilters } from '@/components/filters';
import { useFilterPersistence } from '@/hooks/useFilterPersistence';

interface PropertyFilters {
  propertyClass?: string;
  city?: string;
  minUnits?: number;
  maxUnits?: number;
}

export function PropertiesPage() {
  const [filters, setFilters] = useState<PropertyFilters>({});

  // Enable URL persistence
  const { clearFilters, copyShareableUrl } = useFilterPersistence(
    filters,
    setFilters,
    {
      paramPrefix: 'prop_',
      enabled: true,
    }
  );

  return (
    <div className="p-6">
      <div className="grid grid-cols-4 gap-6">
        {/* Saved Filters Sidebar */}
        <div>
          <SavedFilters
            currentFilters={filters}
            onApplyFilter={setFilters}
            storageKey="properties-filters"
          />
        </div>

        {/* Main Content */}
        <div className="col-span-3">
          {/* Filter Controls */}
          <div className="mb-6">
            <select
              value={filters.propertyClass || ''}
              onChange={(e) =>
                setFilters({ ...filters, propertyClass: e.target.value })
              }
            >
              <option value="">All Classes</option>
              <option value="A">Class A</option>
              <option value="B">Class B</option>
            </select>
            
            <button onClick={clearFilters}>Clear</button>
            <button onClick={copyShareableUrl}>Share</button>
          </div>

          {/* Filtered Results */}
          <div>
            {/* Your filtered content here */}
          </div>
        </div>
      </div>
    </div>
  );
}
```

## 🎨 UI Components

All components use existing design system:
- Tailwind CSS for styling
- Lucide icons
- `cn()` utility from `@/lib/utils`
- Consistent color scheme with primary/neutral colors

## 🔧 Technical Details

### Dependencies
- `zustand`: State management
- `fuse.js`: Fuzzy search
- `react-router-dom`: URL navigation
- `lucide-react`: Icons

### Storage
- **localStorage** for:
  - Recent searches (search store)
  - Saved filters (per page)
- **URL params** for:
  - Filter state (shareable views)
  
### Performance
- Debounced search (300ms)
- Efficient fuzzy matching with Fuse.js
- URL updates use replace mode (no history spam)
- Keyboard shortcuts with proper cleanup

## 📝 Integration Checklist

To add filtering to a new page:

- [ ] Define filter interface type
- [ ] Create filter state with `useState`
- [ ] Add `useFilterPersistence` hook
- [ ] Add `<SavedFilters>` component
- [ ] Create filter controls (inputs, selects)
- [ ] Wire up filter controls to state
- [ ] Apply filters to data
- [ ] Add clear/share buttons
- [ ] Choose unique `storageKey` and `paramPrefix`

## 🎹 Keyboard Shortcuts

### Global Search (Cmd+K / Ctrl+K)
- **Open**: `Cmd/Ctrl + K`
- **Navigate**: `↑` / `↓` arrows
- **Select**: `Enter`
- **Close**: `Escape`
- **Clear**: Click X or backspace

### Saved Filters
- **Save**: Click "Save Current" → Enter name → Enter/Click checkmark
- **Cancel**: Escape key while naming

## 🎯 Best Practices

1. **Unique Keys**: Use unique `storageKey` and `paramPrefix` per page
2. **Exclude Sensitive Data**: Don't persist sensitive filters in URL
3. **Type Safety**: Define filter interfaces for type checking
4. **Clear Empty Values**: Set to `undefined` instead of empty strings
5. **Debounce Inputs**: For text inputs, debounce changes
6. **Error Handling**: Wrap localStorage in try/catch (included)

## 🐛 Troubleshooting

**Search not opening?**
- Check if `GlobalSearch` component is rendered
- Verify keyboard shortcut isn't conflicting
- Check browser console for errors

**Filters not persisting in URL?**
- Verify `enabled: true` in options
- Check if `paramPrefix` is unique
- Ensure filter values aren't `null` or empty strings

**Saved filters not loading?**
- Check localStorage quota
- Verify unique `storageKey` per page
- Check browser console for errors

**Recent searches not showing?**
- Check localStorage availability
- Verify search query is being added
- Max 10 recent searches (oldest removed)

## 📚 Related Files

- `src/data/mockProperties.ts` - Property data
- `src/data/mockDeals.ts` - Deal data
- `src/data/mockDocuments.ts` - Document data
- `src/data/mockTransactions.ts` - Transaction data
- `src/app/layout/TopNav.tsx` - Header with search trigger

## 🔄 Future Enhancements

Potential improvements:
- [ ] Advanced filter operators (AND/OR logic)
- [ ] Filter templates/presets
- [ ] Export filters as JSON
- [ ] Import filters from JSON
- [ ] Filter history/undo
- [ ] Multi-select filters
- [ ] Date range pickers
- [ ] Filter analytics
- [ ] Collaborative filter sharing
- [ ] AI-powered filter suggestions
