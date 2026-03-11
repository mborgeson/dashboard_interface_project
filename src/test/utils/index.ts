/**
 * Barrel export for shared frontend test utilities.
 *
 * Import from '@/test/utils' in test files:
 *
 *   import { renderWithProviders, createMockDeal } from '@/test/utils';
 */
export {
  createTestQueryClient,
  renderWithProviders,
  createWrapper,
} from './renderWithProviders';

export {
  createMockBackendDeal,
  createMockDeal,
  createMockBackendProperty,
  createMockProperty,
  createMockBackendSaleRecord,
  createMockPaginatedResponse,
} from './mockApiResponses';
