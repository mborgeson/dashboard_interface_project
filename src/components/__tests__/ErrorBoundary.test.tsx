import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorBoundary } from '../ErrorBoundary';
import { FeatureErrorBoundary } from '../FeatureErrorBoundary';

// Suppress console.error from React error boundary logging
beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

function ThrowingChild({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error('Test error message');
  return <div>Child content</div>;
}

describe('ErrorBoundary', () => {
  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <div>Hello</div>
      </ErrorBoundary>
    );
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  it('catches errors and shows fallback UI', () => {
    render(
      <ErrorBoundary>
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(screen.getByText('Something Went Wrong')).toBeInTheDocument();
    expect(screen.getByText(/Test error message/)).toBeInTheDocument();
  });

  it('renders static fallback when provided as ReactNode', () => {
    render(
      <ErrorBoundary fallback={<div>Custom fallback</div>}>
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(screen.getByText('Custom fallback')).toBeInTheDocument();
    expect(screen.queryByText('Something Went Wrong')).not.toBeInTheDocument();
  });

  it('renders fallback from render function with error and reset', () => {
    render(
      <ErrorBoundary
        fallback={(error, reset) => (
          <div>
            <span>Render fn: {error.message}</span>
            <button onClick={reset}>Reset</button>
          </div>
        )}
      >
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(screen.getByText('Render fn: Test error message')).toBeInTheDocument();
    expect(screen.getByText('Reset')).toBeInTheDocument();
  });

  it('calls onError callback when error is caught', () => {
    const onError = vi.fn();
    render(
      <ErrorBoundary onError={onError}>
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({ message: 'Test error message' }),
      expect.objectContaining({ componentStack: expect.any(String) })
    );
  });

  it('resets error state when "Try Again" is clicked', () => {
    // Use a ref-like mechanism to control whether the child throws
    let shouldThrow = true;

    function ConditionalThrow() {
      if (shouldThrow) throw new Error('Transient error');
      return <div>Recovered</div>;
    }

    const { rerender } = render(
      <ErrorBoundary>
        <ConditionalThrow />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something Went Wrong')).toBeInTheDocument();

    // Stop throwing, then click Try Again
    shouldThrow = false;
    fireEvent.click(screen.getByText('Try Again'));

    // After reset the boundary should re-render children successfully
    rerender(
      <ErrorBoundary>
        <ConditionalThrow />
      </ErrorBoundary>
    );

    expect(screen.getByText('Recovered')).toBeInTheDocument();
    expect(screen.queryByText('Something Went Wrong')).not.toBeInTheDocument();
  });

  it('shows Reload Page button', () => {
    render(
      <ErrorBoundary>
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(screen.getByText('Reload Page')).toBeInTheDocument();
  });
});

describe('FeatureErrorBoundary', () => {
  it('renders children when no error', () => {
    render(
      <FeatureErrorBoundary featureName="Analytics">
        <div>Feature content</div>
      </FeatureErrorBoundary>
    );
    expect(screen.getByText('Feature content')).toBeInTheDocument();
  });

  it('shows feature-specific error card on crash', () => {
    render(
      <FeatureErrorBoundary featureName="Analytics">
        <ThrowingChild shouldThrow={true} />
      </FeatureErrorBoundary>
    );
    expect(screen.getByText('Analytics failed to load')).toBeInTheDocument();
    expect(screen.getByText(/Something went wrong while rendering Analytics/)).toBeInTheDocument();
    expect(screen.getByText(/Test error message/)).toBeInTheDocument();
    expect(screen.getByText('Try Again')).toBeInTheDocument();
  });

  it('does not show full-page error UI (uses card instead)', () => {
    render(
      <FeatureErrorBoundary featureName="Deals">
        <ThrowingChild shouldThrow={true} />
      </FeatureErrorBoundary>
    );
    // Should NOT show the full-page "Something Went Wrong" from the base boundary
    expect(screen.queryByText('Something Went Wrong')).not.toBeInTheDocument();
    // Should show the feature-specific message
    expect(screen.getByText('Deals failed to load')).toBeInTheDocument();
  });
});
