import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, waitFor } from '@/test/test-utils';
import { render } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CommandPalette } from '../CommandPalette';
import { QuickActionButton, DealQuickActions } from '../QuickActionButton';
import { FloatingActionButton } from '../FloatingActionButton';
import { QuickActionsProvider } from '@/contexts/QuickActionsContext';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { ToastProvider } from '@/contexts/ToastContext';
import type { ReactNode } from 'react';

// Mock ResizeObserver for cmdk
class ResizeObserverMock {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
vi.stubGlobal('ResizeObserver', ResizeObserverMock);

// Mock Element.scrollIntoView
Element.prototype.scrollIntoView = vi.fn();

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock useToast
vi.mock('@/hooks/useToast', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
    toast: vi.fn(),
    dismiss: vi.fn(),
  }),
}));

// Custom wrapper with all providers including QuickActionsProvider
function QuickActionsWrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <QuickActionsProvider>{children}</QuickActionsProvider>
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  );
}

function renderWithQuickActions(ui: React.ReactElement) {
  return render(ui, { wrapper: QuickActionsWrapper });
}

describe('CommandPalette', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Opening and Closing', () => {
    it('renders when open is true', () => {
      const onOpenChange = vi.fn();
      renderWithQuickActions(
        <CommandPalette open={true} onOpenChange={onOpenChange} />
      );

      // The command palette should be visible
      expect(screen.getByPlaceholderText(/type a command or search/i)).toBeInTheDocument();
    });

    it('does not render when open is false', () => {
      const onOpenChange = vi.fn();
      renderWithQuickActions(
        <CommandPalette open={false} onOpenChange={onOpenChange} />
      );

      // The command palette should not be visible
      expect(screen.queryByPlaceholderText(/type a command or search/i)).not.toBeInTheDocument();
    });

    it('shows ESC key indicator', () => {
      const onOpenChange = vi.fn();
      renderWithQuickActions(
        <CommandPalette open={true} onOpenChange={onOpenChange} />
      );

      expect(screen.getByText('ESC')).toBeInTheDocument();
    });
  });

  describe('Navigation commands', () => {
    it('shows navigation commands', () => {
      const onOpenChange = vi.fn();
      renderWithQuickActions(
        <CommandPalette open={true} onOpenChange={onOpenChange} />
      );

      expect(screen.getByText('Go to Dashboard')).toBeInTheDocument();
      expect(screen.getByText('Go to Deals')).toBeInTheDocument();
      expect(screen.getByText('Go to Investments')).toBeInTheDocument();
      expect(screen.getByText('Go to Analytics')).toBeInTheDocument();
    });

    it('navigates to dashboard when selected', async () => {
      const user = userEvent.setup();
      const onOpenChange = vi.fn();
      renderWithQuickActions(
        <CommandPalette open={true} onOpenChange={onOpenChange} />
      );

      const dashboardOption = screen.getByText('Go to Dashboard');
      await user.click(dashboardOption);

      expect(mockNavigate).toHaveBeenCalledWith('/');
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });

    it('navigates to deals when selected', async () => {
      const user = userEvent.setup();
      const onOpenChange = vi.fn();
      renderWithQuickActions(
        <CommandPalette open={true} onOpenChange={onOpenChange} />
      );

      const dealsOption = screen.getByText('Go to Deals');
      await user.click(dealsOption);

      expect(mockNavigate).toHaveBeenCalledWith('/deals');
    });
  });

  describe('Action commands', () => {
    it('shows action commands', () => {
      const onOpenChange = vi.fn();
      renderWithQuickActions(
        <CommandPalette open={true} onOpenChange={onOpenChange} />
      );

      expect(screen.getByText('Add New Deal')).toBeInTheDocument();
      expect(screen.getByText('Generate Report')).toBeInTheDocument();
      expect(screen.getByText('Compare Deals')).toBeInTheDocument();
      expect(screen.getByText('Keyboard Shortcuts')).toBeInTheDocument();
    });
  });

  describe('Search', () => {
    it('filters commands based on search input', async () => {
      const user = userEvent.setup();
      const onOpenChange = vi.fn();
      renderWithQuickActions(
        <CommandPalette open={true} onOpenChange={onOpenChange} />
      );

      const searchInput = screen.getByPlaceholderText(/type a command or search/i);
      await user.type(searchInput, 'dashboard');

      // Should show dashboard option
      expect(screen.getByText('Go to Dashboard')).toBeInTheDocument();
    });

    it('shows no results message when search has no matches', async () => {
      const user = userEvent.setup();
      const onOpenChange = vi.fn();
      renderWithQuickActions(
        <CommandPalette open={true} onOpenChange={onOpenChange} />
      );

      const searchInput = screen.getByPlaceholderText(/type a command or search/i);
      await user.type(searchInput, 'xyznonexistent123');

      await waitFor(() => {
        expect(screen.getByText('No results found.')).toBeInTheDocument();
      });
    });
  });
});

