import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { DashboardMain } from '../DashboardMain';
import type { Property } from '@/types';

// Mock ResizeObserver for Recharts
class ResizeObserverMock {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
vi.stubGlobal('ResizeObserver', ResizeObserverMock);

// Mock Leaflet map component
vi.mock('../components/PropertyMap', () => ({
  PropertyMap: () => <div data-testid="property-map">Map</div>,
}));

// Mock chart components
vi.mock('../components/PortfolioPerformanceChart', () => ({
  PortfolioPerformanceChart: () => <div data-testid="perf-chart">Chart</div>,
}));
vi.mock('../components/PropertyDistributionChart', () => ({
  PropertyDistributionChart: () => <div data-testid="dist-chart">Chart</div>,
}));

// Mock market widgets
vi.mock('@/features/market/components/widgets/MarketTrendsWidget', () => ({
  MarketTrendsWidget: () => <div data-testid="market-trends">Trends</div>,
}));
vi.mock('@/features/market/components/widgets/MarketOverviewWidget', () => ({
  MarketOverviewWidget: () => <div data-testid="market-overview">Overview</div>,
}));
vi.mock('@/features/market/components/widgets/SubmarketComparisonWidget', () => ({
  SubmarketComparisonWidget: () => <div data-testid="submarket-comp">Submarkets</div>,
}));

// Mock hooks
const mockUseProperties = vi.fn();
vi.mock('@/hooks/api/useProperties', () => ({
  useProperties: () => mockUseProperties(),
  selectProperties: (data: { properties: Property[] } | undefined) => data?.properties ?? [],
}));

const mockUseTransactions = vi.fn();
vi.mock('@/hooks/api/useTransactions', () => ({
  useTransactionsWithMockFallback: () => mockUseTransactions(),
}));

// --- Factory ---
function makeProperty(overrides: Partial<Property> & { id: string; name: string }): Property {
  return {
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

// Properties with varying data quality
const propertyWithAllData = makeProperty({
  id: 'p1',
  name: 'Alpha Apartments',
  valuation: { currentValue: 30000000, lastAppraisalDate: new Date('2025-01-01'), capRate: 0.06, appreciationSinceAcquisition: 0.15 },
  operations: { occupancy: 0.95, averageRent: 1600, rentPerSqft: 1.8, monthlyRevenue: 160000, otherIncome: 5000, expenses: { realEstateTaxes: 100000, otherExpenses: 20000, propertyInsurance: 30000, staffingPayroll: 80000, propertyManagementFee: 60000, repairsAndMaintenance: 40000, turnover: 15000, contractServices: 10000, reservesForReplacement: 25000, adminLegalSecurity: 10000, advertisingLeasingMarketing: 5000, total: 395000 }, noi: 1500000, operatingExpenseRatio: 0.22, grossPotentialRevenue: 1800000, netRentalIncome: 1600000, otherIncomeAnnual: 60000, vacancyLoss: 100000, concessions: 0 },
  performance: { leveredIrr: 0.22, leveredMoic: 2.5, unleveredIrr: 0.14, unleveredMoic: 1.8, totalEquityCommitment: 10000000, totalCashFlowsToEquity: 25000000, netCashFlowsToEquity: 15000000, holdPeriodYears: 5, exitCapRate: 0.05, totalBasisPerUnitClose: 250000, seniorLoanBasisPerUnitClose: 150000, totalBasisPerUnitExit: null, seniorLoanBasisPerUnitExit: null },
});

const propertyMissingValue = makeProperty({
  id: 'p2',
  name: 'Beta Missing Value',
  valuation: { currentValue: 0, lastAppraisalDate: new Date('2025-01-01'), capRate: 0, appreciationSinceAcquisition: 0 },
  operations: { occupancy: 0, averageRent: 0, rentPerSqft: 0, monthlyRevenue: 0, otherIncome: 0, expenses: { realEstateTaxes: 0, otherExpenses: 0, propertyInsurance: 0, staffingPayroll: 0, propertyManagementFee: 0, repairsAndMaintenance: 0, turnover: 0, contractServices: 0, reservesForReplacement: 0, adminLegalSecurity: 0, advertisingLeasingMarketing: 0, total: 0 }, noi: 0, operatingExpenseRatio: 0, grossPotentialRevenue: 0, netRentalIncome: 0, otherIncomeAnnual: 0, vacancyLoss: 0, concessions: 0 },
  performance: { leveredIrr: 0, leveredMoic: 0, unleveredIrr: null, unleveredMoic: null, totalEquityCommitment: 0, totalCashFlowsToEquity: 0, netCashFlowsToEquity: 0, holdPeriodYears: 0, exitCapRate: 0, totalBasisPerUnitClose: 0, seniorLoanBasisPerUnitClose: 0, totalBasisPerUnitExit: null, seniorLoanBasisPerUnitExit: null },
  propertyDetails: { units: 0, squareFeet: 0, averageUnitSize: 0, yearBuilt: 0, propertyClass: 'B', assetType: 'Multifamily', amenities: [] },
});

const propertyNegativeIrr = makeProperty({
  id: 'p3',
  name: 'Gamma Negative IRR',
  performance: { leveredIrr: -0.049, leveredMoic: 0.8, unleveredIrr: -0.004, unleveredMoic: 0.9, totalEquityCommitment: 10000000, totalCashFlowsToEquity: 8000000, netCashFlowsToEquity: -2000000, holdPeriodYears: 5, exitCapRate: 0.06, totalBasisPerUnitClose: 250000, seniorLoanBasisPerUnitClose: 150000, totalBasisPerUnitExit: null, seniorLoanBasisPerUnitExit: null },
});

const propertyHighIrr = makeProperty({
  id: 'p4',
  name: 'Delta High IRR',
  performance: { leveredIrr: 0.30, leveredMoic: 3.0, unleveredIrr: 0.20, unleveredMoic: 2.0, totalEquityCommitment: 10000000, totalCashFlowsToEquity: 30000000, netCashFlowsToEquity: 20000000, holdPeriodYears: 5, exitCapRate: 0.045, totalBasisPerUnitClose: 250000, seniorLoanBasisPerUnitClose: 150000, totalBasisPerUnitExit: null, seniorLoanBasisPerUnitExit: null },
});

const secondPropertyWithCapRate = makeProperty({
  id: 'p5',
  name: 'Epsilon Second Cap',
  valuation: { currentValue: 20000000, lastAppraisalDate: new Date('2025-01-01'), capRate: 0.08, appreciationSinceAcquisition: 0.10 },
  performance: { leveredIrr: 0.12, leveredMoic: 1.6, unleveredIrr: 0.08, unleveredMoic: 1.3, totalEquityCommitment: 8000000, totalCashFlowsToEquity: 12800000, netCashFlowsToEquity: 4800000, holdPeriodYears: 5, exitCapRate: 0.055, totalBasisPerUnitClose: 200000, seniorLoanBasisPerUnitClose: 120000, totalBasisPerUnitExit: null, seniorLoanBasisPerUnitExit: null },
});

beforeEach(() => {
  vi.clearAllMocks();
  mockUseTransactions.mockReturnValue({ data: { transactions: [], total: 0 } });
});

describe('DashboardMain', () => {
  describe('loading and error states', () => {
    it('shows skeleton when loading', () => {
      mockUseProperties.mockReturnValue({ data: undefined, isLoading: true, error: null });
      render(<DashboardMain />);
      expect(screen.getByText('Loading real-time performance data...')).toBeInTheDocument();
    });

    it('shows error state on failure', () => {
      mockUseProperties.mockReturnValue({ data: undefined, isLoading: false, error: new Error('Server error') });
      render(<DashboardMain />);
      expect(screen.getByText('Server error')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
    });
  });

  describe('KPI cards exclude missing data from aggregations', () => {
    it('excludes properties with currentValue=0 from Portfolio Value', () => {
      // Alpha: $30M, Beta: $0 (missing), Epsilon: $20M
      mockUseProperties.mockReturnValue({
        data: { properties: [propertyWithAllData, propertyMissingValue, secondPropertyWithCapRate], total: 3 },
        isLoading: false,
        error: null,
      });
      render(<DashboardMain />);

      // Total should be $30M + $20M = $50M; Beta ($0 = missing) excluded
      const portfolioValueCard = screen.getByText('Portfolio Value').closest('.p-6');
      const heroStat = portfolioValueCard!.querySelector('.text-hero-stat');
      expect(heroStat).toHaveTextContent('$50.0M');
    });

    it('excludes properties with occupancy=0 from avg occupancy', () => {
      mockUseProperties.mockReturnValue({
        data: { properties: [propertyWithAllData, propertyMissingValue], total: 2 },
        isLoading: false,
        error: null,
      });
      render(<DashboardMain />);

      // Only Alpha has occupancy (0.95 = 95.0%), Beta is excluded from avg
      expect(screen.getByText(/95\.0% Occupied/)).toBeInTheDocument();
    });

    it('excludes properties with capRate=0 from avg cap rate', () => {
      // Alpha capRate=0.06, Beta capRate=0, Epsilon capRate=0.08
      // Avg should be (0.06 + 0.08) / 2 = 0.07 = 7.0%
      mockUseProperties.mockReturnValue({
        data: { properties: [propertyWithAllData, propertyMissingValue, secondPropertyWithCapRate], total: 3 },
        isLoading: false,
        error: null,
      });
      render(<DashboardMain />);
      expect(screen.getByText('7.0%')).toBeInTheDocument();
    });

    it('shows "--" for cap rate when all properties have capRate=0', () => {
      mockUseProperties.mockReturnValue({
        data: { properties: [propertyMissingValue], total: 1 },
        isLoading: false,
        error: null,
      });
      render(<DashboardMain />);

      // The cap rate card should show '--'
      const avgCapRateCard = screen.getByText('Average Cap Rate');
      // Find the hero stat value in the same card
      const cardEl = avgCapRateCard.closest('.p-6');
      expect(cardEl).toHaveTextContent('--');
    });

    it('shows "--" for monthly NOI when all properties have noi=0', () => {
      mockUseProperties.mockReturnValue({
        data: { properties: [propertyMissingValue], total: 1 },
        isLoading: false,
        error: null,
      });
      render(<DashboardMain />);

      const noiLabel = screen.getByText('Monthly NOI');
      const cardEl = noiLabel.closest('.p-6');
      expect(cardEl).toHaveTextContent('--');
    });
  });

  describe('Top Performing Properties', () => {
    it('filters out properties with leveredIrr=0 (missing data)', () => {
      mockUseProperties.mockReturnValue({
        data: { properties: [propertyWithAllData, propertyMissingValue, propertyHighIrr], total: 3 },
        isLoading: false,
        error: null,
      });
      render(<DashboardMain />);

      // Alpha (22%) and Delta (30%) should appear; Beta (0% = missing) should NOT
      expect(screen.getByText('Delta High IRR')).toBeInTheDocument();
      expect(screen.getByText('Alpha Apartments')).toBeInTheDocument();
      expect(screen.queryByText('Beta Missing Value')).not.toBeInTheDocument();
    });

    it('ranks properties by IRR in descending order', () => {
      mockUseProperties.mockReturnValue({
        data: { properties: [propertyWithAllData, propertyHighIrr, secondPropertyWithCapRate], total: 3 },
        isLoading: false,
        error: null,
      });
      render(<DashboardMain />);

      const performerSection = screen.getByText('Top Performing Properties').closest('.p-6');
      const names = performerSection!.querySelectorAll('.font-medium.text-neutral-900');
      const nameTexts = Array.from(names).map(el => el.textContent);

      // Delta (30%) > Alpha (22%) > Epsilon (12%)
      expect(nameTexts[0]).toBe('Delta High IRR');
      expect(nameTexts[1]).toBe('Alpha Apartments');
      expect(nameTexts[2]).toBe('Epsilon Second Cap');
    });

    it('shows negative IRR in red', () => {
      mockUseProperties.mockReturnValue({
        data: { properties: [propertyNegativeIrr], total: 1 },
        isLoading: false,
        error: null,
      });
      render(<DashboardMain />);

      // Negative IRR should be red
      const irrDisplay = screen.getByText('-4.9%');
      expect(irrDisplay).toHaveClass('text-red-600');
    });

    it('shows N/A for units when units=0', () => {
      const propMissingUnits = makeProperty({
        id: 'p-nounits',
        name: 'No Units Property',
        propertyDetails: { units: 0, squareFeet: 0, averageUnitSize: 0, yearBuilt: 2000, propertyClass: 'B', assetType: 'Multifamily', amenities: [] },
        performance: { leveredIrr: 0.15, leveredMoic: 2.0, unleveredIrr: 0.10, unleveredMoic: 1.5, totalEquityCommitment: 10000000, totalCashFlowsToEquity: 20000000, netCashFlowsToEquity: 10000000, holdPeriodYears: 5, exitCapRate: 0.05, totalBasisPerUnitClose: 250000, seniorLoanBasisPerUnitClose: 150000, totalBasisPerUnitExit: null, seniorLoanBasisPerUnitExit: null },
      });
      mockUseProperties.mockReturnValue({
        data: { properties: [propMissingUnits], total: 1 },
        isLoading: false,
        error: null,
      });
      render(<DashboardMain />);

      // Top performers section should show N/A instead of "0 units"
      const performerSection = screen.getByText('Top Performing Properties').closest('.p-6');
      expect(performerSection).toHaveTextContent('N/A');
      expect(performerSection).not.toHaveTextContent('0 units');
    });
  });

  describe('Recent Transactions', () => {
    it('shows transactions sorted by date (newest first)', () => {
      const transactions = [
        { id: 't1', propertyId: 'p1', propertyName: 'Alpha Deal', type: 'acquisition' as const, amount: 5000000, date: new Date('2025-12-01'), description: 'Acquired Alpha' },
        { id: 't2', propertyId: 'p2', propertyName: 'Beta Deal', type: 'distribution' as const, amount: 200000, date: new Date('2026-01-15'), description: 'Q4 distribution' },
        { id: 't3', propertyId: 'p3', propertyName: 'Gamma Deal', type: 'capital_improvement' as const, amount: 100000, date: new Date('2026-02-01'), description: 'Roof replacement' },
      ];

      mockUseProperties.mockReturnValue({
        data: { properties: [propertyWithAllData], total: 1 },
        isLoading: false,
        error: null,
      });
      mockUseTransactions.mockReturnValue({ data: { transactions, total: 3 } });

      render(<DashboardMain />);

      const txnSection = screen.getByText('Recent Transactions').closest('.p-6');
      const txnNames = txnSection!.querySelectorAll('.font-medium.text-neutral-900');
      const nameTexts = Array.from(txnNames).map(el => el.textContent);

      // Should be sorted newest first
      expect(nameTexts[0]).toBe('Gamma Deal');
      expect(nameTexts[1]).toBe('Beta Deal');
      expect(nameTexts[2]).toBe('Alpha Deal');
    });

    it('shows distribution in green and acquisition in blue', () => {
      const transactions = [
        { id: 't1', propertyId: 'p1', propertyName: 'Acquisition Deal', type: 'acquisition' as const, amount: 5000000, date: new Date('2026-01-15'), description: 'Acquired' },
        { id: 't2', propertyId: 'p2', propertyName: 'Distribution Deal', type: 'distribution' as const, amount: 200000, date: new Date('2026-01-10'), description: 'Distributed' },
      ];

      mockUseProperties.mockReturnValue({
        data: { properties: [propertyWithAllData], total: 1 },
        isLoading: false,
        error: null,
      });
      mockUseTransactions.mockReturnValue({ data: { transactions, total: 2 } });

      render(<DashboardMain />);

      // Acquisition amount should be blue
      const amounts = screen.getAllByText(/\$\d/);
      const acqAmount = amounts.find(el => el.textContent === '$5.0M');
      const distAmount = amounts.find(el => el.textContent === '$200K');

      expect(acqAmount).toHaveClass('text-blue-600');
      expect(distAmount).toHaveClass('text-green-600');
    });
  });

  describe('Portfolio Distribution', () => {
    it('shows correct property class breakdown', () => {
      const classAProperty = makeProperty({
        id: 'pa',
        name: 'Class A Place',
        propertyDetails: { units: 200, squareFeet: 180000, averageUnitSize: 900, yearBuilt: 2020, propertyClass: 'A', assetType: 'Multifamily', amenities: [] },
        valuation: { currentValue: 50000000, lastAppraisalDate: new Date('2025-01-01'), capRate: 0.05, appreciationSinceAcquisition: 0.20 },
      });

      mockUseProperties.mockReturnValue({
        data: { properties: [classAProperty, propertyWithAllData], total: 2 },
        isLoading: false,
        error: null,
      });
      render(<DashboardMain />);

      // Class A should have 1 property, Class B should have 1
      const distSection = screen.getByText('Portfolio Distribution').closest('.p-6');
      expect(distSection).toHaveTextContent('Class A');
      expect(distSection).toHaveTextContent('Class B');
    });
  });

  describe('empty state', () => {
    it('renders with zero properties without crashing', () => {
      mockUseProperties.mockReturnValue({
        data: { properties: [], total: 0 },
        isLoading: false,
        error: null,
      });
      render(<DashboardMain />);

      expect(screen.getByText('Portfolio Dashboard')).toBeInTheDocument();
      expect(screen.getByText(/0 Phoenix MSA properties/)).toBeInTheDocument();
    });
  });
});
