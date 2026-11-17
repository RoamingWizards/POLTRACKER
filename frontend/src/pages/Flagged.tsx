import * as React from 'react';
import dayjs from 'dayjs';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Typography from '@mui/material/Typography';
import TradesGrid from '../components/TradesGrid';
import { useTrades } from '../api/hooks';

const WINDOWS = [
  { key: '30', label: '30 days', days: 30 },
  { key: '90', label: '90 days', days: 90 },
  { key: '365', label: '1 year', days: 365 },
  { key: 'all', label: 'All', days: null },
] as const;

/** Trades flagged for contextual review (the canonical default-methodology flag), newest disclosure first. A review aid, not a finding. */
export default function Flagged() {
  const [win, setWin] = React.useState<string>('all');
  const days = WINDOWS.find((w) => w.key === win)?.days ?? null;
  const filters = React.useMemo(
    () => ({ flagged: true, date_from: days ? dayjs().subtract(days, 'day').format('YYYY-MM-DD') : undefined }),
    [days],
  );
  const total = useTrades({ ...filters, limit: 1 }).data?.total;

  return (
    <Box sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
      <Typography component="h2" variant="h6">
        Flagged trades{total !== undefined ? ` (${total})` : ''}
      </Typography>
      <Typography variant="body2" sx={{ color: 'text.secondary', mb: 2 }}>
        Trades the default context methodology flags for contextual review, most recently disclosed first. A flag is a review aid based on public
        disclosure data, not a finding of wrongdoing. Click a context chip to see the signals behind it.
      </Typography>
      <Stack direction="row" sx={{ mb: 1.5, alignItems: 'center', gap: 1.5 }}>
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          Traded within
        </Typography>
        <ToggleButtonGroup size="small" exclusive value={win} onChange={(_, v) => v && setWin(v)} aria-label="Trade date window">
          {WINDOWS.map((w) => (
            <ToggleButton key={w.key} value={w.key}>
              {w.label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </Stack>
      <TradesGrid filters={filters} />
    </Box>
  );
}
