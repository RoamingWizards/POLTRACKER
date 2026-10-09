import * as React from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import ListSubheader from '@mui/material/ListSubheader';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import AddRoundedIcon from '@mui/icons-material/AddRounded';
import { usePolitician } from '../api/hooks';
import type { FilterField, FilterSpec } from '../api/types';
import { FIELD_DEFS, addFilter, clearFilters, defaultFilter, describeFilter, editFilter, fieldDef, isCompleteFilter, removeFilter } from '../lib/filters';

const GROUPS = ['Politician', 'Security', 'Trade', 'Context', 'Review'] as const;

function FilterChip({ filter, onEdit, onDelete }: { filter: FilterSpec; onEdit: () => void; onDelete: () => void }) {
  const byId = filter.field === 'politician' && filter.op === 'is';
  const { data } = usePolitician(byId ? Number(filter.value) : 0, byId); // only a politician-by-id chip needs the name looked up
  const label = byId ? `Politician: ${data?.name ?? `#${filter.value}`}` : describeFilter(filter);
  return <Chip size="small" label={label} onClick={onEdit} onDelete={onDelete} aria-label={`Filter ${label}`} />;
}

/** Add or edit one filter. Applied only when the value is complete; the server validates again. */
function FilterEditor({ initial, isNew, onApply, onClose }: { initial: FilterSpec | null; isNew: boolean; onApply: (f: FilterSpec) => void; onClose: () => void }) {
  const [draft, setDraft] = React.useState<FilterSpec | null>(initial);
  React.useEffect(() => setDraft(initial), [initial]);
  const def = draft ? fieldDef(draft.field) : null;
  const setField = (field: FilterField) => setDraft(defaultFilter(field));
  const setOp = (op: string) =>
    setDraft((d) => (d ? { ...d, op, value: op === 'between' ? ['', ''] : Array.isArray(d.value) ? '' : d.value } : d));
  const range = Array.isArray(draft?.value) ? (draft!.value as string[]) : ['', ''];
  const complete = draft ? isCompleteFilter(draft) : false;
  return (
    <Dialog open={!!initial} onClose={onClose} maxWidth="xs" fullWidth aria-labelledby="filter-editor-title">
      <DialogTitle id="filter-editor-title">{isNew ? 'Add filter' : 'Edit filter'}</DialogTitle>
      <DialogContent>
        {draft && def && (
          <Stack spacing={2} sx={{ mt: 1 }}>
            <FormControl size="small" fullWidth>
              <InputLabel id="filter-field-label">Field</InputLabel>
              <Select labelId="filter-field-label" label="Field" value={draft.field} onChange={(e) => setField(e.target.value as FilterField)}>
                {GROUPS.flatMap((g) => [
                  <ListSubheader key={g}>{g}</ListSubheader>,
                  ...FIELD_DEFS.filter((d) => d.group === g).map((d) => (
                    <MenuItem key={d.field} value={d.field}>
                      {d.label}
                    </MenuItem>
                  )),
                ])}
              </Select>
            </FormControl>
            {def.ops.length > 1 && (
              <FormControl size="small" fullWidth>
                <InputLabel id="filter-op-label">Condition</InputLabel>
                <Select labelId="filter-op-label" label="Condition" value={draft.op} onChange={(e) => setOp(e.target.value)}>
                  {def.ops.map((o) => (
                    <MenuItem key={o.op} value={o.op}>
                      {o.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
            {def.kind === 'enum' && (
              <FormControl size="small" fullWidth>
                <InputLabel id="filter-value-label">Value</InputLabel>
                <Select labelId="filter-value-label" label="Value" value={String(draft.value)} onChange={(e) => setDraft({ ...draft, value: e.target.value })}>
                  {def.options!.map((o) => (
                    <MenuItem key={o.value} value={o.value}>
                      {o.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
            {(def.kind === 'text' || def.kind === 'number') && (
              <TextField
                size="small"
                fullWidth
                autoFocus
                label={def.kind === 'number' && def.unit ? `Value (${def.unit})` : 'Value'}
                type={def.kind === 'number' ? 'number' : 'text'}
                value={String(draft.value)}
                onChange={(e) => setDraft({ ...draft, value: e.target.value })}
                helperText={def.hint}
              />
            )}
            {def.kind === 'date' && draft.op !== 'between' && (
              <TextField size="small" fullWidth type="date" label="Date" value={String(draft.value)} onChange={(e) => setDraft({ ...draft, value: e.target.value })} slotProps={{ inputLabel: { shrink: true } }} />
            )}
            {def.kind === 'date' && draft.op === 'between' && (
              <Stack direction="row" spacing={1}>
                <TextField size="small" fullWidth type="date" label="From" value={range[0]} onChange={(e) => setDraft({ ...draft, value: [e.target.value, range[1]] })} slotProps={{ inputLabel: { shrink: true } }} />
                <TextField size="small" fullWidth type="date" label="To" value={range[1]} onChange={(e) => setDraft({ ...draft, value: [range[0], e.target.value] })} slotProps={{ inputLabel: { shrink: true } }} />
              </Stack>
            )}
            {def.hint && def.kind === 'enum' && (
              <Typography variant="caption" color="text.secondary">
                {def.hint}
              </Typography>
            )}
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" disabled={!complete} onClick={() => draft && onApply(draft)}>
          Apply
        </Button>
      </DialogActions>
    </Dialog>
  );
}

/** "Add filter" control plus the active filters as removable, editable chips. Filters combine with AND. */
export default function FilterBar({ filters, onChange }: { filters: FilterSpec[]; onChange: (next: FilterSpec[]) => void }) {
  const [menu, setMenu] = React.useState<HTMLElement | null>(null);
  const [editing, setEditing] = React.useState<{ index: number | null; spec: FilterSpec } | null>(null);
  const startNew = (field: FilterField) => {
    setMenu(null);
    setEditing({ index: null, spec: defaultFilter(field) });
  };
  return (
    <Stack direction="row" useFlexGap sx={{ flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
      <Button size="small" variant="outlined" startIcon={<AddRoundedIcon />} onClick={(e) => setMenu(e.currentTarget)}>
        Add filter
      </Button>
      <Menu anchorEl={menu} open={!!menu} onClose={() => setMenu(null)} slotProps={{ paper: { sx: { maxHeight: 420 } } }}>
        {GROUPS.flatMap((g) => [
          <ListSubheader key={g}>{g}</ListSubheader>,
          ...FIELD_DEFS.filter((d) => d.group === g).map((d) => (
            <MenuItem key={d.field} dense onClick={() => startNew(d.field)}>
              {d.label}
            </MenuItem>
          )),
        ])}
      </Menu>
      {filters.map((f, i) => (
        <FilterChip key={`${f.field}-${i}`} filter={f} onEdit={() => setEditing({ index: i, spec: f })} onDelete={() => onChange(removeFilter(filters, i))} />
      ))}
      {filters.length > 0 && (
        <Button size="small" onClick={() => onChange(clearFilters())}>
          Clear all
        </Button>
      )}
      {filters.length > 1 && (
        <Box component="span">
          <Typography variant="caption" color="text.secondary">
            all of these must match
          </Typography>
        </Box>
      )}
      <FilterEditor
        initial={editing?.spec ?? null}
        isNew={editing?.index == null}
        onClose={() => setEditing(null)}
        onApply={(f) => {
          onChange(editing?.index == null ? addFilter(filters, f) : editFilter(filters, editing.index, f));
          setEditing(null);
        }}
      />
    </Stack>
  );
}
