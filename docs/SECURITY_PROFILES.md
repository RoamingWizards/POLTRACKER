# Security profiles (company, industry, sector)

Phase 1 of committee/sector context: enrich each traded security with official company metadata, so later phases can relate a trade's
industry to a politician's committees. **This phase only stores metadata.** It does no committee/industry mapping, scoring or flagging,
makes no relevance judgement, uses no language model, and never changes trades, security ids, tickers, or the trade-derived `name`.

## Source

SEC EDGAR, the official US registrant database:

1. Ticker to CIK: the SEC's `company_tickers_exchange.json`, then the older official `ticker.txt` as a fallback (it lists some tickers the
   JSON omits). **Exact ticker match only.** The one deterministic variant is the class-share spelling (`BRK.B` and `BRK-B`). A ticker listed
   under more than one CIK is never resolved. There is no name matching.
2. CIK to classification: the company's EDGAR submissions record (`data.sec.gov/submissions/CIK##########.json`): official name, SIC code,
   SIC description and exchange.

## Fields added to `securities` (migration 0009, nullable, additive)

`company_name`, `cik`, `sic_code`, `industry` (the SIC description exactly as published, for example *Aircraft*), `sector` (the official SIC
division derived from the SIC code, for example *Manufacturing*), `exchange`, `profile_source`, `profile_source_url` (the EDGAR company page),
`profile_status` (`ok`, `partial` = CIK but no SIC published, `unresolved`), `profile_note`, `profile_checked_at`, `profile_updated_at`.
They are also returned (nullable) by `GET /securities/{ticker}`, and the security page shows a small industry chip when one exists.

`industry`/`sic_code` are the useful keys for later mapping. `sector` (the SIC division) is coarse: *Manufacturing* covers aerospace,
pharmaceuticals and computers alike.

## Usage

```bash
export SEC_USER_AGENT="Your Name your@email.com"     # required by the SEC's fair-access policy; the generic default is refused (HTTP 403)
.venv/bin/alembic upgrade head                       # migration 0009 (back up poltracker.db first)
python -m poltracker.enrich_securities --dry-run --limit 20
python -m poltracker.enrich_securities               # incremental
python -m poltracker.enrich_securities --force --ticker LMT RTX
```

Incremental and idempotent: a verified profile is re-checked after `SECURITY_PROFILE_STALE_DAYS` (90), an unresolved ticker after
`SECURITY_PROFILE_RETRY_DAYS` (30); everything else costs no request. An error on one security leaves it unchecked so the next run retries it.
A verified profile is never wiped if the SEC later stops listing the ticker. Missing metadata is just null everywhere in the app. Nothing
runs automatically and the Mac app never calls the SEC; it works offline exactly as before.

## Cost and fair access

One request per list (two) plus one per resolved security. The SEC allows 10 requests per second; the default pacing is one every 0.15 s.
A first run over the current 1,061 securities took about 4 minutes and about 945 requests. The SEC answered a generic User-Agent with HTTP
403, so `SEC_USER_AGENT` must carry real contact details (not a secret, but do not commit your own).

## Measured result (scratch copy of the real database, 2026-10-07)

921 enriched (CIK + SIC + industry + sector), 20 partial (CIK, no SIC), 120 unresolved: 941 of 1,061 securities (88.7%) have an official
identifier, covering 5,081 of 5,381 trades (94.4%) by industry. The unresolved are mostly securities the SEC does not register as companies:
ETFs and index funds (49), foreign ordinary shares and ADRs (52), mutual funds (4), other funds (2), plus 13 renamed, acquired or malformed
tickers (for example FB, FI, HCN, BRCM, COLPAL). They stay unresolved rather than being guessed.

## Limitations

- The SEC does not classify ETFs, funds, many foreign ADRs or retired tickers, so those have no industry.
- SIC is an older, coarse scheme (for example *Services-Prepackaged Software*), not GICS. Some firms have a SIC that no longer reflects
  their business, and a few registrants have none (`partial`).
- A renamed ticker (FB to META) is not followed; the old ticker stays unresolved.
- `ticker.txt` can still list a company that has since delisted; its CIK and SIC are real, but the security may no longer trade.
