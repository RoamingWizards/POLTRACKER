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

## [x] Phase 7 — Production compatibility

Goal:
Prepare POLTRACKER for the approved zero-cost architecture without deploying it.

Completed:
- PostgreSQL parity fixes (NULLs sort last on both databases, byte-order text sorts on PostgreSQL,
  deterministic security names), `DATABASE_URL` handling, the `psycopg` dependency and pool settings
- migration 0005 (`ingest_state.last_success_at`) and the successful-ingest timestamp
- single-run ingest exits non-zero on a provider error
- configurable CORS (`CORS_ORIGINS`) and configurable frontend API URL (`VITE_API_BASE_URL`)
- stale-ingestion reporting in the API and on the Data Status page
- GitHub Actions ingestion workflow (gated off by default), `render.yaml`, `.python-version`,
  `frontend/.nvmrc`, and `docs/PRODUCTION_READINESS.md`
- Linux PostgreSQL CI (`.github/workflows/ci.yml`)

Merged:
- PR #5, merge commit `629a1fa`; commits `652702d`, `807ad2d`, `e974338`, `2d5be2f`

Verification:
- CI on Linux: PostgreSQL 18.6 (Debian) with `en_US.utf8` collation passed the SQLite-vs-PostgreSQL
  parity tests; 152 PostgreSQL tests passed (0 skipped); 147 SQLite tests passed (5 skipped);
  migrations 0001–0005 applied to a clean database; frontend type check and build passed;
  `actionlint` passed

After the merge:
- The real local `poltracker.db` was migrated from 0004 to 0005. Row counts and per-table content
  hashes were identical before and after, and the Desktop backup was left unchanged.

Not done, by design: no deployment, no Neon / Render / Cloudflare resources, no repository secrets,
no scheduled ingestion.

Carried forward (see the current task and known issues):
- The old Telegram and Finnhub keys still need revoking.
- Neon-specific behaviour (its collation, SSL, latency, pooled connections) is unverified.
- The Render cold-start experience in the frontend is not implemented.

---

# Current task

## [ ] Phase 7B — Neon validation (validation only)

Goal:
Prove that the existing, empty Neon project works with POLTRACKER: connectivity and SSL, the
migrations, and the schema. This task validates; it does not deploy the application and does not
move any real data.

Target:
- the existing Neon project and its `production` branch. The project ID is supplied by the project
  owner on the command line and is deliberately not recorded in this file.

Steps, in order:

1. Link the existing project and `production` branch with the Neon CLI. **Always** pass
   `--no-env-pull`. Make sure `.neon` is git-ignored first (add it to `.gitignore` if it is not).
2. Run `neon config plan` first. If, and only if, the plan is clean, run
   `neon deploy --no-env-pull`.
   - "Clean" means: no conflicts, nothing destructive, nothing that needs `--update-existing` or
     `--allow-protected`. Never pass those flags.
   - If the plan shows anything else, stop and report. Do not deploy.
3. Test Neon connectivity and SSL: connect with PostgreSQL SSL required, and report the server
   version, the database collation, whether the session is encrypted, and the connection latency.
   Record whether the pooled endpoint works with psycopg 3 prepared statements (informational).
4. Check the Neon database is empty, then run Alembic migrations 0001–0005 on it. If it is not
   empty, stop and report.
5. Run the PostgreSQL parity tests against Neon (see the safety constraint below).
6. Confirm the schema is valid: every expected table and column exists, the revision is
   `0005 (head)`, and `alembic check` reports no drift between the models and the database.

Rules:
- Do not write `DATABASE_URL` (or any connection string or token) into the repository, `.env`,
  logs, or output. Supply it to a command through its environment only, and never print it.
- Do not use the Neon MCP server. Do not create API keys or any other secret.
- Do not copy the real local POLTRACKER data. Do not touch the real local `poltracker.db`.
- Do not configure Render or Cloudflare. Do not enable GitHub ingestion (`INGEST_ENABLED`).
  Do not add repository secrets. Do not change GitHub repository settings.
- Do not push anything.
- Do not create Neon resources beyond what the steps above do (no new projects, roles, or
  production-branch databases). The ONE temporary test branch/database authorised in the extended
  scope below is the only exception.

