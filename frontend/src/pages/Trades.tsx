import * as React from 'react';
import { useSearchParams } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import Stack from '@mui/material/Stack';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import TuneRoundedIcon from '@mui/icons-material/TuneRounded';
import ContextRuleDialog from '../components/ContextRuleDialog';
import FilterBar from '../components/FilterBar';
import ScreenSummary from '../components/ScreenSummary';
import TradesGrid from '../components/TradesGrid';
import ViewsControls from '../components/ViewsControls';
import { ApiError } from '../api/client';
import { resetActiveScreen, saveActiveScreen, usePresets, useSavedViews, useViewMutations, useActiveScreen } from '../api/hooks';
import type { ContextRule, FilterSpec, SavedView, ScreenPage } from '../api/types';
import { DEFAULT_RULE, LEGACY_PARAMS, detectPreset, filtersFromLegacyParams, rulesEqual, ruleKind } from '../lib/filters';

interface Screen {
  rule: ContextRule;
  filters: FilterSpec[];
  preset: string; // a built-in preset key or 'custom'
  viewId: number | null;
}

const DEFAULT_SCREEN: Screen = { rule: DEFAULT_RULE, filters: [], preset: 'balanced', viewId: null };

/** Trades with personalization: filters (AND), a preset or custom context rule, and local saved views. Nothing here rewrites stored context. */
export default function Trades() {
  const [params, setParams] = useSearchParams();
  const presetsQ = usePresets();
  const activeQ = useActiveScreen();
  const viewsQ = useSavedViews();
  const mutations = useViewMutations();
  const presets = presetsQ.data?.presets ?? [];
  const defaultRule = presetsQ.data?.default_rule ?? DEFAULT_RULE;

  const [screen, setScreen] = React.useState<Screen>(DEFAULT_SCREEN);
  const [hydrated, setHydrated] = React.useState(false);
  const [ruleOpen, setRuleOpen] = React.useState(false);
  const [page, setPage] = React.useState<ScreenPage | undefined>();
  const [nameError, setNameError] = React.useState<string | null>(null);
  const lastSaved = React.useRef<string>('');

  // Local persistence exists only where the app provides it (the desktop app); a read-only web API answers 404 and the page works in memory.
  const persistent = activeQ.isSuccess && activeQ.data !== null;
  const views: SavedView[] = viewsQ.data ?? [];

  // Hydrate once: older links (/trades?ticker=BA) win, otherwise the last-used screen, otherwise the default methodology.
  React.useEffect(() => {
    if (hydrated || presetsQ.isLoading || activeQ.isLoading) return;
    const legacy = filtersFromLegacyParams(params);
    const stored = activeQ.data && activeQ.data.saved ? activeQ.data : null;
    if (legacy.length) {
      setScreen({ ...DEFAULT_SCREEN, filters: legacy });
      setParams((prev) => {
        const next = new URLSearchParams(prev);
        LEGACY_PARAMS.forEach((k) => next.delete(k));
        return next;
      }, { replace: true });
    } else if (stored) {
      setScreen({ rule: stored.rule, filters: stored.filters, preset: stored.preset ?? detectPreset(stored.rule, presets), viewId: stored.view_id });
      lastSaved.current = JSON.stringify([stored.rule, stored.filters, stored.preset, stored.view_id]);
    }
    setHydrated(true);
  }, [hydrated, presetsQ.isLoading, activeQ.isLoading, activeQ.data, params, presets, setParams]);

  // Remember the last-used screen across restarts (debounced).
  React.useEffect(() => {
    if (!hydrated || !persistent) return;
    const body = { rule: screen.rule, filters: screen.filters, preset: screen.preset, view_id: screen.viewId };
    const key = JSON.stringify([body.rule, body.filters, body.preset, body.view_id]);
    if (key === lastSaved.current) return;
    const t = setTimeout(() => {
      lastSaved.current = key;
      saveActiveScreen(body).catch(() => undefined);
    }, 400);
    return () => clearTimeout(t);
  }, [screen, hydrated, persistent]);

  const kind = ruleKind(screen.rule);
  const preset = presets.find((p) => p.key === screen.preset) ?? null;
  const activeView = views.find((v) => v.id === screen.viewId) ?? null;
  const dirty = !!activeView && (!rulesEqual(activeView.rule, screen.rule) || JSON.stringify(activeView.filters) !== JSON.stringify(screen.filters));
  const isDefaultScreen = rulesEqual(screen.rule, defaultRule) && screen.filters.length === 0;

  const onPage = React.useCallback((p: ScreenPage | undefined) => setPage(p), []);
  const choosePreset = (key: string) => {
    if (key === 'custom') {
      setRuleOpen(true);
      return;
    }
    const p = presets.find((x) => x.key === key);
    if (p) setScreen((s) => ({ ...s, rule: p.rule, preset: key, viewId: null }));
  };
  const applyRule = (rule: ContextRule) => {
    setScreen((s) => ({ ...s, rule, preset: detectPreset(rule, presets), viewId: s.viewId }));
    setRuleOpen(false);
  };
  const messageOf = (e: unknown) => (e instanceof ApiError ? e.message : 'Could not save');

  return (
    <Box sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
      <Typography component="h2" variant="h6" sx={{ mb: 2 }}>
        Trades
      </Typography>
      <Stack direction="row" useFlexGap sx={{ flexWrap: 'wrap', gap: 1.5, mb: 1.5, alignItems: 'center' }}>
        <FormControl size="small" sx={{ minWidth: 190 }}>
          <InputLabel id="preset-label">Context rule</InputLabel>
          <Select labelId="preset-label" label="Context rule" value={presets.length ? screen.preset : ''} onChange={(e) => choosePreset(e.target.value)} disabled={!presets.length}>
            {presets.map((p) => (
              <MenuItem key={p.key} value={p.key}>
                {p.label}
              </MenuItem>
            ))}
            <MenuItem value="custom">Custom…</MenuItem>
          </Select>
        </FormControl>
        <Tooltip title={preset ? [preset.description, ...preset.notes].join(' ') : 'Your own thresholds and signals'}>
          <Button size="small" startIcon={<TuneRoundedIcon />} onClick={() => setRuleOpen(true)} aria-label="Rule settings">
            Rule settings
          </Button>
        </Tooltip>
        {persistent ? (
          <ViewsControls
            views={views}
            activeViewId={screen.viewId}
            dirty={dirty}
            error={nameError}
            onSave={async (name) => {
              setNameError(null);
              try {
                const v = await mutations.create.mutateAsync({ name, rule: screen.rule, filters: screen.filters, preset: screen.preset });
                setScreen((s) => ({ ...s, viewId: v.id }));
                return true;
              } catch (e) {
                setNameError(messageOf(e));
                return false;
              }
            }}
            onUpdate={() => activeView && mutations.update.mutate({ id: activeView.id, rule: screen.rule, filters: screen.filters, preset: screen.preset })}
            onLoad={(v) => {
              setNameError(null);
              setScreen({ rule: v.rule, filters: v.filters, preset: v.preset ?? detectPreset(v.rule, presets), viewId: v.id });
            }}
            onRename={async (v, name) => {
              setNameError(null);
              try {
                await mutations.update.mutateAsync({ id: v.id, name });
                return true;
              } catch (e) {
                setNameError(messageOf(e));
                return false;
              }
            }}
            onDelete={(v) => {
              mutations.remove.mutate(v.id);
              if (screen.viewId === v.id) setScreen((s) => ({ ...s, viewId: null }));
            }}
          />
        ) : (
          activeQ.isSuccess && (
            <Tooltip title="Saved views are stored by the desktop app on this device. This read-only web API does not store them.">
              <span>
                <Button size="small" disabled>
                  Views
                </Button>
              </span>
            </Tooltip>
          )
        )}
        <Button
          size="small"
          disabled={isDefaultScreen && screen.preset === 'balanced' && screen.viewId === null}
          onClick={() => {
            setScreen(DEFAULT_SCREEN);
            if (persistent) {
              lastSaved.current = '';
              resetActiveScreen().catch(() => undefined);
            }
          }}
        >
          Reset
        </Button>
      </Stack>
      <Box sx={{ mb: 1.5 }}>
        <FilterBar filters={screen.filters} onChange={(filters) => setScreen((s) => ({ ...s, filters }))} />
      </Box>
      <Box sx={{ mb: 1.5 }}>
        <ScreenSummary page={page} kind={kind} preset={preset} />
      </Box>
      {presetsQ.isError && <Alert severity="warning" sx={{ mb: 1 }}>Presets could not be loaded; the default methodology is shown.</Alert>}
      {hydrated && <TradesGrid filters={{}} screen={{ rule: screen.rule, filters: screen.filters, onPage }} />}
      <ContextRuleDialog open={ruleOpen} rule={screen.rule} onApply={applyRule} onClose={() => setRuleOpen(false)} />
    </Box>
  );
}
