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
  // Primary hooks with mock fallback
  useDealsWithMockFallback,
  useDealsWithMockFallback as useDeals, // Alias for backwards compatibility
  useKanbanBoard,
  useKanbanBoardWithMockFallback,
  useDealActivities,
  useDealActivitiesWithMockFallback,
  // API-first hooks (no mock fallback)
  useDealsApi,
  useDeal,
  useDealPipeline,
  useDealsByStage,
  useDealStats,
  useKanbanBoardApi,
  useDealActivitiesApi,
  // Mutations
  useCreateDeal,
  useUpdateDeal,
  useUpdateDealStage,
  useDeleteDeal,
  useAddDealActivity,
  // Prefetch utilities
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
  // Prefetch utilities
  usePrefetchKeyRates,
  usePrefetchYieldCurve,
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

// Market Data hooks
export {
  marketDataKeys,
  // Primary hooks with mock fallback
  useMarketOverview,
  useSubmarkets,
  useMarketTrends,
  useComparables,
  // Explicit mock fallback hooks
  useMarketOverviewWithMockFallback,
  useSubmarketsWithMockFallback,
  useMarketTrendsWithMockFallback,
  useComparablesWithMockFallback,
  // API-first hooks (no mock fallback)
  useMarketOverviewApi,
  useSubmarketsApi,
  useMarketTrendsApi,
  useComparablesApi,
  // Prefetch utilities
  usePrefetchMarketOverview,
  usePrefetchSubmarkets,
} from './useMarketData';

// Reporting hooks
export {
  reportingKeys,
  // Primary hooks with mock fallback
  useReportTemplates,
  useQueuedReports,
  useDistributionSchedules,
  useReportWidgets,
  // Explicit mock fallback hooks
  useReportTemplatesWithMockFallback,
  useQueuedReportsWithMockFallback,
  useDistributionSchedulesWithMockFallback,
  useReportWidgetsWithMockFallback,
  // API-first hooks (no mock fallback)
  useReportTemplatesApi,
  useReportTemplate,
  useQueuedReportsApi,
  useQueuedReport,
  useDistributionSchedulesApi,
  useReportWidgetsApi,
  // Mutations
  useCreateReportTemplate,
  useUpdateReportTemplate,
  useDeleteReportTemplate,
  useGenerateReport,
  useCreateDistributionSchedule,
  useUpdateDistributionSchedule,
  useDeleteDistributionSchedule,
  // Prefetch utilities
  usePrefetchReportTemplates,
  usePrefetchReportWidgets,
} from './useReporting';

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

// Market data response types
export type {
  MarketOverviewApiResponse,
  SubmarketsApiResponse,
  MarketTrendsApiResponse,
  ComparablesApiResponse,
  ComparableFilters,
  MarketOverviewWithFallbackResponse,
  SubmarketsWithFallbackResponse,
  MarketTrendsWithFallbackResponse,
  ComparablesWithFallbackResponse,
} from './useMarketData';

// Reporting response types
export type {
  ReportCategory,
  ReportFormat,
  ReportStatus,
  ScheduleFrequency,
  ReportTemplateApiResponse,
  ReportTemplateListApiResponse,
  QueuedReportApiResponse,
  QueuedReportListApiResponse,
  DistributionScheduleApiResponse,
  DistributionScheduleListApiResponse,
  ReportWidgetApiResponse,
  ReportWidgetListApiResponse,
  GenerateReportRequest,
  GenerateReportResponse,
  ReportTemplateCreateInput,
  ReportTemplateUpdateInput,
  DistributionScheduleCreateInput,
  DistributionScheduleUpdateInput,
  TemplateFilters,
  QueueFilters,
  ScheduleFilters,
  TemplatesWithFallbackResponse,
  QueuedReportsWithFallbackResponse,
  SchedulesWithFallbackResponse,
  WidgetsWithFallbackResponse,
} from './useReporting';

// Deal response types
export type {
  KanbanFilters,
  KanbanStageData,
  KanbanBoardApiResponse,
  KanbanBoardWithFallbackResponse,
  DealActivityApiResponse,
  DealActivitiesApiResponse,
  DealActivity,
  DealActivitiesWithFallbackResponse,
  AddActivityInput,
  DealsWithFallbackResponse,
} from './useDeals';
