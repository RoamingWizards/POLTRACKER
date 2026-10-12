import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Link from '@mui/material/Link';
import Paper from '@mui/material/Paper';
import { Link as RouterLink } from 'react-router-dom';
import AiSettingsSection from '../components/AiSettingsSection';

export default function Settings() {
  return (
    <Box sx={{ width: '100%', maxWidth: { md: '1700px' } }}>
      <Typography component="h1" variant="h5" sx={{ mb: 2 }}>
        Settings
      </Typography>
      <Box id="ai" sx={{ maxWidth: 900 }}>
        <AiSettingsSection />
        <Paper variant="outlined" sx={{ p: 2, mt: 2 }} data-testid="privacy-entry">
          <Typography variant="h6" component="h2" sx={{ mb: 0.5 }}>
            Privacy
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            POLTRACKER keeps its data on this Mac, has no account and collects no telemetry. API keys stay in the macOS Keychain, and nothing is sent to an AI provider unless you ask.
          </Typography>
          <Link component={RouterLink} to="/privacy">
            Read the privacy policy
          </Link>
        </Paper>
      </Box>
    </Box>
  );
}
