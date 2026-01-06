import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface DealCardSkeletonProps {
  className?: string;
}

export function DealCardSkeleton({ className }: DealCardSkeletonProps) {
  return (
    <Card className={cn('overflow-hidden', className)}>
      <CardHeader className="pb-3">
        {/* Deal name and amount */}
        <div className="space-y-2">
          <Skeleton className="h-5 w-3/4" />
          <Skeleton className="h-7 w-1/2" />
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Status badge */}
        <div className="flex items-center gap-2">
          <Skeleton className="h-6 w-24 rounded-full" />
          <Skeleton className="h-6 w-20 rounded-full" />
        </div>
        
        {/* Progress bar */}
        <div className="space-y-2">
          <div className="flex justify-between">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-3 w-12" />
          </div>
          <Skeleton className="h-2 w-full rounded-full" />
        </div>
        
        {/* Detail lines */}
        <div className="space-y-3 pt-2">
          <div className="flex items-center justify-between">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-32" />
          </div>
          <div className="flex items-center justify-between">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="h-4 w-28" />
          </div>
          <div className="flex items-center justify-between">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-36" />
          </div>
        </div>
        
        {/* Footer actions */}
        <div className="flex gap-2 pt-2">
          <Skeleton className="h-9 flex-1" />
          <Skeleton className="h-9 w-20" />
        </div>
      </CardContent>
    </Card>
  );
}

interface DealCardSkeletonListProps {
  count?: number;
  className?: string;
}

export function DealCardSkeletonList({ 
  count = 3, 
  className 
}: DealCardSkeletonListProps) {
  return (
    <div className={cn('space-y-4', className)}>
      {Array.from({ length: count }).map((_, i) => (
        <DealCardSkeleton key={`deal-skeleton-${i}`} />
      ))}
    </div>
  );
}

// Pre-defined card counts per stage to avoid Math.random() during render
const STAGE_CARD_COUNTS = [2, 3, 1, 2];

export function DealPipelineSkeleton({ className }: { className?: string }) {
  const stages = ['Prospecting', 'Qualification', 'Due Diligence', 'Closing'];

  return (
    <div className={cn('grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4', className)}>
      {stages.map((stage, i) => (
        <div key={`stage-${i}`} className="space-y-4">
          {/* Stage header */}
          <div className="space-y-1">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-4 w-20" />
          </div>

          {/* Deal cards in stage */}
          <div className="space-y-3">
            {Array.from({ length: STAGE_CARD_COUNTS[i] }).map((_, j) => (
              <Card key={`stage-${i}-card-${j}`} className="p-4">
                <div className="space-y-3">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-6 w-1/2" />
                  <Skeleton className="h-2 w-full rounded-full" />
                  <Skeleton className="h-3 w-24" />
                </div>
              </Card>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
