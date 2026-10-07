import * as React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Link from '@mui/material/Link';
import Skeleton from '@mui/material/Skeleton';
import Stack from '@mui/material/Stack';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import { usePoliticianAnalytics } from '../api/hooks';
import type { ActivityBasis, AnalyticsPeriod, ReturnStat, TradeRef } from '../api/types';
import QueryError from './QueryError';
import { formatPct } from '../lib/format';

const PERIODS: { value: AnalyticsPeriod; label: string; long: string }[] = [
  { value: '7d', label: '7D', long: 'the past 7 days' },
  { value: '1m', label: '1M', long: 'the past month' },
  { value: '3m', label: '3M', long: 'the past 3 months' },
  { value: '6m', label: '6M', long: 'the past 6 months' },
  { value: '1y', label: '1Y', long: 'the past year' },
  { value: 'all', label: 'All', long: 'all available history' },
];

const REASON: Record<string, string> = {
  no_prices: 'no price data',
  no_price_at_date: 'no price near the trade date',
  invalid_date: 'an invalid date',
  no_ticker: 'no ticker',
};

function Pct({ value, bold }: { value: number | null | undefined; bold?: boolean }) {
  if (value == null) return <>—</>;
  return (
    <Typography
      component="span"
      variant="body2"
      sx={{ color: value > 0 ? 'success.main' : value < 0 ? 'error.main' : 'text.primary', fontVariantNumeric: 'tabular-nums', fontWeight: bold ? 600 : undefined }}
    >
      {formatPct(value)}
    </Typography>
  );
}

function TradeCell({ t }: { t: TradeRef | null }) {
  if (!t) return <>—</>;
  return (
    <>
      {t.ticker ? (
        <Link component={RouterLink} to={`/securities/${t.ticker}`} underline="hover">
          {t.ticker}
        </Link>
      ) : (
        'trade'
      )}{' '}
      <Pct value={t.excess_return} />
    </>
  );
}

function Row({ label, hint, a, b }: { label: string; hint?: string; a: React.ReactNode; b: React.ReactNode }) {
  return (
    <TableRow>
      <TableCell sx={{ color: 'text.secondary' }}>
        {hint ? (
          <Tooltip title={hint}>
            <span>{label}</span>
          </Tooltip>
        ) : (
          label
        )}
      </TableCell>
      <TableCell align="right">{a}</TableCell>
      <TableCell align="right">{b}</TableCell>
    </TableRow>
  );
}

const winText = (s: ReturnStat) => (s.n_benchmarked ? `${s.outperformed} of ${s.n_benchmarked} (${Math.round((s.outperformed / s.n_benchmarked) * 100)}%)` : '—');

