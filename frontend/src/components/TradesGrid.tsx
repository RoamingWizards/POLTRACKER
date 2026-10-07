import * as React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import type { GridColDef, GridPaginationModel, GridSortModel } from '@mui/x-data-grid';
import Link from '@mui/material/Link';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import OpenInNewRoundedIcon from '@mui/icons-material/OpenInNewRounded';
import Chip from '@mui/material/Chip';
import TradeContextDialog from './TradeContextDialog';
import AppDataGrid from './AppDataGrid';
import { ChamberChip, TypeChip } from './Chips';
import QueryError from './QueryError';
import { useTrades } from '../api/hooks';
import type { Trade, TradeQuery, TradeSortField } from '../api/types';
import { formatAmountRange } from '../lib/format';

const SORTABLE: TradeSortField[] = ['transaction_date', 'disclosure_date', 'amount_min', 'ticker', 'politician_name'];

function contextColumn(open: (t: Trade) => void): GridColDef<Trade> {
  return {
    field: 'context',
    headerName: 'Context',
    width: 150,
    sortable: false,
    renderCell: ({ row }) => {
      const c = row.context;
      if (!c) return '—';
      const label = c.flagged_for_contextual_review ? 'Flagged for review' : c.committee_relevance ? 'Committee-relevant' : c.committee_relevance === null ? 'Unknown' : 'No flag';
      return (
        <Chip
          size="small"
          variant="outlined"
          color={c.flagged_for_contextual_review ? 'warning' : 'default'}
          label={label}
          onClick={() => open(row)}
          aria-label={`Context signals for ${row.ticker ?? 'trade'}`}
        />
      );
    },
  };
}

const columns: GridColDef<Trade>[] = [
  { field: 'disclosure_date', headerName: 'Disclosed', width: 110 },
  { field: 'transaction_date', headerName: 'Traded', width: 110 },
  {
    field: 'politician_name',
    headerName: 'Politician',
    flex: 1,
    minWidth: 160,
    renderCell: ({ row }) => (
      <Link component={RouterLink} to={`/politicians/${row.politician_id}`} underline="hover">
        {row.politician_name}
      </Link>
    ),
  },
  {
    field: 'chamber',
    headerName: 'Chamber',
    width: 100,
    sortable: false,
    renderCell: ({ row }) => <ChamberChip chamber={row.chamber} />,
  },
  {
    field: 'ticker',
    headerName: 'Ticker',
    width: 90,
    renderCell: ({ row }) =>
      row.ticker ? (
        <Link component={RouterLink} to={`/securities/${row.ticker}`} underline="hover" sx={{ fontWeight: 600 }}>
          {row.ticker}
        </Link>
      ) : (
        '—'
      ),
  },
  { field: 'asset_name', headerName: 'Asset', flex: 1.4, minWidth: 180, sortable: false },
  {
    field: 'transaction_type',
    headerName: 'Type',
    width: 120,
    sortable: false,
    renderCell: ({ row }) => <TypeChip type={row.transaction_type} />,
  },
  {
    field: 'amount_min',
    headerName: 'Amount',
    width: 150,
    align: 'right',
    headerAlign: 'right',
    renderCell: ({ row }) => formatAmountRange(row.amount_min, row.amount_max),
  },
  {
    field: 'source_url',
    headerName: 'Filing',
    width: 70,
    sortable: false,
    align: 'center',
    headerAlign: 'center',
    renderCell: ({ row }) =>
      row.source_url ? (
        <Tooltip title="Open original disclosure">
          <IconButton size="small" component="a" href={row.source_url} target="_blank" rel="noreferrer noopener">
            <OpenInNewRoundedIcon fontSize="inherit" />
          </IconButton>
        </Tooltip>
      ) : null,
  },
];

export type TradeFilters = Omit<TradeQuery, 'limit' | 'offset' | 'sort_by' | 'order'>;

/** Server-paginated, server-sorted trades table. Filters come from the parent. */
export default function TradesGrid({
  filters,
  pageSize = 25,
  hidePoliticianColumn = false,
}: {
  filters: TradeFilters;
  pageSize?: number;
  hidePoliticianColumn?: boolean;
}) {
  const [paging, setPaging] = React.useState<GridPaginationModel>({ page: 0, pageSize });
  const [sort, setSort] = React.useState<GridSortModel>([{ field: 'disclosure_date', sort: 'desc' }]);
  const [selected, setSelected] = React.useState<Trade | null>(null);
  const gridColumns = React.useMemo(() => [...columns.slice(0, -1), contextColumn(setSelected), columns[columns.length - 1]], []);

  const filtersKey = JSON.stringify(filters);
  React.useEffect(() => {
    setPaging((p) => ({ ...p, page: 0 }));
  }, [filtersKey]);

  const active = sort[0];
  const sortBy = SORTABLE.find((f) => f === active?.field);
  const { data, error, isFetching } = useTrades({
    ...filters,
    limit: paging.pageSize,
    offset: paging.page * paging.pageSize,
    sort_by: sortBy,
    order: active?.sort ?? undefined,
  });

  return (
    <>
      {error && <QueryError error={error} what="trades" />}
      <AppDataGrid
        rows={data?.items ?? []}
        columns={gridColumns}
        columnVisibilityModel={{ politician_name: !hidePoliticianColumn, chamber: !hidePoliticianColumn }}
        loading={isFetching}
        rowCount={data?.total ?? 0}
        paginationMode="server"
        sortingMode="server"
        paginationModel={paging}
        onPaginationModelChange={setPaging}
        sortModel={sort}
        onSortModelChange={setSort}
        autoHeight
        sx={{ minHeight: 320 }}
      />
      <TradeContextDialog trade={selected} onClose={() => setSelected(null)} />
    </>
  );
}
