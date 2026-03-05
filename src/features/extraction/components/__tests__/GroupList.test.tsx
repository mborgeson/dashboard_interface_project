import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@/test/test-utils';
import { GroupList } from '../GroupList';
import type { GroupSummary } from '@/types/grouping';

// ---------------------------------------------------------------------------
// Mock the hooks used by GroupList
// ---------------------------------------------------------------------------

const mockRefetch = vi.fn();
const mockRunExtraction = vi.fn().mockResolvedValue(null);
const mockApproveGroup = vi.fn().mockResolvedValue(null);

const defaultUseGroupsReturn = {
  groups: [] as GroupSummary[],
  totalGroups: 0,
  totalUngrouped: 0,
  totalEmptyTemplates: 0,
  isLoading: false,
  error: null as Error | null,
  refetch: mockRefetch,
};

vi.mock('../../hooks/useGroupPipeline', () => ({
  useGroups: vi.fn(() => defaultUseGroupsReturn),
  useRunGroupExtraction: vi.fn(() => ({
    mutate: mockRunExtraction,
    isLoading: false,
    error: null,
  })),
  useApproveGroup: vi.fn(() => ({
    mutate: mockApproveGroup,
    isLoading: false,
    error: null,
  })),
}));

import { useGroups } from '../../hooks/useGroupPipeline';

const mockUseGroups = vi.mocked(useGroups);

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeGroup(overrides: Partial<GroupSummary> = {}): GroupSummary {
  return {
    group_name: 'Standard Template v3',
    file_count: 12,
    structural_overlap: 91.5,
    era: '2020-2024',
    sub_variant_count: 3,
    ...overrides,
  };
}

