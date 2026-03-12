/**
 * Shared test render utility with all providers pre-configured.
 *
 * Wraps the component under test with QueryClientProvider, ToastProvider,
 * and a MemoryRouter. For hook-only tests, exports createTestQueryClient
 * and createWrapper (for renderHook's wrapper option).
 */
import type { ReactElement, ReactNode } from 'react';
import { render, type RenderOptions } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ToastProvider } from '@/contexts/ToastContext';
import React from 'react';

// ---------------------------------------------------------------------------
// QueryClient factory
// ---------------------------------------------------------------------------

/** Create a fresh, test-safe QueryClient (no retries, instant GC). */
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

// ---------------------------------------------------------------------------
// renderWithProviders (for component tests)
// ---------------------------------------------------------------------------

interface RenderWithProvidersOptions extends Omit<RenderOptions, 'wrapper'> {
  /** Initial route for the MemoryRouter. Defaults to "/". */
  route?: string;
  /** Supply a custom QueryClient (e.g. with pre-seeded cache). */
  queryClient?: QueryClient;
}

/**
 * Render a React element wrapped in QueryClientProvider, ToastProvider,
 * and MemoryRouter. Returns the standard RTL render result plus the
 * queryClient instance for cache assertions.
 */
export function renderWithProviders(
  ui: ReactElement,
  options?: RenderWithProvidersOptions,
) {
  const { route = '/', queryClient: qc, ...renderOptions } = options ?? {};
  const queryClient = qc ?? createTestQueryClient();

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <MemoryRouter
            initialEntries={[route]}
            future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
          >
            {children}
          </MemoryRouter>
        </ToastProvider>
      </QueryClientProvider>
    );
  }

  return {
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
    queryClient,
  };
}

// ---------------------------------------------------------------------------
// createWrapper (for renderHook tests)
// ---------------------------------------------------------------------------

interface CreateWrapperOptions {
  /** Supply a custom QueryClient. */
  queryClient?: QueryClient;
  /** Whether to include MemoryRouter. Defaults to false for hook tests. */
  withRouter?: boolean;
  /** Initial route when withRouter is true. */
  route?: string;
}

/**
 * Create a wrapper component suitable for `renderHook({ wrapper })`.
 *
 * By default only wraps with QueryClientProvider (sufficient for most hooks).
 * Pass `withRouter: true` if the hook reads from the router context.
 */
export function createWrapper(options?: CreateWrapperOptions) {
  const queryClient = options?.queryClient ?? createTestQueryClient();
  const withRouter = options?.withRouter ?? false;
  const route = options?.route ?? '/';

  return function Wrapper({ children }: { children: ReactNode }) {
    const inner = React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );

    if (withRouter) {
      return (
        <MemoryRouter
          initialEntries={[route]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          {inner}
        </MemoryRouter>
      );
    }

    return inner;
  };
}
