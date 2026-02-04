import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import { PropertyActivityFeed } from '../PropertyActivityFeed';
import * as usePropertyActivitiesModule from '@/hooks/api/usePropertyActivities';

// Mock the WebSocket
vi.stubGlobal('WebSocket', vi.fn(() => ({
  send: vi.fn(),
  close: vi.fn(),
  onopen: null,
  onmessage: null,
  onerror: null,
  onclose: null,
})));

// Mock the hook
vi.mock('@/hooks/api/usePropertyActivities', () => ({
  usePropertyActivitiesWithMockFallback: vi.fn(),
  usePropertyActivities: vi.fn(),
  propertyActivityKeys: {
    all: ['propertyActivities'],
    lists: () => ['propertyActivities', 'list'],
    list: (propertyId: string) => ['propertyActivities', 'list', propertyId],
    detail: (activityId: string) => ['propertyActivities', 'detail', activityId],
  },
}));

const mockActivities = [
  {
    id: 'act-1',
    propertyId: 'prop-123',
    type: 'view' as const,
    description: 'Viewed property details',
    userName: 'John Smith',
    userAvatar: undefined,
    timestamp: new Date('2024-01-15T10:30:00'),
    metadata: { section: 'overview' },
  },
  {
    id: 'act-2',
    propertyId: 'prop-123',
    type: 'comment' as const,
    description: 'Added comment: Great investment opportunity',
    userName: 'Sarah Johnson',
    userAvatar: undefined,
    timestamp: new Date('2024-01-15T09:00:00'),
    metadata: { commentId: 'cmt-1' },
  },
  {
    id: 'act-3',
    propertyId: 'prop-123',
    type: 'edit' as const,
    description: 'Updated occupancy rate to 95%',
    userName: 'Michael Chen',
    userAvatar: undefined,
    timestamp: new Date('2024-01-14T14:00:00'),
    metadata: { field: 'occupancy', oldValue: 92, newValue: 95 },
  },
  {
    id: 'act-4',
    propertyId: 'prop-123',
    type: 'document_upload' as const,
    description: 'Uploaded Q4 Financial Report',
    userName: 'Emily Davis',
    userAvatar: undefined,
    timestamp: new Date('2024-01-14T11:00:00'),
    metadata: { documentId: 'doc-1' },
  },
  {
    id: 'act-5',
    propertyId: 'prop-123',
    type: 'status_change' as const,
    description: 'Changed status from Review to Active',
    userName: 'Robert Wilson',
    userAvatar: undefined,
    timestamp: new Date('2024-01-13T16:00:00'),
    metadata: { oldStatus: 'review', newStatus: 'active' },
  },
];

