import type { ReactNode } from 'react';
import { ErrorBoundary } from './ErrorBoundary';
import { reportComponentError } from '../services/errorTracking';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';

interface FeatureErrorBoundaryProps {
  children: ReactNode;
  /** Display name shown in the error message, e.g. "Analytics" */
  featureName: string;
}

function FeatureErrorFallback({
  featureName,
  error,
  onReset,
}: {
  featureName: string;
  error: Error;
  onReset: () => void;
}) {
  return (
    <Card className="border-destructive/50">
      <CardHeader className="pb-3">
        <CardTitle className="text-destructive flex items-center gap-2 text-base">
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
          {featureName} failed to load
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 pt-0">
        <p className="text-sm text-muted-foreground">
          Something went wrong while rendering {featureName}. The rest of the
          application is unaffected.
        </p>
        {error.message && (
          <p className="font-mono text-xs text-muted-foreground bg-muted rounded p-2">
            {error.message}
          </p>
        )}
        <Button size="sm" onClick={onReset}>
          Try Again
        </Button>
      </CardContent>
    </Card>
  );
}

export function FeatureErrorBoundary({
  children,
  featureName,
}: FeatureErrorBoundaryProps) {
  return (
    <ErrorBoundary
      fallback={(error: Error, reset: () => void) => (
        <FeatureErrorFallback
          featureName={featureName}
          error={error}
          onReset={reset}
        />
      )}
      onError={(error, errorInfo) => {
        reportComponentError(error, errorInfo.componentStack ?? '');
      }}
    >
      {children}
    </ErrorBoundary>
  );
}
