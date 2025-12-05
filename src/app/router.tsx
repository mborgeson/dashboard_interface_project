import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from './layout/AppLayout';
import { DashboardMain } from '@/features/dashboard-main/DashboardMain';
import { AnalyticsPage } from '@/features/analytics';
import { InvestmentsPage } from '@/features/investments';
import { PropertyDetailPage } from '@/features/property-detail';
import { TransactionsPage } from '@/features/transactions';
import { MappingPage } from '@/features/mapping';

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
        element: <InvestmentsPage />,
      },
      {
        path: 'properties/:id',
        element: <PropertyDetailPage />,
      },
      {
        path: 'transactions',
        element: <TransactionsPage />,
      },
      {
        path: 'analytics',
        element: <AnalyticsPage />,
      },
      {
        path: 'mapping',
        element: <MappingPage />,
      },
    ],
  },
]);
