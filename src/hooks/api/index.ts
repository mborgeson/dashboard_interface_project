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
  useDealsWithMockFallback,
  useDealsWithMockFallback as useDeals, // Alias for backwards compatibility
  useDealsApi,
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

// Transaction hooks
export {
  transactionKeys,
  useTransactionsWithMockFallback,
  useTransactionsApi,
  useTransaction,
  useTransactionsByProperty,
  useTransactionsByType,
  useTransactionSummary,
  useCreateTransaction,
  useUpdateTransaction,
  usePatchTransaction,
  useDeleteTransaction,
  usePrefetchTransaction,
  usePrefetchPropertyTransactions,
} from './useTransactions';

// Interest Rates hooks
export {
  interestRateKeys,
  // Primary hooks with mock fallback
  useInterestRates,
  useYieldCurve,
  useHistoricalRates,
  useDataSources,
  useRateSpreads,
  useLendingContext,
  // Explicit mock fallback hooks
  useKeyRatesWithMockFallback,
  useYieldCurveWithMockFallback,
  useHistoricalRatesWithMockFallback,
  useDataSourcesWithMockFallback,
  useRateSpreadsWithMockFallback,
  useLendingContextWithMockFallback,
  // API-first hooks (no mock fallback)
  useKeyRatesApi,
  useYieldCurveApi,
  useHistoricalRatesApi,
  useDataSourcesApi,
  useRateSpreadsApi,
  useLendingContextApi,
} from './useInterestRates';

// Document hooks
export {
  documentKeys,
  useDocumentsWithMockFallback,
  useDocumentStatsWithMockFallback,
  useDocumentsApi,
  useDocument,
  useDocumentsByProperty,
  useDocumentStats,
  useCreateDocument,
  useUpdateDocument,
  useDeleteDocument,
  usePrefetchDocument,
  usePrefetchPropertyDocuments,
} from './useDocuments';

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

// Interest rates response types
export type {
  KeyRatesWithFallbackResponse,
  YieldCurveWithFallbackResponse,
  HistoricalRatesWithFallbackResponse,
  DataSourcesWithFallbackResponse,
  RateSpreadsWithFallbackResponse,
  LendingContextWithFallbackResponse,
} from './useInterestRates';

// Document response types
export type {
  DocumentApiResponse,
  DocumentListApiResponse,
  DocumentStatsApiResponse,
  DocumentCreateInput,
  DocumentUpdateInput,
  DocumentsWithFallbackResponse,
} from './useDocuments';

// Transaction response types
export type {
  TransactionFilters,
  TransactionApiResponse,
  TransactionListResponse,
  TransactionSummaryResponse,
  TransactionCreateInput,
  TransactionUpdateInput,
  TransactionsWithFallbackResponse,
} from './useTransactions';
