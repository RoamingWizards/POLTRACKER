import { useEffect, useRef } from 'react';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, ApiError } from './client';
import type {
  Overview,
  Page,
  Politician,
  RefreshStatus,
  PriceSeries,
  Security,
  SecurityPerformance,
  Status,
  Trade,
  TradeQuery,
  TriggerResult,
} from './types';

export const useTrades = (query: TradeQuery) =>
  useQuery({
    queryKey: ['trades', query],
    queryFn: () => apiGet<Page<Trade>>('/trades', { ...query }),
    placeholderData: keepPreviousData,
  });

export const usePoliticians = (params: { q?: string; chamber?: string }) =>
  useQuery({
    queryKey: ['politicians', params],
    queryFn: () => apiGet<Page<Politician>>('/politicians', { ...params, limit: 500 }),
  });

export const usePolitician = (id: number) =>
  useQuery({ queryKey: ['politician', id], queryFn: () => apiGet<Politician>(`/politicians/${id}`) });

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
    queryFn: () => apiGet<{ status: string }>('/health'),
    refetchInterval: 30_000,
    retry: false,
  });

// Desktop background refresh. The web API has no such route (404), which simply means "no banner".
export function useRefreshStatus() {
  const queryClient = useQueryClient();
  const query = useQuery({
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
