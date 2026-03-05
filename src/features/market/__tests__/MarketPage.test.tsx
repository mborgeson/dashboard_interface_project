import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { MarketPage } from '../MarketPage';
import type { MSAOverview, EconomicIndicator, MarketTrend, SubmarketMetrics } from '@/types/market';

// ---------- Mock recharts to avoid canvas/SVG issues in JSDOM ----------
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

// ---------- Mock the lazy-loaded ReportWizard ----------
vi.mock('@/features/reporting-suite/components/ReportWizard/ReportWizard', () => ({
  ReportWizard: ({ open }: { open: boolean }) =>
    open ? <div data-testid="report-wizard">Report Wizard</div> : null,
}));

// ---------- Mock data ----------
const mockMsaOverview: MSAOverview = {
  population: 5000000,
  employment: 2500000,
  gdp: 300000000000,
  populationGrowth: 0.018,
  employmentGrowth: 0.025,
  gdpGrowth: 0.032,
  lastUpdated: '2026-03-01T00:00:00Z',
};

const mockIndicators: EconomicIndicator[] = [
  { indicator: 'Unemployment Rate', value: 3.5, yoyChange: -0.02, unit: '%' },
  { indicator: 'Job Growth Rate', value: 3.2, yoyChange: 0.015, unit: '%' },
  { indicator: 'Median Household Income', value: 72000, yoyChange: 0.03, unit: '$' },
  { indicator: 'Population Growth', value: 1.8, yoyChange: 0.005, unit: '%' },
];

const mockTrends: Array<MarketTrend & { rentGrowthPct: number; occupancyPct: number; capRatePct: number }> = [
  { month: '2025-04', rentGrowth: 0.035, occupancy: 0.945, capRate: 0.052, rentGrowthPct: 3.5, occupancyPct: 94.5, capRatePct: 5.2 },
  { month: '2025-05', rentGrowth: 0.038, occupancy: 0.948, capRate: 0.051, rentGrowthPct: 3.8, occupancyPct: 94.8, capRatePct: 5.1 },
];

const mockSubmarkets: Array<SubmarketMetrics & { rentGrowthPct: number; occupancyPct: number; capRatePct: number }> = [
  { name: 'Scottsdale', avgRent: 1850, rentGrowth: 0.042, occupancy: 0.96, capRate: 0.048, inventory: 45000, absorption: 1200, rentGrowthPct: 4.2, occupancyPct: 96.0, capRatePct: 4.8 },
  { name: 'Tempe', avgRent: 1650, rentGrowth: 0.038, occupancy: 0.94, capRate: 0.052, inventory: 38000, absorption: 800, rentGrowthPct: 3.8, occupancyPct: 94.0, capRatePct: 5.2 },
];

const mockSparkline = {
  unemployment: [4.0, 3.8, 3.7, 3.6, 3.5, 3.5],
  jobGrowth: [2.8, 3.0, 3.1, 3.2, 3.3, 3.2],
  incomeGrowth: [2.5, 2.6, 2.8, 2.9, 3.0, 3.0],
  populationGrowth: [1.5, 1.6, 1.7, 1.7, 1.8, 1.8],
};

// ---------- Mock the composite useMarketData hook ----------
const mockRefreshAll = vi.fn().mockResolvedValue(undefined);

const defaultHookReturn = {
  msaOverview: mockMsaOverview,
  economicIndicators: mockIndicators,
  marketTrends: mockTrends,
  submarketMetrics: mockSubmarkets,
  monthlyMarketData: [],
  aggregateMetrics: { totalInventory: 83000, avgOccupancy: 0.95, avgRentGrowth: 0.04, avgCapRate: 0.05 },
  sparklineData: mockSparkline,
  isSparklinePlaceholder: false,
  isLoading: false,
  error: null,
  refreshAll: mockRefreshAll,
};

vi.mock('../hooks/useMarketData', () => ({
  useMarketData: vi.fn(() => defaultHookReturn),
}));

import { useMarketData } from '../hooks/useMarketData';
const mockedUseMarketData = vi.mocked(useMarketData);

// ============================================================================
// Tests
// ============================================================================

