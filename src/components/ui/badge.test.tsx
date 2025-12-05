import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { Badge } from './badge';

describe('Badge', () => {
  it('renders children correctly', () => {
    render(<Badge>Status</Badge>);
    expect(screen.getByText('Status')).toBeInTheDocument();
  });

  it('applies default variant class', () => {
    render(<Badge>Default</Badge>);
    const badge = screen.getByText('Default');
    expect(badge).toHaveClass('bg-primary');
  });

  it('applies secondary variant class', () => {
    render(<Badge variant="secondary">Secondary</Badge>);
    const badge = screen.getByText('Secondary');
    expect(badge).toHaveClass('bg-secondary');
  });

  it('applies destructive variant class', () => {
    render(<Badge variant="destructive">Destructive</Badge>);
    const badge = screen.getByText('Destructive');
    expect(badge).toHaveClass('bg-destructive');
  });

  it('applies outline variant class', () => {
    render(<Badge variant="outline">Outline</Badge>);
    const badge = screen.getByText('Outline');
    expect(badge).toHaveClass('text-foreground');
  });

  it('accepts custom className', () => {
    render(<Badge className="custom-class">Custom</Badge>);
    const badge = screen.getByText('Custom');
    expect(badge).toHaveClass('custom-class');
  });
});
