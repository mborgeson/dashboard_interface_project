/**
 * Zod schemas for report settings API responses
 *
 * Validates the snake_case JSON from /reporting/settings and
 * transforms to camelCase ReportSettings. Replaces snakeToCamel().
 */
import { z } from 'zod';

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
