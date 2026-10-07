import * as React from 'react';
import { BarChart } from '@mui/x-charts/BarChart';
import Stack from '@mui/material/Stack';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import { useTheme } from '@mui/material/styles';
import { useSecurityActivity } from '../api/hooks';
import type { ActivityBasis, ActivityPeriod, SecurityActivity } from '../api/types';
import ChartCard from './ChartCard';
import QueryError from './QueryError';

const PERIODS: { value: ActivityPeriod; label: string; long: string }[] = [
  { value: '7d', label: '7D', long: 'the past 7 days' },
  { value: '1m', label: '1M', long: 'the past month' },
  { value: '3m', label: '3M', long: 'the past 3 months' },
  { value: '6m', label: '6M', long: 'the past 6 months' },
];

const LEAN = {
  more_bought: { label: 'more buys than sells', color: 'success' },
  more_sold: { label: 'more sells than buys', color: 'error' },
  balanced: { label: 'balanced', color: 'default' },
  no_activity: { label: 'no buys or sells', color: 'default' },
} as const;

const usd = (n: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 1 }).format(n);
const day = (iso: string, opts: Intl.DateTimeFormatOptions) => new Date(`${iso}T00:00:00`).toLocaleDateString('en-US', opts);

export function bucketLabel(b: { start: string }, kind: SecurityActivity['bucket']) {
  return kind === 'month' ? day(b.start, { month: 'short' }) : day(b.start, { month: 'short', day: 'numeric' });
}

const range = (min: number, max: number) => (max === 0 && min === 0 ? 'amount not reported' : `${usd(min)}–${usd(max)}`);

/** Disclosed buys vs sells for one ticker over a selectable recent period (counts of trades, not dollars). */
export default function TickerActivityChart({ ticker }: { ticker: string }) {
  const theme = useTheme();
  const palette = (theme.vars ?? theme).palette;
  const [period, setPeriod] = React.useState<ActivityPeriod>('3m');
  const [basis, setBasis] = React.useState<ActivityBasis>('disclosure');
  const { data, isLoading, error, isPlaceholderData } = useSecurityActivity(ticker, period, basis);

  const t = data?.totals;
  const lean = data ? LEAN[data.lean] : undefined;
  const what = basis === 'disclosure' ? 'disclosed' : 'made';
  const periodText = PERIODS.find((p) => p.value === period)?.long ?? '';

  const action = (
    <Stack direction="row" sx={{ gap: 1, alignItems: 'center', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
      <Tooltip title="Count trades by the date they were disclosed (what is newly known) or by the date they were made. Filings arrive weeks late, so recent periods look thin by trade date.">
        <ToggleButtonGroup size="small" exclusive value={basis} aria-label="Date basis" onChange={(_e, v: ActivityBasis | null) => v && setBasis(v)}>
          <ToggleButton value="disclosure">Disclosed</ToggleButton>
          <ToggleButton value="transaction">Traded</ToggleButton>
        </ToggleButtonGroup>
      </Tooltip>
      <ToggleButtonGroup size="small" exclusive value={period} aria-label="Period" onChange={(_e, v: ActivityPeriod | null) => v && setPeriod(v)}>
        {PERIODS.map((p) => (
          <ToggleButton key={p.value} value={p.value}>
            {p.label}
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
    </Stack>
  );

  return (
    <ChartCard
      title="Buys vs sells"
      headline={t ? `${t.buys} ${t.buys === 1 ? 'buy' : 'buys'} · ${t.sells} ${t.sells === 1 ? 'sell' : 'sells'}` : undefined}
      chip={lean ? { label: lean.label, color: lean.color } : undefined}
      caption={data ? `Trades ${what} in ${periodText} (${day(data.start, { month: 'short', day: 'numeric' })} – ${day(data.end, { month: 'short', day: 'numeric', year: 'numeric' })}). Counts of trades, not dollars.` : undefined}
      action={action}
      loading={isLoading}
    >
      {error ? (
        <QueryError error={error} what="trade activity" />
      ) : data && data.lean === 'no_activity' ? (
        <Typography variant="body2" sx={{ color: 'text.secondary', py: 6, textAlign: 'center' }}>
          No buys or sells {what} for {ticker} in {periodText}.
          {t && t.other > 0 ? ` (${t.other} exchange or other trade${t.other === 1 ? '' : 's'} not counted.)` : ''}
        </Typography>
      ) : data ? (
        <>
          <BarChart
            sx={{ opacity: isPlaceholderData ? 0.5 : 1 }}
            borderRadius={4}
            colors={[palette.success.main, palette.error.main]}
            xAxis={[{ scaleType: 'band', categoryGapRatio: 0.35, data: data.buckets.map((b) => bucketLabel(b, data.bucket)), height: 24 }]}
            yAxis={[{ width: 36, valueFormatter: (v: number) => String(Math.abs(v)) }]}
            // Sells are plotted below zero so the chart shows net direction at a glance; labels show absolute counts.
            series={[
              { id: 'buys', label: 'Buys', data: data.buckets.map((b) => b.buys), stack: 'A', valueFormatter: (v: number | null) => String(v ?? 0) },
              { id: 'sells', label: 'Sells', data: data.buckets.map((b) => -b.sells), stack: 'A', valueFormatter: (v: number | null) => String(Math.abs(v ?? 0)) },
            ]}
            height={250}
            margin={{ left: 0, right: 0, top: 20, bottom: 0 }}
            grid={{ horizontal: true }}
            hideLegend
          />
          {t && (
            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mt: 1 }}>
              Reported amount ranges (sums of the filed ranges, not exact values): buys {range(t.buy_amount_min, t.buy_amount_max)} · sells{' '}
              {range(t.sell_amount_min, t.sell_amount_max)}.
              {t.other > 0 && ` ${t.other} exchange or other trade${t.other === 1 ? ' is' : 's are'} not counted.`}
              {data.undated > 0 && ` ${data.undated} trade${data.undated === 1 ? ' has' : 's have'} no ${basis} date and ${data.undated === 1 ? 'is' : 'are'} not included.`}
            </Typography>
          )}
        </>
      ) : null}
    </ChartCard>
  );
}
