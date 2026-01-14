import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

// Quick action types
export type QuickAction =
  | { type: 'watchlist'; dealId: string }
  | { type: 'compare'; dealId: string }
  | { type: 'share'; entityType: string; entityId: string }
  | { type: 'export-pdf'; entityType: string; entityId: string }
  | { type: 'add-note'; entityType: string; entityId: string };

// Recent action tracking
interface RecentAction {
  id: string;
  action: QuickAction;
  timestamp: number;
  label: string;
}

// Context state
interface QuickActionsState {
  // Command palette
  commandPaletteOpen: boolean;
  openCommandPalette: () => void;
  closeCommandPalette: () => void;
  toggleCommandPalette: () => void;

  // Deal comparison
  selectedDealsForComparison: string[];
  addDealToCompare: (dealId: string) => void;
  removeDealFromCompare: (dealId: string) => void;
  clearComparisonSelection: () => void;
  isInCompareMode: boolean;
  toggleCompareMode: () => void;

  // Watchlist
  watchlistIds: string[];
  toggleWatchlist: (dealId: string) => void;
  isInWatchlist: (dealId: string) => boolean;

  // Recent actions
  recentActions: RecentAction[];
  addRecentAction: (action: QuickAction, label: string) => void;
  clearRecentActions: () => void;

  // Shortcuts help
  shortcutsHelpOpen: boolean;
  openShortcutsHelp: () => void;
  closeShortcutsHelp: () => void;
}

const QuickActionsContext = createContext<QuickActionsState | null>(null);

const MAX_RECENT_ACTIONS = 10;
const MAX_COMPARE_DEALS = 4;

interface QuickActionsProviderProps {
  children: ReactNode;
}

export function QuickActionsProvider({ children }: QuickActionsProviderProps) {
  // Command palette state
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  // Comparison state
  const [selectedDealsForComparison, setSelectedDealsForComparison] = useState<string[]>([]);
  const [isInCompareMode, setIsInCompareMode] = useState(false);

  // Watchlist state
  const [watchlistIds, setWatchlistIds] = useState<string[]>([]);

  // Recent actions state
  const [recentActions, setRecentActions] = useState<RecentAction[]>([]);

  // Shortcuts help state
  const [shortcutsHelpOpen, setShortcutsHelpOpen] = useState(false);

  // Command palette handlers
  const openCommandPalette = useCallback(() => setCommandPaletteOpen(true), []);
  const closeCommandPalette = useCallback(() => setCommandPaletteOpen(false), []);
  const toggleCommandPalette = useCallback(() => setCommandPaletteOpen((prev) => !prev), []);

  // Comparison handlers
  const addDealToCompare = useCallback((dealId: string) => {
    setSelectedDealsForComparison((prev) => {
      if (prev.includes(dealId)) return prev;
      if (prev.length >= MAX_COMPARE_DEALS) {
        // Remove the first one and add the new one
        return [...prev.slice(1), dealId];
      }
      return [...prev, dealId];
    });
  }, []);

  const removeDealFromCompare = useCallback((dealId: string) => {
    setSelectedDealsForComparison((prev) => prev.filter((id) => id !== dealId));
  }, []);

  const clearComparisonSelection = useCallback(() => {
    setSelectedDealsForComparison([]);
    setIsInCompareMode(false);
  }, []);

  const toggleCompareMode = useCallback(() => {
    setIsInCompareMode((prev) => !prev);
  }, []);

  // Watchlist handlers
  const toggleWatchlist = useCallback((dealId: string) => {
    setWatchlistIds((prev) => {
      if (prev.includes(dealId)) {
        return prev.filter((id) => id !== dealId);
      }
      return [...prev, dealId];
    });
  }, []);

  const isInWatchlist = useCallback(
    (dealId: string) => watchlistIds.includes(dealId),
    [watchlistIds]
  );

  // Recent actions handlers
  const addRecentAction = useCallback((action: QuickAction, label: string) => {
    const newAction: RecentAction = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      action,
      timestamp: Date.now(),
      label,
    };
    setRecentActions((prev) => [newAction, ...prev].slice(0, MAX_RECENT_ACTIONS));
  }, []);

  const clearRecentActions = useCallback(() => {
    setRecentActions([]);
  }, []);

  // Shortcuts help handlers
  const openShortcutsHelp = useCallback(() => setShortcutsHelpOpen(true), []);
  const closeShortcutsHelp = useCallback(() => setShortcutsHelpOpen(false), []);

  const value: QuickActionsState = {
    commandPaletteOpen,
    openCommandPalette,
    closeCommandPalette,
    toggleCommandPalette,
    selectedDealsForComparison,
    addDealToCompare,
    removeDealFromCompare,
    clearComparisonSelection,
    isInCompareMode,
    toggleCompareMode,
    watchlistIds,
    toggleWatchlist,
    isInWatchlist,
    recentActions,
    addRecentAction,
    clearRecentActions,
    shortcutsHelpOpen,
    openShortcutsHelp,
    closeShortcutsHelp,
  };

  return (
    <QuickActionsContext.Provider value={value}>
      {children}
    </QuickActionsContext.Provider>
  );
}

export function useQuickActions() {
  const context = useContext(QuickActionsContext);
  if (!context) {
    throw new Error('useQuickActions must be used within a QuickActionsProvider');
  }
  return context;
}
