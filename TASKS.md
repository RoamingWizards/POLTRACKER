# TASKS.md — POLTRACKER

## How to use this file

Work through the next unchecked task in order.

Follow all rules in `CLAUDE.md`.

Continue automatically through tasks unless:
- the task says `STOP FOR REVIEW`
- a CLAUDE.md stop condition is triggered

Do not redo completed tasks.

---

# Completed phases

## [x] Phase 1 — Congressional trade ingestion backend

Completed:
- CongressInvests provider
- normalized trade ingestion
- SQLite persistence
- SQLAlchemy models
- Alembic
- deduplication
- FastAPI base endpoints
- tests

Commit:
`624ff48 Build congressional trade ingestion backend`

---

## [x] Phase 2 — Market price enrichment and performance analytics

Completed:
- `PriceProvider`
- yfinance implementation
- persistent price-bar caching
- weekend/holiday price anchoring
- invalid-date handling
- transaction-date returns
- disclosure-date returns
- SPY benchmarking
- excess returns
- performance API endpoints
- tests

Commit:
`960f521 Add market price enrichment and performance analytics`

---

## [x] Phase 3 — React congressional trading dashboard

Completed:
- React + Vite + TypeScript
- Material UI dashboard foundation
- MUI Data Grid
- MUI Charts
- TanStack Query
- Overview
- Trades
- Politicians
- Politician Detail
- Security Detail
- Data Status
- backend summary/status/sorting support
- responsive/mobile behavior
- light/dark mode

Commit:
`17a961d Build React congressional trading dashboard`

---

## [x] Phase 4A — Secure legacy configuration

Completed:
- moved legacy script to `legacy/`
- removed active hardcoded credentials
- environment-variable configuration
- deprecation header

Commit:
`9c89bdc Secure legacy configuration`

---

## [x] Phase 4B — Harden normalization and resumable ingestion

Completed:
- conservative politician normalization
- repeated-first-name normalization
- middle-initial normalization
- fingerprint recomputation
- migration 0003
- ingestion state
- migration 0004
- resumable backfill
- migration regression testing
- live re-ingest validation

Commit:
`9efbfdd Harden normalization and resumable ingestion`

---

## [x] Phase 4C — Dashboard polish and documentation

Completed:
- route-based code splitting
- README
- screenshots
- browser verification
- loading/empty/error-state checks
- no-price-state checks
- 3M/6M/1Y/All chart range checks
- frontend production build with no size warning

Commit:
`d925bbd Polish dashboard and documentation`

Current validation baseline:
- 102 backend tests passing
- frontend type check passing
- frontend production build passing

---

## [x] Phase 5 — Merge PR #1 into main

PR:
`rebuild-dashboard` → `main`

Completed:
- PR #1 merged using a merge commit (`960abfc`), not squashed or rebased
- the six rebuild commits are now on `origin/main`:
  - `624ff48`
  - `960f521`
  - `17a961d`
  - `9c89bdc`
  - `9efbfdd`
  - `d925bbd`
- local `main` switched and pulled
- `rebuild-dashboard` intentionally kept (not deleted)
- history not rewritten

Subsequently, `CLAUDE.md` and `TASKS.md` were added to `main` in commit
`14cbb71` ("Add files via upload").

Reminder:
- The old Telegram and Finnhub keys remain in public Git history and must be revoked separately.

---

## [x] Phase 6 — Deployment planning

Deliverable:
`docs/DEPLOYMENT_PLAN.md` — approved and merged.

Completed:
- deployment plan written under a hard constraint of $0 recurring infrastructure cost
- plan approved by the project owner on 2026-10-06
- merged to `main` via PR #3 using a merge commit (`82c7aa7`); content commit `5b6772f`
  ("Document zero-cost deployment architecture")
- `docs/deployment-plan` branch intentionally kept (not deleted)
- no application code changed, nothing deployed, no accounts or secrets created

Approved $0 architecture:
- Cloudflare Pages — React frontend
- Render Free web service — FastAPI backend (read-only API)
- Neon Free PostgreSQL — persistent storage
- GitHub Actions every 6 hours — ingestion and price enrichment, writing directly to Neon

Approved decisions recorded in the plan:
- target recurring infrastructure cost is $0
- Render Free sleeps after 15 minutes of inactivity; the first request after sleep can take roughly
  one minute. This is accepted and is not a reason to switch to Vercel
- Render local storage is ephemeral and must not hold the production database, so PostgreSQL on
  Neon is required
- GitHub Actions writes directly to Neon and does not depend on the Render API being awake
- scheduled workflows in public GitHub repositories can be disabled after 60 days without
  repository activity
- the Data Status page should make stale ingestion visible
- free-tier terms can change and must be re-checked before deployment

Evidence behind the plan:
- PostgreSQL compatibility was measured locally in a scratch copy: migrations 0001–0004 ran
  unmodified, 98 of 98 database tests passed, and the real data copied in 3.5 s
- two small code fixes were identified (NULL sort ordering; a collation-dependent `max()` query)

**Deployment itself is NOT approved.** Nothing in `docs/DEPLOYMENT_PLAN.md` may be executed yet.
This includes creating Render, Neon or Cloudflare accounts or projects, adding repository or
production secrets, changing GitHub repository settings, and making the PostgreSQL code changes
listed in section 7 of the plan. Each requires separate, explicit approval in this file.

