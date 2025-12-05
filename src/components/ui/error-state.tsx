import { AlertTriangle, AlertCircle, Info, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

type ErrorVariant = 'error' | 'warning' | 'info';

interface ErrorStateProps {
  title?: string;
  description?: string;
  variant?: ErrorVariant;
  onRetry?: () => void;
  retryLabel?: string;
  className?: string;
  showIcon?: boolean;
  fullScreen?: boolean;
}

const variantConfig = {
  error: {
    icon: AlertTriangle,
    iconClassName: 'text-destructive',
    defaultTitle: 'Error',
    defaultDescription: 'An unexpected error occurred. Please try again.',
  },
  warning: {
    icon: AlertCircle,
    iconClassName: 'text-yellow-600 dark:text-yellow-500',
    defaultTitle: 'Warning',
    defaultDescription: 'Something needs your attention.',
  },
  info: {
    icon: Info,
    iconClassName: 'text-blue-600 dark:text-blue-500',
    defaultTitle: 'Information',
    defaultDescription: 'Here\'s what you need to know.',
  },
};

export function ErrorState({
  title,
  description,
  variant = 'error',
  onRetry,
  retryLabel = 'Try Again',
  className,
  showIcon = true,
  fullScreen = false,
}: ErrorStateProps) {
  const config = variantConfig[variant];
  const Icon = config.icon;
  const displayTitle = title || config.defaultTitle;
  const displayDescription = description || config.defaultDescription;

  const content = (
    <Card className={cn('border-none shadow-none', className)}>
      <CardHeader className="text-center pb-3">
        {showIcon && (
          <div className="flex justify-center mb-2">
            <Icon className={cn('h-12 w-12', config.iconClassName)} />
          </div>
        )}
        <CardTitle className="text-xl">{displayTitle}</CardTitle>
        {displayDescription && (
          <CardDescription className="text-base">
            {displayDescription}
          </CardDescription>
        )}
      </CardHeader>
      {onRetry && (
        <CardContent className="flex justify-center">
          <Button onClick={onRetry} variant="default" className="gap-2">
            <RefreshCw className="h-4 w-4" />
            {retryLabel}
          </Button>
        </CardContent>
      )}
    </Card>
  );

  if (fullScreen) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        {content}
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center p-8">
      {content}
    </div>
  );
}

interface InlineErrorProps {
  message: string;
  variant?: ErrorVariant;
  className?: string;
}

export function InlineError({ 
  message, 
  variant = 'error', 
  className 
}: InlineErrorProps) {
  const config = variantConfig[variant];
  const Icon = config.icon;

  return (
    <div
      className={cn(
        'flex items-start gap-3 p-4 rounded-lg border bg-card',
        variant === 'error' && 'border-destructive/50 bg-destructive/5',
        variant === 'warning' && 'border-yellow-500/50 bg-yellow-50 dark:bg-yellow-950/20',
        variant === 'info' && 'border-blue-500/50 bg-blue-50 dark:bg-blue-950/20',
        className
      )}
    >
      <Icon className={cn('h-5 w-5 flex-shrink-0 mt-0.5', config.iconClassName)} />
      <p className="text-sm text-foreground">{message}</p>
    </div>
  );
}

interface ErrorAlertProps {
  title: string;
  message?: string;
  onDismiss?: () => void;
  className?: string;
}

export function ErrorAlert({ 
  title, 
  message, 
  onDismiss, 
  className 
}: ErrorAlertProps) {
  return (
    <div
      className={cn(
        'relative flex gap-3 p-4 rounded-lg border border-destructive/50 bg-destructive/5',
        className
      )}
    >
      <AlertTriangle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
      <div className="flex-1 space-y-1">
        <p className="font-semibold text-sm text-foreground">{title}</p>
        {message && (
          <p className="text-sm text-muted-foreground">{message}</p>
        )}
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Dismiss"
        >
          <svg
            className="h-4 w-4"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </div>
  );
}
