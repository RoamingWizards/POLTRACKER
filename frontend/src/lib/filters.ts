// Pure logic for the Trades page's personalization: filter definitions, editing helpers and rule helpers. No React, no network.
import type { ContextRule, FilterField, FilterSpec, Preset, RuleKind } from '../api/types';

/** The canonical production methodology. Mirrors the server's default rule; the server is the authority (GET /context/presets). */
export const DEFAULT_RULE: ContextRule = {
  committee_relevance_required: true,
  reviewed_direct_only: true,
  require_temporal_verification: true,
  enable_trade_size_signal: true,
  trade_size_percentile_threshold: 90,
  enable_disclosure_delay_signal: true,
  disclosure_delay_threshold_days: 45,
  enable_excess_return_signal: true,
  excess_return_threshold_pct_points: 20,
  minimum_secondary_signals: 2,
};

export type InputKind = 'text' | 'number' | 'date' | 'daterange' | 'enum' | 'list';

export interface OpDef {
  op: string;
  label: string;
}

export interface FieldDef {
  field: FilterField;
  label: string;
  group: 'Trade' | 'Politician' | 'Security' | 'Context' | 'Review';
  kind: InputKind;
  ops: OpDef[];
  options?: { value: string; label: string }[];
  unit?: string;
  hint?: string;
}

const YES_NO = [{ value: 'yes', label: 'Yes' }, { value: 'no', label: 'No' }, { value: 'unknown', label: 'Unknown' }];

export const FIELD_DEFS: FieldDef[] = [
  { field: 'politician', label: 'Politician', group: 'Politician', kind: 'text', ops: [{ op: 'contains', label: 'name contains' }], hint: 'Part of the politician’s name' },
  { field: 'chamber', label: 'Chamber', group: 'Politician', kind: 'enum', ops: [{ op: 'is', label: 'is' }], options: [{ value: 'house', label: 'House' }, { value: 'senate', label: 'Senate' }] },
  { field: 'party', label: 'Party', group: 'Politician', kind: 'text', ops: [{ op: 'is', label: 'is' }], hint: 'For example D or R (blank upstream for some members)' },
  { field: 'state', label: 'State', group: 'Politician', kind: 'text', ops: [{ op: 'is', label: 'is' }], hint: 'Two-letter code, for example CA' },
  { field: 'district', label: 'District', group: 'Politician', kind: 'text', ops: [{ op: 'is', label: 'is' }], hint: 'House district number' },
  { field: 'ticker', label: 'Ticker', group: 'Security', kind: 'text', ops: [{ op: 'is', label: 'is' }, { op: 'contains', label: 'contains' }] },
  { field: 'company', label: 'Company', group: 'Security', kind: 'text', ops: [{ op: 'contains', label: 'name contains' }] },
  { field: 'industry', label: 'Industry', group: 'Security', kind: 'text', ops: [{ op: 'contains', label: 'SIC description contains' }], hint: 'For example Aircraft or Pharmaceutical' },
  {
    field: 'transaction_type', label: 'Transaction type', group: 'Trade', kind: 'enum', ops: [{ op: 'is', label: 'is' }],
    options: [{ value: 'buy', label: 'Buy' }, { value: 'sell', label: 'Sell' }, { value: 'sell_partial', label: 'Sell (partial)' }, { value: 'exchange', label: 'Exchange' }],
  },
  { field: 'transaction_date', label: 'Transaction date', group: 'Trade', kind: 'date', ops: [{ op: 'gte', label: 'on or after' }, { op: 'lte', label: 'on or before' }, { op: 'between', label: 'between' }] },
  { field: 'disclosure_date', label: 'Disclosure date', group: 'Trade', kind: 'date', ops: [{ op: 'gte', label: 'on or after' }, { op: 'lte', label: 'on or before' }, { op: 'between', label: 'between' }] },
  {
    field: 'value', label: 'Disclosed value range', group: 'Trade', kind: 'number', unit: 'USD',
    ops: [{ op: 'gte', label: 'minimum is at least' }, { op: 'lte', label: 'maximum is at most' }], hint: 'Disclosures are ranges, never exact values',
  },
  { field: 'committee_relevance', label: 'Committee relevance', group: 'Context', kind: 'enum', ops: [{ op: 'is', label: 'is' }], options: YES_NO },
  { field: 'committee_name', label: 'Committee name', group: 'Context', kind: 'text', ops: [{ op: 'contains', label: 'in context evidence contains' }], hint: 'A committee or subcommittee behind the stored committee evidence' },
  { field: 'trade_size_percentile', label: 'Trade size percentile', group: 'Context', kind: 'number', unit: 'percentile', ops: [{ op: 'gte', label: '≥' }, { op: 'lte', label: '≤' }], hint: 'Among this member’s own earlier trades' },
  { field: 'disclosure_delay', label: 'Disclosure delay', group: 'Context', kind: 'number', unit: 'days', ops: [{ op: 'gte', label: '≥' }, { op: 'lte', label: '≤' }] },
  {
    field: 'excess_return', label: 'Excess return', group: 'Context', kind: 'number', unit: 'pp',
    ops: [{ op: 'abs_gte', label: '|value| ≥' }, { op: 'gte', label: '≥' }, { op: 'lte', label: '≤' }], hint: 'Percentage points versus SPY over 90 days',
  },
  { field: 'active_signals', label: 'Active signals', group: 'Context', kind: 'number', unit: 'signals', ops: [{ op: 'gte', label: '≥' }, { op: 'lte', label: '≤' }, { op: 'eq', label: '=' }], hint: 'Signals active under the current rule settings' },
  { field: 'review_status', label: 'Contextual-review status', group: 'Review', kind: 'enum', ops: [{ op: 'is', label: 'is' }], options: [{ value: 'flagged', label: 'Flagged (default methodology)' }, { value: 'not_flagged', label: 'Not flagged' }] },
  { field: 'custom_screen', label: 'Custom screen', group: 'Review', kind: 'enum', ops: [{ op: 'is', label: 'is' }], options: [{ value: 'match', label: 'Match' }, { value: 'no_match', label: 'No match' }] },
  { field: 'ai_context', label: 'AI context', group: 'Review', kind: 'enum', ops: [{ op: 'is', label: 'is' }], options: [{ value: 'available', label: 'Available' }, { value: 'unavailable', label: 'Not generated' }] },
];

