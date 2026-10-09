# Trade context signals (Phase 3)

Deterministic, public-data context for each trade. It uses no network, no language model, and stores no suspicion score. A "flag" is a prompt for a
person to look at public context. It does not mean wrongdoing, and it does not estimate whether a member knew anything.

Run: `python -m poltracker.analyze_trade_context` (`--dry-run`, `--force`, `--limit N`, `--trade-id ID`, `--politician ID|NAME`, `--ticker T`, and the threshold
options below). It reads trades, committee seats, SIC codes, the committee/industry mappings and cached price bars, and writes only `trade_context` and
`trade_context_evidence` (migrations 0012, 0013). Reruns leave unchanged rows alone.

## Signals (each True, False, or unknown)

| Signal | True when | Unknown when |
|---|---|---|
| `committee_relevance` | a **reviewed + direct** mapping applies to the member's committee/subcommittee seats and the security's SIC code | no SIC, no committee seats, or an unmapped committee and no direct match |
| `trade_size_anomaly` | the trade's representative value is at or above the 90th percentile of the same politician's earlier trades, with at least 10 earlier trades | no usable range, an untrustworthy date, or fewer than 10 earlier trades |
| `disclosure_delay_signal` | disclosure date minus transaction date is **more than 45 days** | a missing, future or inconsistent date (a negative delay is never repaired) |
| `excess_return_signal` | the absolute excess return versus SPY over the 90 days from the transaction anchor is **at least 20 percentage points** | no prices, an invalid date, or the 90-day window has not elapsed |

`needs_review` mappings never affect a signal. `reviewed + related` mappings are stored as **supporting context** and never create the committee signal.
A trade has one committee signal with one evidence row per supporting mapping, so a parent and a subcommittee mapping are not double counted.

## The flag rule

```
meets_flag_rule = committee_relevance
                  AND at least TWO of (trade_size_anomaly, disclosure_delay_signal, excess_return_signal)
flagged_for_contextual_review = meets_flag_rule AND the committee evidence is temporally_verified
```

Committee relevance is mandatory; unknown never counts as true. Examples: committee + size + delay flags; committee + one secondary does not;
three secondary signals without committee relevance do not; performance alone never flags. `secondary_signal_count` (0-3) is stored on every row, and
`--min-secondary` changes the number needed. When the rule is met but seat timing is unverified, the row has `meets_flag_rule = true`, is not flagged, and the API
sets `flag_pending_temporal_verification`.

## Methodology (engine version `2026.3`)

- **Trade size.** Disclosures give a range. The representative value is the midpoint of a closed range, the lower bound of an open-ended range
  ("Over $50,000,000", which can only understate), and the figure itself when min equals max. It is never an exact transaction value. The percentile is the
  mid-rank among the politician's trades with a strictly **earlier** transaction date (ties count half). Only that politician's own trades are used,
  so a result does not change when later trades arrive.
- **Disclosure delay.** The raw `disclosure_delay_days` is always kept. A periodic transaction report is generally due by the earlier of 30 days after the filer
  became aware of the transaction and 45 days after it. The awareness date is not public, so the transaction date is the only reference POLTRACKER has, and the
  signal marks a delay of more than 45 days. It does not say a filing was late, excused or improper: the filing circumstances are unknown.
- **Excess return.** The existing performance engine over a **fixed 90-calendar-day horizon** from the transaction anchor (`--excess-horizon-days`). A fixed window
  gives every trade a comparable horizon, stops older trades accumulating years of performance, and keeps the age of a trade from driving the signal. A trade younger
  than the horizon, or whose prices stop sooner, is unknown. The absolute raw excess return drives the signal. The direction-adjusted figure for sells is stored
  separately. The 20-point threshold is configurable (`--excess-return`).
- **Committee seats and time.** The House Clerk's snapshot (`MemberData.xml`) lists seats held **now** and has no dates. Dated history comes from adopted House
  resolutions (see [COMMITTEE_HISTORY.md](COMMITTEE_HISTORY.md)): exact start and end dates at committee level. Each piece of committee evidence carries a status:

  | Status | Meaning |
  |---|---|
  | `temporally_verified` | official records establish the committee seat on the transaction date (committee-level mappings only) |
  | `current_assignment_only` | the seat is known only from the current snapshot (always true of a subcommittee seat, whose history is not recorded) |
  | `unavailable` | no committee data for the member (the Senate, or an unmatched politician) |
  | `contradicted` | a current seat would match, but official records show the member did not hold it on the transaction date; the trade is not committee-relevant and the rejected match is kept as evidence |

  The committee/industry match is kept as context in every case, but only `temporally_verified` evidence can flag a trade. A verified committee seat never promotes a
  subcommittee-only match. Dates are never invented, and no third-party committee history is used. `--ignore-temporal-status` exists only for what-if comparisons.
