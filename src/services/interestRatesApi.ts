/**
 * Interest Rates API Service
 * Fetches real-time interest rate data from public APIs
 */

import type { KeyRate, YieldCurvePoint, HistoricalRate } from '@/data/mockInterestRates';

// FRED API (Federal Reserve Economic Data) - Free, requires API key
// Get your free API key at: https://fred.stlouisfed.org/docs/api/api_key.html
const FRED_API_KEY = import.meta.env.VITE_FRED_API_KEY || '';
// Use Vite proxy in development to avoid CORS issues
// Proxy rewrites /api/fred -> https://api.stlouisfed.org (removes /api/fred prefix)
const FRED_BASE_URL = import.meta.env.DEV
  ? '/api/fred/fred/series/observations'
  : 'https://api.stlouisfed.org/fred/series/observations';

// Debug logging for API configuration
console.log('[InterestRatesApi] FRED_API_KEY configured:', !!FRED_API_KEY, 'key length:', FRED_API_KEY.length);
console.log('[InterestRatesApi] FRED_BASE_URL:', FRED_BASE_URL);
console.log('[InterestRatesApi] DEV mode:', import.meta.env.DEV);

// Treasury.gov API - Free, no API key required
const TREASURY_BASE_URL = 'https://api.fiscaldata.treasury.gov/services/api/fiscal_service';

// Series IDs for FRED API
const FRED_SERIES = {
  federalFunds: 'FEDFUNDS',      // Federal Funds Effective Rate
  prime: 'DPRIME',               // Bank Prime Loan Rate
  treasury1M: 'DGS1MO',          // 1-Month Treasury
  treasury3M: 'DGS3MO',          // 3-Month Treasury
  treasury6M: 'DGS6MO',          // 6-Month Treasury
  treasury1Y: 'DGS1',            // 1-Year Treasury
  treasury2Y: 'DGS2',            // 2-Year Treasury
  treasury3Y: 'DGS3',            // 3-Year Treasury
  treasury5Y: 'DGS5',            // 5-Year Treasury
  treasury7Y: 'DGS7',            // 7-Year Treasury
  treasury10Y: 'DGS10',          // 10-Year Treasury
  treasury20Y: 'DGS20',          // 20-Year Treasury
  treasury30Y: 'DGS30',          // 30-Year Treasury
  sofr: 'SOFR',                  // Secured Overnight Financing Rate
  mortgage30Y: 'MORTGAGE30US',   // 30-Year Fixed Rate Mortgage Average
};

interface FredObservation {
  date: string;
  value: string;
}

interface FredResponse {
  observations: FredObservation[];
}

interface TreasuryYieldRecord {
  record_date: string;
  security_desc: string;
  avg_interest_rate_amt: string;
}

interface TreasuryResponse {
  data: TreasuryYieldRecord[];
}

/**
 * Fetch a single series from FRED API
 */
async function fetchFredSeries(
  seriesId: string,
  limit: number = 2
): Promise<FredObservation[]> {
  if (!FRED_API_KEY) {
    console.warn('FRED API key not configured. Using mock data.');
    return [];
  }

  const params = new URLSearchParams({
    series_id: seriesId,
    api_key: FRED_API_KEY,
    file_type: 'json',
    sort_order: 'desc',
    limit: limit.toString(),
  });

  try {
    const response = await fetch(`${FRED_BASE_URL}?${params}`);
    if (!response.ok) {
      throw new Error(`FRED API error: ${response.status}`);
    }
    const data: FredResponse = await response.json();
    return data.observations || [];
  } catch (error) {
    console.error(`Error fetching FRED series ${seriesId}:`, error);
    return [];
  }
}

/**
 * Fetch Treasury yield curve data from Treasury.gov API
 */
