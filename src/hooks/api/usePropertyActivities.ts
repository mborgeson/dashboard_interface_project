/**
 * Property Activities API Hooks
 *
 * Provides React Query hooks for fetching and managing property-specific activities.
 * Follows the use[Feature]WithMockFallback pattern for development/testing.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import { get, post } from '@/lib/api';
import { propertyKeys } from './useProperties';

// ============================================================================
// Types
// ============================================================================

export type PropertyActivityType =
  | 'view'
  | 'edit'
  | 'comment'
  | 'status_change'
  | 'document_upload';

export interface PropertyActivityApiResponse {
  id: string;
  property_id: string;
  type: PropertyActivityType;
  description: string;
  user_name: string;
  user_avatar?: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface PropertyActivitiesApiResponse {
  activities: PropertyActivityApiResponse[];
  total: number;
}

export interface PropertyActivity {
  id: string;
  propertyId: string;
  type: PropertyActivityType;
  description: string;
  userName: string;
  userAvatar?: string;
  timestamp: Date;
  metadata?: Record<string, unknown>;
}

export interface PropertyActivitiesWithFallbackResponse {
  activities: PropertyActivity[];
  total: number;
}

export interface AddPropertyActivityInput {
  propertyId: string;
  type: PropertyActivityType;
  description: string;
  userName?: string;
  metadata?: Record<string, unknown>;
}

// ============================================================================
// Query Key Factory
// ============================================================================

export const propertyActivityKeys = {
  all: ['propertyActivities'] as const,
  lists: () => [...propertyActivityKeys.all, 'list'] as const,
  list: (propertyId: string, activityTypes?: PropertyActivityType[]) =>
    [...propertyActivityKeys.lists(), propertyId, activityTypes] as const,
  detail: (activityId: string) => [...propertyActivityKeys.all, 'detail', activityId] as const,
};

// ============================================================================
// Transform Functions
// ============================================================================

function transformActivityFromApi(apiActivity: PropertyActivityApiResponse): PropertyActivity {
  return {
    id: apiActivity.id,
    propertyId: apiActivity.property_id,
    type: apiActivity.type,
    description: apiActivity.description,
    userName: apiActivity.user_name,
    userAvatar: apiActivity.user_avatar,
    timestamp: new Date(apiActivity.timestamp),
    metadata: apiActivity.metadata,
  };
}

// ============================================================================
// Query Hooks
// ============================================================================

export interface UsePropertyActivitiesOptions {
  activityTypes?: PropertyActivityType[];
}

/**
 * Hook to fetch property activities with mock data fallback
 * Errors propagate to React Query error state
 */
export function usePropertyActivitiesWithMockFallback(
  propertyId: string,
  options?: UsePropertyActivitiesOptions,
  queryOptions?: Omit<
    UseQueryOptions<PropertyActivitiesWithFallbackResponse>,
    'queryKey' | 'queryFn'
  >
) {
  const activityTypes = options?.activityTypes;

  return useQuery({
    queryKey: propertyActivityKeys.list(propertyId, activityTypes),
    queryFn: async (): Promise<PropertyActivitiesWithFallbackResponse> => {
      const params: Record<string, unknown> = {};
      if (activityTypes && activityTypes.length > 0) {
        params.activity_types = activityTypes.join(',');
      }

      const response = await get<PropertyActivitiesApiResponse>(
        `/properties/${propertyId}/activities`,
        params
      );

      const activities = response.activities.map(transformActivityFromApi);
      return {
        activities: activities.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime()),
        total: response.total,
      };
    },
    enabled: !!propertyId,
    staleTime: 1000 * 60 * 2, // 2 minutes - activities should be relatively fresh
    ...queryOptions,
  });
}

/**
 * API-first hook (no mock fallback)
 */
export function usePropertyActivitiesApi(
  propertyId: string,
  options?: UsePropertyActivitiesOptions,
  queryOptions?: Omit<UseQueryOptions<PropertyActivitiesApiResponse>, 'queryKey' | 'queryFn'>
) {
  const activityTypes = options?.activityTypes;
  const params: Record<string, unknown> = {};
  if (activityTypes && activityTypes.length > 0) {
    params.activity_types = activityTypes.join(',');
  }

  return useQuery({
    queryKey: propertyActivityKeys.list(propertyId, activityTypes),
    queryFn: () => get<PropertyActivitiesApiResponse>(`/properties/${propertyId}/activities`, params),
    enabled: !!propertyId,
    ...queryOptions,
  });
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Add a new activity to a property
 */
export function useAddPropertyActivity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ propertyId, ...data }: AddPropertyActivityInput) =>
      post<PropertyActivityApiResponse, Omit<AddPropertyActivityInput, 'propertyId'>>(
        `/properties/${propertyId}/activities`,
        data
      ),
    onSuccess: (_, variables) => {
      // Invalidate activities for this property
      queryClient.invalidateQueries({
        queryKey: propertyActivityKeys.lists(),
      });
      // Also invalidate property detail as activity count may have changed
      queryClient.invalidateQueries({
        queryKey: propertyKeys.detail(variables.propertyId),
      });
    },
  });
}

// ============================================================================
// Convenience Aliases
// ============================================================================

/**
 * Primary hook for property activities - uses mock fallback pattern
 */
export const usePropertyActivities = usePropertyActivitiesWithMockFallback;
