import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import { PropertyDetailPage } from '../PropertyDetailPage';
import { OverviewTab } from '../components/OverviewTab';
import { FinancialsTab } from '../components/FinancialsTab';
import { PerformanceTab } from '../components/PerformanceTab';
import { OperationsTab } from '../components/OperationsTab';
import { TransactionsTab } from '../components/TransactionsTab';
import { PropertyHero } from '../components/PropertyHero';
import type { Property, OperatingYear } from '@/types';

// Note: ResizeObserver and IntersectionObserver are mocked in src/test/setup.ts
// but the factory-function mock may not work as a constructor in vitest 4.x.
// Override with proper class-based mocks to ensure `new` works.
globalThis.ResizeObserver = class {
  observe() { /* noop */ }
  unobserve() { /* noop */ }
  disconnect() { /* noop */ }
} as unknown as typeof ResizeObserver;

globalThis.IntersectionObserver = class {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  constructor(_cb: IntersectionObserverCallback, _opts?: IntersectionObserverInit) { /* noop */ }
  observe() { /* noop */ }
  unobserve() { /* noop */ }
  disconnect() { /* noop */ }
  get root() { return null; }
  get rootMargin() { return ''; }
  get thresholds() { return []; }
  takeRecords() { return []; }
} as unknown as typeof IntersectionObserver;

// Mock WebSocket (used by PropertyActivityFeed for real-time updates)
globalThis.WebSocket = class {
  send() { /* noop */ }
  close() { /* noop */ }
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;
} as unknown as typeof WebSocket;

// Mock react-router-dom hooks
const mockNavigate = vi.fn();
let mockParamsId: string | undefined = 'prop-1';
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useParams: () => ({ id: mockParamsId }),
    useNavigate: () => mockNavigate,
  };
});

// Mock the property hook
const mockUseProperty = vi.fn();
vi.mock('@/hooks/api/useProperties', () => ({
  useProperty: (...args: unknown[]) => mockUseProperty(...args),
  propertyKeys: {
    all: ['properties'],
    lists: () => ['properties', 'list'],
    list: (filters?: unknown) => ['properties', 'list', filters],
    details: () => ['properties', 'detail'],
    detail: (id: string) => ['properties', 'detail', id],
    summary: () => ['properties', 'summary'],
  },
}));

