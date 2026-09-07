#!/bin/sh
# Seed, then serve. Both from /app/src/backend, because DATABASE_URL defaults to
# the relative `sqlite:///./neev.db` and the seed must write the same file
# uvicorn will read.
set -e

cd /app/src/backend

# --reset is safe and wanted here: the filesystem is ephemeral, so this is a
# fresh database on every cold start, not a destructive act on a real one.
echo "Seeding ${DATABASE_URL:-sqlite:///./neev.db} ..."
python -m app.db.seed --reset

# Cloud Run injects PORT and expects the container to listen on it.
echo "Serving on :${PORT:-8080} (NEEV_MODE=${NEEV_MODE:-fixture})"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"
