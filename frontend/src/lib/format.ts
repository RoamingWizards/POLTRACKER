const compactUsd = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  notation: 'compact',
  maximumFractionDigits: 1,
});
const usd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
const int = new Intl.NumberFormat('en-US');

/** Disclosed ranges: $1k – $15k, or "Over $50M" when upstream gives no upper bound. */
export function formatAmountRange(min: number | null, max: number | null): string {
  if (min == null && max == null) return '—';
  if (max == null) return `Over ${compactUsd.format(min ?? 0)}`;
  if (min === max) return compactUsd.format(max);
  return `${compactUsd.format(min ?? 0)} – ${compactUsd.format(max)}`;
}

export const formatUsd = (n: number | null | undefined) => (n == null ? '—' : usd.format(n));
export const formatInt = (n: number | null | undefined) => (n == null ? '—' : int.format(n));

/** Returns arrive as fractions (0.1 = 10%). */
export function formatPct(fraction: number | null | undefined, digits = 1): string {
  if (fraction == null || Number.isNaN(fraction)) return '—';
  const pct = fraction * 100;
  return `${pct > 0 ? '+' : ''}${pct.toFixed(digits)}%`;
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  // The backend stores naive UTC.
  const d = new Date(iso.endsWith('Z') ? iso : `${iso}Z`);
  return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return '—';
  const then = new Date(iso.endsWith('Z') ? iso : `${iso}Z`).getTime();
  const mins = Math.max(0, Math.round((Date.now() - then) / 60_000));
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.round(mins / 60);
  if (hours < 48) return `${hours} h ago`;
  return `${Math.round(hours / 24)} d ago`;
}

export const typeLabel = (t: string) => (t === 'sell_partial' ? 'sell (partial)' : t);
export const isSell = (t: string) => t === 'sell' || t === 'sell_partial';
