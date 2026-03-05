import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import { ExtractionDashboard } from '../ExtractionDashboard';
import { formatExtractedValue, getExtractionDuration } from '../hooks/useExtraction';
import type { ExtractedValue, ExtractionRun } from '@/types/extraction';

// -- Router mock --
const mockNavigate = vi.fn();
let mockParams: Record<string, string> = {};
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate, useParams: () => mockParams };
});

// -- Hook mocks --
const mockRefetch = vi.fn();
const mockStart = vi.fn().mockResolvedValue({ id: 'run-1' });
const mockCancel = vi.fn().mockResolvedValue(true);

const completedRun = {
  id: 'run-1', started_at: '2026-03-01T09:00:00Z', completed_at: '2026-03-01T09:05:00Z',
  status: 'completed' as const, trigger_type: 'manual' as const,
  files_discovered: 10, files_processed: 9, files_failed: 1,
};

vi.mock('../hooks/useExtraction', async () => {
  const actual = await vi.importActual('../hooks/useExtraction');
  return {
    ...actual,
    useExtractionStatus: vi.fn(() => ({
      status: null, currentRun: null, lastRun: completedRun,
      stats: { total_runs: 5, successful_runs: 4, failed_runs: 1, total_properties: 20, total_fields_extracted: 1500 },
      isLoading: false, error: null, refetch: mockRefetch,
    })),
    useStartExtraction: vi.fn(() => ({
      startExtraction: mockStart, cancelExtraction: mockCancel, isLoading: false, error: null,
    })),
    useExtractionHistory: vi.fn(() => ({
      runs: [completedRun], total: 1, page: 1, pageSize: 5,
      isLoading: false, error: null, refetch: mockRefetch,
    })),
    useExtractedProperties: vi.fn(() => ({
      properties: [
        { property_name: 'Sunset Apartments', total_fields: 45, error_count: 2, categories: ['Income', 'Expenses'], last_extracted_at: '2026-03-01T09:05:00Z' },
        { property_name: 'Oak Ridge Plaza', total_fields: 38, error_count: 0, categories: ['Income'], last_extracted_at: '2026-03-01T09:05:00Z' },
      ],
      total: 2, isLoading: false, error: null, refetch: mockRefetch,
    })),
    useExtractedPropertyValues: vi.fn(() => ({
      propertyName: 'Sunset Apartments',
      values: [
        { id: 'v1', extraction_run_id: 'run-1', property_name: 'Sunset Apartments', field_name: 'NOI', field_category: 'Income', sheet_name: 'Sheet1', cell_address: 'B5', value_numeric: 250000, data_type: 'numeric' as const, is_error: false, extracted_at: '2026-03-01T09:05:00Z' },
      ],
      groupedValues: [{ category: 'Income', values: [], errorCount: 0 }],
      categories: ['Income'], total: 1, isLoading: false, error: null, refetch: mockRefetch,
    })),
  };
});

vi.mock('../components/GroupPipelineTab', () => ({
  GroupPipelineTab: () => <div data-testid="group-pipeline-tab">Group Pipeline Content</div>,
}));

beforeEach(() => { vi.clearAllMocks(); mockParams = {}; });

