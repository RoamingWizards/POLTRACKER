import { useState } from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { FilterSpec } from '../api/types';
import { wrap } from '../test/helpers';
import FilterBar from './FilterBar';

function Harness({ initial = [], spy }: { initial?: FilterSpec[]; spy?: (f: FilterSpec[]) => void }) {
  const [filters, setFilters] = useState<FilterSpec[]>(initial);
  return <FilterBar filters={filters} onChange={(f) => { setFilters(f); spy?.(f); }} />;
}

describe('FilterBar', () => {
  it('only looks up a politician for a politician-by-id chip', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => new Response(JSON.stringify(String(input).includes('/politicians/7') ? { id: 7, name: 'Ann Lee' } : {}), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    render(wrap(<Harness initial={[{ field: 'chamber', op: 'is', value: 'house' }, { field: 'ticker', op: 'is', value: 'BA' }, { field: 'politician', op: 'is', value: 7 }]} />));
    expect(await screen.findByText('Politician: Ann Lee')).toBeInTheDocument();
    const urls = fetchMock.mock.calls.map((c) => String(c[0]));
    expect(urls).toEqual(['/api/politicians/7']); // no /politicians/0 for the other chips
  });

  it('adds a filter from the Add filter menu and shows it as a chip', async () => {
    const user = userEvent.setup();
    const spy = vi.fn();
    render(wrap(<Harness spy={spy} />));
    await user.click(screen.getByRole('button', { name: /add filter/i }));
    await user.click(await screen.findByRole('menuitem', { name: 'Excess return' }));
    const dialog = await screen.findByRole('dialog', { name: /add filter/i });
    const value = within(dialog).getByLabelText(/value \(pp\)/i);
    await user.clear(value);
    await user.type(value, '20');
    await user.click(within(dialog).getByRole('button', { name: /apply/i }));
    expect(await screen.findByText('Excess return: |value| ≥ 20 pp')).toBeInTheDocument();
    expect(spy).toHaveBeenLastCalledWith([{ field: 'excess_return', op: 'abs_gte', value: 20 }]);
  });

  it('does not apply an incomplete filter', async () => {
    const user = userEvent.setup();
    render(wrap(<Harness />));
    await user.click(screen.getByRole('button', { name: /add filter/i }));
    await user.click(await screen.findByRole('menuitem', { name: 'Ticker' }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByRole('button', { name: /apply/i })).toBeDisabled();
  });

  it('edits a filter by clicking its chip', async () => {
    const user = userEvent.setup();
    render(wrap(<Harness initial={[{ field: 'trade_size_percentile', op: 'gte', value: 90 }]} />));
    await user.click(screen.getByText('Trade size percentile: ≥ 90 percentile'));
    const dialog = await screen.findByRole('dialog', { name: /edit filter/i });
    const value = within(dialog).getByLabelText(/value \(percentile\)/i);
    await user.clear(value);
    await user.type(value, '95');
    await user.click(within(dialog).getByRole('button', { name: /apply/i }));
    expect(await screen.findByText('Trade size percentile: ≥ 95 percentile')).toBeInTheDocument();
    expect(screen.queryByText('Trade size percentile: ≥ 90 percentile')).not.toBeInTheDocument();
  });

  it('removes one filter and clears all', async () => {
    const user = userEvent.setup();
    const spy = vi.fn();
    render(wrap(<Harness spy={spy} initial={[{ field: 'chamber', op: 'is', value: 'house' }, { field: 'committee_relevance', op: 'is', value: 'yes' }]} />));
    expect(screen.getByText(/all of these must match/i)).toBeInTheDocument(); // AND semantics are stated
    const chip = screen.getByRole('button', { name: /filter chamber/i });
    await user.click(within(chip).getByTestId('CancelIcon'));
    expect(spy).toHaveBeenLastCalledWith([{ field: 'committee_relevance', op: 'is', value: 'yes' }]);
    await user.click(screen.getByRole('button', { name: /clear all/i }));
    expect(spy).toHaveBeenLastCalledWith([]);
    expect(screen.queryByText(/committee relevance: yes/i)).not.toBeInTheDocument();
  });
});
