#!/usr/bin/env bash
# Build release/POLTRACKER.app (Apple Silicon, unsigned). Run from anywhere; needs the repo's .venv and Node.
set -euo pipefail
cd "$(dirname "$0")/.."

PY=".venv/bin/python"
[ -x "$PY" ] || { echo "No .venv found. Create it: python3 -m venv .venv && .venv/bin/pip install -e '.[desktop]'" >&2; exit 1; }
[ "$(uname -m)" = "arm64" ] || { echo "This build targets Apple Silicon (arm64)." >&2; exit 1; }
"$PY" -c "import PyInstaller, webview" 2>/dev/null || { echo "Missing desktop extras: .venv/bin/pip install -e '.[desktop]'" >&2; exit 1; }

echo "==> Frontend"
( cd frontend && { [ -d node_modules ] || npm ci; } && npx tsc -b && npm run build )

echo "==> Packaging"
rm -rf build/pyinstaller release/POLTRACKER.app
"$PY" -m PyInstaller --noconfirm --clean \
  --workpath build/pyinstaller --distpath build/dist packaging/macos/poltracker.spec

mkdir -p release
mv build/dist/POLTRACKER.app release/POLTRACKER.app
echo "==> Built release/POLTRACKER.app ($(du -sh release/POLTRACKER.app | cut -f1))"
