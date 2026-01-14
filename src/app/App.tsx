import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ToastProvider } from '@/contexts/ToastContext';
import { AppRouter } from './router';
import { usePrefetchDashboard } from '@/hooks/usePrefetchDashboard';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
});

/**
 * Inner app component that has access to QueryClient context
 * Required for prefetch hook to work
 */
function AppContent() {
  // Prefetch common dashboard data on app initialization
  usePrefetchDashboard();

  return (
    <ToastProvider>
      <AppRouter />
    </ToastProvider>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}
