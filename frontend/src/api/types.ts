// Mirrors backend/poltracker/api/schemas.py.

export type Chamber = 'house' | 'senate';
export type TransactionType = 'buy' | 'sell' | 'sell_partial' | 'exchange' | 'unknown';

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface Trade {
  id: number;
  source: string;
  politician_id: number;
  security_id: number | null;
  politician_name: string;
  chamber: Chamber;
  party: string | null;
  state: string | null;
  ticker: string | null;
  asset_name: string | null;
  transaction_type: TransactionType;
  transaction_date: string;
  disclosure_date: string | null;
  amount_min: number | null;
  amount_max: number | null;
  source_url: string | null;
  /** Same politician + security + transaction date + type. Display grouping only: rows are never merged. */
  group_key?: string | null;
  group_size?: number | null;
  /** Null until the context analyzer has run. */
  context?: TradeContext | null;
}

export interface ContextEvidence {
  signal_type: string;
  evidence_type: 'reviewed_direct_mapping' | 'reviewed_related_mapping' | 'rejected_current_assignment' | 'metric';
  committee_code: string | null;
  subcommittee_code: string | null;
  source_url: string | null;
  description: string;
  metadata: Record<string, unknown> | null;
}

/** An OpenAI-written explanation of the stored facts, validated against them. It explains; it never sets a signal or the flag. */
export interface AiContext {
  headline: string;
  summary: string;
  signals: { type: string; explanation: string }[];
  limitations: string;
  generated_for: 'flagged' | 'manual';
  model: string;
  prompt_version: string;
  generated_at: string;
}

/** Deterministic context signals from public data. A signal is true, false, or null (unknown). */
export interface TradeContext {
  context_version: string;
  mapping_version: string | null;
  analyzed_at: string;
  committee_relevance: boolean | null;
  committee_relevance_reason: string | null;
  trade_size_anomaly: boolean | null;
  trade_size_value: number | null;
  trade_size_basis: string | null;
  trade_size_percentile: number | null;
  trade_size_sample_size: number | null;
  disclosure_delay_signal: boolean | null;
  disclosure_delay_days: number | null;
  excess_return_signal: boolean | null;
  security_return: number | null;
  spy_return: number | null;
  excess_return: number | null;
  excess_return_direction_adjusted: number | null;
  excess_horizon_days: number | null;
  signals: Record<string, boolean | null>;
  signal_count: number;
  secondary_signal_count: number | null;
  committee_temporal_status: 'temporally_verified' | 'current_assignment_only' | 'unavailable' | 'contradicted' | null;
  meets_flag_rule: boolean | null;
  flag_pending_temporal_verification: boolean;
  flagged_for_contextual_review: boolean;
  evidence: ContextEvidence[];
  notice: string;
  ai_context?: AiContext | null;
}

export type TradeSortField =
  | 'transaction_date'
  | 'disclosure_date'
  | 'amount_min'
  | 'ticker'
  | 'politician_name';

export interface TradeQuery {
  ticker?: string;
  politician_id?: number;
  chamber?: Chamber;
  transaction_type?: string;
  date_from?: string;
  date_to?: string;
  flagged?: boolean;
  sort_by?: TradeSortField;
  order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}

export interface Politician {
  id: number;
  name: string;
  chamber: Chamber;
  party: string | null;
  state: string | null;
  trade_count: number;
  latest_trade_date: string | null;
  // Official enrichment: all null until the politician has been verified against an official roster.
  bioguide_id: string | null;
  district: string | null;
  official_url: string | null;
  active: boolean | null;
  term_start_year: number | null;
  term_end_year: number | null;
  enriched_at: string | null;
  enrichment_source: string | null;
  enrichment_status: 'matched' | 'unmatched' | 'ambiguous' | 'conflict' | 'review' | null;
  enrichment_method: string | null;
}

