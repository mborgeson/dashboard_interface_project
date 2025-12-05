import { cn } from "@/lib/utils"

function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-muted", className)}
      {...props}
    />
  )
}

// Card skeleton for dashboard cards
function CardSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn("rounded-lg border bg-card shadow-sm p-6", className)}>
      <div className="space-y-3">
        {/* Title */}
        <Skeleton className="h-6 w-1/3" />
        {/* Subtitle */}
        <Skeleton className="h-4 w-1/2" />
        {/* Content */}
        <div className="space-y-2 pt-4">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-3/4" />
        </div>
      </div>
    </div>
  )
}

// Table skeleton for data tables
function TableSkeleton({
  rows = 5,
  columns = 4,
  className
}: {
  rows?: number
  columns?: number
  className?: string
}) {
  return (
    <div className={cn("w-full space-y-3", className)}>
      {/* Table header */}
      <div className="flex gap-4 border-b pb-3">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={`header-${i}`} className="h-4 flex-1" />
        ))}
      </div>
      {/* Table rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={`row-${rowIndex}`} className="flex gap-4">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton
              key={`cell-${rowIndex}-${colIndex}`}
              className="h-8 flex-1"
            />
          ))}
        </div>
      ))}
    </div>
  )
}

// Chart skeleton for chart placeholders
function ChartSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn("space-y-3", className)}>
      {/* Chart title */}
      <Skeleton className="h-6 w-1/4" />
      {/* Chart area */}
      <div className="relative h-[300px] w-full">
        <Skeleton className="absolute inset-0" />
        {/* Chart bars/lines simulation */}
        <div className="absolute bottom-0 left-0 right-0 flex items-end justify-around gap-2 p-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton
              key={`bar-${i}`}
              className="w-full"
              style={{ height: `${Math.random() * 60 + 40}%` }}
            />
          ))}
        </div>
      </div>
      {/* Chart legend */}
      <div className="flex gap-4 justify-center">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={`legend-${i}`} className="h-4 w-20" />
        ))}
      </div>
    </div>
  )
}

export { Skeleton, CardSkeleton, TableSkeleton, ChartSkeleton }

// Re-export specialized skeletons
export * from '../skeletons'
