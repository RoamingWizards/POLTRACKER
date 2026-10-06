import * as React from 'react';
import { PieChart } from '@mui/x-charts/PieChart';
import { useDrawingArea } from '@mui/x-charts/hooks';
import { styled } from '@mui/material/styles';
import Typography from '@mui/material/Typography';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import LinearProgress, { linearProgressClasses } from '@mui/material/LinearProgress';

export interface Slice {
  label: string;
  value: number;
  color: string;
}

const StyledText = styled('text', {
  shouldForwardProp: (prop) => prop !== 'variant',
})<{ variant: 'primary' | 'secondary' }>(({ theme }) => ({
  textAnchor: 'middle',
  dominantBaseline: 'central',
  fill: (theme.vars || theme).palette.text.secondary,
  variants: [
    { props: { variant: 'primary' }, style: { fontSize: theme.typography.h5.fontSize, fontWeight: theme.typography.h5.fontWeight } },
    { props: { variant: 'secondary' }, style: { fontSize: theme.typography.body2.fontSize, fontWeight: theme.typography.body2.fontWeight } },
  ],
}));

function PieCenterLabel({ primaryText, secondaryText }: { primaryText: string; secondaryText: string }) {
  const { width, height, left, top } = useDrawingArea();
  const primaryY = top + height / 2 - 10;
  return (
    <React.Fragment>
      <StyledText variant="primary" x={left + width / 2} y={primaryY}>
        {primaryText}
      </StyledText>
      <StyledText variant="secondary" x={left + width / 2} y={primaryY + 24}>
        {secondaryText}
      </StyledText>
    </React.Fragment>
  );
}

/** Donut plus percentage bars (template: ChartUserByCountry). */
export default function SplitDonutCard({
  title,
  slices,
  centerPrimary,
  centerSecondary,
}: {
  title: string;
  slices: Slice[];
  centerPrimary: string;
  centerSecondary: string;
}) {
  const total = slices.reduce((sum, s) => sum + s.value, 0);
  return (
    <Card variant="outlined" sx={{ display: 'flex', flexDirection: 'column', gap: '8px', flexGrow: 1 }}>
      <CardContent>
        <Typography component="h2" variant="subtitle2">
          {title}
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <PieChart
            colors={slices.map((s) => s.color)}
            margin={{ left: 40, right: 40, top: 40, bottom: 40 }}
            series={[
              {
                data: slices.map((s) => ({ label: s.label, value: s.value })),
                innerRadius: 62,
                outerRadius: 85,
                paddingAngle: 0,
                highlightScope: { fade: 'global', highlight: 'item' },
              },
            ]}
            height={220}
            width={220}
            hideLegend
          >
            <PieCenterLabel primaryText={centerPrimary} secondaryText={centerSecondary} />
          </PieChart>
        </Box>
        {slices.map((slice) => {
          const pct = total ? (slice.value / total) * 100 : 0;
          return (
            <Stack key={slice.label} direction="row" sx={{ alignItems: 'center', gap: 2, pb: 1.5 }}>
              <Stack sx={{ gap: 0.75, flexGrow: 1 }}>
                <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', gap: 2 }}>
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>
                    {slice.label}
                  </Typography>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                    {slice.value.toLocaleString()} ({pct.toFixed(0)}%)
                  </Typography>
                </Stack>
                <LinearProgress
                  variant="determinate"
                  aria-label={`${slice.label} share`}
                  value={pct}
                  sx={{ [`& .${linearProgressClasses.bar}`]: { backgroundColor: slice.color } }}
                />
              </Stack>
            </Stack>
          );
        })}
      </CardContent>
    </Card>
  );
}