export const fieldDef = (field: FilterField): FieldDef => FIELD_DEFS.find((d) => d.field === field)!;

const money = (n: number) => `$${Math.round(n).toLocaleString('en-US')}`;

/** The text on a filter chip, for example "Excess return: |value| ≥ 20 pp". */
export function describeFilter(f: FilterSpec): string {
  const def = fieldDef(f.field);
  const op = def.ops.find((o) => o.op === f.op)?.label ?? f.op;
  const v = f.value;
  let value: string;
  if (f.field === 'politician' && f.op === 'is') value = `#${v}`;
  else if (Array.isArray(v)) value = v.length === 2 && def.kind === 'date' ? `${v[0]} – ${v[1]}` : v.join(', ');
  else if (def.kind === 'enum') value = def.options?.find((o) => o.value === v)?.label ?? String(v);
  else if (f.field === 'value') value = money(Number(v));
  else if (def.unit && def.kind === 'number') value = `${v} ${def.unit === 'USD' ? '' : def.unit}`.trim();
  else value = String(v);
  const needsOpWord = def.ops.length > 1 || def.kind === 'date' || f.op === 'contains';
  return `${def.label}: ${needsOpWord || def.kind === 'number' ? `${op} ` : ''}${value}`;
}

export function defaultFilter(field: FilterField): FilterSpec {
  const def = fieldDef(field);
  const op = def.ops[0].op;
  const value = def.kind === 'enum' ? def.options![0].value : def.kind === 'number' ? (field === 'excess_return' ? 20 : field === 'trade_size_percentile' ? 90 : field === 'disclosure_delay' ? 45 : field === 'active_signals' ? 2 : 0) : '';
  return { field, op, value };
}

/** A filter is complete when its value is usable. The server validates again. */
export function isCompleteFilter(f: FilterSpec): boolean {
  const def = fieldDef(f.field);
  if (!def.ops.some((o) => o.op === f.op)) return false;
  if (f.op === 'between') return Array.isArray(f.value) && f.value.length === 2 && f.value.every((x) => /^\d{4}-\d{2}-\d{2}$/.test(String(x)));
  if (def.kind === 'number') return typeof f.value === 'number' ? Number.isFinite(f.value) : String(f.value).trim() !== '' && Number.isFinite(Number(f.value));
  if (def.kind === 'date') return /^\d{4}-\d{2}-\d{2}$/.test(String(f.value));
  if (def.kind === 'enum') return !!def.options?.some((o) => o.value === f.value);
  return typeof f.value === 'string' && f.value.trim() !== '';
}

