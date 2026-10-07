# Legislative data (Congress.gov)

A bounded, normalized local copy of official legislative records, for use by later analysis phases. **This phase only stores data.**
It does not score, flag, rank or contextualize any trade, does not match companies or sectors, uses no AI, and has no UI. It never
reads or changes trades, securities, prices, politicians or committee assignments.

## What is stored (migration 0009, seven additive tables)

| Table | Contents |
| --- | --- |
| `legislation` | One row per bill/resolution, identified by the official `(congress, bill_type, bill_number)`: title, origin chamber, latest official CRS summary (markup removed, not rephrased) and its date, introduced date, latest action date/text, policy area, official sponsor Bioguide ID and name, cosponsor count, the public `congress.gov` URL, and Congress.gov's own `updateDate` |
| `legislation_subjects` | Legislative subject terms |
| `legislation_committees` | Committees the bill was referred to, by Congress.gov system code (for example `hsed00`) |
| `politician_legislation` | `sponsor` / `cosponsor` links to **existing** POLTRACKER politicians, matched by Bioguide ID only; cosponsorship date, original-cosponsor flag, withdrawal date |
| `bill_actions` | Official actions **inside the ingestion window** (date, text, action code, type) |
| `hearings` | Hearing records: `(congress, chamber, jacket_number)`, title, citation, date(s), official API URL |
| `hearing_committees` | Committees of a hearing, when Congress.gov provides them |

Committee reports are not stored (the bill detail only lists references; a clean, useful ingest was not straightforward).

## Source and key

The official Congress.gov API v3, through the existing `CongressGovProvider` (same client, pacing, retry and `Retry-After`
handling as the member roster). It needs `CONGRESS_API_KEY` (free: https://api.congress.gov/sign-up/), sent as a header, never logged.
Without a key the command reports `not_configured` and the app is unaffected. Nothing runs automatically, and the Mac app never ingests
legislation at launch; the new tables simply exist (empty) after the app applies migration 0009.

Endpoints used: `/bill/{congress}`, `/bill/{congress}/{type}/{number}` and its `/actions`, `/subjects`, `/summaries`, `/cosponsors`,
`/committees`; `/hearing/{congress}` and `/hearing/{congress}/{chamber}/{jacket}`.

## Usage

```bash
.venv/bin/alembic upgrade head                               # migration 0009 (back up poltracker.db first)
python -m poltracker.ingest_legislation --dry-run --limit 20  # read from Congress.gov, report what would change, write nothing
python -m poltracker.ingest_legislation --from-date 2026-07-08 --limit 200
python -m poltracker.ingest_legislation                       # default window (below)
```

Options: `--from-date`, `--to-date`, `--dry-run`, `--force` (re-read even if unchanged), `--limit N` (consider at most N bills and N
hearings), `--no-hearings`. It prints a summary (bills listed / fetched / inserted / updated, subjects, committees, actions, links,
hearings, requests, errors). Exit codes: 0 ok, 1 provider error, 2 not configured, 3 rate-limited (progress is kept; re-run to continue).

## The window

- A bill is stored only if it has at least one **official action dated inside `[from, to]`**. Only the actions inside the window are
  stored. A hearing is stored only if one of its dates is inside the window.
- Default window: from the later of *(earliest valid trade date minus `LEGISLATION_BUFFER_DAYS`, default 30)* and *the start of the
  current Congress* (2025-01-03 for the 119th), to today. With no trades: the last 365 days. For the current data this gives
  2025-01-03 to today and covers 96.1% of trades by transaction date (the rest were made in the 118th Congress; use `--from-date` to
  reach them). The invalid future-dated trade is ignored.
- Cheap pruning: a bill whose latest action predates the window cannot have an action inside it, so it costs no request; for the rest
  the actions are read first (one request), and a bill with no in-window action stops there.
- Incremental: a bill whose Congress.gov `updateDate` is unchanged (and is not today's, since a record can change twice in one day) is
  skipped without any further request. Each bill is its own transaction, so an interrupted run keeps what it finished.
- Idempotent: every child row has a unique key; re-runs never duplicate anything. Children are synced to the latest official data
  (subjects, committees and links that disappear upstream are removed; actions are only added).

## Size of a backfill (measured 2026-10-07)

The 119th Congress has about 19,600 bills and 1,024 hearings. A bill in scope costs about 4.5 requests (actions, detail, and subjects,
summaries, cosponsors, committees when present). Congress.gov allows 5,000 requests per hour per key; the default 0.5 s pacing is
about 7,200 per hour, so the hourly limit is what binds.

| Window start | Candidate bills (sampled) | Approx. requests | Approx. time at 5,000/hour |
| --- | --- | --- | --- |
| 2025-01-03 (the default) | ~19,600 | ~89,000 | ~18 hours |
| 2025-07-01 | ~15,300 | ~70,000 | ~14 hours |
| 2026-01-01 | ~9,300 | ~43,000 | ~9 hours |
| last ~90 days (2026-07-08) | ~3,400 | ~16,000 | ~3 hours |

Hearings add about 1,000 requests per run (the hearing list has no useful change filter, so it is re-read each run). Later incremental
runs cost the list pages plus only the bills that changed. Backfill in slices (`--from-date` / `--to-date`) rather than all at once.

## Known Congress.gov limitations

- The bill list's update filter is not a scope filter (thousands of bills are "updated" every few days), so scope is decided from each
  bill's own action dates.
- Summaries are CRS-written HTML; they are stored as plain text and only exist once CRS has written them (new bills have none).
- A bill's policy area is empty until it has been classified; subjects can lag.
- Hearing details often have no committee data (printed Senate hearings especially), and some hearings appear under more than one
  jacket number (for example S.Hrg.119-191 under jackets 1 and 61880). Both are stored as the source gives them; nothing is merged by inference.
- Congress.gov committee system codes (`hsed00`) are a different scheme from the House Clerk codes in `committee_assignments`
  (`ED00`). They are stored as given and are not mapped yet.
- Actions have no stable ID; identity is a hash of date, code and text, so two identical actions on one day collapse into one.
- Sponsors and cosponsors who are not POLTRACKER politicians are not stored as people (the bill's sponsor ID and name are kept on the
  bill row). Nothing is matched by name.
