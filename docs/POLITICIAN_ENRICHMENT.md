# Official politician enrichment

Adds stable identifiers and public office metadata to the politicians POLTRACKER already knows from trade disclosures.
Facts only: party, state, district, term, Bioguide ID, official profile link and committee seats. No scoring, no
inference about trades.

## Sources

| Data | Source | Key |
| --- | --- | --- |
| Member roster (Bioguide ID, party, state, district, term, active) | Congress.gov API v3 `/member/congress/{n}` (`CongressGovProvider`) | `CONGRESS_API_KEY` (free: https://api.congress.gov/sign-up/) |
| House roster + House committees and subcommittees | Clerk of the House `MemberData.xml` (`HouseClerkProvider`) | none |
| Senate committees | **not available yet** | see limitations |

Providers sit behind `PoliticianProvider` / `CommitteeProvider` (`providers/politicians.py`); only the provider modules
know source field names. The key is sent as an `X-Api-Key` header, never in a URL, and is never logged.

## Running it

```
.venv/bin/alembic upgrade head                                   # migration 0006 (back up poltracker.db first)
.venv/bin/python -m poltracker.enrich_politicians --dry-run      # report matches, write nothing
.venv/bin/python -m poltracker.enrich_politicians                # Congress.gov roster + House Clerk committees
.venv/bin/python -m poltracker.enrich_politicians --source house-clerk   # no key: House members only
```

Options: `--limit N`, `--ids 1 2 3`, `--force`, `--no-committees`. Without a key it prints `not_configured`
(exit 2) and changes nothing; the app and existing data are unaffected. Set `CONGRESS_API_KEY` in `.env` (never commit
it); the macOS app reads it from the environment only if you launch it with one.

Incremental: a matched politician is refreshed after `POLITICIAN_ENRICH_STALE_DAYS` (30); an unresolved one is retried
after `POLITICIAN_RETRY_DAYS` (7). If nothing is due, no request is made. Requests are paced
(`POLITICIAN_REQUEST_INTERVAL`, 0.5 s), retried with exponential backoff, and honour `Retry-After`.
A full run needs about **3 Congress.gov requests** (the whole roster, 250 per page) plus **1 House Clerk download**,
regardless of how many politicians are enriched.

## Matching (politician_match.py)

A politician is matched only when all of these hold, and the result is unique:

1. same chamber;
2. same normalized name: accents/case/punctuation folded, honorifics and suffixes dropped, single-letter middle
   initials ignored, a full middle name must agree if both sides have one;
3. same state, when POLTRACKER knows it (it usually does not yet).

Fallback (`name_with_extra_middle`): same first and last name where POLTRACKER has a middle name the official record omits
or abbreviates ("Kelly Louise Morrison" is "Kelly Morrison"). Still chamber-scoped and must be unique.

Never matched: nicknames ("Dan" vs "Daniel"), different spellings, shared surnames. Several candidates is
`ambiguous`; no candidate is `unmatched`; an official already linked to another record, or a record already linked to a
different official, is `conflict` (records are never merged). Each unresolved politician stores the reason and, where
helpful, same-surname candidates for a human to review in `politicians.enrichment_note`. Existing `trades`
and politician ids are never changed.

## Data model (migration 0006, additive)

`politicians`: `bioguide_id` (unique), `district`, `official_url`, `active`, `term_start_year`, `term_end_year`,
`enriched_at`, `enrichment_source`, `enrichment_status`, `enrichment_note`, `enrichment_checked_at`
(existing `party`, `state` are filled from the official record). Term years are integers because the sources give no day.
New table `committee_assignments` (committee/subcommittee name and code, role, chamber, dates, source, source URL).

## Limitations

- Senate committee membership is published at senate.gov, which returns HTTP 403 to automated clients, and
  Congress.gov has no member-to-committee endpoint. Senators therefore show "Not available" for committees.
- The House Clerk gives role only where it names one (Chair, Vice Chair, ...) and gives no start/end dates; none are invented.
- `active` from Congress.gov means the most recent term has no end year; the House Clerk lists sitting members only.
- The Congress.gov provider is tested against fixtures written from the documented response shape; it has not been run
  against the live API (no key was available when it was written).
- The Congress.gov profile URL is built from the Bioguide ID (`/member/<first-last>/<ID>`); the slug is cosmetic.
