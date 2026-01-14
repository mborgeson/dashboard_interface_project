import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const MAX_COMPARISON_DEALS = 4;
const MIN_COMPARISON_DEALS = 2;

interface ComparisonState {
  // Selected deal IDs for comparison
  selectedDealIds: Set<string>;
  // Whether the comparison selector modal is open
  selectorOpen: boolean;

  // Actions
  addDeal: (dealId: string) => boolean;
  removeDeal: (dealId: string) => void;
  toggleDeal: (dealId: string) => boolean;
  clearSelection: () => void;
  setSelectorOpen: (open: boolean) => void;

  // Computed
  canCompare: () => boolean;
  isAtMax: () => boolean;
  isDealSelected: (dealId: string) => boolean;
  getSelectedCount: () => number;
  getComparisonUrl: () => string;
}

export const useComparisonStore = create<ComparisonState>()(
  persist(
    (set, get) => ({
      selectedDealIds: new Set<string>(),
      selectorOpen: false,

      addDeal: (dealId: string) => {
        const { selectedDealIds } = get();
        if (selectedDealIds.size >= MAX_COMPARISON_DEALS) {
          return false;
        }
        set((state) => ({
          selectedDealIds: new Set([...state.selectedDealIds, dealId]),
        }));
        return true;
      },

      removeDeal: (dealId: string) => {
        set((state) => {
          const newSet = new Set(state.selectedDealIds);
          newSet.delete(dealId);
          return { selectedDealIds: newSet };
        });
      },

      toggleDeal: (dealId: string) => {
        const { selectedDealIds } = get();
        if (selectedDealIds.has(dealId)) {
          get().removeDeal(dealId);
          return false;
        } else {
          return get().addDeal(dealId);
        }
      },

      clearSelection: () => {
        set({ selectedDealIds: new Set<string>() });
      },

      setSelectorOpen: (open: boolean) => {
        set({ selectorOpen: open });
      },

      canCompare: () => {
        const { selectedDealIds } = get();
        return selectedDealIds.size >= MIN_COMPARISON_DEALS;
      },

      isAtMax: () => {
        const { selectedDealIds } = get();
        return selectedDealIds.size >= MAX_COMPARISON_DEALS;
      },

      isDealSelected: (dealId: string) => {
        const { selectedDealIds } = get();
        return selectedDealIds.has(dealId);
      },

      getSelectedCount: () => {
        const { selectedDealIds } = get();
        return selectedDealIds.size;
      },

      getComparisonUrl: () => {
        const { selectedDealIds } = get();
        if (selectedDealIds.size < MIN_COMPARISON_DEALS) return '';
        const idsParam = Array.from(selectedDealIds).join(',');
        return `/deals/compare?ids=${idsParam}`;
      },
    }),
    {
      name: 'deal-comparison-storage',
      // Custom serialization for Set
      storage: {
        getItem: (name) => {
          const str = localStorage.getItem(name);
          if (!str) return null;
          const parsed = JSON.parse(str);
          return {
            ...parsed,
            state: {
              ...parsed.state,
              selectedDealIds: new Set(parsed.state.selectedDealIds || []),
            },
          };
        },
        setItem: (name, value) => {
          const serialized = {
            ...value,
            state: {
              ...value.state,
              selectedDealIds: Array.from(value.state.selectedDealIds || []),
            },
          };
          localStorage.setItem(name, JSON.stringify(serialized));
        },
        removeItem: (name) => localStorage.removeItem(name),
      },
    }
  )
);

// Export constants
export { MAX_COMPARISON_DEALS, MIN_COMPARISON_DEALS };
