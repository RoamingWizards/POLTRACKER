import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Divider from '@mui/material/Divider';
import Link from '@mui/material/Link';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import type { ContextEvidence, Trade, TradeContext } from '../api/types';
import { formatPct } from '../lib/format';

const UNKNOWN_REASON: Record<string, string> = {
  no_sic: 'the security has no SIC code',
  no_committee_assignments: 'no committee assignments are available for this member',
  unmapped_committees: 'a committee has no industry mapping',
};

function ordinal(n: number): string {
  const v = Math.round(n);
  const s = ['th', 'st', 'nd', 'rd'];
  const r = v % 100;
  return `${v}${s[(r - 20) % 10] ?? s[r] ?? s[0]}`;
}

const where = (e: ContextEvidence) => {
  const m = e.metadata ?? {};
  const name = [m.committee_name, m.subcommittee_name].filter(Boolean).join(' / ') || e.committee_code;
  return `${name} / ${m.security_industry ?? 'industry'} (SIC ${m.sic_range ?? '—'})`;
};

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '170px 1fr' }, gap: 0.5, py: 1 }}>
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      <Box>{children}</Box>
    </Box>
  );
}

/** Context signals for one trade. Neutral wording only: these are public-data indicators, not findings. */
export default function TradeContextDialog({ trade, onClose }: { trade: Trade | null; onClose: () => void }) {
  const c: TradeContext | null | undefined = trade?.context;
  const direct = c?.evidence.filter((e) => e.evidence_type === 'reviewed_direct_mapping') ?? [];
  const related = c?.evidence.filter((e) => e.evidence_type === 'reviewed_related_mapping') ?? [];
  return (
    <Dialog open={!!trade} onClose={onClose} fullWidth maxWidth="sm" aria-labelledby="trade-context-title">
      <DialogTitle id="trade-context-title">
        Context signals
        {trade && (
          <Typography variant="body2" color="text.secondary" component="div">
            {trade.politician_name} · {trade.ticker ?? '—'} · {trade.transaction_type} · traded {trade.transaction_date}
          </Typography>
        )}
      </DialogTitle>
      <DialogContent dividers>
        {!c ? (
          <Typography color="text.secondary">Context has not been calculated for this trade yet (run python -m poltracker.analyze_trade_context).</Typography>
        ) : (
          <>
            <Row label="Committee relevance">
              {c.committee_relevance === true ? (
                <Stack spacing={0.5}>
                  {direct.map((e, i) => (
                    <Typography key={i} variant="body2">
                      ✓ {where(e)}
                      {e.source_url && (
                        <>
                          {' '}
                          <Link href={e.source_url} target="_blank" rel="noreferrer noopener">
                            source
                          </Link>
                        </>
                      )}
                    </Typography>
                  ))}
                </Stack>
              ) : c.committee_relevance === false ? (
                <Typography variant="body2">No reviewed direct mapping applies</Typography>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Unknown: {UNKNOWN_REASON[c.committee_relevance_reason ?? ''] ?? 'insufficient data'}
                </Typography>
              )}
            </Row>
            <Row label="Trade size">
              {c.trade_size_percentile != null ? (
                <Typography variant="body2">
                  {ordinal(c.trade_size_percentile)} percentile for this politician ({c.trade_size_sample_size} earlier trades)
                  {c.trade_size_anomaly ? ' · unusual size' : ''}
                </Typography>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Unknown: not enough earlier trades with a disclosed range{c.trade_size_sample_size != null ? ` (${c.trade_size_sample_size})` : ''}
                </Typography>
              )}
            </Row>
            <Row label="Disclosure delay">
              {c.disclosure_delay_days != null ? (
                <Typography variant="body2">
                  {c.disclosure_delay_days} days{c.disclosure_delay_signal ? ' · long delay' : ''}
                </Typography>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Unknown: dates missing or inconsistent
                </Typography>
              )}
            </Row>
            <Row label="Excess return">
              {c.excess_return != null ? (
                <Typography variant="body2">
                  {formatPct(c.excess_return)} vs benchmark over {c.excess_horizon_days} days
                  {c.excess_return_signal ? ' · large excess return' : ''}
                  {c.excess_return_direction_adjusted != null && c.excess_return_direction_adjusted !== c.excess_return && (
                    <Typography component="span" variant="body2" color="text.secondary">
                      {' '}
                      (direction-adjusted {formatPct(c.excess_return_direction_adjusted)})
                    </Typography>
                  )}
                </Typography>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Unknown: no prices for the full {c.excess_horizon_days ?? 90}-day window
                </Typography>
              )}
            </Row>
            <Divider sx={{ my: 1 }} />
            <Row label="Status">
              {c.flagged_for_contextual_review ? (
                <Chip size="small" color="warning" variant="outlined" label="Flagged for contextual review" />
              ) : (
                <Typography variant="body2">Not flagged</Typography>
              )}
            </Row>
            {related.length > 0 && (
              <Row label="Supporting context">
                <Stack spacing={0.5}>
                  {related.map((e, i) => (
                    <Typography key={i} variant="body2" color="text.secondary">
                      Related (does not create a signal): {where(e)}
                    </Typography>
                  ))}
                </Stack>
              </Row>
            )}
          </>
        )}
        <Typography variant="caption" color="text.secondary" component="p" sx={{ mt: 2 }}>
          {c?.notice ?? 'Context indicators are derived from public data and do not establish that a member possessed or acted on material non-public information.'}
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
