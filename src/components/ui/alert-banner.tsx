import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';
import type { AlertBannerProps } from '@/types/notification';
import { cn } from '@/lib/utils';
import { useState } from 'react';

const iconMap = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};

const colorMap = {
  success: {
    bg: 'bg-green-50 dark:bg-green-950/50',
    border: 'border-green-200 dark:border-green-800',
    icon: 'text-green-600 dark:text-green-400',
    title: 'text-green-900 dark:text-green-100',
    description: 'text-green-700 dark:text-green-300',
    button: 'text-green-700 hover:text-green-900 dark:text-green-400 dark:hover:text-green-200',
    closeHover: 'hover:bg-green-100 dark:hover:bg-green-900',
  },
  error: {
    bg: 'bg-red-50 dark:bg-red-950/50',
    border: 'border-red-200 dark:border-red-800',
    icon: 'text-red-600 dark:text-red-400',
    title: 'text-red-900 dark:text-red-100',
    description: 'text-red-700 dark:text-red-300',
    button: 'text-red-700 hover:text-red-900 dark:text-red-400 dark:hover:text-red-200',
    closeHover: 'hover:bg-red-100 dark:hover:bg-red-900',
  },
  warning: {
    bg: 'bg-amber-50 dark:bg-amber-950/50',
    border: 'border-amber-200 dark:border-amber-800',
    icon: 'text-amber-600 dark:text-amber-400',
    title: 'text-amber-900 dark:text-amber-100',
    description: 'text-amber-700 dark:text-amber-300',
    button: 'text-amber-700 hover:text-amber-900 dark:text-amber-400 dark:hover:text-amber-200',
    closeHover: 'hover:bg-amber-100 dark:hover:bg-amber-900',
  },
  info: {
    bg: 'bg-blue-50 dark:bg-blue-950/50',
    border: 'border-blue-200 dark:border-blue-800',
    icon: 'text-blue-600 dark:text-blue-400',
    title: 'text-blue-900 dark:text-blue-100',
    description: 'text-blue-700 dark:text-blue-300',
    button: 'text-blue-700 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-200',
    closeHover: 'hover:bg-blue-100 dark:hover:bg-blue-900',
  },
};

export function AlertBanner({
  variant,
  title,
  description,
  dismissible = false,
  action,
  onDismiss,
}: AlertBannerProps) {
  const [isVisible, setIsVisible] = useState(true);

  const Icon = iconMap[variant];
  const colors = colorMap[variant];

  const handleDismiss = () => {
    setIsVisible(false);
    onDismiss?.();
  };

  if (!isVisible) {
    return null;
  }

  return (
    <div
      className={cn(
        'w-full rounded-lg border p-4',
        colors.bg,
        colors.border
      )}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <Icon className={cn('h-5 w-5 flex-shrink-0 mt-0.5', colors.icon)} />
        
        <div className="flex-1 min-w-0">
          <h3 className={cn('font-semibold text-sm', colors.title)}>
            {title}
          </h3>
          
          {description && (
            <p className={cn('mt-1 text-sm', colors.description)}>
              {description}
            </p>
          )}
          
          {action && (
            <button
              onClick={action.onClick}
              className={cn(
                'mt-2 text-sm font-medium underline-offset-4 hover:underline transition-colors',
                colors.button
              )}
            >
              {action.label}
            </button>
          )}
        </div>
        
        {dismissible && (
          <button
            onClick={handleDismiss}
            className={cn(
              'flex-shrink-0 rounded-md p-1 transition-colors',
              colors.title,
              colors.closeHover
            )}
            aria-label="Dismiss alert"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}
