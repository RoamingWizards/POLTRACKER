import * as React from 'react';
import { useParams } from 'react-router-dom';
import { Link as RouterLink } from 'react-router-dom';
import type { GridColDef } from '@mui/x-data-grid';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import FormControlLabel from '@mui/material/FormControlLabel';
import Grid from '@mui/material/Grid';
import Link from '@mui/material/Link';
import Stack from '@mui/material/Stack';
import Switch from '@mui/material/Switch';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import { ApiError } from '../api/client';
import { useSecurity, useSecurityPerformance, useSecurityPrices } from '../api/hooks';
import type { TradePerformance } from '../api/types';
import AppDataGrid from '../components/AppDataGrid';
import ChartCard from '../components/ChartCard';
import { TypeChip } from '../components/Chips';
import PriceChart from '../components/PriceChart';
import QueryError from '../components/QueryError';
import StatCard from '../components/StatCard';
import { formatInt, formatPct, formatUsd } from '../lib/format';

type Range = '3M' | '6M' | '1Y' | 'ALL';
const RANGE_MONTHS: Record<Exclude<Range, 'ALL'>, number> = { '3M': 3, '6M': 6, '1Y': 12 };

function Pct({ value }: { value: number | null | undefined }) {
  if (value == null) return <>—</>;
  return (
    <Typography
      component="span"
      variant="body2"
      sx={{ color: value > 0 ? 'success.main' : value < 0 ? 'error.main' : 'text.primary', fontVariantNumeric: 'tabular-nums' }}
    >
      {formatPct(value)}
    </Typography>
  );
}

const mean = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);

