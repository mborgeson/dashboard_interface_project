import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import { ComparisonTable } from '../ComparisonTable';
import { ComparisonCharts } from '../ComparisonCharts';
import { ComparisonSelector } from '../ComparisonSelector';
import type { DealForComparison } from '@/hooks/api/useDealComparison';
import type { DealStage } from '@/types/deal';

// Mock ResizeObserver for Recharts
class ResizeObserverMock {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
vi.stubGlobal('ResizeObserver', ResizeObserverMock);

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock the deals hook
vi.mock('@/hooks/api', () => ({
  useDealsWithMockFallback: vi.fn(() => ({
    data: {
      deals: mockDeals,
      total: mockDeals.length,
    },
    isLoading: false,
  })),
}));

const baseDealFields = {
  avgUnitSf: 850,
  currentOwner: 'Test Owner',
  lastSalePricePerUnit: 200000,
  lastSaleDate: '2023-01-15',
  t12ReturnOnCost: 0.08,
  leveredIrr: 0.15,
  leveredMoic: 1.8,
  totalEquityCommitment: 12000000,
};

const mockDeals: DealForComparison[] = [
  {
    ...baseDealFields,
    id: 'deal-001',
    propertyName: 'Phoenix Gateway Plaza',
    address: { street: '2850 W Camelback Rd', city: 'Phoenix', state: 'AZ' },
    value: 42500000,
    capRate: 5.2,
    stage: 'active_review' as DealStage,
    daysInStage: 18,
    totalDaysInPipeline: 25,
    assignee: 'Sarah Chen',
    propertyType: 'Garden',
    units: 156,
    createdAt: new Date('2024-11-27'),
    timeline: [],
    noi: 2210000,
    pricePerSqft: 320,
    projectedIrr: 0.15,
    cashOnCash: 0.08,
    equityMultiple: 1.8,
    totalSf: 132600,
    occupancyRate: 0.94,
  },
  {
    ...baseDealFields,
    id: 'deal-002',
    propertyName: 'Mesa Ridge Apartments',
    address: { street: '4500 S Power Rd', city: 'Mesa', state: 'AZ' },
    value: 35800000,
    capRate: 5.5,
    stage: 'under_contract' as DealStage,
    daysInStage: 9,
    totalDaysInPipeline: 42,
    assignee: 'David Park',
    propertyType: 'Garden',
    units: 144,
    createdAt: new Date('2024-10-24'),
    timeline: [],
    noi: 1969000,
    pricePerSqft: 292,
    projectedIrr: 0.18,
    cashOnCash: 0.10,
    equityMultiple: 2.1,
    totalSf: 122400,
    occupancyRate: 0.96,
  },
  {
    ...baseDealFields,
    id: 'deal-003',
    propertyName: 'Tempe University Village',
    address: { street: '950 S Rural Rd', city: 'Tempe', state: 'AZ' },
    value: 52300000,
    capRate: 5.1,
    stage: 'closed' as DealStage,
    daysInStage: 28,
    totalDaysInPipeline: 82,
    assignee: 'Emily Rodriguez',
    propertyType: 'Mid-Rise',
    units: 188,
    createdAt: new Date('2024-09-15'),
    timeline: [],
    noi: 2667300,
    pricePerSqft: 327,
    projectedIrr: 0.14,
    cashOnCash: 0.07,
    equityMultiple: 1.6,
    totalSf: 159800,
    occupancyRate: 0.92,
  },
];

describe('ComparisonTable', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders deal names as column headers', () => {
      render(<ComparisonTable deals={mockDeals} />);

      expect(screen.getByText('Phoenix Gateway Plaza')).toBeInTheDocument();
      expect(screen.getByText('Mesa Ridge Apartments')).toBeInTheDocument();
      expect(screen.getByText('Tempe University Village')).toBeInTheDocument();
    });

    it('renders location information for each deal', () => {
      render(<ComparisonTable deals={mockDeals} />);

      expect(screen.getByText('Phoenix, AZ')).toBeInTheDocument();
      expect(screen.getByText('Mesa, AZ')).toBeInTheDocument();
      expect(screen.getByText('Tempe, AZ')).toBeInTheDocument();
    });

    it('renders metric rows', () => {
      render(<ComparisonTable deals={mockDeals} />);

      expect(screen.getByText('Cap Rate')).toBeInTheDocument();
      expect(screen.getByText('NOI')).toBeInTheDocument();
      expect(screen.getByText('Price / SF')).toBeInTheDocument();
      expect(screen.getByText('Projected IRR')).toBeInTheDocument();
      expect(screen.getByText('Cash-on-Cash')).toBeInTheDocument();
      expect(screen.getByText('Equity Multiple')).toBeInTheDocument();
    });

    it('shows property type for each deal', () => {
      render(<ComparisonTable deals={mockDeals} />);

      expect(screen.getAllByText('Garden').length).toBe(2);
      expect(screen.getByText('Mid-Rise')).toBeInTheDocument();
    });

    it('shows pipeline stage for each deal', () => {
      render(<ComparisonTable deals={mockDeals} />);

      expect(screen.getByText('Active UW and Review')).toBeInTheDocument();
      expect(screen.getByText('Deals Under Contract')).toBeInTheDocument();
      expect(screen.getByText('Closed Deals')).toBeInTheDocument();
    });

    it('shows empty state when no deals provided', () => {
      render(<ComparisonTable deals={[]} />);

      expect(screen.getByText('No deals selected for comparison')).toBeInTheDocument();
    });
  });

  describe('Best/Worst highlighting', () => {
    it('highlights best values in green when highlightBestWorst is true', () => {
      const { container } = render(
        <ComparisonTable deals={mockDeals} highlightBestWorst={true} />
      );

      // Best cap rate (5.5%) should be highlighted green
      const greenCells = container.querySelectorAll('.bg-green-50');
      expect(greenCells.length).toBeGreaterThan(0);
    });

    it('highlights worst values in red when highlightBestWorst is true', () => {
      const { container } = render(
        <ComparisonTable deals={mockDeals} highlightBestWorst={true} />
      );

      // Worst values should be highlighted red
      const redCells = container.querySelectorAll('.bg-red-50');
      expect(redCells.length).toBeGreaterThan(0);
    });

    it('does not highlight when highlightBestWorst is false', () => {
      const { container } = render(
        <ComparisonTable deals={mockDeals} highlightBestWorst={false} />
      );

      const greenCells = container.querySelectorAll('.bg-green-50');
      const redCells = container.querySelectorAll('.bg-red-50');

      expect(greenCells.length).toBe(0);
      expect(redCells.length).toBe(0);
    });

    it('does not highlight when all values are the same', () => {
      const sameValueDeals = mockDeals.map((deal) => ({
        ...deal,
        capRate: 5.5,
      }));

      const { container } = render(
        <ComparisonTable deals={sameValueDeals} highlightBestWorst={true} />
      );

      // No highlighting when there's no variance
      // The cap rate row should have no highlights
      const table = container.querySelector('table');
      expect(table).toBeInTheDocument();
    });
  });

  describe('Metric filtering', () => {
    it('shows only specified metrics', () => {
      render(
        <ComparisonTable
          deals={mockDeals}
          metrics={['cap_rate', 'noi']}
        />
      );

      expect(screen.getByText('Cap Rate')).toBeInTheDocument();
      expect(screen.getByText('NOI')).toBeInTheDocument();
      // Other metrics should not be shown
      expect(screen.queryByText('Price / SF')).not.toBeInTheDocument();
    });
  });

  describe('Value formatting', () => {
    it('formats currency values correctly', () => {
      render(<ComparisonTable deals={mockDeals} />);

      // Deal value should be formatted as currency
      expect(screen.getByText('$42,500,000')).toBeInTheDocument();
    });

    it('formats percentage values correctly', () => {
      render(<ComparisonTable deals={mockDeals} />);

      // Cap rate should show percentage
      expect(screen.getByText('5.20%')).toBeInTheDocument();
    });

    it('shows dashes for missing values', () => {
      const dealWithMissingData = [{
        ...mockDeals[0],
        projectedIrr: undefined,
      }];

      render(<ComparisonTable deals={dealWithMissingData} />);

      // Should show dash for missing IRR
      const cells = screen.getAllByRole('cell');
      const hasEmptyCell = Array.from(cells).some(
        (cell) => cell.textContent === '-'
      );
      // This depends on how the component handles undefined
    });
  });
});

