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

# Refuse to start on an occupied port rather than serving a frontend that points
# at someone else's process. This is not hypothetical: a VS Code helper listens
# on 127.0.0.1:8000 on this machine, so uvicorn lost the port silently and every
# screen failed with "could not reach the backend" -- which reads like a bug in
# the app rather than a port clash.
port_owner() { lsof -nP -iTCP:"$1" -sTCP:LISTEN -t 2>/dev/null | head -1; }

first_free_port() {
  local port="$1"
  while [ -n "$(port_owner "$port")" ]; do port=$((port + 1)); done
  echo "$port"
}

if [ -n "$(port_owner "$BE_PORT")" ]; then
  owner_pid="$(port_owner "$BE_PORT")"
  owner_cmd="$(ps -p "$owner_pid" -o comm= 2>/dev/null || echo unknown)"
  suggested="$(first_free_port "$BE_PORT")"
  echo "Port $BE_PORT is already taken by PID $owner_pid ($owner_cmd)."
  echo "Using $suggested for the backend instead."
  BE_PORT="$suggested"
fi

if [ -n "$(port_owner "$FE_PORT")" ]; then
  owner_pid="$(port_owner "$FE_PORT")"
  echo "Port $FE_PORT is already taken by PID $owner_pid."
  echo "Stop it first (kill $owner_pid), or set FE_PORT. Next refuses a second"
  echo "dev server for the same project, so this cannot be worked around."
  exit 1
fi

if [ ! -x "src/backend/.venv/bin/python" ]; then
  echo "Creating the backend venv (Python 3.11)..."
  "${PYTHON311:-/opt/homebrew/bin/python3.11}" -m venv src/backend/.venv
  src/backend/.venv/bin/pip install -q -e "src/backend[dev]"
fi

if [ ! -d "src/frontend/node_modules" ]; then
  echo "Installing frontend dependencies..."
  (cd src/frontend && npm install)
fi

# Pin the backend port where Next will find it however the frontend is started.
# NEEV_API_BASE passed inline only survives when the frontend is launched by this
# script; start it by hand -- or let this script's env not propagate -- and
# lib/api.ts silently falls back to its hardcoded :8000 default, which is how a
# frontend ends up calling a port it does not own. .env.local is read by Next
# automatically, so `npm run dev` on its own now points at the right backend too.
ENV_LOCAL="src/frontend/.env.local"
{
  echo "# Written by scripts/dev.sh -- do not edit by hand."
  echo "# The backend port this script chose. Regenerated on every run."
  echo "NEEV_API_BASE=http://127.0.0.1:$BE_PORT"
} > "$ENV_LOCAL"
echo "Wrote $ENV_LOCAL -> http://127.0.0.1:$BE_PORT"

echo "Seeding the database..."
(cd src/backend && .venv/bin/python -m app.db.seed --reset)

cleanup() { echo; echo "Stopping..."; kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "Starting backend on :$BE_PORT (NEEV_MODE=fixture)..."
(cd "$ROOT/src/backend" && NEEV_MODE=fixture .venv/bin/python -m uvicorn app.main:app --port "$BE_PORT" --reload) &

echo "Starting frontend on :$FE_PORT..."
(cd "$ROOT/src/frontend" && NEEV_API_BASE="http://127.0.0.1:$BE_PORT" npm run dev -- --port "$FE_PORT") &

for _ in $(seq 1 30); do
  curl -fsS "http://127.0.0.1:$BE_PORT/api/health" >/dev/null 2>&1 && break
  sleep 1
done

if ! curl -fsS "http://127.0.0.1:$BE_PORT/api/health" >/dev/null 2>&1; then
  echo
  echo "The backend is not answering on :$BE_PORT. The frontend would load but"
  echo "every screen would fail with \"could not reach the backend\". Stopping."
  exit 1
fi

echo "Backend healthy: $(curl -fsS "http://127.0.0.1:$BE_PORT/api/health")"
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
