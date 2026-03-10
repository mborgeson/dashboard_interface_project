import { useState, useMemo } from 'react';
import type { Deal, DealStage } from '@/types/deal';

export interface DealFilterState {
  stages: DealStage[];
  propertyTypes: string[];
  assignees: string[];
  valueRange: [number, number];
  searchQuery: string;
  lastSalePricePerUnitRange: [number | null, number | null];
  lastSaleDateRange: [number | null, number | null];
  equityCommitmentRange: [number | null, number | null];
}


const DEFAULT_FILTERS: DealFilterState = {
  stages: [],
  propertyTypes: [],
  assignees: [],
  valueRange: [0, 100000000],
  searchQuery: '',
  lastSalePricePerUnitRange: [null, null],
  lastSaleDateRange: [null, null],
  equityCommitmentRange: [null, null],
};

export function useDeals(initialDeals: Deal[]) {
  // Track local stage overrides from drag-and-drop (keyed by deal ID)
  const [stageOverrides, setStageOverrides] = useState<Record<string, { stage: DealStage; timeline: Deal['timeline'] }>>({});
  const [filters, setFilters] = useState<DealFilterState>(DEFAULT_FILTERS);

  // Merge API data with local drag-and-drop overrides.
  // Stale overrides (for deals no longer in the list) are simply ignored
  // during the map — no need to prune them from state.
  const deals = useMemo(() => {
    return initialDeals.map(deal => {
      const override = stageOverrides[deal.id];
      if (override) {
        return {
          ...deal,
          stage: override.stage,
          daysInStage: 0,
          timeline: override.timeline,
        };
      }
      return deal;
    });
  }, [initialDeals, stageOverrides]);

  // Update deal stage (for Kanban drag-and-drop)
  const updateDealStage = (dealId: string, newStage: DealStage, oldStage: DealStage) => {
    const deal = deals.find(d => d.id === dealId);
    if (!deal) return;

    setStageOverrides(prev => ({
      ...prev,
      [dealId]: {
        stage: newStage,
        timeline: [
          ...deal.timeline,
          {
            id: `${deal.id}-${Date.now()}`,
            date: new Date(),
            stage: newStage,
            description: `Moved from ${oldStage.replace('_', ' ')} to ${newStage.replace('_', ' ')}`,
            user: 'Current User',
          },
        ],
      },
    }));
  };

  // Get unique values for filter options
  const filterOptions = useMemo(() => {
    const propertyTypes = new Set<string>();
    const assignees = new Set<string>();

    deals.forEach((deal) => {
      propertyTypes.add(deal.propertyType);
      assignees.add(deal.assignee);
    });

    return {
      propertyTypes: Array.from(propertyTypes).sort(),
      assignees: Array.from(assignees).sort(),
    };
  }, [deals]);

  // Filter deals
  const filteredDeals = useMemo(() => {
    return deals.filter((deal) => {
      // Stage filter
      if (filters.stages.length > 0 && !filters.stages.includes(deal.stage)) {
        return false;
      }

      // Property type filter
      if (
        filters.propertyTypes.length > 0 &&
        !filters.propertyTypes.includes(deal.propertyType)
      ) {
        return false;
      }

      // Assignee filter
      if (
        filters.assignees.length > 0 &&
        !filters.assignees.includes(deal.assignee)
      ) {
        return false;
      }

      // Value range filter
      if (
        deal.value < filters.valueRange[0] ||
        deal.value > filters.valueRange[1]
      ) {
        return false;
      }

      // Last Sale Price/Unit filter
      const [minPPU, maxPPU] = filters.lastSalePricePerUnitRange;
      if (minPPU != null && (deal.lastSalePricePerUnit == null || deal.lastSalePricePerUnit < minPPU)) return false;
      if (maxPPU != null && (deal.lastSalePricePerUnit == null || deal.lastSalePricePerUnit > maxPPU)) return false;

      // Last Sale Date filter (year range)
      const [fromYear, toYear] = filters.lastSaleDateRange;
      if ((fromYear != null || toYear != null) && deal.lastSaleDate) {
        const saleYear = new Date(deal.lastSaleDate).getFullYear();
        if (fromYear != null && saleYear < fromYear) return false;
        if (toYear != null && saleYear > toYear) return false;
      }

      // Equity Commitment filter
      const [minEq, maxEq] = filters.equityCommitmentRange;
      if (minEq != null && (deal.totalEquityCommitment == null || deal.totalEquityCommitment < minEq)) return false;
      if (maxEq != null && (deal.totalEquityCommitment == null || deal.totalEquityCommitment > maxEq)) return false;

      // Search query filter
      if (filters.searchQuery) {
        const query = filters.searchQuery.toLowerCase();
        const matchesProperty = deal.propertyName.toLowerCase().includes(query);
        const matchesCity = deal.address.city.toLowerCase().includes(query);
        const matchesAssignee = deal.assignee.toLowerCase().includes(query);

        if (!matchesProperty && !matchesCity && !matchesAssignee) {
          return false;
        }
      }

      return true;
    });
  }, [deals, filters]);

  // Group deals by stage
  const dealsByStage = useMemo(() => {
    const grouped: Record<DealStage, Deal[]> = {
      dead: [],
      initial_review: [],
      active_review: [],
      under_contract: [],
      closed: [],
      realized: [],
    };

    filteredDeals.forEach((deal) => {
      grouped[deal.stage].push(deal);
    });

    return grouped;
  }, [filteredDeals]);

  // Calculate metrics from filtered deals
  const metrics = useMemo(() => {
    const pipelineDeals = filteredDeals.filter(
      (d) => d.stage !== 'closed' && d.stage !== 'realized' && d.stage !== 'dead'
    );
    const totalPipelineValue = filteredDeals.reduce(
      (sum, deal) => sum + deal.value,
      0
    );

    const totalUnits = pipelineDeals.reduce((sum, deal) => sum + (deal.units ?? 0), 0);

    const dealsWithYearBuilt = pipelineDeals.filter((d): d is typeof d & { yearBuilt: number } => d.yearBuilt != null && d.yearBuilt > 0);
    const avgVintage =
      dealsWithYearBuilt.length > 0
        ? Math.round(
            dealsWithYearBuilt.reduce((sum, d) => sum + d.yearBuilt, 0) /
              dealsWithYearBuilt.length,
          )
        : null;

    return {
      activeDealsCount: filteredDeals.length,
      pipelineValue: totalPipelineValue,
      totalUnits,
      avgVintage,
    };
  }, [filteredDeals]);

  const updateFilters = (updates: Partial<DealFilterState>) => {
    setFilters((prev) => ({ ...prev, ...updates }));
  };

  const clearFilters = () => {
    setFilters(DEFAULT_FILTERS);
  };

  return {
    filters,
    updateFilters,
    clearFilters,
    filteredDeals,
    dealsByStage,
    metrics,
    filterOptions,
    updateDealStage,
    deals,
  };
}
