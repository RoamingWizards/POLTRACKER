import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { apiGet } from './client';
import type {
  Overview,
  Page,
  Politician,
  PriceSeries,
  Security,
  SecurityPerformance,
  Status,
  Trade,
  TradeQuery,
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
