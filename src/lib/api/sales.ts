/**
 * Sales Analysis API client functions
 */
import { apiClient } from './client';
import {
  salesResponseSchema,
  timeSeriesDataPointSchema,
  submarketComparisonRowSchema,
  buyerActivityRowSchema,
  distributionBucketSchema,
  dataQualityReportSchema,
  importStatusSchema,
  triggerImportResponseSchema,
  reminderStatusSchema,
} from './schemas/sales';
import type {
  SalesFilters,
  SalesResponse,
  TimeSeriesDataPoint,
  SubmarketComparisonRow,
  BuyerActivityRow,
  DistributionBucket,
  DataQualityReport,
  ImportStatus,
  ReminderStatus,
} from '@/features/sales-analysis/types';
import { z } from 'zod';

function filtersToParams(
  filters: SalesFilters
): Record<string, string | number | boolean | undefined> {
  return {
    search: filters.search,
    submarkets: filters.submarkets?.join(','),
    star_ratings: filters.starRatings?.join(','),
    min_units: filters.minUnits,
    max_units: filters.maxUnits,
    min_price: filters.minPrice,
    max_price: filters.maxPrice,
    date_from: filters.dateFrom,
    date_to: filters.dateTo,
    sort_by: filters.sortBy,
    sort_dir: filters.sortDir,
  };
}

/** Fetch paginated sales data */
export async function fetchSalesData(
  filters: SalesFilters,
  page: number,
  pageSize: number
): Promise<SalesResponse> {
  const raw = await apiClient.get<unknown>('/sales-analysis', {
    params: { ...filtersToParams(filters), page, page_size: pageSize },
  });
  return salesResponseSchema.parse(raw);
}

/** Fetch time-series analytics */
export async function fetchTimeSeriesAnalytics(
  filters: SalesFilters
): Promise<TimeSeriesDataPoint[]> {
  const raw = await apiClient.get<unknown>('/sales-analysis/analytics/time-series', {
    params: filtersToParams(filters),
  });
  return z.array(timeSeriesDataPointSchema).parse(raw);
}

/** Fetch submarket comparison data */
export async function fetchSubmarketComparison(
  filters: SalesFilters
): Promise<SubmarketComparisonRow[]> {
  const raw = await apiClient.get<unknown>('/sales-analysis/analytics/submarket-comparison', {
    params: filtersToParams(filters),
  });
  return z.array(submarketComparisonRowSchema).parse(raw);
}

/** Fetch buyer activity data */
export async function fetchBuyerActivity(
  filters: SalesFilters
): Promise<BuyerActivityRow[]> {
  const raw = await apiClient.get<unknown>('/sales-analysis/analytics/buyer-activity', {
    params: filtersToParams(filters),
  });
  return z.array(buyerActivityRowSchema).parse(raw);
}

/** Fetch distribution analysis data */
export async function fetchDistributions(
  filters: SalesFilters
): Promise<DistributionBucket[]> {
  const raw = await apiClient.get<unknown>('/sales-analysis/analytics/distributions', {
    params: filtersToParams(filters),
  });
  return z.array(distributionBucketSchema).parse(raw);
}

/** Fetch data quality report */
export async function fetchDataQuality(): Promise<DataQualityReport> {
  const raw = await apiClient.get<unknown>('/sales-analysis/analytics/data-quality');
  return dataQualityReportSchema.parse(raw);
}

/** Fetch import status (unimported files) */
export async function fetchImportStatus(): Promise<ImportStatus> {
  const raw = await apiClient.get<unknown>('/sales-analysis/import/status');
  return importStatusSchema.parse(raw);
}

/** Trigger import of new sales files */
export async function triggerImport(): Promise<{ success: boolean; message: string }> {
  const raw = await apiClient.post<unknown>('/sales-analysis/import');
  return triggerImportResponseSchema.parse(raw);
}

/** Dismiss the monthly reminder */
export async function dismissReminder(): Promise<void> {
  await apiClient.put<unknown>('/sales-analysis/reminder/dismiss');
}

/** Fetch reminder status */
export async function fetchReminderStatus(): Promise<ReminderStatus> {
  const raw = await apiClient.get<unknown>('/sales-analysis/reminder/status');
  return reminderStatusSchema.parse(raw);
}
