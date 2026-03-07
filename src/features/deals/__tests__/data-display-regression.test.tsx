/**
 * Regression tests for deals data display — ensures optional/nullable fields
 * render "N/A" (or dash) instead of "0", "$0", or "0.0%" when data is missing.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { DealCard } from '../components/DealCard';
import { DealDetailModal } from '../components/DealDetailModal';
import { ComparisonTable } from '../components/comparison/ComparisonTable';
import type { Deal, DealStage } from '@/types/deal';
import type { DealForComparison } from '@/hooks/api/useDealComparison';

// ---------- Mock dependencies ----------

// Mock leaflet (used by DealAerialMap)
vi.mock('leaflet', () => ({
  default: {
    map: vi.fn(() => ({
      remove: vi.fn(),
    })),
    tileLayer: vi.fn(() => ({ addTo: vi.fn() })),
    marker: vi.fn(() => ({ addTo: vi.fn() })),
    icon: vi.fn(),
  },
  map: vi.fn(() => ({ remove: vi.fn() })),
  tileLayer: vi.fn(() => ({ addTo: vi.fn() })),
  marker: vi.fn(() => ({ addTo: vi.fn() })),
  icon: vi.fn(),
}));

vi.mock('leaflet/dist/images/marker-icon.png', () => ({ default: '' }));
vi.mock('leaflet/dist/images/marker-shadow.png', () => ({ default: '' }));

// Mock deals API hooks
const mockDealData = { current: null as Deal | null };
vi.mock('@/hooks/api/useDeals', () => ({
  useDealWithMockFallback: vi.fn(() => ({
    data: mockDealData.current,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
  useDealProformaReturns: vi.fn(() => ({
    data: null,
    isLoading: false,
  })),
  useDealActivitiesWithMockFallback: vi.fn(() => ({
    data: null,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
  useAddDealActivity: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
}));

// ---------- Helpers ----------

/** Create a deal with all optional numeric fields set to undefined */
function makeDealWithMissingData(overrides?: Partial<Deal>): Deal {
  return {
    id: 'test-deal-1',
    propertyName: 'Test Property',
    address: { street: '123 Main St', city: 'Phoenix', state: 'AZ' },
    value: 25000000,
    capRate: 5.2,
    stage: 'active_review' as DealStage,
    daysInStage: 10,
    totalDaysInPipeline: 30,
    assignee: 'Test User',
    propertyType: 'Garden',
    createdAt: new Date('2025-01-01'),
    timeline: [],
    // All optional numeric fields explicitly undefined
    units: undefined,
    avgUnitSf: undefined,
    currentOwner: undefined,
    lastSalePricePerUnit: undefined,
    lastSaleDate: undefined,
    t12ReturnOnCost: undefined,
    leveredIrr: undefined,
    leveredMoic: undefined,
    totalEquityCommitment: undefined,
    noiMargin: undefined,
    purchasePrice: undefined,
    totalAcquisitionBudget: undefined,
    basisPerUnit: undefined,
    t12CapOnPp: undefined,
    t3CapOnPp: undefined,
    totalCostCapT12: undefined,
    totalCostCapT3: undefined,
    loanAmount: undefined,
    lpEquity: undefined,
    exitMonths: undefined,
    exitCapRate: undefined,
    unleveredIrr: undefined,
    unleveredMoic: undefined,
    lpIrr: undefined,
    lpMoic: undefined,
    latitude: undefined,
    longitude: undefined,
    ...overrides,
  };
}

function makeComparisonDeal(overrides?: Partial<DealForComparison>): DealForComparison {
  return {
    ...makeDealWithMissingData(),
    noi: 0,
    pricePerSqft: 0,
    projectedIrr: 0,
    cashOnCash: 0,
    equityMultiple: 0,
    totalSf: 0,
    occupancyRate: 0,
    ...overrides,
  } as DealForComparison;
}

// ---------- DealCard tests ----------

describe('DealCard — missing data display', () => {
  it('shows "N/A" for missing units', () => {
    const deal = makeDealWithMissingData();
    render(<DealCard deal={deal} />);

    // The units row should show N/A
    const unitsRow = screen.getByText('Units').closest('div');
    expect(unitsRow?.parentElement?.textContent).toContain('N/A');
  });

  it('shows "N/A" for missing cap rate', () => {
    const deal = makeDealWithMissingData();
    render(<DealCard deal={deal} />);

    const capRateRow = screen.getByText('Cap Rate — PP (T12)').closest('div');
    expect(capRateRow?.parentElement?.textContent).toContain('N/A');
  });

  it('shows "N/A" for missing basis per unit', () => {
    const deal = makeDealWithMissingData();
    render(<DealCard deal={deal} />);

    const basisRow = screen.getByText('Total Going-In Basis/Unit').closest('div');
    expect(basisRow?.parentElement?.textContent).toContain('N/A');
  });

  it('shows real values when data is present', () => {
    const deal = makeDealWithMissingData({
      units: 150,
      t12CapOnPp: 0.052,
      basisPerUnit: 180000,
    });
    render(<DealCard deal={deal} />);

    // Units should show "150" not "N/A"
    expect(screen.getByText('150')).toBeInTheDocument();
    // Cap rate should show "5.2%"
    expect(screen.getByText('5.2%')).toBeInTheDocument();
    // Basis per unit should show formatted value
    expect(screen.getByText('$180,000/Unit')).toBeInTheDocument();
  });

  it('does not show "$0" or "0" for missing optional fields', () => {
    const deal = makeDealWithMissingData();
    const { container } = render(<DealCard deal={deal} />);

    // Should not contain "$0" anywhere in the card metrics
    const metricsSection = container.querySelector('.space-y-1');
    const text = metricsSection?.textContent ?? '';
    expect(text).not.toMatch(/\$0([^,]|$)/); // $0 but not $0, (which could be part of a larger number)
    expect(text).not.toContain('0.0%');
  });
});

