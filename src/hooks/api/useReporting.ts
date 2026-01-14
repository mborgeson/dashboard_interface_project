import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import { get, post, put, del } from '@/lib/api';
import { USE_MOCK_DATA, IS_DEV } from '@/lib/config';
import {
  mockReportTemplates,
  mockQueuedReports,
  mockDistributionSchedules,
  mockReportWidgets,
  type ReportTemplate,
  type QueuedReport,
  type DistributionSchedule,
  type ReportWidget,
} from '@/data/mockReportingData';

// ============================================================================
// API Types
// ============================================================================

export type ReportCategory = 'executive' | 'financial' | 'market' | 'portfolio' | 'custom';
export type ReportFormat = 'pdf' | 'excel' | 'pptx';
export type ReportStatus = 'pending' | 'generating' | 'completed' | 'failed';
export type ScheduleFrequency = 'daily' | 'weekly' | 'monthly' | 'quarterly';

export interface ReportTemplateApiResponse {
  id: number;
  name: string;
  description: string | null;
  category: ReportCategory;
  sections: string[];
  export_formats: ReportFormat[];
  is_default: boolean;
  created_by: string;
  config: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface ReportTemplateListApiResponse {
  items: ReportTemplateApiResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface QueuedReportApiResponse {
  id: number;
  name: string;
  template_id: number;
  template_name: string | null;
  format: ReportFormat;
  requested_by: string;
  status: ReportStatus;
  progress: number;
  requested_at: string;
  completed_at: string | null;
  file_size: string | null;
  download_url: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface QueuedReportListApiResponse {
  items: QueuedReportApiResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface DistributionScheduleApiResponse {
  id: number;
  name: string;
  template_id: number;
  template_name: string | null;
  recipients: string[];
  frequency: ScheduleFrequency;
  day_of_week: number | null;
  day_of_month: number | null;
  time: string;
  format: ReportFormat;
  is_active: boolean;
  last_sent: string | null;
  next_scheduled: string;
  created_at: string;
  updated_at: string;
}

export interface DistributionScheduleListApiResponse {
  items: DistributionScheduleApiResponse[];
  total: number;
}

export interface ReportWidgetApiResponse {
  id: string;
  type: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  default_width: number;
  default_height: number;
  configurable: boolean;
}

export interface ReportWidgetListApiResponse {
  widgets: ReportWidgetApiResponse[];
  total: number;
}

export interface GenerateReportRequest {
  template_id: number;
  name: string;
  format: ReportFormat;
  parameters?: Record<string, unknown>;
}

export interface GenerateReportResponse {
  queued_report_id: number;
  status: ReportStatus;
  message: string;
}

export interface ReportTemplateCreateInput {
  name: string;
  description?: string;
  category: ReportCategory;
  sections: string[];
  export_formats: ReportFormat[];
  is_default?: boolean;
  created_by?: string;
  config?: Record<string, unknown>;
}

export interface ReportTemplateUpdateInput {
  id: number;
  name?: string;
  description?: string;
  category?: ReportCategory;
  sections?: string[];
  export_formats?: ReportFormat[];
  is_default?: boolean;
  config?: Record<string, unknown>;
}

export interface DistributionScheduleCreateInput {
  name: string;
  template_id: number;
  recipients: string[];
  frequency: ScheduleFrequency;
  day_of_week?: number;
  day_of_month?: number;
  time: string;
  format: ReportFormat;
  is_active?: boolean;
  next_scheduled: string;
}

export interface DistributionScheduleUpdateInput {
  id: number;
  name?: string;
  recipients?: string[];
  frequency?: ScheduleFrequency;
  day_of_week?: number;
  day_of_month?: number;
  time?: string;
  format?: ReportFormat;
  is_active?: boolean;
  next_scheduled?: string;
}

// ============================================================================
// Query Key Factory
// ============================================================================

export const reportingKeys = {
  all: ['reporting'] as const,
  templates: () => [...reportingKeys.all, 'templates'] as const,
  templateList: (filters: TemplateFilters) => [...reportingKeys.templates(), 'list', filters] as const,
  templateDetail: (id: number) => [...reportingKeys.templates(), 'detail', id] as const,
  queue: () => [...reportingKeys.all, 'queue'] as const,
  queueList: (filters: QueueFilters) => [...reportingKeys.queue(), 'list', filters] as const,
  queueDetail: (id: number) => [...reportingKeys.queue(), 'detail', id] as const,
  schedules: () => [...reportingKeys.all, 'schedules'] as const,
  scheduleList: (filters: ScheduleFilters) => [...reportingKeys.schedules(), 'list', filters] as const,
  widgets: (type?: string) => [...reportingKeys.all, 'widgets', type] as const,
};

export interface TemplateFilters {
  page?: number;
  page_size?: number;
  category?: ReportCategory;
  is_default?: boolean;
  search?: string;
}

export interface QueueFilters {
  page?: number;
  page_size?: number;
  status?: ReportStatus;
  template_id?: number;
}

export interface ScheduleFilters {
  active_only?: boolean;
  template_id?: number;
}

// ============================================================================
// Transform Functions
// ============================================================================

function transformTemplateFromApi(api: ReportTemplateApiResponse): ReportTemplate {
  return {
    id: String(api.id),
    name: api.name,
    description: api.description || '',
    category: api.category,
    sections: api.sections,
    lastModified: api.updated_at.split('T')[0],
    createdBy: api.created_by,
    isDefault: api.is_default,
    exportFormats: api.export_formats,
  };
}

function transformQueuedFromApi(api: QueuedReportApiResponse): QueuedReport {
  return {
    id: String(api.id),
    name: api.name,
    templateId: String(api.template_id),
    templateName: api.template_name || '',
    status: api.status,
    progress: api.progress,
    requestedBy: api.requested_by,
    requestedAt: api.requested_at,
    completedAt: api.completed_at || undefined,
    format: api.format,
    fileSize: api.file_size || undefined,
    downloadUrl: api.download_url || undefined,
    error: api.error || undefined,
  };
}

function transformScheduleFromApi(api: DistributionScheduleApiResponse): DistributionSchedule {
  return {
    id: String(api.id),
    name: api.name,
    templateId: String(api.template_id),
    templateName: api.template_name || '',
    recipients: api.recipients,
    frequency: api.frequency,
    dayOfWeek: api.day_of_week || undefined,
    dayOfMonth: api.day_of_month || undefined,
    time: api.time,
    format: api.format,
    isActive: api.is_active,
    lastSent: api.last_sent || undefined,
    nextScheduled: api.next_scheduled,
  };
}

function transformWidgetFromApi(api: ReportWidgetApiResponse): ReportWidget {
  return {
    id: api.id,
    type: api.type as ReportWidget['type'],
    name: api.name,
    description: api.description,
    category: api.category,
    icon: api.icon,
    defaultWidth: api.default_width,
    defaultHeight: api.default_height,
    configurable: api.configurable,
  };
}

// ============================================================================
// Response Types with Fallback
// ============================================================================

export interface TemplatesWithFallbackResponse {
  templates: ReportTemplate[];
  total: number;
}

export interface QueuedReportsWithFallbackResponse {
  reports: QueuedReport[];
  total: number;
}

export interface SchedulesWithFallbackResponse {
  schedules: DistributionSchedule[];
  total: number;
}

export interface WidgetsWithFallbackResponse {
  widgets: ReportWidget[];
  total: number;
}

// ============================================================================
// Query Hooks (with mock data fallback)
// ============================================================================

/**
 * Hook to fetch report templates with mock data fallback
 */
export function useReportTemplatesWithMockFallback(
  filters: TemplateFilters = {},
  options?: Omit<UseQueryOptions<TemplatesWithFallbackResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: reportingKeys.templateList(filters),
    queryFn: async (): Promise<TemplatesWithFallbackResponse> => {
      if (USE_MOCK_DATA) {
        let filtered = [...mockReportTemplates];

        if (filters.category) {
          filtered = filtered.filter((t) => t.category === filters.category);
        }
        if (filters.is_default !== undefined) {
          filtered = filtered.filter((t) => t.isDefault === filters.is_default);
        }
        if (filters.search) {
          const search = filters.search.toLowerCase();
          filtered = filtered.filter(
            (t) =>
              t.name.toLowerCase().includes(search) ||
              t.description.toLowerCase().includes(search)
          );
        }

        const page = filters.page || 1;
        const pageSize = filters.page_size || 20;
        const start = (page - 1) * pageSize;
        const paginated = filtered.slice(start, start + pageSize);

        return {
          templates: paginated,
          total: filtered.length,
        };
      }

      try {
        const response = await get<ReportTemplateListApiResponse>(
          '/reporting/templates',
          filters as Record<string, unknown>
        );
        return {
          templates: response.items.map(transformTemplateFromApi),
          total: response.total,
        };
      } catch (error) {
        if (IS_DEV) {
          console.warn('API unavailable, falling back to mock templates:', error);
          return {
            templates: mockReportTemplates,
            total: mockReportTemplates.length,
          };
        }
        throw error;
      }
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    ...options,
  });
}

/**
 * Hook to fetch queued reports with mock data fallback
 */
export function useQueuedReportsWithMockFallback(
  filters: QueueFilters = {},
  options?: Omit<UseQueryOptions<QueuedReportsWithFallbackResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: reportingKeys.queueList(filters),
    queryFn: async (): Promise<QueuedReportsWithFallbackResponse> => {
      if (USE_MOCK_DATA) {
        let filtered = [...mockQueuedReports];

        if (filters.status) {
          filtered = filtered.filter((r) => r.status === filters.status);
        }
        if (filters.template_id) {
          filtered = filtered.filter((r) => r.templateId === String(filters.template_id));
        }

        const page = filters.page || 1;
        const pageSize = filters.page_size || 20;
        const start = (page - 1) * pageSize;
        const paginated = filtered.slice(start, start + pageSize);

        return {
          reports: paginated,
          total: filtered.length,
        };
      }

      try {
        const response = await get<QueuedReportListApiResponse>(
          '/reporting/queue',
          filters as Record<string, unknown>
        );
        return {
          reports: response.items.map(transformQueuedFromApi),
          total: response.total,
        };
      } catch (error) {
        if (IS_DEV) {
          console.warn('API unavailable, falling back to mock queued reports:', error);
          return {
            reports: mockQueuedReports,
            total: mockQueuedReports.length,
          };
        }
        throw error;
      }
    },
    staleTime: 1000 * 30, // 30 seconds - queue changes more frequently
    ...options,
  });
}

/**
 * Hook to fetch distribution schedules with mock data fallback
 */
export function useDistributionSchedulesWithMockFallback(
  filters: ScheduleFilters = {},
  options?: Omit<UseQueryOptions<SchedulesWithFallbackResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: reportingKeys.scheduleList(filters),
    queryFn: async (): Promise<SchedulesWithFallbackResponse> => {
      if (USE_MOCK_DATA) {
        let filtered = [...mockDistributionSchedules];

        if (filters.active_only) {
          filtered = filtered.filter((s) => s.isActive);
        }
        if (filters.template_id) {
          filtered = filtered.filter((s) => s.templateId === String(filters.template_id));
        }

        return {
          schedules: filtered,
          total: filtered.length,
        };
      }

      try {
        const response = await get<DistributionScheduleListApiResponse>(
          '/reporting/schedules',
          filters as Record<string, unknown>
        );
        return {
          schedules: response.items.map(transformScheduleFromApi),
          total: response.total,
        };
      } catch (error) {
        if (IS_DEV) {
          console.warn('API unavailable, falling back to mock schedules:', error);
          return {
            schedules: mockDistributionSchedules,
            total: mockDistributionSchedules.length,
          };
        }
        throw error;
      }
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    ...options,
  });
}

