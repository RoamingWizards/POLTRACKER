import { useQueryClient } from '@tanstack/react-query';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableRow from '@mui/material/TableRow';
import Typography from '@mui/material/Typography';
import { useTheme } from '@mui/material/styles';
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded';
import { useHealth, useStatus } from '../api/hooks';
import QueryError from '../components/QueryError';
import SplitDonutCard from '../components/SplitDonutCard';
import StatCard from '../components/StatCard';
import { formatDateTime, formatInt, timeAgo } from '../lib/format';

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <TableRow>
      <TableCell sx={{ color: 'text.secondary', width: '45%' }}>{label}</TableCell>
      <TableCell align="right">{children}</TableCell>
    </TableRow>
  );
}

export default function DataStatus() {
  const theme = useTheme();
  const palette = (theme.vars ?? theme).palette;
  const queryClient = useQueryClient();
  const { data: s, isLoading, error, isFetching } = useStatus();
  const health = useHealth();

  return (
    <Box sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
      <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography component="h2" variant="h6">
          Data Status
        </Typography>
        <Button
          size="small"
          variant="outlined"
          startIcon={<RefreshRoundedIcon />}
          disabled={isFetching}
          onClick={() => queryClient.invalidateQueries({ queryKey: ['status'] })}
        >
          Refresh
        </Button>
      </Stack>
      {error && <QueryError error={error} what="status" />}
      {s?.ingest_stale && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          <AlertTitle>Ingestion looks stale</AlertTitle>
          {s.last_successful_ingest_at
            ? `The last successful ingest was ${timeAgo(s.last_successful_ingest_at)} (${formatDateTime(s.last_successful_ingest_at)}), older than the ${s.ingest_stale_after_hours}-hour threshold.`
            : 'No successful ingest has been recorded yet.'}{' '}
          If the scheduled workflow is not running, check that it has not been disabled: GitHub disables scheduled
          workflows in public repositories after 60 days without repository activity.
        </Alert>
      )}

      <Grid container spacing={2} columns={12} sx={{ mb: 2 }}>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <StatCard
            title="Last successful ingest"
            loading={isLoading}
            value={s?.last_successful_ingest_at ? timeAgo(s.last_successful_ingest_at) : 'none yet'}
            interval={s ? (s.last_successful_ingest_at ? formatDateTime(s.last_successful_ingest_at) : 'No run recorded') : undefined}
            chip={s ? (s.ingest_stale ? { label: 'stale', tone: 'warning' } : { label: 'on schedule', tone: 'up' }) : undefined}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <StatCard title="Trades stored" loading={isLoading} value={formatInt(s?.trades_total)} interval={`${formatInt(s?.politicians_total)} politicians`} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <StatCard title="Latest disclosure" loading={isLoading} value={s?.latest_disclosure_date ?? '—'} interval={`Latest trade ${s?.latest_transaction_date ?? '—'}`} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <StatCard
            title="Invalid-date trades"
            loading={isLoading}
            value={formatInt(s?.invalid_date_trades)}
            interval="Excluded from price enrichment"
            chip={s ? (s.invalid_date_trades ? { label: 'review', tone: 'warning' } : { label: 'clean', tone: 'up' }) : undefined}
          />
        </Grid>
      </Grid>

      <Grid container spacing={2} columns={12}>
        <Grid size={{ xs: 12, md: 5, lg: 4 }}>
          <SplitDonutCard
            title="Price coverage (securities)"
            centerPrimary={formatInt(s?.securities_total)}
            centerSecondary="Tickers"
            slices={[
              { label: 'Priced', value: s?.securities_priced ?? 0, color: palette.success.main },
              { label: 'No data from provider', value: s?.securities_unavailable ?? 0, color: palette.warning.main },
              { label: 'Not fetched yet', value: s?.securities_pending ?? 0, color: palette.grey[500] },
            ]}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 7, lg: 8 }}>
          <Card variant="outlined">
            <CardContent>
              <Typography component="h2" variant="subtitle2" gutterBottom>
                Pipeline
              </Typography>
              <Table size="small">
                <TableBody>
                  <Row label="API">
                    <Chip
                      size="small"
                      color={health.data?.status === 'ok' ? 'success' : 'error'}
                      label={health.data?.status === 'ok' ? 'online' : health.isLoading ? 'checking…' : 'unreachable'}
                    />
                  </Row>
                  <Row label="Trade sources">
                    {Object.entries(s?.trades_by_source ?? {}).map(([name, n]) => (
                      <Chip key={name} size="small" variant="outlined" label={`${name}: ${formatInt(n)}`} sx={{ ml: 0.5 }} />
                    ))}
                  </Row>
                  <Row label="Daily price bars cached">{formatInt(s?.price_bars)}</Row>
                  <Row label="Latest price bar">{s?.latest_bar_date ?? '—'}</Row>
                  <Row label={`Benchmark (${s?.benchmark_ticker ?? 'SPY'})`}>
                    {s?.benchmark_from ? `${s.benchmark_from} → ${s.benchmark_to}` : 'not loaded'}
                    {s?.benchmark_status && (
                      <Chip size="small" sx={{ ml: 1 }} color={s.benchmark_status === 'ok' ? 'success' : 'warning'} label={s.benchmark_status} />
                    )}
                  </Row>
                  <Row label="Securities with no provider data">{formatInt(s?.securities_unavailable)}</Row>
                </TableBody>
              </Table>
              <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mt: 2 }}>
                Trades come from the CongressInvests API, which refreshes about every 6 hours. Prices come from
                the backend’s price provider. The browser only talks to the POLTRACKER API.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
