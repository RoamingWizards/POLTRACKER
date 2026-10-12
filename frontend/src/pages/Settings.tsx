import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import AiSettingsSection from '../components/AiSettingsSection';

export default function Settings() {
  return (
    <Box sx={{ width: '100%', maxWidth: { md: '1700px' } }}>
      <Typography component="h1" variant="h5" sx={{ mb: 2 }}>
        Settings
      </Typography>
      <Box id="ai" sx={{ maxWidth: 900 }}>
        <AiSettingsSection />
      </Box>
    </Box>
  );
}