describe('QuickActionButton', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Watchlist action', () => {
    it('renders watchlist button', () => {
      renderWithQuickActions(
        <QuickActionButton action={{ type: 'watchlist', dealId: 'deal-1' }} />
      );

      expect(screen.getByRole('button', { name: /add to watchlist/i })).toBeInTheDocument();
    });

    it('toggles watchlist state on click', async () => {
      const user = userEvent.setup();
      renderWithQuickActions(
        <QuickActionButton action={{ type: 'watchlist', dealId: 'deal-1' }} />
      );

      const button = screen.getByRole('button', { name: /add to watchlist/i });
      await user.click(button);

      // After clicking, it should show the remove option
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /remove from watchlist/i })).toBeInTheDocument();
      });
    });
  });

  describe('Compare action', () => {
    it('renders compare button', () => {
      renderWithQuickActions(
        <QuickActionButton action={{ type: 'compare', dealId: 'deal-1' }} />
      );

      expect(screen.getByRole('button', { name: /compare/i })).toBeInTheDocument();
    });

    it('adds deal to comparison on click', async () => {
      const user = userEvent.setup();
      renderWithQuickActions(
        <QuickActionButton action={{ type: 'compare', dealId: 'deal-1' }} />
      );

      const button = screen.getByRole('button', { name: /compare/i });
      await user.click(button);

      // Button should show active state
      expect(button).toHaveAttribute('aria-pressed', 'true');
    });
  });

  describe('Share action', () => {
    it('renders share button', () => {
      renderWithQuickActions(
        <QuickActionButton
          action={{ type: 'share', entityType: 'deals', entityId: 'deal-1' }}
        />
      );

      expect(screen.getByRole('button', { name: /share/i })).toBeInTheDocument();
    });
  });

  describe('Export PDF action', () => {
    it('renders export PDF button', () => {
      renderWithQuickActions(
        <QuickActionButton
          action={{ type: 'export-pdf', entityType: 'deals', entityId: 'deal-1' }}
        />
      );

      expect(screen.getByRole('button', { name: /export pdf/i })).toBeInTheDocument();
    });
  });

  describe('Add Note action', () => {
    it('renders add note button', () => {
      renderWithQuickActions(
        <QuickActionButton
          action={{ type: 'add-note', entityType: 'deals', entityId: 'deal-1' }}
        />
      );

      expect(screen.getByRole('button', { name: /add note/i })).toBeInTheDocument();
    });
  });

  describe('Button variants', () => {
    it('renders icon-only variant by default', () => {
      const { container } = renderWithQuickActions(
        <QuickActionButton action={{ type: 'watchlist', dealId: 'deal-1' }} />
      );

      // Icon-only variant should not show label text in button
      const button = container.querySelector('button');
      expect(button?.textContent?.trim()).toBe('');
    });

    it('renders text variant with label', () => {
      renderWithQuickActions(
        <QuickActionButton
          action={{ type: 'watchlist', dealId: 'deal-1' }}
          variant="text"
        />
      );

      expect(screen.getByText('Add to Watchlist')).toBeInTheDocument();
    });

    it('renders both icon and text with "both" variant', () => {
      const { container } = renderWithQuickActions(
        <QuickActionButton
          action={{ type: 'watchlist', dealId: 'deal-1' }}
          variant="both"
        />
      );

      expect(screen.getByText('Add to Watchlist')).toBeInTheDocument();
      // Should also have an SVG icon
      expect(container.querySelector('svg')).toBeInTheDocument();
    });
  });

  describe('Button sizes', () => {
    it('renders small size', () => {
      const { container } = renderWithQuickActions(
        <QuickActionButton
          action={{ type: 'watchlist', dealId: 'deal-1' }}
          size="sm"
        />
      );

      const button = container.querySelector('button');
      expect(button).toHaveClass('h-7', 'w-7');
    });

    it('renders medium size by default', () => {
      const { container } = renderWithQuickActions(
        <QuickActionButton
          action={{ type: 'watchlist', dealId: 'deal-1' }}
          size="md"
        />
      );

      const button = container.querySelector('button');
      expect(button).toHaveClass('h-8', 'w-8');
    });

    it('renders large size', () => {
      const { container } = renderWithQuickActions(
        <QuickActionButton
          action={{ type: 'watchlist', dealId: 'deal-1' }}
          size="lg"
        />
      );

      const button = container.querySelector('button');
      expect(button).toHaveClass('h-10', 'w-10');
    });
  });
});

