# POLTRACKER Deployment Plan ($0 Edition)

**Status:** Phase 6 deliverable. **The architecture in section 12 was approved by the project owner on 2026-10-06.**
This document is planning and research only. Nothing described here has been deployed or provisioned. No account,
resource, secret, DNS record, database or billing relationship was created.

> ## Hard constraint: monthly infrastructure cost = £0 / $0
> No paid service is recommended as the primary architecture. Paid hosting appears only as an optional future
> upgrade (section 11). Free tiers can change, so every limit below is tagged with how it was checked.

**Researched:** 2026-10-06. Re-check the linked pages before relying on any figure.

Evidence tags:

- **[V]** verified on the provider's official page on 2026-10-06
- **[S]** secondary source (search summary, third-party article, community post)
- **[M]** measured by me on this repository on 2026-10-06
- **[U]** not verified

---

## 1. Recommendation at a glance

**One $0 architecture:**

```
 Cloudflare Pages ──────────►  Render free web service  ──────────►  Neon free PostgreSQL
 (React build, static)         (FastAPI, read-only, sleeps          (persistent data,
                                after 15 min idle)                   suspends after 5 min idle)
                                                                            ▲
 GitHub Actions (scheduled, public repo) ── ingest + price enrichment ──────┘
 runs every 6 hours, writes straight to the database, does not need the API awake
```

| Question | Answer |
|---|---|
| Services | Cloudflare Pages, Render (free web service), Neon (free Postgres), GitHub Actions |
| Monthly cost | **$0** (no paid component) |
| Persistence | PostgreSQL on Neon. The Render service itself keeps no state |
| Automated ingestion | A GitHub Actions workflow every 6 hours that talks to the database directly |
| Cold start | About **1 minute** after 15 idle minutes (Render), plus a few hundred ms for Neon to wake **[V]** |
| Credit card | Probably none, but Render sometimes requests one for verification **[S]** (section 4) |
| Code changes | Small and concrete (section 7). I tested them: see section 2 |
| SQLite to PostgreSQL | Low effort. Measured: migrations run unmodified, 98 of 98 database tests pass, data copy 3.5 s locally |
| Biggest risks | The 60-day scheduled-workflow auto-disable, shared-IP rate limits at CongressInvests and Yahoo, and free-plan policy changes |

### Approved decisions and fixed constraints

These are stated here in plain terms so they cannot be missed:

1. **Target recurring infrastructure cost is $0 (£0).** No paid service is part of the architecture.
2. **Render's free web service sleeps after 15 minutes of inactivity.** It is accepted as-is. The decision is *not* to
   switch to Vercel merely to avoid it.
3. **The first request after sleep can take roughly one minute** to be answered (Render's spin-up is "about one
   minute" **[V]**).
4. **Render's local storage is ephemeral and must not hold the production database.** Free web services cannot attach
   a persistent disk **[V]**, and the service may restart at any time **[V]**. A SQLite file on Render would be lost.
5. **PostgreSQL on Neon is therefore required**, not optional. SQLite stays only for local development and tests.
6. **GitHub Actions writes directly to Neon.** Ingestion and price enrichment never depend on the Render API being
   awake. The API is only a reader.
7. **Scheduled workflows in public GitHub repositories can be disabled after 60 days without repository activity**
   **[V]**, which would silently stop ingestion until someone re-enables the workflow.
8. **The Data Status page should make stale ingestion visible.** Today it shows how long ago the last ingest ran. A
   required future change (section 7, item 7) is an explicit stale warning when that age exceeds a threshold, so a
   disabled schedule is noticed.
9. **Free-tier terms can change and must be re-checked before deployment.** Every limit in this document was read on
   2026-10-06. Re-verify the plan's figures, especially Render's free-tier terms and card requirement, Neon's
   storage and compute limits, and GitHub's scheduled-workflow rules, immediately before starting (step 2 of the
   deployment sequence).

**Nothing should start until this plan is recorded as approved in `TASKS.md`, and the old Telegram and Finnhub keys have been
revoked** (they remain in public Git history).

