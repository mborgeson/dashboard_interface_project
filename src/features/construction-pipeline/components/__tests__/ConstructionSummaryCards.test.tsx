import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';

/**
 * Regression test: Construction Pipeline summary cards should show "--"
 * for missing pipeline statuses instead of "0".
 *
 * Bug: When a pipeline status (e.g. "delivered") has no data, the summary
 * card displayed "0" (as if 0 units), which is misleading. It should show
 * "--" to indicate missing data, and "No data" for the project count.
 */

// We need to mock the hooks to control the data
vi.mock('../../hooks/useConstructionData', () => ({
  useProjects: () => ({ data: { data: [], total: 0, page: 1, pageSize: 50, totalPages: 1 }, isLoading: false, error: null }),
  useAllProjects: () => ({ data: [], isLoading: false }),
  usePipelineSummary: () => ({
    data: [
      // Only return data for 2 of 5 statuses — others should show "--"
      { status: 'proposed', projectCount: 5, totalUnits: 1200 },
      { status: 'under_construction', projectCount: 10, totalUnits: 3500 },
    ],
    isLoading: false,
  }),
  usePipelineFunnel: () => ({ data: [], isLoading: false }),
  usePermitTrends: () => ({ data: [], isLoading: false }),
  useEmploymentOverlay: () => ({ data: [], isLoading: false }),
  useSubmarketPipeline: () => ({ data: [], isLoading: false }),
  useClassificationBreakdown: () => ({ data: [], isLoading: false }),
  useDeliveryTimeline: () => ({ data: [], isLoading: false }),
  useConstructionDataQuality: () => ({ data: undefined, isLoading: false }),
  useConstructionImportStatus: () => ({ data: undefined, isLoading: false }),
  useTriggerConstructionImport: () => ({ mutate: vi.fn(), isPending: false }),
  useConstructionFilterOptions: () => ({ data: undefined, isLoading: false }),
}));

// Dynamically import AFTER mocks are set up
const { ConstructionPipelinePage } = await import('../../ConstructionPipelinePage');

describe('ConstructionPipelinePage summary cards', () => {
  it('shows "--" for statuses with no data instead of "0"', () => {
    render(<ConstructionPipelinePage />);

    // "Proposed" and "Under Constr." should have real numbers
    expect(screen.getByText('1,200')).toBeInTheDocument(); // proposed totalUnits
    expect(screen.getByText('3,500')).toBeInTheDocument(); // under_construction totalUnits
    expect(screen.getByText('5 projects')).toBeInTheDocument();
    expect(screen.getByText('10 projects')).toBeInTheDocument();

    // Statuses without data (final_planning, permitted, delivered) should show "--"
    const dashElements = screen.getAllByText('--');
    expect(dashElements.length).toBeGreaterThanOrEqual(3); // 3 missing statuses

    // Should show "No data" for missing statuses, not "0 projects"
    const noDataElements = screen.getAllByText('No data');
    expect(noDataElements.length).toBeGreaterThanOrEqual(3);

    // Should NOT show "0 projects" anywhere
    expect(screen.queryByText('0 projects')).not.toBeInTheDocument();
  });

  it('shows real data for statuses that have it', () => {
    render(<ConstructionPipelinePage />);

    // Verify the stat cards for existing data render correctly
    expect(screen.getByText('Proposed')).toBeInTheDocument();
    expect(screen.getByText('Under Constr.')).toBeInTheDocument();
  });
});
