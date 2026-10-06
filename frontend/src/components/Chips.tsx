import Chip from '@mui/material/Chip';
import { isSell, typeLabel } from '../lib/format';

export function TypeChip({ type }: { type: string }) {
  const color = type === 'buy' ? 'success' : isSell(type) ? 'error' : 'default';
  return <Chip size="small" variant="outlined" color={color} label={typeLabel(type)} />;
}

export function ChamberChip({ chamber }: { chamber: string }) {
  return <Chip size="small" variant="outlined" label={chamber === 'senate' ? 'Senate' : 'House'} />;
}
