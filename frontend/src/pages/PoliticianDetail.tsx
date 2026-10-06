import { Link as RouterLink, useParams } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { usePolitician, useTrades } from '../api/hooks';
import ChartCard from '../components/ChartCard';
import { ChamberChip } from '../components/Chips';
import MonthlyBarChart from '../components/MonthlyBarChart';
import QueryError from '../components/QueryError';
import StatCard from '../components/StatCard';
import TopTickersChart from '../components/TopTickersChart';
import TradesGrid from '../components/TradesGrid';
import { formatInt, isSell } from '../lib/format';

const CHART_TRADES = 500;

export default function PoliticianDetail() {
  const id = Number(useParams().id);
  const politician = usePolitician(id);
  // The charts summarise up to the 500 most recent trades; the grid below pages through all of them.
  const trades = useTrades({ politician_id: id, limit: CHART_TRADES, sort_by: 'transaction_date', order: 'desc' });

  if (politician.error) return <QueryError error={politician.error} what="this politician" />;
  const p = politician.data;
  const items = trades.data?.items ?? [];

  const byMonth = new Map<string, { buys: number; sells: number }>();
  const byTicker = new Map<string, { buys: number; sells: number }>();
  for (const t of items) {
    const month = t.transaction_date.slice(0, 7);
    const m = byMonth.get(month) ?? { buys: 0, sells: 0 };
    const k = t.ticker ?? '—';
    const tk = byTicker.get(k) ?? { buys: 0, sells: 0 };
    if (t.transaction_type === 'buy') {
      m.buys++;
      tk.buys++;
    } else if (isSell(t.transaction_type)) {
      m.sells++;
      tk.sells++;
    }
    byMonth.set(month, m);
    byTicker.set(k, tk);
  }
  const monthly = [...byMonth.entries()].sort().map(([month, v]) => ({ month, ...v }));
  const topTickers = [...byTicker.entries()]
    .map(([ticker, v]) => ({ ticker, ...v }))
    .sort((a, b) => b.buys + b.sells - (a.buys + a.sells))
    .slice(0, 10);
  const buys = items.filter((t) => t.transaction_type === 'buy').length;
  const sells = items.filter((t) => isSell(t.transaction_type)).length;
  const truncated = (trades.data?.total ?? 0) > CHART_TRADES;

  return (
    <Box sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
      <Stack direction="row" sx={{ alignItems: 'center', gap: 1.5, mb: 2, flexWrap: 'wrap' }}>
        <Typography component="h2" variant="h6">
          {p?.name ?? 'Politician'}
        </Typography>
        {p && <ChamberChip chamber={p.chamber} />}
        {p?.party && <Chip size="small" variant="outlined" label={p.party} />}
        {p?.state && <Chip size="small" variant="outlined" label={p.state} />}
        <Box sx={{ flexGrow: 1 }} />
        <Button size="small" variant="outlined" component={RouterLink} to={`/trades?politician_id=${id}`}>
          Open in Trades
        </Button>
      </Stack>
      {p && !p.party && !p.state && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Party and state aren’t provided by the current data source.
        </Alert>
      )}
      <Grid container spacing={2} columns={12} sx={{ mb: 2 }}>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <StatCard title="Trades" loading={politician.isLoading} value={formatInt(p?.trade_count)} interval="All disclosed trades" />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <StatCard title="Latest trade" loading={politician.isLoading} value={p?.latest_trade_date ?? '—'} interval="By transaction date" />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <StatCard title="Buys" loading={trades.isLoading} value={formatInt(buys)} interval={truncated ? `Latest ${CHART_TRADES} trades` : 'All trades'} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <StatCard title="Sells" loading={trades.isLoading} value={formatInt(sells)} interval={truncated ? `Latest ${CHART_TRADES} trades` : 'All trades'} />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <ChartCard title="Activity by month" caption="Buys and sells by transaction month" loading={trades.isLoading}>
            <MonthlyBarChart data={monthly} />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <ChartCard title="Most-traded tickers" caption="Buys and sells per ticker" loading={trades.isLoading}>
            <TopTickersChart data={topTickers} />
          </ChartCard>
        </Grid>
      </Grid>
      <Typography component="h2" variant="h6" sx={{ mb: 2 }}>
        Trades
      </Typography>
      <TradesGrid filters={{ politician_id: id }} hidePoliticianColumn />
    </Box>
  );
}
