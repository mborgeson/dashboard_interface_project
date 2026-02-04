/**
 * Interest Rates API Service
 * Fetches interest rate data from the backend API (which handles FRED/DB fallback).
 * No longer calls FRED directly from the frontend.
 */

import { API_URL } from "@/lib/config";
import type {
  KeyRate,
  YieldCurvePoint,
  HistoricalRate,
} from "@/data/mockInterestRates";

/**
 * Fetch current key rates from backend
 */
export async function fetchKeyRates(): Promise<KeyRate[] | null> {
  try {
    const response = await fetch(`${API_URL}/interest-rates/current`);
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    const data = await response.json();

    // Map snake_case backend response to camelCase frontend types
    return (data.key_rates || []).map(
      (r: Record<string, unknown>): KeyRate => ({
        id: r.id as string,
        name: r.name as string,
        shortName: r.short_name as string,
        currentValue: r.current_value as number,
        previousValue: r.previous_value as number,
        change: r.change as number,
        changePercent: r.change_percent as number,
        asOfDate: r.as_of_date as string,
        category: r.category as KeyRate["category"],
        description: r.description as string,
      })
    );
  } catch (error) {
    console.error("Error fetching key rates:", error);
    return null;
  }
}

/**
 * Fetch yield curve data from backend
 */
export async function fetchYieldCurve(): Promise<YieldCurvePoint[] | null> {
  try {
    const response = await fetch(`${API_URL}/interest-rates/yield-curve`);
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    const data = await response.json();

    return (data.yield_curve || []).map(
      (p: Record<string, unknown>): YieldCurvePoint => ({
        maturity: p.maturity as string,
        yield: (p.yield ?? p.yield_value) as number,
        previousYield: p.previous_yield as number,
        maturityMonths: p.maturity_months as number,
      })
    );
  } catch (error) {
    console.error("Error fetching yield curve:", error);
    return null;
  }
}

/**
 * Fetch historical rate data from backend
 */
export async function fetchHistoricalRates(): Promise<HistoricalRate[] | null> {
  try {
    const response = await fetch(
      `${API_URL}/interest-rates/historical?months=12`
    );
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    const data = await response.json();

    return (data.rates || []).map(
      (r: Record<string, unknown>): HistoricalRate => ({
        date: r.date as string,
        federalFunds: r.federal_funds as number,
        treasury2Y: r.treasury_2y as number,
        treasury5Y: r.treasury_5y as number,
        treasury10Y: r.treasury_10y as number,
        treasury30Y: r.treasury_30y as number,
        sofr: r.sofr as number,
        mortgage30Y: r.mortgage_30y as number,
      })
    );
  } catch (error) {
    console.error("Error fetching historical rates:", error);
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
 * Check if API is configured — always true since backend handles fallback
 */
export function isApiConfigured(): boolean {
  return true;
}
