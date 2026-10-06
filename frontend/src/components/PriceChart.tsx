import { LineChart } from '@mui/x-charts/LineChart';
import { useTheme } from '@mui/material/styles';
import type { PriceBar, TradePerformance } from '../api/types';
import { isSell } from '../lib/format';

interface Props {
  ticker: string;
  bars: PriceBar[];
  benchmarkBars?: PriceBar[];
  benchmarkTicker: string;
  trades: TradePerformance[];
  /** Rebase both lines to 100 at the start of the visible window. */
  compare: boolean;
  /** Only show bars on or after this ISO date. */
  from?: string;
}

const localIso = (d: Date) => d.toLocaleDateString('en-CA');

/** Adjusted-close line with buy/sell markers on each trade's anchor day (template: SessionsChart). */
export default function PriceChart({ ticker, bars, benchmarkBars, benchmarkTicker, trades, compare, from }: Props) {
  const theme = useTheme();
  const palette = (theme.vars ?? theme).palette;

  const visible = bars.filter((b) => b.adj_close != null && (!from || b.date >= from));
  const dates = visible.map((b) => b.date);
  const base = visible[0]?.adj_close ?? 1;
  const scale = (v: number, b: number) => (compare ? (v / b) * 100 : v);

  const price = visible.map((b) => scale(b.adj_close as number, base));

  const spyByDate = new Map((benchmarkBars ?? []).map((b) => [b.date, b.adj_close]));
  const spyStart = spyByDate.get(dates[0]) ?? (benchmarkBars ?? []).find((b) => b.date >= (dates[0] ?? ''))?.adj_close ?? null;
  const spy = dates.map((d) => {
    const v = spyByDate.get(d);
    return v != null && spyStart ? scale(v, spyStart) : null;
  });

  const indexByDate = new Map(dates.map((d, i) => [d, i]));
  const buys: (number | null)[] = dates.map(() => null);
  const sells: (number | null)[] = dates.map(() => null);
  for (const { trade, performance } of trades) {
    const anchor = performance.transaction?.anchor_date;
    const i = anchor ? indexByDate.get(anchor) : undefined;
    if (i === undefined) continue;
    if (trade.transaction_type === 'buy') buys[i] = price[i];
    else if (isSell(trade.transaction_type)) sells[i] = price[i];
  }

  const series = [
    { id: 'price', label: ticker, data: price, showMark: false, curve: 'linear' as const, color: palette.primary.main },
    ...(compare
      ? [{ id: 'spy', label: `${benchmarkTicker} (rebased)`, data: spy, showMark: false, curve: 'linear' as const, color: palette.text.secondary }]
      : []),
    { id: 'buys', label: 'Buys', data: buys, showMark: true, curve: 'linear' as const, color: palette.success.main },
    { id: 'sells', label: 'Sells', data: sells, showMark: true, curve: 'linear' as const, color: palette.error.main },
  ];

  return (
    <LineChart
      xAxis={[
        {
          scaleType: 'time',
          data: dates.map((d) => new Date(`${d}T00:00:00`)),
          valueFormatter: (v: Date) => localIso(v),
          height: 28,
        },
      ]}
      yAxis={[{ width: 56 }]}
      series={series}
      height={320}
      margin={{ left: 0, right: 20, top: 20, bottom: 0 }}
      grid={{ horizontal: true }}
      sx={{
        '& .MuiLineElement-series-buys, & .MuiLineElement-series-sells': { strokeWidth: 0 },
      }}
    />
  );
}