async function fetchTreasuryYields(): Promise<TreasuryYieldRecord[]> {
  const today = new Date();
  const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

  const params = new URLSearchParams({
    'filter': `record_date:gte:${thirtyDaysAgo.toISOString().split('T')[0]}`,
    'sort': '-record_date',
    'page[size]': '100',
  });

  try {
    const response = await fetch(
      `${TREASURY_BASE_URL}/v2/accounting/od/avg_interest_rates?${params}`
    );
    if (!response.ok) {
      throw new Error(`Treasury API error: ${response.status}`);
    }
    const data: TreasuryResponse = await response.json();
    return data.data || [];
  } catch (error) {
    console.error('Error fetching Treasury yields:', error);
    return [];
  }
}

/**
 * Fetch current key rates from FRED
 */
export async function fetchKeyRates(): Promise<KeyRate[] | null> {
  if (!FRED_API_KEY) {
    return null; // Will fall back to mock data
  }

  const seriesConfig = [
    { id: 'fed-funds', seriesId: FRED_SERIES.federalFunds, name: 'Federal Funds Rate', shortName: 'Fed Funds', category: 'federal' as const },
    { id: 'prime-rate', seriesId: FRED_SERIES.prime, name: 'Prime Rate', shortName: 'Prime', category: 'federal' as const },
    { id: 'treasury-2y', seriesId: FRED_SERIES.treasury2Y, name: '2-Year Treasury Yield', shortName: '2Y Treasury', category: 'treasury' as const },
    { id: 'treasury-5y', seriesId: FRED_SERIES.treasury5Y, name: '5-Year Treasury Yield', shortName: '5Y Treasury', category: 'treasury' as const },
    { id: 'treasury-7y', seriesId: FRED_SERIES.treasury7Y, name: '7-Year Treasury Yield', shortName: '7Y Treasury', category: 'treasury' as const },
    { id: 'treasury-10y', seriesId: FRED_SERIES.treasury10Y, name: '10-Year Treasury Yield', shortName: '10Y Treasury', category: 'treasury' as const },
    { id: 'sofr-1m', seriesId: FRED_SERIES.sofr, name: 'SOFR Rate', shortName: 'SOFR', category: 'sofr' as const },
    { id: 'mortgage-30y', seriesId: FRED_SERIES.mortgage30Y, name: '30-Year Fixed Mortgage Rate', shortName: '30Y Mortgage', category: 'mortgage' as const },
  ];

  try {
    const results = await Promise.all(
      seriesConfig.map(async (config) => {
        const observations = await fetchFredSeries(config.seriesId, 2);
        if (observations.length === 0) return null;

        const currentObs = observations[0];
        const previousObs = observations[1] || observations[0];

        const currentValue = parseFloat(currentObs.value) || 0;
        const previousValue = parseFloat(previousObs.value) || currentValue;
        const change = currentValue - previousValue;
        const changePercent = previousValue !== 0 ? (change / previousValue) * 100 : 0;

        return {
          id: config.id,
          name: config.name,
          shortName: config.shortName,
          currentValue,
          previousValue,
          change,
          changePercent,
          asOfDate: currentObs.date,
          category: config.category,
          description: `Live data from FRED API`,
        } as KeyRate;
      })
    );

    const validResults = results.filter((r): r is KeyRate => r !== null);
    return validResults.length > 0 ? validResults : null;
  } catch (error) {
    console.error('Error fetching key rates:', error);
    return null;
  }
}

/**
 * Fetch yield curve data from FRED
 */
