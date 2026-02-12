/**
 * Construction Pipeline API client functions
 */
import { apiClient } from './client';
import {
  projectRecordSchema,
  projectsResponseSchema,
  constructionFilterOptionsSchema,
  pipelineSummaryItemSchema,
  pipelineFunnelItemSchema,
  permitTrendPointSchema,
  employmentPointSchema,
  submarketPipelineItemSchema,
  classificationBreakdownItemSchema,
  deliveryTimelineItemSchema,
  constructionDataQualitySchema,
  constructionImportStatusSchema,
  triggerConstructionImportResponseSchema,
} from './schemas/construction';
import type {
  ConstructionFilters,
  ProjectRecord,
  ProjectsResponse,
  ConstructionFilterOptions,
  PipelineSummaryItem,
  PipelineFunnelItem,
  PermitTrendPoint,
  EmploymentPoint,
  SubmarketPipelineItem,
  ClassificationBreakdownItem,
  DeliveryTimelineItem,
  ConstructionDataQuality,
  ConstructionImportStatus,
} from '@/features/construction-pipeline/types';
import { z } from 'zod';

const BASE = '/construction-pipeline';

function filtersToParams(
  filters: ConstructionFilters
): Record<string, string | number | boolean | undefined> {
  return {
    search: filters.search,
    statuses: filters.statuses?.join(','),
    classifications: filters.classifications?.join(','),
    submarkets: filters.submarkets?.join(','),
    cities: filters.cities?.join(','),
    min_units: filters.minUnits,
    max_units: filters.maxUnits,
    min_year_built: filters.minYearBuilt,
    max_year_built: filters.maxYearBuilt,
    rent_type: filters.rentType,
    sort_by: filters.sortBy,
    sort_dir: filters.sortDir,
  };
}

/** Fetch paginated construction projects */
export async function fetchProjects(
  filters: ConstructionFilters,
  page: number,
  pageSize: number
): Promise<ProjectsResponse> {
  const raw = await apiClient.get<unknown>(BASE, {
    params: { ...filtersToParams(filters), page, page_size: pageSize },
  });
  return projectsResponseSchema.parse(raw);
}

/** Fetch all projects without pagination (for map view) */
export async function fetchAllProjects(
  filters: ConstructionFilters
): Promise<ProjectRecord[]> {
  const raw = await apiClient.get<unknown>(`${BASE}/all`, {
    params: filtersToParams(filters),
  });
  return z.array(projectRecordSchema).parse(raw);
}

/** Fetch filter options */
export async function fetchConstructionFilterOptions(): Promise<ConstructionFilterOptions> {
  const raw = await apiClient.get<unknown>(`${BASE}/filter-options`);
  return constructionFilterOptionsSchema.parse(raw);
}

/** Fetch pipeline summary (counts by status) */
export async function fetchPipelineSummary(
  filters: ConstructionFilters
): Promise<PipelineSummaryItem[]> {
  const raw = await apiClient.get<unknown>(`${BASE}/analytics/pipeline-summary`, {
    params: filtersToParams(filters),
  });
  return z.array(pipelineSummaryItemSchema).parse(raw);
}

/** Fetch pipeline funnel */
export async function fetchPipelineFunnel(
  filters: ConstructionFilters
): Promise<PipelineFunnelItem[]> {
  const raw = await apiClient.get<unknown>(`${BASE}/analytics/pipeline-funnel`, {
    params: filtersToParams(filters),
  });
  return z.array(pipelineFunnelItemSchema).parse(raw);
}

/** Fetch permit trends time-series */
export async function fetchPermitTrends(
  source?: string,
  months?: number
): Promise<PermitTrendPoint[]> {
  const raw = await apiClient.get<unknown>(`${BASE}/analytics/permit-trends`, {
    params: { source, months },
  });
  return z.array(permitTrendPointSchema).parse(raw);
}

/** Fetch employment overlay time-series */
export async function fetchEmploymentOverlay(
  months?: number
): Promise<EmploymentPoint[]> {
  const raw = await apiClient.get<unknown>(`${BASE}/analytics/employment-overlay`, {
    params: { months },
  });
  return z.array(employmentPointSchema).parse(raw);
}

/** Fetch submarket pipeline breakdown */
export async function fetchSubmarketPipeline(
  filters: ConstructionFilters
): Promise<SubmarketPipelineItem[]> {
  const raw = await apiClient.get<unknown>(`${BASE}/analytics/submarket-pipeline`, {
    params: filtersToParams(filters),
  });
  return z.array(submarketPipelineItemSchema).parse(raw);
}

/** Fetch classification breakdown */
export async function fetchClassificationBreakdown(
  filters: ConstructionFilters
): Promise<ClassificationBreakdownItem[]> {
  const raw = await apiClient.get<unknown>(`${BASE}/analytics/classification-breakdown`, {
    params: filtersToParams(filters),
  });
  return z.array(classificationBreakdownItemSchema).parse(raw);
}

/** Fetch delivery timeline (quarterly) */
export async function fetchDeliveryTimeline(
  filters: ConstructionFilters
): Promise<DeliveryTimelineItem[]> {
  const raw = await apiClient.get<unknown>(`${BASE}/analytics/delivery-timeline`, {
    params: filtersToParams(filters),
  });
  return z.array(deliveryTimelineItemSchema).parse(raw);
}

/** Fetch data quality report */
export async function fetchConstructionDataQuality(): Promise<ConstructionDataQuality> {
  const raw = await apiClient.get<unknown>(`${BASE}/analytics/data-quality`);
  return constructionDataQualitySchema.parse(raw);
}

/** Fetch import status */
export async function fetchConstructionImportStatus(): Promise<ConstructionImportStatus> {
  const raw = await apiClient.get<unknown>(`${BASE}/import/status`);
  return constructionImportStatusSchema.parse(raw);
}

/** Trigger CoStar construction file import */
export async function triggerConstructionImport(): Promise<{ success: boolean; message: string }> {
  const raw = await apiClient.post<unknown>(`${BASE}/import`);
  return triggerConstructionImportResponseSchema.parse(raw);
}
