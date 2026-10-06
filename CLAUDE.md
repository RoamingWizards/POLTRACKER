# CLAUDE.md — POLTRACKER

## Project purpose

POLTRACKER is a congressional securities-trading analytics application.

It ingests public U.S. congressional trade disclosures through a provider abstraction, stores normalized trade data, enriches it with market prices, calculates benchmark-relative performance, and serves the results through a FastAPI backend and a React dashboard.

The project should remain:
- modular
- testable
- provider-neutral where practical
- inexpensive to operate
- suitable as a public portfolio project

---

## Current architecture

### Backend
- Python
- FastAPI
- SQLAlchemy 2.x
- Alembic
- SQLite for now
- pytest

### Frontend
- React
- TypeScript
- Vite
- Material UI
- MUI X Data Grid
- MUI X Charts
- MUI date pickers
- TanStack Query

### Congressional trade data
Primary live provider:
- CongressInvests

Provider abstraction:
- `CongressProvider`

Current/future providers:
- `CongressInvestsProvider`
- `QuantEnginesProvider` as secondary/future
- official House/Senate disclosure ingestion may be added later

The browser must never call congressional data providers directly.

### Market data
Primary implementation:
- yfinance

Provider abstraction:
- `PriceProvider`

The rest of the application must not depend directly on yfinance.

### Benchmark
- SPY is the current S&P 500 benchmark proxy.

### SEC
- SEC EDGAR integration is not yet part of the implemented scope.
- Do not add it unless TASKS.md explicitly calls for it.

---

## Data flow

CongressInvests API
→ ingestion
→ normalization
→ deduplication
→ SQLite
→ price enrichment
→ performance calculations
→ FastAPI
→ React dashboard

The frontend only communicates with the POLTRACKER FastAPI backend.

---

## Existing major features

The project already includes:

- House and Senate congressional trade ingestion
- persistent SQLite storage
- incremental ingestion
- resumable backfill state
- deterministic trade deduplication
- politician normalization
- market price enrichment
- persistent price-bar caching
- transaction-date and disclosure-date anchors
- weekend and market-holiday handling
- SPY benchmark comparisons
- excess-return calculations
- invalid-date handling
- FastAPI endpoints
- React dashboard
- responsive layout
- light/dark mode
- overview page
- trades page
- politicians page
- politician detail page
- security detail page
- data-status page
- route-based frontend code splitting
- README and screenshots
- automated backend tests

---

## Important data rules

### Source preservation
Never silently alter source data.

If upstream data appears wrong:
- preserve the original value
- flag or annotate the anomaly
- avoid guessing the intended value

Example:
A future transaction date should remain stored as supplied and be marked `invalid_date` for enrichment.

### Transaction amounts
Congressional disclosures usually provide ranges.

Store:
- amount_min
- amount_max

Do not represent the midpoint as the actual transaction value.

If midpoint values are used for optional aggregate calculations, label them clearly as estimates.

### Dates
Keep transaction date and disclosure date separate.

For price anchoring:
- use the first available trading day on or after the stated date
- do not silently move the disclosure itself
- invalid future dates should not be repaired by guessing

### Performance
Keep raw returns separate from direction-adjusted returns.

For sells:
- the raw security return remains the actual security return
- any direction-adjusted measure must be stored/displayed separately

Use neutral wording such as:
- performance
- return
- excess return
- disclosure activity

Do not imply wrongdoing, insider trading, suspicious activity, or illegality from price performance alone.

---

## Known limitations

Current known limitations include:

- CongressInvests does not provide party/state consistently, so some fields remain null
- upstream politician-name variants may still exist for nicknames/full middle names
- some tickers have no usable Yahoo price data
- delisted/acquired/renamed securities may have incomplete price histories
- at least one upstream trade has a clearly invalid future date
- CongressInvests history is limited
- QuantEngines currently has an empty live dataset
- SEC EDGAR enrichment is not yet implemented
- production deployment has not yet been implemented

Do not “fix” these by inventing data.

---

## Git workflow

Primary branches:
- `main`
- feature/development branch as specified in TASKS.md

Rules:
1. Never modify `main` directly unless the task explicitly says to.
2. Never push unless the task explicitly allows or requires it.
3. Before every commit:
   - run `git status`
   - inspect staged files
   - confirm only intended files are staged
