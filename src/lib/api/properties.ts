/**
 * Properties API client functions
 */
import { z } from 'zod';
import { apiClient } from './client';
import type { Property, PropertySummaryStats } from '@/types';
import {
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

/** Loose wrapper schema: only validates the outer shape, not individual properties */
const propertiesEnvelopeSchema = z.object({
  properties: z.array(z.unknown()),
  total: z.number(),
});

/**
 * Fetch all properties from the API.
 *
 * Parses each property individually so that a single malformed row does not
 * silently discard the entire portfolio. Failed rows are logged and skipped;
 * the returned `total` reflects the raw count from the server (not just the
 * successfully-parsed subset).
 */
export async function fetchProperties(filters?: PropertyFiltersParams): Promise<PropertiesResponse> {
  // Default limit=200 to retrieve all properties (backend defaults to 50)
  const params = { limit: 200, ...filters };
  const raw = await apiClient.get<unknown>('/properties/dashboard', {
    params: params as Record<string, string | number | boolean | undefined>,
  });

  // Validate the outer envelope first — throw if the response shape is wrong
  const envelope = propertiesEnvelopeSchema.parse(raw);

  // Parse each property individually, collecting only valid ones
  const properties: Property[] = [];
  let failCount = 0;
  for (const item of envelope.properties) {
    const result = propertySchema.safeParse(item);
    if (result.success) {
      properties.push(result.data as Property);
    } else {
      failCount++;
      if (import.meta.env.DEV) {
        const id = (item as Record<string, unknown>)?.id ?? '?';
        console.warn(
          `[fetchProperties] Property id=${id} failed Zod validation — skipped.`,
          result.error.flatten(),
        );
      }
    }
  }

  if (failCount > 0) {
    console.warn(
      `[fetchProperties] ${failCount}/${envelope.properties.length} properties failed schema validation and were excluded.`,
    );
  }

  return { properties, total: envelope.total };
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
