/**
 * API module exports
 */
export { apiClient, ApiError } from './client';
export {
  fetchProperties,
  fetchPropertyById,
  fetchPortfolioSummary,
  type PropertiesResponse,
  type PropertyFiltersParams,
} from './properties';
