import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from './layout/AppLayout';
import { DashboardMain } from '@/features/dashboard-main/DashboardMain';

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
        element: <div className="p-6"><h1 className="text-2xl font-semibold">Investments (Coming in Phase 2)</h1></div>,
      },
      {
        path: 'analytics',
        element: <div className="p-6"><h1 className="text-2xl font-semibold">Analytics (Coming in Phase 2)</h1></div>,
      },
      {
        path: 'mapping',
        element: <div className="p-6"><h1 className="text-2xl font-semibold">Mapping (Coming in Phase 2)</h1></div>,
      },
    ],
  },
]);
