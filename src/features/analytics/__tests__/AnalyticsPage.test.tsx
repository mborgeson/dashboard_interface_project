import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import { AnalyticsPage } from '../AnalyticsPage';
import { KPICard } from '../components/KPICard';
import type { Property } from '@/types';

// Mock ResizeObserver for Recharts
class ResizeObserverMock {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
vi.stubGlobal('ResizeObserver', ResizeObserverMock);

// Mock market widgets (they fetch their own data)
vi.mock('@/features/market/components/widgets/MarketOverviewWidget', () => ({
  MarketOverviewWidget: () => <div data-testid="market-overview">Market Overview</div>,
}));
vi.mock('@/features/market/components/widgets/EconomicIndicatorsWidget', () => ({
  EconomicIndicatorsWidget: () => <div data-testid="economic-indicators">Economic Indicators</div>,
}));

// Mock ReportWizard lazy import
vi.mock('@/features/reporting-suite/components/ReportWizard/ReportWizard', () => ({
  ReportWizard: ({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) =>
    open ? <div data-testid="report-wizard"><button onClick={() => onOpenChange(false)}>Close</button></div> : null,
}));

// --- Mock useProperties ---
const mockUseProperties = vi.fn();
vi.mock('@/hooks/api/useProperties', () => ({
  useProperties: () => mockUseProperties(),
  selectProperties: (data: { properties: Property[] } | undefined) => data?.properties ?? [],
}));

// --- Factory ---
function makeProperty(overrides: Partial<Property> = {}): Property {
  return {
    id: 'prop-1',
    name: 'Test Property',
    address: { street: '123 Main', city: 'Phoenix', state: 'AZ', zip: '85001', latitude: 33.4, longitude: -112.0, submarket: 'Central Phoenix' },
    propertyDetails: { units: 100, squareFeet: 90000, averageUnitSize: 900, yearBuilt: 2000, propertyClass: 'B', assetType: 'Multifamily', amenities: [] },
    acquisition: { date: new Date('2024-01-15'), purchasePrice: 20000000, pricePerUnit: 200000, closingCosts: 100000, acquisitionFee: 50000, totalInvested: 25000000, landAndAcquisitionCosts: 0, hardCosts: 0, softCosts: 0, lenderClosingCosts: 0, equityClosingCosts: 0, totalAcquisitionBudget: 0 },
    financing: { loanAmount: 15000000, loanToValue: 0.6, interestRate: 0.05, loanTerm: 30, amortization: 30, monthlyPayment: 80000, lender: 'Test Bank', originationDate: new Date('2024-01-15'), maturityDate: null },
    valuation: { currentValue: 28000000, lastAppraisalDate: new Date('2025-01-01'), capRate: 0.055, appreciationSinceAcquisition: 0.12 },
    operations: { occupancy: 0.94, averageRent: 1500, rentPerSqft: 1.67, monthlyRevenue: 150000, otherIncome: 5000, expenses: { realEstateTaxes: 100000, otherExpenses: 20000, propertyInsurance: 30000, staffingPayroll: 80000, propertyManagementFee: 60000, repairsAndMaintenance: 40000, turnover: 15000, contractServices: 10000, reservesForReplacement: 25000, adminLegalSecurity: 10000, advertisingLeasingMarketing: 5000, total: 395000 }, noi: 1400000, operatingExpenseRatio: 0.22, grossPotentialRevenue: 1800000, netRentalIncome: 1600000, otherIncomeAnnual: 60000, vacancyLoss: 100000, concessions: 0 },
    operationsByYear: [],
    performance: { leveredIrr: 0.18, leveredMoic: 2.1, unleveredIrr: 0.12, unleveredMoic: 1.6, totalEquityCommitment: 10000000, totalCashFlowsToEquity: 21000000, netCashFlowsToEquity: 11000000, holdPeriodYears: 5, exitCapRate: 0.05, totalBasisPerUnitClose: 250000, seniorLoanBasisPerUnitClose: 150000, totalBasisPerUnitExit: null, seniorLoanBasisPerUnitExit: null },
    images: { main: '', gallery: [] },
    ...overrides,
  } as Property;
}

const mockProperties = [
  makeProperty({ id: 'p1', name: 'Alpha Apartments', address: { street: '1', city: 'Phoenix', state: 'AZ', zip: '85001', latitude: 33.4, longitude: -112, submarket: 'Central Phoenix' }, operations: { occupancy: 0.94, averageRent: 1500, rentPerSqft: 1.67, monthlyRevenue: 150000, otherIncome: 5000, expenses: { realEstateTaxes: 100000, otherExpenses: 20000, propertyInsurance: 30000, staffingPayroll: 80000, propertyManagementFee: 60000, repairsAndMaintenance: 40000, turnover: 15000, contractServices: 10000, reservesForReplacement: 25000, adminLegalSecurity: 10000, advertisingLeasingMarketing: 5000, total: 395000 }, noi: 1400000, operatingExpenseRatio: 0.22, grossPotentialRevenue: 1800000, netRentalIncome: 1600000, otherIncomeAnnual: 60000, vacancyLoss: 100000, concessions: 0 } }),
  makeProperty({ id: 'p2', name: 'Beta Residences', propertyDetails: { units: 80, squareFeet: 72000, averageUnitSize: 900, yearBuilt: 2005, propertyClass: 'A', assetType: 'Multifamily', amenities: [] }, address: { street: '2', city: 'Tempe', state: 'AZ', zip: '85281', latitude: 33.4, longitude: -111.9, submarket: 'Tempe' }, operations: { occupancy: 0.97, averageRent: 1800, rentPerSqft: 2.0, monthlyRevenue: 144000, otherIncome: 3000, expenses: { realEstateTaxes: 80000, otherExpenses: 15000, propertyInsurance: 25000, staffingPayroll: 60000, propertyManagementFee: 50000, repairsAndMaintenance: 30000, turnover: 10000, contractServices: 8000, reservesForReplacement: 20000, adminLegalSecurity: 8000, advertisingLeasingMarketing: 4000, total: 310000 }, noi: 1200000, operatingExpenseRatio: 0.20, grossPotentialRevenue: 1500000, netRentalIncome: 1400000, otherIncomeAnnual: 36000, vacancyLoss: 50000, concessions: 0 }, performance: { leveredIrr: 0.15, leveredMoic: 1.8, unleveredIrr: 0.10, unleveredMoic: 1.5, totalEquityCommitment: 8000000, totalCashFlowsToEquity: 14400000, netCashFlowsToEquity: 6400000, holdPeriodYears: 5, exitCapRate: 0.05, totalBasisPerUnitClose: 200000, seniorLoanBasisPerUnitClose: 120000, totalBasisPerUnitExit: null, seniorLoanBasisPerUnitExit: null } }),
];

describe('AnalyticsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Loading state', () => {
    it('renders skeleton placeholders while loading', () => {
      mockUseProperties.mockReturnValue({ data: undefined, isLoading: true, error: null });
      const { container } = render(<AnalyticsPage />);

      expect(screen.getByText('Portfolio Analytics')).toBeInTheDocument();
      const pulseElements = container.querySelectorAll('.animate-pulse');
      expect(pulseElements.length).toBeGreaterThan(0);
    });

    it('does not render KPI cards or table while loading', () => {
      mockUseProperties.mockReturnValue({ data: undefined, isLoading: true, error: null });
      render(<AnalyticsPage />);

      expect(screen.queryByText('Portfolio IRR')).not.toBeInTheDocument();
      expect(screen.queryByText('Property Performance Comparison')).not.toBeInTheDocument();
    });
  });

  describe('Error state', () => {
    it('renders error message with retry button', () => {
      mockUseProperties.mockReturnValue({ data: undefined, isLoading: false, error: new Error('Network error') });
      render(<AnalyticsPage />);

      expect(screen.getByText('Error Loading Data')).toBeInTheDocument();
      expect(screen.getByText('Network error')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
    });

    it('shows generic message for non-Error objects', () => {
      mockUseProperties.mockReturnValue({ data: undefined, isLoading: false, error: 'string error' });
      render(<AnalyticsPage />);

      expect(screen.getByText('Failed to load portfolio data')).toBeInTheDocument();
    });
  });

  describe('Loaded state with data', () => {
    beforeEach(() => {
      mockUseProperties.mockReturnValue({
        data: { properties: mockProperties, total: mockProperties.length },
        isLoading: false,
        error: null,
      });
    });

    it('renders the page title', () => {
      render(<AnalyticsPage />);
      expect(screen.getByText('Portfolio Analytics')).toBeInTheDocument();
    });

    it('renders all four KPI cards', () => {
      render(<AnalyticsPage />);

      expect(screen.getByText('Portfolio IRR')).toBeInTheDocument();
      expect(screen.getByText('Cash-on-Cash Return')).toBeInTheDocument();
      expect(screen.getByText('Equity Multiple')).toBeInTheDocument();
      expect(screen.getByText('Average DSCR')).toBeInTheDocument();
    });

    it('renders portfolio summary section', () => {
      render(<AnalyticsPage />);

      expect(screen.getByText('Portfolio Summary')).toBeInTheDocument();
      expect(screen.getByText('Total Annual Portfolio NOI')).toBeInTheDocument();
      expect(screen.getByText('Average Portfolio Occupancy')).toBeInTheDocument();
    });

    it('calculates and displays portfolio NOI correctly', () => {
      render(<AnalyticsPage />);
      // NOI: 1,400,000 + 1,200,000 = 2,600,000 => $2.60M
      expect(screen.getByText('$2.60M')).toBeInTheDocument();
    });

    it('calculates and displays average occupancy correctly', () => {
      render(<AnalyticsPage />);
      // Occupancy: (0.94 + 0.97) / 2 = 0.955 => 95.5%
      expect(screen.getByText('95.5%')).toBeInTheDocument();
    });

    it('renders section headings', () => {
      render(<AnalyticsPage />);

      expect(screen.getByText('Portfolio Distribution')).toBeInTheDocument();
      expect(screen.getByText('Property Analysis')).toBeInTheDocument();
      expect(screen.getByText('Market Insights')).toBeInTheDocument();
      expect(screen.getByText('Property Performance Comparison')).toBeInTheDocument();
    });

    it('renders market insight widgets', () => {
      render(<AnalyticsPage />);

      expect(screen.getByTestId('market-overview')).toBeInTheDocument();
      expect(screen.getByTestId('economic-indicators')).toBeInTheDocument();
    });

    it('renders property names in the comparison table', () => {
      render(<AnalyticsPage />);

      expect(screen.getByText('Alpha Apartments')).toBeInTheDocument();
      expect(screen.getByText('Beta Residences')).toBeInTheDocument();
    });

    it('renders the Export Report button', () => {
      render(<AnalyticsPage />);
      expect(screen.getByRole('button', { name: /export report/i })).toBeInTheDocument();
    });

    it('renders sortable table headers', () => {
      render(<AnalyticsPage />);

      // Use getAllByRole to find column headers specifically
      const columnHeaders = screen.getAllByRole('columnheader');
      const headerTexts = columnHeaders.map(h => h.textContent?.trim());
      expect(headerTexts).toEqual(expect.arrayContaining(['Property \u21C5', 'Class', 'Submarket']));
      expect(headerTexts).toEqual(expect.arrayContaining([expect.stringContaining('IRR')]));
      expect(headerTexts).toEqual(expect.arrayContaining([expect.stringContaining('Annual NOI')]));
    });
  });

  describe('Loaded state with empty data', () => {
    it('renders zero KPI values when no properties returned', () => {
      mockUseProperties.mockReturnValue({
        data: { properties: [], total: 0 },
        isLoading: false,
        error: null,
      });
      render(<AnalyticsPage />);

      expect(screen.getByText('Portfolio IRR')).toBeInTheDocument();
      // IRR=0, CoC=0, EM=0, DSCR=0 => KPICard shows "N/A" for zero values
      const naValues = screen.getAllByText('N/A');
      expect(naValues.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('Data filtering for missing values', () => {
    it('excludes properties with 0 occupancy from average occupancy calculation', () => {
      const propsWithMissing = [
        makeProperty({ id: 'p1', name: 'Good Data', operations: { ...makeProperty().operations, occupancy: 0.90, noi: 1000000 } }),
        makeProperty({ id: 'p2', name: 'Missing Data', operations: { ...makeProperty().operations, occupancy: 0, noi: 500000 } }),
      ];
      mockUseProperties.mockReturnValue({
        data: { properties: propsWithMissing, total: 2 },
        isLoading: false,
        error: null,
      });
      render(<AnalyticsPage />);

      // Should show 90.0% (only Good Data), NOT 45.0% (average of 90% and 0%)
      expect(screen.getByText('90.0%')).toBeInTheDocument();
      expect(screen.queryByText('45.0%')).not.toBeInTheDocument();
    });

    it('does not highlight 0-value properties as worst performers', () => {
      const propsWithMissing = [
        makeProperty({ id: 'p1', name: 'Real Property', performance: { ...makeProperty().performance, leveredIrr: 0.15 } }),
        makeProperty({ id: 'p2', name: 'Missing IRR', performance: { ...makeProperty().performance, leveredIrr: 0 } }),
      ];
      mockUseProperties.mockReturnValue({
        data: { properties: propsWithMissing, total: 2 },
        isLoading: false,
        error: null,
      });
      const { container } = render(<AnalyticsPage />);

      // The property with 0 IRR should show "N/A" in the table, not be red-highlighted
      const redCells = container.querySelectorAll('.bg-red-50');
      // With only one non-zero property, there should be no worst-performer highlighting
      // (max === min when only one non-zero value)
      for (const cell of redCells) {
        expect(cell.textContent).not.toBe('N/A');
      }
    });
  });

  describe('Date range filter', () => {
    it('renders date range dropdown with default "Last Year"', () => {
      mockUseProperties.mockReturnValue({
        data: { properties: mockProperties, total: mockProperties.length },
        isLoading: false,
        error: null,
      });
      render(<AnalyticsPage />);

      const select = screen.getByRole('combobox');
      expect(select).toHaveValue('365');
    });

    it('allows changing date range', async () => {
      const user = userEvent.setup();
      mockUseProperties.mockReturnValue({
        data: { properties: mockProperties, total: mockProperties.length },
        isLoading: false,
        error: null,
      });
      render(<AnalyticsPage />);

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'all');

      expect(select).toHaveValue('all');
    });

    it('shows property count when filter is active', () => {
      mockUseProperties.mockReturnValue({
        data: { properties: mockProperties, total: mockProperties.length },
        isLoading: false,
        error: null,
      });
      render(<AnalyticsPage />);

      // Default is 365, so filter text should appear
      expect(screen.getByText(/of 2 properties/)).toBeInTheDocument();
    });
  });

  describe('Table sorting', () => {
    beforeEach(() => {
      mockUseProperties.mockReturnValue({
        data: { properties: mockProperties, total: mockProperties.length },
        isLoading: false,
        error: null,
      });
    });

    it('sorts by IRR when header is clicked', async () => {
      const user = userEvent.setup();
      render(<AnalyticsPage />);

      const irrHeader = screen.getByText(/^IRR/);
      await user.click(irrHeader);

      // After first click, should sort desc (18% first, 15% second)
      const rows = screen.getAllByRole('row');
      // row[0] is header, row[1] is first data row
      expect(rows[1]).toHaveTextContent('Alpha Apartments');
    });

    it('toggles sort direction on repeated clicks', async () => {
      const user = userEvent.setup();
      render(<AnalyticsPage />);

      const irrHeader = screen.getByText(/^IRR/);
      // First click: desc
      await user.click(irrHeader);
      // Second click: asc
      await user.click(irrHeader);

      const rows = screen.getAllByRole('row');
      expect(rows[1]).toHaveTextContent('Beta Residences');
    });
  });

  describe('Report Wizard', () => {
    it('opens report wizard on export button click', async () => {
      const user = userEvent.setup();
      mockUseProperties.mockReturnValue({
        data: { properties: mockProperties, total: mockProperties.length },
        isLoading: false,
        error: null,
      });
      render(<AnalyticsPage />);

      const exportBtn = screen.getByRole('button', { name: /export report/i });
      await user.click(exportBtn);

      await waitFor(() => {
        expect(screen.getByTestId('report-wizard')).toBeInTheDocument();
      });
    });
  });
});

describe('KPICard', () => {
  it('renders title and description', () => {
    render(<KPICard title="Test KPI" value={0.15} format="percentage" description="A test metric" />);

    expect(screen.getByText('Test KPI')).toBeInTheDocument();
    expect(screen.getByText('A test metric')).toBeInTheDocument();
  });

  it('formats percentage values correctly', () => {
    render(<KPICard title="IRR" value={0.1825} format="percentage" />);
    expect(screen.getByText('18.25%')).toBeInTheDocument();
  });

  it('formats currency values correctly', () => {
    render(<KPICard title="Value" value={1500000} format="currency" />);
    expect(screen.getByText('$1,500,000')).toBeInTheDocument();
  });

  it('formats decimal values correctly', () => {
    render(<KPICard title="Multiple" value={2.156} format="decimal" />);
    expect(screen.getByText('2.16')).toBeInTheDocument();
  });

  it('renders string values as-is', () => {
    render(<KPICard title="Status" value="Active" />);
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('shows positive trend with green color', () => {
    const { container } = render(<KPICard title="KPI" value={100} trend={5.2} />);
    const trendEl = container.querySelector('.text-green-600');
    expect(trendEl).toBeInTheDocument();
    expect(screen.getByText('5.2%')).toBeInTheDocument();
  });

  it('shows negative trend with red color', () => {
    const { container } = render(<KPICard title="KPI" value={100} trend={-3.1} />);
    const trendEl = container.querySelector('.text-red-600');
    expect(trendEl).toBeInTheDocument();
    expect(screen.getByText('3.1%')).toBeInTheDocument();
  });

  it('does not show trend icon when trend is zero', () => {
    const { container } = render(<KPICard title="KPI" value={100} trend={0} />);
    // trend === 0 should not render the trend section
    const trendIcons = container.querySelectorAll('.text-green-600, .text-red-600');
    expect(trendIcons.length).toBe(0);
  });

  it('does not show trend section when trend is undefined', () => {
    render(<KPICard title="KPI" value={100} />);
    // No percentage trend displayed
    expect(screen.queryByText(/%$/)).not.toBeInTheDocument();
  });

  it('shows "N/A" for zero value when treatZeroAsNA is true (default)', () => {
    render(<KPICard title="Cap Rate" value={0} format="percentage" />);
    expect(screen.getByText('N/A')).toBeInTheDocument();
  });

  it('shows "0" for zero value when treatZeroAsNA is false (count metric)', () => {
    render(<KPICard title="Active Deals" value={0} format="number" treatZeroAsNA={false} />);
    expect(screen.getByText('0')).toBeInTheDocument();
  });

  it('shows formatted zero currency when treatZeroAsNA is false', () => {
    render(<KPICard title="Revenue" value={0} format="currency" treatZeroAsNA={false} />);
    expect(screen.getByText('$0')).toBeInTheDocument();
  });

  it('shows "0.00%" for zero percentage when treatZeroAsNA is false', () => {
    render(<KPICard title="Growth" value={0} format="percentage" treatZeroAsNA={false} />);
    expect(screen.getByText('0.00%')).toBeInTheDocument();
  });

  it('shows "0.00" for zero decimal when treatZeroAsNA is false', () => {
    render(<KPICard title="Multiple" value={0} format="decimal" treatZeroAsNA={false} />);
    expect(screen.getByText('0.00')).toBeInTheDocument();
  });
});
