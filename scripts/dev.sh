#!/usr/bin/env bash
# Start both halves of the Neev app for local development or a demo.
#
# Runs entirely in fixture mode: no Gemini, no BigQuery, no billed Google call of
# any kind. The backend venv contains no google-* package, so there is nothing
# there that could bill even if it were asked to.
#
#   bash scripts/dev.sh            # backend 8000, frontend 3000
#   BE_PORT=8010 FE_PORT=3010 bash scripts/dev.sh
#
# Ctrl-C stops both.

set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"

BE_PORT="${BE_PORT:-8000}"
FE_PORT="${FE_PORT:-3000}"

if [ ! -x "src/backend/.venv/bin/python" ]; then
  echo "Creating the backend venv (Python 3.11)..."
  "${PYTHON311:-/opt/homebrew/bin/python3.11}" -m venv src/backend/.venv
  src/backend/.venv/bin/pip install -q -e "src/backend[dev]"
fi

if [ ! -d "src/frontend/node_modules" ]; then
  echo "Installing frontend dependencies..."
  (cd src/frontend && npm install)
fi

echo "Seeding the database..."
(cd src/backend && .venv/bin/python -m app.db.seed --reset)

cleanup() { echo; echo "Stopping..."; kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "Starting backend on :$BE_PORT (NEEV_MODE=fixture)..."
(cd "$ROOT/src/backend" && NEEV_MODE=fixture .venv/bin/python -m uvicorn app.main:app --port "$BE_PORT" --reload) &

echo "Starting frontend on :$FE_PORT..."
(cd "$ROOT/src/frontend" && NEEV_API_BASE="http://127.0.0.1:$BE_PORT" npm run dev -- --port "$FE_PORT") &

sleep 6
cat <<EOF

  Neev is up. The four demo beats, in order:

  1  Before signing     http://localhost:$FE_PORT/owner/loans/1001/boq
  2  At sanction        http://localhost:$FE_PORT/owner/loans/1001/sanction
  3  The bank's view    http://localhost:$FE_PORT/bank/portfolio
  4  The decision       http://localhost:$FE_PORT/bank/loans/1001/tranches/4

  Public         http://localhost:$FE_PORT/
  Log in         http://localhost:$FE_PORT/login
  API docs       http://localhost:$BE_PORT/docs

  Ctrl-C stops both.

EOF
wait
