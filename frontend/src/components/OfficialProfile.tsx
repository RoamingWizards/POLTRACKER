import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Link from '@mui/material/Link';
import Stack from '@mui/material/Stack';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableRow from '@mui/material/TableRow';
import Typography from '@mui/material/Typography';
import type { CommitteeSeat, PoliticianDetail } from '../api/types';

const NA = <Typography component="span" variant="body2" sx={{ color: 'text.secondary' }}>Not available</Typography>;
const PARTY: Record<string, string> = { D: 'Democratic', R: 'Republican', I: 'Independent' };

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <TableRow>
      <TableCell sx={{ color: 'text.secondary', width: '40%' }}>{label}</TableCell>
      <TableCell align="right">{children}</TableCell>
    </TableRow>
  );
}

// Committees grouped as "committee -> its subcommittees"; a subcommittee seat can exist without a parent seat row.
export function groupCommittees(seats: CommitteeSeat[]) {
  const groups = new Map<string, { name: string; role: string | null; subs: { name: string; role: string }[] }>();
  for (const s of seats) {
    const g = groups.get(s.committee_code) ?? { name: s.committee_name, role: null, subs: [] };
    if (s.subcommittee_code) g.subs.push({ name: s.subcommittee_name ?? s.subcommittee_code, role: s.role });
    else g.role = s.role;
    groups.set(s.committee_code, g);
  }
  return [...groups.values()].sort((a, b) => a.name.localeCompare(b.name));
}

function termText(p: PoliticianDetail) {
  if (!p.term_start_year) return null;
  return `${p.term_start_year} – ${p.term_end_year ?? 'present'}`;
}

const METHOD: Record<string, string> = {
  override: 'Reviewed manually',
  llm: 'Suggested by an AI model and approved',
  'exact_name+chamber': 'Automatic: exact name match',
  'name_with_extra_middle+chamber': 'Automatic: name match (extra middle name)',
};
const methodText = (m: string | null) => (m ? (METHOD[m] ?? m) : 'Automatic: name match');

const unavailableReason = (p: PoliticianDetail) =>
  p.enrichment_status === 'review'
    ? 'A possible match has been found and is waiting for review.'
    : p.enrichment_status === 'ambiguous'
    ? 'More than one official has this name, so none was linked.'
    : p.enrichment_status === 'unmatched'
      ? 'This name could not be matched to an official record with confidence.'
      : p.enrichment_status === 'conflict'
        ? 'The official record is already linked to another entry.'
        : 'Official data has not been fetched yet.';

export default function OfficialProfile({ p }: { p: PoliticianDetail }) {
  const enriched = p.enrichment_status === 'matched' && !!p.bioguide_id;
  const groups = groupCommittees(p.committees);
  return (
    <Card variant="outlined" sx={{ mb: 2 }} aria-label="Official profile">
      <CardContent>
        <Typography component="h2" variant="subtitle2" gutterBottom>
          Official profile
        </Typography>
        {!enriched ? (
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            Not available. {unavailableReason(p)}
          </Typography>
        ) : (
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={3}>
            <Box sx={{ flex: 1 }}>
              <Table size="small">
                <TableBody>
                  <Row label="Party">{p.party ? (PARTY[p.party] ?? p.party) : NA}</Row>
                  <Row label="State">{p.state ?? NA}</Row>
                  <Row label="District">{p.chamber === 'senate' ? 'Statewide (Senate)' : (p.district ?? NA)}</Row>
                  <Row label="Chamber">{p.chamber === 'senate' ? 'Senate' : 'House'}</Row>
                  <Row label="Status">
                    {p.active === null ? NA : <Chip size="small" color={p.active ? 'success' : 'default'} label={p.active ? 'Currently in office' : 'Not currently in office'} />}
                  </Row>
                  <Row label="Serving in chamber">{termText(p) ?? NA}</Row>
                  <Row label="Bioguide ID">{p.bioguide_id}</Row>
                  <Row label="Identity match">{methodText(p.enrichment_method)}</Row>
                  <Row label="Official page">
                    {p.official_url ? (
                      <Link href={p.official_url} target="_blank" rel="noopener noreferrer">
                        Congress.gov
                      </Link>
                    ) : (
                      NA
                    )}
                  </Row>
                </TableBody>
              </Table>
              <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mt: 1 }}>
                Source: {p.enrichment_source ?? 'official roster'}
                {p.enriched_at ? `, updated ${p.enriched_at.slice(0, 10)}` : ''}.
              </Typography>
            </Box>
            <Box sx={{ flex: 1 }}>
              <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
                Committee and subcommittee assignments
              </Typography>
              {groups.length === 0 ? (
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  Not available{p.chamber === 'senate' ? ': Senate committee membership is not yet imported.' : '.'}
                </Typography>
              ) : (
                <Stack component="ul" spacing={1} sx={{ listStyle: 'none', p: 0, m: 0 }}>
                  {groups.map((g) => (
                    <li key={g.name}>
                      <Typography variant="body2">
                        {g.name}
                        {g.role && g.role !== 'Member' ? ` (${g.role})` : ''}
                      </Typography>
                      {g.subs.length > 0 && (
                        <Stack direction="row" useFlexGap sx={{ flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                          {g.subs.map((s) => (
                            <Chip key={s.name} size="small" variant="outlined" label={s.role !== 'Member' ? `${s.name} (${s.role})` : s.name} />
                          ))}
                        </Stack>
                      )}
                    </li>
                  ))}
                </Stack>
              )}
            </Box>
          </Stack>
        )}
      </CardContent>
    </Card>
  );
}
