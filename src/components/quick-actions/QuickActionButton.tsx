import { type ButtonHTMLAttributes, forwardRef } from 'react';
import {
  Star,
  StarOff,
  GitCompare,
  Share2,
  FileDown,
  StickyNote,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useQuickActions, type QuickAction } from '@/contexts/QuickActionsContext';
import { useToast } from '@/hooks/useToast';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

type ActionType = QuickAction['type'];

interface QuickActionButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'type'> {
  action: QuickAction;
  variant?: 'icon' | 'text' | 'both';
  size?: 'sm' | 'md' | 'lg';
}

const actionConfig: Record<
  ActionType,
  {
    label: string;
    Icon: typeof Star;
    ActiveIcon?: typeof Star;
    activeLabel?: string;
    color: string;
    activeColor?: string;
  }
> = {
  watchlist: {
    label: 'Add to Watchlist',
    Icon: Star,
    ActiveIcon: StarOff,
    activeLabel: 'Remove from Watchlist',
    color: 'text-neutral-600 hover:text-amber-500',
    activeColor: 'text-amber-500 hover:text-neutral-600',
  },
  compare: {
    label: 'Compare',
    Icon: GitCompare,
    color: 'text-neutral-600 hover:text-blue-500',
    activeColor: 'text-blue-500',
  },
  share: {
    label: 'Share',
    Icon: Share2,
    color: 'text-neutral-600 hover:text-green-500',
  },
  'export-pdf': {
    label: 'Export PDF',
    Icon: FileDown,
    color: 'text-neutral-600 hover:text-purple-500',
  },
  'add-note': {
    label: 'Add Note',
    Icon: StickyNote,
    color: 'text-neutral-600 hover:text-orange-500',
  },
};

const sizeConfig = {
  sm: {
    button: 'h-7 w-7',
    icon: 'h-3.5 w-3.5',
    text: 'text-xs',
    padding: 'px-2',
  },
  md: {
    button: 'h-8 w-8',
    icon: 'h-4 w-4',
    text: 'text-sm',
    padding: 'px-3',
  },
  lg: {
    button: 'h-10 w-10',
    icon: 'h-5 w-5',
    text: 'text-base',
    padding: 'px-4',
  },
};

export const QuickActionButton = forwardRef<HTMLButtonElement, QuickActionButtonProps>(
  ({ action, variant = 'icon', size = 'md', className, onClick, ...props }, ref) => {
    const {
      isInWatchlist,
      toggleWatchlist,
      addDealToCompare,
      selectedDealsForComparison,
      addRecentAction,
    } = useQuickActions();
    const { success, info } = useToast();

    const config = actionConfig[action.type];
    const sizes = sizeConfig[size];

    // Determine active state based on action type
    const isActive = (() => {
      switch (action.type) {
        case 'watchlist':
          return isInWatchlist(action.dealId);
        case 'compare':
          return selectedDealsForComparison.includes(action.dealId);
        default:
          return false;
      }
    })();

    const Icon = isActive && config.ActiveIcon ? config.ActiveIcon : config.Icon;
    const label = isActive && config.activeLabel ? config.activeLabel : config.label;
    const colorClass = isActive && config.activeColor ? config.activeColor : config.color;

    const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
      e.stopPropagation();

      switch (action.type) {
        case 'watchlist':
          toggleWatchlist(action.dealId);
          if (!isActive) {
            success('Added to watchlist');
            addRecentAction(action, 'Added deal to watchlist');
          } else {
            info('Removed from watchlist');
          }
          break;

        case 'compare':
          if (selectedDealsForComparison.length >= 4 && !isActive) {
            info('Maximum 4 deals can be compared at once');
          } else {
            addDealToCompare(action.dealId);
            if (!isActive) {
              success('Added to comparison');
              addRecentAction(action, 'Added deal to comparison');
            }
          }
          break;

        case 'share':
          // Implement share functionality
          navigator.clipboard?.writeText(
            `${window.location.origin}/${action.entityType}/${action.entityId}`
          );
          success('Link copied to clipboard');
          addRecentAction(action, `Shared ${action.entityType}`);
          break;

        case 'export-pdf':
          // Trigger PDF export
          info('Generating PDF...');
          addRecentAction(action, `Exported ${action.entityType} as PDF`);
          break;

        case 'add-note':
          // Open note modal - would need additional context/callback
          info('Opening notes...');
          addRecentAction(action, `Added note to ${action.entityType}`);
          break;
      }

      onClick?.(e);
    };

    const buttonContent = (
      <>
        <Icon className={cn(sizes.icon, variant === 'text' && 'mr-1.5')} />
        {(variant === 'text' || variant === 'both') && (
          <span className={sizes.text}>{label}</span>
        )}
      </>
    );

    const button = (
      <button
        ref={ref}
        onClick={handleClick}
        className={cn(
          'inline-flex items-center justify-center rounded-md transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2',
          'disabled:pointer-events-none disabled:opacity-50',
          colorClass,
          variant === 'icon' && sizes.button,
          (variant === 'text' || variant === 'both') && cn('h-8', sizes.padding),
          'hover:bg-neutral-100',
          className
        )}
        aria-label={label}
        aria-pressed={isActive}
        {...props}
      >
        {buttonContent}
      </button>
    );

    // Only wrap with tooltip for icon-only variant
    if (variant === 'icon') {
      return (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>{button}</TooltipTrigger>
            <TooltipContent side="top" className="text-xs">
              {label}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );
    }

    return button;
  }
);

QuickActionButton.displayName = 'QuickActionButton';

// Convenience wrapper for deal-specific actions
interface DealQuickActionsProps {
  dealId: string;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function DealQuickActions({ dealId, className, size = 'sm' }: DealQuickActionsProps) {
  return (
    <div className={cn('flex items-center gap-1', className)}>
      <QuickActionButton
        action={{ type: 'watchlist', dealId }}
        size={size}
      />
      <QuickActionButton
        action={{ type: 'compare', dealId }}
        size={size}
      />
      <QuickActionButton
        action={{ type: 'share', entityType: 'deals', entityId: dealId }}
        size={size}
      />
    </div>
  );
}
