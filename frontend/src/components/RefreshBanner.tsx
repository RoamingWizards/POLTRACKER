import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import LinearProgress from '@mui/material/LinearProgress';
import Box from '@mui/material/Box';
import { useRefreshStatus } from '../api/hooks';

const TRIGGER_TEXT = { startup: 'Updating data', scheduled: 'Scheduled update', manual: 'Updating data' } as const;

// Desktop app only. Shows what the background refresh is doing so the dashboard never looks blank or stuck:
// the cached data stays on screen and usable underneath.
export default function RefreshBanner() {
  const { data } = useRefreshStatus();
  if (!data?.enabled) return null;

  if (data.running) {
    const p = data.progress;
    const determinate = !!p && !!p.total && p.total > 0;
    const pct = determinate ? Math.min(100, Math.round((p!.done / p!.total!) * 100)) : undefined;
    const first = data.database_empty;
    return (
      <Alert severity="info" sx={{ width: '100%' }} role="status">
        <AlertTitle>
          {first ? 'Loading congressional trades for the first time' : TRIGGER_TEXT[data.trigger ?? 'manual']}
        </AlertTitle>
        {data.label ?? 'Working…'}
        {first && ' This can take a few minutes; the pages fill in as data arrives.'}
        <Box sx={{ mt: 1 }}>
          <LinearProgress variant={determinate ? 'determinate' : 'indeterminate'} value={pct} aria-label="Refresh progress" />
        </Box>
      </Alert>
    );
  }

  if (data.last_attempt_ok === false && data.last_error) {
    return (
      <Alert severity="warning" sx={{ width: '100%' }}>
        <AlertTitle>{data.database_empty ? 'No data yet' : 'Showing saved data'}</AlertTitle>
        The last update did not finish: {data.last_error} POLTRACKER will retry automatically.
      </Alert>
    );
  }
  return null;
}
