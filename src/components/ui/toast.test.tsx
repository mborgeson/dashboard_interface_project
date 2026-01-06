import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import { Toast } from './toast';
import type { Toast as ToastType } from '@/types/notification';

// Mock timers for testing auto-dismiss
beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

const createMockToast = (overrides?: Partial<ToastType>): ToastType => ({
  id: 'test-toast-1',
  type: 'success',
  title: 'Test Toast',
  description: undefined,
  duration: 5000,
  action: undefined,
  ...overrides,
});

describe('Toast', () => {
  it('renders with title', () => {
    const mockRemove = vi.fn();
    const toast = createMockToast({ title: 'Success Message' });

    render(<Toast toast={toast} onRemove={mockRemove} />);

    expect(screen.getByText('Success Message')).toBeInTheDocument();
  });

  it('renders with description when provided', () => {
    const mockRemove = vi.fn();
    const toast = createMockToast({
      title: 'Test Title',
      description: 'Test Description'
    });

    render(<Toast toast={toast} onRemove={mockRemove} />);

    expect(screen.getByText('Test Description')).toBeInTheDocument();
  });

  it('renders success variant with correct icon', () => {
    const mockRemove = vi.fn();
    const toast = createMockToast({ type: 'success' });

    const { container } = render(<Toast toast={toast} onRemove={mockRemove} />);

    // Success variant should have green colors
    expect(container.querySelector('.bg-green-50')).toBeInTheDocument();
    expect(container.querySelector('.border-green-500')).toBeInTheDocument();
  });

  it('renders error variant with correct styling', () => {
    const mockRemove = vi.fn();
    const toast = createMockToast({ type: 'error' });

    const { container } = render(<Toast toast={toast} onRemove={mockRemove} />);

    // Error variant should have red colors
    expect(container.querySelector('.bg-red-50')).toBeInTheDocument();
    expect(container.querySelector('.border-red-500')).toBeInTheDocument();
  });

  it('renders warning variant with correct styling', () => {
    const mockRemove = vi.fn();
    const toast = createMockToast({ type: 'warning' });

    const { container } = render(<Toast toast={toast} onRemove={mockRemove} />);

    // Warning variant should have amber colors
    expect(container.querySelector('.bg-amber-50')).toBeInTheDocument();
    expect(container.querySelector('.border-amber-500')).toBeInTheDocument();
  });

  it('renders info variant with correct styling', () => {
    const mockRemove = vi.fn();
    const toast = createMockToast({ type: 'info' });

    const { container } = render(<Toast toast={toast} onRemove={mockRemove} />);

    // Info variant should have blue colors
    expect(container.querySelector('.bg-blue-50')).toBeInTheDocument();
    expect(container.querySelector('.border-blue-500')).toBeInTheDocument();
  });

  it('calls onRemove when close button is clicked', async () => {
    vi.useRealTimers(); // Need real timers for user interaction
    const user = userEvent.setup();
    const mockRemove = vi.fn();
    const toast = createMockToast();

    render(<Toast toast={toast} onRemove={mockRemove} />);

    const closeButton = screen.getByLabelText('Close notification');
    await user.click(closeButton);

    // Wait for exit animation (300ms)
    await new Promise(resolve => setTimeout(resolve, 350));

    expect(mockRemove).toHaveBeenCalledWith('test-toast-1');
  });

  it('renders action button when action is provided', () => {
    const mockRemove = vi.fn();
    const mockAction = vi.fn();
    const toast = createMockToast({
      action: {
        label: 'Undo',
        onClick: mockAction,
      },
    });

    render(<Toast toast={toast} onRemove={mockRemove} />);

    expect(screen.getByText('Undo')).toBeInTheDocument();
  });

  it('calls action onClick when action button is clicked', async () => {
    vi.useRealTimers();
    const user = userEvent.setup();
    const mockRemove = vi.fn();
    const mockAction = vi.fn();
    const toast = createMockToast({
      action: {
        label: 'Undo',
        onClick: mockAction,
      },
    });

    render(<Toast toast={toast} onRemove={mockRemove} />);

    await user.click(screen.getByText('Undo'));

    expect(mockAction).toHaveBeenCalledTimes(1);
  });

  it('renders progress bar when duration is positive', () => {
    const mockRemove = vi.fn();
    const toast = createMockToast({ duration: 5000 });

    const { container } = render(<Toast toast={toast} onRemove={mockRemove} />);

    // Progress bar container (h-1)
    const progressContainer = container.querySelector('.h-1.bg-black\\/10');
    expect(progressContainer).toBeInTheDocument();
  });

  it('hides progress bar when duration is 0 or negative', () => {
    const mockRemove = vi.fn();
    const toast = createMockToast({ duration: 0 });

    const { container } = render(<Toast toast={toast} onRemove={mockRemove} />);

    // Progress bar should not be present
    const progressContainer = container.querySelector('.h-1.bg-black\\/10');
    expect(progressContainer).not.toBeInTheDocument();
  });

  it('displays correctly without description', () => {
    const mockRemove = vi.fn();
    const toast = createMockToast({
      title: 'Title Only',
      description: undefined
    });

    render(<Toast toast={toast} onRemove={mockRemove} />);

    expect(screen.getByText('Title Only')).toBeInTheDocument();
    // Description should not be rendered
    expect(screen.queryByText('undefined')).not.toBeInTheDocument();
  });

  it('has correct aria-label on close button', () => {
    const mockRemove = vi.fn();
    const toast = createMockToast();

    render(<Toast toast={toast} onRemove={mockRemove} />);

    const closeButton = screen.getByLabelText('Close notification');
    expect(closeButton).toBeInTheDocument();
  });
});