// Mock property activities hook
vi.mock('@/hooks/api/usePropertyActivities', () => ({
  usePropertyActivitiesWithMockFallback: vi.fn(() => ({
    data: { activities: [], total: 0 },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
  usePropertyActivities: vi.fn(() => ({
    data: { activities: [], total: 0 },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
  propertyActivityKeys: {
    all: ['propertyActivities'],
    lists: () => ['propertyActivities', 'list'],
    list: (propertyId: string) => ['propertyActivities', 'list', propertyId],
    detail: (activityId: string) => ['propertyActivities', 'detail', activityId],
  },
}));

// Mock transactions hook
vi.mock('@/hooks/api/useTransactions', () => ({
  useTransactionsWithMockFallback: vi.fn(() => ({
    data: {
      transactions: mockTransactions,
      total: mockTransactions.length,
    },
    isLoading: false,
    error: null,
  })),
}));

// Mock Recharts to avoid canvas/SVG issues in JSDOM
vi.mock('recharts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('recharts')>();
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container" style={{ width: 400, height: 300 }}>
        {children}
      </div>
    ),
  };
});

// ============================================================================
// Test Data
// ============================================================================

const mockOperatingYear: OperatingYear = {
  year: 1,
  grossPotentialRevenue: 2400000,
  lossToLease: 24000,
  vacancyLoss: 120000,
  badDebts: 12000,
  concessions: 36000,
  otherLoss: 6000,
  netRentalIncome: 2202000,
  otherIncome: 180000,
  laundryIncome: 24000,
  parkingIncome: 60000,
  petIncome: 36000,
  storageIncome: 18000,
  utilityIncome: 30000,
  otherMiscIncome: 12000,
  effectiveGrossIncome: 2382000,
  noi: 1428000,
  totalOperatingExpenses: 954000,
  expenses: {
    realEstateTaxes: 240000,
    propertyInsurance: 72000,
    staffingPayroll: 192000,
    propertyManagementFee: 96000,
    repairsAndMaintenance: 84000,
    turnover: 48000,
    contractServices: 60000,
    reservesForReplacement: 48000,
    adminLegalSecurity: 36000,
    advertisingLeasingMarketing: 30000,
    otherExpenses: 24000,
    utilities: 24000,
  },
};

const mockProperty: Property = {
  id: 'prop-1',
  name: 'Sunrise Apartments',
  address: {
    street: '123 Main St',
    city: 'Dallas',
    state: 'TX',
    zip: '75201',
    latitude: 32.7767,
    longitude: -96.797,
    submarket: 'Uptown',
  },
  propertyDetails: {
    units: 200,
    squareFeet: 180000,
    averageUnitSize: 900,
    yearBuilt: 2005,
    propertyClass: 'B',
    assetType: 'Multifamily',
    amenities: ['Pool', 'Gym', 'Dog Park', 'Business Center'],
  },
  acquisition: {
    date: new Date('2022-06-15'),
    purchasePrice: 28000000,
    pricePerUnit: 140000,
    closingCosts: 350000,
    acquisitionFee: 280000,
    totalInvested: 32000000,
    landAndAcquisitionCosts: 5000000,
    hardCosts: 18000000,
    softCosts: 3000000,
    lenderClosingCosts: 500000,
    equityClosingCosts: 200000,
    totalAcquisitionBudget: 32000000,
  },
  financing: {
    loanAmount: 21000000,
    loanToValue: 0.75,
    interestRate: 0.0487,
    loanTerm: 10,
    amortization: 30,
    monthlyPayment: 111500,
    lender: 'Wells Fargo',
    originationDate: new Date('2022-06-15'),
    maturityDate: new Date('2032-06-15'),
  },
  valuation: {
    currentValue: 35000000,
    lastAppraisalDate: new Date('2024-01-15'),
    capRate: 0.058,
    appreciationSinceAcquisition: 0.25,
  },
  operations: {
    occupancy: 0.94,
    averageRent: 1250,
    rentPerSqft: 1.39,
    monthlyRevenue: 235000,
    otherIncome: 15000,
    expenses: {
      realEstateTaxes: 240000,
      otherExpenses: 24000,
      propertyInsurance: 72000,
      staffingPayroll: 192000,
      propertyManagementFee: 96000,
      repairsAndMaintenance: 84000,
      turnover: 48000,
      contractServices: 60000,
      reservesForReplacement: 48000,
      adminLegalSecurity: 36000,
      advertisingLeasingMarketing: 30000,
      total: 930000,
    },
    noi: 1428000,
    operatingExpenseRatio: 0.39,
    grossPotentialRevenue: 2400000,
    netRentalIncome: 2202000,
    otherIncomeAnnual: 180000,
    vacancyLoss: 120000,
    concessions: 36000,
  },
  operationsByYear: [mockOperatingYear],
  performance: {
    leveredIrr: 0.182,
    leveredMoic: 2.1,
    unleveredIrr: 0.125,
    unleveredMoic: 1.65,
    totalEquityCommitment: 11000000,
    totalCashFlowsToEquity: 23100000,
    netCashFlowsToEquity: 12100000,
    holdPeriodYears: 5,
    exitCapRate: 0.06,
    totalBasisPerUnitClose: 160000,
    seniorLoanBasisPerUnitClose: 105000,
    totalBasisPerUnitExit: 175000,
    seniorLoanBasisPerUnitExit: 110000,
  },
  images: {
    main: 'https://example.com/sunrise.jpg',
    gallery: [],
  },
};

const mockTransactions = [
  {
    id: 'txn-1',
    propertyId: 'prop-1',
    propertyName: 'Sunrise Apartments',
    type: 'acquisition' as const,
    category: 'Purchase',
    amount: 28000000,
    date: new Date('2022-06-15'),
    description: 'Initial property acquisition',
  },
  {
    id: 'txn-2',
    propertyId: 'prop-1',
    propertyName: 'Sunrise Apartments',
    type: 'capital_improvement' as const,
    category: 'Renovation',
    amount: 2500000,
    date: new Date('2023-03-01'),
    description: 'Unit renovations Phase 1',
  },
  {
    id: 'txn-3',
    propertyId: 'prop-2',
    propertyName: 'Other Property',
    type: 'distribution' as const,
    category: undefined,
    amount: 500000,
    date: new Date('2024-01-15'),
    description: 'Q4 distribution',
  },
];

// ============================================================================
// PropertyDetailPage Tests
// ============================================================================

describe('PropertyDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockParamsId = 'prop-1';
  });

  describe('Loading state', () => {
    it('shows loading spinner while data is being fetched', () => {
      mockUseProperty.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });

      render(<PropertyDetailPage />);

      expect(screen.getByText('Loading property details...')).toBeInTheDocument();
    });

    it('shows back navigation during loading', () => {
      mockUseProperty.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });

      render(<PropertyDetailPage />);

      expect(screen.getByText('Back to Investments')).toBeInTheDocument();
    });
  });

  describe('Error state', () => {
    it('shows error message when API call fails', () => {
      mockUseProperty.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Network timeout'),
      });

      render(<PropertyDetailPage />);

      expect(screen.getByText('Error Loading Property')).toBeInTheDocument();
      expect(screen.getByText('Network timeout')).toBeInTheDocument();
    });

    it('shows generic error when error is not an Error instance', () => {
      mockUseProperty.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: 'something went wrong',
      });

      render(<PropertyDetailPage />);

      expect(screen.getByText('Failed to load property details')).toBeInTheDocument();
    });

    it('shows retry button on error', () => {
      mockUseProperty.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Server error'),
      });

      render(<PropertyDetailPage />);

      expect(screen.getByText('Retry')).toBeInTheDocument();
    });

    it('shows back navigation during error', () => {
      mockUseProperty.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Server error'),
      });

      render(<PropertyDetailPage />);

      expect(screen.getByText('Back to Investments')).toBeInTheDocument();
    });
  });

  describe('Property not found state', () => {
    it('shows not found message when property is null', () => {
      mockUseProperty.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
      });

      render(<PropertyDetailPage />);

      expect(screen.getByText('Property Not Found')).toBeInTheDocument();
      expect(
        screen.getByText("The property you're looking for doesn't exist.")
      ).toBeInTheDocument();
    });

    it('shows back navigation for not found', () => {
      mockUseProperty.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
      });

      render(<PropertyDetailPage />);

      expect(screen.getByText('Back to Investments')).toBeInTheDocument();
    });
  });

  describe('Back navigation', () => {
    it('navigates to /investments when back button is clicked', async () => {
      const user = userEvent.setup();
      mockUseProperty.mockReturnValue({
        data: mockProperty,
        isLoading: false,
        error: null,
      });

      render(<PropertyDetailPage />);

      const backButton = screen.getByText('Back to Investments');
      await user.click(backButton);

      expect(mockNavigate).toHaveBeenCalledWith('/investments');
    });

    it('navigates back from loading state', async () => {
      const user = userEvent.setup();
      mockUseProperty.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });

      render(<PropertyDetailPage />);

      const backButton = screen.getByText('Back to Investments');
      await user.click(backButton);

      expect(mockNavigate).toHaveBeenCalledWith('/investments');
    });

    it('navigates back from not found state', async () => {
      const user = userEvent.setup();
      mockUseProperty.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
      });

      render(<PropertyDetailPage />);

      const backButton = screen.getByText('Back to Investments');
      await user.click(backButton);

      expect(mockNavigate).toHaveBeenCalledWith('/investments');
    });
  });

  describe('Tab rendering', () => {
    beforeEach(() => {
      mockUseProperty.mockReturnValue({
        data: mockProperty,
        isLoading: false,
        error: null,
      });
    });

    it('renders all five tabs', () => {
      render(<PropertyDetailPage />);

      expect(screen.getByText('Overview')).toBeInTheDocument();
      expect(screen.getByText('Financials')).toBeInTheDocument();
      expect(screen.getByText('Operations')).toBeInTheDocument();
      expect(screen.getByText('Performance')).toBeInTheDocument();
      expect(screen.getByText('Transactions')).toBeInTheDocument();
    });

    it('shows Overview tab content by default', () => {
      render(<PropertyDetailPage />);

      // Overview tab shows key metric cards (some labels like "Current Value" also
      // appear in the Hero section, so use getAllByText for shared labels)
      expect(screen.getAllByText('Current Value').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('Annual NOI')).toBeInTheDocument();
      expect(screen.getByText('Property Details')).toBeInTheDocument();
      expect(screen.getByText('Amenities')).toBeInTheDocument();
    });

    it('switches to Financials tab on click', async () => {
      const user = userEvent.setup();
      render(<PropertyDetailPage />);

      await user.click(screen.getByText('Financials'));

      expect(screen.getByText('Acquisition Details')).toBeInTheDocument();
      expect(screen.getByText('Financing Details')).toBeInTheDocument();
      expect(screen.getByText('Current Valuation')).toBeInTheDocument();
    });

    it('switches to Operations tab on click', async () => {
      const user = userEvent.setup();
      render(<PropertyDetailPage />);

      await user.click(screen.getByText('Operations'));

      expect(screen.getByText('Annual Cashflows')).toBeInTheDocument();
      expect(screen.getByText('Operational Metrics')).toBeInTheDocument();
    });

    it('switches to Performance tab on click', async () => {
      const user = userEvent.setup();
      render(<PropertyDetailPage />);

      await user.click(screen.getByText('Performance'));

      expect(screen.getByText('IRR (Levered)')).toBeInTheDocument();
      expect(screen.getByText('MOIC (Levered)')).toBeInTheDocument();
      expect(screen.getByText('Return Breakdown')).toBeInTheDocument();
    });

    it('switches to Transactions tab on click', async () => {
      const user = userEvent.setup();
      render(<PropertyDetailPage />);

      await user.click(screen.getByText('Transactions'));

      expect(screen.getByText('Total Transactions')).toBeInTheDocument();
      expect(screen.getByText('Transaction History')).toBeInTheDocument();
    });

    it('applies active style to the selected tab', async () => {
      const user = userEvent.setup();
      render(<PropertyDetailPage />);

      // Overview is active by default
      const overviewBtn = screen.getByRole('button', { name: 'Overview' });
      expect(overviewBtn.className).toContain('border-primary-600');

      // Click Financials
      await user.click(screen.getByText('Financials'));

      const financialsBtn = screen.getByRole('button', { name: 'Financials' });
      expect(financialsBtn.className).toContain('border-primary-600');
      expect(overviewBtn.className).toContain('border-transparent');
    });

    it('switches between tabs without losing content', async () => {
      const user = userEvent.setup();
      render(<PropertyDetailPage />);

      // Go to Financials
      await user.click(screen.getByText('Financials'));
      expect(screen.getByText('Acquisition Details')).toBeInTheDocument();

      // Go back to Overview
      await user.click(screen.getByText('Overview'));
      expect(screen.getByText('Property Details')).toBeInTheDocument();
    });
  });

  describe('Hero section', () => {
    it('renders the property name in the hero', () => {
      mockUseProperty.mockReturnValue({
        data: mockProperty,
        isLoading: false,
        error: null,
      });

      render(<PropertyDetailPage />);

      expect(screen.getByText('Sunrise Apartments')).toBeInTheDocument();
    });
  });

  describe('Activity Feed sidebar', () => {
    it('renders the activity feed sidebar', () => {
      mockUseProperty.mockReturnValue({
        data: mockProperty,
        isLoading: false,
        error: null,
      });

      render(<PropertyDetailPage />);

      expect(screen.getByText('Activity Feed')).toBeInTheDocument();
    });
  });
});

