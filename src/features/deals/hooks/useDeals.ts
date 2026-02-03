import { useState, useMemo } from 'react';
import type { Deal, DealStage } from '@/types/deal';

export interface DealFilters {
  stages: DealStage[];
  propertyTypes: string[];
  assignees: string[];
  valueRange: [number, number];
  searchQuery: string;
}

export type { DealFilters as DealFiltersType };

const DEFAULT_FILTERS: DealFilters = {
  stages: [],
  propertyTypes: [],
  assignees: [],
  valueRange: [0, 100000000],
  searchQuery: '',
};

export function useDeals(initialDeals: Deal[]) {
  // Track local stage overrides from drag-and-drop (keyed by deal ID)
  const [stageOverrides, setStageOverrides] = useState<Record<string, { stage: DealStage; timeline: Deal['timeline'] }>>({});
  const [filters, setFilters] = useState<DealFilters>(DEFAULT_FILTERS);

  // Merge API data with any local drag-and-drop overrides
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
    const closedDeals = filteredDeals.filter((d) => d.stage === 'closed');
    const realizedDeals = filteredDeals.filter((d) => d.stage === 'realized');
    const deadDeals = filteredDeals.filter((d) => d.stage === 'dead');

    const totalPipelineValue = filteredDeals.reduce(
      (sum, deal) => sum + deal.value,
      0
    );

    const avgDaysInPipeline =
      pipelineDeals.length > 0
        ? Math.round(
            pipelineDeals.reduce((sum, deal) => sum + deal.totalDaysInPipeline, 0) /
              pipelineDeals.length
          )
        : 0;

    const totalCompleted = closedDeals.length + realizedDeals.length + deadDeals.length;
    const winRate = totalCompleted > 0 ? (closedDeals.length + realizedDeals.length) / totalCompleted : 0;

    return {
      activeDealsCount: filteredDeals.length,
      pipelineValue: totalPipelineValue,
      avgDaysInPipeline,
      winRate,
      closedWonCount: closedDeals.length + realizedDeals.length,
      closedLostCount: deadDeals.length,
    };
  }, [filteredDeals]);

  const updateFilters = (updates: Partial<DealFilters>) => {
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
