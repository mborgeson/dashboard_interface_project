/**
 * Reporting API — report settings CRUD
 */
import { apiClient } from './client';
import type { ReportSettings } from '@/data/mockReportingData';

/* ------------------------------------------------------------------ */
/* Snake ↔ camel helpers (report-settings fields only)                */
/* ------------------------------------------------------------------ */

interface ReportSettingsSnake {
  company_name: string;
  company_logo: string | null;
  primary_color: string;
  secondary_color: string;
  default_font: string;
  default_page_size: string;
  default_orientation: string;
  include_page_numbers: boolean;
  include_table_of_contents: boolean;
  include_timestamp: boolean;
  footer_text: string;
  header_text: string;
  watermark_text: string | null;
}

function snakeToCamel(s: ReportSettingsSnake): ReportSettings {
  return {
    companyName: s.company_name,
    companyLogo: s.company_logo ?? undefined,
    primaryColor: s.primary_color,
    secondaryColor: s.secondary_color,
    defaultFont: s.default_font,
    defaultPageSize: s.default_page_size as ReportSettings['defaultPageSize'],
    defaultOrientation: s.default_orientation as ReportSettings['defaultOrientation'],
    includePageNumbers: s.include_page_numbers,
    includeTableOfContents: s.include_table_of_contents,
    includeTimestamp: s.include_timestamp,
    footerText: s.footer_text,
    headerText: s.header_text,
    watermarkText: s.watermark_text ?? undefined,
  };
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
  const raw = await apiClient.get<ReportSettingsSnake>('/reporting/settings');
  return snakeToCamel(raw);
}

export async function updateReportSettings(
  settings: Partial<ReportSettings>,
): Promise<ReportSettings> {
  const raw = await apiClient.put<ReportSettingsSnake>(
    '/reporting/settings',
    camelToSnake(settings),
  );
  return snakeToCamel(raw);
}
