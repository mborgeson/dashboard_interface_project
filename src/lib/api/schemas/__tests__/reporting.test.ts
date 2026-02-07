import { describe, it, expect } from 'vitest';
import { reportSettingsResponseSchema } from '../reporting';

function makeSnakeSettings(overrides: Record<string, unknown> = {}) {
  return {
    company_name: 'Acme Corp',
    company_logo: 'https://example.com/logo.png',
    primary_color: '#1a73e8',
    secondary_color: '#34a853',
    default_font: 'Inter',
    default_page_size: 'letter',
    default_orientation: 'portrait',
    include_page_numbers: true,
    include_table_of_contents: true,
    include_timestamp: false,
    footer_text: 'Confidential',
    header_text: 'Acme Report',
    watermark_text: null,
    ...overrides,
  };
}

describe('reportSettingsResponseSchema', () => {
  it('transforms snake_case to camelCase', () => {
    const result = reportSettingsResponseSchema.parse(makeSnakeSettings());

    expect(result.companyName).toBe('Acme Corp');
    expect(result.companyLogo).toBe('https://example.com/logo.png');
    expect(result.primaryColor).toBe('#1a73e8');
    expect(result.secondaryColor).toBe('#34a853');
    expect(result.defaultFont).toBe('Inter');
    expect(result.defaultPageSize).toBe('letter');
    expect(result.defaultOrientation).toBe('portrait');
    expect(result.includePageNumbers).toBe(true);
    expect(result.includeTableOfContents).toBe(true);
    expect(result.includeTimestamp).toBe(false);
    expect(result.footerText).toBe('Confidential');
    expect(result.headerText).toBe('Acme Report');
  });

  it('converts null company_logo to undefined', () => {
    const result = reportSettingsResponseSchema.parse(
      makeSnakeSettings({ company_logo: null }),
    );
    expect(result.companyLogo).toBeUndefined();
  });

  it('converts null watermark_text to undefined', () => {
    const result = reportSettingsResponseSchema.parse(
      makeSnakeSettings({ watermark_text: null }),
    );
    expect(result.watermarkText).toBeUndefined();
  });

  it('preserves non-null watermark_text', () => {
    const result = reportSettingsResponseSchema.parse(
      makeSnakeSettings({ watermark_text: 'DRAFT' }),
    );
    expect(result.watermarkText).toBe('DRAFT');
  });

  it('throws on missing required field', () => {
    const raw = makeSnakeSettings();
    delete (raw as Record<string, unknown>).company_name;
    expect(() => reportSettingsResponseSchema.parse(raw)).toThrow();
  });

  it('throws on invalid page size', () => {
    expect(() =>
      reportSettingsResponseSchema.parse(
        makeSnakeSettings({ default_page_size: 'tabloid' }),
      ),
    ).toThrow();
  });

  it('throws on invalid orientation', () => {
    expect(() =>
      reportSettingsResponseSchema.parse(
        makeSnakeSettings({ default_orientation: 'diagonal' }),
      ),
    ).toThrow();
  });
});
