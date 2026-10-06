import { useTheme } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Skeleton from '@mui/material/Skeleton';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { SparkLineChart } from '@mui/x-charts/SparkLineChart';
import { lineClasses } from '@mui/x-charts/LineChart';

export type StatCardProps = {
  title: string;
  value?: string;
  interval?: string;
  /** Optional chip, e.g. "+12%" or "3 invalid". */
  chip?: { label: string; tone: 'up' | 'down' | 'neutral' | 'warning' };
  /** Optional sparkline. */
  data?: number[];
  dates?: string[];
  loading?: boolean;
};

function AreaGradient({ color, id }: { color: string; id: string }) {
  return (
    <defs>
      <linearGradient id={id} x1="50%" y1="0%" x2="50%" y2="100%">
        <stop offset="0%" stopColor={color} stopOpacity={0.3} />
        <stop offset="100%" stopColor={color} stopOpacity={0} />
      </linearGradient>
    </defs>
  );
}

export default function StatCard({ title, value, interval, chip, data, dates, loading }: StatCardProps) {
  const theme = useTheme();
  const light = theme.palette.mode === 'light';
  const chartColors = {
    up: light ? theme.palette.success.main : theme.palette.success.dark,
    down: light ? theme.palette.error.main : theme.palette.error.dark,
    warning: light ? theme.palette.warning.main : theme.palette.warning.dark,
    neutral: light ? theme.palette.grey[400] : theme.palette.grey[700],
  };
  const chipColors = { up: 'success', down: 'error', warning: 'warning', neutral: 'default' } as const;
  const tone = chip?.tone ?? 'neutral';
  const gradientId = `area-gradient-${title.replace(/\W+/g, '-')}`;

  return (
    <Card variant="outlined" sx={{ height: '100%', flexGrow: 1 }}>
      <CardContent>
        <Typography component="h2" variant="subtitle2" gutterBottom>
          {title}
        </Typography>
        <Stack direction="column" sx={{ justifyContent: 'space-between', flexGrow: '1', gap: 1 }}>
          <Stack sx={{ justifyContent: 'space-between' }}>
            <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center' }}>
              {loading ? (
                <Skeleton width={90} height={44} />
              ) : (
                <Typography variant="h4" component="p">
                  {value ?? '—'}
                </Typography>
              )}
              {chip && !loading && <Chip size="small" color={chipColors[tone]} label={chip.label} />}
            </Stack>
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              {interval}
            </Typography>
          </Stack>
          {data && data.length > 1 && (
            <Box sx={{ width: '100%', height: 50 }}>
              <SparkLineChart
                color={chartColors[tone]}
                data={data}
                area
                showHighlight
                showTooltip
                xAxis={{ scaleType: 'band', data: dates ?? data.map((_, i) => String(i)) }}
                sx={{ [`& .${lineClasses.area}`]: { fill: `url(#${gradientId})` } }}
              >
                <AreaGradient color={chartColors[tone]} id={gradientId} />
              </SparkLineChart>
            </Box>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}
