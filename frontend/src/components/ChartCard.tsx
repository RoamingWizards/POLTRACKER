import * as React from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Skeleton from '@mui/material/Skeleton';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

interface ChartCardProps {
  title: string;
  headline?: string;
  chip?: { label: string; color: 'success' | 'error' | 'default' | 'warning' };
  caption?: string;
  action?: React.ReactNode;
  loading?: boolean;
  children?: React.ReactNode;
}

/** The template's chart card header (title / big number / chip / caption) as a wrapper. */
export default function ChartCard({ title, headline, chip, caption, action, loading, children }: ChartCardProps) {
  return (
    <Card variant="outlined" sx={{ width: '100%', height: '100%' }}>
      <CardContent>
        <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Typography component="h2" variant="subtitle2" gutterBottom>
            {title}
          </Typography>
          {action}
        </Stack>
        <Stack sx={{ justifyContent: 'space-between' }}>
          {headline && (
            <Stack direction="row" sx={{ alignItems: 'center', gap: 1 }}>
              <Typography variant="h4" component="p">
                {headline}
              </Typography>
              {chip && <Chip size="small" color={chip.color} label={chip.label} />}
            </Stack>
          )}
          {caption && (
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              {caption}
            </Typography>
          )}
        </Stack>
        {loading ? <Skeleton variant="rounded" height={250} sx={{ mt: 1 }} /> : children}
      </CardContent>
    </Card>
  );
}