4. Prefer small, logically separated commits.
5. Keep commit messages concise and descriptive.
6. Do not rewrite Git history unless explicitly instructed.
7. Do not delete branches unless explicitly instructed.

---

## Secrets and sensitive files

Never commit:
- `.env`
- API keys
- tokens
- passwords
- database files
- `.venv`
- `node_modules`
- `dist`
- caches
- install artifacts
- temporary screenshots outside intended documentation paths

The old Telegram and Finnhub keys were historically committed to the public repository.

Rules:
- never reproduce those credentials
- never copy them into new files
- assume they must be revoked
- do not rewrite public history unless explicitly instructed

Environment-based configuration should be used for secrets.

---

## Database rules

Current database:
- SQLite

ORM:
- SQLAlchemy

Migrations:
- Alembic

Guidelines:
- use SQLAlchemy rather than raw SQL unless there is a strong reason
- keep migrations deterministic
- test migrations on both an existing-style database and a fresh database where relevant
- do not perform destructive/irreversible migration work casually
- call out irreversible migrations clearly
- preserve compatibility with a future PostgreSQL migration where practical

Migration 0003 is irreversible.
Existing databases should be backed up before applying it.

---

## Provider design rules

External data providers must be isolated behind provider interfaces.

Do not spread provider-specific field names across business logic.

Provider-specific behavior belongs in provider modules.

Current abstractions:
- `CongressProvider`
- `PriceProvider`

When replacing or adding a provider:
- normalize provider output into POLTRACKER domain models
- preserve source/provider identifiers where available
- handle retries/rate limits at the provider boundary
- keep downstream services provider-neutral

---

## Testing requirements

### Backend
After backend changes:
- run the relevant focused tests first
- then run the full backend test suite before declaring completion

Current known passing baseline:
- 102 backend tests

### Frontend
After frontend changes:
- run TypeScript type checking
- run the production build

When behavior changes materially:
- test it in a real browser if practical
- verify loading, empty, error, and unavailable-data states where relevant

Do not claim success from static code inspection alone if the task changes runtime behavior.

---

## Frontend design rules

Use the existing Material UI dashboard foundation.

Prefer existing MUI components over custom reimplementation.

Do not introduce a second chart/table/UI library without a clear technical reason.

Keep the interface:
- clean
- dense
- finance-oriented
- responsive
- usable in light and dark mode

Do not add:
- unnecessary animations
- marketing pages
- authentication
- landing-page fluff

unless TASKS.md explicitly requires them.

---

## Cost and token efficiency

Avoid unnecessary redesign and repetition.

Before major work:
- inspect existing code
- reuse working patterns
- modify the minimum number of files necessary

Do not repeatedly:
- rewrite README content
- redesign the architecture
- regenerate existing components
- refactor working code without a concrete benefit

When a task is narrowly scoped, stay within scope.

---

## Execution rules

When starting work:
1. Read this file.
2. Read TASKS.md.
3. Check the current branch.
4. Check `git status`.
5. Identify the next unchecked task.

For each task:
1. understand the acceptance criteria
2. inspect only the relevant code
3. implement the smallest safe change
4. run appropriate tests/checks
5. update TASKS.md if instructed
6. commit only if the task explicitly allows commits
7. continue only if the next task does not require review

---

## Stop conditions

Stop and summarize instead of continuing automatically if:

- TASKS.md says `STOP FOR REVIEW`
- a destructive action is required
- credentials are required
- a paid service would be introduced
- a migration risks data loss
- tests fail and the failure cannot be safely resolved
- the requested action would modify public history
- the next step would merge to main, deploy, or incur billing unless TASKS.md explicitly authorizes it
- a major architectural decision is genuinely ambiguous

When stopping, report:
- what was completed
- what changed
- tests/build results
- remaining issue
- exact decision needed

Do not ask for approval for routine, reversible implementation work that is already authorized by TASKS.md.

---

## Completion summary format

When a task completes, keep the summary concise:

- Files changed
- What was implemented
- Tests/checks run
- Result
- Known caveats
- Next task / stop reason

Do not produce long architectural essays unless the task specifically asks for them.
