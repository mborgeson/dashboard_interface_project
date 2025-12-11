/**
 * ToggleButton - Reusable toggle button for filter selections
 * Provides consistent styling for multi-select filter options
 */
import { cn } from '@/lib/utils';

interface ToggleButtonProps {
  /** Whether the button is in active/selected state */
  isActive: boolean;
  /** Click handler */
  onClick: () => void;
  /** Button label content */
  children: React.ReactNode;
  /** Optional additional class names */
  className?: string;
  /** Accessible label for screen readers */
  'aria-label'?: string;
}

/**
 * A toggle button component for filter selections.
 * Shows active state with accent color background.
 *
 * @example
 * ```tsx
 * <ToggleButton
 *   isActive={selectedStages.includes('lead')}
 *   onClick={() => toggleStage('lead')}
 * >
 *   Lead
 * </ToggleButton>
 * ```
 */
export function ToggleButton({
  isActive,
  onClick,
  children,
  className,
  'aria-label': ariaLabel,
}: ToggleButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={isActive}
      aria-label={ariaLabel}
      className={cn(
        'px-3 py-1.5 rounded-md text-sm font-medium border transition-colors',
        isActive
          ? 'bg-accent-600 text-white border-accent-600'
          : 'bg-white text-neutral-700 border-neutral-300 hover:border-accent-500',
        className
      )}
    >
      {children}
    </button>
  );
}
