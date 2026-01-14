/**
 * Property Activities API Hooks
 *
 * Provides React Query hooks for fetching and managing property-specific activities.
 * Follows the use[Feature]WithMockFallback pattern for development/testing.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import { get, post } from '@/lib/api';
import { USE_MOCK_DATA, IS_DEV } from '@/lib/config';
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
// Mock Data Generator
// ============================================================================

function generateMockPropertyActivities(
  propertyId: string,
  activityTypes?: PropertyActivityType[]
): PropertyActivity[] {
  const now = new Date();
  const users = [
    { name: 'John Smith', avatar: undefined },
    { name: 'Sarah Johnson', avatar: undefined },
    { name: 'Michael Chen', avatar: undefined },
    { name: 'Emily Davis', avatar: undefined },
    { name: 'Robert Wilson', avatar: undefined },
  ];

  const mockActivities: PropertyActivity[] = [
    {
      id: `${propertyId}-act-1`,
      propertyId,
      type: 'view',
      description: 'Viewed property details and financial reports',
      userName: users[0].name,
      userAvatar: users[0].avatar,
      timestamp: new Date(now.getTime() - 1000 * 60 * 30), // 30 min ago
      metadata: { section: 'financials' },
    },
    {
      id: `${propertyId}-act-2`,
      propertyId,
      type: 'comment',
      description: 'Added comment: "Cap rate looks strong, consider refinancing options"',
      userName: users[1].name,
      userAvatar: users[1].avatar,
      timestamp: new Date(now.getTime() - 1000 * 60 * 60 * 2), // 2 hours ago
      metadata: { commentId: 'cmt-123' },
    },
    {
      id: `${propertyId}-act-3`,
      propertyId,
      type: 'document_upload',
      description: 'Uploaded Q4 2024 Financial Report (PDF)',
      userName: users[2].name,
      userAvatar: users[2].avatar,
      timestamp: new Date(now.getTime() - 1000 * 60 * 60 * 5), // 5 hours ago
      metadata: { documentId: 'doc-456', fileName: 'Q4_2024_Report.pdf' },
    },
    {
      id: `${propertyId}-act-4`,
      propertyId,
      type: 'edit',
      description: 'Updated occupancy rate to 96%',
      userName: users[3].name,
      userAvatar: users[3].avatar,
      timestamp: new Date(now.getTime() - 1000 * 60 * 60 * 24), // 1 day ago
      metadata: { field: 'occupancy', oldValue: 94, newValue: 96 },
    },
    {
      id: `${propertyId}-act-5`,
      propertyId,
      type: 'status_change',
      description: 'Changed property status from "Under Review" to "Active"',
      userName: users[4].name,
      userAvatar: users[4].avatar,
      timestamp: new Date(now.getTime() - 1000 * 60 * 60 * 24 * 2), // 2 days ago
      metadata: { oldStatus: 'under_review', newStatus: 'active' },
    },
    {
      id: `${propertyId}-act-6`,
      propertyId,
      type: 'view',
      description: 'Reviewed property from mobile app',
      userName: users[0].name,
      userAvatar: users[0].avatar,
      timestamp: new Date(now.getTime() - 1000 * 60 * 60 * 24 * 3), // 3 days ago
      metadata: { platform: 'mobile' },
    },
    {
      id: `${propertyId}-act-7`,
      propertyId,
      type: 'comment',
      description: 'Added comment: "Tenant retention looking good this quarter"',
      userName: users[1].name,
      userAvatar: users[1].avatar,
      timestamp: new Date(now.getTime() - 1000 * 60 * 60 * 24 * 4), // 4 days ago
      metadata: { commentId: 'cmt-124' },
    },
    {
      id: `${propertyId}-act-8`,
      propertyId,
      type: 'document_upload',
      description: 'Uploaded lease renewal agreement',
      userName: users[2].name,
      userAvatar: users[2].avatar,
      timestamp: new Date(now.getTime() - 1000 * 60 * 60 * 24 * 5), // 5 days ago
      metadata: { documentId: 'doc-789', fileName: 'Lease_Renewal_2025.pdf' },
    },
    {
      id: `${propertyId}-act-9`,
      propertyId,
      type: 'edit',
      description: 'Updated monthly rent to $2,150',
      userName: users[3].name,
      userAvatar: users[3].avatar,
      timestamp: new Date(now.getTime() - 1000 * 60 * 60 * 24 * 7), // 1 week ago
      metadata: { field: 'averageRent', oldValue: 2100, newValue: 2150 },
    },
    {
      id: `${propertyId}-act-10`,
      propertyId,
      type: 'view',
      description: 'Generated property performance report',
      userName: users[4].name,
      userAvatar: users[4].avatar,
      timestamp: new Date(now.getTime() - 1000 * 60 * 60 * 24 * 10), // 10 days ago
      metadata: { reportType: 'performance' },
    },
  ];

  // Filter by activity types if specified
  if (activityTypes && activityTypes.length > 0) {
    return mockActivities.filter((activity) => activityTypes.includes(activity.type));
  }

  return mockActivities;
}

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
 * Falls back to mock data if API is unavailable or USE_MOCK_DATA is true
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
      if (USE_MOCK_DATA) {
        const activities = generateMockPropertyActivities(propertyId, activityTypes);
        return {
          activities: activities.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime()),
          total: activities.length,
        };
      }

      try {
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
      } catch (error) {
        if (IS_DEV) {
          console.warn('API unavailable, falling back to mock property activities:', error);
          const activities = generateMockPropertyActivities(propertyId, activityTypes);
          return {
            activities: activities.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime()),
            total: activities.length,
          };
        }
        throw error;
      }
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
