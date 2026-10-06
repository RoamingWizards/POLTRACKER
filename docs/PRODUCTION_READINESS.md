# Production readiness (Phase 7)

POLTRACKER is now **configurable** for the approved zero-cost architecture (Cloudflare Pages, Render Free, Neon
PostgreSQL, GitHub Actions). **Nothing is deployed.** No account, project, secret or production database exists, and
the real local `poltracker.db` has not been migrated to PostgreSQL. The reasoning and limits behind the architecture
are in [DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md).

## Configuration reference

| Where | Name | Purpose | Secret? |
|---|---|---|---|
| Backend | `DATABASE_URL` | Database. Default `sqlite:///./poltracker.db`. Accepts `postgres://` or `postgresql://` and adds the `psycopg` driver itself | **Yes** for production |
| Backend | `CORS_ORIGINS` | Comma-separated browser origins allowed to call the API, e.g. `https://example.pages.dev`. No trailing slash, no path. Empty disables CORS. Defaults to the local dev and preview ports | No |
| Backend | `INGEST_STALE_AFTER_HOURS` | Data Status warns when the last successful ingest is older than this. Default `24` | No |
| Backend | the rest | `CONGRESSINVESTS_*`, `INGEST_*`, `PRICE_*`, `BENCHMARK_TICKER`: see `.env.example` | Only `CONGRESSINVESTS_API_KEY` |
| Frontend (build time) | `VITE_API_BASE_URL` | Public URL of the API for production builds. Unset in development | **No**: it is baked into the public bundle |
| GitHub Actions | secret `DATABASE_URL` | Direct (non-pooled) PostgreSQL connection string for the ingest job | **Yes** |
| GitHub Actions | variable `INGEST_ENABLED` | Set to `true` to switch the 6-hourly schedule on. Unset means scheduled runs do nothing | No |

A malformed `CORS_ORIGINS` (for example `example.com` or a URL with a path) stops the API at startup with a clear
error, because it could never match a browser's `Origin` header.

## Local development (unchanged)

SQLite remains the default and needs no configuration.

```bash
.venv/bin/alembic upgrade head      # needed once after pulling: migration 0005 adds ingest_state.last_success_at
.venv/bin/uvicorn poltracker.api.main:app --port 8000
cd frontend && npm run dev          # leave VITE_API_BASE_URL unset: /api is proxied to port 8000
```

Back up `poltracker.db` before upgrading an existing database. Migration 0005 only adds a nullable column and can be
reversed, but migration 0003 (older) cannot.

## Database

- **SQLite and PostgreSQL behave the same** for the API. The two known differences were fixed: NULLs now sort last in
  both directions on every database, and a security's display name comes from the `securities` table instead of
  `max(asset_name)`, which depended on the database collation. Name sorting uses byte order on PostgreSQL
  (`COLLATE "C"`) to match SQLite.
- **Connections:** PostgreSQL engines use `pool_pre_ping`, a small pool and early recycling, because Neon suspends idle
  compute and drops connections. Use Neon's **direct** connection string for the ingest job. Whether psycopg 3
  prepared statements work through Neon's pooled (PgBouncer) endpoint is untested.
- **Migrations are applied by hand**, never automatically: run `alembic upgrade head` against the production database
  once before the first deploy. The ingest workflow refuses to run if the database is not at the latest revision.

### Running the tests on PostgreSQL

```bash
# any PostgreSQL 14+; the database name MUST contain "test" because the tests drop and recreate every table
export POLTRACKER_TEST_DATABASE_URL="postgresql://USER:PASSWORD@HOST/poltracker_test"
.venv/bin/pytest
```

With the variable set, the **whole** suite runs on PostgreSQL, plus two PostgreSQL-only modules:
`test_pg_parity.py` (about 38 API requests compared between SQLite and PostgreSQL on the same data) and
`test_migrations_postgres.py` (migrations 0001 to 0005 on a clean database, and the 0003 data merge). Without the
variable they are skipped. The test refuses to run against a database whose name lacks "test".

**Collation caveat.** Text ordering follows the database collation, which differs by platform. The PostgreSQL used
during development (macOS, no ICU) sorts like SQLite, so it cannot show locale differences. The parity dataset
contains names that would expose them (accents, mixed case, punctuation), so the Linux CI job below runs them on a
Linux PostgreSQL and prints its collation. Neon itself is still unchecked.

