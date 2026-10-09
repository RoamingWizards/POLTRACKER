import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { CustomScreen, Trade } from '../api/types';
import { wrap } from '../test/helpers';
import TradeContextDialog, { CustomScreenSection } from './TradeContextDialog';

const cs = (over: Partial<CustomScreen> = {}): CustomScreen => ({
  matches: true, active_signals: ['trade_size_anomaly', 'excess_return_signal'], active_signal_count: 2, kind: 'market_only',
  kind_label: 'Market-signal screen (does not indicate political context)', canonical_flag: false, differs_from_canonical: true, ...over,
});

const context = (flagged: boolean) => ({
  context_version: '2026.3', mapping_version: 'v1', analyzed_at: '2026-10-09T00:00:00', committee_relevance: false, committee_relevance_reason: 'no_reviewed_direct_match',
  trade_size_anomaly: true, trade_size_value: 1, trade_size_basis: 'range_midpoint', trade_size_percentile: 95, trade_size_sample_size: 20, disclosure_delay_signal: false,
  disclosure_delay_days: 10, excess_return_signal: true, security_return: 0.3, spy_return: 0.01, excess_return: 0.29, excess_return_direction_adjusted: 0.29, excess_horizon_days: 90,
  signals: {}, signal_count: 2, secondary_signal_count: 2, committee_temporal_status: null, meets_flag_rule: false, flag_pending_temporal_verification: false,
  flagged_for_contextual_review: flagged, evidence: [], notice: 'n',
});

const trade = (screenOver: Partial<CustomScreen> | null, flagged = false): Trade =>
  ({ id: 1, politician_name: 'A B', ticker: 'BA', transaction_type: 'buy', transaction_date: '2026-01-01', context: context(flagged), custom_screen: screenOver === null ? null : cs(screenOver) }) as unknown as Trade;

describe('custom screen vs the canonical flag', () => {
  it('shows both results side by side and never calls the screen a flag', () => {
    render(<CustomScreenSection cs={cs()} />);
    const box = screen.getByTestId('custom-screen');
    expect(box).toHaveTextContent('Default POLTRACKER flag: not flagged');
    expect(box).toHaveTextContent('Current custom screen: match');
    expect(box).toHaveTextContent('does not indicate political context');
    expect(box).toHaveTextContent(/it is not the contextual-review flag/i);
    expect(box).toHaveTextContent('trade size, excess return');
  });

  it('shows the reverse case: flagged by default, no match under the user’s settings', () => {
    render(<CustomScreenSection cs={cs({ matches: false, canonical_flag: true, kind: 'custom', kind_label: 'Custom screen', active_signals: ['committee_relevance'], active_signal_count: 1 })} />);
    expect(screen.getByTestId('custom-screen')).toHaveTextContent('Default POLTRACKER flag: flagged for contextual review');
    expect(screen.getByTestId('custom-screen')).toHaveTextContent('Current custom screen: no match');
  });

  it('appears in the trade dialog only for a non-default rule, apart from the deterministic signals', () => {
    const { unmount } = render(wrap(<TradeContextDialog trade={trade({})} onClose={() => undefined} />));
    expect(screen.getByTestId('custom-screen')).toBeInTheDocument();
    expect(screen.getByText('Not flagged (2 of 3 secondary signals; two are needed with committee relevance)')).toBeInTheDocument(); // the canonical status line is still there
    unmount();
    render(wrap(<TradeContextDialog trade={trade({ kind: 'default', differs_from_canonical: false })} onClose={() => undefined} />));
    expect(screen.queryByTestId('custom-screen')).not.toBeInTheDocument();
  });

  it('is absent when the trade carries no custom screen (other pages)', () => {
    render(wrap(<TradeContextDialog trade={trade(null)} onClose={() => undefined} />));
    expect(screen.queryByTestId('custom-screen')).not.toBeInTheDocument();
  });
});