Reminders before any deployment is approved:
- Revoke the old Telegram and Finnhub keys (still in public Git history).
- Back up the local `poltracker.db`. CongressInvests only serves the last 365 days, so older
  trades cannot be re-fetched.
- Re-check every free-tier limit and term against the providers' current pages.

---

# Current task

## [~] Phase 8 — Standalone macOS application (`macos-app` branch)

Direction change: cloud deployment (Render / Neon / Cloudflare) is stopped. The PostgreSQL and deployment work stays in
the repository as optional future web support. The target is `release/POLTRACKER.app`; see `docs/MACOS_APP.md`.

Built and tested: desktop launcher, local server, SQLite bootstrap/import, background refresh and UI, PyInstaller spec,
`scripts/build-macos.sh`, packaged-app tests. Awaiting review; nothing merged.

### STOP FOR REVIEW

Do not push further, merge to main, sign, or notarize until reviewed.

## [~] Phase 9A — Official politician enrichment (`politician-enrichment` branch)

Migration 0006, Congress.gov + House Clerk providers, conservative matcher, `python -m poltracker.enrich_politicians`,
Politician Detail profile. See `docs/POLITICIAN_ENRICHMENT.md`. Reviewed alias overrides (0007) and opt-in LLM-assisted identity resolution (0008) added; no trade analysis, scoring or allegations. Awaiting review.

---

# Planned future work

These tasks are intentionally not authorized yet.

## [~] Phase 11A — Company sector and industry enrichment (`feature/committee-sector-context` branch)

Phase 1 of the committee/sector context direction (bill and hearing ingestion was dropped; its experimental work lives on
`feature/legislative-data`, unmerged). Adds SEC EDGAR company profiles (CIK, SIC code, industry, sector, exchange) to `securities` through
migration 0009 and `python -m poltracker.enrich_securities`. See `docs/SECURITY_PROFILES.md`. Metadata only: no committee/industry mapping,
contextual flags, scoring, AI explanation or personalized filters. Later phases: 2 committee-industry mapping, 3 contextual signals,
4 AI explanation of structured signals, 5 personalized filters. Awaiting review.

---

## [~] Phase 11B — Committee/industry mapping (`feature/committee-industry-mapping` branch, stacked on 11A)

Deterministic, explainable mapping from committee/subcommittee jurisdiction (House Rule X) to SIC ranges, a matcher that returns
relevant / not relevant / unknown with provenance, migration 0010, and a read-only measurement over existing trades. See
`docs/COMMITTEE_INDUSTRY_MAPPING.md`. Round 1 of human review is applied (round 2 decisions applied; remaining proposals are in `docs/review/round2/`): 191 mappings, 64 `reviewed` (rounds 1 and 2), 127 still `needs_review` (`docs/review/review_decisions_2026.1-draft.md`).
Review pass: every row now has `review_status` / `reviewed_by` / `jurisdiction_basis` (migration 0011, all rows `needs_review`), and
`python -m poltracker.committee_industry_review` generates the human-review packet (`docs/review/`). The intended Phase 3 flagging policy is
documented, not implemented. The Phase 3 policy is now adopted (only `reviewed` + `direct` mappings may contribute to a flag; one
committee-relevance signal per trade). A 50-row priority review table with proposed actions is in `docs/review/`.
No trade is flagged or scored, no market data or AI is used, and no per-trade result is stored. Later phases: 3 contextual signals and review
flags, 4 AI explanation of structured signals, 5 personalized filters. Awaiting review.

---

## [~] Phase 11C — Deterministic trade context signals (`feature/trade-context-signals` branch, stacked on 11B)

Committee relevance (reviewed + direct mappings only), trade-size percentile, disclosure delay and excess return, combined into a selective
`flagged_for_contextual_review` (committee relevance is mandatory). Migration 0012, `python -m poltracker.analyze_trade_context`, additive API fields and a minimal
Trades-page panel. See `docs/TRADE_CONTEXT.md`. No AI explanation, personalization, scoring, or real-database changes. Awaiting review.

---

## [ ] Phase 7 — SEC EDGAR enrichment

Status:
Not yet approved.

Potential scope:
- ticker ↔ CIK mapping
- company metadata
- 10-K
- 10-Q
- 8-K
- filing links
- company filing panel on Security Detail

Do not implement yet.

---

## [ ] Phase 8 — Additional provider resilience

Status:
Not yet approved.

Potential scope:
- QuantEngines if its live dataset becomes populated
- official House/Senate ingestion
- additional free/paid fallback providers
- provider health/failover

Do not implement yet.

---

## [ ] Phase 9 — Data-quality improvements

Status:
Not yet approved.

Potential scope:
- nickname normalization
- full-middle-name normalization
- party/state enrichment
- ticker rename history
- delisted/acquired security handling
- better anomaly reporting

Do not implement yet.

---

# Known issues / reminders

- CongressInvests history is limited.
- Party/state fields are currently missing for many records.
- Some politician name variants remain.
- Some Yahoo tickers have no usable history.
- Delisted/acquired names can have incomplete price coverage.
- One known upstream SONY transaction date is invalid and is intentionally preserved.
- Migration 0003 is irreversible.
- Back up an existing database before applying irreversible migrations.
- The historical Telegram and Finnhub credentials must be revoked if they have not already been revoked.
- Do not attempt to “repair” bad source values by guessing.
