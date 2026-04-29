/**
 * Zod schemas for the /reporting/* API surface
 *
 * Validates snake_case JSON responses and transforms to camelCase.
 * Replaces snakeToCamel() and provides runtime validation for templates,
 * queued reports, distribution schedules, widgets, and settings.
 */
import { z } from 'zod';

// ---------- Shared enum constants ----------

export const REPORT_CATEGORIES = ['executive', 'financial', 'market', 'portfolio', 'custom'] as const;
export const REPORT_FORMATS = ['pdf', 'excel', 'pptx'] as const;
export const REPORT_STATUSES = ['pending', 'generating', 'completed', 'failed'] as const;
export const SCHEDULE_FREQUENCIES = ['daily', 'weekly', 'monthly', 'quarterly'] as const;

/**
 * Schema for the raw snake_case API response.
 * Transforms to camelCase ReportSettings on parse.
 */
export const reportSettingsResponseSchema = z
  .object({
    company_name: z.string(),
    company_logo: z.string().nullable(),
    primary_color: z.string(),
    secondary_color: z.string(),
    default_font: z.string(),
    default_page_size: z.enum(['letter', 'a4', 'legal']),
    default_orientation: z.enum(['portrait', 'landscape']),
    include_page_numbers: z.boolean(),
    include_table_of_contents: z.boolean(),
    include_timestamp: z.boolean(),
    footer_text: z.string(),
    header_text: z.string(),
    watermark_text: z.string().nullable(),
  })
  .transform((s) => ({
    companyName: s.company_name,
    companyLogo: s.company_logo ?? undefined,
    primaryColor: s.primary_color,
    secondaryColor: s.secondary_color,
    defaultFont: s.default_font,
    defaultPageSize: s.default_page_size,
    defaultOrientation: s.default_orientation,
    includePageNumbers: s.include_page_numbers,
    includeTableOfContents: s.include_table_of_contents,
    includeTimestamp: s.include_timestamp,
    footerText: s.footer_text,
    headerText: s.header_text,
    watermarkText: s.watermark_text ?? undefined,
  }));

// ---------- Report Template ----------

export const reportTemplateResponseSchema = z
  .object({
    id: z.number(),
    name: z.string(),
    description: z.string().nullable().optional(),
    category: z.enum(REPORT_CATEGORIES),
    sections: z.array(z.string()),
    export_formats: z.array(z.enum(REPORT_FORMATS)),
    is_default: z.boolean(),
    created_by: z.string(),
    config: z.record(z.string(), z.unknown()).nullable().optional(),
    created_at: z.string(),
    updated_at: z.string(),
  })
  .transform((t) => ({
    id: t.id,
    name: t.name,
    description: t.description ?? undefined,
    category: t.category,
    sections: t.sections,
    exportFormats: t.export_formats,
    isDefault: t.is_default,
    createdBy: t.created_by,
    config: t.config ?? undefined,
    createdAt: t.created_at,
    updatedAt: t.updated_at,
  }));

export const reportTemplateListResponseSchema = z
  .object({
    items: z.array(reportTemplateResponseSchema),
    total: z.number(),
    page: z.number(),
    page_size: z.number(),
  })
  .transform((r) => ({
    items: r.items,
    total: r.total,
    page: r.page,
    pageSize: r.page_size,
  }));

// ---------- Queued Report ----------

export const queuedReportResponseSchema = z
  .object({
    id: z.number(),
    name: z.string(),
    template_id: z.number(),
    template_name: z.string().nullable().optional(),
    format: z.enum(REPORT_FORMATS),
    requested_by: z.string(),
    status: z.enum(REPORT_STATUSES),
    progress: z.number(),
    requested_at: z.string(),
    completed_at: z.string().nullable().optional(),
    file_size: z.string().nullable().optional(),
    download_url: z.string().nullable().optional(),
    error: z.string().nullable().optional(),
    created_at: z.string(),
    updated_at: z.string(),
  })
  .transform((q) => ({
    id: q.id,
    name: q.name,
    templateId: q.template_id,
    templateName: q.template_name ?? undefined,
    format: q.format,
    requestedBy: q.requested_by,
    status: q.status,
    progress: q.progress,
    requestedAt: q.requested_at,
    completedAt: q.completed_at ?? undefined,
    fileSize: q.file_size ?? undefined,
    downloadUrl: q.download_url ?? undefined,
    error: q.error ?? undefined,
    createdAt: q.created_at,
    updatedAt: q.updated_at,
  }));

export const queuedReportListResponseSchema = z
  .object({
    items: z.array(queuedReportResponseSchema),
    total: z.number(),
    page: z.number(),
    page_size: z.number(),
  })
  .transform((r) => ({
    items: r.items,
    total: r.total,
    page: r.page,
    pageSize: r.page_size,
  }));

// ---------- Distribution Schedule ----------

export const distributionScheduleResponseSchema = z
  .object({
    id: z.number(),
    name: z.string(),
    template_id: z.number(),
    template_name: z.string().nullable().optional(),
    recipients: z.array(z.string()),
    frequency: z.enum(SCHEDULE_FREQUENCIES),
    day_of_week: z.number().nullable().optional(),
    day_of_month: z.number().nullable().optional(),
    time: z.string(),
    format: z.enum(REPORT_FORMATS),
    is_active: z.boolean(),
    last_sent: z.string().nullable().optional(),
    next_scheduled: z.string(),
    created_at: z.string(),
    updated_at: z.string(),
  })
  .transform((d) => ({
    id: d.id,
    name: d.name,
    templateId: d.template_id,
    templateName: d.template_name ?? undefined,
    recipients: d.recipients,
    frequency: d.frequency,
    dayOfWeek: d.day_of_week ?? undefined,
    dayOfMonth: d.day_of_month ?? undefined,
    time: d.time,
    format: d.format,
    isActive: d.is_active,
    lastSent: d.last_sent ?? undefined,
    nextScheduled: d.next_scheduled,
    createdAt: d.created_at,
    updatedAt: d.updated_at,
  }));

export const distributionScheduleListResponseSchema = z.object({
  items: z.array(distributionScheduleResponseSchema),
  total: z.number(),
});

// ---------- Generate Report ----------

export const generateReportRequestSchema = z.object({
  template_id: z.number(),
  name: z.string(),
  format: z.enum(REPORT_FORMATS),
  parameters: z.record(z.string(), z.unknown()).nullable().optional(),
});

export const generateReportResponseSchema = z
  .object({
    queued_report_id: z.number(),
    status: z.enum(REPORT_STATUSES),
    message: z.string(),
  })
  .transform((g) => ({
    queuedReportId: g.queued_report_id,
    status: g.status,
    message: g.message,
  }));

// ---------- Report Widget ----------

export const reportWidgetResponseSchema = z
  .object({
    id: z.string(),
    type: z.string(),
    name: z.string(),
    description: z.string(),
    category: z.string(),
    icon: z.string(),
    default_width: z.number(),
    default_height: z.number(),
    configurable: z.boolean(),
  })
  .transform((w) => ({
    id: w.id,
    type: w.type,
    name: w.name,
    description: w.description,
    category: w.category,
    icon: w.icon,
    defaultWidth: w.default_width,
    defaultHeight: w.default_height,
    configurable: w.configurable,
  }));

export const reportWidgetListResponseSchema = z.object({
  widgets: z.array(reportWidgetResponseSchema),
  total: z.number(),
});
