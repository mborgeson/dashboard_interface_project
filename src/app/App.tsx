import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ToastProvider } from '@/contexts/ToastContext';
import { QuickActionsProvider, useQuickActions } from '@/contexts/QuickActionsContext';
import { AppRouter } from './router';
import { usePrefetchDashboard } from '@/hooks/usePrefetchDashboard';
import { CommandPalette } from '@/components/quick-actions/CommandPalette';
import { FloatingActionButton } from '@/components/quick-actions/FloatingActionButton';
import { KeyboardShortcutsProvider } from '@/components/quick-actions/KeyboardShortcuts';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
});

/**
 * Quick actions integration component
 * Renders command palette and FAB with access to context
 */
function QuickActionsIntegration() {
  const { commandPaletteOpen, closeCommandPalette } = useQuickActions();

  return (
    <>
      <CommandPalette open={commandPaletteOpen} onOpenChange={closeCommandPalette} />
      <FloatingActionButton />
    </>
  );
}

/**
 * Inner app component that has access to QueryClient context
 * Required for prefetch hook to work
 */
function AppContent() {
  // Prefetch common dashboard data on app initialization
  usePrefetchDashboard();

  return (
    <ToastProvider>
      <QuickActionsProvider>
        <KeyboardShortcutsProvider>
          <AppRouter />
          <QuickActionsIntegration />
        </KeyboardShortcutsProvider>
      </QuickActionsProvider>
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
