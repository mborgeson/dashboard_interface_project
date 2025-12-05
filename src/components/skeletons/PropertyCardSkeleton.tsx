import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface PropertyCardSkeletonProps {
  className?: string;
}

export function PropertyCardSkeleton({ className }: PropertyCardSkeletonProps) {
  return (
    <Card className={cn('overflow-hidden', className)}>
      {/* Image placeholder */}
      <Skeleton className="h-48 w-full rounded-t-lg rounded-b-none" />
      
      <CardContent className="p-6 space-y-4">
        {/* Title and subtitle */}
        <div className="space-y-2">
          <Skeleton className="h-6 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
        </div>
        
        {/* Stats row with 3 items */}
        <div className="flex items-center justify-between pt-2">
          <div className="space-y-1">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-5 w-20" />
          </div>
          <div className="space-y-1">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-5 w-20" />
          </div>
          <div className="space-y-1">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-5 w-20" />
          </div>
        </div>
        
        {/* Badge placeholder */}
        <div className="flex gap-2 pt-2">
          <Skeleton className="h-6 w-20 rounded-full" />
          <Skeleton className="h-6 w-24 rounded-full" />
        </div>
      </CardContent>
    </Card>
  );
}

interface PropertyCardSkeletonGridProps {
  count?: number;
  className?: string;
}

export function PropertyCardSkeletonGrid({ 
  count = 6, 
  className 
}: PropertyCardSkeletonGridProps) {
  return (
    <div className={cn(
      'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6',
      className
    )}>
      {Array.from({ length: count }).map((_, i) => (
        <PropertyCardSkeleton key={`property-skeleton-${i}`} />
      ))}
    </div>
  );
}
