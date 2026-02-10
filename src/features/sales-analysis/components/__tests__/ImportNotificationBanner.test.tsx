import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import { ImportNotificationBanner } from '../ImportNotificationBanner';
import type { ImportStatus } from '../../types';

function makeImportStatus(
  overrides: Partial<ImportStatus> = {},
): ImportStatus {
  return {
    unimportedFiles: ['new_data_2024_q3.csv'],
    lastImportedFile: 'file_2024_q2.csv',
    lastImportDate: '2024-07-01',
    ...overrides,
  };
}

describe('ImportNotificationBanner', () => {
  const defaultProps = {
    onTriggerImport: vi.fn(),
    isImporting: false,
    isLoading: false,
  };

  it('returns null when isLoading is true', () => {
    const { container } = render(
      <ImportNotificationBanner
        {...defaultProps}
        importStatus={makeImportStatus()}
        isLoading={true}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('returns null when importStatus is undefined', () => {
    const { container } = render(
      <ImportNotificationBanner
        {...defaultProps}
        importStatus={undefined}
        isLoading={false}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('returns null when unimportedFiles is empty', () => {
    const { container } = render(
      <ImportNotificationBanner
        {...defaultProps}
        importStatus={makeImportStatus({ unimportedFiles: [] })}
        isLoading={false}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('shows banner when files are available', () => {
    render(
      <ImportNotificationBanner
        {...defaultProps}
        importStatus={makeImportStatus()}
        isLoading={false}
      />,
    );
    expect(
      screen.getByText('1 new sales file available for import'),
    ).toBeInTheDocument();
    expect(screen.getByText('new_data_2024_q3.csv')).toBeInTheDocument();
  });

  it('shows plural text when multiple files', () => {
    render(
      <ImportNotificationBanner
        {...defaultProps}
        importStatus={makeImportStatus({
          unimportedFiles: ['file_a.csv', 'file_b.csv'],
        })}
        isLoading={false}
      />,
    );
    expect(
      screen.getByText('2 new sales files available for import'),
    ).toBeInTheDocument();
    expect(screen.getByText('file_a.csv, file_b.csv')).toBeInTheDocument();
  });

  it('renders Import Now button', () => {
    render(
      <ImportNotificationBanner
        {...defaultProps}
        importStatus={makeImportStatus()}
        isLoading={false}
      />,
    );
    expect(
      screen.getByRole('button', { name: /import now/i }),
    ).toBeInTheDocument();
  });

  it('calls onTriggerImport when button is clicked', async () => {
    const user = userEvent.setup();
    const handleImport = vi.fn();
    render(
      <ImportNotificationBanner
        importStatus={makeImportStatus()}
        isLoading={false}
        onTriggerImport={handleImport}
        isImporting={false}
      />,
    );

    await user.click(screen.getByRole('button', { name: /import now/i }));
    expect(handleImport).toHaveBeenCalledTimes(1);
  });

  it('disables button and shows Importing... text when isImporting', () => {
    render(
      <ImportNotificationBanner
        importStatus={makeImportStatus()}
        isLoading={false}
        onTriggerImport={vi.fn()}
        isImporting={true}
      />,
    );
    const button = screen.getByRole('button', { name: /importing/i });
    expect(button).toBeDisabled();
    expect(button).toHaveTextContent('Importing...');
  });

  it('has role="alert" for accessibility', () => {
    render(
      <ImportNotificationBanner
        {...defaultProps}
        importStatus={makeImportStatus()}
        isLoading={false}
      />,
    );
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });
});
