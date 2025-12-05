# Global Search Feature

A comprehensive search feature for the B&R Capital Real Estate Dashboard using Fuse.js for fuzzy searching across properties and transactions.

## Features

- **Fuzzy Search**: Uses Fuse.js for intelligent, typo-tolerant searching
- **Debounced Input**: 300ms debounce to reduce unnecessary searches
- **Grouped Results**: Results are categorized into Properties and Transactions
- **Keyboard Navigation**: Full keyboard support with arrow keys, Enter, and Escape
- **Visual Feedback**: Highlights matched fields and shows search context
- **Click Outside Detection**: Dropdown closes when clicking outside
- **Result Limit**: Shows top 10 most relevant results
- **Navigation Integration**: Clicking a result navigates to the appropriate page

## Search Capabilities

### Properties
Searches across:
- Property Name (highest weight)
- Street Address
- City
- Submarket
- Property Class (A, B, C)

### Transactions
Searches across:
- Property Name
- Description
- Transaction Type (acquisition, refinance, etc.)
- Category

## Usage

The GlobalSearch component is integrated into the TopNav and automatically handles:
- Search input management
- Debouncing
- Result fetching
- Keyboard navigation
- Navigation on result selection

## Implementation Details

### Files Created

1. **src/hooks/useGlobalSearch.ts**
   - Custom hook for search logic
   - Handles debouncing
   - Configures Fuse.js instances
   - Combines and ranks results

2. **src/features/search/GlobalSearch.tsx**
   - Main search component
   - UI and interaction handling
   - Keyboard navigation
   - Click outside detection

3. **src/features/search/index.ts**
   - Barrel export for clean imports

### Dependencies

- `fuse.js`: ^7.1.0 (already installed)
- `react-router-dom`: For navigation
- `lucide-react`: For icons

### Configuration

Fuse.js is configured with:
- `threshold: 0.3` - Balanced fuzzy matching
- `includeScore: true` - For ranking results
- `includeMatches: true` - To show matched fields
- Weighted keys for relevance-based ranking

## Keyboard Shortcuts

- `↑/↓` - Navigate through results
- `Enter` - Select current result
- `Esc` - Close dropdown and clear search
- `Click outside` - Close dropdown

## Future Enhancements

Potential improvements:
- Search history
- Recently viewed items
- Advanced filters (date range, amount range, etc.)
- Search analytics
- Saved searches
- Export search results
