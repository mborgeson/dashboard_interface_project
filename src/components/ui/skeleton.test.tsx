import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { Skeleton } from './skeleton';

describe('Skeleton', () => {
  it('renders with default classes', () => {
    render(<Skeleton data-testid="skeleton" />);
    const skeleton = screen.getByTestId('skeleton');
    expect(skeleton).toBeInTheDocument();
    expect(skeleton).toHaveClass('animate-pulse');
  });

  it('applies custom className', () => {
    render(<Skeleton className="h-10 w-full" data-testid="skeleton" />);
    const skeleton = screen.getByTestId('skeleton');
    expect(skeleton).toHaveClass('h-10');
    expect(skeleton).toHaveClass('w-full');
  });

  it('renders with rounded corners by default', () => {
    render(<Skeleton data-testid="skeleton" />);
    const skeleton = screen.getByTestId('skeleton');
    expect(skeleton).toHaveClass('rounded-md');
  });
});