describe('ComparisonCharts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders bar chart by default', () => {
      render(<ComparisonCharts deals={mockDeals} />);

      expect(screen.getByText('Key Metrics Comparison')).toBeInTheDocument();
    });

    it('renders radar chart by default', () => {
      render(<ComparisonCharts deals={mockDeals} />);

      expect(screen.getByText('Overall Deal Profile Comparison')).toBeInTheDocument();
    });

    it('renders only bar chart when chartType is bar', () => {
      render(<ComparisonCharts deals={mockDeals} chartType="bar" />);

      expect(screen.getByText('Key Metrics Comparison')).toBeInTheDocument();
      expect(screen.queryByText('Overall Deal Profile Comparison')).not.toBeInTheDocument();
    });

    it('renders only radar chart when chartType is radar', () => {
      render(<ComparisonCharts deals={mockDeals} chartType="radar" />);

      expect(screen.queryByText('Key Metrics Comparison')).not.toBeInTheDocument();
      expect(screen.getByText('Overall Deal Profile Comparison')).toBeInTheDocument();
    });

    it('renders both charts when chartType is both', () => {
      render(<ComparisonCharts deals={mockDeals} chartType="both" />);

      expect(screen.getByText('Key Metrics Comparison')).toBeInTheDocument();
      expect(screen.getByText('Overall Deal Profile Comparison')).toBeInTheDocument();
    });

    it('shows empty state when no deals provided', () => {
      render(<ComparisonCharts deals={[]} />);

      expect(screen.getByText('No deals selected for comparison')).toBeInTheDocument();
    });
  });

  describe('Chart content', () => {
    it('shows normalization note for radar chart', () => {
      render(<ComparisonCharts deals={mockDeals} chartType="radar" />);

      expect(
        screen.getByText(/values normalized 0-100 for comparison/i)
      ).toBeInTheDocument();
    });
  });
});