---

## 2. What I measured on this repository

### 2.1 Application footprint **[M]**

| Item | Value |
|---|---|
| Database today | SQLite 30 MB. 5,381 trades, 105 politicians, 1,062 securities, 272,477 price bars |
| API process | 81 MB steady state, ready in 0.5 s |
| Full price backfill (one-time) | 69 s, 232 MB peak |
| Ingest (caught up) | about 1 HTTP request per run |
| Frontend build | 2.6 MB, 77 files |

### 2.2 PostgreSQL compatibility test (real PostgreSQL 18.4, local, scratch copy of the repo) **[M]**

I ran an embedded PostgreSQL server locally. No cloud account or network service was used, and the real repository
and database were not modified.

| Test | Result |
|---|---|
| Alembic migrations 0001 to 0004 on an empty PostgreSQL database, **unmodified** | Applied cleanly |
| Existing backend tests with the database fixture pointed at PostgreSQL | **98 passed**, 4 deselected (those test the SQLite-specific migration 0003 path) |
| Copy the real data (279,000 rows) from SQLite to PostgreSQL | **3.5 s** locally. Needs an empty target |
| PostgreSQL storage for the same data | **46.2 MB** (price bars 34.2 MB, trades 2.8 MB) vs 30 MB in SQLite |
| Storage growth | about 132 bytes per price bar, so roughly **32 MB per year** |
| 32 API requests run against both databases with identical data | **29 identical, 3 different** |

Two causes account for the three differing responses (the `ticker` sort differs in both directions), and a third
finding came out of the comparison:

1. **`/trades?sort_by=ticker` (asc and desc): NULL ordering.** One trade has no ticker. SQLite sorts NULLs first
   ascending and last descending. PostgreSQL does the opposite. Fix: explicit `nulls_last()`.
2. **`/stats/overview` top tickers: nondeterministic display name.** The query uses `max(asset_name)`, and string
   ordering depends on the database collation, so the two databases chose different names for `UNH`. Fix: take the
   name from the `securities` table instead.
3. **Not a database difference, but found by this test:** the PostgreSQL value exposed that `clean_asset_name` leaves noise in some
   names (for example `UnitedHealth Group Incorporated S (partial) 06/12/2026 07/08/2026 $1,001 - $15,000`). The
   pattern `S (partial)` is not handled. This is a pre-existing data-quality issue, listed under future work
   (Phase 9), and does not block deployment.

**Limits of this test:** a local PostgreSQL over a Unix socket is not Neon. Network latency, SSL, connection
pooling, and Neon's PostgreSQL version were not tested **[U]**.

---

## 3. Options evaluated, and why most are eliminated at $0

### 3.1 Backend hosting

| Option | $0? | Persistent disk | Sleep / cold start | Verdict |
|---|---|---|---|---|
| **Render free web service** | Yes | **No** (not supported on free) **[V]** | Spins down after 15 min idle, spin-up about 1 min **[V]**. 750 free instance hours/month **[V]** | **Recommended.** No disk needed once the database is external |
| Vercel Hobby (FastAPI as one serverless function) | Yes. Non-commercial use only **[V]** | None, stateless | Serverless cold start (seconds, **[U]**) | Good alternative (section 10). Needs more code change |
| FastAPI Cloud, Hobby | $0, no card **[V]** | Not stated **[U]** | Automatic scale-to-zero **[V]** | **Public beta pricing** **[V]**, so terms may change. Only 0.1 vCPU (burst to 0.5) and 512 MB **[V]** |
| Koyeb free instance | Yes **[S]** | 2 GB SSD **[S]** | Scales to zero after 1 hour idle **[S]** | Card verification reported (a pre-authorisation) **[S]**, conflicting. Regions limited to Frankfurt and Washington D.C. **[S]** |
| Railway free plan | $1 monthly credit **[V]** | 0.5 GB volume **[V]** | n/a | Credit is too small for an always-on service. Exhaustion behaviour is not stated **[V]** |
| **Hugging Face Spaces** | **No.** Docker Spaces need a paid plan to create **[V]** | n/a | n/a | **Eliminated** |
| Fly.io | **No.** Trial of 2 hours or 7 days only **[V]** | | | Eliminated |
| Google Cloud Run | Free tier exists **[S]** but needs a billing account **[U]** | Ephemeral | Scales to zero | Rejected: card and billing account |
| Oracle Always Free | Reported halved in June 2026 **[S]** | | | Rejected: policy volatility, card **[U]** |
| Cloudflare Workers | Free **[V]** | None | | Not suitable: no pandas or SQLAlchemy runtime, 10 ms CPU limit on free **[V]** |

