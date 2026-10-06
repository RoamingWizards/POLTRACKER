import { BarChart } from '@mui/x-charts/BarChart';
import { useTheme } from '@mui/material/styles';

export interface MonthlyPoint {
  month: string;
  buys: number;
  sells: number;
}

/** Stacked buys/sells per month (template: PageViewsBarChart). */
export default function MonthlyBarChart({ data }: { data: MonthlyPoint[] }) {
  const theme = useTheme();
  const palette = theme.vars ?? theme;
  return (
    <BarChart
      borderRadius={4}
      colors={[palette.palette.success.main, palette.palette.error.main]}
      xAxis={[
        {
          scaleType: 'band',
          categoryGapRatio: 0.4,
          data: data.map((d) => d.month),
          height: 24,
        },
      ]}
      yAxis={[{ width: 40 }]}
      series={[
        { id: 'buys', label: 'Buys', data: data.map((d) => d.buys), stack: 'A' },
        { id: 'sells', label: 'Sells', data: data.map((d) => d.sells), stack: 'A' },
      ]}
      height={250}
      margin={{ left: 0, right: 0, top: 20, bottom: 0 }}
      grid={{ horizontal: true }}
      hideLegend
    />
  );
}
