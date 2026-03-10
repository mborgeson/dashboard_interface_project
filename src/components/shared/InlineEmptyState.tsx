import { cn } from '@/lib/utils';

interface InlineEmptyStateProps {
  /** Message to display (default: "No data available") */
  message?: string;
  className?: string;
}

/**
 * Lightweight inline empty state for widget/section-level "no data" messages.
 * Use this inside cards/widgets instead of raw <p> tags for consistent styling.
 * For full-page empty states, use EmptyState or CompactEmptyState from ui/empty-state.
 */
export function InlineEmptyState({
  message = 'No data available',
  className,
}: InlineEmptyStateProps) {
  return (
    <p className={cn('text-center text-muted-foreground py-8', className)}>
      {message}
    </p>
  );
}

export type { InlineEmptyStateProps };