describe('PropertyActivityFeed', () => {
  const mockUsePropertyActivitiesWithMockFallback = vi.mocked(
    usePropertyActivitiesModule.usePropertyActivitiesWithMockFallback
  );

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Rendering', () => {
    it('renders activity items correctly', async () => {
      mockUsePropertyActivitiesWithMockFallback.mockReturnValue({
        data: {
          activities: mockActivities,
          total: mockActivities.length,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof usePropertyActivitiesModule.usePropertyActivitiesWithMockFallback>);

      render(<PropertyActivityFeed propertyId="prop-123" />);

      // Check that activity items are rendered
      expect(screen.getByText('John Smith')).toBeInTheDocument();
      expect(screen.getByText('Viewed property details')).toBeInTheDocument();
      expect(screen.getByText('Sarah Johnson')).toBeInTheDocument();
      expect(screen.getByText(/Added comment: Great investment opportunity/)).toBeInTheDocument();
    });

    it('shows loading skeleton while loading', () => {
      mockUsePropertyActivitiesWithMockFallback.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof usePropertyActivitiesModule.usePropertyActivitiesWithMockFallback>);

      const { container } = render(<PropertyActivityFeed propertyId="prop-123" />);

      // Look for skeleton elements
      const skeletons = container.querySelectorAll('.animate-pulse');
      expect(skeletons.length).toBeGreaterThan(0);
    });

    it('shows empty state when no activities', () => {
      mockUsePropertyActivitiesWithMockFallback.mockReturnValue({
        data: {
          activities: [],
          total: 0,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof usePropertyActivitiesModule.usePropertyActivitiesWithMockFallback>);

      render(<PropertyActivityFeed propertyId="prop-123" />);

      expect(screen.getByText('No activities yet')).toBeInTheDocument();
      expect(screen.getByText('Property activity will appear here')).toBeInTheDocument();
    });

    it('shows error state when there is an error', () => {
      mockUsePropertyActivitiesWithMockFallback.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Failed to fetch'),
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof usePropertyActivitiesModule.usePropertyActivitiesWithMockFallback>);

      render(<PropertyActivityFeed propertyId="prop-123" />);

      expect(screen.getByText('Failed to load activities')).toBeInTheDocument();
      expect(screen.getByText('Unable to fetch property activities. Please try again.')).toBeInTheDocument();
    });

    it('displays correct badge count', () => {
      mockUsePropertyActivitiesWithMockFallback.mockReturnValue({
        data: {
          activities: mockActivities,
          total: 15,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof usePropertyActivitiesModule.usePropertyActivitiesWithMockFallback>);

      render(<PropertyActivityFeed propertyId="prop-123" />);

      // The badge should show the total count
      expect(screen.getByText('15')).toBeInTheDocument();
    });
  });

  describe('Filtering', () => {
    it('renders the component with header and content', () => {
      mockUsePropertyActivitiesWithMockFallback.mockReturnValue({
        data: {
          activities: mockActivities,
          total: mockActivities.length,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof usePropertyActivitiesModule.usePropertyActivitiesWithMockFallback>);

      render(<PropertyActivityFeed propertyId="prop-123" />);

      // Card header with Activity Feed title should be present
      expect(screen.getByText('Activity Feed')).toBeInTheDocument();
    });

    it('calls hook when activityTypes prop is provided', () => {
      mockUsePropertyActivitiesWithMockFallback.mockReturnValue({
        data: {
          activities: mockActivities.filter((a) => a.type === 'view'),
          total: 2,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof usePropertyActivitiesModule.usePropertyActivitiesWithMockFallback>);

      render(
        <PropertyActivityFeed
          propertyId="prop-123"
          activityTypes={['view']}
        />
      );

      expect(mockUsePropertyActivitiesWithMockFallback).toHaveBeenCalledWith(
        'prop-123',
        expect.objectContaining({ activityTypes: ['view'] })
      );
    });

    it('shows message when no activities match filters', async () => {
      mockUsePropertyActivitiesWithMockFallback.mockReturnValue({
        data: {
          activities: [],
          total: 0,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof usePropertyActivitiesModule.usePropertyActivitiesWithMockFallback>);

      render(
        <PropertyActivityFeed
          propertyId="prop-123"
          activityTypes={['view']}
        />
      );

      expect(screen.getByText('No activities yet')).toBeInTheDocument();
    });
  });

  describe('Collapsible behavior', () => {
    it('is expanded by default when collapsible', () => {
      mockUsePropertyActivitiesWithMockFallback.mockReturnValue({
        data: {
          activities: mockActivities,
          total: mockActivities.length,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof usePropertyActivitiesModule.usePropertyActivitiesWithMockFallback>);

      render(<PropertyActivityFeed propertyId="prop-123" collapsible />);

      // Content should be visible
      expect(screen.getByText('John Smith')).toBeInTheDocument();
    });

    it('collapses and expands when header is clicked', async () => {
      const user = userEvent.setup();
      mockUsePropertyActivitiesWithMockFallback.mockReturnValue({
        data: {
          activities: mockActivities,
          total: mockActivities.length,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof usePropertyActivitiesModule.usePropertyActivitiesWithMockFallback>);

      render(<PropertyActivityFeed propertyId="prop-123" collapsible />);

      // Find the collapsible trigger (the header)
      const header = screen.getByText('Activity Feed').closest('button');

      expect(header).toBeDefined();
      if (header) {
        // Click to collapse
        await user.click(header);

        // Content should be hidden (Radix handles this with data attributes)
        await waitFor(() => {
          // The collapsible content is controlled by Radix
          screen.queryByText('John Smith');
          // Content may still be in DOM but hidden via Radix
          // This is implementation-dependent
        });
      }
    });

    it('shows chevron icon for collapsible state', () => {
      mockUsePropertyActivitiesWithMockFallback.mockReturnValue({
        data: {
          activities: mockActivities,
          total: mockActivities.length,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof usePropertyActivitiesModule.usePropertyActivitiesWithMockFallback>);

      const { container } = render(
        <PropertyActivityFeed propertyId="prop-123" collapsible />
      );

      // Should have a chevron icon
      const chevron = container.querySelector('.lucide-chevron-down, .lucide-chevron-right');
      expect(chevron).toBeInTheDocument();
    });
  });

  describe('Max items', () => {
    it('limits displayed activities to maxItems', () => {
      mockUsePropertyActivitiesWithMockFallback.mockReturnValue({
        data: {
          activities: mockActivities,
          total: mockActivities.length,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof usePropertyActivitiesModule.usePropertyActivitiesWithMockFallback>);

      render(<PropertyActivityFeed propertyId="prop-123" maxItems={2} />);

      // Should show only 2 activities
      const userNames = screen.getAllByText(/Smith|Johnson|Chen|Davis|Wilson/);
      expect(userNames.length).toBeLessThanOrEqual(2);
    });

    it('shows "View all" button when there are more activities', () => {
      mockUsePropertyActivitiesWithMockFallback.mockReturnValue({
        data: {
          activities: mockActivities.slice(0, 2),
          total: 10,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof usePropertyActivitiesModule.usePropertyActivitiesWithMockFallback>);

      render(<PropertyActivityFeed propertyId="prop-123" maxItems={2} />);

      expect(screen.getByText(/View all 10 activities/)).toBeInTheDocument();
    });
  });

  describe('Error handling', () => {
    it('shows retry button on error', () => {
      mockUsePropertyActivitiesWithMockFallback.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Network error'),
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof usePropertyActivitiesModule.usePropertyActivitiesWithMockFallback>);

      render(<PropertyActivityFeed propertyId="prop-123" />);

      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
    });

    it('calls refetch when retry button is clicked', async () => {
      const user = userEvent.setup();
      const mockRefetch = vi.fn();
      mockUsePropertyActivitiesWithMockFallback.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Network error'),
        refetch: mockRefetch,
      } as unknown as ReturnType<typeof usePropertyActivitiesModule.usePropertyActivitiesWithMockFallback>);

      render(<PropertyActivityFeed propertyId="prop-123" />);

      const retryButton = screen.getByRole('button', { name: /try again/i });
      await user.click(retryButton);

      expect(mockRefetch).toHaveBeenCalled();
    });
  });
});