/**
 * Hook to fetch report widgets with mock data fallback
 */
export function useReportWidgetsWithMockFallback(
  widgetType?: string,
  options?: Omit<UseQueryOptions<WidgetsWithFallbackResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: reportingKeys.widgets(widgetType),
    queryFn: async (): Promise<WidgetsWithFallbackResponse> => {
      if (USE_MOCK_DATA) {
        let filtered = [...mockReportWidgets];
        if (widgetType) {
          filtered = filtered.filter((w) => w.type === widgetType);
        }
        return {
          widgets: filtered,
          total: filtered.length,
        };
      }

      try {
        const params = widgetType ? { widget_type: widgetType } : {};
        const response = await get<ReportWidgetListApiResponse>('/reporting/widgets', params);
        return {
          widgets: response.widgets.map(transformWidgetFromApi),
          total: response.total,
        };
      } catch (error) {
        if (IS_DEV) {
          console.warn('API unavailable, falling back to mock widgets:', error);
          return {
            widgets: mockReportWidgets,
            total: mockReportWidgets.length,
          };
        }
        throw error;
      }
    },
    staleTime: 1000 * 60 * 30, // 30 minutes - widgets rarely change
    ...options,
  });
}

// ============================================================================
// Query Hooks (API-first, no mock fallback)
// ============================================================================