### 3.2 Frontend hosting

| Option | $0? | Notes |
|---|---|---|
| **Cloudflare Pages** | Yes | Static asset requests are free and unlimited **[V]**. 500 builds/month, 20,000 files, 25 MiB per file **[V]**. A project without a `404.html` is treated as a single-page app, so deep links like `/securities/NVDA` work **[V]**. Card requirement is not stated in the docs I read **[U]** |
| Vercel Hobby | Yes | 100 GB transfer, 100 deployments/day **[V]**. Non-commercial, personal use only **[V]** |
| GitHub Pages | Yes | 1 GB site, soft 100 GB/month **[V]**. No commercial SaaS use **[V]**. SPA deep links need a workaround **[U]** |

### 3.3 Database

| Option | $0? | Storage / limits | Sleep | Verdict |
|---|---|---|---|---|
| **Neon free** | Yes | **1 GB per project**, 100 CU-hours/month, 5 GB egress **[V]**. A secondary source says 0.5 GB **[S]**, so I designed for the lower figure (we use 46 MB either way) | Suspends after 5 min idle, cannot be disabled **[V]**. Resumes in "a few hundred milliseconds" **[V]** | **Recommended** |
| Supabase free | Yes | 500 MB, 2 projects **[V]** | **Paused after 1 week of inactivity** **[V]** | Plausible backup. The scheduled job should count as activity, but I could not verify what counts **[U]** |
| Aiven free PostgreSQL | Yes, no card **[V]** | 1 GB, 1 GB RAM, single node **[V]** | "Service powers off after a period of inactivity", duration not stated **[V]** | Backup option. Unclear inactivity window, so riskier |
| Turso free (libSQL, SQLite-compatible) | Yes | 5 GB, 500 M reads and 10 M writes per month **[V]** | not stated | Would minimise code change, but SQLAlchemy driver support is untested **[U]** |
| Render free Postgres | Yes | 1 GB | **Expires 30 days after creation** **[V]** | Eliminated |
| SQLite on any free host | n/a | Free hosts above have no persistent disk, or sleep | | Not viable at $0 |

### 3.4 Scheduler

| Option | $0? | Notes |
|---|---|---|
| **GitHub Actions `schedule`** | Free for standard runners in public repos **[V]** | Min interval 5 min; can be delayed (especially at the top of the hour); runs only on the default branch; jobs up to 6 hours **[V]**. **Scheduled workflows in public repos are disabled automatically after 60 days without repository activity** **[V]**. What counts as activity is not stated **[V]** |
| Vercel Cron (Hobby) | Yes | **Once per day only**, with timing precision of +/- 59 minutes **[V]**. Too coarse alone |
| Cloudflare Workers Cron Triggers | 5 triggers on Free, 50 subrequests per invocation, 10 ms CPU **[V]** | Cannot run Python or the ingestion code. Could only poke another service |
| Render cron job | Not free | **Eliminated** |

---

## 4. The recommended services in detail

**Render's local disk is ephemeral.** Nothing written to it survives a restart or redeploy, so it must never hold the
production database. All persistent state lives in Neon (section 1, decision 4).

