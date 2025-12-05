/**
 * Mock Interest Rate Data
 * Based on real-world Treasury rates and market data
 */

export interface KeyRate {
  id: string;
  name: string;
  shortName: string;
  currentValue: number;
  previousValue: number;
  change: number;
  changePercent: number;
  asOfDate: string;
  category: 'federal' | 'treasury' | 'sofr' | 'mortgage';
  description: string;
}

export interface YieldCurvePoint {
  maturity: string;
  yield: number;
  previousYield: number;
  maturityMonths: number;
}

export interface HistoricalRate {
  date: string;
  federalFunds: number;
  treasury2Y: number;
  treasury5Y: number;
  treasury10Y: number;
  treasury30Y: number;
  sofr: number;
  mortgage30Y: number;
}

export interface RateDataSource {
  id: string;
  name: string;
  url: string;
  description: string;
  dataTypes: string[];
  updateFrequency: string;
  logo?: string;
}

// Current key rates (as of mock date)
export const mockKeyRates: KeyRate[] = [
  {
    id: 'fed-funds',
    name: 'Federal Funds Rate',
    shortName: 'Fed Funds',
    currentValue: 5.33,
    previousValue: 5.33,
    change: 0,
    changePercent: 0,
    asOfDate: '2025-12-05',
    category: 'federal',
    description: 'The interest rate at which banks lend reserve balances to other banks overnight.',
  },
  {
    id: 'prime-rate',
    name: 'Prime Rate',
    shortName: 'Prime',
    currentValue: 8.50,
    previousValue: 8.50,
    change: 0,
    changePercent: 0,
    asOfDate: '2025-12-05',
    category: 'federal',
    description: 'The rate that commercial banks charge their most creditworthy customers.',
  },
  {
    id: 'treasury-2y',
    name: '2-Year Treasury Yield',
    shortName: '2Y Treasury',
    currentValue: 4.18,
    previousValue: 4.21,
    change: -0.03,
    changePercent: -0.71,
    asOfDate: '2025-12-05',
    category: 'treasury',
    description: 'Yield on 2-year U.S. Treasury notes.',
  },
  {
    id: 'treasury-5y',
    name: '5-Year Treasury Yield',
    shortName: '5Y Treasury',
    currentValue: 4.05,
    previousValue: 4.09,
    change: -0.04,
    changePercent: -0.98,
    asOfDate: '2025-12-05',
    category: 'treasury',
    description: 'Yield on 5-year U.S. Treasury notes.',
  },
  {
    id: 'treasury-7y',
    name: '7-Year Treasury Yield',
    shortName: '7Y Treasury',
    currentValue: 4.12,
    previousValue: 4.15,
    change: -0.03,
    changePercent: -0.72,
    asOfDate: '2025-12-05',
    category: 'treasury',
    description: 'Yield on 7-year U.S. Treasury notes.',
  },
  {
    id: 'treasury-10y',
    name: '10-Year Treasury Yield',
    shortName: '10Y Treasury',
    currentValue: 4.22,
    previousValue: 4.26,
    change: -0.04,
    changePercent: -0.94,
    asOfDate: '2025-12-05',
    category: 'treasury',
    description: 'Yield on 10-year U.S. Treasury notes. Key benchmark for mortgage rates.',
  },
  {
    id: 'sofr-1m',
    name: '1-Month SOFR',
    shortName: '1M SOFR',
    currentValue: 5.34,
    previousValue: 5.34,
    change: 0,
    changePercent: 0,
    asOfDate: '2025-12-05',
    category: 'sofr',
    description: 'Secured Overnight Financing Rate, 1-month average.',
  },
  {
    id: 'sofr-term-1m',
    name: '1-Month Term SOFR',
    shortName: '1M Term SOFR',
    currentValue: 5.32,
    previousValue: 5.33,
    change: -0.01,
    changePercent: -0.19,
    asOfDate: '2025-12-05',
    category: 'sofr',
    description: 'CME Term SOFR, 1-month rate.',
  },
  {
    id: 'mortgage-30y',
    name: '30-Year Fixed Mortgage Rate',
    shortName: '30Y Mortgage',
    currentValue: 6.84,
    previousValue: 6.91,
    change: -0.07,
    changePercent: -1.01,
    asOfDate: '2025-12-05',
    category: 'mortgage',
    description: 'Average rate for 30-year fixed-rate mortgages.',
  },
];

