import { describe, expect, it } from 'vitest';
import type { FilterSpec, Preset } from '../api/types';
import {
  DEFAULT_RULE, FIELD_DEFS, addFilter, clearFilters, defaultFilter, describeFilter, detectPreset, editFilter, filtersFromLegacyParams, isCompleteFilter, removeFilter, ruleKind,
  ruleProblem,
} from './filters';

const f = (field: FilterSpec['field'], op: string, value: FilterSpec['value']): FilterSpec => ({ field, op, value });

describe('default rule', () => {
  it('is the canonical production methodology', () => {
    expect(DEFAULT_RULE).toEqual({
      committee_relevance_required: true, reviewed_direct_only: true, require_temporal_verification: true,
      enable_trade_size_signal: true, trade_size_percentile_threshold: 90,
      enable_disclosure_delay_signal: true, disclosure_delay_threshold_days: 45,
      enable_excess_return_signal: true, excess_return_threshold_pct_points: 20, minimum_secondary_signals: 2,
    });
    expect(ruleKind(DEFAULT_RULE)).toBe('default');
    expect(ruleProblem(DEFAULT_RULE)).toBeNull();
  });
});

describe('filter chips', () => {
  it.each([
    [f('committee_relevance', 'is', 'yes'), 'Committee relevance: Yes'],
    [f('excess_return', 'abs_gte', 20), 'Excess return: |value| ≥ 20 pp'],
    [f('trade_size_percentile', 'gte', 90), 'Trade size percentile: ≥ 90 percentile'],
    [f('disclosure_delay', 'gte', 46), 'Disclosure delay: ≥ 46 days'],
    [f('transaction_date', 'between', ['2026-01-01', '2026-02-01']), 'Transaction date: between 2026-01-01 – 2026-02-01'],
    [f('value', 'gte', 50000), 'Disclosed value range: minimum is at least $50,000'],
    [f('review_status', 'is', 'flagged'), 'Contextual-review status: Flagged (default methodology)'],
    [f('custom_screen', 'is', 'match'), 'Custom screen: Match'],
    [f('ticker', 'is', 'BA'), 'Ticker: is BA'],
  ])('describes %j', (spec, text) => {
    expect(describeFilter(spec)).toBe(text);
  });

  it('offers every filter the spec asks for', () => {
    expect(FIELD_DEFS.map((d) => d.label)).toEqual(
      expect.arrayContaining([
        'Politician', 'Chamber', 'Party', 'State', 'District', 'Ticker', 'Company', 'Industry', 'Transaction type', 'Transaction date', 'Disclosure date', 'Disclosed value range',
        'Committee relevance', 'Committee name', 'Trade size percentile', 'Disclosure delay', 'Excess return', 'Active signals', 'Contextual-review status', 'AI context',
      ]),
    );
  });

  it('only completes filters with usable values', () => {
    expect(isCompleteFilter(f('ticker', 'is', ''))).toBe(false);
    expect(isCompleteFilter(f('ticker', 'is', ' BA '))).toBe(true);
    expect(isCompleteFilter(f('excess_return', 'abs_gte', ''))).toBe(false);
    expect(isCompleteFilter(f('excess_return', 'abs_gte', 12.5))).toBe(true);
    expect(isCompleteFilter(f('transaction_date', 'between', ['2026-01-01', '']))).toBe(false);
    expect(isCompleteFilter(defaultFilter('chamber'))).toBe(true);
    expect(isCompleteFilter(f('chamber', 'gte', 'house'))).toBe(false);
  });
});

describe('editing a filter list', () => {
  it('adds, edits, removes and clears; filters combine with AND', () => {
    const a = f('ticker', 'is', 'BA');
    const b = f('excess_return', 'abs_gte', '20');
    let list = addFilter([], a);
    list = addFilter(list, b);
    expect(list).toEqual([a, { ...b, value: 20 }]); // numbers are normalised
    list = editFilter(list, 1, f('excess_return', 'abs_gte', 25));
    expect(list[1].value).toBe(25);
    expect(removeFilter(list, 0)).toEqual([list[1]]);
    expect(clearFilters()).toEqual([]);
    expect(list).toHaveLength(2); // the originals are never mutated
  });
});

describe('older links', () => {
  it('turn query parameters into filters', () => {
    const got = filtersFromLegacyParams(new URLSearchParams('ticker=ba&chamber=house&type=sell&politician_id=7&from=2026-01-01&to=2026-02-01&flagged=1'));
    expect(got).toEqual([
      f('ticker', 'is', 'BA'), f('chamber', 'is', 'house'), f('transaction_type', 'is', 'sell'), f('politician', 'is', 7),
      f('transaction_date', 'between', ['2026-01-01', '2026-02-01']), f('review_status', 'is', 'flagged'),
    ]);
    expect(filtersFromLegacyParams(new URLSearchParams(''))).toEqual([]);
  });
});

describe('rules', () => {
  const preset = (key: string, rule: Preset['rule']): Preset => ({ key, label: key, kind: 'default', description: '', notes: [], rule });
  it('detects a built-in preset, else custom', () => {
    const strict = { ...DEFAULT_RULE, minimum_secondary_signals: 3 };
    expect(detectPreset(strict, [preset('balanced', DEFAULT_RULE), preset('strict', strict)])).toBe('strict');
    expect(detectPreset({ ...DEFAULT_RULE, trade_size_percentile_threshold: 80 }, [preset('balanced', DEFAULT_RULE)])).toBe('custom');
  });
  it('labels performance-only and committee-only screens so they are never mistaken for the flag', () => {
    expect(ruleKind({ ...DEFAULT_RULE, committee_relevance_required: false })).toBe('market_only');
    expect(ruleKind({ ...DEFAULT_RULE, minimum_secondary_signals: 0 })).toBe('committee_only');
    expect(ruleKind({ ...DEFAULT_RULE, minimum_secondary_signals: 1 })).toBe('custom');
  });
  it('explains an impossible rule', () => {
    expect(ruleProblem({ ...DEFAULT_RULE, enable_excess_return_signal: false, minimum_secondary_signals: 3 })).toMatch(/only 2 are enabled/);
    expect(ruleProblem({ ...DEFAULT_RULE, committee_relevance_required: false, minimum_secondary_signals: 0 })).toMatch(/every trade would match/);
  });
});
