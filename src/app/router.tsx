import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from './layout/AppLayout';
import { DashboardMain } from '@/features/dashboard-main/DashboardMain';
import { AnalyticsPage } from '@/features/analytics';
import { InvestmentsPage } from '@/features/investments';
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
