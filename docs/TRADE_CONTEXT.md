# Trade context signals (Phase 3)

Deterministic, public-data context for each trade. It uses no network, no language model, and stores no suspicion score. A "flag" is a prompt for a
person to look at public context. It does not mean wrongdoing, and it does not estimate whether a member knew anything.

Run: `python -m poltracker.analyze_trade_context` (`--dry-run`, `--force`, `--limit N`, `--trade-id ID`, `--politician ID|NAME`, `--ticker T`).
It reads trades, committee seats, SIC codes, the committee/industry mappings and cached price bars, and writes only `trade_context` and
`trade_context_evidence` (migration 0012). Reruns leave unchanged rows alone.

## Signals (each True, False, or unknown)

| Signal | True when | Unknown when |
|---|---|---|
| `committee_relevance` | a **reviewed + direct** mapping applies to the member's committee/subcommittee seats and the security's SIC code | no SIC, no committee seats, or an unmapped committee and no direct match |
| `trade_size_anomaly` | the trade's representative value is at or above the 90th percentile of the same politician's earlier trades, with at least 10 earlier trades | no usable range, an untrustworthy date, or fewer than 10 earlier trades |
| `disclosure_delay_signal` | disclosure date minus transaction date is at least 30 days | a missing, future or inconsistent date (a negative delay is never repaired) |
| `excess_return_signal` | the absolute excess return versus SPY over 90 days from the transaction anchor is at least 10 percentage points | no prices, an invalid date, or the 90-day window has not elapsed |

`needs_review` mappings never affect a signal. `reviewed + related` mappings are stored as **supporting context** and never create the committee signal.
A trade has one committee signal with one evidence row per supporting mapping, so a parent and a subcommittee mapping are not double counted.

## The flag

`flagged_for_contextual_review = committee_relevance AND (trade_size_anomaly OR disclosure_delay_signal OR excess_return_signal)`.
Committee relevance is mandatory. Size, delay or excess return alone never flags a trade, and unknown never counts as true.

## Methodology (engine version `2026.1`)

- **Trade size.** Disclosures give a range. The representative value is the midpoint of a closed range, the lower bound of an open-ended range
  ("Over $50,000,000", which can only understate), and the figure itself when min equals max. It is never an exact transaction value. The percentile is the
  mid-rank among the politician's trades with a strictly **earlier** transaction date (ties count half). Only that politician's own trades are used,
  so a result does not change when later trades arrive.
- **Excess return.** The existing performance engine, over a fixed 90-day window (`--excess-horizon-days`). Measured to the latest bar, a year-old trade
  needs far less luck to exceed 10 points than a recent one. The absolute raw excess return drives the signal. The direction-adjusted figure for sells is
  stored separately.
- **Committee seats are current seats.** The House Clerk gives no seat history, so an older trade is matched to the seats held now. Senate members have no
  committee data yet, so their trades are unknown.

## Versioning

`context_version` is the engine version (`2026.1`) and changes when the flag rule, the size methodology or the default thresholds change. A non-default
threshold on the command line gets its own label (`2026.1+custom-xxxxxx`) so it never overwrites default rows. Rows are keyed by trade, context version
and mapping version, so loading a new mapping version adds rows and keeps the old ones. A changed input (new prices, a corrected disclosure) updates
that trade's row in place and sets `analyzed_at`.

## API

`GET /trades` and `GET /trades/{id}` carry an optional `context` object (null until the analyzer has run) with the signals, percentile, delay, returns,
`flagged_for_contextual_review`, `evidence` and a `notice`. `GET /trades?flagged=true` returns flagged trades only. Existing fields are unchanged.
The Trades page has a Context column and a "Flagged for contextual review" filter; clicking a chip shows the signals and their evidence.