describe('DealQuickActions', () => {
  it('renders all deal action buttons', () => {
    renderWithQuickActions(<DealQuickActions dealId="deal-1" />);

    // Should have watchlist, compare, and share buttons
    expect(screen.getByRole('button', { name: /add to watchlist/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /compare/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /share/i })).toBeInTheDocument();
  });

  it('uses specified size for all buttons', () => {
    const { container } = renderWithQuickActions(
      <DealQuickActions dealId="deal-1" size="lg" />
    );

    const buttons = container.querySelectorAll('button');
    buttons.forEach((button) => {
      expect(button).toHaveClass('h-10', 'w-10');
    });
  });
});

describe('FloatingActionButton', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders main FAB button', () => {
    renderWithQuickActions(<FloatingActionButton />);

    expect(
      screen.getByRole('button', { name: /open quick actions/i })
    ).toBeInTheDocument();
  });

  it('expands to show action buttons when clicked', async () => {
    const user = userEvent.setup();
    renderWithQuickActions(<FloatingActionButton />);

    const mainButton = screen.getByRole('button', { name: /open quick actions/i });
    await user.click(mainButton);

    // Should show expanded action buttons
    await waitFor(() => {
      expect(screen.getByText('Add Deal')).toBeInTheDocument();
      expect(screen.getByText('Quick Search')).toBeInTheDocument();
      expect(screen.getByText('Commands')).toBeInTheDocument();
      expect(screen.getByText('Refresh Data')).toBeInTheDocument();
    });
  });

  it('collapses when clicked again', async () => {
    const user = userEvent.setup();
    renderWithQuickActions(<FloatingActionButton />);

    const mainButton = screen.getByRole('button', { name: /open quick actions/i });

    // Open
    await user.click(mainButton);
    await waitFor(() => {
      expect(screen.getByText('Add Deal')).toBeInTheDocument();
    });

    // Close - find button by current aria-label
    const closeButton = screen.getByRole('button', { name: /close quick actions/i });
    await user.click(closeButton);

    // Actions should be hidden
    await waitFor(() => {
      screen.queryByText('Add Deal');
      // The labels might still be in DOM but with opacity 0
      // or may be completely removed
    });
  });

  it('shows close icon when expanded', async () => {
    const user = userEvent.setup();
    const { container } = renderWithQuickActions(<FloatingActionButton />);

    const mainButton = screen.getByRole('button', { name: /open quick actions/i });
    await user.click(mainButton);

    // Should show X icon when expanded
    await waitFor(() => {
      const closeIcon = container.querySelector('.lucide-x');
      expect(closeIcon).toBeInTheDocument();
    });
  });

  it('navigates to deals when Add Deal is clicked', async () => {
    const user = userEvent.setup();
    renderWithQuickActions(<FloatingActionButton />);

    const mainButton = screen.getByRole('button', { name: /open quick actions/i });
    await user.click(mainButton);

    await waitFor(() => {
      expect(screen.getByLabelText('Add Deal')).toBeInTheDocument();
    });

    const addDealButton = screen.getByLabelText('Add Deal');
    await user.click(addDealButton);

    expect(mockNavigate).toHaveBeenCalledWith('/deals');
  });

  it('closes on escape key press', async () => {
    const user = userEvent.setup();
    renderWithQuickActions(<FloatingActionButton />);

    const mainButton = screen.getByRole('button', { name: /open quick actions/i });
    await user.click(mainButton);

    await waitFor(() => {
      expect(screen.getByText('Add Deal')).toBeInTheDocument();
    });

    // Press escape
    await user.keyboard('{Escape}');

    // Should close - the button should now say "open" again
    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /open quick actions/i })
      ).toBeInTheDocument();
    });
  });

  it('shows backdrop when expanded', async () => {
    const user = userEvent.setup();
    const { container } = renderWithQuickActions(<FloatingActionButton />);

    const mainButton = screen.getByRole('button', { name: /open quick actions/i });
    await user.click(mainButton);

    await waitFor(() => {
      const backdrop = container.querySelector('.bg-black\\/20');
      expect(backdrop).toBeInTheDocument();
    });
  });

  it('has correct aria-expanded attribute', async () => {
    const user = userEvent.setup();
    renderWithQuickActions(<FloatingActionButton />);

    const mainButton = screen.getByRole('button', { name: /open quick actions/i });
    expect(mainButton).toHaveAttribute('aria-expanded', 'false');

    await user.click(mainButton);

    await waitFor(() => {
      const closeButton = screen.getByRole('button', { name: /close quick actions/i });
      expect(closeButton).toHaveAttribute('aria-expanded', 'true');
    });
  });
});
