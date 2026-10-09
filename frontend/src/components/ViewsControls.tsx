import * as React from 'react';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Divider from '@mui/material/Divider';
import IconButton from '@mui/material/IconButton';
import ListItemText from '@mui/material/ListItemText';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded';
import EditRoundedIcon from '@mui/icons-material/EditRounded';
import type { SavedView } from '../api/types';

type NameDialog = { mode: 'save' } | { mode: 'rename'; view: SavedView } | null;

/** Saved views: save the current rule and filters under a name, load, rename, delete. Stored locally by the app; no account, no sync. */
export default function ViewsControls({
  views,
  activeViewId,
  dirty,
  error,
  onSave,
  onUpdate,
  onLoad,
  onRename,
  onDelete,
}: {
  views: SavedView[];
  activeViewId: number | null;
  dirty: boolean;
  error: string | null;
  onSave: (name: string) => Promise<boolean>;
  onUpdate: () => void;
  onLoad: (v: SavedView) => void;
  onRename: (v: SavedView, name: string) => Promise<boolean>;
  onDelete: (v: SavedView) => void;
}) {
  const [anchor, setAnchor] = React.useState<HTMLElement | null>(null);
  const [dialog, setDialog] = React.useState<NameDialog>(null);
  const [name, setName] = React.useState('');
  const active = views.find((v) => v.id === activeViewId) ?? null;
  const open = (d: NameDialog, initial = '') => {
    setAnchor(null);
    setName(initial);
    setDialog(d);
  };
  const submit = async () => {
    if (!dialog || !name.trim()) return;
    const ok = dialog.mode === 'save' ? await onSave(name.trim()) : await onRename(dialog.view, name.trim());
    if (ok) setDialog(null);
  };
  return (
    <>
      <Button size="small" variant="outlined" onClick={(e) => setAnchor(e.currentTarget)} aria-haspopup="menu">
        {active ? `View: ${active.name}${dirty ? ' (changed)' : ''}` : 'Views'}
      </Button>
      <Menu anchorEl={anchor} open={!!anchor} onClose={() => setAnchor(null)}>
        <MenuItem onClick={() => open({ mode: 'save' }, active ? '' : '')}>Save current as new view…</MenuItem>
        {active && dirty && (
          <MenuItem
            onClick={() => {
              setAnchor(null);
              onUpdate();
            }}
          >
            Update “{active.name}” with current settings
          </MenuItem>
        )}
        <Divider />
        {views.length === 0 && (
          <MenuItem disabled>
            <Typography variant="body2" color="text.secondary">
              No saved views yet
            </Typography>
          </MenuItem>
        )}
        {views.map((v) => (
          <MenuItem
            key={v.id}
            selected={v.id === activeViewId}
            onClick={() => {
              setAnchor(null);
              onLoad(v);
            }}
          >
            <ListItemText primary={v.name} />
            <Tooltip title="Rename">
              <IconButton size="small" aria-label={`Rename ${v.name}`} onClick={(e) => { e.stopPropagation(); open({ mode: 'rename', view: v }, v.name); }}>
                <EditRoundedIcon fontSize="inherit" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Delete">
              <IconButton size="small" aria-label={`Delete ${v.name}`} onClick={(e) => { e.stopPropagation(); setAnchor(null); onDelete(v); }}>
                <DeleteOutlineRoundedIcon fontSize="inherit" />
              </IconButton>
            </Tooltip>
          </MenuItem>
        ))}
      </Menu>
      <Dialog open={!!dialog} onClose={() => setDialog(null)} maxWidth="xs" fullWidth aria-labelledby="view-name-title">
        <DialogTitle id="view-name-title">{dialog?.mode === 'rename' ? 'Rename view' : 'Save view'}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            size="small"
            margin="dense"
            label="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submit()}
            slotProps={{ htmlInput: { maxLength: 80 } }}
            error={!!error}
            helperText={error ?? 'Saves the rule settings and filters on this device.'}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialog(null)}>Cancel</Button>
          <Button variant="contained" disabled={!name.trim()} onClick={submit}>
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