/**
 * Fetch report templates (API-first)
 */
export function useReportTemplatesApi(
  filters: TemplateFilters = {},
  options?: Omit<UseQueryOptions<ReportTemplateListApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: reportingKeys.templateList(filters),
    queryFn: () =>
      get<ReportTemplateListApiResponse>('/reporting/templates', filters as Record<string, unknown>),
    ...options,
  });
}

/**
 * Fetch a single template by ID
 */
export function useReportTemplate(
  id: number,
  options?: Omit<UseQueryOptions<ReportTemplateApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: reportingKeys.templateDetail(id),
    queryFn: () => get<ReportTemplateApiResponse>(`/reporting/templates/${id}`),
    enabled: !!id,
    ...options,
  });
}

/**
 * Fetch queued reports (API-first)
 */
export function useQueuedReportsApi(
  filters: QueueFilters = {},
  options?: Omit<UseQueryOptions<QueuedReportListApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: reportingKeys.queueList(filters),
    queryFn: () =>
      get<QueuedReportListApiResponse>('/reporting/queue', filters as Record<string, unknown>),
    ...options,
  });
}

/**
 * Fetch a single queued report by ID
 */
export function useQueuedReport(
  id: number,
  options?: Omit<UseQueryOptions<QueuedReportApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: reportingKeys.queueDetail(id),
    queryFn: () => get<QueuedReportApiResponse>(`/reporting/queue/${id}`),
    enabled: !!id,
    ...options,
  });
}