// ============================================================================
// PropertyHero Tests
// ============================================================================

describe('PropertyHero', () => {
  it('displays the property name', () => {
    render(<PropertyHero property={mockProperty} />);

    expect(screen.getByText('Sunrise Apartments')).toBeInTheDocument();
  });

  it('displays the full address', () => {
    render(<PropertyHero property={mockProperty} />);

    expect(screen.getByText(/123 Main St, Dallas, TX 75201/)).toBeInTheDocument();
  });

  it('displays the submarket badge', () => {
    render(<PropertyHero property={mockProperty} />);

    expect(screen.getByText('Uptown')).toBeInTheDocument();
  });

  it('displays the property class badge', () => {
    render(<PropertyHero property={mockProperty} />);

    expect(screen.getByText('Class B')).toBeInTheDocument();
  });

  it('shows quick stats for units, sqft, year built, and asset type', () => {
    render(<PropertyHero property={mockProperty} />);

    expect(screen.getByText('200')).toBeInTheDocument(); // units
    expect(screen.getByText('180,000')).toBeInTheDocument(); // sqft
    expect(screen.getByText('2005')).toBeInTheDocument(); // year built
    expect(screen.getByText('Multifamily')).toBeInTheDocument(); // asset type
  });

  it('renders the occupancy progress bar', () => {
    const { container } = render(<PropertyHero property={mockProperty} />);

    // Occupancy bar should have width matching 94%
    const bar = container.querySelector('[style*="width: 94%"]');
    expect(bar).toBeInTheDocument();
  });

  it('shows building icon placeholder when no image is provided', () => {
    const propertyNoImage = {
      ...mockProperty,
      images: { main: '', gallery: [] },
    };
    const { container } = render(<PropertyHero property={propertyNoImage} />);

    // Should render the Building2 fallback icon
    const buildingIcon = container.querySelector('.lucide-building-2');
    expect(buildingIcon).toBeInTheDocument();
  });

  it('applies correct class color for Class A', () => {
    const classAProperty = {
      ...mockProperty,
      propertyDetails: { ...mockProperty.propertyDetails, propertyClass: 'A' as const },
    };
    render(<PropertyHero property={classAProperty} />);

    const badge = screen.getByText('Class A');
    expect(badge.className).toContain('bg-primary-100');
  });

  it('applies correct class color for Class C', () => {
    const classCProperty = {
      ...mockProperty,
      propertyDetails: { ...mockProperty.propertyDetails, propertyClass: 'C' as const },
    };
    render(<PropertyHero property={classCProperty} />);

    const badge = screen.getByText('Class C');
    expect(badge.className).toContain('bg-gray-100');
  });
});

