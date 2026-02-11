/**
 * Zod schemas for construction pipeline API responses.
 *
 * Validates raw JSON from /construction-pipeline/* endpoints
 * and transforms snake_case → camelCase.
 */
import { z } from 'zod';

// ---------- Project Record Schema ----------

export const projectRecordSchema = z
  .object({
    id: z.number(),
    project_name: z.string().nullable(),
    project_address: z.string().nullable(),
    city: z.string().nullable(),
    submarket_cluster: z.string().nullable(),
    pipeline_status: z.string().nullable(),
    primary_classification: z.string().nullable(),
    number_of_units: z.number().nullable(),
    number_of_stories: z.number().nullable(),
    year_built: z.number().nullable(),
    developer_name: z.string().nullable(),
    owner_name: z.string().nullable(),
    latitude: z.number().nullable(),
    longitude: z.number().nullable(),
    building_sf: z.number().nullable(),
    avg_unit_sf: z.number().nullable(),
    star_rating: z.string().nullable(),
    rent_type: z.string().nullable(),
    vacancy_pct: z.number().nullable(),
    estimated_delivery_date: z.string().nullable(),
    construction_begin: z.string().nullable(),
    for_sale_price: z.number().nullable(),
    source_type: z.string().nullable(),
  })
  .transform((r) => ({
    id: r.id,
    projectName: r.project_name,
    projectAddress: r.project_address,
    city: r.city,
    submarketCluster: r.submarket_cluster,
    pipelineStatus: r.pipeline_status,
    primaryClassification: r.primary_classification,
    numberOfUnits: r.number_of_units,
    numberOfStories: r.number_of_stories,
    yearBuilt: r.year_built,
    developerName: r.developer_name,
    ownerName: r.owner_name,
    latitude: r.latitude,
    longitude: r.longitude,
    buildingSf: r.building_sf,
    avgUnitSf: r.avg_unit_sf,
    starRating: r.star_rating,
    rentType: r.rent_type,
    vacancyPct: r.vacancy_pct,
    estimatedDeliveryDate: r.estimated_delivery_date,
    constructionBegin: r.construction_begin,
    forSalePrice: r.for_sale_price,
    sourceType: r.source_type,
  }));

// ---------- Paginated Response ----------

export const projectsResponseSchema = z
  .object({
    data: z.array(projectRecordSchema),
    total: z.number(),
    page: z.number(),
    page_size: z.number(),
    total_pages: z.number(),
  })
  .transform((r) => ({
    data: r.data,
    total: r.total,
    page: r.page,
    pageSize: r.page_size,
    totalPages: r.total_pages,
  }));

// ---------- Filter Options ----------

export const constructionFilterOptionsSchema = z
  .object({
    submarkets: z.array(z.string()),
    cities: z.array(z.string()),
    statuses: z.array(z.string()),
    classifications: z.array(z.string()),
    rent_types: z.array(z.string()),
  })
  .transform((r) => ({
    submarkets: r.submarkets,
    cities: r.cities,
    statuses: r.statuses,
    classifications: r.classifications,
    rentTypes: r.rent_types,
  }));

// ---------- Analytics Schemas ----------

export const pipelineSummaryItemSchema = z
  .object({
    status: z.string(),
    project_count: z.number(),
    total_units: z.number(),
  })
  .transform((r) => ({
    status: r.status,
    projectCount: r.project_count,
    totalUnits: r.total_units,
  }));

export const pipelineFunnelItemSchema = z
  .object({
    status: z.string(),
    project_count: z.number(),
    total_units: z.number(),
    cumulative_units: z.number(),
  })
  .transform((r) => ({
    status: r.status,
    projectCount: r.project_count,
    totalUnits: r.total_units,
    cumulativeUnits: r.cumulative_units,
  }));

export const permitTrendPointSchema = z
  .object({
    period: z.string(),
    source: z.string(),
    series_id: z.string(),
    value: z.number(),
  })
  .transform((r) => ({
    period: r.period,
    source: r.source,
    seriesId: r.series_id,
    value: r.value,
  }));

export const employmentPointSchema = z
  .object({
    period: z.string(),
    series_id: z.string(),
    value: z.number(),
  })
  .transform((r) => ({
    period: r.period,
    seriesId: r.series_id,
    value: r.value,
  }));

export const submarketPipelineItemSchema = z
  .object({
    submarket: z.string(),
    total_projects: z.number(),
    total_units: z.number(),
    proposed: z.number(),
    under_construction: z.number(),
    delivered: z.number(),
  })
  .transform((r) => ({
    submarket: r.submarket,
    totalProjects: r.total_projects,
    totalUnits: r.total_units,
    proposed: r.proposed,
    underConstruction: r.under_construction,
    delivered: r.delivered,
  }));

export const classificationBreakdownItemSchema = z
  .object({
    classification: z.string(),
    project_count: z.number(),
    total_units: z.number(),
  })
  .transform((r) => ({
    classification: r.classification,
    projectCount: r.project_count,
    totalUnits: r.total_units,
  }));

export const deliveryTimelineItemSchema = z
  .object({
    quarter: z.string(),
    total_units: z.number(),
    project_count: z.number(),
  })
  .transform((r) => ({
    quarter: r.quarter,
    totalUnits: r.total_units,
    projectCount: r.project_count,
  }));

export const constructionDataQualitySchema = z
  .object({
    total_projects: z.number(),
    projects_by_source: z.record(z.string(), z.number()),
    source_logs: z.array(z.record(z.string(), z.unknown())),
    null_rates: z.record(z.string(), z.number()),
    permit_data_count: z.number(),
    employment_data_count: z.number(),
  })
  .transform((r) => ({
    totalProjects: r.total_projects,
    projectsBySource: r.projects_by_source,
    sourceLogs: r.source_logs,
    nullRates: r.null_rates,
    permitDataCount: r.permit_data_count,
    employmentDataCount: r.employment_data_count,
  }));

export const constructionImportStatusSchema = z
  .object({
    unimported_files: z.array(z.string()),
    last_imported_file: z.string().nullable(),
    last_import_date: z.string().nullable(),
    total_projects: z.number(),
  })
  .transform((r) => ({
    unimportedFiles: r.unimported_files,
    lastImportedFile: r.last_imported_file,
    lastImportDate: r.last_import_date,
    totalProjects: r.total_projects,
  }));

export const triggerConstructionImportResponseSchema = z.object({
  success: z.boolean(),
  message: z.string(),
});
