import { DataGrid, type DataGridProps } from '@mui/x-data-grid';

/** The template's CustomizedDataGrid defaults, as a reusable wrapper. */
export default function AppDataGrid(props: DataGridProps) {
  return (
    <DataGrid
      getRowClassName={(params) => (params.indexRelativeToCurrentPage % 2 === 0 ? 'even' : 'odd')}
      pageSizeOptions={[10, 25, 50, 100]}
      disableColumnResize
      disableRowSelectionOnClick
      density="compact"
      {...props}
    />
  );
}
