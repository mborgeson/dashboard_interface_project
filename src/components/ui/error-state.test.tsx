import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import {
  ErrorState,
  InlineError,
  ErrorAlert
} from './error-state';

describe('ErrorState', () => {
  it('renders with default props', () => {
    render(<ErrorState />);

    expect(screen.getByText('Error')).toBeInTheDocument();
    expect(screen.getByText('An unexpected error occurred. Please try again.')).toBeInTheDocument();
  });

  it('renders with custom title and description', () => {
    render(
      <ErrorState
        title="Custom Error"
        description="Something went wrong"
      />
    );

    expect(screen.getByText('Custom Error')).toBeInTheDocument();
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('renders error variant styling', () => {
    const { container } = render(<ErrorState variant="error" />);

    // Error icon should have destructive color class
    const icon = container.querySelector('.text-destructive');
    expect(icon).toBeInTheDocument();
  });

  it('renders warning variant with correct styling', () => {
    const { container } = render(<ErrorState variant="warning" />);

    // Warning default title
    expect(screen.getByText('Warning')).toBeInTheDocument();

    // Warning icon color
    const icon = container.querySelector('[class*="text-yellow"]');
    expect(icon).toBeInTheDocument();
  });

  it('renders info variant with correct styling', () => {
    const { container } = render(<ErrorState variant="info" />);

    expect(screen.getByText('Information')).toBeInTheDocument();

    // Info icon color
    const icon = container.querySelector('[class*="text-blue"]');
    expect(icon).toBeInTheDocument();
  });

  it('renders retry button when onRetry is provided', async () => {
    const user = userEvent.setup();
    const mockRetry = vi.fn();

    render(<ErrorState onRetry={mockRetry} />);

    const retryButton = screen.getByRole('button', { name: /try again/i });
    expect(retryButton).toBeInTheDocument();

    await user.click(retryButton);
    expect(mockRetry).toHaveBeenCalledTimes(1);
  });

  it('renders custom retry label', () => {
    render(<ErrorState onRetry={() => {}} retryLabel="Reload Page" />);

    expect(screen.getByRole('button', { name: /reload page/i })).toBeInTheDocument();
  });

  it('does not render retry button when onRetry is not provided', () => {
    render(<ErrorState />);

    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<ErrorState className="custom-error-class" />);

    expect(container.querySelector('.custom-error-class')).toBeInTheDocument();
  });

  it('hides icon when showIcon is false', () => {
    const { container } = render(<ErrorState showIcon={false} />);

    // Icon should not be present
    const iconContainer = container.querySelector('.text-destructive');
    expect(iconContainer).not.toBeInTheDocument();
  });

  it('renders fullScreen layout', () => {
    const { container } = render(<ErrorState fullScreen={true} />);

    expect(container.querySelector('.min-h-screen')).toBeInTheDocument();
  });
});

describe('InlineError', () => {
  it('renders with message', () => {
    render(<InlineError message="This is an error" />);

    expect(screen.getByText('This is an error')).toBeInTheDocument();
  });

  it('renders error variant by default', () => {
    const { container } = render(<InlineError message="Error" />);

    expect(container.querySelector('.border-destructive\\/50')).toBeInTheDocument();
  });

  it('renders warning variant', () => {
    const { container } = render(<InlineError message="Warning" variant="warning" />);

    expect(container.querySelector('[class*="border-yellow"]')).toBeInTheDocument();
  });

  it('renders info variant', () => {
    const { container } = render(<InlineError message="Info" variant="info" />);

    expect(container.querySelector('[class*="border-blue"]')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <InlineError message="Error" className="custom-inline-class" />
    );

    expect(container.querySelector('.custom-inline-class')).toBeInTheDocument();
  });
});

describe('ErrorAlert', () => {
  it('renders with title', () => {
    render(<ErrorAlert title="Alert Title" />);

    expect(screen.getByText('Alert Title')).toBeInTheDocument();
  });

  it('renders with message', () => {
    render(<ErrorAlert title="Alert" message="Alert message content" />);

    expect(screen.getByText('Alert message content')).toBeInTheDocument();
  });

  it('renders dismiss button when onDismiss is provided', async () => {
    const user = userEvent.setup();
    const mockDismiss = vi.fn();

    render(<ErrorAlert title="Alert" onDismiss={mockDismiss} />);

    const dismissButton = screen.getByLabelText('Dismiss');
    expect(dismissButton).toBeInTheDocument();

    await user.click(dismissButton);
    expect(mockDismiss).toHaveBeenCalledTimes(1);
  });

  it('does not render dismiss button when onDismiss is not provided', () => {
    render(<ErrorAlert title="Alert" />);

    expect(screen.queryByLabelText('Dismiss')).not.toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <ErrorAlert title="Alert" className="custom-alert-class" />
    );

    expect(container.querySelector('.custom-alert-class')).toBeInTheDocument();
  });

  it('has destructive styling', () => {
    const { container } = render(<ErrorAlert title="Alert" />);

    expect(container.querySelector('.border-destructive\\/50')).toBeInTheDocument();
    expect(container.querySelector('.bg-destructive\\/5')).toBeInTheDocument();
  });
});