### Continuous integration

`.github/workflows/ci.yml` runs on every pull request and every push to `main`. It deploys nothing and needs no
secrets.

| Job | What it does |
|---|---|
| Backend | Python 3.13 on Linux with an official `postgres:18` service container and a throwaway database named `poltracker_test`. It prints the server version and collation, applies migrations 0001 to 0005 to the clean database (and checks the result is `0005 (head)`), then runs the **whole suite on PostgreSQL**, then again on SQLite |
| Frontend | Node 22: `npm ci`, `npx tsc -b`, `npm run build` |

Safeguards: the PostgreSQL step **fails if any test was skipped**, so a misconfigured URL cannot turn the
PostgreSQL-only tests into a silent pass. Test runs use `pytest-socket` to refuse every connection except localhost, so
a test that tried to reach CongressInvests, Yahoo, Neon or Render would fail instead of passing quietly. The service
container uses trust authentication and is reachable only from the runner, so no password or secret exists. Only the
package registries and the container registry are contacted, to install dependencies and pull the image.

## Render (API): settings to use later

`render.yaml` records them. It is only a record until a Blueprint is created in Render.

| Setting | Value |
|---|---|
| Runtime / plan | Python, `free` |
| Build command | `pip install .` |
| Start command | `uvicorn poltracker.api.main:app --host 0.0.0.0 --port $PORT` |
| Health check path | `/health` |
| Python version | pinned by `.python-version` (`3.13`). Render's default for new services is 3.14.3, which is untested here |
| Environment variables | `DATABASE_URL`, `CORS_ORIGINS` (entered in the dashboard, never committed) |

Free services sleep after 15 minutes idle (the next request takes roughly a minute) and have no persistent disk, so
the database must be PostgreSQL. Verified locally: the package installs with `pip install .` and the start command
serves `/health` against PostgreSQL.

## Cloudflare Pages (frontend): settings to use later

| Setting | Value |
|---|---|
| Root directory | `frontend` |
| Build command | `npm run build` (runs `tsc -b && vite build`) |
| Build output directory | `dist` (that is `frontend/dist`) |
| Environment variable | `VITE_API_BASE_URL` = the API's public URL (no trailing slash needed, one is stripped) |
| Node version | 22. `frontend/.nvmrc` says so; also set `NODE_VERSION=22` in the Pages settings to be certain. Vite 8 needs Node 20.19+ or 22.12+ |
| SPA routing | Pages treats a project without a `404.html` as a single-page app, so deep links work |

After the first deploy, add the Pages URL to `CORS_ORIGINS` on the API.

## GitHub Actions ingestion

`.github/workflows/ingest.yml` runs `python -m poltracker.ingest --enrich` every 6 hours (cron `17 */6 * * *`) and on
manual dispatch.

- **Off until you opt in:** scheduled runs are skipped unless the repository variable `INGEST_ENABLED` is `true`.
  Manual runs are always allowed and need the `DATABASE_URL` secret, otherwise they fail with a clear message.
- **Safe checks first:** the job fails early if the secret is missing or is not a PostgreSQL URL, and if the database
  is not at the latest migration. It never runs migrations.
- **Failures are visible:** a provider error makes the command exit non-zero, so the run shows as failed.
- **Reads straight from the database:** it does not need the Render API awake.
- **Limits that still apply:** scheduled workflows in public repositories are disabled after 60 days without
  repository activity, runs can start late, and runs execute from `main`. The workflow was checked with `actionlint`
  and contains no secrets; it has **not** been run against any production database.

## Stale-ingestion warning

`GET /status` now returns `last_successful_ingest_at`, `ingest_age_hours`, `ingest_stale_after_hours` and
`ingest_stale`. The timestamp is written at the end of every ingest run that finishes without a provider error, even
when it found nothing new, so a quiet weekend does not trigger a false alarm. The Data Status page shows a warning
banner (and the sidebar shows "stale") when the last successful ingest is older than the threshold or has never been
recorded. When data is fresh nothing is shown but a normal "on schedule" chip.

## Still to do before any deployment

See the deployment sequence in [DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md). Not done in this phase: creating the Render,
Neon and Cloudflare projects, adding secrets, applying migrations to a production database, copying the real data,
setting `INGEST_ENABLED`, and the Render cold-start experience in the frontend (retry and "waking up" message).
