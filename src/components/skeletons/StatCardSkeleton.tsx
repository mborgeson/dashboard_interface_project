import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface StatCardSkeletonProps {
  className?: string;
  orientation?: 'horizontal' | 'vertical';
}

export function StatCardSkeleton({ 
  className, 
  orientation = 'horizontal' 
}: StatCardSkeletonProps) {
  if (orientation === 'vertical') {
    return (
      <Card className={className}>
        <CardContent className="pt-6 space-y-4">
          {/* Icon placeholder */}
          <Skeleton className="h-12 w-12 rounded-lg" />
          
          {/* Value and label */}
          <div className="space-y-2">
            <Skeleton className="h-8 w-24" />
            <Skeleton className="h-4 w-32" />
          </div>
          
          {/* Trend indicator */}
          <div className="flex items-center gap-2">
            <Skeleton className="h-4 w-4 rounded-full" />
            <Skeleton className="h-4 w-16" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          {/* Left: Label and value */}
          <div className="space-y-2 flex-1">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-8 w-24" />
            
            {/* Trend indicator */}
            <div className="flex items-center gap-2 pt-1">
              <Skeleton className="h-4 w-4 rounded-full" />
              <Skeleton className="h-3 w-20" />
            </div>
          </div>
          
          {/* Right: Icon placeholder */}
          <Skeleton className="h-12 w-12 rounded-lg" />
        </div>
      </CardContent>
    </Card>
  );
}

interface StatCardSkeletonGridProps {
  count?: number;
  className?: string;
  orientation?: 'horizontal' | 'vertical';
}

export function StatCardSkeletonGrid({ 
  count = 4, 
  className,
  orientation = 'horizontal'
}: StatCardSkeletonGridProps) {
  return (
    <div className={cn(
      'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4',
      className
    )}>
      {Array.from({ length: count }).map((_, i) => (
        <StatCardSkeleton 
          key={`stat-skeleton-${i}`} 
          orientation={orientation}
        />
      ))}
    </div>
  );
}

export function MiniStatSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-center gap-3', className)}>
      <Skeleton className="h-10 w-10 rounded-full" />
      <div className="space-y-1 flex-1">
        <Skeleton className="h-6 w-20" />
        <Skeleton className="h-3 w-24" />
      </div>
    </div>
  );
}