const sampleGroups: GroupSummary[] = [
  makeGroup({ group_name: 'Alpha Template', file_count: 10, structural_overlap: 95.0, era: '2022-2024', sub_variant_count: 2 }),
  makeGroup({ group_name: 'Beta Template', file_count: 5, structural_overlap: 72.1, era: '2018-2020', sub_variant_count: 1 }),
  makeGroup({ group_name: 'Gamma Template', file_count: 8, structural_overlap: 55.0, era: '2015-2018', sub_variant_count: 4 }),
];

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('GroupList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseGroups.mockReturnValue({ ...defaultUseGroupsReturn });
  });

  describe('loading state', () => {
    it('shows a loading spinner when isLoading is true', () => {
      mockUseGroups.mockReturnValue({ ...defaultUseGroupsReturn, isLoading: true });

      const { container } = render(<GroupList onGroupSelect={vi.fn()} />);

      const spinner = container.querySelector('.animate-spin');
      expect(spinner).toBeInTheDocument();
    });
  });

  describe('error state', () => {
    it('shows error message and retry button when there is an error', () => {
      mockUseGroups.mockReturnValue({
        ...defaultUseGroupsReturn,
        error: new Error('Failed to load groups'),
      });

      render(<GroupList onGroupSelect={vi.fn()} />);

      expect(screen.getByText('Failed to load groups')).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });

    it('calls refetch when retry button is clicked', () => {
      mockUseGroups.mockReturnValue({
        ...defaultUseGroupsReturn,
        error: new Error('Connection lost'),
      });

      render(<GroupList onGroupSelect={vi.fn()} />);

      fireEvent.click(screen.getByText('Retry'));
      expect(mockRefetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('empty state', () => {
    it('shows empty state message when no groups exist', () => {
      mockUseGroups.mockReturnValue({ ...defaultUseGroupsReturn, groups: [] });

      render(<GroupList onGroupSelect={vi.fn()} />);

      expect(
        screen.getByText('No groups yet. Run Discovery & Fingerprint first.'),
      ).toBeInTheDocument();
    });
  });

  describe('populated table', () => {
    beforeEach(() => {
      mockUseGroups.mockReturnValue({
        ...defaultUseGroupsReturn,
        groups: sampleGroups,
        totalGroups: 3,
        totalUngrouped: 5,
      });
    });

    it('renders group names in the table', () => {
      render(<GroupList onGroupSelect={vi.fn()} />);

      expect(screen.getByText('Alpha Template')).toBeInTheDocument();
      expect(screen.getByText('Beta Template')).toBeInTheDocument();
      expect(screen.getByText('Gamma Template')).toBeInTheDocument();
    });

    it('shows file count column values', () => {
      render(<GroupList onGroupSelect={vi.fn()} />);

      expect(screen.getByText('10')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument();
      expect(screen.getByText('8')).toBeInTheDocument();
    });

    it('shows era badge values', () => {
      render(<GroupList onGroupSelect={vi.fn()} />);

      expect(screen.getByText('2022-2024')).toBeInTheDocument();
      expect(screen.getByText('2018-2020')).toBeInTheDocument();
      expect(screen.getByText('2015-2018')).toBeInTheDocument();
    });

    it('shows structural overlap percentages', () => {
      render(<GroupList onGroupSelect={vi.fn()} />);

      expect(screen.getByText('95.0%')).toBeInTheDocument();
      expect(screen.getByText('72.1%')).toBeInTheDocument();
      expect(screen.getByText('55.0%')).toBeInTheDocument();
    });

    it('shows sub-variant count column', () => {
      render(<GroupList onGroupSelect={vi.fn()} />);

      expect(screen.getByText('2')).toBeInTheDocument();
      expect(screen.getByText('1')).toBeInTheDocument();
      expect(screen.getByText('4')).toBeInTheDocument();
    });

    it('displays total groups count in header', () => {
      render(<GroupList onGroupSelect={vi.fn()} />);

      expect(screen.getByText('3 groups')).toBeInTheDocument();
    });

    it('displays ungrouped count badge when ungrouped > 0', () => {
      render(<GroupList onGroupSelect={vi.fn()} />);

      expect(screen.getByText('5 ungrouped')).toBeInTheDocument();
    });

    it('renders column headers', () => {
      render(<GroupList onGroupSelect={vi.fn()} />);

      expect(screen.getByText('Group Name')).toBeInTheDocument();
      expect(screen.getByText('Files')).toBeInTheDocument();
      expect(screen.getByText('Era')).toBeInTheDocument();
      expect(screen.getByText('Overlap')).toBeInTheDocument();
      expect(screen.getByText('Sub-variants')).toBeInTheDocument();
      expect(screen.getByText('Actions')).toBeInTheDocument();
    });
  });

  describe('group selection', () => {
    it('calls onGroupSelect when a group name link is clicked', () => {
      mockUseGroups.mockReturnValue({
        ...defaultUseGroupsReturn,
        groups: sampleGroups,
        totalGroups: 3,
      });

      const onGroupSelect = vi.fn();
      render(<GroupList onGroupSelect={onGroupSelect} />);

      fireEvent.click(screen.getByText('Alpha Template'));
      expect(onGroupSelect).toHaveBeenCalledWith('Alpha Template');
    });

    it('calls onGroupSelect when the view (eye) button is clicked', () => {
      mockUseGroups.mockReturnValue({
        ...defaultUseGroupsReturn,
        groups: [makeGroup({ group_name: 'Test Group' })],
        totalGroups: 1,
      });

      const onGroupSelect = vi.fn();
      render(<GroupList onGroupSelect={onGroupSelect} />);

      // The View button has title="View"
      const viewButton = screen.getByTitle('View');
      fireEvent.click(viewButton);
      expect(onGroupSelect).toHaveBeenCalledWith('Test Group');
    });
  });

  describe('overlap color coding', () => {
    it('applies green color for overlap >= 90', () => {
      mockUseGroups.mockReturnValue({
        ...defaultUseGroupsReturn,
        groups: [makeGroup({ group_name: 'High Overlap', structural_overlap: 95.0 })],
        totalGroups: 1,
      });

      const { container } = render(<GroupList onGroupSelect={vi.fn()} />);

      const greenEl = container.querySelector('.text-green-600');
      expect(greenEl).toBeInTheDocument();
      expect(greenEl?.textContent).toBe('95.0%');
    });

    it('applies amber color for overlap between 70 and 90', () => {
      mockUseGroups.mockReturnValue({
        ...defaultUseGroupsReturn,
        groups: [makeGroup({ group_name: 'Mid Overlap', structural_overlap: 78.0 })],
        totalGroups: 1,
      });

      const { container } = render(<GroupList onGroupSelect={vi.fn()} />);

      const amberEl = container.querySelector('.text-amber-600');
      expect(amberEl).toBeInTheDocument();
      expect(amberEl?.textContent).toBe('78.0%');
    });

    it('applies red color for overlap below 70', () => {
      mockUseGroups.mockReturnValue({
        ...defaultUseGroupsReturn,
        groups: [makeGroup({ group_name: 'Low Overlap', structural_overlap: 55.0 })],
        totalGroups: 1,
      });

      const { container } = render(<GroupList onGroupSelect={vi.fn()} />);

      const redEl = container.querySelector('.text-red-600');
      expect(redEl).toBeInTheDocument();
      expect(redEl?.textContent).toBe('55.0%');
    });
  });

  describe('ungrouped badge visibility', () => {
    it('does not show ungrouped badge when totalUngrouped is 0', () => {
      mockUseGroups.mockReturnValue({
        ...defaultUseGroupsReturn,
        groups: sampleGroups,
        totalGroups: 3,
        totalUngrouped: 0,
      });

      render(<GroupList onGroupSelect={vi.fn()} />);

      expect(screen.queryByText(/ungrouped/)).not.toBeInTheDocument();
    });
  });
});