| | Cloudflare Pages | Render free web service | Neon free Postgres | GitHub Actions |
|---|---|---|---|---|
| **Role** | Static React build | FastAPI (read-only) | Persistent data | Scheduled ingestion and enrichment |
| **Why it is free** | Static hosting is the loss-leader for Cloudflare's network. Static requests are free and unlimited **[V]** | A free tier to attract users to paid plans. 750 free instance hours per workspace per month **[V]** | A free tier to attract developers. Usage-based paid plan, no monthly minimum **[V]** | Free standard runners for public repositories **[V]** |
| **Limits** | 500 builds/month, 20,000 files, 25 MiB per file **[V]** | 750 hours/month, single instance, no disk, no SSH, restarts any time **[V]** | 1 GB storage per project, 100 CU-hours/month, 5 GB egress **[V]** | 6 h per job, 20 concurrent jobs **[V]** |
| **Our usage** | 77 files, 2.6 MB | One idle-capable service (max 744 h if never sleeping) | 46 MB, a few CU-hours | A few minutes per run, 4 runs per day |
| **If exceeded** | Builds stop for the month **[U]**. Static serving continues | Free services are **suspended until next month** **[V]** | **Compute suspended until next period**; at the storage cap, **inserts, updates and deletes fail** **[V]**. Egress overage **[U]** | A job over 6 h is terminated **[V]**. Disabled schedule: ingestion **stops silently** |
| **Credit card** | Not stated **[U]** | Docs say none. Community reports a $1 verification hold that is cancelled **[S]** | No card required **[S]** | None |
| **Cold start** | None | **About 1 minute** **[V]** | A few hundred ms **[V]** | n/a |
| **Free plan withdrawal risk** | Low: core business is free static delivery | Moderate: free terms have changed before (free Postgres expires at 30 days) **[V]** | Moderate: acquired by Databricks in May 2025, and terms have changed since **[S]** | Low to moderate: the 60-day rule is real **[V]** |

**On the "why it is free" row:** those explanations are my inference from each provider's published pricing model.
The providers do not state their reasons, and none of them guarantees a free plan will continue.

**Credit-card summary.** I expect to need no card. The one realistic exception is **Render asking for verification**
before the first free deploy **[S]**. If that happens, a fallback is Vercel for the API (section 10).

---

## 5. Cold-start behaviour and how the app should handle it

First visit after the API has been idle for more than 15 minutes:

1. Cloudflare Pages serves the React app instantly.
2. The first API call wakes Render: **about 1 minute** **[V]**. What a browser's `fetch` sees during that minute
   (hang, 502/503, or a loading page) is **[U]**.
3. The API then reaches Neon, which resumes in a few hundred ms **[V]**.
4. After that, responses are normal (measured locally at 3 to 40 ms warm **[M]**).

Today the frontend retries once with no wake-up message. That would show skeletons and then an error. Required change
(section 7): retry with backoff for a few minutes, show a clear "API is waking up" message, and send a warm-up request
as soon as the app loads. You said cold starts are acceptable, so this is a UX change and not a blocker.

---

## 6. Scheduled ingestion when the backend sleeps

The API does **not** perform ingestion in this design, so its sleeping is irrelevant to freshness.

```
every 6 hours (GitHub Actions cron, e.g. "17 */6 * * *")
  └─ checkout repo → install deps → python -m poltracker.ingest --enrich
        ├─ reads/writes Neon directly with DATABASE_URL (a repository secret)
        ├─ calls CongressInvests (about 1 request when caught up)
        └─ calls Yahoo for missing price ranges (cached per day)
```

- The existing CLI already does exactly this. It needs the PostgreSQL support from section 7.
- Neon wakes on connect and suspends 5 minutes after the job ends **[V]**. A rough estimate is under 40 minutes of
  compute per day, about 20 compute-hours per month at worst against 100 **[M estimate, compute size U]**.
- The next visitor wakes Render and sees whatever the last run wrote.
- A GitHub Actions run does not need the API, so there is no "wake the sleeping server" problem to solve.

**Scheduler limitations (all real):**

- **60-day auto-disable [V].** If the repository has no activity for 60 days, scheduled workflows are turned off and
  ingestion silently stops. GitHub does not say what counts as activity, nor whether manual dispatch still works
  while disabled **[V: stated as not stated]**. Mitigations: any commit or PR resets the clock (I believe, **[U]**);
  re-enabling is one click or `gh workflow enable`; and the Data Status page already shows the age of the last
  ingest, so staleness is visible. After deployment, test and document the actual behaviour.
