import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

interface TableSkeletonProps {
  rows?: number;
  columns?: number;
  showHeader?: boolean;
  columnWidths?: string[];
  className?: string;
}

export function TableSkeleton({
  rows = 5,
  columns = 4,
  showHeader = true,
  columnWidths,
  className,
}: TableSkeletonProps) {
  // Default column widths if not provided
  const widths = columnWidths || Array.from({ length: columns }, () => 'flex-1');

  return (
    <div className={cn('w-full space-y-3', className)}>
      {/* Table header */}
      {showHeader && (
        <div className="flex gap-4 border-b pb-3">
          {Array.from({ length: columns }).map((_, i) => (
            <Skeleton 
              key={`header-${i}`} 
              className={cn('h-4', widths[i] || 'flex-1')} 
            />
          ))}
        </div>
      )}
      
      {/* Table rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={`row-${rowIndex}`} className="flex gap-4 items-center">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton
              key={`cell-${rowIndex}-${colIndex}`}
              className={cn('h-8', widths[colIndex] || 'flex-1')}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

interface CompactTableSkeletonProps {
  rows?: number;
  className?: string;
}

export function CompactTableSkeleton({ 
  rows = 5, 
  className 
}: CompactTableSkeletonProps) {
  return (
    <div className={cn('w-full space-y-2', className)}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={`compact-row-${i}`} className="flex items-center justify-between p-3 border rounded-lg">
          <div className="flex items-center gap-3 flex-1">
            <Skeleton className="h-10 w-10 rounded-full" />
            <div className="space-y-2 flex-1">
              <Skeleton className="h-4 w-1/3" />
              <Skeleton className="h-3 w-1/4" />
            </div>
          </div>
          <Skeleton className="h-8 w-24" />
        </div>
      ))}
    </div>
  );
}