// ============================================================================
// OverviewTab Tests
// ============================================================================

describe('OverviewTab', () => {
  it('displays key metrics cards', () => {
    render(<OverviewTab property={mockProperty} />);

    expect(screen.getByText('Current Value')).toBeInTheDocument();
    expect(screen.getByText('Annual NOI')).toBeInTheDocument();
    expect(screen.getByText('Cap Rate')).toBeInTheDocument();
    expect(screen.getByText('T12 Occupancy')).toBeInTheDocument();
  });

  it('displays formatted current value', () => {
    render(<OverviewTab property={mockProperty} />);

    // $35,000,000
    expect(screen.getByText('$35,000,000')).toBeInTheDocument();
  });

  it('displays property details section', () => {
    render(<OverviewTab property={mockProperty} />);

    expect(screen.getByText('Property Details')).toBeInTheDocument();
    expect(screen.getByText('Total Units')).toBeInTheDocument();
    expect(screen.getByText('Total Square Feet')).toBeInTheDocument();
    expect(screen.getByText('Average Unit Size')).toBeInTheDocument();
    expect(screen.getByText('Year Built')).toBeInTheDocument();
    expect(screen.getByText('Property Class')).toBeInTheDocument();
    expect(screen.getByText('Asset Type')).toBeInTheDocument();
  });

  it('displays amenities', () => {
    render(<OverviewTab property={mockProperty} />);

    expect(screen.getByText('Amenities')).toBeInTheDocument();
    expect(screen.getByText('Pool')).toBeInTheDocument();
    expect(screen.getByText('Gym')).toBeInTheDocument();
    expect(screen.getByText('Dog Park')).toBeInTheDocument();
    expect(screen.getByText('Business Center')).toBeInTheDocument();
  });

  it('displays location information', () => {
    render(<OverviewTab property={mockProperty} />);

    expect(screen.getByText('Location')).toBeInTheDocument();
    expect(screen.getByText('Submarket')).toBeInTheDocument();
    expect(screen.getByText('Coordinates')).toBeInTheDocument();
  });

  it('displays formatted coordinates', () => {
    render(<OverviewTab property={mockProperty} />);

    expect(screen.getByText('32.7767, -96.7970')).toBeInTheDocument();
  });

  it('shows N/A for coordinates when not available', () => {
    const noCoordsProp = {
      ...mockProperty,
      address: { ...mockProperty.address, latitude: null, longitude: null },
    };
    render(<OverviewTab property={noCoordsProp} />);

    expect(screen.getByText('N/A')).toBeInTheDocument();
  });

  it('displays occupied units out of total', () => {
    render(<OverviewTab property={mockProperty} />);

    // 200 * 0.94 = 188
    expect(screen.getByText(/188 of 200 units occupied/)).toBeInTheDocument();
  });
});

