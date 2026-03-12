import type { LucideIcon } from 'lucide-react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

type TrendDirection = 'up' | 'down' | 'neutral';

interface StatCardProps {
  /** Label/title displayed above the value */
  label: string;
  /** The main display value (pre-formatted string) */
  value: string;
  /** Optional subtitle/description below the value */
  subtitle?: string;
  /** Optional icon to display */
  icon?: LucideIcon;
  /** Icon color class (e.g. "text-blue-600") */
  iconColor?: string;
  /** Icon background color class (e.g. "bg-blue-100") */
  iconBgColor?: string;
  /** Trend direction for indicator arrow */
  trend?: TrendDirection;
  /** Trend percentage value to display (e.g. 5.2 renders as "5.2%") */
  trendValue?: number;
  /** Visual size variant */
  variant?: 'default' | 'compact' | 'hero';
  /** Optional click handler */
  onClick?: () => void;
  className?: string;
}

export function StatCard({
  label,
  value,
  subtitle,
  icon: Icon,
  iconColor = 'text-neutral-600',
  iconBgColor = 'bg-neutral-100',
  trend,
  trendValue,
  variant = 'default',
  onClick,
  className,
}: StatCardProps) {
  const isHero = variant === 'hero';
  const isCompact = variant === 'compact';

  const trendColor =
    trend === 'up'
      ? 'text-green-600'
      : trend === 'down'
        ? 'text-red-600'
        : 'text-neutral-500';

  const TrendIcon = trend === 'up' ? TrendingUp : TrendingDown;

  return (
    <Card
      onClick={onClick}
      className={cn(
        'bg-white border border-neutral-200 transition-shadow',
        isHero
          ? 'p-6 shadow-card hover:shadow-card-hover'
          : isCompact
            ? 'p-4 hover:shadow-sm'
            : 'p-6 shadow-card',
        onClick && 'cursor-pointer',
        className,
      )}
    >
      {/* Icon row */}
      {Icon && (
        <div className="flex items-center justify-between mb-2">
          <div className={cn('rounded-lg', isHero ? 'p-3' : 'p-2', iconBgColor)}>
            <Icon
              className={cn(isHero ? 'w-6 h-6' : 'w-5 h-5', iconColor)}
            />
          </div>
        </div>
      )}

      {/* Label (above value for compact/default, below for hero) */}
      {!isHero && (
        <span className="text-sm text-neutral-600">{label}</span>
      )}

      {/* Value + trend */}
      <div className="flex items-baseline gap-2">
        <span
          className={cn(
            'font-bold text-neutral-900',
            isHero ? 'text-hero-stat' : isCompact ? 'text-xl' : 'text-2xl',
          )}
        >
          {value}
        </span>
        {trend && trend !== 'neutral' && (
          <span className={cn('flex items-center gap-0.5 text-sm font-medium', trendColor)}>
            <TrendIcon className="h-4 w-4" />
            {trendValue !== undefined && (
              <span>{Math.abs(trendValue).toFixed(1)}%</span>
            )}
          </span>
        )}
      </div>

      {/* Label for hero variant (below value) */}
      {isHero && (
        <div className="text-sm text-neutral-600 mt-1">{label}</div>
      )}

      {/* Subtitle */}
      {subtitle && (
        <p className={cn('text-neutral-500 mt-1', isCompact ? 'text-xs' : 'text-sm')}>
          {subtitle}
        </p>
      )}
    </Card>
  );
}

export type { StatCardProps };
