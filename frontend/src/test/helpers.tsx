import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import type { ContextRule, Preset, SavedView, FilterSpec } from '../api/types';
import { DEFAULT_RULE } from '../lib/filters';

export function wrap(ui: ReactNode, route = '/trades') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

const rule = (over: Partial<ContextRule> = {}): ContextRule => ({ ...DEFAULT_RULE, ...over });

export const PRESETS: Preset[] = [
  { key: 'balanced', label: 'Balanced', kind: 'default', description: 'The default methodology', notes: ['n'], rule: rule() },
  { key: 'strict', label: 'Strict', kind: 'custom', description: 'Narrower', notes: ['n'], rule: rule({ minimum_secondary_signals: 3, trade_size_percentile_threshold: 95, disclosure_delay_threshold_days: 60, excess_return_threshold_pct_points: 25 }) },
  { key: 'committee_focus', label: 'Committee focus', kind: 'committee_only', description: 'Browse by committee', notes: ['n'], rule: rule({ minimum_secondary_signals: 0 }) },
  { key: 'market_focus', label: 'Market focus', kind: 'market_only', description: 'Market signals', notes: ['n'], rule: rule({ committee_relevance_required: false }) },
];

/** An in-memory stand-in for the local API, so tests never touch a network. */
export function fakeApi(opts: { persistent?: boolean; views?: SavedView[] } = {}) {
  const persistent = opts.persistent ?? true;
  let nextId = 100;
  const state = {
    views: [...(opts.views ?? [])],
    active: null as null | { rule: ContextRule; filters: FilterSpec[]; preset: string | null; view_id: number | null },
    calls: [] as string[],
  };
  const json = (body: unknown, status = 200) => new Response(status === 204 ? null : JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
  const handler = async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), 'http://localhost');
    const path = url.pathname.replace(/^\/api/, '');
    const method = (init?.method ?? 'GET').toUpperCase();
    state.calls.push(`${method} ${path}`);
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    if (path === '/context/presets') return json({ default_rule: DEFAULT_RULE, presets: PRESETS, kind_labels: {}, notice: '' });
    if (path.startsWith('/context/') && !persistent) return json({ detail: 'Not Found' }, 404);
    if (path === '/context/active') {
      if (method === 'PUT') {
        state.active = body;
        return json({ ...body, saved: true });
      }
      if (method === 'DELETE') {
        state.active = null;
        return json({ rule: DEFAULT_RULE, filters: [], preset: 'balanced', view_id: null, saved: false });
      }
      return json(state.active ? { ...state.active, saved: true } : { rule: DEFAULT_RULE, filters: [], preset: 'balanced', view_id: null, saved: false });
    }
    if (path === '/context/views' && method === 'GET') return json(state.views);
    if (path === '/context/views' && method === 'POST') {
      if (state.views.some((v) => v.name.toLowerCase() === body.name.toLowerCase())) return json({ detail: `a view named '${body.name}' already exists` }, 409);
      const v: SavedView = { id: nextId++, name: body.name, preset: body.preset, rule: body.rule, filters: body.filters, created_at: 'x', updated_at: 'x' };
      state.views.push(v);
      return json(v, 201);
    }
    const m = path.match(/^\/context\/views\/(\d+)$/);
    if (m && method === 'PATCH') {
      const v = state.views.find((x) => x.id === Number(m[1]))!;
      Object.assign(v, body);
      return json(v);
    }
    if (m && method === 'DELETE') {
      state.views = state.views.filter((x) => x.id !== Number(m[1]));
      return json(null, 204);
    }
    return json({ detail: 'unexpected ' + path }, 500);
  };
  return { state, handler };
}