// -- Dashboard rendering --
describe('ExtractionDashboard', () => {
  describe('main dashboard view', () => {
    it('renders page heading and description', () => {
      render(<ExtractionDashboard />);
      expect(screen.getByText('UW Model Extraction')).toBeInTheDocument();
      expect(screen.getByText(/Extract and view underwriting model data/)).toBeInTheDocument();
    });

    it('renders both tab buttons', () => {
      render(<ExtractionDashboard />);
      expect(screen.getByRole('button', { name: 'Quick Extraction' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Group Pipeline' })).toBeInTheDocument();
    });

    it('shows Quick Extraction tab content by default', () => {
      render(<ExtractionDashboard />);
      expect(screen.getByText('Extraction Status')).toBeInTheDocument();
      expect(screen.getAllByText('Properties').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('Extraction History')).toBeInTheDocument();
    });

    it('does not show Group Pipeline content by default', () => {
      render(<ExtractionDashboard />);
      expect(screen.queryByTestId('group-pipeline-tab')).not.toBeInTheDocument();
    });
  });

  describe('tab switching', () => {
    it('switches to Group Pipeline tab on click', async () => {
      const user = userEvent.setup();
      render(<ExtractionDashboard />);
      await user.click(screen.getByRole('button', { name: 'Group Pipeline' }));
      expect(screen.getByTestId('group-pipeline-tab')).toBeInTheDocument();
      expect(screen.queryByText('Extraction Status')).not.toBeInTheDocument();
    });

    it('switches back to Quick Extraction tab', async () => {
      const user = userEvent.setup();
      render(<ExtractionDashboard />);
      await user.click(screen.getByRole('button', { name: 'Group Pipeline' }));
      await user.click(screen.getByRole('button', { name: 'Quick Extraction' }));
      expect(screen.getByText('Extraction Status')).toBeInTheDocument();
      expect(screen.queryByTestId('group-pipeline-tab')).not.toBeInTheDocument();
    });
  });

  describe('property detail view', () => {
    it('renders detail view when propertyName param is present', () => {
      mockParams = { propertyName: 'Sunset%20Apartments' };
      render(<ExtractionDashboard />);
      expect(screen.getByText('Extracted Data')).toBeInTheDocument();
      expect(screen.getByText(/View extracted underwriting model data for Sunset Apartments/)).toBeInTheDocument();
    });

    it('does not render tabs in detail view', () => {
      mockParams = { propertyName: 'Sunset%20Apartments' };
      render(<ExtractionDashboard />);
      expect(screen.queryByRole('button', { name: 'Quick Extraction' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Group Pipeline' })).not.toBeInTheDocument();
    });
  });

  describe('navigation', () => {
    it('navigates to property detail when a property is clicked', async () => {
      const user = userEvent.setup();
      render(<ExtractionDashboard />);
      await user.click(screen.getByText('Sunset Apartments'));
      expect(mockNavigate).toHaveBeenCalledWith('/extraction/Sunset%20Apartments');
    });
  });

  describe('ExtractionStatus content', () => {
    it('displays run stats labels', () => {
      render(<ExtractionDashboard />);
      expect(screen.getByText('Discovered')).toBeInTheDocument();
      expect(screen.getByText('Processed')).toBeInTheDocument();
      expect(screen.getByText('Failed')).toBeInTheDocument();
    });

    it('displays overall stats', () => {
      render(<ExtractionDashboard />);
      expect(screen.getByText('Total Runs')).toBeInTheDocument();
      expect(screen.getByText('1,500')).toBeInTheDocument();
    });

    it('shows Start Extraction button when idle', () => {
      render(<ExtractionDashboard />);
      expect(screen.getByRole('button', { name: /Start Extraction/i })).toBeInTheDocument();
    });
  });

  describe('ExtractionHistory content', () => {
    it('displays history table headers', () => {
      render(<ExtractionDashboard />);
      expect(screen.getAllByText('Duration').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('Files')).toBeInTheDocument();
      expect(screen.getByText('Trigger')).toBeInTheDocument();
      expect(screen.getByText('Success Rate')).toBeInTheDocument();
    });

    it('renders run rows with status badge', () => {
      render(<ExtractionDashboard />);
      expect(screen.getByText('completed')).toBeInTheDocument();
    });
  });

  describe('ExtractedPropertyList content', () => {
    it('renders property names', () => {
      render(<ExtractionDashboard />);
      expect(screen.getByText('Sunset Apartments')).toBeInTheDocument();
      expect(screen.getByText('Oak Ridge Plaza')).toBeInTheDocument();
    });

    it('shows error badge for properties with errors', () => {
      render(<ExtractionDashboard />);
      expect(screen.getByText('2 errors')).toBeInTheDocument();
    });

    it('shows total count badge', () => {
      render(<ExtractionDashboard />);
      expect(screen.getByText('2')).toBeInTheDocument();
    });
  });
});

// -- Utility function tests --
describe('formatExtractedValue', () => {
  const base: ExtractedValue = {
    id: 'v1', extraction_run_id: 'run-1', property_name: 'Test', field_name: 'Test Field',
    field_category: 'General', sheet_name: 'Sheet1', cell_address: 'A1',
    data_type: 'text', is_error: false, extracted_at: '2026-03-01T09:00:00Z',
  };

  it('returns error message for error values', () => {
    expect(formatExtractedValue({ ...base, is_error: true, error_message: 'Cell not found' })).toBe('Cell not found');
  });

  it('returns "Error" when is_error but no message', () => {
    expect(formatExtractedValue({ ...base, is_error: true })).toBe('Error');
  });

  it('formats large numeric as USD currency', () => {
    expect(formatExtractedValue({ ...base, data_type: 'numeric', value_numeric: 1500000 })).toBe('$1,500,000');
  });

  it('formats rate-like field name as percentage', () => {
    expect(formatExtractedValue({ ...base, data_type: 'numeric', field_name: 'Cap Rate', value_numeric: 0.055 })).toBe('5.50%');
  });

  it('formats small numeric without currency', () => {
    expect(formatExtractedValue({ ...base, data_type: 'numeric', value_numeric: 42 })).toBe('42');
  });

  it('falls back to value_text for numeric with no numeric value', () => {
    expect(formatExtractedValue({ ...base, data_type: 'numeric', value_text: 'N/A' })).toBe('N/A');
  });

  it('formats date values', () => {
    const result = formatExtractedValue({ ...base, data_type: 'date', value_date: '2026-06-15T12:00:00Z' });
    expect(result).toContain('2026');
    expect(result).toContain('Jun');
    expect(result).toContain('15');
  });

  it('returns "Yes" / "No" for boolean', () => {
    expect(formatExtractedValue({ ...base, data_type: 'boolean', value_text: 'true' })).toBe('Yes');
    expect(formatExtractedValue({ ...base, data_type: 'boolean', value_text: 'false' })).toBe('No');
  });

  it('returns value_text for text type, or "-" if absent', () => {
    expect(formatExtractedValue({ ...base, data_type: 'text', value_text: 'Hello' })).toBe('Hello');
    expect(formatExtractedValue({ ...base, data_type: 'text' })).toBe('-');
  });
});

describe('getExtractionDuration', () => {
  const makeRun = (start: string, end?: string): ExtractionRun => ({
    id: 'r1', started_at: start, completed_at: end, status: end ? 'completed' : 'running',
    trigger_type: 'manual', files_discovered: 10, files_processed: 10, files_failed: 0,
  });

  it('returns seconds for short durations', () => {
    expect(getExtractionDuration(makeRun('2026-03-01T09:00:00Z', '2026-03-01T09:00:45Z'))).toBe('45s');
  });

  it('returns minutes and seconds for medium durations', () => {
    expect(getExtractionDuration(makeRun('2026-03-01T09:00:00Z', '2026-03-01T09:05:30Z'))).toBe('5m 30s');
  });

  it('returns hours and minutes for long durations', () => {
    expect(getExtractionDuration(makeRun('2026-03-01T09:00:00Z', '2026-03-01T11:30:00Z'))).toBe('2h 30m');
  });

  it('calculates from now when run has no completed_at', () => {
    const result = getExtractionDuration(makeRun(new Date(Date.now() - 5000).toISOString()));
    expect(result).toMatch(/^\d+s$/);
  });
});
