import * as React from 'react';
import { Link as RouterLink, useNavigate, useSearchParams } from 'react-router-dom';
import type { GridColDef } from '@mui/x-data-grid';
import Box from '@mui/material/Box';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Link from '@mui/material/Link';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import AppDataGrid from '../components/AppDataGrid';
import { ChamberChip } from '../components/Chips';
import QueryError from '../components/QueryError';
import { usePoliticians } from '../api/hooks';
import type { Politician } from '../api/types';

const columns: GridColDef<Politician>[] = [
  {
    field: 'name',
    headerName: 'Politician',
    flex: 1,
    minWidth: 200,
    renderCell: ({ row }) => (
      <Link component={RouterLink} to={`/politicians/${row.id}`} underline="hover">
        {row.name}
      </Link>
    ),
  },
  {
    field: 'chamber',
    headerName: 'Chamber',
    width: 110,
    renderCell: ({ row }) => <ChamberChip chamber={row.chamber} />,
  },
  { field: 'party', headerName: 'Party', width: 90, valueFormatter: (v: string | null) => v ?? '—' },
  { field: 'state', headerName: 'State', width: 80, valueFormatter: (v: string | null) => v ?? '—' },
  { field: 'trade_count', headerName: 'Trades', type: 'number', width: 100 },
  { field: 'latest_trade_date', headerName: 'Latest trade', width: 130, valueFormatter: (v: string | null) => v ?? '—' },
];

export default function Politicians() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const q = params.get('q') ?? '';
  const chamber = params.get('chamber') ?? '';
  const set = (key: string, value: string) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (value) next.set(key, value);
        else next.delete(key);
        return next;
      },
      { replace: true },
    );

  const [input, setInput] = React.useState(q);
  React.useEffect(() => {
    const t = setTimeout(() => set('q', input.trim()), 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [input]);

  const { data, isLoading, error } = usePoliticians({ q: q || undefined, chamber: chamber || undefined });

  return (
    <Box sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
      <Typography component="h2" variant="h6" sx={{ mb: 2 }}>
        Politicians
      </Typography>
      {error && <QueryError error={error} what="politicians" />}
      <Stack direction="row" useFlexGap sx={{ flexWrap: 'wrap', gap: 1.5, mb: 2 }}>
        <TextField size="small" label="Search name" value={input} onChange={(e) => setInput(e.target.value)} />
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel id="chamber-label">Chamber</InputLabel>
          <Select labelId="chamber-label" label="Chamber" value={chamber} onChange={(e) => set('chamber', e.target.value)}>
            <MenuItem value="">All</MenuItem>
            <MenuItem value="house">House</MenuItem>
            <MenuItem value="senate">Senate</MenuItem>
          </Select>
        </FormControl>
      </Stack>
      <AppDataGrid
        rows={data?.items ?? []}
        columns={columns}
        loading={isLoading}
        initialState={{
          pagination: { paginationModel: { pageSize: 25 } },
          sorting: { sortModel: [{ field: 'trade_count', sort: 'desc' }] },
        }}
        onRowClick={(p) => navigate(`/politicians/${p.id}`)}
        sx={{ '& .MuiDataGrid-row': { cursor: 'pointer' }, minHeight: 320 }}
        autoHeight
      />
    </Box>
  );
}