/**
 * Fetch distribution schedules (API-first)
 */
export function useDistributionSchedulesApi(
  filters: ScheduleFilters = {},
  options?: Omit<UseQueryOptions<DistributionScheduleListApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: reportingKeys.scheduleList(filters),
    queryFn: () =>
      get<DistributionScheduleListApiResponse>(
        '/reporting/schedules',
        filters as Record<string, unknown>
      ),
    ...options,
  });
}

/**
 * Fetch report widgets (API-first)
 */
export function useReportWidgetsApi(
  widgetType?: string,
  options?: Omit<UseQueryOptions<ReportWidgetListApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: reportingKeys.widgets(widgetType),
    queryFn: () => {
      const params = widgetType ? { widget_type: widgetType } : {};
      return get<ReportWidgetListApiResponse>('/reporting/widgets', params);
    },
    ...options,
  });
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Create a new report template
 */
export function useCreateReportTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ReportTemplateCreateInput) =>
      post<ReportTemplateApiResponse, ReportTemplateCreateInput>('/reporting/templates', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: reportingKeys.templates() });
    },
  });
}

/**
 * Update a report template
 */
export function useUpdateReportTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, ...data }: ReportTemplateUpdateInput) =>
      put<ReportTemplateApiResponse, Omit<ReportTemplateUpdateInput, 'id'>>(
        `/reporting/templates/${id}`,
        data
      ),
    onSuccess: (data) => {
      queryClient.setQueryData(reportingKeys.templateDetail(data.id), data);
      queryClient.invalidateQueries({ queryKey: reportingKeys.templates() });
    },
  });
}

/**
 * Delete a report template
 */
export function useDeleteReportTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => del<void>(`/reporting/templates/${id}`),
    onSuccess: (_, id) => {
      queryClient.removeQueries({ queryKey: reportingKeys.templateDetail(id) });
      queryClient.invalidateQueries({ queryKey: reportingKeys.templates() });
    },
  });
}

/**
 * Generate a report
 */
export function useGenerateReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: GenerateReportRequest) =>
      post<GenerateReportResponse, GenerateReportRequest>('/reporting/generate', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: reportingKeys.queue() });
    },
  });
}

/**
 * Create a distribution schedule
 */
export function useCreateDistributionSchedule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: DistributionScheduleCreateInput) =>
      post<DistributionScheduleApiResponse, DistributionScheduleCreateInput>(
        '/reporting/schedules',
        data
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: reportingKeys.schedules() });
    },
  });
}

/**
 * Update a distribution schedule
 */
export function useUpdateDistributionSchedule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, ...data }: DistributionScheduleUpdateInput) =>
      put<DistributionScheduleApiResponse, Omit<DistributionScheduleUpdateInput, 'id'>>(
        `/reporting/schedules/${id}`,
        data
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: reportingKeys.schedules() });
    },
  });
}

/**
 * Delete a distribution schedule
 */
export function useDeleteDistributionSchedule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => del<void>(`/reporting/schedules/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: reportingKeys.schedules() });
    },
  });
}

// ============================================================================
// Convenience Aliases
// ============================================================================

export const useReportTemplates = useReportTemplatesWithMockFallback;
export const useQueuedReports = useQueuedReportsWithMockFallback;
export const useDistributionSchedules = useDistributionSchedulesWithMockFallback;
export const useReportWidgets = useReportWidgetsWithMockFallback;
