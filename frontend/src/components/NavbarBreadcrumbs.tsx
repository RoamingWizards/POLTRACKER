import { Link as RouterLink, useLocation, useParams } from 'react-router-dom';
import { styled } from '@mui/material/styles';
import Link from '@mui/material/Link';
import Typography from '@mui/material/Typography';
import Breadcrumbs, { breadcrumbsClasses } from '@mui/material/Breadcrumbs';
import NavigateNextRoundedIcon from '@mui/icons-material/NavigateNextRounded';
import { usePolitician } from '../api/hooks';

const StyledBreadcrumbs = styled(Breadcrumbs)(({ theme }) => ({
  margin: theme.spacing(1, 0),
  [`& .${breadcrumbsClasses.separator}`]: {
    color: (theme.vars || theme).palette.action.disabled,
    margin: 1,
  },
  [`& .${breadcrumbsClasses.ol}`]: {
    alignItems: 'center',
  },
}));

function PoliticianName({ id }: { id: number }) {
  const { data } = usePolitician(id);
  return <>{data?.name ?? `#${id}`}</>;
}

export default function NavbarBreadcrumbs() {
  const { pathname } = useLocation();
  const params = useParams();
  const parts = pathname.split('/').filter(Boolean);
  const section = parts[0];

  const trail: { label: React.ReactNode; to?: string }[] = [{ label: 'POLTRACKER', to: '/' }];
  if (!section) trail.push({ label: 'Overview' });
  else if (section === 'trades') trail.push({ label: 'Trades' });
  else if (section === 'status') trail.push({ label: 'Data Status' });
  else if (section === 'politicians') {
    trail.push({ label: 'Politicians', to: parts[1] ? '/politicians' : undefined });
    const id = Number(parts[1]);
    if (parts[1] && Number.isFinite(id)) trail.push({ label: <PoliticianName id={id} /> });
  } else if (section === 'securities') {
    trail.push({ label: 'Security' });
    if (parts[1]) trail.push({ label: (params.ticker ?? parts[1]).toUpperCase() });
  }

  return (
    <StyledBreadcrumbs aria-label="breadcrumb" separator={<NavigateNextRoundedIcon fontSize="small" />}>
      {trail.map((crumb, i) =>
        i === trail.length - 1 ? (
          <Typography key={i} variant="body1" sx={{ color: 'text.primary', fontWeight: 600 }}>
            {crumb.label}
          </Typography>
        ) : crumb.to ? (
          <Link key={i} component={RouterLink} to={crumb.to} variant="body1" underline="hover" color="inherit">
            {crumb.label}
          </Link>
        ) : (
          <Typography key={i} variant="body1">
            {crumb.label}
          </Typography>
        ),
      )}
    </StyledBreadcrumbs>
  );
}
