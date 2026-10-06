import { BarChart } from '@mui/x-charts/BarChart';
import { useTheme } from '@mui/material/styles';

export interface TickerPoint {
  ticker: string;
  buys: number;
  sells: number;
}

export default function TopTickersChart({ data }: { data: TickerPoint[] }) {
  const theme = useTheme();
  const palette = theme.vars ?? theme;
  return (
    <BarChart
      layout="horizontal"
      borderRadius={4}
      colors={[palette.palette.success.main, palette.palette.error.main]}
      yAxis={[{ scaleType: 'band', data: data.map((d) => d.ticker), width: 56, categoryGapRatio: 0.3 }]}
      xAxis={[{ height: 24 }]}
      series={[
        { id: 'buys', label: 'Buys', data: data.map((d) => d.buys), stack: 'A' },
        { id: 'sells', label: 'Sells', data: data.map((d) => d.sells), stack: 'A' },
      ]}
      height={250}
      margin={{ left: 0, right: 8, top: 10, bottom: 0 }}
      grid={{ vertical: true }}
      hideLegend
    />
  );
}
