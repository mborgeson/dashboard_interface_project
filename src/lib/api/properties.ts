/**
 * Properties API client functions
 */
import { apiClient } from './client';
import type { Property, PropertySummaryStats } from '@/types';

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
  const response = await apiClient.get<PropertiesResponse>('/properties', {
    params: filters as Record<string, string | number | boolean | undefined>,
  });

  // Transform date strings to Date objects if needed
  const properties = response.properties.map(transformPropertyDates);

  return {
    properties,
    total: response.total,
  };
}

/**
 * Fetch a single property by ID
 */
export async function fetchPropertyById(id: string): Promise<Property> {
  const response = await apiClient.get<Property>(`/properties/${id}`);
  return transformPropertyDates(response);
}

/**
 * Fetch portfolio summary statistics
 */
export async function fetchPortfolioSummary(): Promise<PropertySummaryStats> {
  return apiClient.get<PropertySummaryStats>('/properties/summary');
}

/**
 * Transform date strings from API to Date objects
 * The API returns ISO date strings, but our Property type expects Date objects
 */
function transformPropertyDates(property: Property): Property {
  return {
    ...property,
    acquisition: {
      ...property.acquisition,
      date: new Date(property.acquisition.date),
    },
    financing: {
      ...property.financing,
      originationDate: new Date(property.financing.originationDate),
      maturityDate: new Date(property.financing.maturityDate),
    },
    valuation: {
      ...property.valuation,
      lastAppraisalDate: new Date(property.valuation.lastAppraisalDate),
    },
  };
}
