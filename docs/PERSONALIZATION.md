# Personalized context screens

A user can change **how POLTRACKER surfaces trades** without changing **what it recorded about them**.

| Objective stored facts (never rewritten) | User personalization (local, adjustable) |
|---|---|
| committee relevance and its seat timing, trade-size percentile, disclosure delay, 90-day excess return, evidence, and the canonical `flagged_for_contextual_review` | which signals are enabled, their thresholds, how many secondary signals are required, filters, presets and saved views |

Changing a setting never writes `trade_context`. A custom screen is computed on the fly from the stored facts and reported **next to** the canonical flag, never instead of it.

## The rule (`context_rules.ContextRule`)

| Setting | Default (canonical methodology) |
|---|---|
| `committee_relevance_required` | true |
| `reviewed_direct_only` | true (false also counts *reviewed* related mappings; a `needs_review` mapping is never stored or used) |
| `require_temporal_verification` | true (committee seat verified for the transaction date) |
| `enable_trade_size_signal` / `trade_size_percentile_threshold` | true / 90 (percentile >= 90, among the member's own earlier trades) |
| `enable_disclosure_delay_signal` / `disclosure_delay_threshold_days` | true / 45 (more than 45 days) |
| `enable_excess_return_signal` / `excess_return_threshold_pct_points` | true / 20 (absolute 90-day excess return, percentage points) |
| `minimum_secondary_signals` | 2 |

At a default threshold the rule reads the engine's own stored boolean for that signal, so the default rule reproduces the canonical flag exactly (checked over all 5,381 trades of a scratch copy: 2 and 2, zero mismatches). A different threshold reads the stored number (percentile, days, excess return). An incoherent rule is refused: more required signals than are enabled, or no committee requirement and no secondary signal (it would match every trade).

## Presets (transparent configurations, shown in the UI)

- **Balanced**: the default methodology.
- **Strict**: committee relevance, all 3 secondary signals, percentile >= 95, delay > 60 days, |excess return| >= 25 points.
- **Committee focus**: committee relevance only. For browsing; **not** the contextual-review flag.
- **Market focus**: no committee requirement; 2 of 3 market signals. A performance and filing-timing screen that says nothing about political context.
- **Custom**: your own settings.

## Filters (AND only)

politician, chamber, party, state, district, ticker, company, industry, transaction type, transaction date, disclosure date, disclosed value range (the range, never a midpoint), committee relevance, committee name (from the stored evidence), trade-size percentile, disclosure delay, excess return (including `|value| >=`), active signals (under the current rule), contextual-review status (the canonical flag), custom-screen match, AI-context availability. Filters are applied on the server.

## API

- `GET /context/presets`: the default rule and the built-in presets with notes.
- `GET /trades/screen?rule=<json>&filters=<json>&sort_by&order&limit&offset`: read-only, GET only. Each trade carries `custom_screen` (match, active signals, kind, and the canonical flag repeated for comparison); the page carries `custom_match_count` and `canonical_flag_count` over all filtered trades. `GET /trades` is unchanged.
- Local writes, mounted only in the desktop app or with `POLTRACKER_LOCAL_VIEWS=1`: `GET/POST /context/views`, `PATCH/DELETE /context/views/{id}`, `GET/PUT/DELETE /context/active` (the last-used screen, so it survives a restart).

Saved views and the last-used screen live in the local SQLite database (`context_views`, `app_preferences`, migration 0016). There are no accounts, no sync and no network call. The public read-only API has no write routes.

## Wording

"Contextual review", "custom screen", "active signals" and "committee relevance". A custom screen is a way of browsing stored context. It is not the contextual-review flag, and neither says anything about intent or knowledge. A market-only screen is never presented as political context.