// ============================================================================
// FinancialsTab Tests
// ============================================================================

describe('FinancialsTab', () => {
  it('displays acquisition details section', () => {
    render(<FinancialsTab property={mockProperty} />);

    expect(screen.getByText('Acquisition Details')).toBeInTheDocument();
    expect(screen.getByText('Acquisition Date')).toBeInTheDocument();
    expect(screen.getByText('Land & Acquisition Costs')).toBeInTheDocument();
    expect(screen.getByText('Hard Costs')).toBeInTheDocument();
    expect(screen.getByText('Soft Costs')).toBeInTheDocument();
    expect(screen.getByText('Lender Closing Costs')).toBeInTheDocument();
    expect(screen.getByText('Equity Closing Costs')).toBeInTheDocument();
  });

  it('displays total acquisition budget', () => {
    render(<FinancialsTab property={mockProperty} />);

    expect(screen.getByText('Total Acquisition Budget')).toBeInTheDocument();
    expect(screen.getByText('$32,000,000')).toBeInTheDocument();
  });

  it('displays financing details section', () => {
    render(<FinancialsTab property={mockProperty} />);

    expect(screen.getByText('Financing Details')).toBeInTheDocument();
    expect(screen.getByText('Loan Amount')).toBeInTheDocument();
    expect(screen.getByText('Loan-to-Value (LTV)')).toBeInTheDocument();
    expect(screen.getByText('Interest Rate')).toBeInTheDocument();
    expect(screen.getByText('Loan Term')).toBeInTheDocument();
    expect(screen.getByText('Amortization Period')).toBeInTheDocument();
  });

  it('displays lender name', () => {
    render(<FinancialsTab property={mockProperty} />);

    expect(screen.getByText('Wells Fargo')).toBeInTheDocument();
  });

  it('shows -- when lender is null', () => {
    const noLenderProp = {
      ...mockProperty,
      financing: { ...mockProperty.financing, lender: null },
    };
    render(<FinancialsTab property={noLenderProp} />);

    expect(screen.getByText('--')).toBeInTheDocument();
  });

  it('displays current valuation section', () => {
    render(<FinancialsTab property={mockProperty} />);

    expect(screen.getByText('Current Valuation')).toBeInTheDocument();
    expect(screen.getByText('Appreciation Since Acquisition')).toBeInTheDocument();
    expect(screen.getByText('Last Appraisal Date')).toBeInTheDocument();
  });

  it('displays formatted interest rate', () => {
    render(<FinancialsTab property={mockProperty} />);

    // 0.0487 * 100 = 4.87%
    expect(screen.getByText('4.87%')).toBeInTheDocument();
  });

  it('displays loan term and amortization in years', () => {
    render(<FinancialsTab property={mockProperty} />);

    expect(screen.getByText('10 years')).toBeInTheDocument();
    expect(screen.getByText('30 years')).toBeInTheDocument();
  });
});

