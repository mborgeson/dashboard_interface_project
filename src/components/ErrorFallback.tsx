import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';

interface ErrorFallbackProps {
  error: Error;
  onReset?: () => void;
  /** Optional title override (defaults to "Something Went Wrong") */
  title?: string;
  /** Optional description override */
  description?: string;
}

/**
 * User-friendly error fallback UI.
 *
 * Can be used standalone or passed as the `fallback` render function
 * for `<ErrorBoundary>`:
 *
 * ```tsx
 * <ErrorBoundary fallback={(error, reset) => <ErrorFallback error={error} onReset={reset} />}>
 *   <MyComponent />
 * </ErrorBoundary>
 * ```
 */
export function ErrorFallback({
  error,
  onReset,
  title = 'Something Went Wrong',
  description = 'The application encountered an unexpected error. Please try again or contact support if the problem persists.',
}: ErrorFallbackProps) {
  return (
    <div className="flex items-center justify-center p-4">
      <Card className="max-w-lg w-full">
        <CardHeader>
          <CardTitle className="text-destructive flex items-center gap-2">
            <svg
              className="h-5 w-5 flex-shrink-0"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            {title}
          </CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error.message && (
            <div className="rounded-md bg-muted p-3">
              <p className="font-mono text-sm text-muted-foreground">
                <span className="font-semibold">Error:</span> {error.message}
              </p>
            </div>
          )}
          <div className="flex gap-3">
            {onReset && (
              <Button onClick={onReset} variant="default" size="sm">
                Try Again
              </Button>
            )}
            <Button
              onClick={() => window.location.reload()}
              variant="outline"
              size="sm"
            >
              Reload Page
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
