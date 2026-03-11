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
                <FeatureErrorBoundary featureName="Property Detail">
                  <LazyRoute>
                    <PropertyDetailPage />
                  </LazyRoute>
                </FeatureErrorBoundary>
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
                <FeatureErrorBoundary featureName="Deal Comparison">
                  <LazyRoute>
                    <DealComparisonPage />
                  </LazyRoute>
                </FeatureErrorBoundary>
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
                <FeatureErrorBoundary featureName="Mapping">
                  <LazyRoute>
                    <MappingPage />
                  </LazyRoute>
                </FeatureErrorBoundary>
              ),
            },
            {
              path: 'market',
              element: (
                <FeatureErrorBoundary featureName="Market">
                  <LazyRoute>
                    <MarketPage />
                  </LazyRoute>
                </FeatureErrorBoundary>
              ),
            },
            {
              path: 'market/usa',
              element: (
                <FeatureErrorBoundary featureName="USA Market">
                  <LazyRoute>
                    <USAMarketPage />
                  </LazyRoute>
                </FeatureErrorBoundary>
              ),
            },
            {
              path: 'documents',
              element: (
                <FeatureErrorBoundary featureName="Documents">
                  <LazyRoute>
                    <DocumentsPage />
                  </LazyRoute>
                </FeatureErrorBoundary>
              ),
            },
            {
              path: 'interest-rates',
              element: (
                <FeatureErrorBoundary featureName="Interest Rates">
                  <LazyRoute>
                    <InterestRatesPage />
                  </LazyRoute>
                </FeatureErrorBoundary>
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
                <FeatureErrorBoundary featureName="Extraction">
                  <LazyRoute>
                    <ExtractionDashboard />
                  </LazyRoute>
                </FeatureErrorBoundary>
              ),
            },
            {
              path: 'extraction/:propertyName',
              element: (
                <FeatureErrorBoundary featureName="Extraction">
                  <LazyRoute>
                    <ExtractionDashboard />
                  </LazyRoute>
                </FeatureErrorBoundary>
              ),
            },
            {
              path: 'sales-analysis',
              element: (
                <FeatureErrorBoundary featureName="Sales Analysis">
                  <LazyRoute>
                    <SalesAnalysisPage />
                  </LazyRoute>
                </FeatureErrorBoundary>
              ),
            },
            {
              path: 'construction-pipeline',
              element: (
                <FeatureErrorBoundary featureName="Construction Pipeline">
                  <LazyRoute>
                    <ConstructionPipelinePage />
                  </LazyRoute>
                </FeatureErrorBoundary>
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