- **Delays.** Runs can start late, especially at the top of the hour **[V]**, so schedule at an odd minute.
- **Default branch only [V]**, so changes to the workflow take effect when merged to `main`.
- **Shared IPs.** GitHub runners egress from shared cloud IP ranges **[U]**. This affects two upstreams:
  - CongressInvests allows **100 requests/day per IP** **[V]**. We need about 4 per day, but the quota is per IP.
    The code already stops cleanly on HTTP 429 and resumes next run (tested).
  - Yahoo may throttle datacenter and CI IPs **[S]**. Mitigation: enrichment is incremental and cached, failures
    are retried next run, and the large one-time backfill is done **from your own machine**, not from CI.
- **Secrets.** `DATABASE_URL` must be stored as a repository secret. That is a GitHub repository settings change and
  needs your explicit approval at deployment time, not now.

---

## 7. Required application-code changes (not made in this phase)

Everything below was either **measured** (section 2) or follows directly from a measured result.

1. **PostgreSQL driver:** add `psycopg[binary]` as a dependency (it was installed and worked in my test).
2. **Database URL handling:** providers hand out `postgresql://` (or `postgres://`) URLs, but SQLAlchemy needs
   `postgresql+psycopg://`. Normalise the scheme in `config.py`.
3. **Connection pool settings** in `db.py` for a database that suspends: `pool_pre_ping=True`, a small pool, and
   `pool_recycle`. Idle connections will be dropped when Neon's compute suspends (my inference from scale-to-zero, **[U]**). The
   existing SQLite-only `PRAGMA` branch stays as is.
4. **Explicit NULL ordering** (`nulls_last()`) in the trade sorts (difference 1 in section 2.2).
5. **Deterministic security name** in `/stats/overview` (difference 2). Use `securities.name`, not `max(asset_name)`.
6. **CORS middleware** driven by a `CORS_ORIGINS` setting, limited to the Pages origin. The API has none today **[M]**.
7. **Frontend:** `VITE_API_BASE` at build time, the wake-up retry and message, and the warm-up request (section 5),
   plus a **stale-ingestion warning on the Data Status page** (for example when the last ingest is older than about
   24 hours, four missed 6-hour runs) so a disabled schedule becomes visible.
8. **Data copy script** (SQLite to PostgreSQL). My scratch prototype is about 25 lines of SQLAlchemy, takes 3.5 s
   locally, and **requires an empty target** (a duplicate-key failure when I forgot to truncate proved it).
9. **GitHub Actions workflows:** `ingest.yml` (schedule plus manual dispatch) and `ci.yml` (tests, type check, build).
   For CI, run the backend tests against both SQLite and a PostgreSQL service container. Public repos run free.
10. **Render configuration:** build and start commands (for example `pip install .` then
    `uvicorn poltracker.api.main:app --host 0.0.0.0 --port $PORT`). Whether Render's native Python runtime accepts a
    `pyproject.toml`-only project without extra files is **[U]**.
11. **Optional:** handle the `S (partial)` asset-name noise (Phase 9).

**Effort estimate (my judgement, based on the measured results):** roughly one working day for items 1 to 9,
including tests. The measured evidence is that migrations ran unmodified, 98 of 98 database tests passed, and only
two small behavioural differences appeared. The unknown part is Neon-specific behaviour (SSL, pooling, latency),
which a local test cannot reveal.

**One caution to verify at deployment:** Neon offers a pooled connection string (PgBouncer in transaction mode).
psycopg 3 uses server-side prepared statements, which are known to conflict with transaction pooling **[U for this
exact combination]**. Use the **direct** connection string for the GitHub Actions job and test the API against
whichever string you choose before relying on it.

---

## 8. Secrets and environment

