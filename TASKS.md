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

# Current task

## [ ] Phase 6 — Deployment planning (planning and research only)

Status:
Approved. This phase produces a recommendation document. It does not deploy anything.

Deliverable:
A deployment recommendation, saved as `docs/DEPLOYMENT_PLAN.md`, covering:

1. frontend hosting options
2. backend hosting options
3. persistent database options
4. scheduled ingestion options
5. environment and secrets handling
6. expected free-tier and low-cost limits
7. estimated monthly cost
8. recommended architecture for POLTRACKER
9. migration path from local SQLite
10. deployment steps
11. risks and limitations

Guidance:
- Prefer low-cost or free-tier options appropriate for a public portfolio project.
- Base claims about pricing and limits on current provider documentation, and state when
  figures could not be verified.
- Keep the recommendation consistent with the constraints in `CLAUDE.md`
  (cost-conscious, provider-neutral, SQLite today with a PostgreSQL path later).

Phase 6 must NOT:
- deploy anything
- create paid resources
- modify DNS
- create cloud databases
- add production secrets
- change GitHub repository settings
- add billing
- migrate SQLite to PostgreSQL
- change production branches

Documentation changes only. Any hosting accounts, deployments or spending decisions
require a separate, explicit approval in this file.

### STOP FOR REVIEW

Stop after the recommendation is written and summarize it.

Do not begin deployment.

---

# Planned future work

These tasks are intentionally not authorized yet.

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
