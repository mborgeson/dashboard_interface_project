/**
 * Zod schemas for sales analysis API responses
 *
 * Validates raw JSON from /sales/* endpoints and transforms
 * snake_case → camelCase where needed.
 */
import { z } from 'zod';

// ---------- Sale Record Schema ----------

export const saleRecordSchema = z
  .object({
    id: z.number(),
    property_name: z.string().nullable(),
    property_address: z.string().nullable(),
    property_city: z.string().nullable(),
    submarket_cluster: z.string().nullable(),
    seller_true_company: z.string().nullable(),
    star_rating: z.string().nullable(),
    year_built: z.number().nullable(),
    number_of_units: z.number().nullable(),
    avg_unit_sf: z.number().nullable(),
    sale_date: z.string().nullable(),
    sale_price: z.number().nullable(),
    price_per_unit: z.number().nullable(),
    buyer_true_company: z.string().nullable(),
    latitude: z.number().nullable(),
    longitude: z.number().nullable(),
    nrsf: z.number().nullable(),
    price_per_nrsf: z.number().nullable(),
  })
  .transform((s) => ({
    id: s.id,
    propertyName: s.property_name,
    propertyAddress: s.property_address,
    propertyCity: s.property_city,
    submarketCluster: s.submarket_cluster,
    sellerTrueCompany: s.seller_true_company,
    starRating: s.star_rating,
    yearBuilt: s.year_built,
    numberOfUnits: s.number_of_units,
    avgUnitSf: s.avg_unit_sf,
    saleDate: s.sale_date,
    salePrice: s.sale_price,
    pricePerUnit: s.price_per_unit,
    buyerTrueCompany: s.buyer_true_company,
    latitude: s.latitude,
    longitude: s.longitude,
    nrsf: s.nrsf,
    pricePerNrsf: s.price_per_nrsf,
  }));

// ---------- Paginated Response Schema ----------

export const salesResponseSchema = z
  .object({
    data: z.array(saleRecordSchema),
    total: z.number(),
    page: z.number(),
    page_size: z.number(),
    total_pages: z.number(),
  })
  .transform((s) => ({
    data: s.data,
    total: s.total,
    page: s.page,
    pageSize: s.page_size,
    totalPages: s.total_pages,
  }));

// ---------- Analytics Schemas ----------

export const timeSeriesDataPointSchema = z
  .object({
    period: z.string(),
    count: z.number(),
    total_volume: z.number(),
    avg_price_per_unit: z.number().nullable(),
  })
  .transform((s) => ({
    period: s.period,
    count: s.count,
    totalVolume: s.total_volume,
    avgPricePerUnit: s.avg_price_per_unit,
  }));

export const submarketComparisonRowSchema = z
  .object({
    submarket: z.string(),
    year: z.number(),
    avg_price_per_unit: z.number().nullable(),
    sales_count: z.number(),
    total_volume: z.number(),
  })
  .transform((s) => ({
    submarket: s.submarket,
    year: s.year,
    avgPricePerUnit: s.avg_price_per_unit,
    salesCount: s.sales_count,
    totalVolume: s.total_volume,
  }));

export const buyerActivityRowSchema = z
  .object({
    buyer: z.string(),
    transaction_count: z.number(),
    total_volume: z.number(),
    submarkets: z.array(z.string()),
    first_purchase: z.string().nullable(),
    last_purchase: z.string().nullable(),
  })
  .transform((s) => ({
    buyer: s.buyer,
    transactionCount: s.transaction_count,
    totalVolume: s.total_volume,
    submarkets: s.submarkets,
    firstPurchase: s.first_purchase,
    lastPurchase: s.last_purchase,
  }));

export const distributionBucketSchema = z
  .object({
    label: z.string(),
    count: z.number(),
    avg_price_per_unit: z.number().nullable(),
  })
  .transform((s) => ({
    label: s.label,
    count: s.count,
    avgPricePerUnit: s.avg_price_per_unit,
  }));

export const dataQualityReportSchema = z
  .object({
    total_records: z.number(),
    records_by_file: z.record(z.string(), z.number()),
    null_rates: z.record(z.string(), z.number()),
    flagged_outliers: z.record(z.string(), z.number()),
  })
  .transform((s) => ({
    totalRecords: s.total_records,
    recordsByFile: s.records_by_file,
    nullRates: s.null_rates,
    flaggedOutliers: s.flagged_outliers,
  }));

export const importStatusSchema = z
  .object({
    unimported_files: z.array(z.string()),
    last_imported_file: z.string().nullable(),
    last_import_date: z.string().nullable(),
  })
  .transform((s) => ({
    unimportedFiles: s.unimported_files,
    lastImportedFile: s.last_imported_file,
    lastImportDate: s.last_import_date,
  }));

export const reminderStatusSchema = z
  .object({
    show_reminder: z.boolean(),
    last_imported_file_name: z.string().nullable(),
    last_imported_file_date: z.string().nullable(),
  })
  .transform((s) => ({
    showReminder: s.show_reminder,
    lastImportedFileName: s.last_imported_file_name,
    lastImportedFileDate: s.last_imported_file_date,
  }));

export const triggerImportResponseSchema = z.object({
  success: z.boolean(),
  message: z.string(),
});

export const filterOptionsSchema = z.object({
  submarkets: z.array(z.string()),
});
