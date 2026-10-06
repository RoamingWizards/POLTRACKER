import * as React from 'react';
import { useNavigate } from 'react-router-dom';
import FormControl from '@mui/material/FormControl';
import InputAdornment from '@mui/material/InputAdornment';
import OutlinedInput from '@mui/material/OutlinedInput';
import SearchRoundedIcon from '@mui/icons-material/SearchRounded';
import { apiGet } from '../api/client';

/** Jump to a ticker if it exists, otherwise search politicians by name. */
export default function Search() {
  const navigate = useNavigate();
  const [value, setValue] = React.useState('');

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const term = value.trim();
    if (!term) return;
    if (/^[A-Za-z0-9.-]{1,10}$/.test(term)) {
      try {
        await apiGet(`/securities/${term.toUpperCase()}`);
        navigate(`/securities/${term.toUpperCase()}`);
        setValue('');
        return;
      } catch {
        /* not a known ticker: fall through to politician search */
      }
    }
    navigate(`/politicians?q=${encodeURIComponent(term)}`);
    setValue('');
  };

  return (
    <form onSubmit={submit}>
      <FormControl sx={{ width: { xs: '100%', md: '28ch' } }} variant="outlined">
        <OutlinedInput
          size="small"
          id="search"
          placeholder="Ticker or politician…"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          sx={{ flexGrow: 1 }}
          startAdornment={
            <InputAdornment position="start" sx={{ color: 'text.primary' }}>
              <SearchRoundedIcon fontSize="small" />
            </InputAdornment>
          }
          inputProps={{ 'aria-label': 'search ticker or politician' }}
        />
      </FormControl>
    </form>
  );
}