export default function SecurityDetail() {
  const ticker = (useParams().ticker ?? '').toUpperCase();
  const [range, setRange] = React.useState<Range>('1Y');
  const [compare, setCompare] = React.useState(true);
  const [adjusted, setAdjusted] = React.useState(false);

  const security = useSecurity(ticker);
  const performance = useSecurityPerformance(ticker);
  const benchmark = performance.data?.benchmark ?? 'SPY';
  const prices = useSecurityPrices(ticker);
  const spy = useSecurityPrices(benchmark, compare);

  if (security.error instanceof ApiError && security.error.status === 404) {
    return <Alert severity="warning">No trades have been recorded for “{ticker}”.</Alert>;
  }
  if (security.error) return <QueryError error={security.error} what="this security" />;

  const sec = security.data;
  const bars = prices.data?.bars ?? [];
  const last = bars[bars.length - 1];
  const from =
    range === 'ALL' || !last
      ? undefined
      : (() => {
          const d = new Date(`${last.date}T00:00:00`);
          d.setMonth(d.getMonth() - RANGE_MONTHS[range]);
          return d.toLocaleDateString('en-CA');
        })();

  const items = performance.data?.items ?? [];
  const priced = items.filter((i) => i.performance.status === 'ok');
  const avgReturn = mean(priced.map((i) => i.performance.transaction?.return).filter((v): v is number => v != null));
  const avgExcess = mean(priced.map((i) => i.performance.transaction?.excess_return).filter((v): v is number => v != null));

  const noPrices = sec && (sec.price_status === 'unavailable' || sec.price_status === null);
  const buys = items.filter((i) => i.trade.transaction_type === 'buy').length;

  const da = (row: TradePerformance, key: string) => row.performance.direction_adjusted[key] ?? null;
  const columns: GridColDef<TradePerformance>[] = [
    { field: 'traded', headerName: 'Traded', width: 110, valueGetter: (_v, row) => row.trade.transaction_date },
    {
      field: 'politician',
      headerName: 'Politician',
      flex: 1,
      minWidth: 160,
      valueGetter: (_v, row) => row.trade.politician_name,
      renderCell: ({ row }) => (
        <Link component={RouterLink} to={`/politicians/${row.trade.politician_id}`} underline="hover">
          {row.trade.politician_name}
        </Link>
      ),
    },
    { field: 'type', headerName: 'Type', width: 120, valueGetter: (_v, row) => row.trade.transaction_type, renderCell: ({ row }) => <TypeChip type={row.trade.transaction_type} /> },
    {
      field: 'entry',
      headerName: 'Entry (adj.)',
      description: 'Adjusted close on the trade date (first trading day on or after it)',
      width: 105,
      align: 'right',
      headerAlign: 'right',
      valueGetter: (_v, row) => row.performance.transaction?.price ?? null,
      renderCell: ({ row }) => formatUsd(row.performance.transaction?.price),
    },
    {
      field: 'ret_tx',
      headerName: adjusted ? 'Return (dir.)' : 'Return',
      description: 'Adjusted-close return from the trade date to the latest price',
      width: 105,
      align: 'right',
      headerAlign: 'right',
      valueGetter: (_v, row) => (adjusted ? da(row, 'transaction_return') : (row.performance.transaction?.return ?? null)),
      renderCell: ({ value }) => <Pct value={value} />,
    },
    {
      field: 'spy_tx',
      headerName: `${benchmark}`,
      description: `${benchmark} return over the same period`,
      width: 90,
      align: 'right',
      headerAlign: 'right',
      valueGetter: (_v, row) => row.performance.transaction?.benchmark_return ?? null,
      renderCell: ({ value }) => <Pct value={value} />,
    },
    {
      field: 'ex_tx',
      headerName: adjusted ? 'Excess (dir.)' : 'Excess',
      description: `Return minus ${benchmark} return`,
      width: 105,
      align: 'right',
      headerAlign: 'right',
      valueGetter: (_v, row) => (adjusted ? da(row, 'transaction_excess_return') : (row.performance.transaction?.excess_return ?? null)),
      renderCell: ({ value }) => <Pct value={value} />,
    },
    { field: 'disclosed', headerName: 'Disclosed', width: 110, valueGetter: (_v, row) => row.trade.disclosure_date },
    {
      field: 'ret_di',
      headerName: adjusted ? 'Since disc. (dir.)' : 'Since disclosure',
      description: 'Return from the disclosure date: what a follower could actually have captured',
      width: 130,
      align: 'right',
      headerAlign: 'right',
      valueGetter: (_v, row) => (adjusted ? da(row, 'disclosure_return') : (row.performance.disclosure?.return ?? null)),
      renderCell: ({ value }) => <Pct value={value} />,
    },
    {
      field: 'ex_di',
      headerName: adjusted ? 'Excess (dir.)' : 'Excess',
      width: 105,
      align: 'right',
      headerAlign: 'right',
      valueGetter: (_v, row) => (adjusted ? da(row, 'disclosure_excess_return') : (row.performance.disclosure?.excess_return ?? null)),
      renderCell: ({ value }) => <Pct value={value} />,
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 140,
      valueGetter: (_v, row) => row.performance.status,
      renderCell: ({ row }) =>
        row.performance.status === 'ok' ? (
          <Chip size="small" variant="outlined" color="success" label="priced" />
        ) : (
          <Tooltip title={row.performance.detail ?? row.performance.status}>
            <Chip size="small" variant="outlined" color="warning" label={row.performance.status.replace(/_/g, ' ')} />
          </Tooltip>
        ),
    },
  ];

  return (
    <Box sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
      <Stack direction="row" sx={{ alignItems: 'baseline', gap: 1.5, mb: 2, flexWrap: 'wrap' }}>
        <Typography component="h2" variant="h6">
          {ticker}
        </Typography>
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          {sec?.name}
        </Typography>
        {sec?.industry && (
          <Tooltip title={`${sec.sector ?? 'Sector n/a'} · SIC ${sec.sic_code ?? 'n/a'}${sec.cik ? ` · CIK ${sec.cik}` : ''} (SEC EDGAR)`}>
            <Chip size="small" variant="outlined" label={`${sec.industry}${sec.exchange ? ` · ${sec.exchange}` : ''}`} />
          </Tooltip>
        )}
        {sec?.price_status === 'ok' && <Chip size="small" color="success" variant="outlined" label="prices cached" />}
        {sec?.price_status === 'unavailable' && <Chip size="small" color="warning" variant="outlined" label="no price data" />}
      </Stack>

      {noPrices && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {sec?.price_status === 'unavailable'
            ? 'The price provider has no data for this ticker (it may be delisted, renamed or acquired), so performance can’t be calculated.'
            : 'Prices for this ticker haven’t been fetched yet. Run the enrichment job to load them.'}
        </Alert>
      )}
      {performance.error && !(performance.error instanceof ApiError && performance.error.status === 404) && (
        <QueryError error={performance.error} what="performance" />
      )}

      <Grid container spacing={2} columns={12} sx={{ mb: 2 }}>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <StatCard
            title="Latest price"
            loading={prices.isLoading}
            value={last?.close != null ? formatUsd(last.close) : '—'}
            interval={last ? `Close on ${last.date}` : 'No price data'}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <StatCard
            title="Congressional trades"
            loading={security.isLoading}
            value={formatInt(sec?.trade_count)}
            interval={items.length ? `${buys} buys · ${items.length - buys} other` : undefined}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <StatCard
            title="Avg return since trade"
            loading={performance.isLoading}
            value={formatPct(avgReturn)}
            interval={`Raw, ${priced.length} priced trades`}
            chip={avgReturn == null ? undefined : { label: avgReturn >= 0 ? 'up' : 'down', tone: avgReturn >= 0 ? 'up' : 'down' }}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <StatCard
            title={`Avg excess vs ${benchmark}`}
            loading={performance.isLoading}
            value={formatPct(avgExcess)}
            interval={`Raw, ${priced.length} priced trades`}
            chip={avgExcess == null ? undefined : { label: avgExcess >= 0 ? 'ahead' : 'behind', tone: avgExcess >= 0 ? 'up' : 'down' }}
          />
        </Grid>
        <Grid size={12}>
          <ChartCard
            title="Price history"
            caption={compare ? `Adjusted close, rebased to 100 · markers show trade dates` : 'Adjusted close · markers show trade dates'}
            loading={prices.isLoading}
            action={
              <Stack direction="row" sx={{ gap: 1.5, alignItems: 'center' }}>
                <FormControlLabel
                  control={<Switch size="small" checked={compare} onChange={(e) => setCompare(e.target.checked)} />}
                  label={`vs ${benchmark}`}
                />
                <ToggleButtonGroup size="small" exclusive value={range} onChange={(_e, v: Range | null) => v && setRange(v)}>
                  {(['3M', '6M', '1Y', 'ALL'] as Range[]).map((r) => (
                    <ToggleButton key={r} value={r}>
                      {r === 'ALL' ? 'All' : r}
                    </ToggleButton>
                  ))}
                </ToggleButtonGroup>
              </Stack>
            }
          >
            {bars.length ? (
              <PriceChart
                ticker={ticker}
                bars={bars}
                benchmarkBars={spy.data?.bars}
                benchmarkTicker={benchmark}
                trades={items}
                compare={compare && !!spy.data?.bars.length}
                from={from}
              />
            ) : (
              <Typography variant="body2" sx={{ color: 'text.secondary', py: 6, textAlign: 'center' }}>
                No price history available.
              </Typography>
            )}
          </ChartCard>
        </Grid>
      </Grid>

      <Stack direction="row" sx={{ alignItems: 'center', justifyContent: 'space-between', mb: 2, flexWrap: 'wrap', gap: 1 }}>
        <Typography component="h2" variant="h6">
          Trade performance
        </Typography>
        <ToggleButtonGroup size="small" exclusive value={adjusted ? 'adj' : 'raw'} onChange={(_e, v: string | null) => v && setAdjusted(v === 'adj')}>
          <ToggleButton value="raw">Raw price change</ToggleButton>
          <ToggleButton value="adj">Direction-adjusted (sells flipped)</ToggleButton>
        </ToggleButtonGroup>
      </Stack>
      <AppDataGrid
        rows={items}
        columns={columns}
        getRowId={(r: TradePerformance) => r.trade.id}
        loading={performance.isLoading}
        initialState={{
          pagination: { paginationModel: { pageSize: 25 } },
          sorting: { sortModel: [{ field: 'traded', sort: 'desc' }] },
        }}
        autoHeight
        sx={{ minHeight: 300 }}
      />
    </Box>
  );
}