export async function fetchYieldCurve(): Promise<YieldCurvePoint[] | null> {
  if (!FRED_API_KEY) {
    return null;
  }

  const maturities = [
    { maturity: '1M', seriesId: FRED_SERIES.treasury1M, months: 1 },
    { maturity: '3M', seriesId: FRED_SERIES.treasury3M, months: 3 },
    { maturity: '6M', seriesId: FRED_SERIES.treasury6M, months: 6 },
    { maturity: '1Y', seriesId: FRED_SERIES.treasury1Y, months: 12 },
    { maturity: '2Y', seriesId: FRED_SERIES.treasury2Y, months: 24 },
    { maturity: '3Y', seriesId: FRED_SERIES.treasury3Y, months: 36 },
    { maturity: '5Y', seriesId: FRED_SERIES.treasury5Y, months: 60 },
    { maturity: '7Y', seriesId: FRED_SERIES.treasury7Y, months: 84 },
    { maturity: '10Y', seriesId: FRED_SERIES.treasury10Y, months: 120 },
    { maturity: '20Y', seriesId: FRED_SERIES.treasury20Y, months: 240 },
    { maturity: '30Y', seriesId: FRED_SERIES.treasury30Y, months: 360 },
  ];

  try {
    const results = await Promise.all(
      maturities.map(async (m) => {
        const observations = await fetchFredSeries(m.seriesId, 2);
        if (observations.length === 0) return null;

        const currentYield = parseFloat(observations[0].value) || 0;
        const previousYield = parseFloat(observations[1]?.value || observations[0].value) || currentYield;

        return {
          maturity: m.maturity,
          yield: currentYield,
          previousYield,
          maturityMonths: m.months,
        } as YieldCurvePoint;
      })
    );

    const validResults = results.filter((r): r is YieldCurvePoint => r !== null);
    return validResults.length > 0 ? validResults : null;
  } catch (error) {
    console.error('Error fetching yield curve:', error);
    return null;
  }
}

/**
 * Fetch historical rate data from FRED (last 12 months)
 */
export async function fetchHistoricalRates(): Promise<HistoricalRate[] | null> {
  if (!FRED_API_KEY) {
    return null;
  }

  const today = new Date();
  const oneYearAgo = new Date(today.getFullYear() - 1, today.getMonth(), 1);

  const params = new URLSearchParams({
    api_key: FRED_API_KEY,
    file_type: 'json',
    observation_start: oneYearAgo.toISOString().split('T')[0],
    frequency: 'm', // Monthly
    aggregation_method: 'avg',
  });

  const series = [
    { key: 'federalFunds', seriesId: FRED_SERIES.federalFunds },
    { key: 'treasury2Y', seriesId: FRED_SERIES.treasury2Y },
    { key: 'treasury5Y', seriesId: FRED_SERIES.treasury5Y },
    { key: 'treasury10Y', seriesId: FRED_SERIES.treasury10Y },
    { key: 'treasury30Y', seriesId: FRED_SERIES.treasury30Y },
    { key: 'sofr', seriesId: FRED_SERIES.sofr },
    { key: 'mortgage30Y', seriesId: FRED_SERIES.mortgage30Y },
  ];

  try {
    const seriesData = await Promise.all(
      series.map(async (s) => {
        const response = await fetch(
          `${FRED_BASE_URL}?series_id=${s.seriesId}&${params}`
        );
        if (!response.ok) return { key: s.key, data: [] };
        const json: FredResponse = await response.json();
        return { key: s.key, data: json.observations || [] };
      })
    );

    // Combine all series by date
    const dateMap = new Map<string, Partial<HistoricalRate>>();

    for (const { key, data } of seriesData) {
      for (const obs of data) {
        const dateKey = obs.date.substring(0, 7); // YYYY-MM format
        if (!dateMap.has(dateKey)) {
          dateMap.set(dateKey, { date: dateKey });
        }
        const record = dateMap.get(dateKey)!;
        const value = parseFloat(obs.value);
        if (!isNaN(value)) {
          (record as Record<string, unknown>)[key] = value;
        }
      }
    }

    const results = Array.from(dateMap.values())
      .filter(r =>
        r.federalFunds !== undefined &&
        r.treasury2Y !== undefined &&
        r.treasury10Y !== undefined
      )
      .sort((a, b) => (a.date || '').localeCompare(b.date || '')) as HistoricalRate[];

    return results.length > 0 ? results : null;
  } catch (error) {
    console.error('Error fetching historical rates:', error);
    return null;
  }
}

/**
 * Get the last update timestamp
 */
export function getLastUpdateTime(): string {
  return new Date().toISOString();
}

/**
 * Check if FRED API is configured
 */
export function isApiConfigured(): boolean {
  return !!FRED_API_KEY;
}
