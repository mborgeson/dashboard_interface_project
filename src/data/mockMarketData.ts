import type {
  SubmarketMetrics,
  MarketTrend,
  EconomicIndicator,
  MSAOverview,
  MonthlyMarketData
} from '@/types/market';

// Phoenix MSA Overview
export const phoenixMSAOverview: MSAOverview = {
  population: 5100000,
  employment: 2450000,
  gdp: 263000000000,
  populationGrowth: 0.023,
  employmentGrowth: 0.032,
  gdpGrowth: 0.041,
  lastUpdated: '2024-12-04',
};

// Economic Indicators
export const economicIndicators: EconomicIndicator[] = [
  {
    indicator: 'Unemployment Rate',
    value: 3.6,
    yoyChange: -0.4,
    unit: '%',
  },
  {
    indicator: 'Job Growth Rate',
    value: 3.2,
    yoyChange: 0.8,
    unit: '%',
  },
  {
    indicator: 'Median Household Income',
    value: 72500,
    yoyChange: 0.045,
    unit: '$',
  },
  {
    indicator: 'Population Growth',
    value: 2.3,
    yoyChange: 0.2,
    unit: '%',
  },
];

// Market Trends (12 months)
export const marketTrends: MarketTrend[] = [
  { month: 'Jan', rentGrowth: 0.048, occupancy: 0.945, capRate: 0.052 },
  { month: 'Feb', rentGrowth: 0.051, occupancy: 0.947, capRate: 0.051 },
  { month: 'Mar', rentGrowth: 0.053, occupancy: 0.949, capRate: 0.051 },
  { month: 'Apr', rentGrowth: 0.055, occupancy: 0.951, capRate: 0.050 },
  { month: 'May', rentGrowth: 0.057, occupancy: 0.953, capRate: 0.050 },
  { month: 'Jun', rentGrowth: 0.059, occupancy: 0.954, capRate: 0.049 },
  { month: 'Jul', rentGrowth: 0.061, occupancy: 0.956, capRate: 0.049 },
  { month: 'Aug', rentGrowth: 0.062, occupancy: 0.957, capRate: 0.048 },
  { month: 'Sep', rentGrowth: 0.063, occupancy: 0.958, capRate: 0.048 },
  { month: 'Oct', rentGrowth: 0.064, occupancy: 0.959, capRate: 0.047 },
  { month: 'Nov', rentGrowth: 0.065, occupancy: 0.960, capRate: 0.047 },
  { month: 'Dec', rentGrowth: 0.066, occupancy: 0.961, capRate: 0.046 },
];

// Monthly Market Data (for charts)
export const monthlyMarketData: MonthlyMarketData[] = [
  { month: 'Jan', rentGrowth: 0.048, occupancy: 0.945, capRate: 0.052, employment: 2380000, population: 5020000 },
  { month: 'Feb', rentGrowth: 0.051, occupancy: 0.947, capRate: 0.051, employment: 2395000, population: 5035000 },
  { month: 'Mar', rentGrowth: 0.053, occupancy: 0.949, capRate: 0.051, employment: 2405000, population: 5045000 },
  { month: 'Apr', rentGrowth: 0.055, occupancy: 0.951, capRate: 0.050, employment: 2415000, population: 5055000 },
  { month: 'May', rentGrowth: 0.057, occupancy: 0.953, capRate: 0.050, employment: 2425000, population: 5065000 },
  { month: 'Jun', rentGrowth: 0.059, occupancy: 0.954, capRate: 0.049, employment: 2430000, population: 5070000 },
  { month: 'Jul', rentGrowth: 0.061, occupancy: 0.956, capRate: 0.049, employment: 2435000, population: 5075000 },
  { month: 'Aug', rentGrowth: 0.062, occupancy: 0.957, capRate: 0.048, employment: 2440000, population: 5080000 },
  { month: 'Sep', rentGrowth: 0.063, occupancy: 0.958, capRate: 0.048, employment: 2445000, population: 5085000 },
  { month: 'Oct', rentGrowth: 0.064, occupancy: 0.959, capRate: 0.047, employment: 2450000, population: 5090000 },
  { month: 'Nov', rentGrowth: 0.065, occupancy: 0.960, capRate: 0.047, employment: 2455000, population: 5095000 },
  { month: 'Dec', rentGrowth: 0.066, occupancy: 0.961, capRate: 0.046, employment: 2460000, population: 5100000 },
];

// Submarket Metrics
export const submarketMetrics: SubmarketMetrics[] = [
  {
    name: 'Downtown Phoenix',
    avgRent: 1850,
    rentGrowth: 0.068,
    occupancy: 0.965,
    capRate: 0.045,
    inventory: 18500,
    absorption: 245,
  },
  {
    name: 'Scottsdale',
    avgRent: 2150,
    rentGrowth: 0.072,
    occupancy: 0.970,
    capRate: 0.042,
    inventory: 15200,
    absorption: 198,
  },
  {
    name: 'Tempe',
    avgRent: 1650,
    rentGrowth: 0.065,
    occupancy: 0.960,
    capRate: 0.048,
    inventory: 21000,
    absorption: 285,
  },
  {
    name: 'Mesa',
    avgRent: 1450,
    rentGrowth: 0.058,
    occupancy: 0.952,
    capRate: 0.051,
    inventory: 24500,
    absorption: 312,
  },
  {
    name: 'Chandler',
    avgRent: 1750,
    rentGrowth: 0.070,
    occupancy: 0.963,
    capRate: 0.046,
    inventory: 19800,
    absorption: 268,
  },
  {
    name: 'Gilbert',
    avgRent: 1800,
    rentGrowth: 0.069,
    occupancy: 0.964,
    capRate: 0.047,
    inventory: 16700,
    absorption: 221,
  },
];

// Sparkline data for economic indicators (last 6 months)
export const unemploymentSparkline = [4.2, 4.0, 3.9, 3.8, 3.7, 3.6];
export const jobGrowthSparkline = [2.1, 2.4, 2.6, 2.8, 3.0, 3.2];
export const incomeGrowthSparkline = [3.8, 4.0, 4.1, 4.2, 4.3, 4.5];
export const populationGrowthSparkline = [2.0, 2.1, 2.1, 2.2, 2.2, 2.3];
