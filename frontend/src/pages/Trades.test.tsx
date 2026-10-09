import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ContextRule, FilterSpec, ScreenPage } from '../api/types';
import { DEFAULT_RULE } from '../lib/filters';
import { PRESETS, fakeApi, wrap } from '../test/helpers';

// The data grid needs real layout; the page's job is what it hands the grid, so the grid is replaced by a probe that records its props.
const grid = vi.hoisted(() => ({ last: null as null | { rule: ContextRule; filters: FilterSpec[] }, page: null as null | ScreenPage }));
vi.mock('../components/TradesGrid', async () => {
  const React = await import('react');
  return {
    default: ({ screen }: { screen: { rule: ContextRule; filters: FilterSpec[]; onPage?: (p: ScreenPage | undefined) => void } }) => {
      grid.last = { rule: screen.rule, filters: screen.filters };
      React.useEffect(() => screen.onPage?.(grid.page ?? undefined), [screen]);
      return <div data-testid="grid">{JSON.stringify(screen.rule)}</div>;
    },
  };
});

import Trades from './Trades';

const page = (over: Partial<ScreenPage> = {}): ScreenPage => ({
  items: [], total: 40, limit: 25, offset: 0, rule: DEFAULT_RULE, kind: 'default', kind_label: 'Default methodology', is_default_rule: true,
  custom_match_count: 3, canonical_flag_count: 3, notice: '', ...over,
});

let api: ReturnType<typeof fakeApi>;
function start(opts: Parameters<typeof fakeApi>[0] = {}, route = '/trades') {
  api = fakeApi(opts);
  vi.stubGlobal('fetch', vi.fn(api.handler));
  return render(wrap(<Trades />, route));
}

beforeEach(() => {
  grid.last = null;
  grid.page = page();
});

async function ready() {
  await screen.findByTestId('grid');
}