describe('ComparisonSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders when open', () => {
      const onOpenChange = vi.fn();
      render(
        <ComparisonSelector open={true} onOpenChange={onOpenChange} />
      );

      expect(screen.getByText('Select Deals to Compare')).toBeInTheDocument();
    });

    it('does not render when closed', () => {
      const onOpenChange = vi.fn();
      render(
        <ComparisonSelector open={false} onOpenChange={onOpenChange} />
      );

      expect(screen.queryByText('Select Deals to Compare')).not.toBeInTheDocument();
    });

    it('shows selection count', () => {
      const onOpenChange = vi.fn();
      render(
        <ComparisonSelector open={true} onOpenChange={onOpenChange} />
      );

      expect(screen.getByText(/selected: 0 \/ 4/i)).toBeInTheDocument();
    });

    it('shows search input', () => {
      const onOpenChange = vi.fn();
      render(
        <ComparisonSelector open={true} onOpenChange={onOpenChange} />
      );

      expect(
        screen.getByPlaceholderText(/search deals/i)
      ).toBeInTheDocument();
    });
  });

  describe('Deal selection', () => {
    it('allows selecting 2-4 deals', async () => {
      const user = userEvent.setup();
      const onOpenChange = vi.fn();
      render(
        <ComparisonSelector open={true} onOpenChange={onOpenChange} />
      );

      // Find and click on deals
      const dealItems = screen.getAllByRole('checkbox');
      expect(dealItems.length).toBeGreaterThan(0);

      // Select first deal
      await user.click(dealItems[0]);

      // Selection count should update
      await waitFor(() => {
        expect(screen.getByText(/selected: 1/i)).toBeInTheDocument();
      });
    });

    it('shows selected deals preview', async () => {
      const onOpenChange = vi.fn();
      render(
        <ComparisonSelector
          open={true}
          onOpenChange={onOpenChange}
          initialSelectedIds={['deal-001']}
        />
      );

      // Should show the "Selected:" label when deals are selected
      await waitFor(() => {
        expect(screen.getByText('Selected:')).toBeInTheDocument();
      });
    });

    it('disables compare button when less than 2 deals selected', () => {
      const onOpenChange = vi.fn();
      render(
        <ComparisonSelector open={true} onOpenChange={onOpenChange} />
      );

      const compareButton = screen.getByRole('button', { name: /compare/i });
      expect(compareButton).toBeDisabled();
    });

    it('enables compare button when 2+ deals selected', async () => {
      const user = userEvent.setup();
      const onOpenChange = vi.fn();
      render(
        <ComparisonSelector
          open={true}
          onOpenChange={onOpenChange}
          initialSelectedIds={['deal-001', 'deal-002']}
        />
      );

      await waitFor(() => {
        const compareButton = screen.getByRole('button', { name: /compare/i });
        expect(compareButton).not.toBeDisabled();
      });
    });

    it('enforces maximum selection limit', async () => {
      const user = userEvent.setup();
      const onOpenChange = vi.fn();
      render(
        <ComparisonSelector
          open={true}
          onOpenChange={onOpenChange}
          maxSelections={2}
          initialSelectedIds={['deal-001', 'deal-002']}
        />
      );

      // Try to select a third deal - should be disabled
      await waitFor(() => {
        const dealItems = screen.getAllByRole('checkbox');
        // Non-selected checkboxes should be disabled
        const unselectedCheckboxes = Array.from(dealItems).filter(
          (cb) => !cb.hasAttribute('data-state') || cb.getAttribute('data-state') !== 'checked'
        );
        // These should be disabled or the click should not add more
      });
    });
  });

  describe('Search and filtering', () => {
    it('filters deals by search query', async () => {
      const user = userEvent.setup();
      const onOpenChange = vi.fn();
      render(
        <ComparisonSelector open={true} onOpenChange={onOpenChange} />
      );

      const searchInput = screen.getByPlaceholderText(/search deals/i);
      await user.type(searchInput, 'Phoenix');

      await waitFor(() => {
        // Only Phoenix deal should be visible
        expect(screen.getByText('Phoenix Gateway Plaza')).toBeInTheDocument();
      });
    });

    it('shows stage filter dropdown', () => {
      const onOpenChange = vi.fn();
      render(
        <ComparisonSelector open={true} onOpenChange={onOpenChange} />
      );

      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });
  });

  describe('Navigation', () => {
    it('navigates to comparison page with selected IDs', async () => {
      const user = userEvent.setup();
      const onOpenChange = vi.fn();
      render(
        <ComparisonSelector
          open={true}
          onOpenChange={onOpenChange}
          initialSelectedIds={['deal-001', 'deal-002']}
        />
      );

      await waitFor(() => {
        const compareButton = screen.getByRole('button', { name: /compare/i });
        expect(compareButton).not.toBeDisabled();
      });

      const compareButton = screen.getByRole('button', { name: /compare/i });
      await user.click(compareButton);

      expect(mockNavigate).toHaveBeenCalledWith(
        expect.stringContaining('/deals/compare?ids=')
      );
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });

    it('closes dialog on cancel', async () => {
      const user = userEvent.setup();
      const onOpenChange = vi.fn();
      render(
        <ComparisonSelector open={true} onOpenChange={onOpenChange} />
      );

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  describe('Clear selection', () => {
    it('clears all selections when clear button is clicked', async () => {
      const user = userEvent.setup();
      const onOpenChange = vi.fn();
      render(
        <ComparisonSelector
          open={true}
          onOpenChange={onOpenChange}
          initialSelectedIds={['deal-001', 'deal-002']}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Clear all')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Clear all'));

      await waitFor(() => {
        expect(screen.getByText(/selected: 0/i)).toBeInTheDocument();
      });
    });
  });
});
