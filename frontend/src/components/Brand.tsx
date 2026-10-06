import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import AccountBalanceRoundedIcon from '@mui/icons-material/AccountBalanceRounded';

/** The template's gradient logo chip, with the POLTRACKER mark. */
export function BrandIcon() {
  return (
    <Box
      sx={{
        width: '1.5rem',
        height: '1.5rem',
        borderRadius: '999px',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        alignSelf: 'center',
        backgroundImage: 'linear-gradient(135deg, hsl(210, 98%, 60%) 0%, hsl(210, 100%, 35%) 100%)',
        color: 'hsla(210, 100%, 95%, 0.9)',
        border: '1px solid',
        borderColor: 'hsl(210, 100%, 55%)',
        boxShadow: 'inset 0 2px 5px rgba(255, 255, 255, 0.3)',
      }}
    >
      <AccountBalanceRoundedIcon color="inherit" sx={{ fontSize: '1rem' }} />
    </Box>
  );
}

export default function Brand() {
  return (
    <Stack direction="row" spacing={1.25} sx={{ alignItems: 'center', px: 0.5, py: 0.5 }}>
      <BrandIcon />
      <Stack>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
          POLTRACKER
        </Typography>
        <Typography variant="caption" sx={{ color: 'text.secondary', lineHeight: 1.2 }}>
          Congressional trades
        </Typography>
      </Stack>
    </Stack>
  );
}
