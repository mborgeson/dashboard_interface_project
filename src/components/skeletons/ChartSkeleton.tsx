import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface ChartSkeletonProps {
  className?: string;
  showLegend?: boolean;
  showTitle?: boolean;
  height?: number;
}

export function ChartSkeleton({ 
  className, 
  showLegend = true, 
  showTitle = true,
  height = 300 
}: ChartSkeletonProps) {
  return (
    <div className={cn('space-y-3', className)}>
      {/* Chart title */}
      {showTitle && <Skeleton className="h-6 w-1/4" />}
      
      {/* Chart area */}
      <div 
        className="relative w-full rounded-lg bg-muted/50" 
        style={{ height: `${height}px` }}
      >
        {/* Chart bars/lines simulation */}
        <div className="absolute bottom-0 left-0 right-0 flex items-end justify-around gap-2 p-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton
              key={`bar-${i}`}
              className="w-full rounded-t"
              style={{ 
                height: `${Math.floor(Math.random() * 60) + 40}%`,
                animationDelay: `${i * 100}ms`
              }}
            />
          ))}
        </div>
      </div>
      
      {/* Chart legend */}
      {showLegend && (
        <div className="flex gap-4 justify-center flex-wrap">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={`legend-${i}`} className="flex items-center gap-2">
              <Skeleton className="h-3 w-3 rounded-full" />
              <Skeleton className="h-4 w-16" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function ChartCardSkeleton({ className }: { className?: string }) {
  return (
    <Card className={className}>
      <CardHeader>
        <Skeleton className="h-6 w-1/3" />
        <Skeleton className="h-4 w-1/2 mt-2" />
      </CardHeader>
      <CardContent>
        <ChartSkeleton showTitle={false} />
      </CardContent>
    </Card>
  );
}

export function LineChartSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('space-y-3', className)}>
      <Skeleton className="h-6 w-1/4" />
      <div className="relative h-[300px] w-full rounded-lg bg-muted/50">
        {/* Line chart path simulation */}
        <svg className="absolute inset-0 w-full h-full p-4">
          <defs>
            <linearGradient id="shimmer" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="hsl(var(--muted))" stopOpacity="0.3" />
              <stop offset="50%" stopColor="hsl(var(--muted-foreground))" stopOpacity="0.3" />
              <stop offset="100%" stopColor="hsl(var(--muted))" stopOpacity="0.3" />
            </linearGradient>
          </defs>
          {/* Simulate line chart paths */}
          {Array.from({ length: 2 }).map((_, i) => (
            <polyline
              key={`line-${i}`}
              points={Array.from({ length: 10 }, (_, j) => {
                const x = (j / 9) * 100;
                const y = 20 + Math.random() * 60;
                return `${x},${y}`;
              }).join(' ')}
              fill="none"
              stroke="url(#shimmer)"
              strokeWidth="2"
              vectorEffect="non-scaling-stroke"
              className="animate-pulse"
              style={{ animationDelay: `${i * 200}ms` }}
            />
          ))}
        </svg>
      </div>
      <div className="flex gap-4 justify-center">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={`legend-${i}`} className="flex items-center gap-2">
            <Skeleton className="h-3 w-3 rounded-full" />
            <Skeleton className="h-4 w-16" />
          </div>
        ))}
      </div>
    </div>
  );
}
