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
  const [deals, setDeals] = useState<Deal[]>(initialDeals);
  const [filters, setFilters] = useState<DealFilters>(DEFAULT_FILTERS);

  // Update deal stage (for Kanban drag-and-drop)
  const updateDealStage = (dealId: string, newStage: DealStage, oldStage: DealStage) => {
    setDeals((prevDeals) =>
      prevDeals.map((deal) =>
        deal.id === dealId
          ? {
              ...deal,
              stage: newStage,
              daysInStage: 0, // Reset days in stage when moved
              timeline: [
                ...deal.timeline,
                {
                  id: `${deal.id}-${Date.now()}`,
                  date: new Date(),
                  stage: newStage,
                  description: `Moved from ${oldStage.replace('_', ' ')} to ${newStage.replace('_', ' ')}`,
                  user: 'Current User', // Would come from auth context in production
                },
              ],
            }
          : deal
      )
    );
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
      lead: [],
      underwriting: [],
      loi: [],
      due_diligence: [],
      closing: [],
      closed_won: [],
      closed_lost: [],
    };

    filteredDeals.forEach((deal) => {
      grouped[deal.stage].push(deal);
    });

    return grouped;
  }, [filteredDeals]);

  // Calculate metrics
  const metrics = useMemo(() => {
    const activeDeals = filteredDeals.filter(
      (d) => d.stage !== 'closed_won' && d.stage !== 'closed_lost'
    );
    const closedWon = filteredDeals.filter((d) => d.stage === 'closed_won');
    const closedLost = filteredDeals.filter((d) => d.stage === 'closed_lost');
    
    const totalPipelineValue = activeDeals.reduce(
      (sum, deal) => sum + deal.value,
      0
    );

    const avgDaysInPipeline =
      activeDeals.length > 0
        ? Math.round(
            activeDeals.reduce((sum, deal) => sum + deal.totalDaysInPipeline, 0) /
              activeDeals.length
          )
        : 0;

    const totalClosed = closedWon.length + closedLost.length;
    const winRate = totalClosed > 0 ? closedWon.length / totalClosed : 0;

    return {
      activeDealsCount: activeDeals.length,
      pipelineValue: totalPipelineValue,
      avgDaysInPipeline,
      winRate,
      closedWonCount: closedWon.length,
      closedLostCount: closedLost.length,
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