// Treasury Yield Curve Data
export const mockYieldCurve: YieldCurvePoint[] = [
  { maturity: '1M', yield: 5.47, previousYield: 5.48, maturityMonths: 1 },
  { maturity: '3M', yield: 5.41, previousYield: 5.42, maturityMonths: 3 },
  { maturity: '6M', yield: 5.18, previousYield: 5.20, maturityMonths: 6 },
  { maturity: '1Y', yield: 4.65, previousYield: 4.68, maturityMonths: 12 },
  { maturity: '2Y', yield: 4.18, previousYield: 4.21, maturityMonths: 24 },
  { maturity: '3Y', yield: 4.08, previousYield: 4.11, maturityMonths: 36 },
  { maturity: '5Y', yield: 4.05, previousYield: 4.09, maturityMonths: 60 },
  { maturity: '7Y', yield: 4.12, previousYield: 4.15, maturityMonths: 84 },
  { maturity: '10Y', yield: 4.22, previousYield: 4.26, maturityMonths: 120 },
  { maturity: '20Y', yield: 4.52, previousYield: 4.55, maturityMonths: 240 },
  { maturity: '30Y', yield: 4.42, previousYield: 4.46, maturityMonths: 360 },
];

// Historical Rate Data (last 12 months)
export const mockHistoricalRates: HistoricalRate[] = [
  { date: '2025-01', federalFunds: 5.33, treasury2Y: 4.21, treasury5Y: 3.84, treasury10Y: 3.95, treasury30Y: 4.14, sofr: 5.31, mortgage30Y: 6.64 },
  { date: '2025-02', federalFunds: 5.33, treasury2Y: 4.64, treasury5Y: 4.26, treasury10Y: 4.25, treasury30Y: 4.38, sofr: 5.31, mortgage30Y: 6.94 },
  { date: '2025-03', federalFunds: 5.33, treasury2Y: 4.59, treasury5Y: 4.21, treasury10Y: 4.20, treasury30Y: 4.34, sofr: 5.31, mortgage30Y: 6.82 },
  { date: '2025-04', federalFunds: 5.33, treasury2Y: 4.97, treasury5Y: 4.63, treasury10Y: 4.59, treasury30Y: 4.73, sofr: 5.31, mortgage30Y: 7.17 },
  { date: '2025-05', federalFunds: 5.33, treasury2Y: 4.87, treasury5Y: 4.48, treasury10Y: 4.50, treasury30Y: 4.65, sofr: 5.31, mortgage30Y: 7.06 },
  { date: '2025-06', federalFunds: 5.33, treasury2Y: 4.71, treasury5Y: 4.31, treasury10Y: 4.36, treasury30Y: 4.51, sofr: 5.31, mortgage30Y: 6.92 },
  { date: '2025-07', federalFunds: 5.33, treasury2Y: 4.38, treasury5Y: 4.07, treasury10Y: 4.17, treasury30Y: 4.40, sofr: 5.31, mortgage30Y: 6.77 },
  { date: '2025-08', federalFunds: 5.33, treasury2Y: 3.92, treasury5Y: 3.70, treasury10Y: 3.90, treasury30Y: 4.19, sofr: 5.31, mortgage30Y: 6.50 },
  { date: '2025-09', federalFunds: 5.00, treasury2Y: 3.55, treasury5Y: 3.42, treasury10Y: 3.73, treasury30Y: 4.08, sofr: 4.96, mortgage30Y: 6.18 },
  { date: '2025-10', federalFunds: 4.83, treasury2Y: 4.17, treasury5Y: 4.04, treasury10Y: 4.28, treasury30Y: 4.52, sofr: 4.81, mortgage30Y: 6.72 },
  { date: '2025-11', federalFunds: 4.58, treasury2Y: 4.24, treasury5Y: 4.12, treasury10Y: 4.35, treasury30Y: 4.54, sofr: 4.56, mortgage30Y: 6.88 },
  { date: '2025-12', federalFunds: 4.58, treasury2Y: 4.18, treasury5Y: 4.05, treasury10Y: 4.22, treasury30Y: 4.42, sofr: 4.56, mortgage30Y: 6.84 },
];

