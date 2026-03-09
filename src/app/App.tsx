import { useEffect } from 'react';
import { ToastProvider } from '@/contexts/ToastContext';
import { AppRouter } from './router';
import { usePrefetchDashboard } from '@/hooks/usePrefetchDashboard';
import { useAuthStore } from '@/stores/authStore';

export function App() {
  // Initialize auth — validate stored token on app boot
  useEffect(() => {
    useAuthStore.getState().initialize();
  }, []);

  // Prefetch common dashboard data on app initialization
  usePrefetchDashboard();

  return (
    <ToastProvider>
      <AppRouter />
    </ToastProvider>
  );
}
