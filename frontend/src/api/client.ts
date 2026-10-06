// The browser only ever talks to the POLTRACKER FastAPI backend (never to
// CongressInvests or yfinance).
//
// - Local development: leave VITE_API_BASE_URL unset. Requests go to /api, which the Vite dev
//   server proxies to the backend (see vite.config.ts), so no CORS is involved.
// - Production build: set VITE_API_BASE_URL to the API's public URL at build time, for example
//   https://your-api.example.com (the backend must allow this site's origin via CORS_ORIGINS).
//   The value is baked into the bundle, so it must never contain a secret.
const BASE = (import.meta.env.VITE_API_BASE_URL?.trim() || '/api').replace(/\/+$/, '');

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

type Params = Record<string, string | number | boolean | null | undefined>;

export async function apiGet<T>(path: string, params: Params = {}): Promise<T> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') query.set(key, String(value));
  }
  const qs = query.toString();
  const res = await fetch(`${BASE}${path}${qs ? `?${qs}` : ''}`, { headers: { Accept: 'application/json' } });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}
