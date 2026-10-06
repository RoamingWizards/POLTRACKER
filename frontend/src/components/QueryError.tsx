import Alert from '@mui/material/Alert';
import { ApiError } from '../api/client';

export default function QueryError({ error, what }: { error: unknown; what: string }) {
  const message =
    error instanceof ApiError
      ? `${error.status}: ${error.message}`
      : error instanceof Error
        ? error.message
        : 'Unknown error';
  return (
    <Alert severity="error" sx={{ mb: 2 }}>
      Couldn’t load {what}. {message}. Is the POLTRACKER API running?
    </Alert>
  );
}
