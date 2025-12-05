import { Suspense } from 'react';
import type { ReactNode, ComponentType } from 'react';
import { ErrorBoundary } from './ErrorBoundary';
import { LoadingSpinner } from '@/contexts/LoadingContext';

interface SuspenseWrapperProps {
  children: ReactNode;
  fallback?: ReactNode;
  errorFallback?: ReactNode;
  onError?: (error: Error) => void;
}

export function SuspenseWrapper({
  children,
  fallback,
  errorFallback,
  onError,
}: SuspenseWrapperProps) {
  const defaultFallback = (
    <div className="flex items-center justify-center min-h-[400px]">
      <LoadingSpinner size="lg" />
    </div>
  );

  return (
    <ErrorBoundary fallback={errorFallback}>
      <Suspense fallback={fallback || defaultFallback}>
        {children}
      </Suspense>
    </ErrorBoundary>
  );
}

interface WithSuspenseOptions {
  fallback?: ReactNode;
  errorFallback?: ReactNode;
}

export function withSuspense<P extends object>(
  Component: ComponentType<P>,
  options: WithSuspenseOptions = {}
) {
  return function WithSuspenseComponent(props: P) {
    return (
      <SuspenseWrapper 
        fallback={options.fallback} 
        errorFallback={options.errorFallback}
      >
        <Component {...props} />
      </SuspenseWrapper>
    );
  };
}

interface PageSuspenseWrapperProps {
  children: ReactNode;
  fallback?: ReactNode;
}

export function PageSuspenseWrapper({ 
  children, 
  fallback 
}: PageSuspenseWrapperProps) {
  const defaultFallback = (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-center min-h-[calc(100vh-200px)]">
        <div className="text-center space-y-4">
          <LoadingSpinner size="xl" />
          <p className="text-sm text-muted-foreground">Loading page...</p>
        </div>
      </div>
    </div>
  );

  return (
    <SuspenseWrapper fallback={fallback || defaultFallback}>
      {children}
    </SuspenseWrapper>
  );
}

interface CardSuspenseWrapperProps {
  children: ReactNode;
  fallback?: ReactNode;
}

export function CardSuspenseWrapper({ 
  children, 
  fallback 
}: CardSuspenseWrapperProps) {
  const defaultFallback = (
    <div className="flex items-center justify-center p-12">
      <LoadingSpinner size="md" />
    </div>
  );

  return (
    <SuspenseWrapper fallback={fallback || defaultFallback}>
      {children}
    </SuspenseWrapper>
  );
}

interface TableSuspenseWrapperProps {
  children: ReactNode;
  fallback?: ReactNode;
}

export function TableSuspenseWrapper({ 
  children, 
  fallback 
}: TableSuspenseWrapperProps) {
  const defaultFallback = (
    <div className="flex items-center justify-center py-12 border-t">
      <div className="text-center space-y-3">
        <LoadingSpinner size="md" />
        <p className="text-xs text-muted-foreground">Loading data...</p>
      </div>
    </div>
  );

  return (
    <SuspenseWrapper fallback={fallback || defaultFallback}>
      {children}
    </SuspenseWrapper>
  );
}