// ============================================================================
// PerformanceTab Tests
// ============================================================================

describe('PerformanceTab', () => {
  it('displays levered and unlevered IRR/MOIC cards', () => {
    render(<PerformanceTab property={mockProperty} />);

    expect(screen.getByText('IRR (Levered)')).toBeInTheDocument();
    expect(screen.getByText('MOIC (Levered)')).toBeInTheDocument();
    expect(screen.getByText('IRR (Unlevered)')).toBeInTheDocument();
    expect(screen.getByText('MOIC (Unlevered)')).toBeInTheDocument();
  });

  it('displays formatted levered IRR', () => {
    render(<PerformanceTab property={mockProperty} />);

    // 0.182 * 100 = 18.2%
    expect(screen.getByText('18.2%')).toBeInTheDocument();
  });

  it('displays formatted levered MOIC', () => {
    render(<PerformanceTab property={mockProperty} />);

    expect(screen.getByText('2.10x')).toBeInTheDocument();
  });

  it('displays return breakdown section', () => {
    render(<PerformanceTab property={mockProperty} />);

    expect(screen.getByText('Return Breakdown')).toBeInTheDocument();
    expect(screen.getByText('Total Equity Commitment')).toBeInTheDocument();
    expect(screen.getByText('Total Cash Flows to Equity')).toBeInTheDocument();
    expect(screen.getByText('Net Cash Flows to Equity')).toBeInTheDocument();
  });

  it('displays investment metrics summary', () => {
    render(<PerformanceTab property={mockProperty} />);

    expect(screen.getByText('Investment Metrics Summary')).toBeInTheDocument();
    expect(screen.getByText('Holding Period')).toBeInTheDocument();
    expect(screen.getByText('5 years')).toBeInTheDocument();
  });

  it('displays exit metrics', () => {
    render(<PerformanceTab property={mockProperty} />);

    expect(screen.getByText('Exit Cap Rate')).toBeInTheDocument();
    expect(screen.getByText('Total Basis/Unit @ Close')).toBeInTheDocument();
    expect(screen.getByText('Total Basis/Unit @ Exit')).toBeInTheDocument();
  });

  it('shows -- when unlevered metrics are null', () => {
    const noUnleveredProp = {
      ...mockProperty,
      performance: {
        ...mockProperty.performance,
        unleveredIrr: null,
        unleveredMoic: null,
      },
    };
    render(<PerformanceTab property={noUnleveredProp} />);

    // Both unlevered cards should show --
    const dashes = screen.getAllByText('--');
    expect(dashes.length).toBeGreaterThanOrEqual(2);
  });

  it('shows -- when exit metrics are null', () => {
    const noExitProp = {
      ...mockProperty,
      performance: {
        ...mockProperty.performance,
        totalBasisPerUnitExit: null,
        seniorLoanBasisPerUnitExit: null,
        exitCapRate: 0, // 0 is falsy -> '--'
      },
    };
    render(<PerformanceTab property={noExitProp} />);

    const dashes = screen.getAllByText('--');
    expect(dashes.length).toBeGreaterThanOrEqual(3);
  });
});

