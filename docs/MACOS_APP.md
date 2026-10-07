# POLTRACKER for macOS

A standalone Apple Silicon app: native window (pywebview/WKWebView) around the existing React dashboard, served by the
existing FastAPI backend on `127.0.0.1:<random port>`, with a local SQLite database. No Terminal, Node, Python, cloud
database or hosting is needed to run it.

## Local development (unchanged)

```
python3 -m venv .venv && .venv/bin/pip install -e ".[dev,desktop]"
.venv/bin/uvicorn poltracker.api.main:app --reload        # API on :8000, SQLite poltracker.db
cd frontend && npm ci && npm run dev                       # dashboard on :5173, proxies /api
.venv/bin/python -m poltracker.desktop.main                # optional: run the desktop shell from source
```

## Build

```
./scripts/build-macos.sh        # type-checks and builds the frontend, then PyInstaller
```

Output: `release/POLTRACKER.app` (arm64, about 94 MB, bundle id `com.roamingwizards.poltracker`). The recipe is
`packaging/macos/poltracker.spec`. Drop `POLTRACKER.icns` into `packaging/macos/icon/` to add an icon.
`POLTRACKER --selftest` (`open release/POLTRACKER.app --args --selftest`) drives the real window through every page and
writes `selftest.json` to the data folder.

## Where things live

| What | Path |
| --- | --- |
| Database | `~/Library/Application Support/POLTRACKER/poltracker.db` (never inside the .app) |
| Pre-upgrade backups | next to the database: `poltracker.db.backup-<schema>-<timestamp>` |
| Log | `~/Library/Logs/POLTRACKER/poltracker.log` |

Overrides for development: `POLTRACKER_HOME` (data folder), `POLTRACKER_DATABASE_URL` (explicit database). A cloud
`DATABASE_URL` in the environment is ignored by the desktop app. No `.env` is read or needed; no secrets are bundled.

## First run and refresh

First launch creates the database, applies the Alembic migrations, then downloads congressional trades and market prices
in the background. The window opens immediately with a progress banner; pages fill in as data arrives. While the app is
open it checks every minute whether the last successful update is older than 6 hours, and updates when it is (failures
back off 15 min, doubling). **Data Status > Background refresh** shows the state and an "Update now" button. With no
network the app opens with the saved data and shows a notice.

Existing data: `.venv/bin/python -m poltracker.desktop.importer path/to/poltracker.db` copies a local database into the
app (verified table by table; the original is never modified; `--replace` keeps the previous app database as a backup).

## Unsigned app and Gatekeeper

The build is ad-hoc signed only. A copy built on your own Mac opens normally. A copy downloaded or AirDropped carries a
quarantine flag, and Gatekeeper rejects it (`spctl` reports "rejected"): right-click > Open once, or
`xattr -dr com.apple.quarantine POLTRACKER.app`.

To distribute properly later (not done, needs a paid Apple Developer membership): sign with a Developer ID Application
certificate (`codesign --options runtime --timestamp`, deep-signing the bundled libraries), notarize with
`xcrun notarytool submit --wait`, staple the ticket, package a DMG, and attach it to a GitHub Release.

## Known limits

- Cmd-Q ends the process without running Python's shutdown hooks; no process is left behind and SQLite's WAL keeps the
  database consistent, but the "shut down cleanly" log line is only written when the window is closed normally.
- Apple Silicon only; Intel Macs are not built.
