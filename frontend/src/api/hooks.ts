import { useEffect, useRef } from 'react';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, apiSend, ApiError } from './client';
import type {
  ActiveScreen,
  ContextRule,
  FilterSpec,
  PresetsResponse,
  SavedView,
  ScreenPage,
  Overview,
  Page,
  Politician,
  PoliticianDetail,
  RefreshStatus,
  PriceSeries,
  Security,
  SecurityPerformance,
  Status,
  Trade,
  TradeQuery,
  TriggerResult,
} from './types';

export const useTrades = (query: TradeQuery, enabled = true) =>
  useQuery({
    queryKey: ['trades', query],
    queryFn: () => apiGet<Page<Trade>>('/trades', { ...query }),
    placeholderData: keepPreviousData,
    enabled,
  });

export const usePoliticians = (params: { q?: string; chamber?: string }) =>
  useQuery({
    queryKey: ['politicians', params],
    queryFn: () => apiGet<Page<Politician>>('/politicians', { ...params, limit: 500 }),
  });

export const usePolitician = (id: number, enabled = true) =>
  useQuery({ queryKey: ['politician', id], queryFn: () => apiGet<PoliticianDetail>(`/politicians/${id}`), enabled });

export const useSecurity = (ticker: string) =>
  useQuery({
    queryKey: ['security', ticker],
    queryFn: () => apiGet<Security>(`/securities/${ticker}`),
    retry: false,
  });

export const useSecurityPrices = (ticker: string, enabled = true) =>
  useQuery({
    queryKey: ['prices', ticker],
    queryFn: () => apiGet<PriceSeries>(`/securities/${ticker}/prices`),
    enabled,
    staleTime: 5 * 60_000,
  });

export const useSecurityPerformance = (ticker: string) =>
  useQuery({
    queryKey: ['performance', ticker],
    queryFn: () => apiGet<SecurityPerformance>(`/securities/${ticker}/performance`, { limit: 1000 }),
    retry: false,
  });

export const useOverview = (days = 30) =>
  useQuery({ queryKey: ['overview', days], queryFn: () => apiGet<Overview>('/stats/overview', { days }) });

export const useStatus = () =>
  useQuery({ queryKey: ['status'], queryFn: () => apiGet<Status>('/status'), refetchInterval: 60_000 });

export const useHealth = () =>
  useQuery({
    queryKey: ['health'],
    queryFn: () => apiGet<{ status: string; desktop?: boolean }>('/health'),
    refetchInterval: 30_000,
    retry: false,
  });

// Desktop background refresh. The refresh routes exist only in the desktop app, which says so on /health ("desktop": true); anywhere else this
// never makes the request (no 404 in the console) and the banner simply does not appear. The 404 handling stays as a defence.
export function useRefreshStatus() {
  const queryClient = useQueryClient();
  const isDesktop = useHealth().data?.desktop === true;
  const query = useQuery({
    enabled: isDesktop,
    queryKey: ['refresh-status'],
    queryFn: async () => {
      try {
        return await apiGet<RefreshStatus>('/refresh/status');
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) return null;
        throw e;
      }
    },
    refetchInterval: (q) => (q.state.data?.running ? 2_000 : q.state.data === null ? false : 15_000),
    retry: false,
    staleTime: 0,
  });
  // When a refresh finishes, everything on screen may be out of date: reload it in place (no blank state).
  const wasRunning = useRef(false);
  const running = query.data?.running ?? false;
  useEffect(() => {
    if (wasRunning.current && !running) {
      queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] !== 'refresh-status' });
    }
    wasRunning.current = running;
  }, [running, queryClient]);
  return query;
}

export function useTriggerRefresh() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiPost<TriggerResult>('/refresh'),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['refresh-status'] }),
  });
}


// --- Personalization: a custom screen over the STORED trade context. Nothing here changes stored context. ---

export const usePresets = () =>
  useQuery({ queryKey: ['context-presets'], queryFn: () => apiGet<PresetsResponse>('/context/presets'), staleTime: Infinity });

export interface ScreenQuery {
  rule: ContextRule;
  filters: FilterSpec[];
  sort_by?: string;
  order?: 'asc' | 'desc';
  limit: number;
  offset: number;
}

export const useScreen = (q: ScreenQuery, enabled = true) =>
  useQuery({
    enabled,
    queryKey: ['screen', q],
    queryFn: () =>
      apiGet<ScreenPage>('/trades/screen', {
        rule: JSON.stringify(q.rule),
        filters: JSON.stringify(q.filters),
        sort_by: q.sort_by,
        order: q.order,
        limit: q.limit,
        offset: q.offset,
      }),
    placeholderData: keepPreviousData,
  });

// Saved views and the last-used screen are local writes: the desktop app has them, a read-only web API answers 404, which simply means "not available here".
async function orUnavailable<T>(fn: () => Promise<T>): Promise<T | null> {
  try {
    return await fn();
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}

export const useActiveScreen = () =>
  useQuery({ queryKey: ['context-active'], queryFn: () => orUnavailable(() => apiGet<ActiveScreen>('/context/active')), retry: false, staleTime: Infinity });

export const useSavedViews = () =>
  useQuery({ queryKey: ['context-views'], queryFn: () => orUnavailable(() => apiGet<SavedView[]>('/context/views')), retry: false });

export function useViewMutations() {
  const qc = useQueryClient();
  const refresh = () => qc.invalidateQueries({ queryKey: ['context-views'] });
  return {
    create: useMutation({
      mutationFn: (v: { name: string; rule: ContextRule; filters: FilterSpec[]; preset: string | null }) => apiSend<SavedView>('POST', '/context/views', v),
      onSuccess: refresh,
    }),
    update: useMutation({
      mutationFn: ({ id, ...patch }: { id: number; name?: string; rule?: ContextRule; filters?: FilterSpec[]; preset?: string | null }) =>
        apiSend<SavedView>('PATCH', `/context/views/${id}`, patch),
      onSuccess: refresh,
    }),
    remove: useMutation({ mutationFn: (id: number) => apiSend<void>('DELETE', `/context/views/${id}`), onSuccess: refresh }),
  };
}

export const saveActiveScreen = (a: Omit<ActiveScreen, 'saved'>) => apiSend<ActiveScreen>('PUT', '/context/active', a);
export const resetActiveScreen = () => apiSend<ActiveScreen>('DELETE', '/context/active');