// ============================================================================
// OperationsTab Tests
// ============================================================================

describe('OperationsTab', () => {
  it('renders the annual cashflows table with multi-year data', () => {
    render(<OperationsTab property={mockProperty} />);

    expect(screen.getByText('Annual Cashflows')).toBeInTheDocument();
    expect(screen.getByText('Year 1')).toBeInTheDocument();
    expect(screen.getByText('Revenue')).toBeInTheDocument();
    expect(screen.getByText('Gross Potential Revenue')).toBeInTheDocument();
    expect(screen.getByText('Net Rental Income')).toBeInTheDocument();
  });

  it('renders expense breakdown section', () => {
    render(<OperationsTab property={mockProperty} />);

    expect(screen.getByText('Expense Breakdown (Year 1)')).toBeInTheDocument();
    expect(screen.getByText('Expense Details (Year 1)')).toBeInTheDocument();
  });

  it('renders operational metrics', () => {
    render(<OperationsTab property={mockProperty} />);

    expect(screen.getByText('Operational Metrics')).toBeInTheDocument();
    expect(screen.getByText('T12 Occupancy Rate')).toBeInTheDocument();
    expect(screen.getByText('Average Rent')).toBeInTheDocument();
    expect(screen.getByText('Rent Per Sq Ft')).toBeInTheDocument();
    expect(screen.getByText('Occupied Units')).toBeInTheDocument();
  });

  it('displays expense line items in the details table', () => {
    render(<OperationsTab property={mockProperty} />);

    // Expense items appear in both the cashflows table and the expense details.
    // Check that they appear at least once (getAllByText).
    expect(screen.getAllByText('Real Estate Taxes').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Property Insurance').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Staffing/Payroll').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Property Management Fee').length).toBeGreaterThanOrEqual(1);
  });

  it('falls back to single-year display when operationsByYear is empty', () => {
    const noYearsProp = {
      ...mockProperty,
      operationsByYear: [],
    };
    render(<OperationsTab property={noYearsProp} />);

    // Fallback uses operations.noi directly
    expect(screen.getByText('Net Operating Income (NOI)')).toBeInTheDocument();
    // Should not show Year 1 column header
    expect(screen.queryByText('Year 1')).not.toBeInTheDocument();
  });

  it('shows "No expense data available" when there are no expenses', () => {
    const noExpensesProp = {
      ...mockProperty,
      operationsByYear: [
        {
          ...mockOperatingYear,
          expenses: {
            realEstateTaxes: 0,
            propertyInsurance: 0,
            staffingPayroll: 0,
            propertyManagementFee: 0,
            repairsAndMaintenance: 0,
            turnover: 0,
            contractServices: 0,
            reservesForReplacement: 0,
            adminLegalSecurity: 0,
            advertisingLeasingMarketing: 0,
            otherExpenses: 0,
            utilities: 0,
          },
        },
      ],
    };
    render(<OperationsTab property={noExpensesProp} />);

    expect(screen.getByText('No expense data available')).toBeInTheDocument();
  });

  it('displays revenue loss items', () => {
    render(<OperationsTab property={mockProperty} />);

    expect(screen.getByText('Less: Loss to Lease')).toBeInTheDocument();
    expect(screen.getByText('Less: Vacancy Loss')).toBeInTheDocument();
    expect(screen.getByText('Less: Bad Debts')).toBeInTheDocument();
    expect(screen.getByText('Less: Concessions')).toBeInTheDocument();
  });

  it('displays other income items', () => {
    render(<OperationsTab property={mockProperty} />);

    expect(screen.getByText('Laundry Income')).toBeInTheDocument();
    expect(screen.getByText('Parking Income')).toBeInTheDocument();
    expect(screen.getByText('Pet Income')).toBeInTheDocument();
  });
});

