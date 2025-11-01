/**
 * Test utilities for React Testing Library
 *
 * Provides custom render function with:
 * - React Query provider
 * - Router context
 * - User event helpers
 */

import { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import userEvent from '@testing-library/user-event';

/**
 * Create a new QueryClient for each test to ensure isolation
 */
export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        cacheTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

/**
 * Custom render function with providers
 */
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  queryClient?: QueryClient;
}

export function renderWithProviders(
  ui: ReactElement,
  options?: CustomRenderOptions
) {
  const { queryClient = createTestQueryClient(), ...renderOptions } =
    options || {};

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  }

  return {
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
    queryClient,
  };
}

/**
 * Create user event instance with default options
 */
export function setupUser() {
  return userEvent.setup();
}

/**
 * Wait for all async operations to complete
 */
export async function waitForLoadingToFinish() {
  const { waitForElementToBeRemoved } = await import('@testing-library/react');
  return waitForElementToBeRemoved(() => document.querySelector('[data-testid="loading"]'), {
    timeout: 3000,
  }).catch(() => {
    // Ignore if no loading element found
  });
}

/**
 * Mock API response helper
 */
export function mockApiResponse(data: any, status = 200) {
  return Promise.resolve({
    data,
    status,
    statusText: 'OK',
    headers: {},
    config: {} as any,
  });
}

/**
 * Mock API error helper
 */
export function mockApiError(message: string, status = 500) {
  return Promise.reject({
    response: {
      data: { detail: message },
      status,
      statusText: 'Error',
      headers: {},
      config: {} as any,
    },
  });
}

// Re-export everything from React Testing Library
export * from '@testing-library/react';
export { userEvent };