describe('Trades page personalization', () => {
  it('starts on the default methodology and says so', async () => {
    start();
    await ready();
    expect(grid.last!.rule).toEqual(DEFAULT_RULE);
    expect(await screen.findByTestId('screen-summary')).toHaveTextContent('3 flagged for contextual review (default methodology)');
    expect(screen.getByRole('combobox', { name: /context rule/i })).toHaveTextContent('Balanced');
  });

  it('selects a built-in preset and sends its rule to the grid', async () => {
    const user = userEvent.setup();
    start();
    await ready();
    grid.page = page({ rule: PRESETS[1].rule, kind: 'custom', kind_label: 'Custom screen', is_default_rule: false, custom_match_count: 1, canonical_flag_count: 3 });
    await user.click(screen.getByRole('combobox', { name: /context rule/i }));
    await user.click(await screen.findByRole('option', { name: 'Strict' }));
    await waitFor(() => expect(grid.last!.rule.minimum_secondary_signals).toBe(3));
    expect(grid.last!.rule.trade_size_percentile_threshold).toBe(95);
    expect(screen.getByRole('combobox', { name: /context rule/i })).toHaveTextContent('Strict');
  });

  it('shows a custom screen separately from the canonical flag, and market-only is not political context', async () => {
    const user = userEvent.setup();
    start();
    await ready();
    grid.page = page({ rule: PRESETS[3].rule, kind: 'market_only', kind_label: 'Market-signal screen (does not indicate political context)', is_default_rule: false, custom_match_count: 17, canonical_flag_count: 2 });
    await user.click(screen.getByRole('combobox', { name: /context rule/i }));
    await user.click(await screen.findByRole('option', { name: 'Market focus' }));
    const summary = await screen.findByText(/17 match this screen/);
    expect(summary).toBeInTheDocument();
    expect(screen.getByTestId('canonical-count')).toHaveTextContent('2 flagged by the default methodology');
    expect(screen.getByTestId('screen-summary')).toHaveTextContent(/not the contextual-review flag/i);
    expect(screen.getByTestId('screen-summary')).toHaveTextContent(/says nothing about political context/i);
    expect(screen.getByTestId('screen-summary')).not.toHaveTextContent(/flagged for contextual review \(default/i);
  });

  it('adds filters as chips and clears them', async () => {
    const user = userEvent.setup();
    start();
    await ready();
    await user.click(screen.getByRole('button', { name: /add filter/i }));
    await user.click(await screen.findByRole('menuitem', { name: 'Committee relevance' }));
    await user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: /apply/i }));
    expect(await screen.findByText('Committee relevance: Yes')).toBeInTheDocument();
    await waitFor(() => expect(grid.last!.filters).toEqual([{ field: 'committee_relevance', op: 'is', value: 'yes' }]));
    await user.click(await screen.findByRole('button', { name: /clear all/i }));
    await waitFor(() => expect(grid.last!.filters).toEqual([]));
  });

  it('turns an older link into filter chips', async () => {
    start({}, '/trades?ticker=ba&politician_id=7&flagged=1');
    await ready();
    expect(grid.last!.filters).toEqual([
      { field: 'ticker', op: 'is', value: 'BA' }, { field: 'politician', op: 'is', value: 7 }, { field: 'review_status', op: 'is', value: 'flagged' },
    ]);
    expect(screen.getByText('Ticker: is BA')).toBeInTheDocument();
  });

  it('edits the rule in settings and becomes a custom rule', async () => {
    const user = userEvent.setup();
    start();
    await ready();
    await user.click(screen.getByRole('button', { name: /rule settings/i }));
    const dialog = await screen.findByRole('dialog', { name: /context rule settings/i });
    const pct = within(dialog).getByLabelText('Percentile ≥');
    await user.clear(pct);
    await user.type(pct, '80');
    await user.click(within(dialog).getByRole('button', { name: /apply/i }));
    await waitFor(() => expect(grid.last!.rule.trade_size_percentile_threshold).toBe(80));
    expect(await screen.findByRole('combobox', { name: /context rule/i })).toHaveTextContent('Custom');
  });

  it('refuses an impossible rule in settings', async () => {
    const user = userEvent.setup();
    start();
    await ready();
    await user.click(screen.getByRole('button', { name: /rule settings/i }));
    const dialog = await screen.findByRole('dialog', { name: /context rule settings/i });
    await user.click(within(dialog).getByRole('switch', { name: /excess return/i }));
    await user.click(within(dialog).getByRole('switch', { name: /trade size/i }));
    expect(await within(dialog).findByText(/needs 2 secondary signals but only 1 is enabled/i)).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: /apply/i })).toBeDisabled();
  });

  it('saves a named view, loads it back after a reset, renames and deletes it', async () => {
    const user = userEvent.setup();
    start();
    await ready();
    await user.click(screen.getByRole('combobox', { name: /context rule/i }));
    await user.click(await screen.findByRole('option', { name: 'Committee focus' }));
    await user.click(screen.getByRole('button', { name: /add filter/i }));
    await user.click(await screen.findByRole('menuitem', { name: 'Ticker' }));
    const editor = await screen.findByRole('dialog');
    await user.type(within(editor).getByLabelText('Value'), 'BA');
    await user.click(within(editor).getByRole('button', { name: /apply/i }));

    await user.click(await screen.findByRole('button', { name: 'Views' }));
    await user.click(await screen.findByRole('menuitem', { name: /save current as new view/i }));
    await user.type(await screen.findByLabelText('Name'), 'Defense trades');
    await user.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(api.state.views.map((v) => v.name)).toEqual(['Defense trades']));
    expect(api.state.views[0].rule.minimum_secondary_signals).toBe(0);
    expect(api.state.views[0].filters).toEqual([{ field: 'ticker', op: 'is', value: 'BA' }]);
    expect(await screen.findByRole('button', { name: /view: defense trades/i })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Reset' })); // back to the default methodology
    await waitFor(() => expect(grid.last!.rule).toEqual(DEFAULT_RULE));
    expect(grid.last!.filters).toEqual([]);
    expect(api.state.active).toBeNull();

    await user.click(screen.getByRole('button', { name: 'Views' })); // load it
    await user.click(await screen.findByRole('menuitem', { name: /defense trades/i }));
    await waitFor(() => expect(grid.last!.rule.minimum_secondary_signals).toBe(0));
    expect(grid.last!.filters).toEqual([{ field: 'ticker', op: 'is', value: 'BA' }]);

    await user.click(screen.getByRole('button', { name: /view: defense trades/i })); // rename
    await user.click(await screen.findByRole('button', { name: /rename defense trades/i }));
    const name = await screen.findByLabelText('Name');
    await user.clear(name);
    await user.type(name, 'Large committee-related buys');
    await user.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(api.state.views[0].name).toBe('Large committee-related buys'));

    await user.click(await screen.findByRole('button', { name: /view: large committee-related buys/i })); // delete
    await user.click(await screen.findByRole('button', { name: /delete large committee-related buys/i }));
    await waitFor(() => expect(api.state.views).toEqual([]));
  });

  it('reports a duplicate view name instead of silently overwriting', async () => {
    const user = userEvent.setup();
    start({ views: [{ id: 1, name: 'Mine', preset: 'balanced', rule: DEFAULT_RULE, filters: [], created_at: 'x', updated_at: 'x' }] });
    await ready();
    await user.click(await screen.findByRole('button', { name: 'Views' }));
    await user.click(await screen.findByRole('menuitem', { name: /save current as new view/i }));
    await user.type(await screen.findByLabelText('Name'), 'mine');
    await user.click(screen.getByRole('button', { name: 'Save' }));
    expect(await screen.findByText(/already exists/i)).toBeInTheDocument();
    expect(api.state.views).toHaveLength(1);
  });

  it('remembers the last-used screen, and restores it on the next start', async () => {
    const user = userEvent.setup();
    const first = start();
    await ready();
    await user.click(screen.getByRole('combobox', { name: /context rule/i }));
    await user.click(await screen.findByRole('option', { name: 'Strict' }));
    await waitFor(() => expect(api.state.active?.preset).toBe('strict'), { timeout: 3000 });
    const saved = api.state.active!;
    first.unmount();
    // a new app start with the same stored state
    api = fakeApi();
    api.state.active = saved;
    vi.stubGlobal('fetch', vi.fn(api.handler));
    render(wrap(<Trades />));
    await ready();
    await waitFor(() => expect(grid.last!.rule.minimum_secondary_signals).toBe(3));
    expect(screen.getByRole('combobox', { name: /context rule/i })).toHaveTextContent('Strict');
  });

  it('works without local storage (a read-only API): presets and filters still work, views are unavailable', async () => {
    const user = userEvent.setup();
    start({ persistent: false });
    await ready();
    expect(await screen.findByRole('button', { name: 'Views' })).toBeDisabled();
    await user.click(screen.getByRole('combobox', { name: /context rule/i }));
    await user.click(await screen.findByRole('option', { name: 'Strict' }));
    await waitFor(() => expect(grid.last!.rule.minimum_secondary_signals).toBe(3));
    expect(api.state.calls.some((c) => c.startsWith('PUT') || c.startsWith('POST'))).toBe(false);
  });
});