// ============================================================================
// TransactionsTab Tests
// ============================================================================

describe('TransactionsTab', () => {
  it('displays transaction summary cards', () => {
    render(<TransactionsTab propertyId="prop-1" />);

    expect(screen.getByText('Total Transactions')).toBeInTheDocument();
    expect(screen.getByText('Total Value')).toBeInTheDocument();
    expect(screen.getByText('First Transaction')).toBeInTheDocument();
    expect(screen.getByText('Last Transaction')).toBeInTheDocument();
  });

  it('filters transactions by propertyId', () => {
    render(<TransactionsTab propertyId="prop-1" />);

    // Should show prop-1 transactions but not prop-2
    expect(screen.getByText('Initial property acquisition')).toBeInTheDocument();
    expect(screen.getByText('Unit renovations Phase 1')).toBeInTheDocument();
    expect(screen.queryByText('Q4 distribution')).not.toBeInTheDocument();
  });

  it('displays the count of matching transactions', () => {
    render(<TransactionsTab propertyId="prop-1" />);

    // 2 transactions for prop-1
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('displays transaction breakdown by type', () => {
    render(<TransactionsTab propertyId="prop-1" />);

    expect(screen.getByText('Transaction Breakdown by Type')).toBeInTheDocument();
    // Type names appear in both the breakdown card and transaction history badges
    expect(screen.getAllByText('Acquisition').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Capital Improvement').length).toBeGreaterThanOrEqual(1);
  });

  it('shows empty state when no transactions match', () => {
    render(<TransactionsTab propertyId="prop-999" />);

    expect(screen.getByText('No transactions found for this property.')).toBeInTheDocument();
  });

  it('shows N/A for first/last transaction dates when empty', () => {
    render(<TransactionsTab propertyId="prop-999" />);

    const naTexts = screen.getAllByText('N/A');
    expect(naTexts.length).toBe(2); // First and Last transaction dates
  });

  it('displays transaction history list', () => {
    render(<TransactionsTab propertyId="prop-1" />);

    expect(screen.getByText('Transaction History')).toBeInTheDocument();
    expect(screen.getByText('Initial property acquisition')).toBeInTheDocument();
  });
});
