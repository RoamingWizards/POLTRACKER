import type {} from '@mui/x-date-pickers/themeAugmentation';
import type {} from '@mui/x-charts/themeAugmentation';
import type {} from '@mui/x-data-grid/themeAugmentation';
import { lazy, Suspense } from 'react';
import { Outlet, Route, Routes } from 'react-router-dom';
import { alpha } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Alert from '@mui/material/Alert';
import LinearProgress from '@mui/material/LinearProgress';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import AppNavbar from './components/AppNavbar';
import Header from './components/Header';
import SideMenu from './components/SideMenu';
import AppTheme from './shared-theme/AppTheme';
import { chartsCustomizations, dataGridCustomizations, datePickersCustomizations } from './theme/customizations';

// Each page is its own chunk, loaded on first visit.
const Overview = lazy(() => import('./pages/Overview'));
const Trades = lazy(() => import('./pages/Trades'));
const Politicians = lazy(() => import('./pages/Politicians'));
const PoliticianDetail = lazy(() => import('./pages/PoliticianDetail'));
const SecurityDetail = lazy(() => import('./pages/SecurityDetail'));
const DataStatus = lazy(() => import('./pages/DataStatus'));

const xThemeComponents = {
  ...chartsCustomizations,
  ...dataGridCustomizations,
  ...datePickersCustomizations,
};

function Layout() {
  return (
    <Box sx={{ display: 'flex' }}>
      <SideMenu />
      <AppNavbar />
      <Box
        component="main"
        sx={(theme) => ({
          flexGrow: 1,
          minWidth: 0,
          minHeight: '100vh',
          backgroundColor: theme.vars
            ? `rgba(${theme.vars.palette.background.defaultChannel} / 1)`
            : alpha(theme.palette.background.default, 1),
          overflow: 'auto',
        })}
      >
        <Stack spacing={2} sx={{ alignItems: 'center', mx: 3, pb: 5, mt: { xs: 8, md: 0 } }}>
          <Header />
          <Suspense fallback={<LinearProgress sx={{ width: '100%', maxWidth: { md: '1700px' } }} aria-label="Loading page" />}>
            <Outlet />
          </Suspense>
        </Stack>
      </Box>
    </Box>
  );
}

export default function App() {
  return (
    <AppTheme themeComponents={xThemeComponents}>
      <CssBaseline enableColorScheme />
      <LocalizationProvider dateAdapter={AdapterDayjs}>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Overview />} />
            <Route path="trades" element={<Trades />} />
            <Route path="politicians" element={<Politicians />} />
            <Route path="politicians/:id" element={<PoliticianDetail />} />
            <Route path="securities/:ticker" element={<SecurityDetail />} />
            <Route path="status" element={<DataStatus />} />
            <Route path="*" element={<Alert severity="info">Page not found.</Alert>} />
          </Route>
        </Routes>
      </LocalizationProvider>
    </AppTheme>
  );
}
