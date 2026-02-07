/**
 * Reporting API — report settings CRUD
 */
import { apiClient } from './client';
import type { ReportSettings } from '@/data/mockReportingData';
import { reportSettingsResponseSchema } from './schemas/reporting';

/* ------------------------------------------------------------------ */
/* camelCase → snake_case helper (outgoing PUT body)                   */
/* ------------------------------------------------------------------ */

interface ReportSettingsSnake {
  company_name?: string;
  company_logo?: string | null;
  primary_color?: string;
  secondary_color?: string;
  default_font?: string;
  default_page_size?: string;
  default_orientation?: string;
  include_page_numbers?: boolean;
  include_table_of_contents?: boolean;
  include_timestamp?: boolean;
  footer_text?: string;
  header_text?: string;
  watermark_text?: string | null;
}

function camelToSnake(c: Partial<ReportSettings>): Partial<ReportSettingsSnake> {
  const out: Record<string, unknown> = {};
  if (c.companyName !== undefined) out.company_name = c.companyName;
  if (c.companyLogo !== undefined) out.company_logo = c.companyLogo ?? null;
  if (c.primaryColor !== undefined) out.primary_color = c.primaryColor;
  if (c.secondaryColor !== undefined) out.secondary_color = c.secondaryColor;
  if (c.defaultFont !== undefined) out.default_font = c.defaultFont;
  if (c.defaultPageSize !== undefined) out.default_page_size = c.defaultPageSize;
  if (c.defaultOrientation !== undefined) out.default_orientation = c.defaultOrientation;
  if (c.includePageNumbers !== undefined) out.include_page_numbers = c.includePageNumbers;
  if (c.includeTableOfContents !== undefined) out.include_table_of_contents = c.includeTableOfContents;
  if (c.includeTimestamp !== undefined) out.include_timestamp = c.includeTimestamp;
  if (c.footerText !== undefined) out.footer_text = c.footerText;
  if (c.headerText !== undefined) out.header_text = c.headerText;
  if (c.watermarkText !== undefined) out.watermark_text = c.watermarkText ?? null;
  return out as Partial<ReportSettingsSnake>;
}

/* ------------------------------------------------------------------ */
/* Public API                                                         */
/* ------------------------------------------------------------------ */

export async function fetchReportSettings(): Promise<ReportSettings> {
  const raw = await apiClient.get<unknown>('/reporting/settings');
  return reportSettingsResponseSchema.parse(raw);
}

export async function updateReportSettings(
  settings: Partial<ReportSettings>,
): Promise<ReportSettings> {
  const raw = await apiClient.put<unknown>(
    '/reporting/settings',
    camelToSnake(settings),
  );
  return reportSettingsResponseSchema.parse(raw);
}
