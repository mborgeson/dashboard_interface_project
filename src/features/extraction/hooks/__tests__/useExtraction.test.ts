import { describe, it, expect } from 'vitest';
import { formatExtractedValue, getExtractionDuration } from '../useExtraction';
import type { ExtractedValue, ExtractionRun } from '@/types/extraction';

function makeValue(overrides: Partial<ExtractedValue>): ExtractedValue {
  return {
    id: '1',
    extraction_run_id: 'run-1',
    property_name: 'Test Property',
    field_name: 'TEST_FIELD',
    field_category: 'Test',
    data_type: 'text',
    value_text: undefined,
    value_numeric: undefined,
    value_date: undefined,
    is_error: false,
    error_message: undefined,
    sheet_name: 'Sheet1',
    cell_address: 'A1',
    extracted_at: '2026-01-01',
    ...overrides,
  };
}

describe('formatExtractedValue', () => {
  it('returns error message for error values', () => {
    const v = makeValue({ is_error: true, error_message: 'Cell not found' });
    expect(formatExtractedValue(v)).toBe('Cell not found');
  });

  it('returns "Error" for error without message', () => {
    const v = makeValue({ is_error: true });
    expect(formatExtractedValue(v)).toBe('Error');
  });

  it('formats numeric values as currency when >= 1000', () => {
    const v = makeValue({ data_type: 'numeric', value_numeric: 15000, field_name: 'PURCHASE_PRICE' });
    const result = formatExtractedValue(v);
    expect(result).toContain('15,000');
  });

  it('formats rate fields as percentage', () => {
    const v = makeValue({ data_type: 'numeric', value_numeric: 0.0525, field_name: 'CAP_RATE' });
    expect(formatExtractedValue(v)).toContain('5.25%');
  });

  it('formats percent fields as percentage', () => {
    const v = makeValue({ data_type: 'numeric', value_numeric: 0.95, field_name: 'OCCUPANCY_PERCENT' });
    expect(formatExtractedValue(v)).toContain('95.00%');
  });

  it('formats small numeric without special formatting', () => {
    const v = makeValue({ data_type: 'numeric', value_numeric: 42.5, field_name: 'UNITS' });
    expect(formatExtractedValue(v)).toBe('42.5');
  });

  it('falls back to value_text for null numeric', () => {
    const v = makeValue({ data_type: 'numeric', value_numeric: undefined, value_text: 'N/A' });
    expect(formatExtractedValue(v)).toBe('N/A');
  });

  it('returns "-" for null numeric and null text', () => {
    const v = makeValue({ data_type: 'numeric', value_numeric: undefined, value_text: undefined });
    expect(formatExtractedValue(v)).toBe('-');
  });

  it('formats date values', () => {
    const v = makeValue({ data_type: 'date', value_date: '2026-03-06' });
    const result = formatExtractedValue(v);
    expect(result).toContain('2026');
    expect(result).toContain('Mar');
  });

  it('falls back to text for null date', () => {
    const v = makeValue({ data_type: 'date', value_date: undefined, value_text: '3/6/2026' });
    expect(formatExtractedValue(v)).toBe('3/6/2026');
  });

  it('formats boolean true as Yes', () => {
    const v = makeValue({ data_type: 'boolean', value_text: 'true' });
    expect(formatExtractedValue(v)).toBe('Yes');
  });

  it('formats boolean false as No', () => {
    const v = makeValue({ data_type: 'boolean', value_text: 'false' });
    expect(formatExtractedValue(v)).toBe('No');
  });

  it('returns text for text data type', () => {
    const v = makeValue({ data_type: 'text', value_text: 'Phoenix, AZ' });
    expect(formatExtractedValue(v)).toBe('Phoenix, AZ');
  });

  it('returns "-" for empty text', () => {
    const v = makeValue({ data_type: 'text', value_text: undefined });
    expect(formatExtractedValue(v)).toBe('-');
  });
});

describe('getExtractionDuration', () => {
  function makeRun(started: string, completed?: string): ExtractionRun {
    return {
      id: 'run-1',
      status: completed ? 'completed' : 'running',
      started_at: started,
      completed_at: completed,
      files_discovered: 10,
      files_processed: completed ? 10 : 5,
      files_failed: 0,
      error_message: undefined,
      trigger_type: 'manual',
    };
  }

  it('formats seconds-only duration', () => {
    const run = makeRun('2026-03-06T10:00:00Z', '2026-03-06T10:00:45Z');
    expect(getExtractionDuration(run)).toBe('45s');
  });

  it('formats minutes and seconds', () => {
    const run = makeRun('2026-03-06T10:00:00Z', '2026-03-06T10:03:15Z');
    expect(getExtractionDuration(run)).toBe('3m 15s');
  });

  it('formats hours and minutes', () => {
    const run = makeRun('2026-03-06T10:00:00Z', '2026-03-06T11:30:00Z');
    expect(getExtractionDuration(run)).toBe('1h 30m');
  });
});