// Rate comparison data for spread analysis
export const mockRateSpreads = {
  treasurySpread2s10s: mockHistoricalRates.map(r => ({
    date: r.date,
    spread: r.treasury10Y - r.treasury2Y,
  })),
  mortgageSpread: mockHistoricalRates.map(r => ({
    date: r.date,
    spread: r.mortgage30Y - r.treasury10Y,
  })),
  fedFundsVsTreasury: mockHistoricalRates.map(r => ({
    date: r.date,
    fedFunds: r.federalFunds,
    treasury10Y: r.treasury10Y,
    spread: r.federalFunds - r.treasury10Y,
  })),
};

// Data Sources
export const mockDataSources: RateDataSource[] = [
  {
    id: 'treasury-gov',
    name: 'U.S. Treasury Department',
    url: 'https://home.treasury.gov/',
    description: 'Official source for Treasury yield curve data, auction results, and government securities information.',
    dataTypes: ['Treasury Yields', 'Yield Curve', 'Auction Results', 'Savings Bonds'],
    updateFrequency: 'Daily',
  },
  {
    id: 'fred',
    name: 'Federal Reserve Economic Data (FRED)',
    url: 'https://fred.stlouisfed.org/',
    description: 'Comprehensive economic database maintained by the Federal Reserve Bank of St. Louis. Provides historical and current rates.',
    dataTypes: ['Federal Funds Rate', 'Treasury Yields', 'SOFR', 'Economic Indicators'],
    updateFrequency: 'Daily',
  },
  {
    id: 'treasury-direct',
    name: 'TreasuryDirect',
    url: 'https://treasurydirect.gov/',
    description: 'Official source for purchasing and managing U.S. Treasury securities directly from the government.',
    dataTypes: ['Savings Bonds', 'Treasury Bills', 'Treasury Notes', 'Treasury Bonds'],
    updateFrequency: 'Real-time',
  },
  {
    id: 'bankrate',
    name: 'Bankrate',
    url: 'https://www.bankrate.com/',
    description: 'Leading source for current mortgage rates, personal loan rates, and consumer banking information.',
    dataTypes: ['Mortgage Rates', 'CD Rates', 'Savings Rates', 'Loan Rates'],
    updateFrequency: 'Daily',
  },
  {
    id: 'cme-sofr',
    name: 'CME Group - SOFR',
    url: 'https://www.cmegroup.com/markets/interest-rates/stirs/sofr.html',
    description: 'Official source for Term SOFR rates and SOFR futures trading information.',
    dataTypes: ['Term SOFR', 'SOFR Futures', 'SOFR Options'],
    updateFrequency: 'Real-time',
  },
  {
    id: 'ny-fed',
    name: 'Federal Reserve Bank of New York',
    url: 'https://www.newyorkfed.org/markets/reference-rates/sofr',
    description: 'Official administrator of SOFR (Secured Overnight Financing Rate) and related reference rates.',
    dataTypes: ['SOFR', 'EFFR', 'OBFR', 'TGCR'],
    updateFrequency: 'Daily',
  },
];

// Real Estate Lending Context
export const realEstateLendingContext = {
  typicalSpreads: {
    multifamilyPerm: { name: 'Multifamily Permanent', spreadOverTreasury: 1.50, benchmark: '10Y Treasury' },
    multifamilyBridge: { name: 'Multifamily Bridge', spreadOverSOFR: 3.00, benchmark: 'SOFR' },
    commercialPerm: { name: 'Commercial Permanent', spreadOverTreasury: 1.75, benchmark: '10Y Treasury' },
    construction: { name: 'Construction', spreadOverPrime: 0.50, benchmark: 'Prime Rate' },
  },
  currentIndicativeRates: {
    multifamilyPerm: 5.72, // 10Y Treasury 4.22 + 1.50
    multifamilyBridge: 8.34, // SOFR 5.34 + 3.00
    commercialPerm: 5.97, // 10Y Treasury 4.22 + 1.75
    construction: 9.00, // Prime 8.50 + 0.50
  },
};
