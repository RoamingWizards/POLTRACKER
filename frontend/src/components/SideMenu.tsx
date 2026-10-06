import { styled } from '@mui/material/styles';
import MuiDrawer, { drawerClasses } from '@mui/material/Drawer';
import Box from '@mui/material/Box';
import Divider from '@mui/material/Divider';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Brand from './Brand';
import MenuContent from './MenuContent';
import { useStatus } from '../api/hooks';
import { timeAgo } from '../lib/format';

const drawerWidth = 240;

const Drawer = styled(MuiDrawer)({
  width: drawerWidth,
  flexShrink: 0,
  boxSizing: 'border-box',
  mt: 10,
  [`& .${drawerClasses.paper}`]: {
    width: drawerWidth,
    boxSizing: 'border-box',
  },
});

export function DataFreshness() {
  const { data } = useStatus();
  return (
    <Stack sx={{ p: 2, gap: 0.25, borderTop: '1px solid', borderColor: 'divider' }}>
      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
        Last ingest: {timeAgo(data?.last_ingested_at)}
      </Typography>
      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
        Latest disclosure: {data?.latest_disclosure_date ?? '—'}
      </Typography>
    </Stack>
  );
}

export default function SideMenu() {
  return (
    <Drawer
      variant="permanent"
      sx={{
        display: { xs: 'none', md: 'block' },
        [`& .${drawerClasses.paper}`]: {
          backgroundColor: 'background.paper',
        },
      }}
    >
      <Box sx={{ display: 'flex', mt: 'calc(var(--template-frame-height, 0px) + 4px)', p: 1.5 }}>
        <Brand />
      </Box>
      <Divider />
      <Box sx={{ overflow: 'auto', height: '100%', display: 'flex', flexDirection: 'column' }}>
        <MenuContent />
      </Box>
      <DataFreshness />
    </Drawer>
  );
}