Safety constraint for step 5:
- The PostgreSQL test suite DROPS and recreates every table, and one test wipes the whole `public`
  schema. It must never run against the `production` database. The test fixtures refuse any
  database whose name does not contain "test".
- Running it against Neon therefore needs a separate database or short-lived branch whose name
  contains "test". The extended scope below authorises exactly one such temporary environment
  (created, used, and deleted within Phase B). Nothing else may be created.

If a step fails, or a command is blocked or needs approval, stop and report instead of working
around it.

### Extended authorization (2026-10-07)

The project owner authorised proceeding automatically through the steps below, stopping only at the
STOP GATES. Routine, reversible work inside an authorised phase needs no further approval.

- **Phase A, Neon production schema.** Inspect the linked production database read-only. If the
  public schema has no unexpected tables or data: run migrations 0001–0005, confirm
  `alembic current` is `0005 (head)`, run `alembic check`, confirm the expected tables exist with
  zero rows, and verify the pooled endpoint works with the migrated schema. If anything unexpected
  exists: STOP FOR REVIEW. Do not copy data and do not run ingestion.
- **Phase B, temporary Neon test environment.** Create ONE temporary branch/database whose name
  contains `test`, that is not production, and that never receives real POLTRACKER data. Run
  migrations 0001–0005, the full PostgreSQL parity/backend suite, and the pooling checks against
  it, then delete it. A real compatibility failure: STOP FOR REVIEW.
- **Phase C, copy preparation.** Prepare and validate the exact SQLite-to-Neon copy method (source
  unchanged, IDs and relationships and migration state preserved, counts and content hashes
  verified). Do not copy any data.
- **STOP GATE 1.** Before copying real data into Neon production, report: production schema status,
  temporary test results, the exact copy method, expected row counts, the rollback/recovery plan,
  and confirmation that the local database stays untouched. Do not copy until approved.
- **Phase D (only after Gate 1 approval).** Copy the data into Neon production and verify counts,
  foreign keys, and API-equivalent queries; confirm the local SQLite is unchanged; report the
  free-tier backup/export strategy. Any mismatch: STOP FOR REVIEW.
- **Phase E, Render preparation.** Inspect read-only and prepare the free web service from the
  repo's existing config (Python 3.13, the repo build and start commands, `DATABASE_URL`,
  `CORS_ORIGINS`). **STOP GATE 2** before creating or materially changing the service (report name,
  free-tier status, build and start commands, env vars, and whether any payment prompt appears;
  any paid requirement: stop immediately).
- **Phase F (only after Gate 2 approval).** Create the free service, set the variables securely,
  deploy, verify `/health`, `/status`, `/trades`, a politician and a security endpoint, and record
  the backend URL. Do not enable scheduled ingestion.
- **Phase G, Cloudflare Pages preparation.** Build the frontend with `VITE_API_BASE_URL` set to the
  backend URL, confirm CORS matches the eventual Pages origin, and verify no secrets are in the
  bundle. **STOP GATE 3** before creating the Pages project (report name, build command, output
  directory, env vars, and any payment requirement).
- **Phase H (only after Gate 3 approval).** Create the free Pages project from `main`, set the
  variable, deploy, record the URL, update Render's CORS if needed, and verify the dashboard.
- **Phase I, GitHub ingestion.** Add the production `DATABASE_URL` as a repository secret without
  printing it, keep `INGEST_ENABLED` unset, run the ingestion workflow manually once, and verify
  success, `last_success_at`, a fresh `/status`, and no duplicates. **STOP GATE 4** before setting
  `INGEST_ENABLED`.
- **Phase J (only after Gate 4 approval).** Set `INGEST_ENABLED=true`, confirm the schedule is
  registered, and create no additional schedulers.

Standing prohibitions for all phases: no paid tiers or billing, no Neon MCP, no git-history
rewrites, no branch deletion except the single temporary Neon test environment, no modification of
the local SQLite data, and no credential in the repository, a log, or any output.

Status: Phases A, B and C are authorised now. Phases D–J are NOT authorised until the preceding
STOP GATE is approved by the project owner.

### STOP FOR REVIEW

Stop at STOP GATE 1 (or earlier if a phase says STOP FOR REVIEW) and summarize.

Do not continue into data migration, Render, Cloudflare, or ingestion beyond the gates above.

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
