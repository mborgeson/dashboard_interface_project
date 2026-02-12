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
}
