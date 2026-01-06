/**
 * API Hooks Index
 *
 * This module exports all React-Query based API hooks for the dashboard.
 * Each hook module includes:
 * - Query key factories for cache management
 * - Query hooks for fetching data
 * - Mutation hooks for creating/updating/deleting data
 * - Prefetch utilities for optimistic data loading
 */

// Property hooks
export {
  propertyKeys,
  useProperties,
  usePropertiesApi,
  useProperty,
  usePropertyApi,
  usePortfolioSummary,
  usePropertySummary,
  useCreateProperty,
  useUpdateProperty,
  useDeleteProperty,
  usePrefetchProperty,
  usePrefetchNextPage as usePrefetchNextPropertyPage,
  selectProperties,
} from './useProperties';

// Deal hooks
export {
  dealKeys,
  useDeals,
  useDeal,
  useDealPipeline,
  useDealsByStage,
  useDealStats,
  useCreateDeal,
  useUpdateDeal,
  useUpdateDealStage,
  useDeleteDeal,
  usePrefetchDeal,
  usePrefetchDealStage,
} from './useDeals';

// Extraction hooks
export {
  extractionKeys,
  useExtractionStatus,
  useExtractionRun,
  useExtractionHistory,
  useExtractedValues,
  usePropertyExtractions,
  useDealExtractions,
  useStartExtraction,
  useCancelExtraction,
  useValidateExtractedValue,
  useDeleteExtraction,
  useRetryExtraction,
  useIsPropertyExtracting,
  useIsDealExtracting,
} from './useExtraction';

// Re-export types for convenience
export type {
  PropertyFilters,
  PropertyApiResponse,
  PropertyListResponse,
  PropertyCreateInput,
  PropertyUpdateInput,
  DealFilters,
  DealApiResponse,
  DealListResponse,
  DealCreateInput,
  DealUpdateInput,
  DealStageUpdateInput,
  DealStageApi,
  ExtractionRun,
  ExtractionStatus,
  ExtractionSource,
  ExtractedValue,
  ExtractionHistoryFilters,
  ExtractionHistoryResponse,
  StartExtractionInput,
  ExtractionStatusResponse,
  PaginatedResponse,
  ApiError,
} from '@/types/api';