| Variable | Where | Secret? |
|---|---|---|
| `DATABASE_URL` (Neon, with SSL) | Render environment variables, and a GitHub Actions repository secret | **Yes** |
| `CORS_ORIGINS` | Render | No |
| `VITE_API_BASE` | Cloudflare Pages build variable | No, it ships in the JS |
| `CONGRESSINVESTS_API_KEY` | not used (free tier) | n/a |

Never commit `.env`. Use each platform's secret store. Nothing from the legacy script is needed.

---

## 9. Risks and limitations

| Risk | Impact | Mitigation |
|---|---|---|
| **Scheduled workflow auto-disabled after 60 days of repo inactivity** **[V]** | Data silently goes stale | Data Status shows last ingest. Re-enable with one click. Verify the exact rule after deployment. Consider a periodic commit as a keep-alive **[U]** |
| **CongressInvests per-IP quota on shared CI IPs** | Ingest returns 429 | Clean stop and resume (tested). About 4 requests/day needed |
| **Yahoo throttling cloud/CI IPs** **[S]** | Missing prices | Incremental cache, retry next run, backfill locally |
| **CongressInvests keeps only 365 days of history** **[V]** | **Losing the database loses trades older than a year that cannot be re-fetched** | Take periodic exports (for example a weekly `pg_dump` or CSV workflow artifact). Artifact retention and size limits **[U]**. Neon's free history window is only 6 hours **[V]** |
| Neon storage cap reached | Writes fail **[V]** | At 46 MB and +32 MB/year this is decades away |
| Neon compute hours exhausted | Database suspended until next period **[V]** | Estimated usage is a fraction of 100 CU-hours |
| Render free restart "at any time" and 1-minute wake **[V]** | Slow first load | Wake-up UX (section 5) |
| Render may request a card **[S]** | Blocks the free deploy | Fallback: Vercel for the API (section 10) |
| Free-plan policy drift or withdrawal | Architecture needs moving | Provider-neutral code. The app is portable: only the database URL, the start command and the workflow file change |
| Public unauthenticated API | Scraping or traffic spikes use free quotas | Cache headers and rate limiting at the edge (future). Exceeding Render hours suspends the service, which stops spend but also the demo |
| Terms | CongressInvests restricts commercial redistribution **[V]** | Keep the site non-commercial with attribution |
| Legacy credentials still in public history | Possible misuse | **Revoke them.** History is not rewritten |

---

## 10. Other $0 alternatives (and why they rank lower)

| | Setup | Advantage | Disadvantage |
|---|---|---|---|
| **B. Vercel for both frontend and API** + Neon + GitHub Actions | FastAPI as one serverless function (officially supported, bundle limit 500 MB, Hobby function duration up to 300 s **[V]**) | One platform, no CORS, no 1-minute Render wake (serverless cold starts are shorter, **[U]**) | More code change: an `/api` prefix (SPA routes such as `/trades` collide with API routes, and API routes win), a function entrypoint, serverless-friendly connections. Hobby is non-commercial only **[V]**. Hobby cron is daily only, so GitHub Actions is still needed **[V]** |
| C. FastAPI Cloud (Hobby) + Pages + Neon + Actions | Built by the FastAPI team, $0, no card **[V]** | Simplest FastAPI deploy | **Public beta pricing** and tiny CPU **[V]**. Disk and outbound access not stated **[U]** |
| D. Koyeb free + Pages + Neon + Actions | | Roughly the same as Render | Card verification reported **[S]**; scale-to-zero after 1 hour **[S]** |
| E. Turso (libSQL) instead of PostgreSQL | Keeps SQLite semantics | Least code change in theory | SQLAlchemy driver untested **[U]**. Remote latency per query. Not recommended without a test |
| F. Supabase or Aiven instead of Neon | | Free Postgres alternatives | Pause after 1 week inactive **[V]** (Supabase), unclear power-off window **[V]** (Aiven) |

---

## 11. Optional future upgrades (paid, not recommended now)

Kept only for reference. These keep SQLite, because each gives a persistent disk. Figures are from my earlier research
on 2026-10-06.