export const normalizeFilter = (f: FilterSpec): FilterSpec => {
  const def = fieldDef(f.field);
  if (def.kind === 'number') return { ...f, value: Number(f.value) };
  if (typeof f.value === 'string') return { ...f, value: f.value.trim() };
  return f;
};

// List operations. A filter list is combined with AND.
export const addFilter = (list: FilterSpec[], f: FilterSpec): FilterSpec[] => [...list, normalizeFilter(f)];
export const editFilter = (list: FilterSpec[], index: number, f: FilterSpec): FilterSpec[] => list.map((x, i) => (i === index ? normalizeFilter(f) : x));
export const removeFilter = (list: FilterSpec[], index: number): FilterSpec[] => list.filter((_, i) => i !== index);
export const clearFilters = (): FilterSpec[] => [];

/** Older links use query parameters (/trades?ticker=BA&politician_id=3). Turn them into filters once; the page then keeps filters in its own state. */
export function filtersFromLegacyParams(params: URLSearchParams): FilterSpec[] {
  const out: FilterSpec[] = [];
  const ticker = params.get('ticker');
  if (ticker) out.push({ field: 'ticker', op: 'is', value: ticker.toUpperCase() });
  const chamber = params.get('chamber');
  if (chamber === 'house' || chamber === 'senate') out.push({ field: 'chamber', op: 'is', value: chamber });
  const type = params.get('type');
  if (type) out.push({ field: 'transaction_type', op: 'is', value: type });
  const pid = Number(params.get('politician_id'));
  if (pid) out.push({ field: 'politician', op: 'is', value: pid });
  const from = params.get('from');
  const to = params.get('to');
  if (from && to) out.push({ field: 'transaction_date', op: 'between', value: [from, to] });
  else if (from) out.push({ field: 'transaction_date', op: 'gte', value: from });
  else if (to) out.push({ field: 'transaction_date', op: 'lte', value: to });
  if (params.get('flagged') === '1') out.push({ field: 'review_status', op: 'is', value: 'flagged' });
  return out;
}

export const LEGACY_PARAMS = ['ticker', 'chamber', 'type', 'politician_id', 'from', 'to', 'flagged'];

export const rulesEqual = (a: ContextRule, b: ContextRule): boolean => (Object.keys(a) as (keyof ContextRule)[]).every((k) => a[k] === b[k]);

/** The built-in preset whose rule equals this one, else 'custom'. */
export function detectPreset(rule: ContextRule, presets: Preset[]): string {
  return presets.find((p) => rulesEqual(p.rule, rule))?.key ?? 'custom';
}

/** Why a rule cannot be applied, mirroring the server's checks (the server validates again). Null when it is fine. */
export function ruleProblem(rule: ContextRule): string | null {
  const enabled = [rule.enable_trade_size_signal, rule.enable_disclosure_delay_signal, rule.enable_excess_return_signal].filter(Boolean).length;
  if (rule.minimum_secondary_signals > enabled) return `Needs ${rule.minimum_secondary_signals} secondary signals but only ${enabled} ${enabled === 1 ? 'is' : 'are'} enabled.`;
  if (!rule.committee_relevance_required && rule.minimum_secondary_signals < 1) return 'Without committee relevance, at least one secondary signal is needed, or every trade would match.';
  if (rule.trade_size_percentile_threshold < 0 || rule.trade_size_percentile_threshold > 100) return 'The percentile threshold is between 0 and 100.';
  if (rule.disclosure_delay_threshold_days < 0) return 'The delay threshold cannot be negative.';
  if (rule.excess_return_threshold_pct_points < 0) return 'The excess-return threshold cannot be negative.';
  return null;
}

export function ruleKind(rule: ContextRule): RuleKind {
  if (rulesEqual(rule, DEFAULT_RULE)) return 'default';
  if (!rule.committee_relevance_required) return 'market_only';
  return rule.minimum_secondary_signals === 0 ? 'committee_only' : 'custom';
}

export const KIND_LABEL: Record<RuleKind, string> = {
  default: 'Default methodology',
  custom: 'Custom screen',
  committee_only: 'Browsing by committee relevance (not the contextual-review flag)',
  market_only: 'Market-signal screen (does not indicate political context)',
};