describe('MarketPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedUseMarketData.mockReturnValue(defaultHookReturn);
  });

  // ------ Render tests ------

  it('renders the page header', () => {
    render(<MarketPage />);
    expect(screen.getByText('Market Data')).toBeInTheDocument();
    expect(
      screen.getByText('Phoenix MSA real estate market analysis and economic indicators')
    ).toBeInTheDocument();
  });

  it('renders the sub-navigation with Phoenix MSA and USA tabs', () => {
    render(<MarketPage />);
    expect(screen.getByText('Phoenix MSA')).toBeInTheDocument();
    expect(screen.getByText('USA')).toBeInTheDocument();
  });

  it('renders refresh and export buttons', () => {
    render(<MarketPage />);
    expect(screen.getByText('Refresh Data')).toBeInTheDocument();
    expect(screen.getByText('Export Report')).toBeInTheDocument();
  });

  it('renders the timeframe indicator', () => {
    render(<MarketPage />);
    expect(screen.getByText('YoY (Year-over-Year)')).toBeInTheDocument();
  });

  // ------ Section visibility tests ------

  it('renders Phoenix MSA Overview section with metrics', () => {
    render(<MarketPage />);
    expect(screen.getByText('Phoenix MSA Overview')).toBeInTheDocument();
    expect(screen.getByText('Population')).toBeInTheDocument();
    expect(screen.getByText('Employment')).toBeInTheDocument();
    expect(screen.getByText('GDP')).toBeInTheDocument();
  });

  it('renders Key Economic Indicators section', () => {
    render(<MarketPage />);
    expect(screen.getByText('Key Economic Indicators')).toBeInTheDocument();
    expect(screen.getByText('Unemployment Rate')).toBeInTheDocument();
    expect(screen.getByText('Job Growth Rate')).toBeInTheDocument();
  });

  it('renders Market Trends chart section', () => {
    render(<MarketPage />);
    expect(screen.getByText('Market Trends')).toBeInTheDocument();
  });

  it('renders Market Performance Heatmap section', () => {
    render(<MarketPage />);
    expect(screen.getByText('Market Performance Heatmap')).toBeInTheDocument();
  });

  it('renders Submarket Comparison section', () => {
    render(<MarketPage />);
    expect(screen.getByText('Submarket Comparison')).toBeInTheDocument();
  });

  it('renders Market Data Sources footer', () => {
    render(<MarketPage />);
    expect(screen.getByText('Market Data Sources')).toBeInTheDocument();
  });

  // ------ Loading state ------

  it('shows skeleton loading state when data is loading', () => {
    mockedUseMarketData.mockReturnValue({
      ...defaultHookReturn,
      isLoading: true,
      msaOverview: null,
      economicIndicators: [],
      marketTrends: [],
      submarketMetrics: [],
    });

    const { container } = render(<MarketPage />);
    // Should show skeleton placeholders
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
    // Should NOT show data sections
    expect(screen.queryByText('Phoenix MSA Overview')).not.toBeInTheDocument();
  });

  // ------ Error state ------

  it('shows error state when hook returns an error', () => {
    mockedUseMarketData.mockReturnValue({
      ...defaultHookReturn,
      error: new Error('Network error'),
      isLoading: false,
    });

    render(<MarketPage />);
    expect(screen.getByText('Failed to load market data')).toBeInTheDocument();
    expect(
      screen.getByText('Unable to fetch market data. Please try again later.')
    ).toBeInTheDocument();
    expect(screen.getByText('Try Again')).toBeInTheDocument();
  });

  it('still shows header and sub-nav in error state', () => {
    mockedUseMarketData.mockReturnValue({
      ...defaultHookReturn,
      error: new Error('Server error'),
      isLoading: false,
    });

    render(<MarketPage />);
    expect(screen.getByText('Market Data')).toBeInTheDocument();
    expect(screen.getByText('Phoenix MSA')).toBeInTheDocument();
    expect(screen.getByText('USA')).toBeInTheDocument();
  });

  // ------ Null msaOverview ------

  it('does not render MarketOverview when msaOverview is null', () => {
    mockedUseMarketData.mockReturnValue({
      ...defaultHookReturn,
      msaOverview: null,
    });

    render(<MarketPage />);
    expect(screen.queryByText('Phoenix MSA Overview')).not.toBeInTheDocument();
    // Other sections should still render
    expect(screen.getByText('Key Economic Indicators')).toBeInTheDocument();
  });

  // ------ Empty submarkets ------

  it('renders heatmap and comparison with empty submarkets without crashing', () => {
    mockedUseMarketData.mockReturnValue({
      ...defaultHookReturn,
      submarketMetrics: [],
    });

    render(<MarketPage />);
    expect(screen.getByText('Market Performance Heatmap')).toBeInTheDocument();
    expect(screen.getByText('Submarket Comparison')).toBeInTheDocument();
  });

  // ------ Sparkline placeholder ------

  it('shows sparkline placeholder badge when no trend data', () => {
    mockedUseMarketData.mockReturnValue({
      ...defaultHookReturn,
      isSparklinePlaceholder: true,
      sparklineData: { unemployment: [], jobGrowth: [], incomeGrowth: [], populationGrowth: [] },
    });

    render(<MarketPage />);
    expect(screen.getByText('No trend data available')).toBeInTheDocument();
  });

  // ------ Refresh button ------

  it('calls refreshAll when refresh button is clicked', async () => {
    render(<MarketPage />);
    const refreshBtn = screen.getByText('Refresh Data');
    refreshBtn.click();

    await waitFor(() => {
      expect(mockRefreshAll).toHaveBeenCalledTimes(1);
    });
  });

  // ------ Submarket data display ------

  it('displays submarket names in heatmap and comparison', () => {
    render(<MarketPage />);
    // Each submarket appears in both heatmap and comparison table
    expect(screen.getAllByText('Scottsdale').length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText('Tempe').length).toBeGreaterThanOrEqual(2);
  });

  // ------ MarketOverview formatting ------

  it('formats large population numbers with M suffix', () => {
    render(<MarketPage />);
    expect(screen.getByText('5.0M')).toBeInTheDocument();
  });

  it('formats GDP with dollar sign and B suffix', () => {
    render(<MarketPage />);
    expect(screen.getByText('$300.0B')).toBeInTheDocument();
  });

  // ------ Economic Indicators formatting ------

  it('displays indicator values with correct formatting', () => {
    render(<MarketPage />);
    // Unemployment 3.5%
    expect(screen.getByText('3.5%')).toBeInTheDocument();
    // Median Household Income $72K
    expect(screen.getByText('$72K')).toBeInTheDocument();
  });
});
