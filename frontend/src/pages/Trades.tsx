import * as React from 'react';
import { useSearchParams } from 'react-router-dom';
import dayjs from 'dayjs';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import TradesGrid, { type TradeFilters } from '../components/TradesGrid';
import { usePolitician } from '../api/hooks';
import type { Chamber } from '../api/types';

function PoliticianChip({ id, onDelete }: { id: number; onDelete: () => void }) {
  const { data } = usePolitician(id);
  return <Chip label={`Politician: ${data?.name ?? `#${id}`}`} onDelete={onDelete} />;
}

export default function Trades() {
  const [params, setParams] = useSearchParams();
  const get = (k: string) => params.get(k) ?? '';
  const update = React.useCallback(
    (key: string, value: string | null) => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (value) next.set(key, value);
          else next.delete(key);
          return next;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  // Ticker is typed freely, so debounce it into the URL.
  const [tickerInput, setTickerInput] = React.useState(get('ticker'));
  React.useEffect(() => {
    const t = setTimeout(() => update('ticker', tickerInput.trim().toUpperCase() || null), 350);
    return () => clearTimeout(t);
  }, [tickerInput, update]);

  const politicianId = Number(get('politician_id')) || undefined;
  const filters: TradeFilters = {
    ticker: get('ticker') || undefined,
    chamber: (get('chamber') as Chamber) || undefined,
    transaction_type: get('type') || undefined,
    politician_id: politicianId,
    date_from: get('from') || undefined,
    date_to: get('to') || undefined,
  };
  const anyFilter = Object.values(filters).some(Boolean);

  return (
    <Box sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
      <Typography component="h2" variant="h6" sx={{ mb: 2 }}>
        Trades
      </Typography>
      <Stack direction="row" useFlexGap sx={{ flexWrap: 'wrap', gap: 1.5, mb: 2, alignItems: 'center' }}>
        <TextField
          size="small"
          label="Ticker"
          value={tickerInput}
          onChange={(e) => setTickerInput(e.target.value)}
          sx={{ width: 120 }}
        />
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel id="chamber-label">Chamber</InputLabel>
          <Select labelId="chamber-label" label="Chamber" value={get('chamber')} onChange={(e) => update('chamber', e.target.value || null)}>
            <MenuItem value="">All</MenuItem>
            <MenuItem value="house">House</MenuItem>
            <MenuItem value="senate">Senate</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel id="type-label">Type</InputLabel>
          <Select labelId="type-label" label="Type" value={get('type')} onChange={(e) => update('type', e.target.value || null)}>
            <MenuItem value="">All</MenuItem>
            <MenuItem value="buy">Buy</MenuItem>
            <MenuItem value="sell">Sell</MenuItem>
            <MenuItem value="sell_partial">Sell (partial)</MenuItem>
            <MenuItem value="exchange">Exchange</MenuItem>
          </Select>
        </FormControl>
        <DatePicker
          label="Traded from"
          value={get('from') ? dayjs(get('from')) : null}
          onChange={(v) => update('from', v?.isValid() ? v.format('YYYY-MM-DD') : null)}
          slotProps={{ textField: { size: 'small', sx: { width: 195 } }, field: { clearable: true } }}
        />
        <DatePicker
          label="Traded to"
          value={get('to') ? dayjs(get('to')) : null}
          onChange={(v) => update('to', v?.isValid() ? v.format('YYYY-MM-DD') : null)}
          slotProps={{ textField: { size: 'small', sx: { width: 195 } }, field: { clearable: true } }}
        />
        {politicianId && <PoliticianChip id={politicianId} onDelete={() => update('politician_id', null)} />}
        {anyFilter && (
          <Button
            size="small"
            onClick={() => {
              setTickerInput('');
              setParams({}, { replace: true });
            }}
          >
            Clear filters
          </Button>
        )}
      </Stack>
      <TradesGrid filters={filters} />
    </Box>
  );
}
