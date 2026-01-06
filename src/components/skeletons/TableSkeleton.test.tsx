import { describe, it, expect } from 'vitest';
import { render } from '@/test/test-utils';
import { TableSkeleton, CompactTableSkeleton } from './TableSkeleton';

describe('TableSkeleton', () => {
  it('renders with default props', () => {
    const { container } = render(<TableSkeleton />);

    // Should have space-y-3 container
    const tableContainer = container.querySelector('.space-y-3');
    expect(tableContainer).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<TableSkeleton className="custom-table-class" />);

    const table = container.querySelector('.custom-table-class');
    expect(table).toBeInTheDocument();
  });

  it('renders header by default', () => {
    const { container } = render(<TableSkeleton />);

    // Header row with border-b
    const headerRow = container.querySelector('.border-b');
    expect(headerRow).toBeInTheDocument();
  });

  it('hides header when showHeader is false', () => {
    const { container } = render(<TableSkeleton showHeader={false} />);

    // Should not have header row
    const headerRow = container.querySelector('.border-b');
    expect(headerRow).not.toBeInTheDocument();
  });

  it('renders default 5 rows', () => {
    const { container } = render(<TableSkeleton />);

    // Rows (flex gap-4 items-center) - excluding header
    const allRows = container.querySelectorAll('.flex.gap-4');
    // 1 header + 5 data rows = 6
    expect(allRows.length).toBe(6);
  });

  it('renders custom number of rows', () => {
    const { container } = render(<TableSkeleton rows={3} />);

    // 1 header + 3 data rows = 4
    const allRows = container.querySelectorAll('.flex.gap-4');
    expect(allRows.length).toBe(4);
  });

  it('renders default 4 columns', () => {
    const { container } = render(<TableSkeleton />);

    // Header should have 4 skeleton cells
    const headerRow = container.querySelector('.border-b');
    const headerCells = headerRow?.querySelectorAll('.h-4');
    expect(headerCells?.length).toBe(4);
  });

  it('renders custom number of columns', () => {
    const { container } = render(<TableSkeleton columns={6} />);

    // Header should have 6 skeleton cells
    const headerRow = container.querySelector('.border-b');
    const headerCells = headerRow?.querySelectorAll('.h-4');
    expect(headerCells?.length).toBe(6);
  });

  it('applies custom column widths', () => {
    const customWidths = ['w-1/4', 'w-1/2', 'w-1/4'];
    const { container } = render(<TableSkeleton columns={3} columnWidths={customWidths} />);

    // Check if custom width is applied
    const firstColumnCells = container.querySelectorAll('.w-1\\/4');
    expect(firstColumnCells.length).toBeGreaterThan(0);
  });
});

describe('CompactTableSkeleton', () => {
  it('renders with default structure', () => {
    const { container } = render(<CompactTableSkeleton />);

    // Should have space-y-2 container
    const tableContainer = container.querySelector('.space-y-2');
    expect(tableContainer).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<CompactTableSkeleton className="custom-compact-class" />);

    const table = container.querySelector('.custom-compact-class');
    expect(table).toBeInTheDocument();
  });

  it('renders default 5 rows', () => {
    const { container } = render(<CompactTableSkeleton />);

    // Each row has border and rounded-lg
    const rows = container.querySelectorAll('.border.rounded-lg');
    expect(rows.length).toBe(5);
  });

  it('renders custom number of rows', () => {
    const { container } = render(<CompactTableSkeleton rows={3} />);

    const rows = container.querySelectorAll('.border.rounded-lg');
    expect(rows.length).toBe(3);
  });

  it('renders avatar placeholder in each row', () => {
    const { container } = render(<CompactTableSkeleton />);

    // Avatar placeholders (h-10 w-10 rounded-full)
    const avatars = container.querySelectorAll('.h-10.w-10.rounded-full');
    expect(avatars.length).toBe(5);
  });

  it('renders action button placeholder', () => {
    const { container } = render(<CompactTableSkeleton />);

    // Action button (h-8 w-24)
    const actionButtons = container.querySelectorAll('.h-8.w-24');
    expect(actionButtons.length).toBe(5);
  });
});