export interface CommitteeSeat {
  committee_name: string;
  committee_code: string;
  subcommittee_name: string | null;
  subcommittee_code: string;
  role: string;
  chamber: Chamber;
  start_date: string | null;
  end_date: string | null;
  source: string;
  source_url: string | null;
}

export interface PoliticianDetail extends Politician {
  committees: CommitteeSeat[];
}

export interface Security {
  id: number;
  ticker: string;
  name: string | null;
  price_status: 'ok' | 'unavailable' | null;
  price_from: string | null;
  price_to: string | null;
  trade_count: number;
  latest_trade_date: string | null;
  recent_trades: Trade[];
  // Official company profile (SEC EDGAR); null until enriched or when the source does not list the ticker.
  company_name?: string | null;
  cik?: string | null;
  sic_code?: string | null;
  industry?: string | null;
  sector?: string | null;
  exchange?: string | null;
  profile_status?: 'ok' | 'partial' | 'unresolved' | null;
  profile_source_url?: string | null;
}

export interface PriceBar {
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  adj_close: number | null;
  volume: number | null;
}

export interface PriceSeries {
  ticker: string;
  price_status: 'ok' | 'unavailable' | null;
  price_from: string | null;
  price_to: string | null;
  bars: PriceBar[];
}

export interface Leg {
  status: string;
  anchor_date: string | null;
  price: number | null;
  return: number | null;
  benchmark_return: number | null;
  excess_return: number | null;
}

export interface Performance {
  status: string;
  detail: string | null;
  benchmark: string | null;
  latest_date: string | null;
  latest_price: number | null;
  direction: number | null;
  transaction: Leg | null;
  disclosure: Leg | null;
  direction_adjusted: Record<string, number | null>;
}

export interface TradePerformance {
  trade: Trade;
  performance: Performance;
}

export interface SecurityPerformance {
  ticker: string;
  benchmark: string;
  status_counts: Record<string, number>;
  total: number;
  items: TradePerformance[];
}

export interface Overview {
  window_days: number;
  totals: {
    trades: number;
    politicians: number;
    securities: number;
    trades_in_window: number;
    buys_in_window: number;
    sells_in_window: number;
  };
  latest_disclosure_date: string | null;
  daily: { date: string; count: number }[];
  monthly: { month: string; buys: number; sells: number; other: number }[];
  top_tickers: { ticker: string; name: string | null; trades: number; buys: number; sells: number }[];
  top_politicians: { id: number; name: string; chamber: Chamber; trades: number }[];
}

export interface Status {
  trades_total: number;
  trades_by_source: Record<string, number>;
  politicians_total: number;
  latest_disclosure_date: string | null;
  latest_transaction_date: string | null;
  last_ingested_at: string | null; // when the newest trade row was inserted
  last_successful_ingest_at: string | null; // when the last ingest run finished without error
  ingest_age_hours: number | null;
  ingest_stale_after_hours: number;
  ingest_stale: boolean;
  invalid_date_trades: number;
  securities_total: number;
  securities_priced: number;
  securities_unavailable: number;
  securities_pending: number;
  price_bars: number;
  latest_bar_date: string | null;
  benchmark_ticker: string;
  benchmark_from: string | null;
  benchmark_to: string | null;
  benchmark_status: string | null;
}

// Desktop app only: the background refresh service (absent from the web API, which answers 404).
export interface RefreshStatus {
  enabled: boolean;
  running: boolean;
  phase: 'idle' | 'ingesting' | 'prices';
  trigger: 'startup' | 'scheduled' | 'manual' | null;
  label: string | null;
  progress: { done: number; total: number | null } | null;
  started_at: string | null;
  finished_at: string | null;
  last_attempt_ok: boolean | null;
  last_error: string | null;
  last_success_at: string | null;
  next_run_at: string | null;
  interval_hours: number;
  database_empty: boolean;
}

export interface TriggerResult {
  accepted: boolean;
  reason: string;
}
