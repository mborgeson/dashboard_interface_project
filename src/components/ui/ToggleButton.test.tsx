import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import { ToggleButton } from './ToggleButton';

describe('ToggleButton', () => {
  it('renders children correctly', () => {
    render(
      <ToggleButton isActive={false} onClick={() => {}}>
        Test Label
      </ToggleButton>
    );
    expect(screen.getByRole('button', { name: /test label/i })).toBeInTheDocument();
  });

  it('handles click events', async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();

    render(
      <ToggleButton isActive={false} onClick={handleClick}>
        Click me
      </ToggleButton>
    );
    await user.click(screen.getByRole('button'));

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('applies active styles when isActive is true', () => {
    render(
      <ToggleButton isActive={true} onClick={() => {}}>
        Active
      </ToggleButton>
    );
    const button = screen.getByRole('button');
    expect(button).toHaveClass('bg-accent-600');
    expect(button).toHaveAttribute('aria-pressed', 'true');
  });

  it('applies inactive styles when isActive is false', () => {
    render(
      <ToggleButton isActive={false} onClick={() => {}}>
        Inactive
      </ToggleButton>
    );
    const button = screen.getByRole('button');
    expect(button).toHaveClass('bg-white');
    expect(button).toHaveAttribute('aria-pressed', 'false');
  });

  it('applies custom className', () => {
    render(
      <ToggleButton isActive={false} onClick={() => {}} className="custom-class">
        Custom
      </ToggleButton>
    );
    expect(screen.getByRole('button')).toHaveClass('custom-class');
  });

  it('supports aria-label for accessibility', () => {
    render(
      <ToggleButton isActive={false} onClick={() => {}} aria-label="Toggle filter">
        Filter
      </ToggleButton>
    );
    expect(screen.getByRole('button', { name: /toggle filter/i })).toBeInTheDocument();
  });
});