- **Duplicate-looking rows.** Rows are never merged or deleted. The API adds `group_key` (politician + security + transaction date + type) and `group_size` so a
  UI can show that rows belong together. Owner codes (self, spouse, joint, dependent) can mark separate reportable transactions.

## Versioning

`context_version` is `2026.3`. It changes when the flag rule, the size methodology or the default thresholds change; `2026.2` added the 45-day delay, 20-point excess return, two secondary signals and a temporal gate on snapshot seats; `2026.3` uses dated seat history. `2026.1` used a 30-day delay, a 10-point
excess return over a variable horizon, one secondary signal and no temporal gate. A non-default option on the command line gets its own label
(`2026.3+custom-xxxxxx`) so it never overwrites default rows. Rows are keyed by trade, context version and mapping version, so a new mapping version or engine
version adds rows and keeps the old ones. A changed input (new prices, a corrected disclosure) updates that trade's row in place and sets `analyzed_at`.

## API

`GET /trades` and `GET /trades/{id}` carry `group_key`, `group_size` and an optional `context` object (null until the analyzer has run) with the signals, percentile,
delay, returns, `secondary_signal_count`, `committee_temporal_status`, `meets_flag_rule`, `flag_pending_temporal_verification`, `flagged_for_contextual_review`,
`evidence` and a `notice`. `GET /trades?flagged=true` returns flagged trades only. Existing fields are unchanged. The Trades page has a Context column and a
"Flagged for contextual review" filter; clicking a chip shows the signals, their evidence and the seat-timing caveat.

## AI context (optional explanations)

`python -m poltracker.analyze_trade_context_llm` asks OpenAI for a short, neutral explanation of one trade's **already-calculated** context. The deterministic engine stays
authoritative: the model cannot set a signal, change the flag, or add evidence, and this command never writes `trade_context`. It needs `OPENAI_API_KEY`; without it
the explanation is simply unavailable (the app, the API and the dialog work as before).

- **Which trades.** Flagged trades only by default, at most 25 OpenAI calls per run (`--limit`, `POLTRACKER_TRADE_LLM_MAX_CALLS`). `--trade-id` explains a named trade even when it is
  not flagged; that text is labelled `manual` and the dialog says it is an explanation on request, not a flag. `--ticker`/`--politician` stay flagged-only unless `--no-flagged-only`.
  `--dry-run` shows what would be sent without a key or a call. `--force` regenerates. `--verbose` prints the facts and the answer.
- **What is sent.** One trade's facts: ticker, company, SIC industry, type, disclosed range, dates; the politician's name, chamber, state and district; the committee evidence
  (committee, reviewed-direct status, seat timing and whether the seat was held on the transaction date, mapping rationale and source); the four signals with their values,
  percentile, sample size, delay, 90-day security / SPY / excess return (raw, plus the direction-adjusted figure labelled as such); and the flag state. No other rows, no key.
- **How.** OpenAI Responses API, `store: false`, no tools, strict JSON schema (`headline`, `summary`, `signals[]`, `limitations`). Model: `POLTRACKER_TRADE_LLM_MODEL`
  (default `gpt-4o-mini`). Prompt version `1`.
- **Validation (untrusted text).** A reply is rejected, never stored and never repaired, if it is malformed, refused or incomplete; names a signal that is not one of the trade's
  four; explains a signal twice; names a committee that is not in this trade's stored evidence (including a known committee named without the word "committee"); states a number
  that is not among the supplied values (to the precision written); uses insider / illegal / corrupt / suspicious / wrongdoing / non-public / probability and similar wording outside an
  explicit denial in the same clause; speaks of a flag on an unflagged trade; or is empty or over-long.
- **Cache.** Table `trade_context_analysis` (migration 0015), one row per trade, context version, mapping version, prompt version and model. A rerun with unchanged facts makes no call.
  Changed facts replace the row only after the new text validates. A changed prompt, model or context version adds a new row. The API shows an explanation only while it still
  matches the context it explained (`context_digest`).
- **API and UI.** `context.ai_context` is optional (null when none exists). The dialog shows it in a separate "AI context" panel below the deterministic signals, with a subtle
  "not generated" state.
- **Cost.** The run summary reports calls, input and output tokens and, only if you set `POLTRACKER_TRADE_LLM_INPUT_USD_PER_MTOK` / `..._OUTPUT_USD_PER_MTOK`, an estimate. No rate is assumed.