| Option | Approx. monthly cost | Notes |
|---|---|---|
| Fly.io 512 MB machine + 1 GB volume | $3.69 + $0.15 **[V]** | No free tier. Always-on API with the ingest loop in the same machine |
| Railway Hobby | $5 (includes $5 usage credit) **[V]** | Simple GitHub deploys. Volume sharing between services not verified **[U]** |
| Hetzner CX23 VPS | about EUR 3.99 **[S]** | Most headroom. You operate the server |
| CongressInvests Pro key | $29 **[S]** | Removes the 100 requests/day limit. Not needed |

---

## 12. Recommended $0 architecture

**Cloudflare Pages + Render free web service + Neon free PostgreSQL + GitHub Actions.**

| Layer | Service | Monthly cost |
|---|---|---|
| Frontend | Cloudflare Pages | $0 |
| API | Render free web service (FastAPI) | $0 |
| Database | Neon free PostgreSQL | $0 |
| Scheduler | GitHub Actions (public repo) | $0 |
| **Total** | | **$0** |

Why this one:

- It is the only combination I found where **every** component is free, none needs a disk, and the data is on a
  persistent managed database.
- It maps onto the project with **small, measured** changes. The migration test showed clean migrations, 98 of 98
  database tests passing, and two minor behavioural differences.
- Ingestion is decoupled from the sleeping API, which removes the usual "scheduler versus cold start" trap.
- Everything is replaceable independently (section 10), and the code stays provider-neutral.

What you accept: a roughly 1-minute first load after idle, ingestion every 6 hours, a possible card verification at
Render, free-tier terms that can change, and an auto-disable rule on the scheduler that needs occasional attention.

---

## 13. Future deployment sequence

> **Do not execute.** This is a plan. Each step needs explicit approval in `TASKS.md`, including account creation,
> repository-settings changes and secrets.

**Step 0: preconditions**
1. Revoke the old Telegram bot token and Finnhub key.
2. Record the approved architecture and the $0 constraint in `TASKS.md`, then **re-check every free-tier limit and term
   in this document against the providers' current pages** (they can change). Pay particular attention to Render's
   card requirement, Neon's storage and compute limits, and GitHub's scheduled-workflow rules.
3. Back up the local `poltracker.db` (a plain file copy). Migration 0003 is irreversible, and CongressInvests only
   serves the last 365 days, so this file is the only complete copy of older trades.

**Step 1: code preparation (normal PRs, no cloud accounts needed)**
4. PostgreSQL support: driver, URL normalisation, pool settings, NULL ordering, deterministic security name
   (section 7, items 1 to 5), with the test suite also running on PostgreSQL in CI.
5. CORS setting; frontend `VITE_API_BASE`, wake-up retry, message and warm-up request (items 6 and 7).
6. Data copy script and a short runbook (item 8).
7. `ci.yml` and `ingest.yml` (schedule plus manual dispatch) (item 9). Do not add secrets yet.
8. Run the whole stack locally against a local PostgreSQL, then run tests, type check and build.

**Step 2: database**
9. Create the Neon project (free). Record the direct and pooled connection strings. Choose a region close to Render's.
10. Run `alembic upgrade head` against Neon. Confirm version `0004`.
11. Run the copy script from your machine with the backed-up `poltracker.db`. Verify row counts match
    (105 politicians, 1,062 securities, 5,381 trades, 272,477 price bars, plus the single `ingest_state` row).
12. Point a local API at Neon and compare a few responses with SQLite. Check SSL, latency and the pooled versus
    direct connection behaviour.

**Step 3: backend**
13. Create the Render free web service from the repository. Set the build and start commands, `DATABASE_URL`,
    and `CORS_ORIGINS` (filled in after step 14).
14. Verify `GET /health` and `GET /status`. Measure the real cold-start time and what the browser sees while waking.

**Step 4: frontend**
15. Connect Cloudflare Pages: root `frontend`, build `npm run build`, output `dist`, `VITE_API_BASE` set to the
    Render URL. Update `CORS_ORIGINS` and redeploy the API.
