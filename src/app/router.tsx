import { createBrowserRouter, RouterProvider as ReactRouterProvider } from 'react-router-dom';
import { AppLayout } from './layout/AppLayout';
import { PageSuspenseWrapper } from '@/components/SuspenseWrapper';
import {
  AnalyticsPage,
  InvestmentsPage,
  PropertyDetailPage,
  TransactionsPage,
  MappingPage,
  DealsPage,
  MarketPage,
  DocumentsPage,
  InterestRatesPage,
  ReportingSuitePage,
  ExtractionDashboard,
  DealComparisonPage,
  routerOptions,
} from './routes';

// Eager load - Dashboard is the landing page
import { DashboardMain } from '@/features/dashboard-main/DashboardMain';

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

// Create the router instance (internal, not exported)
const router = createBrowserRouter(
  [
    {
      path: '/',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: <DashboardMain />,
        },
        {
          path: 'investments',
          element: (
            <LazyRoute>
              <InvestmentsPage />
            </LazyRoute>
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
          path: 'transactions',
          element: (
            <LazyRoute>
              <TransactionsPage />
            </LazyRoute>
          ),
        },
        {
          path: 'deals',
          element: (
            <LazyRoute>
              <DealsRoute />
            </LazyRoute>
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
            <LazyRoute>
              <AnalyticsPage />
            </LazyRoute>
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
            <LazyRoute>
              <ReportingSuitePage />
            </LazyRoute>
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
      ],
    },
  ],
  routerOptions
);

// Export only the RouterProvider component wrapper
export function AppRouter() {
  return <ReactRouterProvider router={router} future={{ v7_startTransition: true }} />;
}
