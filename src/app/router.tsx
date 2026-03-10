import { createBrowserRouter, RouterProvider as ReactRouterProvider, Navigate, Outlet } from 'react-router-dom';
import { AppLayout } from './layout/AppLayout';
import { PageSuspenseWrapper } from '@/components/SuspenseWrapper';
import { FeatureErrorBoundary } from '@/components/FeatureErrorBoundary';
import { useAuthStore } from '@/stores/authStore';
import {
  DashboardMain,
  AnalyticsPage,
  InvestmentsPage,
  PropertyDetailPage,
  MappingPage,
  DealsPage,
  MarketPage,
  USAMarketPage,
  DocumentsPage,
  InterestRatesPage,
  ReportingSuitePage,
  ExtractionDashboard,
  DealComparisonPage,
  SalesAnalysisPage,
  ConstructionPipelinePage,
  LoginPage,
  routerOptions,
} from './routes';

// Wrapper for lazy-loaded routes
function LazyRoute({ children }: { children: React.ReactNode }) {
  return (
    <PageSuspenseWrapper>
      {children}
    </PageSuspenseWrapper>
  );
}

// Separate component to handle the Deals route with Suspense
function DealsRoute() {
  return <DealsPage />;
}

// Auth gate — redirects unauthenticated users to /login
function RequireAuth() {
  const { isAuthenticated, isLoading } = useAuthStore();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

// Create the router instance (internal, not exported)
const router = createBrowserRouter(
  [
    {
      path: '/login',
      element: (
        <LazyRoute>
          <LoginPage />
        </LazyRoute>
      ),
    },
    {
      element: <RequireAuth />,
      children: [
        {
          path: '/',
          element: <AppLayout />,
          children: [
            {
              index: true,
              element: (
                <FeatureErrorBoundary featureName="Dashboard">
                  <LazyRoute>
                    <DashboardMain />
                  </LazyRoute>
                </FeatureErrorBoundary>
              ),
            },
            {
              path: 'investments',
              element: (
                <FeatureErrorBoundary featureName="Investments">
                  <LazyRoute>
                    <InvestmentsPage />
                  </LazyRoute>
                </FeatureErrorBoundary>
              ),
            },
            {
              path: 'properties/:id',
              element: (
                <LazyRoute>
                  <PropertyDetailPage />
                </LazyRoute>
              ),
            },
            {
              path: 'deals',
              element: (
                <FeatureErrorBoundary featureName="Deals">
                  <LazyRoute>
                    <DealsRoute />
                  </LazyRoute>
                </FeatureErrorBoundary>
              ),
            },
            {
              path: 'deals/compare',
              element: (
                <LazyRoute>
                  <DealComparisonPage />
                </LazyRoute>
              ),
            },
            {
              path: 'analytics',
              element: (
                <FeatureErrorBoundary featureName="Analytics">
                  <LazyRoute>
                    <AnalyticsPage />
                  </LazyRoute>
                </FeatureErrorBoundary>
              ),
            },
            {
              path: 'mapping',
              element: (
                <LazyRoute>
                  <MappingPage />
                </LazyRoute>
              ),
            },
            {
              path: 'market',
              element: (
                <LazyRoute>
                  <MarketPage />
                </LazyRoute>
              ),
            },
            {
              path: 'market/usa',
              element: (
                <LazyRoute>
                  <USAMarketPage />
                </LazyRoute>
              ),
            },
            {
              path: 'documents',
              element: (
                <LazyRoute>
                  <DocumentsPage />
                </LazyRoute>
              ),
            },
            {
              path: 'interest-rates',
              element: (
                <LazyRoute>
                  <InterestRatesPage />
                </LazyRoute>
              ),
            },
            {
              path: 'reporting',
              element: (
                <FeatureErrorBoundary featureName="Reporting">
                  <LazyRoute>
                    <ReportingSuitePage />
                  </LazyRoute>
                </FeatureErrorBoundary>
              ),
            },
            {
              path: 'extraction',
              element: (
                <LazyRoute>
                  <ExtractionDashboard />
                </LazyRoute>
              ),
            },
            {
              path: 'extraction/:propertyName',
              element: (
                <LazyRoute>
                  <ExtractionDashboard />
                </LazyRoute>
              ),
            },
            {
              path: 'sales-analysis',
              element: (
                <LazyRoute>
                  <SalesAnalysisPage />
                </LazyRoute>
              ),
            },
            {
              path: 'construction-pipeline',
              element: (
                <LazyRoute>
                  <ConstructionPipelinePage />
                </LazyRoute>
              ),
            },
          ],
        },
      ],
    },
  ],
  routerOptions
);

// Export only the RouterProvider component wrapper
export function AppRouter() {
  return <ReactRouterProvider router={router} future={{ v7_startTransition: true }} />;
}