16. Test deep links, light and dark mode, mobile, and the cold-start message on the live site.

**Step 5: scheduler**
17. Add `DATABASE_URL` as a GitHub repository secret (a repository settings change).
18. Run `ingest.yml` manually once. Confirm `last_ingested_at` advances and no duplicates appear.
19. Enable the 6-hourly schedule. After a few days, confirm runs actually fire. Note the 60-day rule in the runbook.

**Step 6: operations**
20. Add an export workflow (for example weekly) and test a restore once.
21. Document the runbook: re-enable a disabled workflow, rotate `DATABASE_URL`, and move to an alternative host.
22. Add the live URLs and a deployment note to the README.

**Rollback:** the frontend, API and scheduler are independent. Revert or redeploy each separately. The database can be
restored from the backups in steps 3 and 20.

---

## Appendix A. Not verified in this research

- Whether Cloudflare Pages needs a credit card on the free plan, and Pages' behaviour once the 500 builds are used
- What a browser's request sees during Render's roughly 1-minute spin-up (502/503, hang, or a loading page)
- Neon: free-plan compute size, the egress-overage behaviour, behaviour of pooled connections with psycopg 3 prepared
  statements, and the PostgreSQL version Neon runs
- Whether GitHub counts commits, PRs or other events as "repository activity" for the 60-day rule, and whether manual
  or dispatch triggers still work while a scheduled workflow is disabled
- Whether GitHub runner IPs are rate-limited by Yahoo or share the CongressInvests per-IP quota with other users
- Render: free instance RAM (I relied on third-party reports of 512 MB), native Python runtime requirements
- Vercel serverless cold-start time, FastAPI Cloud persistence and outbound access, Koyeb's actual card requirement
- GitHub Actions artifact retention and storage limits for backups
- Turso with SQLAlchemy; Cloud Run billing-account requirement; Oracle free-tier terms
- Everything in section 11 comes from the earlier research (some from secondary sources)

---

## Appendix B. Sources

Official documentation fetched 2026-10-06 **[V]**:

- Render free tier: https://render.com/docs/free
- Neon pricing: https://neon.com/pricing, plans: https://neon.com/docs/introduction/plans, scale to zero:
  https://neon.com/docs/introduction/scale-to-zero
- Cloudflare Pages: https://developers.cloudflare.com/pages/platform/limits/,
  https://developers.cloudflare.com/pages/functions/pricing/,
  https://developers.cloudflare.com/pages/configuration/serving-pages/
- Cloudflare Workers limits: https://developers.cloudflare.com/workers/platform/limits/
- GitHub Actions: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows,
  https://docs.github.com/en/actions/reference/limits,
  https://docs.github.com/en/actions/concepts/billing-and-usage,
  https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows
- Vercel: https://vercel.com/docs/plans/hobby, https://vercel.com/docs/cron-jobs/usage-and-pricing,
  https://vercel.com/docs/frameworks/backend/fastapi
- Hugging Face Spaces: https://huggingface.co/docs/hub/spaces-overview
- FastAPI Cloud: https://fastapicloud.com/pricing
- Supabase: https://supabase.com/pricing, https://supabase.com/docs/guides/platform/billing-on-supabase
- Aiven free PostgreSQL: https://aiven.io/free-postgresql-database
- Turso: https://turso.tech/pricing
- Railway: https://railway.com/pricing, https://docs.railway.com/reference/pricing/plans
- Fly.io: https://docs.fly.io/about/pricing
- CongressInvests: https://congressinfor-production.up.railway.app/docs

Secondary sources **[S]**: search summaries and third-party articles for Render's card verification and RAM, Neon's
card requirement and acquisition, Koyeb's free instance, Google Cloud Run's free tier, Hetzner and Oracle, and Yahoo
throttling reports (community issues in https://github.com/ranaroussi/yfinance/issues).

**Measurements [M]:** the application figures in section 2.1 and the PostgreSQL test in section 2.2 were produced
locally on 2026-10-06 in a scratch copy of the repository. No application code was changed.
