import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Grid from '@mui/material/Grid';
import Link from '@mui/material/Link';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { useTheme } from '@mui/material/styles';
import { useOverview } from '../api/hooks';
import ChartCard from '../components/ChartCard';
import MonthlyBarChart from '../components/MonthlyBarChart';
import QueryError from '../components/QueryError';
import SplitDonutCard from '../components/SplitDonutCard';
import StatCard from '../components/StatCard';
import TopTickersChart from '../components/TopTickersChart';
import TradesGrid from '../components/TradesGrid';
import { formatInt } from '../lib/format';

const WINDOW_DAYS = 30;

export default function Overview() {
  const theme = useTheme();
  const palette = (theme.vars ?? theme).palette;
  const { data, isLoading, error } = useOverview(WINDOW_DAYS);

  const daily = data?.daily ?? [];
  const half = Math.floor(daily.length / 2);
  const recent = daily.slice(half).reduce((s, d) => s + d.count, 0);
  const earlier = daily.slice(0, half).reduce((s, d) => s + d.count, 0);
  const change = earlier ? Math.round(((recent - earlier) / earlier) * 100) : null;

  const t = data?.totals;
  const buyShare = t && t.trades_in_window ? Math.round((t.buys_in_window / t.trades_in_window) * 100) : null;
  const months = (data?.monthly ?? []).slice(-12);
  const monthTotal = months.reduce((s, m) => s + m.buys + m.sells + m.other, 0);

  return (
    <Box sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
      <Typography component="h2" variant="h6" sx={{ mb: 2 }}>
        Overview
      </Typography>
      {error && <QueryError error={error} what="the overview" />}
      <Grid container spacing={2} columns={12} sx={{ mb: 2 }}>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <StatCard
            title="Disclosures"
            loading={isLoading}
            value={formatInt(t?.trades_in_window)}
            interval={`Filed in the last ${WINDOW_DAYS} days`}
            chip={change == null ? undefined : { label: `${change > 0 ? '+' : ''}${change}%`, tone: 'neutral' }}
            data={daily.map((d) => d.count)}
            dates={daily.map((d) => d.date)}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <StatCard
            title="Buys / sells"
            loading={isLoading}
            value={t ? `${formatInt(t.buys_in_window)} / ${formatInt(t.sells_in_window)}` : undefined}
            interval={`Last ${WINDOW_DAYS} days`}
            chip={buyShare == null ? undefined : { label: `${buyShare}% buys`, tone: 'neutral' }}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <StatCard
            title="Politicians tracked"
            loading={isLoading}
            value={formatInt(t?.politicians)}
            interval={`${formatInt(t?.securities)} securities traded`}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <StatCard
            title="Trades stored"
            loading={isLoading}
            value={formatInt(t?.trades)}
            interval={`Latest disclosure ${data?.latest_disclosure_date ?? '—'}`}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <ChartCard
            title="Disclosures by month"
            headline={formatInt(monthTotal)}
            caption="Buys and sells by filing month, last 12 months"
            loading={isLoading}
          >
            <MonthlyBarChart data={months} />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <ChartCard
            title="Most-traded tickers"
            caption={`Trades disclosed in the last ${WINDOW_DAYS} days`}
            loading={isLoading}
          >
            <TopTickersChart data={data?.top_tickers ?? []} />
          </ChartCard>
        </Grid>
      </Grid>

      <Typography component="h2" variant="h6" sx={{ mb: 2 }}>
        Details
      </Typography>
      <Grid container spacing={2} columns={12}>
        <Grid size={{ xs: 12, lg: 9 }}>
          <TradesGrid filters={{}} pageSize={10} />
        </Grid>
        <Grid size={{ xs: 12, lg: 3 }}>
          <Stack direction={{ xs: 'column', sm: 'row', lg: 'column' }} sx={{ gap: 2 }}>
            <SplitDonutCard
              title={`Buy / sell split (${WINDOW_DAYS}d)`}
              centerPrimary={formatInt(t?.trades_in_window)}
              centerSecondary="Trades"
              slices={[
                { label: 'Buys', value: t?.buys_in_window ?? 0, color: palette.success.main },
                { label: 'Sells', value: t?.sells_in_window ?? 0, color: palette.error.main },
              ]}
            />
            <Card variant="outlined" sx={{ flexGrow: 1 }}>
              <CardContent>
                <Typography component="h2" variant="subtitle2">
                  Most active politicians
                </Typography>
                <List dense disablePadding>
                  {(data?.top_politicians ?? []).map((p) => (
                    <ListItem key={p.id} disableGutters secondaryAction={<Chip size="small" label={p.trades} />}>
                      <ListItemText
                        primary={
                          <Link component={RouterLink} to={`/politicians/${p.id}`} underline="hover">
                            {p.name}
                          </Link>
                        }
                        secondary={p.chamber === 'senate' ? 'Senate' : 'House'}
                      />
                    </ListItem>
                  ))}
                </List>
              </CardContent>
            </Card>
          </Stack>
        </Grid>
      </Grid>
    </Box>
  );
}
