import { NavLink, useLocation } from 'react-router-dom';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Stack from '@mui/material/Stack';
import HomeRoundedIcon from '@mui/icons-material/HomeRounded';
import SwapHorizRoundedIcon from '@mui/icons-material/SwapHorizRounded';
import PeopleRoundedIcon from '@mui/icons-material/PeopleRounded';
import StorageRoundedIcon from '@mui/icons-material/StorageRounded';

const mainListItems = [
  { text: 'Overview', icon: <HomeRoundedIcon />, to: '/', match: (p: string) => p === '/' },
  { text: 'Trades', icon: <SwapHorizRoundedIcon />, to: '/trades', match: (p: string) => p.startsWith('/trades') },
  {
    text: 'Politicians',
    icon: <PeopleRoundedIcon />,
    to: '/politicians',
    match: (p: string) => p.startsWith('/politicians'),
  },
];

const secondaryListItems = [
  { text: 'Data Status', icon: <StorageRoundedIcon />, to: '/status', match: (p: string) => p.startsWith('/status') },
];

type Item = (typeof mainListItems)[number];

export default function MenuContent({ onNavigate }: { onNavigate?: () => void }) {
  const { pathname } = useLocation();
  const renderList = (items: Item[]) => (
    <List dense>
      {items.map((item) => (
        <ListItem key={item.to} disablePadding sx={{ display: 'block' }}>
          <ListItemButton component={NavLink} to={item.to} selected={item.match(pathname)} onClick={onNavigate}>
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.text} />
          </ListItemButton>
        </ListItem>
      ))}
    </List>
  );

  return (
    <Stack sx={{ flexGrow: 1, p: 1, justifyContent: 'space-between' }}>
      {renderList(mainListItems)}
      {renderList(secondaryListItems)}
    </Stack>
  );
}
