import * as React from 'react';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import FormControl from '@mui/material/FormControl';
import FormControlLabel from '@mui/material/FormControlLabel';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import Stack from '@mui/material/Stack';
import Switch from '@mui/material/Switch';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import type { ContextRule } from '../api/types';
import { DEFAULT_RULE, KIND_LABEL, ruleKind, ruleProblem } from '../lib/filters';

function Threshold({ label, value, unit, disabled, onChange }: { label: string; value: number; unit: string; disabled: boolean; onChange: (n: number) => void }) {
  return (
    <TextField
      size="small"
      type="number"
      label={label}
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(Number(e.target.value))}
      slotProps={{ htmlInput: { min: 0, 'aria-label': label } }}
      sx={{ width: 190 }}
      helperText={unit}
    />
  );
}

/** Context rule settings. They change only which trades match YOUR screen; the stored objective context and the default flag are never rewritten. */
export default function ContextRuleDialog({ open, rule, onApply, onClose }: { open: boolean; rule: ContextRule; onApply: (r: ContextRule) => void; onClose: () => void }) {
  const [draft, setDraft] = React.useState<ContextRule>(rule);
  React.useEffect(() => {
    if (open) setDraft(rule);
  }, [open, rule]);
  const set = <K extends keyof ContextRule>(k: K, v: ContextRule[K]) => setDraft((d) => ({ ...d, [k]: v }));
  const problem = ruleProblem(draft);
  const kind = ruleKind(draft);
  const enabledCount = [draft.enable_trade_size_signal, draft.enable_disclosure_delay_signal, draft.enable_excess_return_signal].filter(Boolean).length;
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth aria-labelledby="rule-dialog-title">
      <DialogTitle id="rule-dialog-title">
        Context rule settings
        <Typography variant="body2" color="text.secondary" component="div">
          These settings define your custom screen. They never change the stored context or the default contextual-review flag.
        </Typography>
      </DialogTitle>
      <DialogContent dividers>
        <Stack spacing={2}>
          <Stack>
            <FormControlLabel
              control={<Switch checked={draft.committee_relevance_required} onChange={(e) => set('committee_relevance_required', e.target.checked)} />}
              label="Require committee relevance"
            />
            <FormControlLabel
              control={<Switch checked={draft.reviewed_direct_only} disabled={!draft.committee_relevance_required} onChange={(e) => set('reviewed_direct_only', e.target.checked)} />}
              label="Reviewed direct mappings only (off also counts reviewed related, supporting mappings)"
            />
            <FormControlLabel
              control={<Switch checked={draft.require_temporal_verification} disabled={!draft.committee_relevance_required} onChange={(e) => set('require_temporal_verification', e.target.checked)} />}
              label="Committee seat verified for the transaction date"
            />
          </Stack>
          <Stack spacing={1.5}>
            <Typography variant="subtitle2">Secondary signals</Typography>
            <Stack direction="row" spacing={2} sx={{ alignItems: 'flex-start' }}>
              <FormControlLabel control={<Switch checked={draft.enable_trade_size_signal} onChange={(e) => set('enable_trade_size_signal', e.target.checked)} />} label="Trade size" sx={{ width: 150 }} />
              <Threshold label="Percentile ≥" unit="of this member’s own earlier trades" value={draft.trade_size_percentile_threshold} disabled={!draft.enable_trade_size_signal} onChange={(n) => set('trade_size_percentile_threshold', n)} />
            </Stack>
            <Stack direction="row" spacing={2} sx={{ alignItems: 'flex-start' }}>
              <FormControlLabel control={<Switch checked={draft.enable_disclosure_delay_signal} onChange={(e) => set('enable_disclosure_delay_signal', e.target.checked)} />} label="Disclosure delay" sx={{ width: 150 }} />
              <Threshold label="Delay more than" unit="days after the transaction" value={draft.disclosure_delay_threshold_days} disabled={!draft.enable_disclosure_delay_signal} onChange={(n) => set('disclosure_delay_threshold_days', n)} />
            </Stack>
            <Stack direction="row" spacing={2} sx={{ alignItems: 'flex-start' }}>
              <FormControlLabel control={<Switch checked={draft.enable_excess_return_signal} onChange={(e) => set('enable_excess_return_signal', e.target.checked)} />} label="Excess return" sx={{ width: 150 }} />
              <Threshold label="|Excess return| ≥" unit="percentage points vs SPY, 90 days" value={draft.excess_return_threshold_pct_points} disabled={!draft.enable_excess_return_signal} onChange={(n) => set('excess_return_threshold_pct_points', n)} />
            </Stack>
            <FormControl size="small" sx={{ width: 260 }}>
              <InputLabel id="min-secondary-label">Secondary signals required</InputLabel>
              <Select labelId="min-secondary-label" label="Secondary signals required" value={draft.minimum_secondary_signals} onChange={(e) => set('minimum_secondary_signals', Number(e.target.value))}>
                {[0, 1, 2, 3].map((n) => (
                  <MenuItem key={n} value={n} disabled={n > enabledCount}>
                    {n} of {enabledCount} enabled
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>
          {problem ? (
            <Alert severity="warning">{problem}</Alert>
          ) : (
            <Alert severity={kind === 'default' ? 'success' : 'info'} icon={false}>
              {KIND_LABEL[kind]}
            </Alert>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setDraft(DEFAULT_RULE)}>Restore defaults</Button>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" disabled={!!problem} onClick={() => onApply(draft)}>
          Apply
        </Button>
      </DialogActions>
    </Dialog>
  );
}