/** Equal-weighted aggregate return across a politician's trades in a selectable period. */
export default function PoliticianReturns({ id }: { id: number }) {
  const [period, setPeriod] = React.useState<AnalyticsPeriod>('1y');
  const [basis, setBasis] = React.useState<ActivityBasis>('transaction');
  const [adjusted, setAdjusted] = React.useState(false);
  const { data, isLoading, error, isPlaceholderData } = usePoliticianAnalytics(id, period, basis);

  const periodText = PERIODS.find((p) => p.value === period)?.long ?? '';
  const what = basis === 'transaction' ? 'made' : 'disclosed';
  const tx = data && (adjusted ? data.transaction.adjusted : data.transaction.raw);
  const di = data && (adjusted ? data.disclosure.adjusted : data.disclosure.raw);
  const bench = data?.benchmark ?? 'SPY';
  const unpriced = data ? Object.entries(data.unpriced) : [];

  return (
    <Card variant="outlined" sx={{ width: '100%', mb: 2 }} aria-label="Returns in period">
      <CardContent>
        <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 1, mb: 1 }}>
          <Box>
            <Typography component="h2" variant="subtitle2">
              Returns across trades in the period
            </Typography>
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              Equal-weighted price returns of trades {what} in {periodText}, to the latest close, versus {bench}.
            </Typography>
          </Box>
          <Stack direction="row" sx={{ gap: 1, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            <Tooltip title="Select trades by the date they were made or the date they were disclosed. Filings arrive weeks late, so very recent periods are thin by trade date.">
              <ToggleButtonGroup size="small" exclusive value={basis} aria-label="Date basis" onChange={(_e, v: ActivityBasis | null) => v && setBasis(v)}>
                <ToggleButton value="transaction">Traded</ToggleButton>
                <ToggleButton value="disclosure">Disclosed</ToggleButton>
              </ToggleButtonGroup>
            </Tooltip>
            <ToggleButtonGroup size="small" exclusive value={period} aria-label="Period" onChange={(_e, v: AnalyticsPeriod | null) => v && setPeriod(v)}>
              {PERIODS.map((p) => (
                <ToggleButton key={p.value} value={p.value}>
                  {p.label}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
            <Tooltip title="Direction-adjusted flips the sign of sells (a sale that was followed by a fall counts as positive). Raw is the actual price change of the security.">
              <ToggleButtonGroup size="small" exclusive value={adjusted ? 'adj' : 'raw'} aria-label="Return type" onChange={(_e, v: string | null) => v && setAdjusted(v === 'adj')}>
                <ToggleButton value="raw">Raw</ToggleButton>
                <ToggleButton value="adj">Direction-adjusted</ToggleButton>
              </ToggleButtonGroup>
            </Tooltip>
          </Stack>
        </Stack>

        {error ? (
          <QueryError error={error} what="return analytics" />
        ) : isLoading ? (
          <Skeleton variant="rounded" height={220} />
        ) : data && data.trades_in_period === 0 ? (
          <Typography variant="body2" sx={{ color: 'text.secondary', py: 4, textAlign: 'center' }}>
            No trades {what} in {periodText}.{' '}
            {period === '7d' || period === '1m' ? 'Filings arrive weeks after the trade, so try a longer period or “Disclosed”.' : ''}
          </Typography>
        ) : data && tx && di ? (
          <Box sx={{ opacity: isPlaceholderData ? 0.5 : 1 }}>
            <Typography variant="body2" sx={{ mb: 1 }}>
              {data.trades_in_period} trade{data.trades_in_period === 1 ? '' : 's'} ({data.by_type.buys} buy{data.by_type.buys === 1 ? '' : 's'}, {data.by_type.sells} sell
              {data.by_type.sells === 1 ? '' : 's'}
              {data.by_type.other ? `, ${data.by_type.other} other` : ''}); {data.priced} fully priced.
            </Typography>
            <Table size="small" aria-label="Aggregate returns">
              <TableHead>
                <TableRow>
                  <TableCell />
                  <TableCell align="right">Since trade date</TableCell>
                  <TableCell align="right">
                    <Tooltip title="From the disclosure date: what a follower could actually have captured">
                      <span>Since disclosure</span>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                <Row label="Trades with a return" a={tx.n} b={di.n} />
                <Row label="Average return" a={<Pct value={tx.mean_return} bold />} b={<Pct value={di.mean_return} bold />} />
                <Row label="Median return" a={<Pct value={tx.median_return} />} b={<Pct value={di.median_return} />} />
                <Row
                  label={`Average ${bench} return`}
                  hint={adjusted ? 'The benchmark has no direction, so it is shown only in the raw view' : `${bench} over the same holding period for each trade`}
                  a={<Pct value={tx.mean_benchmark_return} />}
                  b={<Pct value={di.mean_benchmark_return} />}
                />
                <Row label="Average excess return" hint={`Return minus ${bench} return`} a={<Pct value={tx.mean_excess_return} bold />} b={<Pct value={di.mean_excess_return} bold />} />
                <Row label="Median excess return" a={<Pct value={tx.median_excess_return} />} b={<Pct value={di.median_excess_return} />} />
                <Row label={`Ahead of ${bench}`} hint="Trades with a positive excess return" a={winText(tx)} b={winText(di)} />
                <Row label="Best trade (excess)" a={<TradeCell t={tx.best} />} b={<TradeCell t={di.best} />} />
                <Row label="Worst trade (excess)" a={<TradeCell t={tx.worst} />} b={<TradeCell t={di.worst} />} />
              </TableBody>
            </Table>
            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mt: 1 }}>
              Each trade counts once regardless of size (disclosures report amount ranges only).
              {unpriced.length > 0 &&
                ` Not priced: ${unpriced.map(([k, n]) => `${n} with ${REASON[k] ?? k.replace(/_/g, ' ')}`).join(', ')}.`}
              {data.undated > 0 && basis === 'disclosure' && ` ${data.undated} trade${data.undated === 1 ? ' has' : 's have'} no disclosure date and ${data.undated === 1 ? 'is' : 'are'} not included.`}
              {' '}Returns describe price movement only and say nothing about intent.
            </Typography>
          </Box>
        ) : null}
      </CardContent>
    </Card>
  );
}
