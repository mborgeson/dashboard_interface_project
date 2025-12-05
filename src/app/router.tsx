import { createBrowserRouter } from 'react-router-dom';
import { lazy } from 'react';
import { AppLayout } from './layout/AppLayout';
import { PageSuspenseWrapper } from '@/components/SuspenseWrapper';

// Eager load - Dashboard is the landing page
import { DashboardMain } from '@/features/dashboard-main/DashboardMain';

// Lazy load all other pages for code splitting
const AnalyticsPage = lazy(() =>
  import('@/features/analytics').then(m => ({ default: m.AnalyticsPage }))
);
const InvestmentsPage = lazy(() =>
  import('@/features/investments').then(m => ({ default: m.InvestmentsPage }))
);
const PropertyDetailPage = lazy(() =>
  import('@/features/property-detail').then(m => ({ default: m.PropertyDetailPage }))
);
const TransactionsPage = lazy(() =>
  import('@/features/transactions').then(m => ({ default: m.TransactionsPage }))
);
const MappingPage = lazy(() =>
  import('@/features/mapping').then(m => ({ default: m.MappingPage }))
);
const DealsPage = lazy(() =>
  import('@/features/deals').then(m => ({ default: m.DealsPage }))
);
const MarketPage = lazy(() =>
  import('@/features/market').then(m => ({ default: m.MarketPage }))
);
const DocumentsPage = lazy(() =>
  import('@/features/documents').then(m => ({ default: m.DocumentsPage }))
);

// Wrapper for lazy-loaded routes
function LazyRoute({ children }: { children: React.ReactNode }) {
  return (
    <PageSuspenseWrapper>
      {children}
    </PageSuspenseWrapper>
  );
}

export const router = createBrowserRouter([
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
    ],
  },
]);

// Separate component to handle the Deals route with Suspense
function DealsRoute() {
  return <DealsPage />;
}
