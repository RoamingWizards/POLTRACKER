import Alert from '@mui/material/Alert';
import Typography from '@mui/material/Typography';
import type { Preset, RuleKind, ScreenPage } from '../api/types';
import { KIND_LABEL } from '../lib/filters';

/** Says plainly which result is which: the default POLTRACKER flag is the stored methodology; a custom screen is the user's own reading of the same stored facts. */
export default function ScreenSummary({ page, kind, preset }: { page: ScreenPage | undefined; kind: RuleKind; preset: Preset | null }) {
  const label = page?.kind_label ?? KIND_LABEL[kind];
  if (kind === 'default') {
    return (
      <Typography variant="body2" color="text.secondary" data-testid="screen-summary">
        {page ? `${page.total.toLocaleString()} trades · ${page.canonical_flag_count.toLocaleString()} flagged for contextual review (default methodology)` : 'Default methodology'}
      </Typography>
    );
  }
  return (
    <Alert severity="info" icon={false} sx={{ py: 0 }} data-testid="screen-summary">
      <Typography variant="body2">
        <strong>{preset && preset.key !== 'custom' ? `${preset.label}: ` : ''}{label}.</strong>{' '}
        {page ? (
          <>
            {page.total.toLocaleString()} trades · <span data-testid="custom-count">{page.custom_match_count.toLocaleString()} match this screen</span> ·{' '}
            <span data-testid="canonical-count">{page.canonical_flag_count.toLocaleString()} flagged by the default methodology</span>
          </>
        ) : null}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        A custom screen re-reads stored context under your settings. It is not the contextual-review flag, and neither says anything about intent or knowledge.
        {kind === 'market_only' ? ' This screen ignores committee relevance entirely, so it says nothing about political context.' : ''}
      </Typography>
    </Alert>
  );
}
