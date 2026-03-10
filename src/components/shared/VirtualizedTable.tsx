import { useRef, type ReactNode, type CSSProperties } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import {
  Table,
  TableBody,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn } from '@/lib/utils';

export interface VirtualizedTableProps<T> {
  /** Array of rows to render */
  rows: T[];
  /** Render function for the table header (thead content) */
  renderHeader: () => ReactNode;
  /** Render function for each row — should return a <TableRow> with <TableCell> children */
  renderRow: (row: T, index: number) => ReactNode;
  /** Estimated height of each row in pixels */
  estimateRowHeight?: number;
  /** Number of rows to render outside the visible area */
  overscan?: number;
  /** Unique key extractor for rows */
  getRowKey: (row: T, index: number) => string | number;
  /** Height of the scrollable container (CSS value) */
  height?: number | string;
  /** Minimum row count before virtualization activates */
  virtualizeThreshold?: number;
  /** Additional CSS classes for the outer container */
  className?: string;
  /** Additional CSS classes for the table element */
  tableClassName?: string;
}

/**
 * VirtualizedTable — a virtualized table built on @tanstack/react-virtual
 * that preserves shadcn/ui Table styling.
 *
 * For lists below `virtualizeThreshold` (default 50), it renders a plain
 * shadcn Table with no virtualization overhead.
 *
 * @example
 * ```tsx
 * <VirtualizedTable
 *   rows={documents}
 *   estimateRowHeight={52}
 *   getRowKey={(doc) => doc.id}
 *   renderHeader={() => (
 *     <TableRow>
 *       <TableHead>Name</TableHead>
 *       <TableHead>Size</TableHead>
 *     </TableRow>
 *   )}
 *   renderRow={(doc) => (
 *     <TableRow key={doc.id}>
 *       <TableCell>{doc.name}</TableCell>
 *       <TableCell>{doc.size}</TableCell>
 *     </TableRow>
 *   )}
 * />
 * ```
 */
export function VirtualizedTable<T>({
  rows,
  renderHeader,
  renderRow,
  estimateRowHeight = 52,
  overscan = 10,
  getRowKey,
  height = 600,
  virtualizeThreshold = 50,
  className,
  tableClassName,
}: VirtualizedTableProps<T>) {
  const shouldVirtualize = rows.length >= virtualizeThreshold;

  // Non-virtualized fast path
  if (!shouldVirtualize) {
    return (
      <div className={cn('relative w-full overflow-auto', className)} style={{ maxHeight: height }}>
        <table className={cn('w-full caption-bottom text-sm', tableClassName)}>
          <TableHeader>{renderHeader()}</TableHeader>
          <TableBody>
            {rows.map((row, index) => (
              <VirtualizedTableRowWrapper key={getRowKey(row, index)}>
                {renderRow(row, index)}
              </VirtualizedTableRowWrapper>
            ))}
          </TableBody>
        </table>
      </div>
    );
  }

  return (
    <VirtualizedTableInner
      rows={rows}
      renderHeader={renderHeader}
      renderRow={renderRow}
      estimateRowHeight={estimateRowHeight}
      overscan={overscan}
      getRowKey={getRowKey}
      height={height}
      className={className}
      tableClassName={tableClassName}
    />
  );
}

/**
 * Trivial wrapper so React can attach keys without requiring renderRow
 * to wrap its own content in a fragment.
 */
function VirtualizedTableRowWrapper({ children }: { children: ReactNode }) {
  return <>{children}</>;
}

/**
 * Inner component that actually uses the virtualizer hook.
 * Separated so the hook is only called when virtualization is active.
 */
function VirtualizedTableInner<T>({
  rows,
  renderHeader,
  renderRow,
  estimateRowHeight = 52,
  overscan = 10,
  getRowKey,
  height = 600,
  className,
  tableClassName,
}: Omit<VirtualizedTableProps<T>, 'virtualizeThreshold'>) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollContainerRef.current,
    estimateSize: () => estimateRowHeight,
    overscan,
    getItemKey: (index) => getRowKey(rows[index], index),
  });

  const virtualItems = virtualizer.getVirtualItems();
  const totalSize = virtualizer.getTotalSize();

  // Offset for the first virtual item — used to position the visible rows
  const paddingTop = virtualItems.length > 0 ? virtualItems[0].start : 0;
  const paddingBottom =
    virtualItems.length > 0
      ? totalSize - virtualItems[virtualItems.length - 1].end
      : 0;

  const containerStyle: CSSProperties =
    typeof height === 'number'
      ? { height, overflow: 'auto' }
      : { height, overflow: 'auto' };

  return (
    <div
      ref={scrollContainerRef}
      className={cn('relative w-full', className)}
      style={containerStyle}
    >
      <table className={cn('w-full caption-bottom text-sm', tableClassName)}>
        <TableHeader className="sticky top-0 z-10 bg-background">
          {renderHeader()}
        </TableHeader>
        <TableBody>
          {/* Top spacer row */}
          {paddingTop > 0 && (
            <tr>
              <td style={{ height: paddingTop, padding: 0, border: 'none' }} />
            </tr>
          )}

          {virtualItems.map((virtualRow) => {
            const row = rows[virtualRow.index];
            return (
              <VirtualizedTableRowWrapper key={getRowKey(row, virtualRow.index)}>
                {renderRow(row, virtualRow.index)}
              </VirtualizedTableRowWrapper>
            );
          })}

          {/* Bottom spacer row */}
          {paddingBottom > 0 && (
            <tr>
              <td style={{ height: paddingBottom, padding: 0, border: 'none' }} />
            </tr>
          )}
        </TableBody>
      </table>
    </div>
  );
}

export default VirtualizedTable;
