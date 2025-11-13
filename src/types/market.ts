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

export interface EconomicIndicator {
  id: string;
  indicator: 'population' | 'employment' | 'income' | 'permits';
  date: Date;
  value: number;
  change: number;
  region: 'Phoenix MSA' | 'Arizona' | 'United States';
}
