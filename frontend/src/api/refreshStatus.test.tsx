import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { useRefreshStatus } from './hooks';

const wrapper = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })}>{children}</QueryClientProvider>
);

function backend(health: object, refresh: object | null = null) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    if (path.endsWith('/health')) return new Response(JSON.stringify(health), { status: 200 });
    if (path.endsWith('/refresh/status')) return refresh ? new Response(JSON.stringify(refresh), { status: 200 }) : new Response('{}', { status: 404 });
    return new Response('{}', { status: 500 });
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

describe('refresh status (desktop only)', () => {
  it('never requests /refresh/status from the read-only web API, so there is no 404 to log', async () => {
    const fetchMock = backend({ status: 'ok' });
    const { result } = renderHook(() => useRefreshStatus(), { wrapper });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/health', expect.anything()));
    await new Promise((r) => setTimeout(r, 100));
    expect(fetchMock.mock.calls.map((c) => String(c[0]))).toEqual(['/api/health']);
    expect(result.current.data).toBeUndefined();
  });

  it('still gets the refresh status in the desktop app', async () => {
    const status = { enabled: true, running: false, phase: 'idle', interval_hours: 6, database_empty: false };
    const fetchMock = backend({ status: 'ok', desktop: true }, status);
    const { result } = renderHook(() => useRefreshStatus(), { wrapper });
    await waitFor(() => expect(result.current.data).toEqual(status));
    expect(fetchMock.mock.calls.map((c) => String(c[0]))).toContain('/api/refresh/status');
  });
});
