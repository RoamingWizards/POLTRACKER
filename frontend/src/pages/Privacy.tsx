import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import policy from '../../../PRIVACY.md?raw';
import { inline, parseBlocks } from '../lib/markdown';

/** The repository's PRIVACY.md, shown as it is written: the file is the single source, so the app and the repository cannot disagree. */
export default function Privacy() {
  const blocks = parseBlocks(policy);
  return (
    <Box sx={{ width: '100%', maxWidth: { md: '1700px' } }}>
      <Paper variant="outlined" sx={{ p: { xs: 2, sm: 3 }, maxWidth: 820 }} data-testid="privacy-policy">
        {blocks.map((b, i) =>
          b.type === 'h1' ? (
            <Typography key={i} component="h1" variant="h5" sx={{ mb: 1 }}>
              {b.text}
            </Typography>
          ) : b.type === 'h2' ? (
            <Typography key={i} component="h2" variant="h6" sx={{ mt: 3, mb: 1 }}>
              {b.text}
            </Typography>
          ) : b.type === 'ul' ? (
            <Box key={i} component="ul" sx={{ m: 0, mb: 1, pl: 3 }}>
              {b.items.map((it, j) => (
                <Typography key={j} component="li" variant="body2" sx={{ mb: 0.5, '& code': { fontSize: '0.85em', wordBreak: 'break-all' } }}>
                  {inline(it)}
                </Typography>
              ))}
            </Box>
          ) : (
            <Typography key={i} variant="body2" sx={{ mb: 1, '& code': { fontSize: '0.85em', wordBreak: 'break-all' } }}>
              {inline(b.text)}
            </Typography>
          ),
        )}
      </Paper>
    </Box>
  );
}
