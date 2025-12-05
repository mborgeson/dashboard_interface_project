export interface SubmarketMetrics {
  name: string;
  avgRent: number;
  rentGrowth: number;
  occupancy: number;
  capRate: number;
  inventory: number;
  absorption: number;
}

export interface MarketTrend {
  month: string;
  rentGrowth: number;
  occupancy: number;
  capRate: number;
}

export interface EconomicIndicator {
  indicator: string;
  value: number;
  yoyChange: number;
  unit: string;
}

export interface MSAOverview {
  population: number;
  employment: number;
  gdp: number;
  populationGrowth: number;
  employmentGrowth: number;
  gdpGrowth: number;
  lastUpdated: string;
}

export interface MonthlyMarketData {
  month: string;
  rentGrowth: number;
  occupancy: number;
  capRate: number;
  employment: number;
  population: number;
}

export interface MarketData {
  id: string;
  submarket: string;
  date: Date;
  metrics: {
    totalUnits: number;
    vacancy: number;
    averageRent: number;
    rentGrowthYoY: number;
    capRateRange: [number, number];
    newSupply: number;
    absorption: number;
  };
}