// ---------- DealDetailModal tests ----------

describe('DealDetailModal — missing data display', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows "N/A" for all missing financial metrics', () => {
    const deal = makeDealWithMissingData();
    mockDealData.current = deal;

    render(
      <DealDetailModal dealId="test-deal-1" open={true} onOpenChange={vi.fn()} />
    );

    // Many metric rows show combined values like "N/A / N/A" so the exact
    // standalone "N/A" count varies. Instead, count all visible N/A occurrences
    // in the metrics grid (includes those inside combined strings).
    const metricsGrid = document.querySelector('.grid.grid-cols-1');
    const allNaCount = (metricsGrid?.textContent ?? '').split('N/A').length - 1;
    // Should have N/A for: units, avgSf, NOI margin, loss factor, basis total, basis/unit,
    // cap rates (T12 PP, T3 PP, T12 TC, T3 TC), debt, equity, returns x6, exit month, exit cap
    expect(allNaCount).toBeGreaterThanOrEqual(10);
  });

  it('does not show "$0" or "0.0%" for missing metrics', () => {
    const deal = makeDealWithMissingData();
    mockDealData.current = deal;

    const { container } = render(
      <DealDetailModal dealId="test-deal-1" open={true} onOpenChange={vi.fn()} />
    );

    // Find the metrics grid
    const metricsGrid = container.querySelector('.grid.grid-cols-1');
    const text = metricsGrid?.textContent ?? '';
    expect(text).not.toContain('0.0%');
    // Allow "$25.0M" (the deal value) but no standalone "$0"
    expect(text).not.toMatch(/\$0([^,.\d]|$)/);
  });

  it('shows real values when data is present', () => {
    const deal = makeDealWithMissingData({
      units: 200,
      avgUnitSf: 900,
      noiMargin: 0.65,
      t12CapOnPp: 0.052,
      t3CapOnPp: 0.048,
      leveredIrr: 0.15,
      leveredMoic: 1.8,
    });
    mockDealData.current = deal;

    render(
      <DealDetailModal dealId="test-deal-1" open={true} onOpenChange={vi.fn()} />
    );

    // Units should show 200
    expect(screen.getByText(/200/)).toBeInTheDocument();
    // NOI margin
    expect(screen.getByText('65.0%')).toBeInTheDocument();
    // Levered returns
    expect(screen.getByText(/15\.0%/)).toBeInTheDocument();
    expect(screen.getByText(/1\.8x/)).toBeInTheDocument();
  });

  it('shows "N/A" for missing loss factor total', () => {
    const deal = makeDealWithMissingData();
    mockDealData.current = deal;

    render(
      <DealDetailModal dealId="test-deal-1" open={true} onOpenChange={vi.fn()} />
    );

    // Total Loss Factor row should show N/A when all loss rates are undefined/0
    const lossRow = screen.getByText('Total Loss Factor (T12)').closest('div');
    expect(lossRow?.parentElement?.textContent).toContain('N/A');
  });
});

// ---------- ComparisonTable tests ----------

describe('ComparisonTable — missing data display', () => {
  it('shows "N/A" for missing units and avgUnitSf', () => {
    const deals = [makeComparisonDeal({ units: undefined, avgUnitSf: undefined })];
    render(<ComparisonTable deals={deals} />);

    // The Units / Avg SF row should contain "N/A / N/A SF"
    const cells = screen.getAllByRole('cell');
    const unitsCell = cells.find(c => c.textContent?.includes('N/A / N/A SF'));
    expect(unitsCell).toBeTruthy();
  });

  it('shows real units when present (does not use falsy check)', () => {
    const deals = [makeComparisonDeal({ units: 200, avgUnitSf: 850 })];
    render(<ComparisonTable deals={deals} />);

    const cells = screen.getAllByRole('cell');
    const unitsCell = cells.find(c => c.textContent?.includes('200 / 850 SF'));
    expect(unitsCell).toBeTruthy();
  });

  it('shows "N/A" for missing NOI margin', () => {
    const deals = [makeComparisonDeal({ noiMargin: undefined })];
    render(<ComparisonTable deals={deals} />);

    // NOI Margin row should show N/A
    const cells = screen.getAllByRole('cell');
    const noiCell = cells.find(c => {
      const prev = c.previousElementSibling;
      return prev?.textContent === 'NOI Margin' && c.textContent === 'N/A';
    });
    expect(noiCell).toBeTruthy();
  });

  it('shows "N/A" for missing IRR/MOIC values', () => {
    const deals = [makeComparisonDeal({
      unleveredIrr: undefined,
      unleveredMoic: undefined,
      leveredIrr: undefined,
      leveredMoic: undefined,
    })];
    render(<ComparisonTable deals={deals} />);

    const cells = screen.getAllByRole('cell');
    const irrCell = cells.find(c => c.textContent === 'N/A / N/A');
    expect(irrCell).toBeTruthy();
  });

  it('formats present cap rates as percentages, not "0.0%"', () => {
    const deals = [makeComparisonDeal({
      t12CapOnPp: 0.052,
      totalCostCapT12: 0.048,
    })];
    render(<ComparisonTable deals={deals} />);

    const cells = screen.getAllByRole('cell');
    const capRateCell = cells.find(c => c.textContent === '5.2%');
    expect(capRateCell).toBeTruthy();
  });
});
