import Divider from '@mui/material/Divider';
import Drawer, { drawerClasses } from '@mui/material/Drawer';
import Stack from '@mui/material/Stack';
import Brand from './Brand';
import MenuContent from './MenuContent';
import { DataFreshness } from './SideMenu';

interface SideMenuMobileProps {
  open: boolean | undefined;
  toggleDrawer: (newOpen: boolean) => () => void;
}

export default function SideMenuMobile({ open, toggleDrawer }: SideMenuMobileProps) {
  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={toggleDrawer(false)}
      sx={{
        zIndex: (theme) => theme.zIndex.drawer + 1,
        [`& .${drawerClasses.paper}`]: {
          backgroundImage: 'none',
          backgroundColor: 'background.paper',
        },
      }}
    >
      <Stack sx={{ maxWidth: '70dvw', minWidth: 220, height: '100%' }}>
        <Stack direction="row" sx={{ p: 2, pb: 1.5 }}>
          <Brand />
        </Stack>
        <Divider />
        <Stack sx={{ flexGrow: 1 }}>
          <MenuContent onNavigate={toggleDrawer(false)} />
        </Stack>
        <DataFreshness />
      </Stack>
    </Drawer>
  );
}
