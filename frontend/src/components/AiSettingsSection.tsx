import { useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import LinearProgress from '@mui/material/LinearProgress';
import MenuItem from '@mui/material/MenuItem';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { useAiBulkPreview, useAiBulkStatus, useAiMutations, useAiSettings, useStartAiBulk } from '../api/hooks';
import type { AiBulkPreview, AiTestResult } from '../api/types';

const msg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong.');

function BulkGeneration({ configured }: { configured: boolean }) {
  const [open, setOpen] = useState(false);
  const preview = useAiBulkPreview(open);
  const status = useAiBulkStatus();
  const start = useStartAiBulk();
  const s = status.data;
  const running = s?.state === 'running';
  const p: AiBulkPreview | undefined = preview.data;
  return (
    <Stack spacing={1} data-testid="ai-bulk">
      <Typography variant="subtitle2">Generate explanations for flagged trades</Typography>
      <Typography variant="body2" color="text.secondary">
        Explains only trades flagged by the default methodology, one request each. Trades that already have a valid explanation from the selected provider and model are skipped.
      </Typography>
      <Box>
        <Button variant="outlined" size="small" disabled={!configured || running} onClick={() => setOpen(true)}>
          Generate explanations for flagged trades…
        </Button>
      </Box>
      {s && s.state !== 'idle' && (
        <Stack spacing={0.5} role="status">
          {running && <LinearProgress variant={s.total ? 'determinate' : 'indeterminate'} value={s.total ? Math.min(100, (s.done / s.total) * 100) : 0} aria-label="Bulk generation progress" />}
          <Typography variant="body2" color={s.state === 'failed' ? 'error' : 'text.secondary'}>
            {running ? `Generating explanations… ${s.done} of ${s.total}` : s.state === 'failed' ? `Stopped: ${s.message ?? 'an error occurred'}.` : 'Finished.'}{' '}
            {s.generated} generated, {s.cached} already cached, {s.rejected} not accepted, {s.errors} errors.
          </Typography>
        </Stack>
      )}
      <Dialog open={open} onClose={() => setOpen(false)} aria-labelledby="ai-bulk-title" fullWidth maxWidth="xs">
        <DialogTitle id="ai-bulk-title">Generate explanations for flagged trades</DialogTitle>
        <DialogContent dividers>
          {preview.isLoading && <Typography>Counting…</Typography>}
          {preview.isError && <Alert severity="error">{msg(preview.error)}</Alert>}
          {p && (
            <Stack spacing={0.5}>
              <Typography>
                <strong>{p.to_generate}</strong> flagged {p.to_generate === 1 ? 'trade needs' : 'trades need'} an explanation ({p.already_cached} of {p.flagged_total} already cached).
              </Typography>
              <Typography>Provider: {p.provider_label}</Typography>
              <Typography>Model: {p.model}</Typography>
              <Typography>Estimated API calls: {p.estimated_api_calls}</Typography>
              <Typography variant="caption" color="text.secondary">
                Each call is billed by your provider to your account. Nothing is sent until you confirm.
              </Typography>
            </Stack>
          )}
          {start.isError && <Alert severity="error" sx={{ mt: 1 }}>{msg(start.error)}</Alert>}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={!p || p.to_generate === 0 || !p.configured || start.isPending}
            onClick={() => start.mutate(undefined, { onSuccess: () => setOpen(false) })}
          >
            Confirm and generate
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}

/** Choose a provider, keep its API key in the macOS Keychain, test it. The key is typed once; afterwards only a masked tail is ever shown. */
export default function AiSettingsSection() {
  const settings = useAiSettings();
  const m = useAiMutations();
  const [key, setKey] = useState('');
  const [model, setModel] = useState<string | null>(null);
  const [tests, setTests] = useState<Record<string, AiTestResult>>({});
  const [confirmRemove, setConfirmRemove] = useState(false);
  const forget = (id: string) => setTests((t) => Object.fromEntries(Object.entries(t).filter(([k]) => k !== id)));

  if (settings.isLoading) return <LinearProgress aria-label="Loading AI settings" />;
  const s = settings.data;
  if (!s) {
    return (
      <Alert severity="info">
        {settings.isError ? 'AI settings could not be loaded.' : 'AI provider settings are available in the POLTRACKER desktop app. Cached explanations remain visible here.'}
      </Alert>
    );
  }
  const current = s.providers.find((p) => p.id === s.provider)!;
  const test = tests[current.id];
  const connected = current.configured && test?.ok;
  const error = m.saveKey.error ?? m.removeKey.error ?? m.setProvider.error ?? m.test.error;
  const modelValue = model ?? current.model;

  return (
    <Paper variant="outlined" sx={{ p: 2 }} data-testid="ai-settings">
      <Stack spacing={2}>
        <Typography variant="h6" component="h2">
          AI Context
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {s.notice}
        </Typography>

        <TextField
          select
          size="small"
          label="Provider"
          value={s.provider}
          onChange={(e) => {
            setModel(null);
            setKey('');
            m.setProvider.mutate({ provider: e.target.value });
          }}
          sx={{ maxWidth: 320 }}
        >
          {s.providers.map((p) => (
            <MenuItem key={p.id} value={p.id}>
              {p.label}
            </MenuItem>
          ))}
        </TextField>

        <Box role="status" aria-label="Provider status">
          <Typography variant="body2">
            {connected ? '● Connected' : current.configured ? '● Key saved' : '○ Not configured'}
            {current.configured && current.masked ? ` — ${current.label} key configured: ${current.masked}` : ''}
          </Typography>
          {test && (
            <Typography variant="caption" color={test.ok ? 'success.main' : 'error'}>
              {test.message}
            </Typography>
          )}
          {s.storage_error && (
            <Typography variant="caption" color="error" component="div">
              {s.storage_error}
            </Typography>
          )}
        </Box>

        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ alignItems: { sm: 'flex-start' } }}>
          <TextField
            size="small"
            label="API key"
            type="password"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            autoComplete="off"
            placeholder={current.configured ? 'Enter a new key to replace the saved one' : 'Paste your API key'}
            slotProps={{ htmlInput: { spellCheck: false, autoCapitalize: 'off', 'data-1p-ignore': true } }}
            sx={{ flex: 1, maxWidth: 420 }}
          />
          <Button
            variant="contained"
            disabled={!key.trim() || m.saveKey.isPending}
            onClick={() => m.saveKey.mutate({ provider: current.id, api_key: key }, { onSuccess: () => { setKey(''); forget(current.id); } })}
          >
            {current.configured ? 'Replace key' : 'Save key'}
          </Button>
          <Button
            variant="outlined"
            disabled={!current.configured || m.test.isPending}
            onClick={() => m.test.mutate(current.id, { onSuccess: (r) => setTests((t) => ({ ...t, [current.id]: r })) })}
          >
            {m.test.isPending ? 'Testing…' : 'Test connection'}
          </Button>
          <Button color="error" variant="outlined" disabled={!current.configured || m.removeKey.isPending} onClick={() => setConfirmRemove(true)}>
            Remove key
          </Button>
        </Stack>

        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ alignItems: { sm: 'flex-start' } }}>
          <TextField
            size="small"
            label="Model"
            value={modelValue}
            onChange={(e) => setModel(e.target.value)}
            helperText={`Default: ${current.default_model}. Suggested: ${current.suggested_models.join(', ')}`}
            sx={{ flex: 1, maxWidth: 420 }}
          />
          <Button variant="outlined" disabled={model === null || model === current.model || m.setProvider.isPending} onClick={() => m.setProvider.mutate({ provider: current.id, model: modelValue.trim() === current.default_model ? null : modelValue }, { onSuccess: () => setModel(null) })}>
            Save model
          </Button>
        </Stack>

        {error && <Alert severity="error">{msg(error)}</Alert>}

        <Typography variant="caption" color="text.secondary">
          {s.key_notice}
        </Typography>

        <BulkGeneration configured={s.configured} />
      </Stack>

      <Dialog open={confirmRemove} onClose={() => setConfirmRemove(false)} aria-labelledby="ai-remove-title">
        <DialogTitle id="ai-remove-title">Remove the {current.label} key?</DialogTitle>
        <DialogContent>
          <Typography>It will be deleted from the macOS Keychain. Existing explanations stay available; new ones cannot be generated until you save a key again.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmRemove(false)}>Cancel</Button>
          <Button color="error" onClick={() => m.removeKey.mutate(current.id, { onSuccess: () => { setConfirmRemove(false); forget(current.id); } })}>
            Remove key
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}
