/**
 * Properties API client functions
 */
import { apiClient } from './client';
import type { Property, PropertySummaryStats } from '@/types';
import {
  propertiesResponseSchema,
  propertySchema,
  propertySummaryStatsSchema,
} from './schemas/property';

export interface PropertiesResponse {
  properties: Property[];
  total: number;
}

export interface PropertyFiltersParams {
  submarket?: string;
  property_class?: string;
  min_units?: number;
  max_units?: number;
  min_value?: number;
  max_value?: number;
  skip?: number;
  limit?: number;
}

/**
 * Fetch all properties from the API
 */
export async function fetchProperties(filters?: PropertyFiltersParams): Promise<PropertiesResponse> {
  const raw = await apiClient.get<unknown>('/properties/dashboard', {
    params: filters as Record<string, string | number | boolean | undefined>,
  });
  return propertiesResponseSchema.parse(raw);
}

/**
 * Fetch a single property by ID
 */
export async function fetchPropertyById(id: string): Promise<Property> {
  const raw = await apiClient.get<unknown>(`/properties/dashboard/${id}`);
  return propertySchema.parse(raw);
}

/**
 * Fetch portfolio summary statistics
 */
export async function fetchPortfolioSummary(): Promise<PropertySummaryStats> {
  const raw = await apiClient.get<unknown>('/properties/summary');
  return propertySummaryStatsSchema.parse(raw);
}
