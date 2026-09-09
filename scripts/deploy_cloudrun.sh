#!/usr/bin/env bash
# Deploy Neev to Cloud Run: backend first, then the frontend pointed at it.
#
# Run this yourself -- it calls `gcloud`, which the CLAUDE.md dry-run rules keep
# out of agent hands. Nothing here bills Gemini or BigQuery: both services
# deploy in NEEV_MODE=fixture, serving whatever is in
# src/backend/app/fixtures/. Capture real runs first (see
# scripts/record_golden_run.py) and the deployed app serves real figures.
#
#   bash scripts/deploy_cloudrun.sh
#
# Prerequisites, once per project:
#   gcloud auth login
#   gcloud config set project buildguard-ai-2026
#   gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
#       artifactregistry.googleapis.com
set -euo pipefail

if [ "${NEEV_DEPLOY_SANDBOX:-0}" != "1" ]; then
  echo "Refusing deployment: this build has demo login and ephemeral data only."
  echo "After owner approval, explicitly set NEEV_DEPLOY_SANDBOX=1 for synthetic-data demos."
  exit 1
fi

PROJECT="${GOOGLE_CLOUD_PROJECT:-buildguard-ai-2026}"
REGION="${REGION:-asia-south1}"
BACKEND="${BACKEND_SERVICE:-neev-api}"
FRONTEND="${FRONTEND_SERVICE:-neev-web}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Signs the demo session cookie. Without it the backend picks a random key per
# process, and at --min-instances 0 Cloud Run recycles the instance after about
# fifteen idle minutes: a visitor who reads a page, steps away and comes back
# would be bounced to /login by a cookie signed with a key that no longer
# exists. Pass your own to keep sessions across a redeploy; generated here so
# forgetting cannot leave it empty.
SESSION_SECRET="${NEEV_SESSION_SECRET:-$(openssl rand -hex 32)}"

echo "Project : $PROJECT"
echo "Region  : $REGION"
echo

# --- backend -----------------------------------------------------------------
# Context is the repo root, because the image needs both src/backend/ and
# fixtures/ (the seed reads fixtures/draw_schedule.csv via a repo-root path).
# `gcloud run deploy --source` builds with the Dockerfile at the root of the
# context, which is why ./Dockerfile is the backend's and the frontend keeps its
# own under src/frontend/.
#
# max-instances=1 IS a correctness requirement: SQLite lives on the instance's
# own disk, so two instances would serve two different databases and a decision
# written on one would be invisible to the other.
#
# min-instances=0 is a cost one. Keeping an instance warm for a fortnight bills
# about 1.2M vCPU-seconds against a 180k free tier -- roughly Rs 2,530 to answer
# nobody at 3am. The price is a 3-6 second cold start (the entrypoint reseeds on
# boot); hit the URL once before presenting and no viewer sees it. Decisions
# recorded during a session are lost when the instance recycles after 15 idle
# minutes, which for a demo is arguably right: every visitor gets clean state.
echo "==> Building and deploying $BACKEND"
gcloud run deploy "$BACKEND" \
  --project "$PROJECT" \
  --region "$REGION" \
  --source . \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 1 \
  --memory 1Gi \
  --timeout 300 \
  --set-env-vars "NEEV_MODE=fixture,NEEV_DEMO_AUTH=true,NEEV_SESSION_SECRET=$SESSION_SECRET"

API_URL="$(gcloud run services describe "$BACKEND" \
  --project "$PROJECT" --region "$REGION" --format='value(status.url)')"
echo "Backend URL: $API_URL"

# Fail here rather than deploying a frontend pointed at a broken API.
echo "==> Checking $API_URL/api/health"
curl -fsS "$API_URL/api/health" && echo

# --- frontend ----------------------------------------------------------------
# NEEV_API_BASE is server-side only: lib/api.ts imports 'server-only' and the
# variable has no NEXT_PUBLIC_ prefix, so the browser never learns the backend's
# address and every call is a server-to-server hop inside Cloud Run. That is
# also why no CORS configuration is needed.
echo "==> Building and deploying $FRONTEND"
gcloud run deploy "$FRONTEND" \
  --project "$PROJECT" \
  --region "$REGION" \
  --source src/frontend \
  --allow-unauthenticated \
  --min-instances 0 \
  --memory 1Gi \
  --set-env-vars "NEEV_API_BASE=$API_URL"

WEB_URL="$(gcloud run services describe "$FRONTEND" \
  --project "$PROJECT" --region "$REGION" --format='value(status.url)')"

echo
echo "──────────────────────────────────────────────────────────────"
echo "  Neev is live:  $WEB_URL"
echo "  API:           $API_URL"
echo "──────────────────────────────────────────────────────────────"
echo
echo "Sign in with any 10-digit number. 'Home owner' lands on loan 1001;"
echo "'Bank officer' opens the portfolio. Auth is a demo session, not a"
echo "credential -- see src/backend/app/api/deps.py."
