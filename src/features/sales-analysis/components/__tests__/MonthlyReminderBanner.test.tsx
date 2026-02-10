import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import { MonthlyReminderBanner } from '../MonthlyReminderBanner';
import type { ReminderStatus } from '../../types';

function makeReminderStatus(
  overrides: Partial<ReminderStatus> = {},
): ReminderStatus {
  return {
    showReminder: true,
    lastImportedFileName: 'file_2024_q2.csv',
    lastImportedFileDate: '2024-07-01',
    ...overrides,
  };
}

describe('MonthlyReminderBanner', () => {
  const defaultProps = {
    onDismiss: vi.fn(),
    isLoading: false,
  };

  it('returns null when isLoading is true', () => {
    const { container } = render(
      <MonthlyReminderBanner
        {...defaultProps}
        reminderStatus={makeReminderStatus()}
        isLoading={true}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('returns null when reminderStatus is undefined', () => {
    const { container } = render(
      <MonthlyReminderBanner
        {...defaultProps}
        reminderStatus={undefined}
        isLoading={false}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('returns null when showReminder is false', () => {
    const { container } = render(
      <MonthlyReminderBanner
        {...defaultProps}
        reminderStatus={makeReminderStatus({ showReminder: false })}
        isLoading={false}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('shows banner when showReminder is true', () => {
    render(
      <MonthlyReminderBanner
        {...defaultProps}
        reminderStatus={makeReminderStatus()}
        isLoading={false}
      />,
    );
    expect(
      screen.getByText('Monthly reminder: Check for new CoStar sales data'),
    ).toBeInTheDocument();
  });

  it('shows last imported file info', () => {
    render(
      <MonthlyReminderBanner
        {...defaultProps}
        reminderStatus={makeReminderStatus()}
        isLoading={false}
      />,
    );
    expect(
      screen.getByText(/Last imported: file_2024_q2\.csv/),
    ).toBeInTheDocument();
    expect(screen.getByText(/2024-07-01/)).toBeInTheDocument();
  });

  it('shows fallback text when no files imported yet', () => {
    render(
      <MonthlyReminderBanner
        {...defaultProps}
        reminderStatus={makeReminderStatus({
          lastImportedFileName: null,
          lastImportedFileDate: null,
        })}
        isLoading={false}
      />,
    );
    expect(
      screen.getByText('No files imported yet'),
    ).toBeInTheDocument();
  });

  it('renders Dismiss button', () => {
    render(
      <MonthlyReminderBanner
        {...defaultProps}
        reminderStatus={makeReminderStatus()}
        isLoading={false}
      />,
    );
    expect(
      screen.getByRole('button', { name: /dismiss/i }),
    ).toBeInTheDocument();
  });

  it('calls onDismiss when Dismiss button is clicked', async () => {
    const user = userEvent.setup();
    const handleDismiss = vi.fn();
    render(
      <MonthlyReminderBanner
        reminderStatus={makeReminderStatus()}
        isLoading={false}
        onDismiss={handleDismiss}
      />,
    );

    await user.click(screen.getByRole('button', { name: /dismiss/i }));
    expect(handleDismiss).toHaveBeenCalledTimes(1);
  });

  it('has role="alert" for accessibility', () => {
    render(
      <MonthlyReminderBanner
        {...defaultProps}
        reminderStatus={makeReminderStatus()}
        isLoading={false}
      />,
    );
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });
});
